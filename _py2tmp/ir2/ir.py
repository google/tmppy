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

from typing import List, Optional, Set

from _py2tmp.utils import ValueType


class ExprType(ValueType):
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
    def __init__(self, name: str, expr_type: ExprType):
        self.name = name
        self.expr_type = expr_type

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
    def __init__(self, expr_type: ExprType):
        self.expr_type = expr_type

class FunctionArgDecl:
    def __init__(self, expr_type: ExprType, name: str = ''):
        self.expr_type = expr_type
        self.name = name

class VarReference(Expr):
    def __init__(self,
                 expr_type: ExprType,
                 name: str,
                 is_global_function: bool,
                 is_function_that_may_throw: bool,
                 source_module: Optional[str] = None):
        super().__init__(expr_type=expr_type)
        assert name
        self.name = name
        self.is_global_function = is_global_function
        self.is_function_that_may_throw = is_function_that_may_throw
        self.source_module = source_module

class MatchCase:
    def __init__(self, matched_var_names: Set[str], matched_variadic_var_names: Set[str], type_patterns: List[Expr], expr: Expr):
        self.matched_var_names = matched_var_names
        self.matched_variadic_var_names = matched_variadic_var_names
        self.type_patterns = type_patterns
        self.expr = expr

    def is_main_definition(self):
        matched_var_names_set = set(self.matched_var_names).union(self.matched_variadic_var_names)
        return all(isinstance(pattern, VarReference) and pattern.name in matched_var_names_set
                   for pattern in self.type_patterns)

class MatchExpr(Expr):
    def __init__(self, matched_exprs: List[Expr], match_cases: List[MatchCase]):
        assert matched_exprs
        assert match_cases
        for match_case in match_cases:
            assert len(match_case.type_patterns) == len(matched_exprs)
            assert match_case.expr.expr_type == match_cases[0].expr.expr_type
        super().__init__(expr_type=match_cases[0].expr.expr_type)
        self.matched_exprs = matched_exprs
        self.match_cases = match_cases

        assert len([match_case
                    for match_case in match_cases
                    if match_case.is_main_definition()]) <= 1

class BoolLiteral(Expr):
    def __init__(self, value: bool):
        super().__init__(BoolType())
        self.value = value

class AtomicTypeLiteral(Expr):
    def __init__(self, cpp_type: str):
        super().__init__(expr_type=TypeType())
        self.cpp_type = cpp_type

class PointerTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

class ReferenceTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

class RvalueReferenceTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

class ConstTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

class ArrayTypeExpr(Expr):
    def __init__(self, type_expr: Expr):
        super().__init__(expr_type=TypeType())
        assert type_expr.expr_type == TypeType()
        self.type_expr = type_expr

class FunctionTypeExpr(Expr):
    def __init__(self, return_type_expr: Expr, arg_list_expr: Expr):
        assert return_type_expr.expr_type == TypeType()
        assert arg_list_expr.expr_type == ListType(TypeType())

        super().__init__(expr_type=TypeType())
        self.return_type_expr = return_type_expr
        self.arg_list_expr = arg_list_expr

# E.g. TemplateInstantiationExpr('std::vector', [AtomicTypeLiteral('int')]) is the type 'std::vector<int>'.
class TemplateInstantiationExpr(Expr):
    def __init__(self, template_atomic_cpp_type: str, arg_list_expr: Expr):
        assert arg_list_expr.expr_type == ListType(TypeType())

        super().__init__(expr_type=TypeType())
        self.template_atomic_cpp_type = template_atomic_cpp_type
        self.arg_list_expr = arg_list_expr

# E.g. TemplateMemberAccessExpr(AtomicTypeLiteral('foo'), 'bar', [AtomicTypeLiteral('int')]) is the type 'foo::bar<int>'.
class TemplateMemberAccessExpr(Expr):
    def __init__(self, class_type_expr: Expr, member_name: str, arg_list_expr: Expr):
        assert class_type_expr.expr_type == TypeType()
        assert arg_list_expr.expr_type == ListType(TypeType())

        super().__init__(expr_type=TypeType())
        self.class_type_expr = class_type_expr
        self.member_name = member_name
        self.arg_list_expr = arg_list_expr

