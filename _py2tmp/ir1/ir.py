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

from typing import Optional, Union, Tuple, FrozenSet, Generator
from contextlib import contextmanager

import itertools
from dataclasses import dataclass, field

from _py2tmp.coverage import SourceBranch


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

@dataclass(frozen=True)
class _ExprType:
    def __str__(self) -> str: ...  # pragma: no cover

@dataclass(frozen=True)
class BoolType(_ExprType):
    def __str__(self) -> str:
        return 'bool'

# A type with no values. This is the return type of functions that never return.
@dataclass(frozen=True)
class BottomType(_ExprType):
    def __str__(self) -> str:
        return 'BottomType'

@dataclass(frozen=True)
class IntType(_ExprType):
    def __str__(self) -> str:
        return 'int'

@dataclass(frozen=True)
class TypeType(_ExprType):
    def __str__(self) -> str:
        return 'Type'

@dataclass(frozen=True)
class ErrorOrVoidType(_ExprType):
    def __str__(self) -> str:
        return 'ErrorOrVoid'

@dataclass(frozen=True)
class FunctionType(_ExprType):
    argtypes: Tuple['ExprType', ...]
    returns: 'ExprType'

    def __str__(self) -> str:
        return 'Callable[[%s], %s]' % (
            ', '.join(str(arg)
                      for arg in self.argtypes),
            str(self.returns))

@dataclass(frozen=True)
class ListType(_ExprType):
    elem_type: 'ExprType'

    def __post_init__(self) -> None:
        assert not isinstance(self.elem_type, FunctionType)

    def __str__(self) -> str:
        return 'List[%s]' % str(self.elem_type)

@dataclass(frozen=True)
class ParameterPackType(_ExprType):
    element_type: Union[BoolType, IntType, TypeType, ErrorOrVoidType]

    def __post_init__(self) -> None:
        assert not isinstance(self.element_type, (FunctionType, ParameterPackType, BottomType))

    def __str__(self) -> str:
        return 'Sequence[%s]' % (
            str(self.element_type))

@dataclass(frozen=True)
class CustomTypeArgDecl:
    name: str
    expr_type: 'ExprType'

    def __str__(self) -> str:
        return '%s: %s' % (self.name, str(self.expr_type))

@dataclass(frozen=True)
class CustomType(_ExprType):
    name: str
    arg_types: Tuple[CustomTypeArgDecl, ...]
    constructor_source_branches: Tuple[SourceBranch, ...]

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

@dataclass(frozen=True)
class _Expr:
    expr_type: ExprType
    
    def _init_expr_type(self, expr_type: ExprType):
        object.__setattr__(self, 'expr_type', expr_type)

    def __str__(self) -> str: ...  # pragma: no cover

    def describe_other_fields(self) -> str: ...  # pragma: no cover

@dataclass(frozen=True)
class PatternExpr:
    expr_type: ExprType

    def _init_expr_type(self, expr_type: ExprType):
        object.__setattr__(self, 'expr_type', expr_type)

    def __str__(self) -> str: ...  # pragma: no cover

    def describe_other_fields(self) -> str: ...  # pragma: no cover


Expr = Union[_Expr, PatternExpr]


@dataclass(frozen=True)
class FunctionArgDecl:
    expr_type: ExprType
    name: str = ''

    def __str__(self) -> str:
        return '%s: %s' % (self.name, str(self.expr_type))

@dataclass(frozen=True)
class VarReference(_Expr):
    name: str
    is_global_function: bool
    is_function_that_may_throw: bool

    def __post_init__(self) -> None:
        assert self.name

    def __str__(self) -> str:
        return self.name

    def describe_other_fields(self) -> str:
        return 'is_global_function=%s, is_function_that_may_throw=%s' % (
            self.is_global_function,
            self.is_function_that_may_throw)

