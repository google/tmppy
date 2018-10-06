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

from typing import Iterable, Optional, Union, Tuple, Set, Sequence
from contextlib import contextmanager

import itertools

from _py2tmp import utils

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

class ExprType(utils.ValueType):
    def __str__(self) -> str: ...  # pragma: no cover

class BoolType(ExprType):
    def __str__(self):
        return 'bool'

# A type with no values. This is the return type of functions that never return.
class BottomType(ExprType):
    def __str__(self):
        return 'BottomType'

class IntType(ExprType):
    def __str__(self):
        return 'int'

class TypeType(ExprType):
    def __str__(self):
        return 'Type'

class ListType(ExprType):
    def __init__(self, elem_type: ExprType):
        self.elem_type = elem_type

    def __str__(self):
        return 'List[%s]' % str(self.elem_type)

class ErrorOrVoidType(ExprType):
    def __str__(self):
        return 'ErrorOrVoid'

class FunctionType(ExprType):
    def __init__(self, argtypes: Sequence[ExprType], returns: ExprType):
        self.argtypes = tuple(argtypes)
        self.returns = returns

    def __str__(self):
        return 'Callable[[%s], %s]' % (
            ', '.join(str(arg)
                      for arg in self.argtypes),
            str(self.returns))

class ParameterPackType(ExprType):
    def __init__(self, element_type: Union[BoolType, IntType, TypeType, ErrorOrVoidType]):
        assert not isinstance(element_type, (FunctionType, ParameterPackType, BottomType))
        self.element_type = element_type

    def __str__(self):
        return 'Sequence[%s]' % (
            str(self.element_type))

class CustomTypeArgDecl(utils.ValueType):
    def __init__(self, name: str, expr_type: ExprType):
        self.name = name
        self.expr_type = expr_type

    def __str__(self):
        return '%s: %s' % (self.name, str(self.expr_type))

class CustomType(ExprType):
    def __init__(self, name: str, arg_types: Sequence[CustomTypeArgDecl]):
        self.name = name
        self.arg_types = tuple(arg_types)
        for arg in arg_types:
            assert not isinstance(arg, ParameterPackType)

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
    def __init__(self, expr_type: ExprType):
        self.expr_type = expr_type

    # Note: it's the caller's responsibility to de-duplicate VarReference objects that reference the same symbol, if
    # desired.
    def get_free_variables(self) -> 'Iterable[VarReference]': ...  # pragma: no cover

    def __str__(self) -> str: ...  # pragma: no cover

    def describe_other_fields(self) -> str: ...  # pragma: no cover

class FunctionArgDecl:
    def __init__(self, expr_type: ExprType, name: str = ''):
        self.expr_type = expr_type
        self.name = name

    def __str__(self):
        return '%s: %s' % (self.name, str(self.expr_type))

class VarReference(Expr):
    def __init__(self, expr_type: ExprType, name: str, is_global_function: bool, is_function_that_may_throw: bool):
        super().__init__(expr_type=expr_type)
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
                 type_patterns: Sequence[Expr],
                 matched_var_names: Sequence[str],
                 matched_variadic_var_names: Sequence[str],
                 expr: 'FunctionCall'):
        self.type_patterns = tuple(type_patterns)
        self.matched_var_names = tuple(matched_var_names)
        self.matched_variadic_var_names = tuple(matched_variadic_var_names)
        self.expr = expr

    def is_main_definition(self):
        matched_vars = set()
        for type_pattern in self.type_patterns:
            if isinstance(type_pattern, VarReference):
                matched_vars.add(type_pattern.name)
            else:
                return False

        return matched_vars == set(self.matched_var_names).union(self.matched_variadic_var_names)

    def write(self, writer: Writer):
        writer.writeln('TypePattern(\'%s\')' % '\', \''.join(str(type_pattern)
                                                             for type_pattern in self.type_patterns))
        with writer.indent():
            writer.writeln('lambda %s:' % ', '.join(itertools.chain(self.matched_var_names, self.matched_variadic_var_names)))
            with writer.indent():
                writer.write(str(self.expr))
                writer.writeln(',')