class ListExpr(Expr):
    def __init__(self, elem_type: ExprType, elem_exprs: List[Expr], list_extraction_expr: Optional[VarReference]):
        assert not isinstance(elem_type, FunctionType)
        super().__init__(expr_type=ListType(elem_type))
        self.elem_type = elem_type
        self.elem_exprs = elem_exprs
        self.list_extraction_expr = list_extraction_expr

class SetExpr(Expr):
    def __init__(self, elem_type: ExprType, elem_exprs: List[Expr]):
        assert not isinstance(elem_type, FunctionType)
        super().__init__(expr_type=SetType(elem_type))
        self.elem_type = elem_type
        self.elem_exprs = elem_exprs

class IntListSumExpr(Expr):
    def __init__(self, list_expr: Expr):
        assert isinstance(list_expr.expr_type, ListType)
        assert isinstance(list_expr.expr_type.elem_type, IntType)
        super().__init__(expr_type=IntType())
        self.list_expr = list_expr

class IntSetSumExpr(Expr):
    def __init__(self, set_expr: Expr):
        assert isinstance(set_expr.expr_type, SetType)
        assert isinstance(set_expr.expr_type.elem_type, IntType)
        super().__init__(expr_type=IntType())
        self.set_expr = set_expr

class BoolListAllExpr(Expr):
    def __init__(self, list_expr: Expr):
        assert isinstance(list_expr.expr_type, ListType)
        assert isinstance(list_expr.expr_type.elem_type, BoolType)
        super().__init__(expr_type=BoolType())
        self.list_expr = list_expr

class BoolSetAllExpr(Expr):
    def __init__(self, set_expr: Expr):
        assert isinstance(set_expr.expr_type, SetType)
        assert isinstance(set_expr.expr_type.elem_type, BoolType)
        super().__init__(expr_type=BoolType())
        self.set_expr = set_expr

class BoolListAnyExpr(Expr):
    def __init__(self, list_expr: Expr):
        assert isinstance(list_expr.expr_type, ListType)
        assert isinstance(list_expr.expr_type.elem_type, BoolType)
        super().__init__(expr_type=BoolType())
        self.list_expr = list_expr

class BoolSetAnyExpr(Expr):
    def __init__(self, set_expr: Expr):
        assert isinstance(set_expr.expr_type, SetType)
        assert isinstance(set_expr.expr_type.elem_type, BoolType)
        super().__init__(expr_type=BoolType())
        self.set_expr = set_expr

class FunctionCall(Expr):
    def __init__(self,
                 fun_expr: Expr,
                 args: List[Expr],
                 may_throw: bool):
        assert isinstance(fun_expr.expr_type, FunctionType)
        assert len(fun_expr.expr_type.argtypes) == len(args)
        super().__init__(expr_type=fun_expr.expr_type.returns)
        self.fun_expr = fun_expr
        self.args = args
        self.may_throw = may_throw