@dataclass(frozen=True)
class VarReferencePattern(PatternExpr):
    name: str
    is_global_function: bool
    is_function_that_may_throw: bool

    def __post_init__(self) -> None:
        assert self.name

    def __str__(self) -> str:
        return self.name

    def describe_other_fields(self) -> str:
        return 'is_global_function=%s, is_function_that_may_throw=%s' % (
            self.is_global_function,
            self.is_function_that_may_throw)

@dataclass(frozen=True)
class MatchCase:
    type_patterns: Tuple[PatternExpr, ...]
    matched_var_names: Tuple[str, ...]
    matched_variadic_var_names: Tuple[str, ...]
    expr: 'FunctionCall'
    match_case_start_branch: Optional[SourceBranch]
    match_case_end_branch: Optional[SourceBranch]

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

@dataclass(frozen=True)
class MatchExpr(_Expr):
    expr_type: ExprType = field(init=False)
    matched_vars: Tuple[VarReference, ...]
    match_cases: Tuple[MatchCase, ...]

    def __post_init__(self) -> None:
        self._init_expr_type(self.match_cases[0].expr.expr_type)

        assert self.matched_vars
        assert self.match_cases
        for match_case in self.match_cases:
            assert len(match_case.type_patterns) == len(self.matched_vars)

        assert len([match_case
                    for match_case in self.match_cases
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

@dataclass(frozen=True)
class BoolLiteral(_Expr):
    expr_type: ExprType = field(init=False)
    value: bool

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())

    def __str__(self) -> str:
        return repr(self.value)

    def describe_other_fields(self) -> str:
        return ''

@dataclass(frozen=True)
class AtomicTypeLiteral(_Expr):
    expr_type: ExprType = field(init=False)
    cpp_type: str

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())

    def __str__(self) -> str:
        return 'Type(\'%s\')' % self.cpp_type

    def describe_other_fields(self) -> str:
        return ''

@dataclass(frozen=True)
class AtomicTypeLiteralPattern(PatternExpr):
    expr_type: ExprType = field(init=False)
    cpp_type: str

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())

    def __str__(self) -> str:
        return 'Type(\'%s\')' % self.cpp_type

    def describe_other_fields(self) -> str:
        return ''

@dataclass(frozen=True)
class PointerTypeExpr(_Expr):
    expr_type: ExprType = field(init=False)
    type_expr: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

    def __str__(self) -> str:
        return 'Type.pointer(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

@dataclass(frozen=True)
class PointerTypePatternExpr(PatternExpr):
    expr_type: ExprType = field(init=False)
    type_expr: PatternExpr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

    def __str__(self) -> str:
        return 'Type.pointer(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

@dataclass(frozen=True)
class ReferenceTypeExpr(_Expr):
    expr_type: ExprType = field(init=False)
    type_expr: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

    def __str__(self) -> str:
        return 'Type.reference(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

@dataclass(frozen=True)
class ReferenceTypePatternExpr(PatternExpr):
    expr_type: ExprType = field(init=False)
    type_expr: PatternExpr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

    def __str__(self) -> str:
        return 'Type.reference(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

@dataclass(frozen=True)
class RvalueReferenceTypeExpr(_Expr):
    expr_type: ExprType = field(init=False)
    type_expr: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

    def __str__(self) -> str:
        return 'Type.rvalue_reference(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

@dataclass(frozen=True)
class RvalueReferenceTypePatternExpr(PatternExpr):
    expr_type: ExprType = field(init=False)
    type_expr: PatternExpr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

    def __str__(self) -> str:
        return 'Type.rvalue_reference(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

@dataclass(frozen=True)
class ConstTypeExpr(_Expr):
    expr_type: ExprType = field(init=False)
    type_expr: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

    def __str__(self) -> str:
        return 'Type.const(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

@dataclass(frozen=True)
class ConstTypePatternExpr(PatternExpr):
    expr_type: ExprType = field(init=False)
    type_expr: PatternExpr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

    def __str__(self) -> str:
        return 'Type.const(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

