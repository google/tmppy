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
from dataclasses import dataclass, field
from typing import Optional, Tuple, FrozenSet

from _py2tmp.coverage._source_branch import SourceBranch

@dataclass(frozen=True)
class ExprType:
    def __str__(self) -> str: ...  # pragma: no cover

@dataclass(frozen=True)
class BoolType(ExprType):
    def __str__(self) -> str:
        return 'bool'

# A type with no values. This is the return type of functions that never return.
@dataclass(frozen=True)
class BottomType(ExprType):
    def __str__(self) -> str:
        return 'BottomType'

@dataclass(frozen=True)
class IntType(ExprType):
    def __str__(self) -> str:
        return 'int'

@dataclass(frozen=True)
class TypeType(ExprType):
    def __str__(self) -> str:
        return 'Type'

@dataclass(frozen=True)
class FunctionType(ExprType):
    argtypes: Tuple[ExprType, ...]
    # If present, it matches element-by-element argtypes and the function can be called with these keyword args.
    argnames: Optional[Tuple[str, ...]] = field(compare=False)
    returns: ExprType

    def __post_init__(self) -> None:
        if self.argnames:
            assert len(self.argtypes) == len(self.argnames)
            for arg in self.argnames:
                assert arg

    def __str__(self) -> str:
        return "(%s) -> %s" % (
            ', '.join(str(arg)
                      for arg in self.argtypes),
            str(self.returns))

@dataclass(frozen=True)
class ListType(ExprType):
    elem_type: ExprType

    def __post_init__(self) -> None:
        assert not isinstance(self.elem_type, FunctionType)

    def __str__(self) -> str:
        return "List[%s]" % str(self.elem_type)

@dataclass(frozen=True)
class SetType(ExprType):
    elem_type: ExprType

    def __post_init__(self) -> None:
        assert not isinstance(self.elem_type, FunctionType)

    def __str__(self) -> str:
        return "Set[%s]" % str(self.elem_type)

@dataclass(frozen=True)
class CustomTypeArgDecl:
    name: str
    expr_type: ExprType

@dataclass(frozen=True)
class CustomType(ExprType):
    name: str
    arg_types: Tuple[CustomTypeArgDecl, ...]
    is_exception_class: bool
    exception_message: Optional[str]
    constructor_source_branches: Tuple[SourceBranch, ...]

    def __post_init__(self) -> None:
        assert (self.exception_message is not None) == self.is_exception_class

    def __str__(self) -> str:
        return self.name

@dataclass(frozen=True)
class Expr:
    expr_type: ExprType

    def _init_expr_type(self, expr_type: ExprType):
        object.__setattr__(self, 'expr_type', expr_type)

@dataclass(frozen=True)
class FunctionArgDecl:
    expr_type: ExprType
    name: str = ''

@dataclass(frozen=True)
class VarReference(Expr):
    expr_type: ExprType
    name: str
    is_global_function: bool
    is_function_that_may_throw: bool
    source_module: Optional[str] = None

    def __post_init__(self) -> None:
        assert self.name

@dataclass(frozen=True)
class MatchCase:
    matched_var_names: FrozenSet[str]
    matched_variadic_var_names: FrozenSet[str]
    type_patterns: Tuple[Expr, ...]
    expr: Expr
    match_case_start_branch: SourceBranch
    match_case_end_branch: SourceBranch

    def is_main_definition(self) -> bool:
        matched_var_names_set = set(self.matched_var_names).union(self.matched_variadic_var_names)
        return all(isinstance(pattern, VarReference) and pattern.name in matched_var_names_set
                   for pattern in self.type_patterns)

@dataclass(frozen=True)
class MatchExpr(Expr):
    expr_type: ExprType = field(init=False)
    matched_exprs: Tuple[Expr, ...]
    match_cases: Tuple[MatchCase, ...]

    def __post_init__(self) -> None:
        self._init_expr_type(self.match_cases[0].expr.expr_type)

        assert self.matched_exprs
        assert self.match_cases
        for match_case in self.match_cases:
            assert len(match_case.type_patterns) == len(self.matched_exprs)
            assert match_case.expr.expr_type == self.match_cases[0].expr.expr_type

        assert len([match_case
                    for match_case in self.match_cases
                    if match_case.is_main_definition()]) <= 1