class EqualityComparison(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        super().__init__(expr_type=BoolType())
        assert lhs.expr_type == rhs.expr_type
        assert not isinstance(lhs.expr_type, FunctionType)
        self.lhs = lhs
        self.rhs = rhs

class InExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        super().__init__(expr_type=BoolType())
        assert isinstance(rhs.expr_type, (ListType, SetType))
        assert lhs.expr_type == rhs.expr_type.elem_type
        assert not isinstance(lhs.expr_type, FunctionType)
        self.lhs = lhs
        self.rhs = rhs

class AttributeAccessExpr(Expr):
    def __init__(self, expr: Expr, attribute_name: str, expr_type: ExprType):
        super().__init__(expr_type=expr_type)
        assert isinstance(expr.expr_type, (TypeType, CustomType))
        self.expr = expr
        self.attribute_name = attribute_name

class AndExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        assert lhs.expr_type == BoolType()
        assert rhs.expr_type == BoolType()
        super().__init__(expr_type=BoolType())
        self.lhs = lhs
        self.rhs = rhs

class OrExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        assert lhs.expr_type == BoolType()
        assert rhs.expr_type == BoolType()
        super().__init__(expr_type=BoolType())
        self.lhs = lhs
        self.rhs = rhs

class NotExpr(Expr):
    def __init__(self, expr: Expr):
        assert expr.expr_type == BoolType()
        super().__init__(expr_type=BoolType())
        self.expr = expr

class IntLiteral(Expr):
    def __init__(self, value: int):
        super().__init__(expr_type=IntType())
        self.value = value

class IntComparisonExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr, op: str):
        assert lhs.expr_type == IntType()
        assert rhs.expr_type == IntType()
        assert op in ('<', '>', '<=', '>=')
        super().__init__(expr_type=BoolType())
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

class IntUnaryMinusExpr(Expr):
    def __init__(self, expr: Expr):
        assert expr.expr_type == IntType()
        super().__init__(expr_type=IntType())
        self.expr = expr

class IntBinaryOpExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr, op: str):
        assert lhs.expr_type == IntType()
        assert rhs.expr_type == IntType()
        super().__init__(expr_type=IntType())
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

class ListConcatExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        assert isinstance(lhs.expr_type, ListType)
        assert lhs.expr_type == rhs.expr_type
        super().__init__(expr_type=lhs.expr_type)
        self.lhs = lhs
        self.rhs = rhs

class ListComprehension(Expr):
    def __init__(self,
                 list_expr: Expr,
                 loop_var: VarReference,
                 result_elem_expr: Expr):
        super().__init__(expr_type=ListType(result_elem_expr.expr_type))
        self.list_expr = list_expr
        self.loop_var = loop_var
        self.result_elem_expr = result_elem_expr

class SetComprehension(Expr):
    def __init__(self,
                 set_expr: Expr,
                 loop_var: VarReference,
                 result_elem_expr: Expr):
        assert isinstance(set_expr.expr_type, SetType)
        super().__init__(expr_type=SetType(result_elem_expr.expr_type))
        self.set_expr = set_expr
        self.loop_var = loop_var
        self.result_elem_expr = result_elem_expr

class Stmt:
    pass

class Assert(Stmt):
    def __init__(self, expr: Expr, message: str):
        assert isinstance(expr.expr_type, BoolType)
        self.expr = expr
        self.message = message

class Assignment(Stmt):
    def __init__(self, lhs: VarReference, rhs: Expr):
        assert lhs.expr_type == rhs.expr_type
        self.lhs = lhs
        self.rhs = rhs

class UnpackingAssignment(Stmt):
    def __init__(self, lhs_list: List[VarReference], rhs: Expr, error_message: str):
        assert isinstance(rhs.expr_type, ListType)
        assert lhs_list
        for lhs in lhs_list:
            assert lhs.expr_type == rhs.expr_type.elem_type
        self.lhs_list = lhs_list
        self.rhs = rhs
        self.error_message = error_message

class ReturnStmt(Stmt):
    def __init__(self, expr: Expr):
        self.expr = expr

class IfStmt(Stmt):
    def __init__(self, cond_expr: Expr, if_stmts: List[Stmt], else_stmts: List[Stmt]):
        assert cond_expr.expr_type == BoolType()
        self.cond_expr = cond_expr
        self.if_stmts = if_stmts
        self.else_stmts = else_stmts

class RaiseStmt(Stmt):
    def __init__(self, expr: Expr):
        assert isinstance(expr.expr_type, CustomType)
        assert expr.expr_type.is_exception_class
        self.expr = expr

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