@dataclass(frozen=True)
class ArrayTypeExpr(_Expr):
    expr_type: ExprType = field(init=False)
    type_expr: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

    def __str__(self) -> str:
        return 'Type.array(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

@dataclass(frozen=True)
class ArrayTypePatternExpr(PatternExpr):
    expr_type: ExprType = field(init=False)
    type_expr: PatternExpr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

    def __str__(self) -> str:
        return 'Type.array(%s)' % str(self.type_expr)

    def describe_other_fields(self) -> str:
        return self.type_expr.describe_other_fields()

@dataclass(frozen=True)
class FunctionTypeExpr(_Expr):
    expr_type: ExprType = field(init=False)
    return_type_expr: VarReference
    arg_list_expr: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.return_type_expr.expr_type == TypeType()
        assert self.arg_list_expr.expr_type == ListType(TypeType())

    def __str__(self) -> str:
        return 'Type.function(%s, %s)' % (str(self.return_type_expr), str(self.arg_list_expr))

    def describe_other_fields(self) -> str:
        return 'return_type: %s; arg_type_list: %s' % (str(self.return_type_expr.describe_other_fields()),
                                                       str(self.arg_list_expr.describe_other_fields()))

@dataclass(frozen=True)
class FunctionTypePatternExpr(PatternExpr):
    expr_type: ExprType = field(init=False)
    return_type_expr: PatternExpr
    arg_list_expr: PatternExpr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.return_type_expr.expr_type == TypeType()
        assert self.arg_list_expr.expr_type == ListType(TypeType())

    def __str__(self) -> str:
        return 'Type.function(%s, %s)' % (str(self.return_type_expr), str(self.arg_list_expr))

    def describe_other_fields(self) -> str:
        return 'return_type: %s; arg_type_list: %s' % (str(self.return_type_expr.describe_other_fields()),
                                                       str(self.arg_list_expr.describe_other_fields()))

@dataclass(frozen=True)
class ParameterPackExpansion(_Expr):
    expr_type: ExprType = field(init=False)
    expr: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(self.expr.expr_type.element_type)
        assert isinstance(self.expr.expr_type, ParameterPackType)

    def __str__(self) -> str:
        return '*(%s)' % str(self.expr)

    def describe_other_fields(self) -> str:
        return self.expr.describe_other_fields()

# E.g. TemplateInstantiationExpr('std::vector', [AtomicTypeLiteral('int')]) is the type 'std::vector<int>'.
@dataclass(frozen=True)
class TemplateInstantiationExpr(_Expr):
    expr_type: ExprType = field(init=False)
    template_atomic_cpp_type: str
    arg_list_expr: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.arg_list_expr.expr_type == ListType(TypeType())

    def __str__(self) -> str:
        return 'Type.template_instantiation(\'%s\', %s)' % (self.template_atomic_cpp_type, str(self.arg_list_expr))

    def describe_other_fields(self) -> str:
        return self.arg_list_expr.describe_other_fields()

# E.g. TemplateInstantiationExpr('std::vector', [AtomicTypeLiteral('int')]) is the type 'std::vector<int>'.
@dataclass(frozen=True)
class TemplateInstantiationPatternExpr(PatternExpr):
    expr_type: ExprType = field(init=False)
    template_atomic_cpp_type: str
    arg_exprs: Tuple[PatternExpr, ...]
    list_extraction_arg_expr: Optional[VarReferencePattern]

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        for arg in self.arg_exprs:
            assert arg.expr_type == TypeType()
        if self.list_extraction_arg_expr:
            assert self.list_extraction_arg_expr.expr_type == ListType(TypeType())

    def __str__(self) -> str:
        return 'Type.template_instantiation(\'%s\', [%s%s])' % (self.template_atomic_cpp_type,
                                                                ', '.join(str(arg_expr) for arg_expr in self.arg_exprs),
                                                                ', *' + str(self.list_extraction_arg_expr) if self.list_extraction_arg_expr else '')

    def describe_other_fields(self) -> str:
        return '; '.join(arg_expr.describe_other_fields()
                         for arg_expr in itertools.chain(self.arg_exprs,
                                                         (self.list_extraction_arg_expr,) if self.list_extraction_arg_expr else tuple()))

