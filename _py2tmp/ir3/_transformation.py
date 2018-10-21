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

from typing import List
from _py2tmp.ir3 import ir as ir3


class Transformation:
    def transform_module(self, module: ir3.Module) -> ir3.Module:
        return ir3.Module(function_defns=[self.transform_function_defn(function_defn)
                                          for function_defn in module.function_defns],
                          assertions=[self.transform_assert(assertion)
                                      for assertion in module.assertions],
                          custom_types=module.custom_types,
                          public_names=module.public_names)

    def transform_function_defn(self, function_defn: ir3.FunctionDefn) -> ir3.FunctionDefn:
        return ir3.FunctionDefn(name=function_defn.name,
                                args=[self.transform_function_arg_decl(arg)
                                      for arg in function_defn.args],
                                body=self.transform_stmts(function_defn.body),
                                return_type=function_defn.return_type)

    def transform_function_arg_decl(self, arg_decl: ir3.FunctionArgDecl):
        return arg_decl

    def transform_stmts(self, stmts: List[ir3.Stmt]) -> List[ir3.Stmt]:
        return [self.transform_stmt(stmt)
                for stmt in stmts]

    def transform_stmt(self, stmt: ir3.Stmt) -> ir3.Stmt:
        if isinstance(stmt, ir3.TryExcept):
            return self.transform_try_except(stmt)
        elif isinstance(stmt, ir3.RaiseStmt):
            return self.transform_raise_stmt(stmt)
        elif isinstance(stmt, ir3.IfStmt):
            return self.transform_if_stmt(stmt)
        elif isinstance(stmt, ir3.ReturnStmt):
            return self.transform_return_stmt(stmt)
        elif isinstance(stmt, ir3.UnpackingAssignment):
            return self.transform_unpacking_assignment(stmt)
        elif isinstance(stmt, ir3.Assignment):
            return self.transform_assignment(stmt)
        elif isinstance(stmt, ir3.Assert):
            return self.transform_assert(stmt)
        else:
            raise NotImplementedError('Unexpected stmt: %s' % stmt.__class__.__name__)

    def transform_try_except(self, try_except: ir3.TryExcept) -> ir3.TryExcept:
        return ir3.TryExcept(try_body=self.transform_stmts(try_except.try_body),
                             except_body=self.transform_stmts(try_except.except_body),
                             caught_exception_name=try_except.caught_exception_name,
                             caught_exception_type=try_except.caught_exception_type)


    def transform_raise_stmt(self, stmt: ir3.RaiseStmt) -> ir3.RaiseStmt:
        return ir3.RaiseStmt(expr=self.transform_expr(stmt.expr))

    def transform_if_stmt(self, stmt: ir3.IfStmt) -> ir3.IfStmt:
        return ir3.IfStmt(cond_expr=self.transform_expr(stmt.cond_expr),
                          if_stmts=self.transform_stmts(stmt.if_stmts),
                          else_stmts=self.transform_stmts(stmt.else_stmts))

    def transform_return_stmt(self, stmt: ir3.ReturnStmt) -> ir3.ReturnStmt:
        return ir3.ReturnStmt(expr=self.transform_expr(stmt.expr))

    def transform_unpacking_assignment(self, assignment: ir3.UnpackingAssignment) -> ir3.UnpackingAssignment:
        return ir3.UnpackingAssignment(lhs_list=[self.transform_var_reference(var)
                                                 for var in assignment.lhs_list],
                                       rhs=self.transform_expr(assignment.rhs),
                                       error_message=assignment.error_message)

    def transform_assignment(self, assignment: ir3.Assignment) -> ir3.Assignment:
        return ir3.Assignment(lhs=self.transform_var_reference(assignment.lhs),
                              rhs=self.transform_expr(assignment.rhs))

    def transform_assert(self, stmt: ir3.Assert) -> ir3.Assert:
        return ir3.Assert(expr=self.transform_expr(stmt.expr),
                          message=stmt.message)

    def transform_expr(self, expr: ir3.Expr) -> ir3.Expr:
        if isinstance(expr, ir3.SetComprehension):
            return self.transform_set_comprehension(expr)
        elif isinstance(expr, ir3.ListComprehension):
            return self.transform_list_comprehension(expr)
        elif isinstance(expr, ir3.ListConcatExpr):
            return self.transform_list_concat_expr(expr)
        elif isinstance(expr, ir3.IntBinaryOpExpr):
            return self.transform_int_binary_op_expr(expr)
        elif isinstance(expr, ir3.IntUnaryMinusExpr):
            return self.transform_int_unary_minus_expr(expr)
        elif isinstance(expr, ir3.IntComparisonExpr):
            return self.transform_int_comparison_expr(expr)
        elif isinstance(expr, ir3.IntLiteral):
            return self.transform_int_literal_expr(expr)
        elif isinstance(expr, ir3.NotExpr):
            return self.transform_not_expr(expr)
        elif isinstance(expr, ir3.OrExpr):
            return self.transform_or_expr(expr)
        elif isinstance(expr, ir3.AndExpr):
            return self.transform_and_expr(expr)
        elif isinstance(expr, ir3.AttributeAccessExpr):
            return self.transform_attribute_access_expr(expr)
        elif isinstance(expr, ir3.EqualityComparison):
            return self.transform_equality_comparison(expr)
        elif isinstance(expr, ir3.InExpr):
            return self.transform_in_expr(expr)
        elif isinstance(expr, ir3.FunctionCall):
            return self.transform_function_call(expr)
        elif isinstance(expr, ir3.BoolSetAnyExpr):
            return self.transform_bool_set_any_expr(expr)
        elif isinstance(expr, ir3.BoolSetAllExpr):
            return self.transform_bool_set_all_expr(expr)
        elif isinstance(expr, ir3.BoolListAnyExpr):
            return self.transform_bool_list_any_expr(expr)
        elif isinstance(expr, ir3.BoolListAllExpr):
            return self.transform_bool_list_all_expr(expr)
        elif isinstance(expr, ir3.IntSetSumExpr):
            return self.transform_int_set_sum_expr(expr)
        elif isinstance(expr, ir3.IntListSumExpr):
            return self.transform_int_list_sum_expr(expr)
        elif isinstance(expr, ir3.SetExpr):
            return self.transform_set_expr(expr)
        elif isinstance(expr, ir3.ListExpr):
            return self.transform_list_expr(expr)
        elif isinstance(expr, ir3.AtomicTypeLiteral):
            return self.transform_atomic_type_literal_expr(expr)
        elif isinstance(expr, ir3.BoolLiteral):
            return self.transform_bool_literal_expr(expr)
        elif isinstance(expr, ir3.MatchExpr):
            return self.transform_match_expr(expr)
        elif isinstance(expr, ir3.VarReference):
            return self.transform_var_reference(expr)
        elif isinstance(expr, ir3.PointerTypeExpr):
            return self.transform_pointer_type_expr(expr)
        elif isinstance(expr, ir3.ReferenceTypeExpr):
            return self.transform_reference_type_expr(expr)
        elif isinstance(expr, ir3.RvalueReferenceTypeExpr):
            return self.transform_rvalue_reference_type_expr(expr)
        elif isinstance(expr, ir3.ConstTypeExpr):
            return self.transform_const_type_expr(expr)
        elif isinstance(expr, ir3.ArrayTypeExpr):
            return self.transform_array_type_expr(expr)
        elif isinstance(expr, ir3.FunctionTypeExpr):
            return self.transform_function_type_expr(expr)
        elif isinstance(expr, ir3.TemplateInstantiationExpr):
            return self.transform_template_instantiation_expr(expr)
        elif isinstance(expr, ir3.TemplateMemberAccessExpr):
            return self.transform_template_member_access_expr(expr)
        else:
            raise NotImplementedError('Unexpected expression: %s' % expr.__class__.__name__)

    def transform_set_comprehension(self, comprehension: ir3.SetComprehension) -> ir3.SetComprehension:
        return ir3.SetComprehension(set_expr=self.transform_expr(comprehension.set_expr),
                                    loop_var=self.transform_var_reference(comprehension.loop_var),
                                    result_elem_expr=self.transform_expr(comprehension.result_elem_expr))

    def transform_list_comprehension(self, comprehension: ir3.ListComprehension) -> ir3.ListComprehension:
        return ir3.ListComprehension(list_expr=self.transform_expr(comprehension.list_expr),
                                     loop_var=self.transform_var_reference(comprehension.loop_var),
                                     result_elem_expr=self.transform_expr(comprehension.result_elem_expr))

    def transform_list_concat_expr(self, expr: ir3.ListConcatExpr) -> ir3.ListConcatExpr:
        return ir3.ListConcatExpr(lhs=self.transform_expr(expr.lhs),
                                  rhs=self.transform_expr(expr.rhs))

    def transform_int_binary_op_expr(self, expr: ir3.IntBinaryOpExpr) -> ir3.IntBinaryOpExpr:
        return ir3.IntBinaryOpExpr(lhs=self.transform_expr(expr.lhs),
                                   rhs=self.transform_expr(expr.rhs),
                                   op=expr.op)

    def transform_int_unary_minus_expr(self, expr: ir3.IntUnaryMinusExpr) -> ir3.IntUnaryMinusExpr:
        return ir3.IntUnaryMinusExpr(expr=self.transform_expr(expr.expr))

    def transform_int_comparison_expr(self, expr: ir3.IntComparisonExpr) -> ir3.IntComparisonExpr:
        return ir3.IntComparisonExpr(lhs=self.transform_expr(expr.lhs),
                                     rhs=self.transform_expr(expr.rhs),
                                     op=expr.op)

    def transform_int_literal_expr(self, expr: ir3.IntLiteral) -> ir3.IntLiteral:
        return expr

    def transform_not_expr(self, expr: ir3.NotExpr) -> ir3.NotExpr:
        return ir3.NotExpr(expr=self.transform_expr(expr.expr))

    def transform_or_expr(self, expr: ir3.OrExpr) -> ir3.OrExpr:
        return ir3.OrExpr(lhs=self.transform_expr(expr.lhs),
                          rhs=self.transform_expr(expr.rhs))

    def transform_and_expr(self, expr: ir3.AndExpr) -> ir3.AndExpr:
        return ir3.AndExpr(lhs=self.transform_expr(expr.lhs),
                           rhs=self.transform_expr(expr.rhs))

    def transform_attribute_access_expr(self, expr: ir3.AttributeAccessExpr) -> ir3.AttributeAccessExpr:
        return ir3.AttributeAccessExpr(expr=self.transform_expr(expr.expr),
                                       attribute_name=expr.attribute_name,
                                       expr_type=expr.expr_type)

    def transform_equality_comparison(self, expr: ir3.EqualityComparison) -> ir3.EqualityComparison:
        return ir3.EqualityComparison(lhs=self.transform_expr(expr.lhs),
                                      rhs=self.transform_expr(expr.rhs))

    def transform_in_expr(self, expr: ir3.InExpr) -> ir3.InExpr:
        return ir3.InExpr(lhs=self.transform_expr(expr.lhs),
                          rhs=self.transform_expr(expr.rhs))

    def transform_function_call(self, expr: ir3.FunctionCall) -> ir3.FunctionCall:
        return ir3.FunctionCall(fun_expr=self.transform_expr(expr.fun_expr),
                                args=[self.transform_expr(arg)
                                      for arg in expr.args],
                                may_throw=expr.may_throw)

    def transform_bool_set_any_expr(self, expr: ir3.BoolSetAnyExpr) -> ir3.BoolSetAnyExpr:
        return ir3.BoolSetAnyExpr(set_expr=self.transform_expr(expr.set_expr))

    def transform_bool_set_all_expr(self, expr: ir3.BoolSetAllExpr) -> ir3.BoolSetAllExpr:
        return ir3.BoolSetAllExpr(set_expr=self.transform_expr(expr.set_expr))

    def transform_bool_list_any_expr(self, expr: ir3.BoolListAnyExpr) -> ir3.BoolListAnyExpr:
        return ir3.BoolListAnyExpr(list_expr=self.transform_expr(expr.list_expr))

    def transform_bool_list_all_expr(self, expr: ir3.BoolListAllExpr) -> ir3.BoolListAllExpr:
        return ir3.BoolListAllExpr(list_expr=self.transform_expr(expr.list_expr))

    def transform_int_set_sum_expr(self, expr: ir3.IntSetSumExpr) -> ir3.IntSetSumExpr:
        return ir3.IntSetSumExpr(set_expr=self.transform_expr(expr.set_expr))

    def transform_int_list_sum_expr(self, expr: ir3.IntListSumExpr) -> ir3.IntListSumExpr:
        return ir3.IntListSumExpr(list_expr=self.transform_expr(expr.list_expr))

    def transform_set_expr(self, expr: ir3.SetExpr) -> ir3.SetExpr:
        return ir3.SetExpr(elem_type=expr.elem_type,
                           elem_exprs=[self.transform_expr(elem)
                                       for elem in expr.elem_exprs])

    def transform_list_expr(self, expr: ir3.ListExpr) -> ir3.ListExpr:
        return ir3.ListExpr(elem_type=expr.elem_type,
                            elem_exprs=[self.transform_expr(elem)
                                        for elem in expr.elem_exprs],
                            list_extraction_expr=self.transform_var_reference(expr.list_extraction_expr)
                                                 if expr.list_extraction_expr else None)

    def transform_atomic_type_literal_expr(self, expr: ir3.AtomicTypeLiteral) -> ir3.AtomicTypeLiteral:
        return expr

    def transform_pointer_type_expr(self, expr: ir3.PointerTypeExpr) -> ir3.PointerTypeExpr:
        return ir3.PointerTypeExpr(self.transform_expr(expr.type_expr))

    def transform_reference_type_expr(self, expr: ir3.ReferenceTypeExpr) -> ir3.ReferenceTypeExpr:
        return ir3.ReferenceTypeExpr(self.transform_expr(expr.type_expr))

    def transform_rvalue_reference_type_expr(self, expr: ir3.RvalueReferenceTypeExpr) -> ir3.RvalueReferenceTypeExpr:
        return ir3.RvalueReferenceTypeExpr(self.transform_expr(expr.type_expr))

    def transform_const_type_expr(self, expr: ir3.ConstTypeExpr) -> ir3.ConstTypeExpr:
        return ir3.ConstTypeExpr(self.transform_expr(expr.type_expr))

    def transform_array_type_expr(self, expr: ir3.ArrayTypeExpr) -> ir3.ArrayTypeExpr:
        return ir3.ArrayTypeExpr(self.transform_expr(expr.type_expr))

    def transform_function_type_expr(self, expr: ir3.FunctionTypeExpr) -> ir3.FunctionTypeExpr:
        return ir3.FunctionTypeExpr(return_type_expr=self.transform_expr(expr.return_type_expr),
                                    arg_list_expr=self.transform_expr(expr.arg_list_expr))

    def transform_template_instantiation_expr(self, expr: ir3.TemplateInstantiationExpr) -> ir3.TemplateInstantiationExpr:
        return ir3.TemplateInstantiationExpr(template_atomic_cpp_type=expr.template_atomic_cpp_type,
                                             arg_list_expr=self.transform_expr(expr.arg_list_expr))

    def transform_template_member_access_expr(self, expr: ir3.TemplateMemberAccessExpr) -> ir3.TemplateMemberAccessExpr:
        return ir3.TemplateMemberAccessExpr(class_type_expr=self.transform_expr(expr.class_type_expr),
                                            member_name=expr.member_name,
                                            arg_list_expr=self.transform_expr(expr.arg_list_expr))

    def transform_bool_literal_expr(self, expr: ir3.BoolLiteral) -> ir3.BoolLiteral:
        return expr

    def transform_match_expr(self, expr: ir3.MatchExpr) -> ir3.MatchExpr:
        return ir3.MatchExpr(matched_exprs=[self.transform_expr(matched_expr)
                                            for matched_expr in expr.matched_exprs],
                             match_cases=[self.transform_match_case(match_case)
                                          for match_case in expr.match_cases])

    def transform_match_case(self, match_case: ir3.MatchCase) -> ir3.MatchCase:
      return ir3.MatchCase(type_patterns=match_case.type_patterns,
                           matched_var_names=match_case.matched_var_names,
                           matched_variadic_var_names=match_case.matched_variadic_var_names,
                           expr=self.transform_expr(match_case.expr))

    def transform_var_reference(self, expr: ir3.VarReference) -> ir3.VarReference:
        return expr