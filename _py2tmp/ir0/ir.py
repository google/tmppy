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
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence, Set, Optional, Iterable, Union, Tuple, FrozenSet

from _py2tmp.coverage import SourceBranch
from _py2tmp.utils import ir_to_string


class ExprKind(Enum):
    BOOL = 1
    INT64 = 2
    TYPE = 3
    TEMPLATE = 4

class _TemplateBodyElementOrExprOrTemplateDefn:
    @property
    def referenced_identifiers(self) -> Iterable[str]:
        for expr in self.transitive_subexpressions:
            for identifier in expr.local_referenced_identifiers:
                yield identifier

    # Returns all transitive subexpressions
    @property
    def transitive_subexpressions(self) -> Iterable['Expr']:
        if isinstance(self, Expr):
            yield self
        for elem in self.direct_subelements:
            for subexpr in elem.transitive_subexpressions:
                yield subexpr
        for expr in self.direct_subexpressions:
            for subexpr in expr.transitive_subexpressions:
                yield subexpr

    @property
    def direct_subelements(self) -> Iterable['TemplateBodyElement']: ...

    @property
    def direct_subexpressions(self) -> Iterable['Expr']: ...

@dataclass(frozen=True)
class _ExprType:
    kind: ExprKind

@dataclass(frozen=True)
class BoolType(_ExprType):
    kind: ExprKind = field(default=ExprKind.BOOL, init=False)

@dataclass(frozen=True)
class Int64Type(_ExprType):
    kind: ExprKind = field(default=ExprKind.INT64, init=False)

@dataclass(frozen=True)
class TypeType(_ExprType):
    kind: ExprKind = field(default=ExprKind.TYPE, init=False)

@dataclass(frozen=True)
class TemplateArgType:
    expr_type: 'ExprType'
    is_variadic: bool

@dataclass(frozen=True)
class TemplateType(_ExprType):
    kind: ExprKind = field(default=ExprKind.TEMPLATE, init=False)
    args: Tuple[TemplateArgType, ...]

# Similar to _ExprType but more precise, to help type checking.
ExprType = Union[BoolType, Int64Type, TypeType, TemplateType]

@dataclass(frozen=True)
class Expr(_TemplateBodyElementOrExprOrTemplateDefn):
    expr_type: ExprType

    def references_any_of(self, variables: Set[str]):
        return any(isinstance(expr, AtomicTypeLiteral) and expr.cpp_type in variables
                   for expr in self.transitive_subexpressions)

    @property
    def free_vars(self) -> Iterable['AtomicTypeLiteral']:
        for expr in self.transitive_subexpressions:
            if isinstance(expr, AtomicTypeLiteral) and expr.is_local:
                yield expr

    @property
    def local_referenced_identifiers(self) -> Iterable[str]:
        if isinstance(self, AtomicTypeLiteral):
            yield self.cpp_type

    @property
    def direct_subelements(self) -> Iterable['TemplateBodyElement']:
        return []

    def is_same_expr_excluding_subexpressions(self, other: 'Expr') -> bool: ...

    def copy_with_subexpressions(self, new_subexpressions: Sequence['Expr']): ...

@dataclass(frozen=True)
class _TemplateBodyElement(_TemplateBodyElementOrExprOrTemplateDefn):
    pass

@dataclass(frozen=True)
class StaticAssert(_TemplateBodyElement):
    expr: Expr
    message: str

    def __post_init__(self) -> None:
        assert isinstance(self.expr.expr_type, BoolType)

    @property
    def direct_subelements(self) -> Iterable['TemplateBodyElement']:
        return []

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.expr

@dataclass(frozen=True)
class NoOpStmt(_TemplateBodyElement):
    source_branch: SourceBranch

    @property
    def direct_subelements(self) -> Iterable['TemplateBodyElement']:
        return ()

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        return ()

