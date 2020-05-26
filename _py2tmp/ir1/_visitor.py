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
from typing import Tuple, Iterable

from _py2tmp.ir1 import ir


class Visitor:
    def visit_expr(self, expr: ir.Expr):
        if isinstance(expr, (ir.VarReference, ir.VarReferencePattern)):
            self.visit_var_reference(expr)
        elif isinstance(expr, ir.MatchExpr):
            self.visit_match_expr(expr)
        elif isinstance(expr, ir.BoolLiteral):
            self.visit_bool_literal(expr)
        elif isinstance(expr, ir.IntLiteral):
            self.visit_int_literal(expr)
        elif isinstance(expr, (ir.AtomicTypeLiteral, ir.AtomicTypeLiteralPattern)):
            self.visit_atomic_type_literal(expr)
        elif isinstance(expr, (ir.PointerTypeExpr, ir.PointerTypePatternExpr)):
            self.visit_pointer_type_expr(expr)
        elif isinstance(expr, (ir.ReferenceTypeExpr, ir.ReferenceTypePatternExpr)):
            self.visit_reference_type_expr(expr)
        elif isinstance(expr, (ir.RvalueReferenceTypeExpr, ir.RvalueReferenceTypePatternExpr)):
            self.visit_rvalue_reference_type_expr(expr)
        elif isinstance(expr, (ir.ConstTypeExpr, ir.ConstTypePatternExpr)):
            self.visit_const_type_expr(expr)
        elif isinstance(expr, (ir.ArrayTypeExpr, ir.ArrayTypePatternExpr)):
            self.visit_array_type_expr(expr)
        elif isinstance(expr, (ir.FunctionTypeExpr, ir.FunctionTypePatternExpr)):
            self.visit_function_type_expr(expr)
        elif isinstance(expr, ir.TemplateInstantiationExpr):
            self.visit_template_instantiation_expr(expr)
        elif isinstance(expr, ir.TemplateMemberAccessExpr):
            self.visit_template_member_access_expr(expr)
        elif isinstance(expr, (ir.ListExpr, ir.ListPatternExpr)):
            self.visit_list_expr(expr)
        elif isinstance(expr, ir.FunctionCall):
            self.visit_function_call(expr)
        elif isinstance(expr, ir.EqualityComparison):
            self.visit_equality_comparison(expr)
        elif isinstance(expr, ir.IsInListExpr):
            self.visit_is_in_list_expr(expr)
        elif isinstance(expr, ir.AttributeAccessExpr):
            self.visit_attribute_access_expr(expr)
        elif isinstance(expr, ir.NotExpr):
            self.visit_not_expr(expr)
        elif isinstance(expr, ir.IntComparisonExpr):
            self.visit_int_comparison_expr(expr)
        elif isinstance(expr, ir.UnaryMinusExpr):
            self.visit_unary_minus_expr(expr)
        elif isinstance(expr, ir.IntListSumExpr):
            self.visit_int_list_sum_expr(expr)
        elif isinstance(expr, ir.BoolListAllExpr):
            self.visit_bool_list_all_expr(expr)
        elif isinstance(expr, ir.BoolListAnyExpr):
            self.visit_bool_list_any_expr(expr)
        elif isinstance(expr, ir.IntBinaryOpExpr):
            self.visit_int_binary_op_expr(expr)
        elif isinstance(expr, ir.ListConcatExpr):
            self.visit_list_concat_expr(expr)
        elif isinstance(expr, ir.ListComprehensionExpr):
            self.visit_list_comprehension_expr(expr)
        elif isinstance(expr, ir.IsInstanceExpr):
            self.visit_is_instance_expr(expr)
        elif isinstance(expr, ir.SafeUncheckedCast):
            self.visit_safe_unchecked_cast(expr)
        elif isinstance(expr, ir.AddToSetExpr):
            self.visit_add_to_set_expr(expr)
        elif isinstance(expr, ir.SetEqualityComparison):
            self.visit_set_equality_comparison(expr)
        elif isinstance(expr, ir.ListToSetExpr):
            self.visit_list_to_set_expr(expr)
        elif isinstance(expr, ir.SetToListExpr):
            self.visit_set_to_list_expr(expr)
        elif isinstance(expr, ir.TemplateInstantiationPatternExpr):
            self.visit_template_instantiation_pattern_expr(expr)
        else:
            raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))
    
    def visit_pattern_expr(self, expr: ir.PatternExpr):
        pass
    
    def visit_var_reference(self, expr: ir.VarReference):
        pass
    
    def visit_var_reference_pattern(self, expr: ir.VarReferencePattern):
        pass
    
    def visit_match_case(self, match_case: ir.MatchCase):
        self.visit_expr(match_case.expr)
        for pattern in match_case.type_patterns:
            self.visit_expr(pattern)
    
    def visit_match_expr(self, expr: ir.MatchExpr):
        for matched_var in expr.matched_vars:
            self.visit_expr(matched_var)
        for match_case in expr.match_cases:
            self.visit_match_case(match_case)
    
    def visit_bool_literal(self, expr: ir.BoolLiteral):
        pass
    
    def visit_atomic_type_literal(self, expr: ir.AtomicTypeLiteral):
        pass
    
    def visit_atomic_type_literal_pattern(self, expr: ir.AtomicTypeLiteralPattern):
        pass
    
    def visit_pointer_type_expr(self, expr: ir.PointerTypeExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_pointer_type_pattern_expr(self, expr: ir.PointerTypePatternExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_reference_type_expr(self, expr: ir.ReferenceTypeExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_reference_type_pattern_expr(self, expr: ir.ReferenceTypePatternExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_rvalue_reference_type_expr(self, expr: ir.RvalueReferenceTypeExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_rvalue_reference_type_pattern_expr(self, expr: ir.RvalueReferenceTypePatternExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_const_type_expr(self, expr: ir.ConstTypeExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_const_type_pattern_expr(self, expr: ir.ConstTypePatternExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_array_type_expr(self, expr: ir.ArrayTypeExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_array_type_pattern_expr(self, expr: ir.ArrayTypePatternExpr):
        self.visit_expr(expr.type_expr)
    
    def visit_function_type_expr(self, expr: ir.FunctionTypeExpr):
        self.visit_expr(expr.return_type_expr)
        self.visit_expr(expr.arg_list_expr)
    
    def visit_function_type_pattern_expr(self, expr: ir.FunctionTypePatternExpr):
        self.visit_expr(expr.return_type_expr)
        self.visit_expr(expr.arg_list_expr)
    
    def visit_template_instantiation_expr(self, expr: ir.TemplateInstantiationExpr):
        self.visit_expr(expr.arg_list_expr)
    
    def visit_template_instantiation_pattern_expr(self, expr: ir.TemplateInstantiationPatternExpr):
        for arg_expr in expr.arg_exprs:
            self.visit_expr(arg_expr)
        if expr.list_extraction_arg_expr:
            self.visit_expr(expr.list_extraction_arg_expr)
    
    def visit_template_member_access_expr(self, expr: ir.TemplateMemberAccessExpr):
        self.visit_expr(expr.class_type_expr)
        self.visit_expr(expr.arg_list_expr)
    
    def visit_list_expr(self, expr: ir.ListExpr):
        for elem in expr.elems:
            self.visit_expr(elem)
    
    def visit_list_pattern_expr(self, expr: ir.ListPatternExpr):
        for elem in expr.elems:
            self.visit_expr(elem)
        if expr.list_extraction_expr:
            self.visit_expr(expr.list_extraction_expr)
    
    def visit_add_to_set_expr(self, expr: ir.AddToSetExpr):
        self.visit_expr(expr.set_expr)
        self.visit_expr(expr.elem_expr)
    
    def visit_set_to_list_expr(self, expr: ir.SetToListExpr):
        self.visit_expr(expr.var)
    
    def visit_list_to_set_expr(self, expr: ir.ListToSetExpr):
        self.visit_expr(expr.var)
    
    def visit_function_call(self, expr: ir.FunctionCall):
        self.visit_expr(expr.fun)
        for arg in expr.args:
            self.visit_expr(arg)
    
    def visit_equality_comparison(self, expr: ir.EqualityComparison):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_set_equality_comparison(self, expr: ir.SetEqualityComparison):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_is_in_list_expr(self, expr: ir.IsInListExpr):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_attribute_access_expr(self, expr: ir.AttributeAccessExpr):
        self.visit_expr(expr.var)
    
    def visit_int_literal(self, expr: ir.IntLiteral):
        pass
    
    def visit_not_expr(self, expr: ir.NotExpr):
        self.visit_expr(expr.var)
    
    def visit_unary_minus_expr(self, expr: ir.UnaryMinusExpr):
        self.visit_expr(expr.var)
    
    def visit_int_list_sum_expr(self, expr: ir.IntListSumExpr):
        self.visit_expr(expr.var)
    
    def visit_bool_list_all_expr(self, expr: ir.BoolListAllExpr):
        self.visit_expr(expr.var)
    
    def visit_bool_list_any_expr(self, expr: ir.BoolListAnyExpr):
        self.visit_expr(expr.var)
    
    def visit_int_comparison_expr(self, expr: ir.IntComparisonExpr):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_int_binary_op_expr(self, expr: ir.IntBinaryOpExpr):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_list_concat_expr(self, expr: ir.ListConcatExpr):
        self.visit_expr(expr.lhs)
        self.visit_expr(expr.rhs)
    
    def visit_is_instance_expr(self, expr: ir.IsInstanceExpr):
        self.visit_expr(expr.var)
    
    def visit_safe_unchecked_cast(self, expr: ir.SafeUncheckedCast):
        self.visit_expr(expr.var)
    
    def visit_list_comprehension_expr(self, expr: ir.ListComprehensionExpr):
        self.visit_expr(expr.list_var)
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
        elif isinstance(stmt, ir.Assert):
            self.visit_assert(stmt)
        elif isinstance(stmt, ir.PassStmt):
            self.visit_pass_stmt(stmt)
        else:
            raise NotImplementedError('Unexpected statement: %s' % str(stmt.__class__))
    
    def visit_assert(self, stmt: ir.Assert):
        self.visit_expr(stmt.var)
    
    def visit_pass_stmt(self, stmt: ir.PassStmt):
        pass

    def visit_assignment(self, stmt: ir.Assignment):
        self.visit_expr(stmt.lhs)
        self.visit_expr(stmt.rhs)
        if stmt.lhs2:
            self.visit_expr(stmt.lhs2)
    
    def visit_check_if_error(self, stmt: ir.CheckIfError):
        self.visit_expr(stmt.var)
    
    def visit_unpacking_assignment(self, stmt: ir.UnpackingAssignment):
        for lhs in stmt.lhs_list:
            self.visit_expr(lhs)
        self.visit_expr(stmt.rhs)
    
    def visit_return_stmt(self, stmt: ir.ReturnStmt):
        if stmt.result:
            self.visit_expr(stmt.result)
        if stmt.error:
            self.visit_expr(stmt.error)

    def visit_stmts(self, stmts: Iterable[ir.Stmt]):
        for stmt in stmts:
            self.visit_stmt(stmt)
    
    def visit_if_stmt(self, stmt: ir.IfStmt):
        self.visit_expr(stmt.cond)
        self.visit_stmts(stmt.if_stmts)
        self.visit_stmts(stmt.else_stmts)

    def visit_function_defn(self, function_defn: ir.FunctionDefn):
        self.visit_stmts(function_defn.body)

    def visit_check_if_error_defn(self, check_if_error_defn: ir.CheckIfErrorDefn):
        pass

    def visit_custom_type_definition(self, elem: ir.CustomType):
        pass

    def visit_module(self, module: ir.Module):
        for elem in module.body:
            if isinstance(elem, ir.FunctionDefn):
                self.visit_function_defn(elem)
            elif isinstance(elem, ir.Assignment):
                self.visit_assignment(elem)
            elif isinstance(elem, ir.Assert):
                self.visit_assert(elem)
            elif isinstance(elem, ir.CustomType):
                self.visit_custom_type_definition(elem)
            elif isinstance(elem, ir.CheckIfErrorDefn):
                self.visit_check_if_error_defn(elem)
            elif isinstance(elem, ir.CheckIfError):
                self.visit_check_if_error(elem)
            elif isinstance(elem, ir.PassStmt):
                self.visit_pass_stmt(elem)
            else:
                raise NotImplementedError('Unexpected toplevel element: %s' % str(elem.__class__))