class MatchExpr(Expr):
    def __init__(self, matched_vars: Sequence[VarReference], match_cases: Sequence[MatchCase]):
        assert matched_vars
        assert match_cases
        for match_case in match_cases:
            assert len(match_case.type_patterns) == len(matched_vars)
        super().__init__(expr_type=match_cases[0].expr.expr_type)
        self.matched_vars = tuple(matched_vars)
        self.match_cases = tuple(match_cases)

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
            yield  # pragma: no cover

    def __str__(self):
        return repr(self.value)

    def describe_other_fields(self):
        return ''


class AtomicTypeLiteral(Expr):
    def __init__(self, cpp_type: str, expr_type: ExprType):
        assert isinstance(expr_type, (TypeType, ListType))
        super().__init__(expr_type=expr_type)
        self.cpp_type = cpp_type

    def get_free_variables(self):
        if False:
            yield  # pragma: no cover

    def __str__(self):
        return 'Type(\'%s\')' % self.cpp_type

    def describe_other_fields(self):
        return ''


class PointerTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.expr_type_expr = type_expr

    def get_free_variables(self):
        for var in self.expr_type_expr.get_free_variables():
            yield var

    def __str__(self):
        return 'Type.pointer(%s)' % str(self.expr_type_expr)

    def describe_other_fields(self):
        return self.expr_type_expr.describe_other_fields()

class ReferenceTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.expr_type_expr = type_expr

    def get_free_variables(self):
        for var in self.expr_type_expr.get_free_variables():
            yield var

    def __str__(self):
        return 'Type.reference(%s)' % str(self.expr_type_expr)

    def describe_other_fields(self):
        return self.expr_type_expr.describe_other_fields()

class RvalueReferenceTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.expr_type_expr = type_expr

    def get_free_variables(self):
        for var in self.expr_type_expr.get_free_variables():
            yield var

    def __str__(self):
        return 'Type.rvalue_reference(%s)' % str(self.expr_type_expr)

    def describe_other_fields(self):
        return self.expr_type_expr.describe_other_fields()

class ConstTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.expr_type_expr = type_expr

    def get_free_variables(self):
        for var in self.expr_type_expr.get_free_variables():
            yield var

    def __str__(self):
        return 'Type.const(%s)' % str(self.expr_type_expr)

    def describe_other_fields(self):
        return self.expr_type_expr.describe_other_fields()

class ArrayTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.expr_type_expr = type_expr

    def get_free_variables(self):
        for var in self.expr_type_expr.get_free_variables():
            yield var

    def __str__(self):
        return 'Type.array(%s)' % str(self.expr_type_expr)

    def describe_other_fields(self):
        return self.expr_type_expr.describe_other_fields()

class FunctionTypeExpr(Expr):
    def __init__(self, return_type_expr: Expr, arg_list_expr: Expr):
        assert return_type_expr.expr_type == TypeType()
        assert arg_list_expr.expr_type == ListType(TypeType()), arg_list_expr.expr_type

        super().__init__(expr_type=TypeType())
        self.return_type_expr = return_type_expr
        self.arg_list_expr = arg_list_expr

    def get_free_variables(self):
        for expr in (self.return_type_expr, self.arg_list_expr):
            for var in expr.get_free_variables():
                yield var

    def __str__(self):
        return 'Type.function(%s, %s)' % (str(self.return_type_expr),
                                          str(self.arg_list_expr))

    def describe_other_fields(self):
        return 'return_type: %s; arg_type_list: %s' % (str(self.return_type_expr.describe_other_fields()),
                                                       str(self.arg_list_expr.describe_other_fields()))

class TemplateInstantiation(Expr):
    def __init__(self,
                 template_name: str,
                 arg_exprs: Sequence[Expr],
                 instantiation_might_trigger_static_asserts: bool,
                 expr_type: ExprType = TypeType()):
        super().__init__(expr_type=expr_type)
        self.template_name = template_name
        self.arg_exprs = arg_exprs
        self.instantiation_might_trigger_static_asserts = instantiation_might_trigger_static_asserts

    def get_free_variables(self):
        for arg_expr in self.arg_exprs:
            for var in arg_expr.get_free_variables():
                yield var

    def __str__(self):
        return 'Type.template_instantiation(\'%s\', [%s])' % (self.template_name, ', '.join(str(arg_expr)
                                                                                            for arg_expr in self.arg_exprs))

    def describe_other_fields(self):
        return '[%s]' % '; '.join(arg_expr.describe_other_fields()
                                  for arg_expr in self.arg_exprs)

