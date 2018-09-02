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

from typing import List, Iterable, Optional, Dict, Set
from _py2tmp import utils

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

class FunctionType(ExprType):
    def __init__(self, argtypes: List[ExprType], returns: ExprType):
        self.argtypes = argtypes
        self.returns = returns

    def __str__(self):
        return "(%s) -> %s" % (
            ', '.join(str(arg)
                      for arg in self.argtypes),
            str(self.returns))

class ListType(ExprType):
    def __init__(self, elem_type: ExprType):
        assert not isinstance(elem_type, FunctionType)
        self.elem_type = elem_type

    def __str__(self):
        return "List[%s]" % str(self.elem_type)

class SetType(ExprType):
    def __init__(self, elem_type: ExprType):
        assert not isinstance(elem_type, FunctionType)
        self.elem_type = elem_type

    def __str__(self):
        return "Set[%s]" % str(self.elem_type)

class CustomTypeArgDecl:
    def __init__(self, name: str, type: ExprType):
        self.name = name
        self.type = type

class CustomType(ExprType):
    def __init__(self,
                 name: str,
                 arg_types: List[CustomTypeArgDecl],
                 is_exception_class: bool,
                 exception_message: Optional[str]):
        assert (exception_message is not None) == is_exception_class
        self.name = name
        self.arg_types = arg_types
        self.is_exception_class = is_exception_class
        self.exception_message = exception_message

    def __str__(self):
        return self.name

class Expr:
    def __init__(self, type: ExprType):
        self.type = type

    # Note: it's the caller's responsibility to de-duplicate VarReference objects that reference the same symbol, if
    # desired.
    def get_free_variables(self) -> 'Iterable[VarReference]': ...  # pragma: no cover

class FunctionArgDecl:
    def __init__(self, type: ExprType, name: str = ''):
        self.type = type
        self.name = name

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

class MatchCase:
    def __init__(self, matched_var_names: Set[str], type_patterns: List[Expr], expr: Expr):
        self.matched_var_names = matched_var_names
        self.type_patterns = type_patterns
        self.expr = expr

    def is_main_definition(self):
        matched_var_names_set = set(self.matched_var_names)
        return all(isinstance(pattern, VarReference) and pattern.name in matched_var_names_set
                   for pattern in self.type_patterns)

class MatchExpr(Expr):
    def __init__(self, matched_exprs: List[Expr], match_cases: List[MatchCase]):
        assert matched_exprs
        assert match_cases
        for match_case in match_cases:
            assert len(match_case.type_patterns) == len(matched_exprs)
            assert match_case.expr.type == match_cases[0].expr.type
        super().__init__(type=match_cases[0].expr.type)
        self.matched_exprs = matched_exprs
        self.match_cases = match_cases

        assert len([match_case
                    for match_case in match_cases
                    if match_case.is_main_definition()]) <= 1

    def get_free_variables(self):
        for expr in self.matched_exprs:
            for var in expr.get_free_variables():
                yield var
        for match_case in self.match_cases:
            local_vars = set(match_case.matched_var_names)
            for var in match_case.expr.get_free_variables():
                if var.name not in local_vars:
                    yield var

class BoolLiteral(Expr):
    def __init__(self, value: bool):
        super().__init__(BoolType())
        self.value = value

    def get_free_variables(self):
        if False:
            yield  # pragma: no cover

class AtomicTypeLiteral(Expr):
    def __init__(self, cpp_type: str):
        super().__init__(type=TypeType())
        self.cpp_type = cpp_type

    def get_free_variables(self):
        if False:
            yield  # pragma: no cover

class PointerTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(type=TypeType())
        assert type_expr.type == TypeType()
        self.type_expr = type_expr

    def get_free_variables(self):
        for var in self.type_expr.get_free_variables():
            yield var

class ReferenceTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(type=TypeType())
        assert type_expr.type == TypeType()
        self.type_expr = type_expr

    def get_free_variables(self):
        for var in self.type_expr.get_free_variables():
            yield var

class RvalueReferenceTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(type=TypeType())
        assert type_expr.type == TypeType()
        self.type_expr = type_expr

    def get_free_variables(self):
        for var in self.type_expr.get_free_variables():
            yield var

class ConstTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(type=TypeType())
        assert type_expr.type == TypeType()
        self.type_expr = type_expr

    def get_free_variables(self):
        for var in self.type_expr.get_free_variables():
            yield var

class ArrayTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(type=TypeType())
        assert type_expr.type == TypeType()
        self.type_expr = type_expr

    def get_free_variables(self):
        for var in self.type_expr.get_free_variables():
            yield var

class FunctionTypeExpr(Expr):
    def __init__(self, return_type_expr: Expr, arg_list_expr: Expr):
        assert return_type_expr.type == TypeType()
        assert arg_list_expr.type == ListType(TypeType())

        super().__init__(type=TypeType())
        self.return_type_expr = return_type_expr
        self.arg_list_expr = arg_list_expr

    def get_free_variables(self):
        for expr in (self.return_type_expr, self.arg_list_expr):
            for var in expr.get_free_variables():
                yield var

# E.g. TemplateInstantiationExpr('std::vector', [AtomicTypeLiteral('int')]) is the type 'std::vector<int>'.
class TemplateInstantiationExpr(Expr):
    def __init__(self, template_atomic_cpp_type: str, arg_list_expr: Expr):
        assert arg_list_expr.type == ListType(TypeType())

        super().__init__(type=TypeType())
        self.template_atomic_cpp_type = template_atomic_cpp_type
        self.arg_list_expr = arg_list_expr

    def get_free_variables(self):
        for var in self.arg_list_expr.get_free_variables():
            yield var

# E.g. TemplateMemberAccessExpr(AtomicTypeLiteral('foo'), 'bar', [AtomicTypeLiteral('int')]) is the type 'foo::bar<int>'.
class TemplateMemberAccessExpr(Expr):
    def __init__(self, class_type_expr: Expr, member_name: str, arg_list_expr: Expr):
        assert class_type_expr.type == TypeType()
        assert arg_list_expr.type == ListType(TypeType())

        super().__init__(type=TypeType())
        self.class_type_expr = class_type_expr
        self.member_name = member_name
        self.arg_list_expr = arg_list_expr

    def get_free_variables(self):
        for expr in (self.class_type_expr, self.arg_list_expr):
            for var in expr.get_free_variables():
                yield var

class ListExpr(Expr):
    def __init__(self, elem_type: ExprType, elem_exprs: List[Expr]):
        assert not isinstance(elem_type, FunctionType)
        super().__init__(type=ListType(elem_type))
        self.elem_type = elem_type
        self.elem_exprs = elem_exprs

    def get_free_variables(self):
        for expr in self.elem_exprs:
            for var in expr.get_free_variables():
                yield var

class SetExpr(Expr):
    def __init__(self, elem_type: ExprType, elem_exprs: List[Expr]):
        assert not isinstance(elem_type, FunctionType)
        super().__init__(type=SetType(elem_type))
        self.elem_type = elem_type
        self.elem_exprs = elem_exprs

    def get_free_variables(self):
        for expr in self.elem_exprs:
            for var in expr.get_free_variables():
                yield var

class IntListSumExpr(Expr):
    def __init__(self, list_expr: Expr):
        assert isinstance(list_expr.type, ListType)
        assert isinstance(list_expr.type.elem_type, IntType)
        super().__init__(type=IntType())
        self.list_expr = list_expr

    def get_free_variables(self):
        for var in self.list_expr.get_free_variables():
            yield var

class IntSetSumExpr(Expr):
    def __init__(self, set_expr: Expr):
        assert isinstance(set_expr.type, SetType)
        assert isinstance(set_expr.type.elem_type, IntType)
        super().__init__(type=IntType())
        self.set_expr = set_expr

    def get_free_variables(self):
        for var in self.set_expr.get_free_variables():
            yield var

class BoolListAllExpr(Expr):
    def __init__(self, list_expr: Expr):
        assert isinstance(list_expr.type, ListType)
        assert isinstance(list_expr.type.elem_type, BoolType)
        super().__init__(type=BoolType())
        self.list_expr = list_expr

    def get_free_variables(self):
        for var in self.list_expr.get_free_variables():
            yield var

class BoolSetAllExpr(Expr):
    def __init__(self, set_expr: Expr):
        assert isinstance(set_expr.type, SetType)
        assert isinstance(set_expr.type.elem_type, BoolType)
        super().__init__(type=BoolType())
        self.set_expr = set_expr

    def get_free_variables(self):
        for var in self.set_expr.get_free_variables():
            yield var