@dataclass(frozen=True)
class ConstantDef(_TemplateBodyElement):
    name: str
    expr: Expr

    def __post_init__(self) -> None:
        assert isinstance(self.expr.expr_type, (BoolType, Int64Type))

    @property
    def direct_subelements(self) -> Iterable['TemplateBodyElement']:
        return []

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.expr

@dataclass(frozen=True)
class Typedef(_TemplateBodyElement):
    name: str
    expr: Expr
    description: str = ''
    template_args: Tuple['TemplateArgDecl', ...] = ()

    def __post_init__(self) -> None:
        assert isinstance(self.expr.expr_type, (TypeType, TemplateType))

    @property
    def direct_subelements(self) -> Iterable['TemplateBodyElement']:
        return []

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.expr


# Similar to _TemplateBodyElement but more precise, to help type checking.
TemplateBodyElement = Union[StaticAssert, ConstantDef, Typedef, NoOpStmt]


@dataclass(frozen=True)
class TemplateArgDecl:
    expr_type: ExprType
    name: str
    is_variadic: bool

    def __post_init__(self) -> None:
        assert self.name

_non_identifier_char_pattern = re.compile('[^a-zA-Z0-9_]+')

@dataclass(frozen=True)
class TemplateSpecialization:
    args: Tuple[TemplateArgDecl, ...]
    patterns: Optional[Tuple[Expr, ...]]
    body: Tuple[TemplateBodyElement, ...]
    is_metafunction: bool

    def __post_init__(self) -> None:
        if self.body:
            for arg in self.args:
                assert arg.name

        assert (not self.body
                or not self.is_metafunction
                or any(isinstance(elem, Typedef) and elem.name in ('type', 'error', 'value')
                       for elem in self.body)
                or any(isinstance(elem, ConstantDef) and elem.name == 'value'
                       for elem in self.body)), ir_to_string(self)

@dataclass(frozen=True)
class TemplateDefn(_TemplateBodyElementOrExprOrTemplateDefn):
    main_definition: Optional[TemplateSpecialization]
    specializations: Tuple[TemplateSpecialization, ...]
    name: str
    description: str
    result_element_names: FrozenSet[str]
    args: Optional[Tuple[TemplateArgDecl, ...]] = None

    def __post_init__(self) -> None:
        if self.main_definition and not self.args:
            object.__setattr__(self, 'args', self.main_definition.args)

        assert self.main_definition or self.specializations
        assert not self.main_definition or self.main_definition.patterns is None
        for specialization in self.specializations:
            assert specialization.patterns is not None
        assert '\n' not in self.description
        assert self.args is not None
        if self.main_definition:
            declaration_args = [(arg.expr_type, arg.name) for arg in self.args]
            main_defn_args = [(arg.expr_type, arg.name) for arg in self.main_definition.args]
            assert declaration_args == main_defn_args, '%s != %s' % (
                ', '.join('(%s, %s)' % (str(expr_type), name) for expr_type, name in declaration_args),
                ', '.join('(%s, %s)' % (str(expr_type), name) for expr_type, name in main_defn_args))

    @property
    def all_definitions(self) -> Iterable[TemplateSpecialization]:
        if self.main_definition:
            yield self.main_definition
        for specialization in self.specializations:
            yield specialization

    @property
    def direct_subelements(self) -> Iterable[TemplateBodyElement]:
        for specialization in self.all_definitions:
            for elem in specialization.body:
                yield elem

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        for specialization in self.all_definitions:
            if specialization.patterns:
                for expr in specialization.patterns:
                    yield expr

@dataclass(frozen=True)
class Literal(Expr):
    expr_type: ExprType = field(init=False)
    value: Union[bool, int]

    def __post_init__(self) -> None:
        if isinstance(self.value, bool):
            expr_type = BoolType()
        elif isinstance(self.value, int):
            expr_type = Int64Type()
        else:
            raise NotImplementedError('Unexpected value: ' + repr(self.value))
        object.__setattr__(self, 'expr_type', expr_type)

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, Literal) and self.value == other.value

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        return []

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]) -> Expr:
        assert not new_subexpressions
        return self

