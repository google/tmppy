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

from typing import Tuple
from _py2tmp.ir2 import ir as ir2


# noinspection PyMethodMayBeStatic
class Transformation:
    def transform_module(self, module: ir2.Module) -> ir2.Module:
        return ir2.Module(function_defns=tuple(self.transform_function_defn(function_defn)
                                               for function_defn in module.function_defns),
                          assertions=tuple(self.transform_assert(assertion)
                                           for assertion in module.assertions),
                          custom_types=module.custom_types,
                          public_names=module.public_names,
                          pass_stmts=tuple(self.transform_pass_stmt(stmt)
                                           for stmt in module.pass_stmts))

    def transform_function_defn(self, function_defn: ir2.FunctionDefn) -> ir2.FunctionDefn:
        return ir2.FunctionDefn(name=function_defn.name,
                                args=tuple(self.transform_function_arg_decl(arg)
                                           for arg in function_defn.args),
                                body=self.transform_stmts(function_defn.body),
                                return_type=function_defn.return_type)

    def transform_function_arg_decl(self, arg_decl: ir2.FunctionArgDecl):
        return arg_decl

    def transform_stmts(self, stmts: Tuple[ir2.Stmt, ...]) -> Tuple[ir2.Stmt, ...]:
        return tuple(self.transform_stmt(stmt)
                     for stmt in stmts)

    def transform_stmt(self, stmt: ir2.Stmt) -> ir2.Stmt:
        if isinstance(stmt, ir2.TryExcept):
            return self.transform_try_except(stmt)
        elif isinstance(stmt, ir2.RaiseStmt):
            return self.transform_raise_stmt(stmt)
        elif isinstance(stmt, ir2.IfStmt):
            return self.transform_if_stmt(stmt)
        elif isinstance(stmt, ir2.ReturnStmt):
            return self.transform_return_stmt(stmt)
        elif isinstance(stmt, ir2.UnpackingAssignment):
            return self.transform_unpacking_assignment(stmt)
        elif isinstance(stmt, ir2.Assignment):
            return self.transform_assignment(stmt)
        elif isinstance(stmt, ir2.Assert):
            return self.transform_assert(stmt)
        elif isinstance(stmt, ir2.PassStmt):
            return self.transform_pass_stmt(stmt)
        else:
            raise NotImplementedError('Unexpected stmt: %s' % stmt.__class__.__name__)

    def transform_try_except(self, try_except: ir2.TryExcept) -> ir2.TryExcept:
        return ir2.TryExcept(try_body=self.transform_stmts(try_except.try_body),
                             except_body=self.transform_stmts(try_except.except_body),
                             caught_exception_name=try_except.caught_exception_name,
                             caught_exception_type=try_except.caught_exception_type,
                             try_branch=try_except.try_branch,
                             except_branch=try_except.except_branch)

    def transform_raise_stmt(self, stmt: ir2.RaiseStmt) -> ir2.RaiseStmt:
        return ir2.RaiseStmt(expr=self.transform_expr(stmt.expr),
                             source_branch=stmt.source_branch)

    def transform_if_stmt(self, stmt: ir2.IfStmt) -> ir2.IfStmt:
        return ir2.IfStmt(cond_expr=self.transform_expr(stmt.cond_expr),
                          if_stmts=self.transform_stmts(stmt.if_stmts),
                          else_stmts=self.transform_stmts(stmt.else_stmts))

    def transform_return_stmt(self, stmt: ir2.ReturnStmt) -> ir2.ReturnStmt:
        return ir2.ReturnStmt(expr=self.transform_expr(stmt.expr),
                              source_branch=stmt.source_branch)

    def transform_unpacking_assignment(self, assignment: ir2.UnpackingAssignment) -> ir2.UnpackingAssignment:
        return ir2.UnpackingAssignment(lhs_list=tuple(self.transform_var_reference(var)
                                                      for var in assignment.lhs_list),
                                       rhs=self.transform_expr(assignment.rhs),
                                       error_message=assignment.error_message,
                                       source_branch=assignment.source_branch)

    def transform_assignment(self, assignment: ir2.Assignment) -> ir2.Assignment:
        return ir2.Assignment(lhs=self.transform_var_reference(assignment.lhs),
                              rhs=self.transform_expr(assignment.rhs),
                              source_branch=assignment.source_branch)

    def transform_assert(self, stmt: ir2.Assert) -> ir2.Assert:
        return ir2.Assert(expr=self.transform_expr(stmt.expr),
                          message=stmt.message,
                          source_branch=stmt.source_branch)

    def transform_pass_stmt(self, stmt: ir2.PassStmt) -> ir2.PassStmt:
        return ir2.PassStmt(source_branch=stmt.source_branch)

    def transform_expr(self, expr: ir2.Expr) -> ir2.Expr:
        if isinstance(expr, ir2.SetComprehension):
            return self.transform_set_comprehension(expr)
        elif isinstance(expr, ir2.ListComprehension):
            return self.transform_list_comprehension(expr)
        elif isinstance(expr, ir2.ListConcatExpr):
            return self.transform_list_concat_expr(expr)
        elif isinstance(expr, ir2.IntBinaryOpExpr):
            return self.transform_int_binary_op_expr(expr)
        elif isinstance(expr, ir2.IntUnaryMinusExpr):
            return self.transform_int_unary_minus_expr(expr)
        elif isinstance(expr, ir2.IntComparisonExpr):
            return self.transform_int_comparison_expr(expr)
        elif isinstance(expr, ir2.IntLiteral):
            return self.transform_int_literal_expr(expr)
        elif isinstance(expr, ir2.NotExpr):
            return self.transform_not_expr(expr)
        elif isinstance(expr, ir2.OrExpr):
            return self.transform_or_expr(expr)
        elif isinstance(expr, ir2.AndExpr):
            return self.transform_and_expr(expr)
        elif isinstance(expr, ir2.AttributeAccessExpr):
            return self.transform_attribute_access_expr(expr)
        elif isinstance(expr, ir2.EqualityComparison):
            return self.transform_equality_comparison(expr)
        elif isinstance(expr, ir2.InExpr):
            return self.transform_in_expr(expr)
        elif isinstance(expr, ir2.FunctionCall):
            return self.transform_function_call(expr)
        elif isinstance(expr, ir2.BoolSetAnyExpr):
            return self.transform_bool_set_any_expr(expr)
        elif isinstance(expr, ir2.BoolSetAllExpr):
            return self.transform_bool_set_all_expr(expr)
        elif isinstance(expr, ir2.BoolListAnyExpr):
            return self.transform_bool_list_any_expr(expr)
        elif isinstance(expr, ir2.BoolListAllExpr):
            return self.transform_bool_list_all_expr(expr)
        elif isinstance(expr, ir2.IntSetSumExpr):
            return self.transform_int_set_sum_expr(expr)
        elif isinstance(expr, ir2.IntListSumExpr):
            return self.transform_int_list_sum_expr(expr)
        elif isinstance(expr, ir2.SetExpr):
            return self.transform_set_expr(expr)
        elif isinstance(expr, ir2.ListExpr):
            return self.transform_list_expr(expr)
        elif isinstance(expr, ir2.AtomicTypeLiteral):
            return self.transform_atomic_type_literal_expr(expr)
        elif isinstance(expr, ir2.BoolLiteral):
            return self.transform_bool_literal_expr(expr)
        elif isinstance(expr, ir2.MatchExpr):
            return self.transform_match_expr(expr)
        elif isinstance(expr, ir2.VarReference):
            return self.transform_var_reference(expr)
        elif isinstance(expr, ir2.PointerTypeExpr):
            return self.transform_pointer_type_expr(expr)
        elif isinstance(expr, ir2.ReferenceTypeExpr):
            return self.transform_reference_type_expr(expr)
        elif isinstance(expr, ir2.RvalueReferenceTypeExpr):
            return self.transform_rvalue_reference_type_expr(expr)
        elif isinstance(expr, ir2.ConstTypeExpr):
            return self.transform_const_type_expr(expr)
        elif isinstance(expr, ir2.ArrayTypeExpr):
            return self.transform_array_type_expr(expr)
        elif isinstance(expr, ir2.FunctionTypeExpr):
            return self.transform_function_type_expr(expr)
        elif isinstance(expr, ir2.TemplateInstantiationExpr):
            return self.transform_template_instantiation_expr(expr)
        elif isinstance(expr, ir2.TemplateMemberAccessExpr):
            return self.transform_template_member_access_expr(expr)
        else:
            raise NotImplementedError('Unexpected expression: %s' % expr.__class__.__name__)

    def transform_set_comprehension(self, comprehension: ir2.SetComprehension) -> ir2.SetComprehension:
        return ir2.SetComprehension(set_expr=self.transform_expr(comprehension.set_expr),
                                    loop_var=self.transform_var_reference(comprehension.loop_var),
                                    result_elem_expr=self.transform_expr(comprehension.result_elem_expr),
                                    loop_body_start_branch=comprehension.loop_body_start_branch,
                                    loop_exit_branch=comprehension.loop_exit_branch)

    def transform_list_comprehension(self, comprehension: ir2.ListComprehension) -> ir2.ListComprehension:
        return ir2.ListComprehension(list_expr=self.transform_expr(comprehension.list_expr),
                                     loop_var=self.transform_var_reference(comprehension.loop_var),
                                     result_elem_expr=self.transform_expr(comprehension.result_elem_expr),
                                     loop_body_start_branch=comprehension.loop_body_start_branch,
                                     loop_exit_branch=comprehension.loop_exit_branch)

    def transform_list_concat_expr(self, expr: ir2.ListConcatExpr) -> ir2.ListConcatExpr:
        return ir2.ListConcatExpr(lhs=self.transform_expr(expr.lhs),
                                  rhs=self.transform_expr(expr.rhs))

    def transform_int_binary_op_expr(self, expr: ir2.IntBinaryOpExpr) -> ir2.IntBinaryOpExpr:
        return ir2.IntBinaryOpExpr(lhs=self.transform_expr(expr.lhs),
                                   rhs=self.transform_expr(expr.rhs),
                                   op=expr.op)

    def transform_int_unary_minus_expr(self, expr: ir2.IntUnaryMinusExpr) -> ir2.IntUnaryMinusExpr:
        return ir2.IntUnaryMinusExpr(expr=self.transform_expr(expr.expr))

    def transform_int_comparison_expr(self, expr: ir2.IntComparisonExpr) -> ir2.IntComparisonExpr:
        return ir2.IntComparisonExpr(lhs=self.transform_expr(expr.lhs),
                                     rhs=self.transform_expr(expr.rhs),
                                     op=expr.op)

    def transform_int_literal_expr(self, expr: ir2.IntLiteral) -> ir2.IntLiteral:
        return expr

    def transform_not_expr(self, expr: ir2.NotExpr) -> ir2.NotExpr:
        return ir2.NotExpr(expr=self.transform_expr(expr.expr))

    def transform_or_expr(self, expr: ir2.OrExpr) -> ir2.OrExpr:
        return ir2.OrExpr(lhs=self.transform_expr(expr.lhs),
                          rhs=self.transform_expr(expr.rhs))

    def transform_and_expr(self, expr: ir2.AndExpr) -> ir2.AndExpr:
        return ir2.AndExpr(lhs=self.transform_expr(expr.lhs),
                           rhs=self.transform_expr(expr.rhs))

    def transform_attribute_access_expr(self, expr: ir2.AttributeAccessExpr) -> ir2.AttributeAccessExpr:
        return ir2.AttributeAccessExpr(expr=self.transform_expr(expr.expr),
                                       attribute_name=expr.attribute_name,
                                       expr_type=expr.expr_type)

    def transform_equality_comparison(self, expr: ir2.EqualityComparison) -> ir2.EqualityComparison:
        return ir2.EqualityComparison(lhs=self.transform_expr(expr.lhs),
                                      rhs=self.transform_expr(expr.rhs))

    def transform_in_expr(self, expr: ir2.InExpr) -> ir2.InExpr:
        return ir2.InExpr(lhs=self.transform_expr(expr.lhs),
                          rhs=self.transform_expr(expr.rhs))

    def transform_function_call(self, expr: ir2.FunctionCall) -> ir2.FunctionCall:
        return ir2.FunctionCall(fun_expr=self.transform_expr(expr.fun_expr),
                                args=tuple(self.transform_expr(arg)
                                           for arg in expr.args),
                                may_throw=expr.may_throw)

    def transform_bool_set_any_expr(self, expr: ir2.BoolSetAnyExpr) -> ir2.BoolSetAnyExpr:
        return ir2.BoolSetAnyExpr(set_expr=self.transform_expr(expr.set_expr))

    def transform_bool_set_all_expr(self, expr: ir2.BoolSetAllExpr) -> ir2.BoolSetAllExpr:
        return ir2.BoolSetAllExpr(set_expr=self.transform_expr(expr.set_expr))

    def transform_bool_list_any_expr(self, expr: ir2.BoolListAnyExpr) -> ir2.BoolListAnyExpr:
        return ir2.BoolListAnyExpr(list_expr=self.transform_expr(expr.list_expr))

    def transform_bool_list_all_expr(self, expr: ir2.BoolListAllExpr) -> ir2.BoolListAllExpr:
        return ir2.BoolListAllExpr(list_expr=self.transform_expr(expr.list_expr))

    def transform_int_set_sum_expr(self, expr: ir2.IntSetSumExpr) -> ir2.IntSetSumExpr:
        return ir2.IntSetSumExpr(set_expr=self.transform_expr(expr.set_expr))

    def transform_int_list_sum_expr(self, expr: ir2.IntListSumExpr) -> ir2.IntListSumExpr:
        return ir2.IntListSumExpr(list_expr=self.transform_expr(expr.list_expr))

    def transform_set_expr(self, expr: ir2.SetExpr) -> ir2.SetExpr:
        return ir2.SetExpr(elem_type=expr.elem_type,
                           elem_exprs=tuple(self.transform_expr(elem)
                                            for elem in expr.elem_exprs))

    def transform_list_expr(self, expr: ir2.ListExpr) -> ir2.ListExpr:
        return ir2.ListExpr(elem_type=expr.elem_type,
                            elem_exprs=tuple(self.transform_expr(elem)
                                             for elem in expr.elem_exprs),
                            list_extraction_expr=(self.transform_var_reference(expr.list_extraction_expr)
                                                  if expr.list_extraction_expr else None))

    def transform_atomic_type_literal_expr(self, expr: ir2.AtomicTypeLiteral) -> ir2.AtomicTypeLiteral:
        return expr

    def transform_pointer_type_expr(self, expr: ir2.PointerTypeExpr) -> ir2.PointerTypeExpr:
        return ir2.PointerTypeExpr(self.transform_expr(expr.type_expr))

    def transform_reference_type_expr(self, expr: ir2.ReferenceTypeExpr) -> ir2.ReferenceTypeExpr:
        return ir2.ReferenceTypeExpr(self.transform_expr(expr.type_expr))

    def transform_rvalue_reference_type_expr(self, expr: ir2.RvalueReferenceTypeExpr) -> ir2.RvalueReferenceTypeExpr:
        return ir2.RvalueReferenceTypeExpr(self.transform_expr(expr.type_expr))

    def transform_const_type_expr(self, expr: ir2.ConstTypeExpr) -> ir2.ConstTypeExpr:
        return ir2.ConstTypeExpr(self.transform_expr(expr.type_expr))

    def transform_array_type_expr(self, expr: ir2.ArrayTypeExpr) -> ir2.ArrayTypeExpr:
        return ir2.ArrayTypeExpr(self.transform_expr(expr.type_expr))

    def transform_function_type_expr(self, expr: ir2.FunctionTypeExpr) -> ir2.FunctionTypeExpr:
        return ir2.FunctionTypeExpr(return_type_expr=self.transform_expr(expr.return_type_expr),
                                    arg_list_expr=self.transform_expr(expr.arg_list_expr))

    def transform_template_instantiation_expr(self, expr: ir2.TemplateInstantiationExpr) -> ir2.TemplateInstantiationExpr:
        return ir2.TemplateInstantiationExpr(template_atomic_cpp_type=expr.template_atomic_cpp_type,
                                             arg_list_expr=self.transform_expr(expr.arg_list_expr))

    def transform_template_member_access_expr(self, expr: ir2.TemplateMemberAccessExpr) -> ir2.TemplateMemberAccessExpr:
        return ir2.TemplateMemberAccessExpr(class_type_expr=self.transform_expr(expr.class_type_expr),
                                            member_name=expr.member_name,
                                            arg_list_expr=self.transform_expr(expr.arg_list_expr))

    def transform_bool_literal_expr(self, expr: ir2.BoolLiteral) -> ir2.BoolLiteral:
        return expr

    def transform_match_expr(self, expr: ir2.MatchExpr) -> ir2.MatchExpr:
        return ir2.MatchExpr(matched_exprs=tuple(self.transform_expr(matched_expr)
                                                 for matched_expr in expr.matched_exprs),
                             match_cases=tuple(self.transform_match_case(match_case)
                                               for match_case in expr.match_cases))

    def transform_match_case(self, match_case: ir2.MatchCase) -> ir2.MatchCase:
        return ir2.MatchCase(type_patterns=match_case.type_patterns,
                             matched_var_names=match_case.matched_var_names,
                             matched_variadic_var_names=match_case.matched_variadic_var_names,
                             expr=self.transform_expr(match_case.expr),
                             match_case_start_branch=match_case.match_case_start_branch,
                             match_case_end_branch=match_case.match_case_end_branch)

    def transform_var_reference(self, expr: ir2.VarReference) -> ir2.VarReference:
        return expr
