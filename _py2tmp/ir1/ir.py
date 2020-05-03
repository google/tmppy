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

from typing import List, Optional, Union, Tuple, Set, Generator
from contextlib import contextmanager

import itertools

from _py2tmp.utils import ValueType


class Writer:
    def __init__(self) -> None:
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
    def indent(self) -> Generator[None, None, None]:
        old_indent = self.current_indent
        self.current_indent = self.current_indent + '  '
        yield
        self.current_indent = old_indent

class _ExprType(ValueType):
    def __str__(self) -> str: ...  # pragma: no cover

class BoolType(_ExprType):
    def __str__(self) -> str:
        return 'bool'

# A type with no values. This is the return type of functions that never return.
class BottomType(_ExprType):
    def __str__(self) -> str:
        return 'BottomType'

class IntType(_ExprType):
    def __str__(self) -> str:
        return 'int'

class TypeType(_ExprType):
    def __str__(self) -> str:
        return 'Type'

class ErrorOrVoidType(_ExprType):
    def __str__(self) -> str:
        return 'ErrorOrVoid'

class FunctionType(_ExprType):
    def __init__(self, argtypes: List['ExprType'], returns: 'ExprType'):
        self.argtypes = argtypes
        self.returns = returns

    def __str__(self) -> str:
        return 'Callable[[%s], %s]' % (
            ', '.join(str(arg)
                      for arg in self.argtypes),
            str(self.returns))

class ListType(_ExprType):
    def __init__(self, elem_type: 'ExprType'):
        assert not isinstance(elem_type, FunctionType)
        self.elem_type = elem_type

    def __str__(self) -> str:
        return 'List[%s]' % str(self.elem_type)

class ParameterPackType(_ExprType):
    def __init__(self, element_type: Union[BoolType, IntType, TypeType, ErrorOrVoidType]):
        assert not isinstance(element_type, (FunctionType, ParameterPackType, BottomType))
        self.element_type = element_type

    def __str__(self) -> str:
        return 'Sequence[%s]' % (
            str(self.element_type))

class CustomTypeArgDecl(ValueType):
    def __init__(self, name: str, expr_type: 'ExprType'):
        self.name = name
        self.expr_type = expr_type

    def __str__(self) -> str:
        return '%s: %s' % (self.name, str(self.expr_type))

class CustomType(_ExprType):
    def __init__(self, name: str, arg_types: List[CustomTypeArgDecl]):
        self.name = name
        self.arg_types = arg_types

    def __str__(self) -> str:
        return self.name

    def write(self, writer: Writer, verbose: bool):
        writer.writeln('class %s:' % self.name)
        with writer.indent():
            writer.writeln('def __init__(%s):' % ', '.join(str(arg)
                                                           for arg in self.arg_types))
            with writer.indent():
                for arg in self.arg_types:
                    writer.writeln('self.%s = %s' % (arg.name, arg.name))

ExprType = Union[BoolType, BottomType, CustomType, ErrorOrVoidType, FunctionType, IntType, ListType, ParameterPackType, TypeType]

class _Expr:
    def __init__(self, expr_type: ExprType):
        self.expr_type = expr_type

    def __str__(self) -> str: ...  # pragma: no cover

    def describe_other_fields(self) -> str: ...  # pragma: no cover

class PatternExpr:
    def __init__(self, expr_type: ExprType):
        self.expr_type = expr_type

    def __str__(self) -> str: ...  # pragma: no cover

    def describe_other_fields(self) -> str: ...  # pragma: no cover


Expr = Union[_Expr, PatternExpr]


class FunctionArgDecl:
    def __init__(self, expr_type: ExprType, name: str = ''):
        self.expr_type = expr_type
        self.name = name

    def __str__(self) -> str:
        return '%s: %s' % (self.name, str(self.expr_type))

class VarReference(_Expr):
    def __init__(self, expr_type: ExprType, name: str, is_global_function: bool, is_function_that_may_throw: bool):
        super().__init__(expr_type=expr_type)
        assert name
        self.name = name
        self.is_global_function = is_global_function
        self.is_function_that_may_throw = is_function_that_may_throw

    def __str__(self) -> str:
        return self.name

    def describe_other_fields(self) -> str:
        return 'is_global_function=%s, is_function_that_may_throw=%s' % (
            self.is_global_function,
            self.is_function_that_may_throw)

