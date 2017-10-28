#  Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List, Iterable, Optional, Union, Dict, Tuple
from contextlib import contextmanager

class Writer:
    def __init__(self):
        self.strings = []
        self.current_indent = ''
        self.needs_indent = False

    def write(self, s: str):
        assert '\n' not in s
        if self.needs_indent:
            self.strings.append(self.current_indent)
            self.needs_indent = False
        self.strings.append(s)

    def writeln(self, s: str):
        self.write(s)
        self.strings.append('\n')
        self.needs_indent = True

    @contextmanager
    def indent(self):
        old_indent = self.current_indent
        self.current_indent = self.current_indent + '  '
        yield
        self.current_indent = old_indent

class ExprType:
    def __eq__(self, other) -> bool: ...  # pragma: no cover

    def __str__(self) -> str: ...  # pragma: no cover

class BoolType(ExprType):
    def __eq__(self, other):
        return isinstance(other, BoolType)

    def __str__(self):
        return 'bool'

# A type with no values. This is the return type of functions that never return.
class BottomType(ExprType):
    def __eq__(self, other):
        return isinstance(other, BottomType)

    def __str__(self):
        return 'BottomType'

class IntType(ExprType):
    def __eq__(self, other):
        return isinstance(other, IntType)

    def __str__(self):
        return 'int'

class TypeType(ExprType):
    def __eq__(self, other):
        return isinstance(other, TypeType)

    def __str__(self):
        return 'Type'

class ErrorOrVoidType(ExprType):
    def __eq__(self, other):
        return isinstance(other, ErrorOrVoidType)

    def __str__(self):
        return 'ErrorOrVoid'

class FunctionType(ExprType):
    def __init__(self, argtypes: List[ExprType], returns: ExprType):
        self.argtypes = argtypes
        self.returns = returns

    def __eq__(self, other):
        return isinstance(other, FunctionType) and self.__dict__ == other.__dict__

    def __str__(self):
        return 'Callable[[%s], %s]' % (
            ', '.join(str(arg)
                      for arg in self.argtypes),
            str(self.returns))

class ListType(ExprType):
    def __init__(self, elem_type: ExprType):
        assert not isinstance(elem_type, FunctionType)
        self.elem_type = elem_type

    def __eq__(self, other):
        return isinstance(other, ListType) and self.__dict__ == other.__dict__

    def __str__(self):
        return 'List[%s]' % str(self.elem_type)

class CustomTypeArgDecl:
    def __init__(self, name: str, type: ExprType):
        self.name = name
        self.type = type

    def __eq__(self, other):
        return isinstance(other, CustomTypeArgDecl) and self.__dict__ == other.__dict__

    def __str__(self):
        return '%s: %s' % (self.name, str(self.type))

class CustomType(ExprType):
    def __init__(self, name: str, arg_types: List[CustomTypeArgDecl]):
        self.name = name
        self.arg_types = arg_types

    def __eq__(self, other):
        return isinstance(other, CustomType) and self.__dict__ == other.__dict__

    def __str__(self):
        return self.name

    def write(self, writer: Writer, verbose: bool):
        writer.writeln('class %s:' % self.name)
        with writer.indent():
            writer.writeln('def __init__(%s):' % ', '.join(str(arg)
                                                           for arg in self.arg_types))
            with writer.indent():
                for arg in self.arg_types:
                    writer.writeln('self.%s = %s' % (arg.name, arg.name))

class Expr:
    def __init__(self, type: ExprType):
        self.type = type

    # Note: it's the caller's responsibility to de-duplicate VarReference objects that reference the same symbol, if
    # desired.
    def get_free_variables(self) -> 'Iterable[VarReference]': ...  # pragma: no cover

    def __str__(self) -> str: ...  # pragma: no cover

    def describe_other_fields(self) -> str: ...  # pragma: no cover

class FunctionArgDecl:
    def __init__(self, type: ExprType, name: str = ''):
        self.type = type
        self.name = name

    def __str__(self):
        return '%s: %s' % (self.name, str(self.type))

class VarReference(Expr):
    def __init__(self, type: ExprType, name: str, is_global_function: bool, is_function_that_may_throw: bool):
        super().__init__(type=type)
        assert name
        self.name = name
        self.is_global_function = is_global_function
        self.is_function_that_may_throw = is_function_that_may_throw

    def get_free_variables(self):
        if not self.is_global_function:
            yield self

    def __str__(self):
        return self.name

    def describe_other_fields(self):
        return 'is_global_function=%s, is_function_that_may_throw=%s' % (
            self.is_global_function,
            self.is_function_that_may_throw)