@dataclass(frozen=True)
class AtomicTypeLiteral(Expr):
    expr_type: ExprType = field()
    cpp_type: str
    is_local: bool
    is_metafunction_that_may_return_error: bool
    # Only relevant for non-local literals.
    may_be_alias: bool
    is_variadic: bool

    def __post_init__(self) -> None:
        assert not (self.is_metafunction_that_may_return_error and not isinstance(self.expr_type, TemplateType))
        if self.is_variadic:
            assert self.expr_type.kind in (ExprKind.BOOL, ExprKind.INT64, ExprKind.TYPE)

    @property
    def direct_free_vars(self) -> Iterable[Expr]:
        if self.is_local:
            yield self

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        # We intentionally don't compare type, is_metafunction_that_may_return_error, may_be_alias since we might have
        # different information for different literal expressions (e.g. a 2-arg std::tuple vs a 3-arg one).
        return isinstance(other, AtomicTypeLiteral) and self.cpp_type == other.cpp_type and self.is_local == other.is_local

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        return []

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        assert not new_subexpressions
        return self

    @staticmethod
    def for_local(cpp_type: str,
                  expr_type: ExprType,
                  is_variadic: bool):
        return AtomicTypeLiteral(cpp_type=cpp_type,
                                 is_local=True,
                                 expr_type=expr_type,
                                 is_metafunction_that_may_return_error=(expr_type.kind == ExprKind.TEMPLATE),
                                 may_be_alias=True,
                                 is_variadic=is_variadic)

    @staticmethod
    def for_nonlocal(cpp_type: str,
                     expr_type: ExprType,
                     is_metafunction_that_may_return_error: bool,
                     may_be_alias: bool):
        return AtomicTypeLiteral(cpp_type=cpp_type,
                                 is_local=False,
                                 expr_type=expr_type,
                                 is_metafunction_that_may_return_error=is_metafunction_that_may_return_error,
                                 may_be_alias=may_be_alias,
                                 is_variadic=False)

    @staticmethod
    def for_nonlocal_type(cpp_type: str, may_be_alias: bool):
        return AtomicTypeLiteral.for_nonlocal(cpp_type=cpp_type,
                                              expr_type=TypeType(),
                                              is_metafunction_that_may_return_error=False,
                                              may_be_alias=may_be_alias)

    @staticmethod
    def for_nonlocal_template(cpp_type: str,
                              args: Tuple[TemplateArgType, ...],
                              is_metafunction_that_may_return_error: bool,
                              may_be_alias: bool):
        return AtomicTypeLiteral.for_nonlocal(cpp_type=cpp_type,
                                              expr_type=TemplateType(args),
                                              is_metafunction_that_may_return_error=is_metafunction_that_may_return_error,
                                              may_be_alias=may_be_alias)

    @staticmethod
    def from_nonlocal_template_defn(template_defn: TemplateDefn,
                                    is_metafunction_that_may_return_error: bool):
        return AtomicTypeLiteral.for_nonlocal_template(cpp_type=template_defn.name,
                                                       args=tuple(TemplateArgType(expr_type=arg.expr_type, is_variadic=arg.is_variadic)
                                                                  for arg in template_defn.args),
                                                       is_metafunction_that_may_return_error=is_metafunction_that_may_return_error,
                                                       may_be_alias=False)

@dataclass(frozen=True)
class PointerTypeExpr(Expr):
    expr_type: TypeType = field(default=TypeType(), init=False)
    type_expr: Expr

    def __post_init__(self) -> None:
        assert self.type_expr.expr_type == TypeType()

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, PointerTypeExpr)

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.type_expr

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [new_type_expr] = new_subexpressions
        return PointerTypeExpr(new_type_expr)