@dataclass(frozen=True)
class BoolLiteral(Expr):
    expr_type: ExprType = field(init=False)
    value: bool

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())

@dataclass(frozen=True)
class AtomicTypeLiteral(Expr):
    expr_type: ExprType = field(init=False)
    cpp_type: str

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())

@dataclass(frozen=True)
class PointerTypeExpr(Expr):
    expr_type: ExprType = field(init=False)
    type_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

@dataclass(frozen=True)
class ReferenceTypeExpr(Expr):
    expr_type: ExprType = field(init=False)
    type_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

@dataclass(frozen=True)
class RvalueReferenceTypeExpr(Expr):
    expr_type: ExprType = field(init=False)
    type_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

@dataclass(frozen=True)
class ConstTypeExpr(Expr):
    expr_type: ExprType = field(init=False)
    type_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

@dataclass(frozen=True)
class ArrayTypeExpr(Expr):
    expr_type: ExprType = field(init=False)
    type_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())
        assert self.type_expr.expr_type == TypeType()

@dataclass(frozen=True)
class FunctionTypeExpr(Expr):
    expr_type: ExprType = field(init=False)
    return_type_expr: Expr
    arg_list_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())

        assert self.return_type_expr.expr_type == TypeType()
        assert self.arg_list_expr.expr_type == ListType(TypeType())

# E.g. TemplateInstantiationExpr('std::vector', [AtomicTypeLiteral('int')]) is the type 'std::vector<int>'.

@dataclass(frozen=True)
class TemplateInstantiationExpr(Expr):
    expr_type: ExprType = field(init=False)
    template_atomic_cpp_type: str
    arg_list_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())

        assert self.arg_list_expr.expr_type == ListType(TypeType())

# E.g. TemplateMemberAccessExpr(AtomicTypeLiteral('foo'), 'bar', [AtomicTypeLiteral('int')]) is the type 'foo::bar<int>'.

@dataclass(frozen=True)
class TemplateMemberAccessExpr(Expr):
    expr_type: ExprType = field(init=False)
    class_type_expr: Expr
    member_name: str
    arg_list_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(TypeType())

        assert self.class_type_expr.expr_type == TypeType()
        assert self.arg_list_expr.expr_type == ListType(TypeType())

@dataclass(frozen=True)
class ListExpr(Expr):
    expr_type: ExprType = field(init=False)
    elem_type: ExprType
    elem_exprs: Tuple[Expr, ...]
    list_extraction_expr: Optional[VarReference]

    def __post_init__(self) -> None:
        self._init_expr_type(ListType(self.elem_type))
        assert not isinstance(self.elem_type, FunctionType)

@dataclass(frozen=True)
class SetExpr(Expr):
    expr_type: ExprType = field(init=False)
    elem_type: ExprType
    elem_exprs: Tuple[Expr, ...]

    def __post_init__(self) -> None:
        self._init_expr_type(SetType(self.elem_type))
        assert not isinstance(self.elem_type, FunctionType)

@dataclass(frozen=True)
class IntListSumExpr(Expr):
    expr_type: ExprType = field(init=False)
    list_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(IntType())
        assert isinstance(self.list_expr.expr_type, ListType)
        assert isinstance(self.list_expr.expr_type.elem_type, IntType)

@dataclass(frozen=True)
class IntSetSumExpr(Expr):
    expr_type: ExprType = field(init=False)
    set_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(IntType())
        assert isinstance(self.set_expr.expr_type, SetType)
        assert isinstance(self.set_expr.expr_type.elem_type, IntType)