class MatchCase:
    def __init__(self,
                 type_patterns: List[str],
                 matched_var_names: List[str],
                 expr: 'FunctionCall'):
        self.type_patterns = type_patterns
        self.matched_var_names = matched_var_names
        self.expr = expr

    def is_main_definition(self):
        return set(self.type_patterns) == set(self.matched_var_names)

    def write(self, writer: Writer):
        writer.writeln('TypePattern(\'%s\')' % '\', \''.join(self.type_patterns))
        with writer.indent():
            writer.writeln('lambda %s:' % ', '.join(self.matched_var_names))
            with writer.indent():
                writer.write(str(self.expr))
                writer.writeln(',')

class MatchExpr(Expr):
    def __init__(self, matched_vars: List[VarReference], match_cases: List[MatchCase]):
        assert matched_vars
        assert match_cases
        for match_case in match_cases:
            assert len(match_case.type_patterns) == len(matched_vars)
        super().__init__(type=match_cases[0].expr.type)
        self.matched_vars = matched_vars
        self.match_cases = match_cases

        assert len([match_case
                    for match_case in match_cases
                    if match_case.is_main_definition()]) <= 1

    def get_free_variables(self):
        for expr in self.matched_vars:
            for var in expr.get_free_variables():
                yield var
        for match_case in self.match_cases:
            local_vars = set(match_case.matched_var_names)
            for var in match_case.expr.get_free_variables():
                if var.name not in local_vars:
                    yield var

    def write(self, writer: Writer):
        writer.writeln('match(%s)({' % ', '.join(var.name
                                                 for var in self.matched_vars))
        with writer.indent():
            for case in self.match_cases:
                case.write(writer)
        writer.writeln('})')

    def describe_other_fields(self):
        return ''

class BoolLiteral(Expr):
    def __init__(self, value: bool):
        super().__init__(BoolType())
        self.value = value

    def get_free_variables(self):
        if False:
            yield

    def __str__(self):
        return repr(self.value)

    def describe_other_fields(self):
        return ''


class TypeLiteral(Expr):
    def __init__(self, cpp_type: str, args: Dict[str, VarReference]):
        super().__init__(type=TypeType())
        self.cpp_type = cpp_type
        self.args = args

    def get_free_variables(self):
        for arg in self.args.values():
            for var in arg.get_free_variables():
                yield var

    def __str__(self):
        return 'Type(\'%s\'%s)' % (self.cpp_type, ''.join(', %s=%s' % (arg_name, str(arg_expr))
                                                          for arg_name, arg_expr in self.args.items()))

    def describe_other_fields(self):
        return ''

class ListExpr(Expr):
    def __init__(self, elem_type: ExprType, elems: List[VarReference]):
        assert not isinstance(elem_type, FunctionType)
        super().__init__(type=ListType(elem_type))
        self.elem_type = elem_type
        self.elems = elems

    def get_free_variables(self):
        for expr in self.elems:
            for var in expr.get_free_variables():
                yield var

    def __str__(self):
        return '[%s]' % ', '.join(var.name
                                  for var in self.elems)

    def describe_other_fields(self):
        return ''

class FunctionCall(Expr):
    def __init__(self, fun: VarReference, args: List[VarReference]):
        assert isinstance(fun.type, FunctionType)
        assert len(fun.type.argtypes) == len(args)
        super().__init__(type=fun.type.returns)
        self.fun = fun
        self.args = args

    def get_free_variables(self):
        for var in self.fun.get_free_variables():
            yield var
        for expr in self.args:
            for var in expr.get_free_variables():
                yield var

    def __str__(self):
        return '%s(%s)' % (
            self.fun.name,
            ', '.join(var.name
                      for var in self.args))

    def describe_other_fields(self):
        return '; '.join('%s: %s' % (var.name, var.describe_other_fields())
                         for vars in ([self.fun], self.args)
                         for var in vars)

class EqualityComparison(Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference):
        super().__init__(type=BoolType())
        assert (lhs.type == ErrorOrVoidType() and rhs.type == TypeType()) or (lhs.type == rhs.type), '%s vs %s' % (str(lhs.type), str(rhs.type))
        assert not isinstance(lhs.type, FunctionType)
        self.lhs = lhs
        self.rhs = rhs

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

    def __str__(self):
        return '%s == %s' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self):
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class AttributeAccessExpr(Expr):
    def __init__(self, var: VarReference, attribute_name: str, type: ExprType):
        super().__init__(type=type)
        assert isinstance(var.type, (TypeType, CustomType))
        self.var = var
        self.attribute_name = attribute_name
        self.type = type

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

    def __str__(self):
        return '%s.%s' % (self.var.name, self.attribute_name)

    def describe_other_fields(self):
        return ''