class BoolListAnyExpr(Expr):
    def __init__(self, list_expr: Expr):
        assert isinstance(list_expr.type, ListType)
        assert isinstance(list_expr.type.elem_type, BoolType)
        super().__init__(type=BoolType())
        self.list_expr = list_expr

    def get_free_variables(self):
        for var in self.list_expr.get_free_variables():
            yield var

class BoolSetAnyExpr(Expr):
    def __init__(self, set_expr: Expr):
        assert isinstance(set_expr.type, SetType)
        assert isinstance(set_expr.type.elem_type, BoolType)
        super().__init__(type=BoolType())
        self.set_expr = set_expr

    def get_free_variables(self):
        for var in self.set_expr.get_free_variables():
            yield var

class FunctionCall(Expr):
    def __init__(self,
                 fun_expr: Expr,
                 args: List[Expr],
                 may_throw: bool):
        assert isinstance(fun_expr.type, FunctionType)
        assert len(fun_expr.type.argtypes) == len(args)
        super().__init__(type=fun_expr.type.returns)
        self.fun_expr = fun_expr
        self.args = args
        self.may_throw = may_throw

    def get_free_variables(self):
        for var in self.fun_expr.get_free_variables():
            yield var
        for expr in self.args:
            for var in expr.get_free_variables():
                yield var

class EqualityComparison(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        super().__init__(type=BoolType())
        assert lhs.type == rhs.type
        assert not isinstance(lhs.type, FunctionType)
        self.lhs = lhs
        self.rhs = rhs

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

class AttributeAccessExpr(Expr):
    def __init__(self, expr: Expr, attribute_name: str, type: ExprType):
        super().__init__(type=type)
        assert isinstance(expr.type, (TypeType, CustomType))
        self.expr = expr
        self.attribute_name = attribute_name

    def get_free_variables(self):
        for var in self.expr.get_free_variables():
            yield var

class AndExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        assert lhs.type == BoolType()
        assert rhs.type == BoolType()
        super().__init__(type=BoolType())
        self.lhs = lhs
        self.rhs = rhs

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

class OrExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        assert lhs.type == BoolType()
        assert rhs.type == BoolType()
        super().__init__(type=BoolType())
        self.lhs = lhs
        self.rhs = rhs

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

class NotExpr(Expr):
    def __init__(self, expr: Expr):
        assert expr.type == BoolType()
        super().__init__(type=BoolType())
        self.expr = expr

    def get_free_variables(self):
        for var in self.expr.get_free_variables():
            yield var

class IntLiteral(Expr):
    def __init__(self, value: int):
        super().__init__(type=IntType())
        self.value = value

    def get_free_variables(self):
        if False:
            yield  # pragma: no cover

class IntComparisonExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr, op: str):
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

class IntUnaryMinusExpr(Expr):
    def __init__(self, expr: Expr):
        assert expr.type == IntType()
        super().__init__(type=IntType())
        self.expr = expr

    def get_free_variables(self):
        for var in self.expr.get_free_variables():
            yield var

class IntBinaryOpExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr, op: str):
        assert lhs.type == IntType()
        assert rhs.type == IntType()
        super().__init__(type=IntType())
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

class ListConcatExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        assert isinstance(lhs.type, ListType)
        assert lhs.type == rhs.type
        super().__init__(type=lhs.type)
        self.lhs = lhs
        self.rhs = rhs

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

class ListComprehension(Expr):
    def __init__(self,
                 list_expr: Expr,
                 loop_var: VarReference,
                 result_elem_expr: Expr):
        super().__init__(type=ListType(result_elem_expr.type))
        self.list_expr = list_expr
        self.loop_var = loop_var
        self.result_elem_expr = result_elem_expr

    def get_free_variables(self):
        for var in self.list_expr.get_free_variables():
            yield var
        for var in self.result_elem_expr.get_free_variables():
            if var.name != self.loop_var.name:
                yield var

class SetComprehension(Expr):
    def __init__(self,
                 set_expr: Expr,
                 loop_var: VarReference,
                 result_elem_expr: Expr):
        assert isinstance(set_expr.type, SetType)
        super().__init__(type=SetType(result_elem_expr.type))
        self.set_expr = set_expr
        self.loop_var = loop_var
        self.result_elem_expr = result_elem_expr

    def get_free_variables(self):
        for var in self.set_expr.get_free_variables():
            yield var
        for var in self.result_elem_expr.get_free_variables():
            if var.name != self.loop_var.name:
                yield var