class VarReferencePattern(PatternExpr):
    def __init__(self, expr_type: ExprType, name: str, is_global_function: bool, is_function_that_may_throw: bool):
        super().__init__(expr_type=expr_type)
        assert name
        self.name = name
        self.is_global_function = is_global_function
        self.is_function_that_may_throw = is_function_that_may_throw

    def __str__(self) -> str:
        return self.name

    def describe_other_fields(self) -> str:
        return 'is_global_function=%s, is_function_that_may_throw=%s' % (
            self.is_global_function,
            self.is_function_that_may_throw)

class MatchCase:
    def __init__(self,
                 type_patterns: List[PatternExpr],
                 matched_var_names: List[str],
                 matched_variadic_var_names: List[str],
                 expr: 'FunctionCall'):
        self.type_patterns = type_patterns
        self.matched_var_names = matched_var_names
        self.matched_variadic_var_names = matched_variadic_var_names
        self.expr = expr

    def is_main_definition(self) -> bool:
        return set(self.type_patterns) == set(self.matched_var_names).union(self.matched_variadic_var_names)

    def write(self, writer: Writer):
        writer.writeln('lambda %s:' % ', '.join(itertools.chain(self.matched_var_names, self.matched_variadic_var_names)))
        with writer.indent():
            writer.write('\', \''.join(str(type_pattern)
                                       for type_pattern in self.type_patterns))
            writer.writeln(':')
            with writer.indent():
                writer.write(str(self.expr))
                writer.writeln(',')

class MatchExpr(_Expr):
    def __init__(self, matched_vars: List[VarReference], match_cases: List[MatchCase]):
        assert matched_vars
        assert match_cases
        for match_case in match_cases:
            assert len(match_case.type_patterns) == len(matched_vars)
        super().__init__(expr_type=match_cases[0].expr.expr_type)
        self.matched_vars = matched_vars
        self.match_cases = match_cases

        assert len([match_case
                    for match_case in match_cases
                    if match_case.is_main_definition()]) <= 1

    def write(self, writer: Writer):
        writer.writeln('match(%s)({' % ', '.join(var.name
                                                 for var in self.matched_vars))
        with writer.indent():
            for case in self.match_cases:
                case.write(writer)
        writer.writeln('})')

    def describe_other_fields(self) -> str:
        return ''

class BoolLiteral(_Expr):
    def __init__(self, value: bool):
        super().__init__(BoolType())
        self.value = value

    def __str__(self) -> str:
        return repr(self.value)

    def describe_other_fields(self) -> str:
        return ''

class AtomicTypeLiteral(_Expr):
    def __init__(self, cpp_type: str):
        super().__init__(expr_type=TypeType())
        self.cpp_type = cpp_type

    def __str__(self) -> str:
        return 'Type(\'%s\')' % self.cpp_type

    def describe_other_fields(self) -> str:
        return ''

class AtomicTypeLiteralPattern(PatternExpr):
    def __init__(self, cpp_type: str):
        super().__init__(expr_type=TypeType())
        self.cpp_type = cpp_type

    def __str__(self) -> str:
        return 'Type(\'%s\')' % self.cpp_type

    def describe_other_fields(self) -> str:
        return ''

class PointerTypeExpr(_Expr):
    def __init__(self, type_expr: VarReference):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

    def __str__(self) -> str:
        return 'Type.pointer(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