@dataclass(frozen=True)
class BoolListAllExpr(Expr):
    expr_type: ExprType = field(init=False)
    list_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert isinstance(self.list_expr.expr_type, ListType)
        assert isinstance(self.list_expr.expr_type.elem_type, BoolType)

@dataclass(frozen=True)
class BoolSetAllExpr(Expr):
    expr_type: ExprType = field(init=False)
    set_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert isinstance(self.set_expr.expr_type, SetType)
        assert isinstance(self.set_expr.expr_type.elem_type, BoolType)

@dataclass(frozen=True)
class BoolListAnyExpr(Expr):
    expr_type: ExprType = field(init=False)
    list_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert isinstance(self.list_expr.expr_type, ListType)
        assert isinstance(self.list_expr.expr_type.elem_type, BoolType)

@dataclass(frozen=True)
class BoolSetAnyExpr(Expr):
    expr_type: ExprType = field(init=False)
    set_expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert isinstance(self.set_expr.expr_type, SetType)
        assert isinstance(self.set_expr.expr_type.elem_type, BoolType)

@dataclass(frozen=True)
class FunctionCall(Expr):
    expr_type: ExprType = field(init=False)
    fun_expr: Expr
    args: Tuple[Expr, ...]
    may_throw: bool

    def __post_init__(self) -> None:
        assert isinstance(self.fun_expr.expr_type, FunctionType)
        assert len(self.fun_expr.expr_type.argtypes) == len(self.args)
        self._init_expr_type(self.fun_expr.expr_type.returns)

@dataclass(frozen=True)
class EqualityComparison(Expr):
    expr_type: ExprType = field(init=False)
    lhs: Expr
    rhs: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert self.lhs.expr_type == self.rhs.expr_type
        assert not isinstance(self.lhs.expr_type, FunctionType)

@dataclass(frozen=True)
class InExpr(Expr):
    expr_type: ExprType = field(init=False)
    lhs: Expr
    rhs: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert isinstance(self.rhs.expr_type, (ListType, SetType))
        assert self.lhs.expr_type == self.rhs.expr_type.elem_type
        assert not isinstance(self.lhs.expr_type, FunctionType)

@dataclass(frozen=True)
class AttributeAccessExpr(Expr):
    expr: Expr
    attribute_name: str

    def __post_init__(self) -> None:
        assert isinstance(self.expr.expr_type, (TypeType, CustomType))

@dataclass(frozen=True)
class AndExpr(Expr):
    expr_type: ExprType = field(init=False)
    lhs: Expr
    rhs: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert self.lhs.expr_type == BoolType()
        assert self.rhs.expr_type == BoolType()

@dataclass(frozen=True)
class OrExpr(Expr):
    expr_type: ExprType = field(init=False)
    lhs: Expr
    rhs: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert self.lhs.expr_type == BoolType()
        assert self.rhs.expr_type == BoolType()

@dataclass(frozen=True)
class NotExpr(Expr):
    expr_type: ExprType = field(init=False)
    expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert self.expr.expr_type == BoolType()

@dataclass(frozen=True)
class IntLiteral(Expr):
    expr_type: ExprType = field(init=False)
    value: int

    def __post_init__(self) -> None:
        self._init_expr_type(IntType())

@dataclass(frozen=True)
class IntComparisonExpr(Expr):
    expr_type: ExprType = field(init=False)
    lhs: Expr
    rhs: Expr
    op: str

    def __post_init__(self) -> None:
        self._init_expr_type(BoolType())
        assert self.lhs.expr_type == IntType()
        assert self.rhs.expr_type == IntType()
        assert self.op in ('<', '>', '<=', '>=')

@dataclass(frozen=True)
class IntUnaryMinusExpr(Expr):
    expr_type: ExprType = field(init=False)
    expr: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(IntType())
        assert self.expr.expr_type == IntType()

@dataclass(frozen=True)
class IntBinaryOpExpr(Expr):
    expr_type: ExprType = field(init=False)
    lhs: Expr
    rhs: Expr
    op: str

    def __post_init__(self) -> None:
        self._init_expr_type(IntType())
        assert self.lhs.expr_type == IntType()
        assert self.rhs.expr_type == IntType()