@dataclass(frozen=True)
class ReferenceTypeExpr(Expr):
    expr_type: TypeType = field(default=TypeType(), init=False)
    type_expr: Expr

    def __post_init__(self) -> None:
        assert self.type_expr.expr_type == TypeType()

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, ReferenceTypeExpr)

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.type_expr

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [new_type_expr] = new_subexpressions
        return ReferenceTypeExpr(new_type_expr)

@dataclass(frozen=True)
class RvalueReferenceTypeExpr(Expr):
    expr_type: TypeType = field(default=TypeType(), init=False)
    type_expr: Expr

    def __post_init__(self) -> None:
        assert self.type_expr.expr_type == TypeType()

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, RvalueReferenceTypeExpr)

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.type_expr

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [new_type_expr] = new_subexpressions
        return RvalueReferenceTypeExpr(new_type_expr)

@dataclass(frozen=True)
class ConstTypeExpr(Expr):
    expr_type: TypeType = field(default=TypeType(), init=False)
    type_expr: Expr

    def __post_init__(self) -> None:
        assert self.type_expr.expr_type == TypeType()

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, ConstTypeExpr)

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.type_expr
    
    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [new_type_expr] = new_subexpressions
        return ConstTypeExpr(new_type_expr)

@dataclass(frozen=True)
class ArrayTypeExpr(Expr):
    expr_type: TypeType = field(default=TypeType(), init=False)
    type_expr: Expr

    def __post_init__(self) -> None:
        assert self.type_expr.expr_type == TypeType()

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, ArrayTypeExpr)

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.type_expr
    
    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [new_type_expr] = new_subexpressions
        return ArrayTypeExpr(new_type_expr)

@dataclass(frozen=True)
class FunctionTypeExpr(Expr):
    expr_type: TypeType = field(default=TypeType(), init=False)
    return_type_expr: Expr
    arg_exprs: Tuple[Expr, ...]

    def __post_init__(self) -> None:
        assert self.return_type_expr.expr_type == TypeType(), self.return_type_expr.expr_type

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, FunctionTypeExpr)

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.return_type_expr
        for expr in self.arg_exprs:
            yield expr

    def copy_with_subexpressions(self, new_subexpressions: Sequence['Expr']):
        [new_return_type_expr, *new_arg_exprs] = new_subexpressions
        return FunctionTypeExpr(new_return_type_expr, new_arg_exprs)

@dataclass(frozen=True)
class UnaryExpr(Expr):
    expr_type: ExprType
    inner_expr: Expr

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.inner_expr

@dataclass(frozen=True)
class BinaryExpr(Expr):
    expr_type: ExprType
    lhs: Expr
    rhs: Expr

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.lhs
        yield self.rhs

@dataclass(frozen=True)
class ComparisonExpr(BinaryExpr):
    expr_type: BoolType = field(default=BoolType(), init=False)
    op: str

    def __post_init__(self) -> None:
        assert self.lhs.expr_type == self.rhs.expr_type
        if isinstance(self.lhs.expr_type, BoolType):
            assert self.op in ('==', '!=')
        elif isinstance(self.lhs.expr_type, Int64Type):
            assert self.op in ('==', '!=', '<', '>', '<=', '>=')
        else:
            raise NotImplementedError('Unexpected type: %s' % str(self.lhs.expr_type))

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, ComparisonExpr) and self.op == other.op

    def copy_with_subexpressions(self, new_subexpressions: Sequence['Expr']):
        [lhs, rhs] = new_subexpressions
        return ComparisonExpr(lhs, rhs, self.op)

@dataclass(frozen=True)
class Int64BinaryOpExpr(BinaryExpr):
    expr_type: Int64Type = field(default=Int64Type(), init=False)
    op: str

    def __post_init__(self) -> None:
        assert isinstance(self.lhs.expr_type, Int64Type)
        assert isinstance(self.rhs.expr_type, Int64Type)
        assert self.op in ('+', '-', '*', '/', '%')

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, Int64BinaryOpExpr) and self.op == other.op

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [lhs, rhs] = new_subexpressions
        return Int64BinaryOpExpr(lhs, rhs, self.op)

