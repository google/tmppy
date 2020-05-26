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

from typing import Union, Tuple
from _py2tmp.ir0 import ir


class Visitor:
    def visit_header(self, header: ir.Header):
        for template_defn in header.template_defns:
            self.visit_template_defn(template_defn)

        for elem in header.toplevel_content:
            self.visit_toplevel_elem(elem)

    def visit_toplevel_elem(self, elem: Union[ir.StaticAssert, ir.ConstantDef, ir.Typedef]):
        if isinstance(elem, ir.StaticAssert):
            self.visit_static_assert(elem)
        elif isinstance(elem, ir.ConstantDef):
            self.visit_constant_def(elem)
        elif isinstance(elem, ir.Typedef):
            self.visit_typedef(elem)
        elif isinstance(elem, ir.NoOpStmt):
            self.visit_no_op_stmt(elem)
        else:
            raise NotImplementedError('Unexpected elem: ' + elem.__class__.__name__)

    def visit_template_defn(self, template_defn: ir.TemplateDefn):
        for arg_decl in template_defn.args:
            self.visit_template_arg_decl(arg_decl)
        if template_defn.main_definition is not None:
            self.visit_template_specialization(template_defn.main_definition)
        for specialization in template_defn.specializations:
            self.visit_template_specialization(specialization)

    def visit_static_assert(self, static_assert: ir.StaticAssert):
        self.visit_expr(static_assert.expr)

    def visit_no_op_stmt(self, stmt: ir.NoOpStmt):
        pass

    def visit_constant_def(self, constant_def: ir.ConstantDef):
        self.visit_expr(constant_def.expr)

    def visit_typedef(self, typedef: ir.Typedef):
        self.visit_expr(typedef.expr)

    def visit_template_arg_decl(self, arg_decl: ir.TemplateArgDecl):
        pass

    def visit_template_body_elems(self,
                                  elems: Tuple[ir.TemplateBodyElement, ...]):
        for elem in elems:
            self.visit_template_body_elem(elem)

    def visit_template_specialization(self, specialization: ir.TemplateSpecialization):
        if specialization.patterns is not None:
            for pattern in specialization.patterns:
                self.visit_pattern(pattern)

        for arg_decl in specialization.args:
            self.visit_template_arg_decl(arg_decl)
        self.visit_template_body_elems(specialization.body)

    def visit_pattern(self, expr: ir.Expr):
        self.visit_expr(expr)

    def visit_expr(self, expr: ir.Expr):
        if isinstance(expr, ir.Literal):
            self.visit_literal(expr)
        elif isinstance(expr, ir.AtomicTypeLiteral):
            self.visit_type_literal(expr)
        elif isinstance(expr, ir.ClassMemberAccess):
            self.visit_class_member_access(expr)
        elif isinstance(expr, ir.NotExpr):
            self.visit_not_expr(expr)
        elif isinstance(expr, ir.UnaryMinusExpr):
            self.visit_unary_minus_expr(expr)
        elif isinstance(expr, ir.ComparisonExpr):
            self.visit_comparison_expr(expr)
        elif isinstance(expr, ir.Int64BinaryOpExpr):
            self.visit_int64_binary_op_expr(expr)
        elif isinstance(expr, ir.BoolBinaryOpExpr):
            self.visit_bool_binary_op_expr(expr)
        elif isinstance(expr, ir.TemplateInstantiation):
            self.visit_template_instantiation(expr)
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
        elif isinstance(expr, ir.VariadicTypeExpansion):
            self.visit_variadic_type_expansion(expr)
        else:
            raise NotImplementedError('Unexpected expr: ' + expr.__class__.__name__)

    def visit_exprs(self, exprs: Tuple[ir.Expr, ...]):
        for expr in exprs:
            self.visit_expr(expr)

    def visit_template_body_elem(self, elem: ir.TemplateBodyElement):
        if isinstance(elem, ir.TemplateDefn):
            self.visit_template_defn(elem)
        elif isinstance(elem, ir.StaticAssert):
            self.visit_static_assert(elem)
        elif isinstance(elem, ir.ConstantDef):
            self.visit_constant_def(elem)
        elif isinstance(elem, ir.Typedef):
            self.visit_typedef(elem)
        elif isinstance(elem, ir.NoOpStmt):
            self.visit_no_op_stmt(elem)
        else:
            raise NotImplementedError('Unexpected elem: ' + elem.__class__.__name__)

    def visit_literal(self, literal: ir.Literal) -> ir.Expr:
        pass

    def visit_type_literal(self, type_literal: ir.AtomicTypeLiteral):
        pass

    def visit_class_member_access(self, class_member_access: ir.ClassMemberAccess):
        self.visit_expr(class_member_access.inner_expr)

    def visit_not_expr(self, not_expr: ir.NotExpr):
        self.visit_expr(not_expr.inner_expr)

    def visit_unary_minus_expr(self, unary_minus: ir.UnaryMinusExpr):
        self.visit_expr(unary_minus.inner_expr)
        
    def visit_comparison_expr(self, comparison: ir.ComparisonExpr):
        self.visit_exprs((comparison.lhs, comparison.rhs))

    def visit_int64_binary_op_expr(self, binary_op: ir.Int64BinaryOpExpr):
        self.visit_exprs((binary_op.lhs, binary_op.rhs))

    def visit_bool_binary_op_expr(self, binary_op: ir.BoolBinaryOpExpr):
        self.visit_exprs((binary_op.lhs, binary_op.rhs))

    def visit_template_instantiation(self, template_instantiation: ir.TemplateInstantiation):
        self.visit_exprs((template_instantiation.template_expr, *template_instantiation.args))

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
        self.visit_exprs((expr.return_type_expr, *expr.arg_exprs))

    def visit_variadic_type_expansion(self, expr: ir.VariadicTypeExpansion):
        self.visit_expr(expr.inner_expr)