class ReturnTypeInfo:
    def __init__(self, type: Optional[ExprType], always_returns: bool):
        # When expr_type is None, the statement never returns.
        # expr_type can't be None if always_returns is True.
        self.type = type
        self.always_returns = always_returns

class Stmt:
    def get_return_type(self) -> ReturnTypeInfo: ...  # pragma: no cover

class Assert(Stmt):
    def __init__(self, expr: Expr, message: str):
        assert isinstance(expr.type, BoolType)
        self.expr = expr
        self.message = message

    def get_return_type(self):
        return ReturnTypeInfo(type=None, always_returns=False)

class Assignment(Stmt):
    def __init__(self, lhs: VarReference, rhs: Expr):
        assert lhs.type == rhs.type
        self.lhs = lhs
        self.rhs = rhs

    def get_return_type(self):
        return ReturnTypeInfo(type=None, always_returns=False)

class UnpackingAssignment(Stmt):
    def __init__(self, lhs_list: List[VarReference], rhs: Expr, error_message: str):
        assert isinstance(rhs.type, ListType)
        assert lhs_list
        for lhs in lhs_list:
            assert lhs.type == rhs.type.elem_type
        self.lhs_list = lhs_list
        self.rhs = rhs
        self.error_message = error_message

    def get_return_type(self):
        return ReturnTypeInfo(type=None, always_returns=False)

class ReturnStmt(Stmt):
    def __init__(self, expr: Expr):
        self.expr = expr

    def get_return_type(self):
        return ReturnTypeInfo(type=self.expr.type, always_returns=True)

def _combine_return_type_of_branches(branch1_stmts: List[Stmt], branch2_stmts: List[Stmt]):
    if branch1_stmts:
        branch1_return_type_info = branch1_stmts[-1].get_return_type()
    else:
        branch1_return_type_info = ReturnTypeInfo(type=None, always_returns=False)
    if branch2_stmts:
        branch2_return_type_info = branch2_stmts[-1].get_return_type()
    else:
        branch2_return_type_info = ReturnTypeInfo(type=None, always_returns=False)

    if branch1_return_type_info.type:
        assert not branch2_return_type_info.type or branch1_return_type_info.type == branch2_return_type_info.type
        type = branch1_return_type_info.type
    elif branch2_return_type_info.type:
        type = branch2_return_type_info.type
    else:
        type = None
    return ReturnTypeInfo(type=type,
                          always_returns=branch1_return_type_info.always_returns and branch2_return_type_info.always_returns)

class IfStmt(Stmt):
    def __init__(self, cond_expr: Expr, if_stmts: List[Stmt], else_stmts: List[Stmt]):
        assert cond_expr.type == BoolType()
        self.cond_expr = cond_expr
        self.if_stmts = if_stmts
        self.else_stmts = else_stmts

    def get_return_type(self):
        return _combine_return_type_of_branches(self.if_stmts, self.else_stmts)

class RaiseStmt(Stmt):
    def __init__(self, expr: Expr):
        assert isinstance(expr.type, CustomType)
        assert expr.type.is_exception_class
        self.expr = expr

    def get_return_type(self):
        return ReturnTypeInfo(type=None, always_returns=True)

class TryExcept(Stmt):
    def __init__(self,
                 try_body: List[Stmt],
                 caught_exception_type: ExprType,
                 caught_exception_name: str,
                 except_body: List[Stmt]):
        self.try_body = try_body
        self.caught_exception_type = caught_exception_type
        self.caught_exception_name = caught_exception_name
        self.except_body = except_body

    def get_return_type(self):
        return _combine_return_type_of_branches(self.try_body, self.except_body)

class FunctionDefn:
    def __init__(self,
                 name: str,
                 args: List[FunctionArgDecl],
                 body: List[Stmt],
                 return_type: ExprType):
        self.name = name
        self.args = args
        self.body = body
        self.return_type = return_type

class Module:
    def __init__(self,
                 function_defns: List[FunctionDefn],
                 assertions: List[Assert],
                 custom_types: List[CustomType],
                 public_names: Set[str]):
        self.function_defns = function_defns
        self.assertions = assertions
        self.custom_types = custom_types
        self.public_names = public_names