@dataclass(frozen=True)
class BoolBinaryOpExpr(BinaryExpr):
    expr_type: BoolType = field(default=BoolType(), init=False)
    op: str

    def __post_init__(self) -> None:
        assert isinstance(self.lhs.expr_type, BoolType)
        assert isinstance(self.rhs.expr_type, BoolType)
        assert self.op in ('&&', '||')

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, BoolBinaryOpExpr) and self.op == other.op

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [lhs, rhs] = new_subexpressions
        return BoolBinaryOpExpr(lhs, rhs, self.op)

@dataclass(frozen=True)
class TemplateInstantiation(Expr):
    expr_type: TypeType = field(default=TypeType(), init=False)
    template_expr: Expr
    args: Tuple[Expr, ...]
    instantiation_might_trigger_static_asserts: bool

    def __post_init__(self) -> None:
        assert isinstance(self.template_expr.expr_type, TemplateType), str(self.template_expr.expr_type)

        if any(arg.is_variadic
               for arg in self.template_expr.expr_type.args):
            # In this case it's fine if the two lists "don't match up"
            pass
        else:
            assert len(self.template_expr.expr_type.args) == len(self.args)
            for arg_decl, arg_expr in zip(self.template_expr.expr_type.args, self.args):
                assert arg_decl.expr_type == arg_expr.expr_type, '\n%s vs:\n%s' % (str(arg_decl.expr_type), str(arg_expr.expr_type))

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, TemplateInstantiation)

    @property
    def direct_subexpressions(self) -> Iterable[Expr]:
        yield self.template_expr
        for expr in self.args:
            yield expr

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [template_expr, *args] = new_subexpressions
        return TemplateInstantiation(template_expr, args, self.instantiation_might_trigger_static_asserts)

@dataclass(frozen=True)
class ClassMemberAccess(UnaryExpr):
    member_name: str

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, ClassMemberAccess) and self.member_name == other.member_name

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [inner_expr] = new_subexpressions
        return ClassMemberAccess(inner_expr=inner_expr, member_name=self.member_name, expr_type=self.expr_type)

@dataclass(frozen=True)
class NotExpr(UnaryExpr):
    expr_type: BoolType = field(default=BoolType(), init=False)

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, NotExpr)

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [expr] = new_subexpressions
        return NotExpr(expr)

@dataclass(frozen=True)
class UnaryMinusExpr(UnaryExpr):
    expr_type: Int64Type = field(default=Int64Type(), init=False)

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, UnaryMinusExpr)

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [expr] = new_subexpressions
        return UnaryMinusExpr(expr)

@dataclass(frozen=True)
class VariadicTypeExpansion(UnaryExpr):
    expr_type: BoolType = field(default=BoolType(), init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'expr_type', self.inner_expr.expr_type)
        assert any(var.is_variadic
                   for var in self.inner_expr.free_vars)

    def is_same_expr_excluding_subexpressions(self, other: Expr):
        return isinstance(other, VariadicTypeExpansion)

    def copy_with_subexpressions(self, new_subexpressions: Sequence[Expr]):
        [expr] = new_subexpressions
        return VariadicTypeExpansion(inner_expr=expr)

@dataclass(frozen=True)
class Header:
    template_defns: Tuple[TemplateDefn, ...]
    check_if_error_specializations: Tuple[TemplateSpecialization, ...]
    toplevel_content: Tuple[Union[StaticAssert, ConstantDef, Typedef], ...]
    public_names: FrozenSet[str]
    # Semantically, this is a map (old_name, result_element_name) -> split_template_name.
    split_template_name_by_old_name_and_result_element_name: Tuple[Tuple[Tuple[str, str], str], ...]