class IntLiteral(Expr):
    def __init__(self, value: int):
        super().__init__(type=IntType())
        self.value = value

    def get_free_variables(self):
        if False:
            yield

    def __str__(self):
        return str(self.value)

    def describe_other_fields(self):
        return ''

class NotExpr(Expr):
    def __init__(self, var: VarReference):
        assert var.type == BoolType()
        super().__init__(type=BoolType())
        self.var = var

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

    def __str__(self):
        return 'not %s' % self.var.name

    def describe_other_fields(self):
        return self.var.describe_other_fields()

class UnaryMinusExpr(Expr):
    def __init__(self, var: VarReference):
        assert var.type == IntType()
        super().__init__(type=IntType())
        self.var = var

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

    def __str__(self):
        return '-%s' % self.var.name

    def describe_other_fields(self):
        return self.var.describe_other_fields()

class IntComparisonExpr(Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference, op: str):
        assert lhs.type == IntType()
        assert rhs.type == IntType()
        assert op in ('<', '>', '<=', '>=')
        super().__init__(type=BoolType())
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

    def __str__(self):
        return '%s %s %s' % (self.lhs.name, self.op, self.rhs.name)

    def describe_other_fields(self):
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class IntBinaryOpExpr(Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference, op: str):
        assert lhs.type == IntType()
        assert rhs.type == IntType()
        assert op in ('+', '-', '*', '//', '%')
        super().__init__(type=IntType())
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

    def __str__(self):
        return '%s %s %s' % (self.lhs.name, self.op, self.rhs.name)

    def describe_other_fields(self):
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class ListConcatExpr(Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference):
        assert isinstance(lhs.type, ListType)
        assert lhs.type == rhs.type
        super().__init__(type=lhs.type)
        self.lhs = lhs
        self.rhs = rhs

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

    def __str__(self):
        return '%s + %s' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self):
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class IsInstanceExpr(Expr):
    def __init__(self, var: VarReference, checked_type: CustomType):
        super().__init__(type=BoolType())
        self.var = var
        self.checked_type = checked_type

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

    def __str__(self):
        return 'isinstance(%s, %s)' % (self.var.name, str(self.checked_type))

    def describe_other_fields(self):
        return ''

class SafeUncheckedCast(Expr):
    def __init__(self, var: VarReference, type: ExprType):
        assert isinstance(var.type, ErrorOrVoidType)
        assert isinstance(type, CustomType)
        super().__init__(type=type)
        self.var = var

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

    def __str__(self):
        return '%s  # type: %s' % (self.var.name, str(self.type))

    def describe_other_fields(self):
        return ''

class ListComprehensionExpr(Expr):
    def __init__(self, list_var: VarReference, loop_var: VarReference, result_elem_expr: FunctionCall):
        assert isinstance(list_var.type, ListType)
        assert list_var.type.elem_type == loop_var.type
        super().__init__(type=ListType(result_elem_expr.type))
        self.list_var = list_var
        self.loop_var = loop_var
        self.result_elem_expr = result_elem_expr

    def get_free_variables(self):
        for var in self.list_var.get_free_variables():
            yield var
        for var in self.result_elem_expr.get_free_variables():
            if var.name != self.loop_var.name:
                yield var

    def __str__(self):
        return '[%s for %s in %s]' % (str(self.result_elem_expr), self.loop_var.name, self.list_var.name)

    def describe_other_fields(self):
        return ''

class ReturnTypeInfo:
    def __init__(self, type: Optional[ExprType], always_returns: bool):
        # When expr_type is None, the statement never returns.
        # expr_type can't be None if always_returns is True.
        self.type = type
        self.always_returns = always_returns

class Stmt:
    # Note: it's the caller's responsibility to de-duplicate VarReference objects that reference the same symbol, if
    # desired.
    def get_free_variables(self) -> 'Iterable[VarReference]': ...  # pragma: no cover

    def write(self, writer: Writer, verbose: bool): ...  # pragma: no cover

class Assert(Stmt):
    def __init__(self, var: VarReference, message: str):
        assert isinstance(var.type, BoolType)
        self.var = var
        self.message = message

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

    def write(self, writer: Writer, verbose: bool):
        writer.write('assert ')
        writer.write(self.var.name)
        if verbose:
            writer.writeln('  # %s' % self.var.describe_other_fields())
        else:
            writer.writeln('')