class ParameterPackExpansion(Expr):
    def __init__(self, expr: VarReference):
        assert isinstance(expr.expr_type, ParameterPackType)
        super().__init__(expr.expr_type.element_type)
        self.expr = expr

    def get_free_variables(self):
        for var in self.expr.get_free_variables():
            yield var

    def __str__(self):
        return '*(%s)' % str(self.expr)

    def describe_other_fields(self):
        return self.expr.describe_other_fields()

class TemplateInstantiationWithList(Expr):
    def __init__(self,
                 template_name: str,
                 arg_list_expr: Expr,
                 instantiation_might_trigger_static_asserts: bool):
        assert isinstance(arg_list_expr.expr_type, ListType), arg_list_expr.expr_type

        super().__init__(expr_type=TypeType())
        self.template_name = template_name
        self.arg_list_expr = arg_list_expr
        self.instantiation_might_trigger_static_asserts = instantiation_might_trigger_static_asserts

    def get_free_variables(self):
        for var in self.arg_list_expr.get_free_variables():
            yield var

    def __str__(self):
        return 'Type.template_instantiation(\'%s\', %s)' % (self.template_name, str(self.arg_list_expr))

    def describe_other_fields(self):
        return self.arg_list_expr.describe_other_fields()

class ClassMemberAccess(Expr):
    def __init__(self, class_type_expr: Expr, member_name: str, member_type: ExprType):
        super().__init__(expr_type=member_type)
        self.class_type_expr = class_type_expr
        self.member_name = member_name
        self.member_type = member_type

    def get_free_variables(self):
        for var in self.class_type_expr.get_free_variables():
            yield var

    def __str__(self):
        return '%s::%s' % (self.class_type_expr, self.member_name)

    def describe_other_fields(self):
        return self.class_type_expr.describe_other_fields()

class TemplateMemberAccess(Expr):
    def __init__(self, class_type_expr: VarReference, member_name: str, arg_list_expr: VarReference):
        assert isinstance(arg_list_expr.expr_type, ListType)

        super().__init__(expr_type=TypeType())
        self.class_type_expr = class_type_expr
        self.member_name = member_name
        self.arg_list_expr = arg_list_expr

    def get_free_variables(self):
        for var in self.class_type_expr.get_free_variables():
            yield var

    def __str__(self):
        return 'Type.template_member(%s, \'%s\', %s)' % (str(self.class_type_expr),
                                                         self.member_name,
                                                         str(self.arg_list_expr))

    def describe_other_fields(self):
        return self.class_type_expr.describe_other_fields()

class FunctionCall(Expr):
    def __init__(self, fun: VarReference, args: Sequence[VarReference]):
        assert isinstance(fun.expr_type, FunctionType)
        assert len(fun.expr_type.argtypes) == len(args)
        assert args
        super().__init__(expr_type=fun.expr_type.returns)
        self.fun = fun
        self.args = tuple(args)

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
        super().__init__(expr_type=BoolType())
        assert (lhs.expr_type == ErrorOrVoidType() and rhs.expr_type == TypeType()) or (lhs.expr_type == rhs.expr_type), '%s vs %s' % (str(lhs.expr_type), str(rhs.expr_type))
        assert not isinstance(lhs.expr_type, FunctionType)
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

class SetEqualityComparison(Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference, elem_type: ExprType):
        super().__init__(expr_type=BoolType())
        assert isinstance(lhs.expr_type, ListType)
        assert isinstance(rhs.expr_type, ListType)
        self.lhs = lhs
        self.rhs = rhs
        self.elem_type = elem_type

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

    def __str__(self):
        return 'set_equals(%s, %s, %s)' % (self.lhs.name, self.rhs.name, str(self.elem_type))

    def describe_other_fields(self):
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class IsInListExpr(Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference):
        super().__init__(expr_type=BoolType())
        assert isinstance(rhs.expr_type, ListType)
        assert lhs.expr_type == rhs.expr_type.elem_type
        self.lhs = lhs
        self.rhs = rhs

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

    def __str__(self):
        return '%s in %s' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self):
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class ListToSetExpr(Expr):
    def __init__(self, var: VarReference, elem_type: ExprType):
        assert isinstance(var.expr_type, ListType)
        super().__init__(expr_type=var.expr_type)
        self.elem_type = elem_type
        self.var = var

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

    def __str__(self):
        return 'list_to_set(%s)' % self.var.name

    def describe_other_fields(self):
        return self.var.describe_other_fields()

