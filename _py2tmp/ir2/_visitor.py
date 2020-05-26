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
import itertools

from _py2tmp.ir2 import ir

class Visitor:
    def visit_custom_type_defn(self, custom_type: ir.CustomType):
        pass
    
    def visit_expr(self, expr: ir.Expr):
        if isinstance(expr, ir.VarReference):
            self.visit_var_reference(expr)
        elif isinstance(expr, ir.MatchExpr):
            self.visit_match_expr(expr)
        elif isinstance(expr, ir.BoolLiteral):
            self.visit_bool_literal(expr)
        elif isinstance(expr, ir.IntLiteral):
            self.visit_int_literal(expr)
        elif isinstance(expr, ir.AtomicTypeLiteral):
            self.visit_atomic_type_literal(expr)
        elif isinstance(expr, ir.PointerTypeExpr):
            self.visit_pointer_type_expr(expr)
        elif isinstance(expr, ir.ReferenceTypeExpr):
            self.visit_reference_type_expr(expr)
        elif isinstance(expr, ir.RvalueReferenceTypeExpr):
            self.visit_rvalue_reference_type_expr(expr)
        elif isinstance(expr, ir.ConstTypeExpr):
            self.visit_const_type_expr(expr)
        elif isinstance(expr, ir.ArrayTypeExpr):
            self.visit_array_type_expr(expr)
        elif isinstance(expr, ir.FunctionTypeExpr):
            self.visit_function_type_expr(expr)
        elif isinstance(expr, ir.TemplateInstantiationExpr):
            self.visit_template_instantiation_expr(expr)
        elif isinstance(expr, ir.TemplateMemberAccessExpr):
            self.visit_template_member_access_expr(expr)
        elif isinstance(expr, ir.ListExpr):
            self.visit_list_expr(expr)
        elif isinstance(expr, ir.SetExpr):
            self.visit_set_expr(expr)
        elif isinstance(expr, ir.FunctionCall):
            self.visit_function_call(expr)
        elif isinstance(expr, ir.EqualityComparison):
            self.visit_equality_comparison(expr)
        elif isinstance(expr, ir.InExpr):
            self.visit_in_expr(expr)
        elif isinstance(expr, ir.AttributeAccessExpr):
            self.visit_attribute_access_expr(expr)
        elif isinstance(expr, ir.AndExpr):
            self.visit_and_expr(expr)
        elif isinstance(expr, ir.OrExpr):
            self.visit_or_expr(expr)
        elif isinstance(expr, ir.NotExpr):
            self.visit_not_expr(expr)
        elif isinstance(expr, ir.IntUnaryMinusExpr):
            self.visit_int_unary_minus_expr(expr)
        elif isinstance(expr, ir.IntListSumExpr):
            self.visit_int_list_sum_expr(expr)
        elif isinstance(expr, ir.IntSetSumExpr):
            self.visit_int_set_sum_expr(expr)
        elif isinstance(expr, ir.BoolListAllExpr):
            self.visit_bool_list_all_expr(expr)
        elif isinstance(expr, ir.BoolSetAllExpr):
            self.visit_bool_set_all_expr(expr)
        elif isinstance(expr, ir.BoolListAnyExpr):
            self.visit_bool_list_any_expr(expr)
        elif isinstance(expr, ir.BoolSetAnyExpr):
            self.visit_bool_set_any_expr(expr)
        elif isinstance(expr, ir.IntComparisonExpr):
            self.visit_int_comparison_expr(expr)
        elif isinstance(expr, ir.IntBinaryOpExpr):
            self.visit_int_binary_op_expr(expr)
        elif isinstance(expr, ir.ListConcatExpr):
            self.visit_list_concat_expr(expr)
        elif isinstance(expr, ir.ListComprehension):
            self.visit_list_comprehension(expr)
        elif isinstance(expr, ir.SetComprehension):
            self.visit_set_comprehension(expr)
        else:
            raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))
    
    def visit_var_reference(self, var_reference: ir.VarReference):
        pass
    
    def visit_match_case(self, match_case: ir.MatchCase):
        self.visit_expr(match_case.expr)
        for pattern in match_case.type_patterns:
            self.visit_expr(pattern)
    
    def visit_match_expr(self, match_expr: ir.MatchExpr):
        for match_case in match_expr.match_cases:
            self.visit_match_case(match_case)
        for expr in match_expr.matched_exprs:
            self.visit_expr(expr)

    def visit_bool_literal(self, bool_literal: ir.BoolLiteral):
        pass
    
    def visit_atomic_type_literal(self, atomic_type_literal: ir.AtomicTypeLiteral):
        pass
    
    def visit_pointer_type_expr(self, expr: ir.PointerTypeExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_reference_type_expr(self, expr: ir.ReferenceTypeExpr):
        self.visit_expr(expr.type_expr)
        
    def visit_rvalue_reference_type_expr(self, expr: ir.RvalueReferenceTypeExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_const_type_expr(self, expr: ir.ConstTypeExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_array_type_expr(self, expr: ir.ArrayTypeExpr):
        self.visit_expr(expr.type_expr)
        
    def visit_function_type_expr(self, expr: ir.FunctionTypeExpr):
        self.visit_expr(expr.return_type_expr)
        self.visit_expr(expr.arg_list_expr)
        
    def visit_template_instantiation_expr(self, expr: ir.TemplateInstantiationExpr):
        self.visit_expr(expr.arg_list_expr)
        
    def visit_template_member_access_expr(self, expr: ir.TemplateMemberAccessExpr):
        self.visit_expr(expr.class_type_expr)
        self.visit_expr(expr.arg_list_expr)
    
    def visit_list_expr(self, expr: ir.ListExpr):
        for elem_expr in expr.elem_exprs:
            self.visit_expr(elem_expr)
        if expr.list_extraction_expr:
            self.visit_expr(expr.list_extraction_expr)
    
    def visit_set_expr(self, expr: ir.SetExpr):
        for elem_expr in expr.elem_exprs:
            self.visit_expr(elem_expr)
    
    def visit_int_list_sum_expr(self, expr: ir.IntListSumExpr):
        self.visit_expr(expr.list_expr)
    
    def visit_int_set_sum_expr(self, expr: ir.IntSetSumExpr):
        self.visit_expr(expr.set_expr)
    
    def visit_bool_list_all_expr(self, expr: ir.BoolListAllExpr):
        self.visit_expr(expr.list_expr)
    
    def visit_bool_list_any_expr(self, expr: ir.BoolListAnyExpr):
        self.visit_expr(expr.list_expr)
    
    def visit_bool_set_all_expr(self, expr: ir.BoolSetAllExpr):
        self.visit_expr(expr.set_expr)
    
    def visit_bool_set_any_expr(self, expr: ir.BoolSetAnyExpr):
        self.visit_expr(expr.set_expr)
        
    def visit_function_call(self, expr: ir.FunctionCall):
        self.visit_expr(expr.fun_expr)
        for arg in expr.args:
            self.visit_expr(arg)
    
    def visit_equality_comparison(self, expr: ir.EqualityComparison):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
        
    def visit_in_expr(self, expr: ir.InExpr):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_attribute_access_expr(self, expr: ir.AttributeAccessExpr):
        self.visit_expr(expr.expr)
        
    def visit_and_expr(self, expr: ir.AndExpr):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_or_expr(self, expr: ir.OrExpr):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_not_expr(self, expr: ir.NotExpr):
        self.visit_expr(expr.expr)
        
    def visit_int_literal(self, expr: ir.IntLiteral):
        pass
    
    def visit_int_comparison_expr(self, expr: ir.IntComparisonExpr):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
        
    def visit_int_unary_minus_expr(self, expr: ir.IntUnaryMinusExpr):
        self.visit_expr(expr.expr)
    
    def visit_int_binary_op_expr(self, expr: ir.IntBinaryOpExpr):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_list_concat_expr(self, expr: ir.ListConcatExpr):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_list_comprehension(self, expr: ir.ListComprehension):
        self.visit_expr(expr.list_expr)
        self.visit_expr(expr.loop_var)
        self.visit_expr(expr.result_elem_expr)
    
    def visit_set_comprehension(self, expr: ir.SetComprehension):
        self.visit_expr(expr.set_expr)
        self.visit_expr(expr.loop_var)
        self.visit_expr(expr.result_elem_expr)
    
    def visit_stmt(self, stmt: ir.Stmt):
        if isinstance(stmt, ir.IfStmt):
            self.visit_if_stmt(stmt)
        elif isinstance(stmt, ir.Assignment):
            self.visit_assignment(stmt)
        elif isinstance(stmt, ir.UnpackingAssignment):
            self.visit_unpacking_assignment(stmt)
        elif isinstance(stmt, ir.ReturnStmt):
            self.visit_return_stmt(stmt)
        elif isinstance(stmt, ir.RaiseStmt):
            self.visit_raise_stmt(stmt)
        elif isinstance(stmt, ir.Assert):
            self.visit_assert(stmt)
        elif isinstance(stmt, ir.TryExcept):
            self.visit_try_except_stmt(stmt)
            return
        elif isinstance(stmt, ir.PassStmt):
            self.visit_pass_stmt(stmt)
            return
        else:
            raise NotImplementedError('Unexpected statement: %s' % str(stmt.__class__))

    def visit_assert(self, stmt: ir.Assert):
        self.visit_expr(stmt.expr)

    def visit_assignment(self, stmt: ir.Assignment):
        self.visit_expr(stmt.lhs)
        self.visit_expr(stmt.rhs)

    def visit_unpacking_assignment(self, stmt: ir.UnpackingAssignment):
        for lhs in stmt.lhs_list:
            self.visit_expr(lhs)
        self.visit_expr(stmt.rhs)

    def visit_return_stmt(self, stmt: ir.ReturnStmt):
        self.visit_expr(stmt.expr)

    def visit_if_stmt(self, stmt: ir.IfStmt):
        self.visit_expr(stmt.cond_expr)
        for child_stmt in itertools.chain(stmt.if_stmts, stmt.else_stmts):
            self.visit_stmt(child_stmt)

    def visit_raise_stmt(self, stmt: ir.RaiseStmt):
        self.visit_expr(stmt.expr)

    def visit_try_except_stmt(self, stmt: ir.TryExcept):
        for child_stmt in itertools.chain(stmt.try_body, stmt.except_body):
            self.visit_stmt(child_stmt)

    def visit_pass_stmt(self, stmt: ir.PassStmt):
        pass

    def visit_function_defn(self, function_defn: ir.FunctionDefn):
        for stmt in function_defn.body:
            self.visit_stmt(stmt)

    def visit_module(self, module: ir.Module):
        for function_defn in module.function_defns:
            self.visit_function_defn(function_defn)
        for assert_stmt in module.assertions:
            self.visit_assert(assert_stmt)
        for custom_type in module.custom_types:
            self.visit_custom_type_defn(custom_type)
        for pass_stmt in module.pass_stmts:
            self.visit_pass_stmt(pass_stmt)