class Assignment(Stmt):
    def __init__(self,
                 lhs: VarReference,
                 rhs: Expr,
                 lhs2: Optional[VarReference] = None):
        assert lhs.type == rhs.type
        if lhs2:
            assert isinstance(lhs2.type, ErrorOrVoidType)
            assert isinstance(rhs, (MatchExpr, FunctionCall, ListComprehensionExpr))
        self.lhs = lhs
        self.lhs2 = lhs2
        self.rhs = rhs

    def get_free_variables(self):
        for var in self.rhs.get_free_variables():
            yield var

    def write(self, writer: Writer, verbose: bool):
        writer.write(self.lhs.name)
        if self.lhs2:
            writer.write(', ')
            writer.write(self.lhs2.name)
        writer.write(' = ')
        if isinstance(self.rhs, MatchExpr):
            self.rhs.write(writer)
        else:
            writer.write(str(self.rhs))
            if verbose:
                writer.writeln('  # lhs: %s; rhs: %s' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields()))
            else:
                writer.writeln('')

class ReturnStmt(Stmt):
    def __init__(self, result: Optional[VarReference], error: Optional[VarReference]):
        assert result or error
        self.result = result
        self.error = error

    def get_free_variables(self):
        for expr in (self.result, self.error):
            if expr:
                for var in expr.get_free_variables():
                    yield var

    def write(self, writer: Writer, verbose: bool):
        writer.write('return ')
        writer.write(str(self.result))
        writer.write(', ')
        writer.write(str(self.error))
        if verbose:
            writer.writeln('  # result: %s, error: %s' % (
                self.result.describe_other_fields() if self.result else '',
                self.error.describe_other_fields() if self.error else ''))
        else:
            writer.writeln('')

class IfStmt(Stmt):
    def __init__(self, cond: VarReference, if_stmts: List[Stmt], else_stmts: List[Stmt]):
        assert cond.type == BoolType()
        assert if_stmts
        self.cond = cond
        self.if_stmts = if_stmts
        self.else_stmts = else_stmts

    def get_free_variables(self):
        for var in self.cond.get_free_variables():
            yield var
        for stmts in (self.if_stmts, self.else_stmts):
            for var in get_free_variables_in_stmts(stmts):
                yield var

    def write(self, writer: Writer, verbose: bool):
        writer.write('if %s:' % self.cond.name)
        if verbose:
            writer.writeln('  # %s' % self.cond.describe_other_fields())
        else:
            writer.writeln('')
        with writer.indent():
            for stmt in self.if_stmts:
                stmt.write(writer, verbose)
            if not self.if_stmts:
                writer.writeln('pass')
        if self.else_stmts:
            writer.writeln('else:')
            with writer.indent():
                for stmt in self.else_stmts:
                    stmt.write(writer, verbose)

class FunctionDefn:
    def __init__(self,
                 name: str,
                 args: List[FunctionArgDecl],
                 body: List[Stmt],
                 return_type: ExprType):
        assert body
        self.name = name
        self.args = args
        self.body = body
        self.return_type = return_type

    def write(self, writer: Writer, verbose: bool):
        writer.writeln('def %s(%s) -> %s:' % (
            self.name,
            ', '.join('%s: %s' % (arg.name, str(arg.type))
                      for arg in self.args),
            str(self.return_type)))
        with writer.indent():
            for stmt in self.body:
                stmt.write(writer, verbose)
        writer.writeln('')

class CheckIfErrorDefn:
    def __init__(self, error_types_and_messages: List[Tuple[CustomType, str]]):
        self.error_types_and_messages = error_types_and_messages

    def write(self, writer: Writer, verbose: bool):
        writer.writeln('def check_if_error(x):')
        with writer.indent():
            for error_type, error_message in self.error_types_and_messages:
                writer.writeln('if isinstance(x, %s):' % error_type.name)
                with writer.indent():
                    writer.writeln('... # builtin')
            if not self.error_types_and_messages:
                writer.writeln('... # builtin')
        writer.writeln('')

class Module:
    def __init__(self, body: List[Union[FunctionDefn, Assignment, Assert, CustomType]]):
        self.body = body

    def __str__(self):
        writer = Writer()
        for elem in self.body:
            elem.write(writer, verbose=False)
        return ''.join(writer.strings)

def get_free_variables_in_stmts(stmts: List[Stmt]):
    local_var_names = set()
    for stmt in stmts:
        for var in stmt.get_free_variables():
            if var.name not in local_var_names:
                yield var
        if isinstance(stmt, Assignment):
            local_var_names.add(stmt.lhs.name)
            if stmt.lhs2:
                local_var_names.add(stmt.lhs2.name)

def get_unique_free_variables_in_stmts(stmts: List[Stmt]) -> List[VarReference]:
    var_by_name = dict()
    for var in get_free_variables_in_stmts(stmts):
        if var.name not in var_by_name:
            var_by_name[var.name] = var
    return list(sorted(var_by_name.values(),
                       key=lambda var: var.name))