# E.g. TemplateMemberAccessExpr(AtomicTypeLiteral('foo'), 'bar', [AtomicTypeLiteral('int')]) is the type 'foo::bar<int>'.
@dataclass(frozen=True)
class TemplateMemberAccessExpr(_Expr):
    expr_type: ExprType = field(init=False)
    class_type_expr: VarReference
    member_name: str
    arg_list_expr: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.class_type_expr.expr_type == TypeType()
        assert self.arg_list_expr.expr_type == ListType(TypeType())

    def __str__(self) -> str:
        return 'Type.template_member(%s, \'%s\', %s)' % (str(self.class_type_expr),
                                                         self.member_name,
                                                         str(self.arg_list_expr))

    def describe_other_fields(self) -> str:
        return 'class_type: %s; arg_type_list: %s' % (str(self.class_type_expr.describe_other_fields()),
                                                      str(self.arg_list_expr.describe_other_fields()))

@dataclass(frozen=True)
class ListExpr(_Expr):
    expr_type: ExprType = field(init=False)
    elem_type: ExprType
    elems: Tuple[VarReference, ...]

    def __post_init__(self) -> None:
        self._init_expr_type(ListType(self.elem_type))
        assert not isinstance(self.elem_type, FunctionType)

    def __str__(self) -> str:
        return '[%s]' % ', '.join(var.name
                                  for var in self.elems)

    def describe_other_fields(self) -> str:
        return ''

@dataclass(frozen=True)
class ListPatternExpr(PatternExpr):
    expr_type: ExprType = field(init=False)
    elem_type: ExprType
    elems: Tuple[PatternExpr, ...]
    list_extraction_expr: Optional[VarReference]

    def __post_init__(self) -> None:
        self._init_expr_type(ListType(self.elem_type))
        assert not isinstance(self.elem_type, FunctionType)

    def __str__(self) -> str:
        return '[%s]' % ', '.join(str(elem)
                                  for elem in self.elems)

    def describe_other_fields(self) -> str:
        return '[%s]' % '; '.join(elem.describe_other_fields()
                                  for elem in self.elems)

@dataclass(frozen=True)
class AddToSetExpr(_Expr):
    expr_type: ExprType = field(init=False)
    set_expr: VarReference
    elem_expr: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(ListType(self.set_expr.expr_type.elem_type))
        assert isinstance(self.set_expr.expr_type, ListType)
        assert self.set_expr.expr_type.elem_type == self.elem_expr.expr_type

    def __str__(self) -> str:
        return 'add_to_set(%s, %s)' % (
            str(self.set_expr),
            str(self.elem_expr))

    def describe_other_fields(self) -> str:
        return 'set: %s; elem: %s' % (self.set_expr.describe_other_fields(), self.elem_expr.describe_other_fields())

@dataclass(frozen=True)
class SetToListExpr(_Expr):
    expr_type: ExprType = field(init=False)
    var: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(ListType(self.var.expr_type.elem_type))
        assert isinstance(self.var.expr_type, ListType)

    def __str__(self) -> str:
        return 'set_to_list(%s)' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

@dataclass(frozen=True)
class ListToSetExpr(_Expr):
    expr_type: ExprType = field(init=False)
    var: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(ListType(self.var.expr_type.elem_type))
        assert isinstance(self.var.expr_type, ListType)

    def __str__(self) -> str:
        return 'list_to_set(%s)' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