class AttributeAccessExpr(Expr):
    def __init__(self, var: VarReference, attribute_name: str, expr_type: ExprType):
        super().__init__(expr_type=expr_type)
        assert isinstance(var.expr_type, (TypeType, CustomType))
        self.var = var
        self.attribute_name = attribute_name
        self.expr_type = expr_type

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

    def __str__(self):
        return '%s.%s' % (self.var.name, self.attribute_name)

    def describe_other_fields(self):
        return ''

class IntLiteral(Expr):
    def __init__(self, value: int):
        super().__init__(expr_type=IntType())
        self.value = value

    def get_free_variables(self):
        if False:
            yield  # pragma: no cover

    def __str__(self):
        return str(self.value)

    def describe_other_fields(self):
        return ''

class NotExpr(Expr):
    def __init__(self, var: VarReference):
        assert var.expr_type == BoolType()
        super().__init__(expr_type=BoolType())
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
        assert var.expr_type == IntType()
        super().__init__(expr_type=IntType())
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
        assert lhs.expr_type == IntType()
        assert rhs.expr_type == IntType()
        assert op in ('<', '>', '<=', '>=')
        super().__init__(expr_type=BoolType())
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
        assert lhs.expr_type == IntType()
        assert rhs.expr_type == IntType()
        assert op in ('+', '-', '*', '//', '%')
        super().__init__(expr_type=IntType())
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

class IsInstanceExpr(Expr):
    def __init__(self, var: VarReference, checked_type: CustomType):
        super().__init__(expr_type=BoolType())
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
    def __init__(self, var: VarReference, expr_type: ExprType):
        assert isinstance(var.expr_type, ErrorOrVoidType)
        assert isinstance(expr_type, CustomType)
        super().__init__(expr_type=expr_type)
        self.var = var

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

    def __str__(self):
        return '%s  # type: %s' % (self.var.name, str(self.expr_type))

    def describe_other_fields(self):
        return ''

class ListComprehensionExpr(Expr):
    def __init__(self, list_var: VarReference, loop_var: VarReference, result_elem_expr: FunctionCall):
        assert isinstance(list_var.expr_type, ListType), list_var.expr_type
        super().__init__(expr_type=ListType(result_elem_expr.expr_type))
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

class AddToSetExpr(Expr):
    def __init__(self, set_expr: VarReference, elem_expr: VarReference):
        assert isinstance(set_expr.expr_type, ListType), set_expr.expr_type
        super().__init__(expr_type=set_expr.expr_type)
        self.set_expr = set_expr
        self.elem_expr = elem_expr

    def get_free_variables(self):
        for expr in (self.set_expr, self.elem_expr):
            for var in expr.get_free_variables():
                yield var

    def __str__(self):
        return 'add_to_set(%s, %s)' % (
            str(self.set_expr),
            str(self.elem_expr))

    def describe_other_fields(self):
        return 'set: %s; elem: %s' % (self.set_expr.describe_other_fields(), self.elem_expr.describe_other_fields())

class ReturnTypeInfo:
    def __init__(self, expr_type: Optional[ExprType], always_returns: bool):
        # When expr_type is None, the statement never returns.
        # expr_type can't be None if always_returns is True.
        self.expr_type = expr_type
        self.always_returns = always_returns

class Stmt:
    # Note: it's the caller's responsibility to de-duplicate VarReference objects that reference the same symbol, if
    # desired.
    def get_free_variables(self) -> 'Iterable[VarReference]': ...  # pragma: no cover

    def write(self, writer: Writer, verbose: bool): ...  # pragma: no cover