@dataclass(frozen=True)
class ListConcatExpr(Expr):
    expr_type: ExprType = field(init=False)
    lhs: Expr
    rhs: Expr

    def __post_init__(self) -> None:
        self._init_expr_type(self.lhs.expr_type)
        assert isinstance(self.lhs.expr_type, ListType)
        assert self.lhs.expr_type == self.rhs.expr_type

@dataclass(frozen=True)
class ListComprehension(Expr):
    expr_type: ExprType = field(init=False)
    list_expr: Expr
    loop_var: VarReference
    result_elem_expr: Expr
    loop_body_start_branch: SourceBranch
    loop_exit_branch: SourceBranch

    def __post_init__(self) -> None:
        self._init_expr_type(ListType(self.result_elem_expr.expr_type))

@dataclass(frozen=True)
class SetComprehension(Expr):
    expr_type: ExprType = field(init=False)
    set_expr: Expr
    loop_var: VarReference
    result_elem_expr: Expr
    loop_body_start_branch: SourceBranch
    loop_exit_branch: SourceBranch

    def __post_init__(self) -> None:
        self._init_expr_type(SetType(self.result_elem_expr.expr_type))
        assert isinstance(self.set_expr.expr_type, SetType)

@dataclass(frozen=True)
class Stmt:
    pass

@dataclass(frozen=True)
class PassStmt(Stmt):
    source_branch: SourceBranch

@dataclass(frozen=True)
class Assert(Stmt):
    expr: Expr
    message: str
    source_branch: SourceBranch

    def __post_init__(self) -> None:
        assert isinstance(self.expr.expr_type, BoolType)

@dataclass(frozen=True)
class Assignment(Stmt):
    lhs: VarReference
    rhs: Expr
    source_branch: SourceBranch

    def __post_init__(self) -> None:
        assert self.lhs.expr_type == self.rhs.expr_type

@dataclass(frozen=True)
class UnpackingAssignment(Stmt):
    lhs_list: Tuple[VarReference, ...]
    rhs: Expr
    error_message: str
    source_branch: SourceBranch

    def __post_init__(self) -> None:
        assert isinstance(self.rhs.expr_type, ListType)
        assert self.lhs_list
        for lhs in self.lhs_list:
            assert lhs.expr_type == self.rhs.expr_type.elem_type

@dataclass(frozen=True)
class ReturnStmt(Stmt):
    expr: Expr
    source_branch: SourceBranch

@dataclass(frozen=True)
class IfStmt(Stmt):
    cond_expr: Expr
    if_stmts: Tuple[Stmt, ...]
    else_stmts: Tuple[Stmt, ...]

    def __post_init__(self) -> None:
        assert self.cond_expr.expr_type == BoolType()

@dataclass(frozen=True)
class RaiseStmt(Stmt):
    expr: Expr
    source_branch: SourceBranch

    def __post_init__(self) -> None:
        assert isinstance(self.expr.expr_type, CustomType)
        assert self.expr.expr_type.is_exception_class

@dataclass(frozen=True)
class TryExcept(Stmt):
    try_body: Tuple[Stmt, ...]
    caught_exception_type: ExprType
    caught_exception_name: str
    except_body: Tuple[Stmt, ...]
    try_branch: SourceBranch
    except_branch: SourceBranch

@dataclass(frozen=True)
class FunctionDefn:
    name: str
    args: Tuple[FunctionArgDecl, ...]
    body: Tuple[Stmt, ...]
    return_type: ExprType

@dataclass(frozen=True)
class Module:
    function_defns: Tuple[FunctionDefn, ...]
    assertions: Tuple[Assert, ...]
    custom_types: Tuple[CustomType, ...]
    public_names: FrozenSet[str]
    pass_stmts: Tuple[PassStmt, ...]
    public_names: FrozenSet[str]