@dataclass(frozen=True)
class FunctionCall(_Expr):
    expr_type: ExprType = field(init=False)
    fun: VarReference
    args: Tuple[VarReference, ...]

    def __post_init__(self) -> None:
        self._init_expr_type(self.fun.expr_type.returns)
        assert isinstance(self.fun.expr_type, FunctionType)
        assert len(self.fun.expr_type.argtypes) == len(self.args)
        assert self.args

    def __str__(self) -> str:
        return '%s(%s)' % (
            self.fun.name,
            ', '.join(var.name
                      for var in self.args))

    def describe_other_fields(self) -> str:
        return '; '.join('%s: %s' % (var.name, var.describe_other_fields())
                         for vars in ([self.fun], self.args)
                         for var in vars)

@dataclass(frozen=True)
class EqualityComparison(_Expr):
    expr_type: ExprType = field(init=False)
    lhs: VarReference
    rhs: VarReference

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert ((self.lhs.expr_type == ErrorOrVoidType() and self.rhs.expr_type == TypeType())
                or self.lhs.expr_type == self.rhs.expr_type), \
            f'{self.lhs.expr_type} ({self.lhs.expr_type!r}) vs {self.rhs.expr_type} ({self.rhs.expr_type!r})'
        assert not isinstance(self.lhs.expr_type, FunctionType)

    def __str__(self) -> str:
        return '%s == %s' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

@dataclass(frozen=True)
class SetEqualityComparison(_Expr):
    expr_type: ExprType = field(init=False)
    lhs: VarReference
    rhs: VarReference
    
    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert isinstance(self.lhs.expr_type, ListType)
        assert self.lhs.expr_type == self.rhs.expr_type

    def __str__(self) -> str:
        return 'set_equals(%s, %s)' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

@dataclass(frozen=True)
class IsInListExpr(_Expr):
    expr_type: ExprType = field(init=False)
    lhs: VarReference
    rhs: VarReference
    
    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert isinstance(self.rhs.expr_type, ListType)
        assert self.lhs.expr_type == self.rhs.expr_type.elem_type

    def __str__(self) -> str:
        return '%s in %s' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

@dataclass(frozen=True)
class AttributeAccessExpr(_Expr):
    var: VarReference
    attribute_name: str
    expr_type: ExprType
    
    def __post_init__(self) -> None:
        assert isinstance(self.var.expr_type, (TypeType, CustomType))

    def __str__(self) -> str:
        return '%s.%s' % (self.var.name, self.attribute_name)

    def describe_other_fields(self) -> str:
        return ''

@dataclass(frozen=True)
class IntLiteral(_Expr):
    expr_type: ExprType = field(init=False)
    value: int
    
    def __post_init__(self) -> None:
        self._init_expr_type(IntType())

    def __str__(self) -> str:
        return str(self.value)

    def describe_other_fields(self) -> str:
        return ''

@dataclass(frozen=True)
class NotExpr(_Expr):
    expr_type: ExprType = field(init=False)
    var: VarReference

    def __post_init__(self) -> None:
        assert self.var.expr_type == BoolType()
        self._init_expr_type(BoolType())

    def __str__(self) -> str:
        return 'not %s' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

@dataclass(frozen=True)
class UnaryMinusExpr(_Expr):
    expr_type: ExprType = field(init=False)
    var: VarReference

    def __post_init__(self) -> None:
        assert self.var.expr_type == IntType()
        self._init_expr_type(IntType())

    def __str__(self) -> str:
        return '-%s' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

@dataclass(frozen=True)
class IntListSumExpr(_Expr):
    expr_type: ExprType = field(init=False)
    var: VarReference

    def __post_init__(self) -> None:
        assert isinstance(self.var.expr_type, ListType)
        assert isinstance(self.var.expr_type.elem_type, IntType)
        self._init_expr_type(IntType())

    def __str__(self) -> str:
        return 'sum(%s)' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

@dataclass(frozen=True)
class BoolListAllExpr(_Expr):
    expr_type: ExprType = field(init=False)
    var: VarReference

    def __post_init__(self) -> None:
        assert isinstance(self.var.expr_type, ListType)
        assert isinstance(self.var.expr_type.elem_type, BoolType)
        self._init_expr_type(BoolType())

    def __str__(self) -> str:
        return 'all(%s)' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