class Assert(Stmt):
    def __init__(self, var: VarReference, message: str):
        assert isinstance(var.expr_type, BoolType)
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
        assert lhs.expr_type == rhs.expr_type, 'Different types: %s vs %s. RHS class: %s' % (str(lhs.expr_type), str(rhs.expr_type), rhs.__class__.__name__)
        if lhs2:
            assert isinstance(lhs2.expr_type, ErrorOrVoidType)
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

class UnpackingAssignment(Stmt):
    def __init__(self,
                 lhs_list: Sequence[VarReference],
                 rhs: VarReference,
                 error_message: str):
        assert isinstance(rhs.expr_type, ListType)
        assert lhs_list
        for lhs in lhs_list:
            assert lhs.expr_type == rhs.expr_type.elem_type
        self.lhs_list = tuple(lhs_list)
        self.rhs = rhs
        self.error_message = error_message

    def get_free_variables(self):
        for var in self.rhs.get_free_variables():
            yield var

    def write(self, writer: Writer, verbose: bool):
        writer.write('[')
        writer.write(', '.join(var.name
                               for var in self.lhs_list))
        writer.write('] = ')
        writer.write(self.rhs.name)
        if verbose:
            writer.writeln('  # lhs: [%s]; rhs: %s' % (
                ', '.join(lhs_var.describe_other_fields()
                          for lhs_var in self.lhs_list),
                self.rhs.describe_other_fields()))
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
    def __init__(self, cond: VarReference, if_stmts: Sequence[Stmt], else_stmts: Sequence[Stmt]):
        assert cond.expr_type == BoolType()
        self.cond = cond
        self.if_stmts = tuple(if_stmts)
        self.else_stmts = tuple(else_stmts)

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
                 description: str,
                 args: Sequence[FunctionArgDecl],
                 body: Sequence[Stmt],
                 return_type: ExprType):
        assert body
        self.name = name
        self.description = description
        self.args = tuple(args)
        self.body = tuple(body)
        self.return_type = return_type

    def write(self, writer: Writer, verbose: bool):
        if self.description:
            writer.write('# ')
            writer.writeln(self.description)
        writer.writeln('def %s(%s) -> %s:' % (
            self.name,
            ', '.join(str(arg) for arg in self.args),
            str(self.return_type)))
        with writer.indent():
            for stmt in self.body:
                stmt.write(writer, verbose)
        writer.writeln('')

class CheckIfErrorDefn:
    def __init__(self, error_types_and_messages: Sequence[Tuple[CustomType, str]]):
        self.error_types_and_messages = tuple(error_types_and_messages)

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

class CheckIfErrorStmt(Stmt):
    def __init__(self, expr: VarReference):
        self.expr = expr

    def get_free_variables(self):
        for var in self.expr.get_free_variables():
            yield var

    def write(self, writer: Writer, verbose: bool):
        writer.write('check_if_error(')
        writer.write(str(self.expr))
        if verbose:
            writer.write(')  # ')
            writer.writeln(self.expr.describe_other_fields())
        else:
            writer.writeln(')')

class Module:
    def __init__(self,
                 body: Sequence[Union[FunctionDefn, Assignment, Assert, CustomType, CheckIfErrorDefn]],
                 public_names: Set[str]):
        self.body = tuple(body)
        self.public_names = public_names

    def __str__(self):
        writer = Writer()
        for elem in self.body:
            elem.write(writer, verbose=False)
        return ''.join(writer.strings)

def get_free_variables_in_stmts(stmts: Sequence[Stmt]):
    local_var_names = set()
    for stmt in stmts:
        for var in stmt.get_free_variables():
            if var.name not in local_var_names:
                yield var
        if isinstance(stmt, Assignment):
            local_var_names.add(stmt.lhs.name)
            if stmt.lhs2:
                local_var_names.add(stmt.lhs2.name)

def get_unique_free_variables_in_stmts(stmts: Sequence[Stmt]) -> Sequence[VarReference]:
    var_by_name = dict()
    for var in get_free_variables_in_stmts(stmts):
        if var.name not in var_by_name:
            var_by_name[var.name] = var
    return list(sorted(var_by_name.values(),
                       key=lambda var: var.name))