class PointerTypePatternExpr(PatternExpr):
    def __init__(self, type_expr: PatternExpr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

    def __str__(self) -> str:
        return 'Type.pointer(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

class ReferenceTypeExpr(_Expr):
    def __init__(self, type_expr: VarReference):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

    def __str__(self) -> str:
        return 'Type.reference(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

class ReferenceTypePatternExpr(PatternExpr):
    def __init__(self, type_expr: PatternExpr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

    def __str__(self) -> str:
        return 'Type.reference(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

class RvalueReferenceTypeExpr(_Expr):
    def __init__(self, type_expr: VarReference):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

    def __str__(self) -> str:
        return 'Type.rvalue_reference(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

class RvalueReferenceTypePatternExpr(PatternExpr):
    def __init__(self, type_expr: PatternExpr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

    def __str__(self) -> str:
        return 'Type.rvalue_reference(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

class ConstTypeExpr(_Expr):
    def __init__(self, type_expr: VarReference):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

    def __str__(self) -> str:
        return 'Type.const(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

class ConstTypePatternExpr(PatternExpr):
    def __init__(self, type_expr: PatternExpr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

    def __str__(self) -> str:
        return 'Type.const(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

class ArrayTypeExpr(_Expr):
    def __init__(self, type_expr: VarReference):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

    def __str__(self) -> str:
        return 'Type.array(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

class ArrayTypePatternExpr(PatternExpr):
    def __init__(self, type_expr: PatternExpr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

    def __str__(self) -> str:
        return 'Type.array(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

class FunctionTypeExpr(_Expr):
    def __init__(self, return_type_expr: VarReference, arg_list_expr: VarReference):
        assert return_type_expr.expr_type == TypeType()
        assert arg_list_expr.expr_type == ListType(TypeType())

        super().__init__(expr_type=TypeType())
        self.return_type_expr = return_type_expr
        self.arg_list_expr = arg_list_expr

    def __str__(self) -> str:
        return 'Type.function(%s, %s)' % (str(self.return_type_expr), str(self.arg_list_expr))

    def describe_other_fields(self) -> str:
        return 'return_type: %s; arg_type_list: %s' % (str(self.return_type_expr.describe_other_fields()),
                                                       str(self.arg_list_expr.describe_other_fields()))

class FunctionTypePatternExpr(PatternExpr):
    def __init__(self, return_type_expr: PatternExpr, arg_list_expr: PatternExpr):
        assert return_type_expr.expr_type == TypeType()
        assert arg_list_expr.expr_type == ListType(TypeType())

        super().__init__(expr_type=TypeType())
        self.return_type_expr = return_type_expr
        self.arg_list_expr = arg_list_expr

    def __str__(self) -> str:
        return 'Type.function(%s, %s)' % (str(self.return_type_expr), str(self.arg_list_expr))

    def describe_other_fields(self) -> str:
        return 'return_type: %s; arg_type_list: %s' % (str(self.return_type_expr.describe_other_fields()),
                                                       str(self.arg_list_expr.describe_other_fields()))

class ParameterPackExpansion(_Expr):
    def __init__(self, expr: VarReference):
        assert isinstance(expr.expr_type, ParameterPackType)
        super().__init__(expr.expr_type.element_type)
        self.expr = expr

    def __str__(self) -> str:
        return '*(%s)' % str(self.expr)

    def describe_other_fields(self) -> str:
        return self.expr.describe_other_fields()

# E.g. TemplateInstantiationExpr('std::vector', [AtomicTypeLiteral('int')]) is the type 'std::vector<int>'.
class TemplateInstantiationExpr(_Expr):
    def __init__(self, template_atomic_cpp_type: str, arg_list_expr: VarReference):
        assert arg_list_expr.expr_type == ListType(TypeType())

        super().__init__(expr_type=TypeType())
        self.template_atomic_cpp_type = template_atomic_cpp_type
        self.arg_list_expr = arg_list_expr

    def __str__(self) -> str:
        return 'Type.template_instantiation(\'%s\', %s)' % (self.template_atomic_cpp_type, str(self.arg_list_expr))

    def describe_other_fields(self) -> str:
        return self.arg_list_expr.describe_other_fields()

# E.g. TemplateInstantiationExpr('std::vector', [AtomicTypeLiteral('int')]) is the type 'std::vector<int>'.
class TemplateInstantiationPatternExpr(PatternExpr):
    def __init__(self, template_atomic_cpp_type: str, arg_exprs: List[PatternExpr], list_extraction_arg_expr: Optional[VarReferencePattern]):
        for arg in arg_exprs:
            assert arg.expr_type == TypeType()
        if list_extraction_arg_expr:
            assert list_extraction_arg_expr.expr_type == ListType(TypeType())

        super().__init__(expr_type=TypeType())
        self.template_atomic_cpp_type = template_atomic_cpp_type
        self.arg_exprs = arg_exprs
        self.list_extraction_arg_expr = list_extraction_arg_expr

    def __str__(self) -> str:
        return 'Type.template_instantiation(\'%s\', [%s%s])' % (self.template_atomic_cpp_type,
                                                                ', '.join(str(arg_expr) for arg_expr in self.arg_exprs),
                                                                ', *' + str(self.list_extraction_arg_expr) if self.list_extraction_arg_expr else '')

    def describe_other_fields(self) -> str:
        return '; '.join(arg_expr.describe_other_fields()
                         for arg_expr in itertools.chain(self.arg_exprs,
                                                         (self.list_extraction_arg_expr,) if self.list_extraction_arg_expr else tuple()))

# E.g. TemplateMemberAccessExpr(AtomicTypeLiteral('foo'), 'bar', [AtomicTypeLiteral('int')]) is the type 'foo::bar<int>'.
class TemplateMemberAccessExpr(_Expr):
    def __init__(self, class_type_expr: VarReference, member_name: str, arg_list_expr: VarReference):
        assert class_type_expr.expr_type == TypeType()
        assert arg_list_expr.expr_type == ListType(TypeType())

        super().__init__(expr_type=TypeType())
        self.class_type_expr = class_type_expr
        self.member_name = member_name
        self.arg_list_expr = arg_list_expr

    def __str__(self) -> str:
        return 'Type.template_member(%s, \'%s\', %s)' % (str(self.class_type_expr),
                                                         self.member_name,
                                                         str(self.arg_list_expr))

    def describe_other_fields(self) -> str:
        return 'class_type: %s; arg_type_list: %s' % (str(self.class_type_expr.describe_other_fields()),
                                                      str(self.arg_list_expr.describe_other_fields()))

class ListExpr(_Expr):
    def __init__(self, elem_type: ExprType, elems: List[VarReference]):
        assert not isinstance(elem_type, FunctionType)
        super().__init__(expr_type=ListType(elem_type))
        self.elem_type = elem_type
        self.elems = elems

    def __str__(self) -> str:
        return '[%s]' % ', '.join(var.name
                                  for var in self.elems)

    def describe_other_fields(self) -> str:
        return ''

class ListPatternExpr(PatternExpr):
    def __init__(self, elem_type: ExprType, elems: List[PatternExpr], list_extraction_expr: Optional[VarReference]):
        assert not isinstance(elem_type, FunctionType)
        super().__init__(expr_type=ListType(elem_type))
        self.elem_type = elem_type
        self.elems = elems
        self.list_extraction_expr = list_extraction_expr

    def __str__(self) -> str:
        return '[%s]' % ', '.join(str(elem)
                                  for elem in self.elems)

    def describe_other_fields(self) -> str:
        return '[%s]' % '; '.join(elem.describe_other_fields()
                                  for elem in self.elems)

class AddToSetExpr(_Expr):
    def __init__(self, set_expr: VarReference, elem_expr: VarReference):
        assert isinstance(set_expr.expr_type, ListType)
        assert set_expr.expr_type.elem_type == elem_expr.expr_type
        super().__init__(expr_type=ListType(set_expr.expr_type.elem_type))
        self.set_expr = set_expr
        self.elem_expr = elem_expr

    def __str__(self) -> str:
        return 'add_to_set(%s, %s)' % (
            str(self.set_expr),
            str(self.elem_expr))

    def describe_other_fields(self) -> str:
        return 'set: %s; elem: %s' % (self.set_expr.describe_other_fields(), self.elem_expr.describe_other_fields())

class SetToListExpr(_Expr):
    def __init__(self, var: VarReference):
        assert isinstance(var.expr_type, ListType)
        super().__init__(expr_type=ListType(elem_type=var.expr_type.elem_type))
        self.var = var

    def __str__(self) -> str:
        return 'set_to_list(%s)' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

class ListToSetExpr(_Expr):
    def __init__(self, var: VarReference):
        assert isinstance(var.expr_type, ListType)
        super().__init__(expr_type=ListType(elem_type=var.expr_type.elem_type))
        self.var = var

    def __str__(self) -> str:
        return 'list_to_set(%s)' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

class FunctionCall(_Expr):
    def __init__(self, fun: VarReference, args: List[VarReference]):
        assert isinstance(fun.expr_type, FunctionType)
        assert len(fun.expr_type.argtypes) == len(args)
        assert args
        super().__init__(expr_type=fun.expr_type.returns)
        self.fun = fun
        self.args = args

    def __str__(self) -> str:
        return '%s(%s)' % (
            self.fun.name,
            ', '.join(var.name
                      for var in self.args))

    def describe_other_fields(self) -> str:
        return '; '.join('%s: %s' % (var.name, var.describe_other_fields())
                         for vars in ([self.fun], self.args)
                         for var in vars)

class EqualityComparison(_Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference):
        super().__init__(expr_type=BoolType())
        assert (lhs.expr_type == ErrorOrVoidType() and rhs.expr_type == TypeType()) or (lhs.expr_type == rhs.expr_type), '%s (%s) vs %s (%s)' % (
            str(lhs.expr_type), lhs.expr_type.__dict__, str(rhs.expr_type), rhs.expr_type.__dict__)
        assert not isinstance(lhs.expr_type, FunctionType)
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self) -> str:
        return '%s == %s' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class SetEqualityComparison(_Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference):
        super().__init__(expr_type=BoolType())
        assert isinstance(lhs.expr_type, ListType)
        assert lhs.expr_type == rhs.expr_type
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self) -> str:
        return 'set_equals(%s, %s)' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class IsInListExpr(_Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference):
        super().__init__(expr_type=BoolType())
        assert isinstance(rhs.expr_type, ListType)
        assert lhs.expr_type == rhs.expr_type.elem_type
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self) -> str:
        return '%s in %s' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class AttributeAccessExpr(_Expr):
    def __init__(self, var: VarReference, attribute_name: str, expr_type: ExprType):
        super().__init__(expr_type=expr_type)
        assert isinstance(var.expr_type, (TypeType, CustomType))
        self.var = var
        self.attribute_name = attribute_name
        self.expr_type = expr_type

    def __str__(self) -> str:
        return '%s.%s' % (self.var.name, self.attribute_name)

    def describe_other_fields(self) -> str:
        return ''

class IntLiteral(_Expr):
    def __init__(self, value: int):
        super().__init__(expr_type=IntType())
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    def describe_other_fields(self) -> str:
        return ''

class NotExpr(_Expr):
    def __init__(self, var: VarReference):
        assert var.expr_type == BoolType()
        super().__init__(expr_type=BoolType())
        self.var = var

    def __str__(self) -> str:
        return 'not %s' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

class UnaryMinusExpr(_Expr):
    def __init__(self, var: VarReference):
        assert var.expr_type == IntType()
        super().__init__(expr_type=IntType())
        self.var = var

    def __str__(self) -> str:
        return '-%s' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

class IntListSumExpr(_Expr):
    def __init__(self, var: VarReference):
        assert isinstance(var.expr_type, ListType)
        assert isinstance(var.expr_type.elem_type, IntType)
        super().__init__(expr_type=IntType())
        self.var = var

    def __str__(self) -> str:
        return 'sum(%s)' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

class BoolListAllExpr(_Expr):
    def __init__(self, var: VarReference):
        assert isinstance(var.expr_type, ListType)
        assert isinstance(var.expr_type.elem_type, BoolType)
        super().__init__(expr_type=BoolType())
        self.var = var

    def __str__(self) -> str:
        return 'all(%s)' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

class BoolListAnyExpr(_Expr):
    def __init__(self, var: VarReference):
        assert isinstance(var.expr_type, ListType)
        assert isinstance(var.expr_type.elem_type, BoolType)
        super().__init__(expr_type=BoolType())
        self.var = var

    def __str__(self) -> str:
        return 'any(%s)' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

class IntComparisonExpr(_Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference, op: str):
        assert lhs.expr_type == IntType()
        assert rhs.expr_type == IntType()
        assert op in ('<', '>', '<=', '>=')
        super().__init__(expr_type=BoolType())
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

    def __str__(self) -> str:
        return '%s %s %s' % (self.lhs.name, self.op, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class IntBinaryOpExpr(_Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference, op: str):
        assert lhs.expr_type == IntType()
        assert rhs.expr_type == IntType()
        assert op in ('+', '-', '*', '//', '%')
        super().__init__(expr_type=IntType())
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

    def __str__(self) -> str:
        return '%s %s %s' % (self.lhs.name, self.op, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class ListConcatExpr(_Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference):
        assert isinstance(lhs.expr_type, ListType)
        assert lhs.expr_type == rhs.expr_type
        super().__init__(expr_type=lhs.expr_type)
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self) -> str:
        return '%s + %s' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

class IsInstanceExpr(_Expr):
    def __init__(self, var: VarReference, checked_type: CustomType):
        super().__init__(expr_type=BoolType())
        self.var = var
        self.checked_type = checked_type

    def __str__(self) -> str:
        return 'isinstance(%s, %s)' % (self.var.name, str(self.checked_type))

    def describe_other_fields(self) -> str:
        return ''

class SafeUncheckedCast(_Expr):
    def __init__(self, var: VarReference, expr_type: ExprType):
        assert isinstance(var.expr_type, ErrorOrVoidType)
        assert isinstance(expr_type, CustomType)
        super().__init__(expr_type=expr_type)
        self.var = var

    def __str__(self) -> str:
        return '%s  # type: %s' % (self.var.name, str(self.expr_type))

    def describe_other_fields(self) -> str:
        return ''

class ListComprehensionExpr(_Expr):
    def __init__(self, list_var: VarReference, loop_var: VarReference, result_elem_expr: FunctionCall):
        assert isinstance(list_var.expr_type, ListType)
        assert list_var.expr_type.elem_type == loop_var.expr_type
        super().__init__(expr_type=ListType(result_elem_expr.expr_type))
        self.list_var = list_var
        self.loop_var = loop_var
        self.result_elem_expr = result_elem_expr

    def __str__(self) -> str:
        return '[%s for %s in %s]' % (str(self.result_elem_expr), self.loop_var.name, self.list_var.name)

    def describe_other_fields(self) -> str:
        return ''

class ReturnTypeInfo:
    def __init__(self, expr_type: Optional[ExprType], always_returns: bool):
        # When expr_type is None, the statement never returns.
        # expr_type can't be None if always_returns is True.
        self.expr_type = expr_type
        self.always_returns = always_returns

class Stmt:
    def write(self, writer: Writer, verbose: bool): ...  # pragma: no cover

class Assert(Stmt):
    def __init__(self, var: VarReference, message: str):
        assert isinstance(var.expr_type, BoolType)
        self.var = var
        self.message = message

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
        assert lhs.expr_type == rhs.expr_type, '%s vs %s' % (str(lhs.expr_type), str(rhs.expr_type))
        if lhs2:
            assert isinstance(lhs2.expr_type, ErrorOrVoidType)
            assert isinstance(rhs, (MatchExpr, FunctionCall, ListComprehensionExpr))
        self.lhs = lhs
        self.lhs2 = lhs2
        self.rhs = rhs

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

class CheckIfError(Stmt):
    def __init__(self,
                 var: VarReference):
        assert var.expr_type == ErrorOrVoidType()
        self.var = var

    def write(self, writer: Writer, verbose: bool):
        writer.write('check_if_error(')
        writer.write(str(self.var))
        if verbose:
            writer.write(')  # ')
            writer.writeln(self.var.describe_other_fields())
        else:
            writer.writeln(')')

class UnpackingAssignment(Stmt):
    def __init__(self,
                 lhs_list: List[VarReference],
                 rhs: VarReference,
                 error_message: str):
        assert isinstance(rhs.expr_type, ListType)
        assert lhs_list
        for lhs in lhs_list:
            assert lhs.expr_type == rhs.expr_type.elem_type
        self.lhs_list = lhs_list
        self.rhs = rhs
        self.error_message = error_message

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
        assert cond.expr_type == BoolType()
        self.cond = cond
        self.if_stmts = if_stmts
        self.else_stmts = else_stmts

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
                 args: List[FunctionArgDecl],
                 body: List[Stmt],
                 return_type: ExprType):
        assert body
        self.name = name
        self.description = description
        self.args = args
        self.body = body
        self.return_type = return_type

    def write(self, writer: Writer, verbose: bool):
        if self.description:
            writer.write('# ')
            writer.writeln(self.description)
        writer.writeln('def %s(%s) -> %s:' % (
            self.name,
            ', '.join('%s: %s' % (arg.name, str(arg.expr_type))
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
    def __init__(self,
                 body: List[Union[FunctionDefn, Assignment, Assert, CustomType, CheckIfErrorDefn]],
                 public_names: Set[str]):
        self.body = body
        self.public_names = public_names

    def __str__(self) -> str:
        writer = Writer()
        for elem in self.body:
            elem.write(writer, verbose=False)
        return ''.join(writer.strings)