@dataclass(frozen=True)
class BoolListAnyExpr(_Expr):
    expr_type: ExprType = field(init=False)
    var: VarReference

    def __post_init__(self) -> None:
        assert isinstance(self.var.expr_type, ListType)
        assert isinstance(self.var.expr_type.elem_type, BoolType)
        self._init_expr_type(BoolType())

    def __str__(self) -> str:
        return 'any(%s)' % self.var.name

    def describe_other_fields(self) -> str:
        return self.var.describe_other_fields()

@dataclass(frozen=True)
class IntComparisonExpr(_Expr):
    expr_type: ExprType = field(init=False)
    lhs: VarReference
    rhs: VarReference
    op: str

    def __post_init__(self) -> None:
        assert self.lhs.expr_type == IntType()
        assert self.rhs.expr_type == IntType()
        assert self.op in ('<', '>', '<=', '>=')
        self._init_expr_type(BoolType())

    def __str__(self) -> str:
        return '%s %s %s' % (self.lhs.name, self.op, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

@dataclass(frozen=True)
class IntBinaryOpExpr(_Expr):
    expr_type: ExprType = field(init=False)
    lhs: VarReference
    rhs: VarReference
    op: str

    def __post_init__(self) -> None:
        assert self.lhs.expr_type == IntType()
        assert self.rhs.expr_type == IntType()
        assert self.op in ('+', '-', '*', '//', '%')
        self._init_expr_type(IntType())

    def __str__(self) -> str:
        return '%s %s %s' % (self.lhs.name, self.op, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

@dataclass(frozen=True)
class ListConcatExpr(_Expr):
    expr_type: ExprType = field(init=False)
    lhs: VarReference
    rhs: VarReference

    def __post_init__(self) -> None:
        assert isinstance(self.lhs.expr_type, ListType)
        assert self.lhs.expr_type == self.rhs.expr_type
        self._init_expr_type(self.lhs.expr_type)

    def __str__(self) -> str:
        return '%s + %s' % (self.lhs.name, self.rhs.name)

    def describe_other_fields(self) -> str:
        return '(lhs: %s; rhs: %s)' % (self.lhs.describe_other_fields(), self.rhs.describe_other_fields())

@dataclass(frozen=True)
class IsInstanceExpr(_Expr):
    expr_type: ExprType = field(init=False)
    var: VarReference
    checked_type: CustomType

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())

    def __str__(self) -> str:
        return 'isinstance(%s, %s)' % (self.var.name, str(self.checked_type))

    def describe_other_fields(self) -> str:
        return ''

@dataclass(frozen=True)
class SafeUncheckedCast(_Expr):
    var: VarReference

    def __post_init__(self) -> None:
        assert isinstance(self.var.expr_type, ErrorOrVoidType)
        assert isinstance(self.expr_type, CustomType)

    def __str__(self) -> str:
        return '%s  # type: %s' % (self.var.name, str(self.expr_type))

    def describe_other_fields(self) -> str:
        return ''

@dataclass(frozen=True)
class ListComprehensionExpr(_Expr):
    expr_type: ExprType = field(init=False)
    list_var: VarReference
    loop_var: VarReference
    result_elem_expr: FunctionCall
    loop_body_start_branch: Optional[SourceBranch]
    loop_exit_branch: Optional[SourceBranch]

    def __post_init__(self) -> None:
        assert isinstance(self.list_var.expr_type, ListType)
        assert self.list_var.expr_type.elem_type == self.loop_var.expr_type
        self._init_expr_type(ListType(self.result_elem_expr.expr_type))

    def __str__(self) -> str:
        return '[%s for %s in %s]' % (str(self.result_elem_expr), self.loop_var.name, self.list_var.name)

    def describe_other_fields(self) -> str:
        return ''

@dataclass(frozen=True)
class ReturnTypeInfo:
    # When expr_type is None, the statement never returns.
    # expr_type can't be None if always_returns is True.
    expr_type: Optional[ExprType]
    always_returns: bool

    def __post_init__(self) -> None:
        if self.always_returns:
            assert self.expr_type

@dataclass(frozen=True)
class Stmt:
    def write(self, writer: Writer, verbose: bool): ...  # pragma: no cover

@dataclass(frozen=True)
class PassStmt(Stmt):
    source_branch: Optional[SourceBranch]

    def write(self, writer: Writer, verbose: bool):
        writer.writeln('pass')

@dataclass(frozen=True)
class Assert(Stmt):
    var: VarReference
    message: str
    source_branch: Optional[SourceBranch]

    def __post_init__(self) -> None:
        assert isinstance(self.var.expr_type, BoolType)

    def write(self, writer: Writer, verbose: bool):
        writer.write('assert ')
        writer.write(self.var.name)
        if verbose:
            writer.writeln('  # %s' % self.var.describe_other_fields())
        else:
            writer.writeln('')

@dataclass(frozen=True)
class Assignment(Stmt):
    lhs: VarReference
    rhs: Expr
    source_branch: Optional[SourceBranch]
    lhs2: Optional[VarReference] = None

    def __post_init__(self) -> None:
        assert self.lhs.expr_type == self.rhs.expr_type, '%s vs %s' % (str(self.lhs.expr_type), str(self.rhs.expr_type))
        if self.lhs2:
            assert isinstance(self.lhs2.expr_type, ErrorOrVoidType)
            assert isinstance(self.rhs, (MatchExpr, FunctionCall, ListComprehensionExpr))

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

@dataclass(frozen=True)
class CheckIfError(Stmt):
    var: VarReference

    def __post_init__(self) -> None:
        assert self.var.expr_type == ErrorOrVoidType()

    def write(self, writer: Writer, verbose: bool):
        writer.write('check_if_error(')
        writer.write(str(self.var))
        if verbose:
            writer.write(')  # ')
            writer.writeln(self.var.describe_other_fields())
        else:
            writer.writeln(')')

@dataclass(frozen=True)
class UnpackingAssignment(Stmt):
    lhs_list: Tuple[VarReference, ...]
    rhs: VarReference
    error_message: str
    source_branch: Optional[SourceBranch]

    def __post_init__(self) -> None:
        assert isinstance(self.rhs.expr_type, ListType)
        assert self.lhs_list
        for lhs in self.lhs_list:
            assert lhs.expr_type == self.rhs.expr_type.elem_type

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

@dataclass(frozen=True)
class ReturnStmt(Stmt):
    result: Optional[VarReference]
    error: Optional[VarReference]
    source_branch: Optional[SourceBranch]

    def __post_init__(self) -> None:
        assert self.result or self.error

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

@dataclass(frozen=True)
class IfStmt(Stmt):
    cond: VarReference
    if_stmts: Tuple[Stmt, ...]
    else_stmts: Tuple[Stmt, ...]

    def __post_init__(self) -> None:
        assert self.cond.expr_type == BoolType()

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

@dataclass(frozen=True)
class FunctionDefn:
    name: str
    description: str
    args: Tuple[FunctionArgDecl, ...]
    body: Tuple[Stmt, ...]
    return_type: ExprType

    def __post_init__(self) -> None:
        assert self.body

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

@dataclass(frozen=True)
class CheckIfErrorDefn:
    error_types_and_messages: Tuple[Tuple[CustomType, str], ...]

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

@dataclass(frozen=True)
class Module:
    body: Tuple[Union[FunctionDefn, Assignment, Assert, CustomType, CheckIfErrorDefn, PassStmt], ...]
    public_names: FrozenSet[str]

    def __str__(self) -> str:
        writer = Writer()
        for elem in self.body:
            elem.write(writer, verbose=False)
        return ''.join(writer.strings)
