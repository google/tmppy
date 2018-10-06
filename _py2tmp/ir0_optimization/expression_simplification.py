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

from typing import List, Union
from _py2tmp import ir0, transform_ir0, ir0_builtins
from _py2tmp.ir0_optimization.recalculate_template_instantiation_can_trigger_static_asserts_info import expr_can_trigger_static_asserts

class _ExpressionSimplificationTransformation(transform_ir0.Transformation):
    def __init__(self):
        super().__init__()
        self.in_variadic_type_expansion = False

    def transform_not_expr(self, not_expr: ir0.NotExpr, writer: transform_ir0.Writer) -> ir0.Expr:
        expr = self.transform_expr(not_expr.expr, writer)
        # !true => false
        # !false => true
        if isinstance(expr, ir0.Literal):
            assert isinstance(expr.value, bool)
            return ir0.Literal(not expr.value)
        # !!x => x
        if isinstance(expr, ir0.NotExpr):
            return expr.expr
        # !(x && y) => (!x || !y)
        # !(x || y) => (!x && !y)
        if isinstance(expr, ir0.BoolBinaryOpExpr):
            op = {
                '&&': '||',
                '||': '&&',
            }[expr.op]
            return self.transform_expr(ir0.BoolBinaryOpExpr(lhs=ir0.NotExpr(expr.lhs), rhs=ir0.NotExpr(expr.rhs), op=op), writer)
        # !(x == y) => x != y
        # !(x != y) => x == y
        # !(x < y) => x >= y
        # !(x <= y) => x > y
        # !(x > y) => x <= y
        # !(x >= y) => x < y
        if isinstance(expr, ir0.ComparisonExpr) and expr.op in ('==', '!='):
            op = {
                '==': '!=',
                '!=': '==',
                '<': '>=',
                '<=': '>',
                '>': '<=',
                '>=': '<',
            }[expr.op]
            return ir0.ComparisonExpr(expr.lhs, expr.rhs, op)

        return ir0.NotExpr(expr)

    def transform_unary_minus_expr(self, unary_minus: ir0.UnaryMinusExpr, writer: transform_ir0.Writer) -> ir0.Expr:
        expr = self.transform_expr(unary_minus.expr, writer)
        # -(3) => -3
        if isinstance(expr, ir0.Literal):
            assert isinstance(expr.value, int)
            return ir0.Literal(-expr.value)
        # -(x - y) => y - x
        if isinstance(expr, ir0.Int64BinaryOpExpr) and expr.op == '-':
            return ir0.Int64BinaryOpExpr(lhs=expr.rhs, rhs=expr.lhs, op='-')
        return ir0.UnaryMinusExpr(expr)

    def transform_int64_binary_op_expr(self, binary_op: ir0.Int64BinaryOpExpr, writer: transform_ir0.Writer) -> ir0.Expr:
        lhs = binary_op.lhs
        rhs = binary_op.rhs
        op = binary_op.op
        # (x - y) => (x + -y)
        # This pushes down the minus, so that e.g. (x - (-y)) => (x + y).
        if op == '-':
            rhs = ir0.UnaryMinusExpr(rhs)
            op = '+'

        lhs = self.transform_expr(lhs, writer)
        rhs = self.transform_expr(rhs, writer)

        if op == '+' and isinstance(rhs, ir0.UnaryMinusExpr):
            # We could not push down the minus, so switch back to a subtraction.
            op = '-'
            rhs = rhs.expr

        if op == '+':
            # 3 + 5 => 8
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value + rhs.value)
            # 0 + x => x
            if isinstance(lhs, ir0.Literal) and lhs.value == 0:
                return rhs
            # x + 0 => x
            if isinstance(rhs, ir0.Literal) and rhs.value == 0:
                return lhs

        if op == '-':
            # 8 - 5 => 3
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value - rhs.value)
            # 0 - x => -x
            if isinstance(lhs, ir0.Literal) and lhs.value == 0:
                return ir0.UnaryMinusExpr(rhs)
            # x - 0 => x
            if isinstance(rhs, ir0.Literal) and rhs.value == 0:
                return lhs

        if op == '*':
            # 3 * 5 => 15
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value * rhs.value)
            # 0 * x => 0
            if isinstance(lhs, ir0.Literal) and lhs.value == 0:
                if self._can_remove_subexpression(rhs):
                    return ir0.Literal(0)
            # x * 0 => 0
            if isinstance(rhs, ir0.Literal) and rhs.value == 0:
                if self._can_remove_subexpression(lhs):
                    return ir0.Literal(0)
            # 1 * x => x
            if isinstance(lhs, ir0.Literal) and lhs.value == 1:
                return rhs
            # x * 1 => x
            if isinstance(rhs, ir0.Literal) and rhs.value == 1:
                return lhs

        if op == '/':
            # 16 / 3 => 5
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value // rhs.value)
            # x / 1 => x
            if isinstance(rhs, ir0.Literal) and rhs.value == 1:
                return lhs

        if op == '%':
            # 16 % 3 => 1
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value % rhs.value)
            # x % 1 => 0
            if isinstance(rhs, ir0.Literal) and rhs.value == 1:
                return ir0.Literal(0)

        return ir0.Int64BinaryOpExpr(lhs, rhs, op)

    def transform_bool_binary_op_expr(self, binary_op: ir0.BoolBinaryOpExpr, writer: transform_ir0.Writer) -> ir0.Expr:
        lhs = binary_op.lhs
        rhs = binary_op.rhs
        op = binary_op.op

        lhs = self.transform_expr(lhs, writer)
        rhs = self.transform_expr(rhs, writer)

        if op == '&&':
            # true && false => false
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value and rhs.value)
            # true && x => x
            if isinstance(lhs, ir0.Literal) and lhs.value is True:
                return rhs
            # x && true => x
            if isinstance(rhs, ir0.Literal) and rhs.value is True:
                return lhs
            # false && x => false
            if isinstance(lhs, ir0.Literal) and lhs.value is False:
                if self._can_remove_subexpression(rhs):
                    return ir0.Literal(False)
            # x && false => false
            if isinstance(rhs, ir0.Literal) and rhs.value is False:
                if self._can_remove_subexpression(lhs):
                    return ir0.Literal(False)

        if op == '||':
            # true || false => true
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value or rhs.value)
            # false || x => x
            if isinstance(lhs, ir0.Literal) and lhs.value is False:
                return rhs
            # x || false => x
            if isinstance(rhs, ir0.Literal) and rhs.value is False:
                return lhs
            # true || x => true
            if isinstance(lhs, ir0.Literal) and lhs.value is True:
                if self._can_remove_subexpression(rhs):
                    return ir0.Literal(True)
            # x || true => true
            if isinstance(rhs, ir0.Literal) and rhs.value is True:
                if self._can_remove_subexpression(lhs):
                    return ir0.Literal(True)

        return ir0.BoolBinaryOpExpr(lhs, rhs, op)

    def transform_comparison_expr(self, comparison: ir0.ComparisonExpr, writer: transform_ir0.Writer) -> ir0.Expr:
        lhs = comparison.lhs
        rhs = comparison.rhs
        op = comparison.op

        lhs = self.transform_expr(lhs, writer)
        rhs = self.transform_expr(rhs, writer)

        if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
            if op == '==':
                return ir0.Literal(lhs.value == rhs.value)
            if op == '!=':
                return ir0.Literal(lhs.value != rhs.value)
            if op == '<':
                return ir0.Literal(lhs.value < rhs.value)
            if op == '<=':
                return ir0.Literal(lhs.value <= rhs.value)
            if op == '>':
                return ir0.Literal(lhs.value > rhs.value)
            if op == '>=':
                return ir0.Literal(lhs.value >= rhs.value)

        if op in ('==', '!=') and self._is_syntactically_equal(lhs, rhs) and not expr_can_trigger_static_asserts(lhs):
            if self._can_remove_subexpression(lhs) and self._can_remove_subexpression(rhs):
                return {
                    '==': ir0.Literal(True),
                    '!=': ir0.Literal(False),
                }[op]

        return ir0.ComparisonExpr(lhs, rhs, op)

    def transform_static_assert(self, static_assert: ir0.StaticAssert, writer: transform_ir0.Writer):
        expr = self.transform_expr(static_assert.expr, writer)

        if isinstance(expr, ir0.Literal) and expr.value is True:
            return

        writer.write(ir0.StaticAssert(expr=expr,
                                      message=static_assert.message))

    def _is_syntactically_equal(self, lhs, rhs):
        if not lhs.is_same_expr_excluding_subexpressions(rhs):
            return False
        lhs_exprs = lhs.get_direct_subelements()
        rhs_exprs = rhs.get_direct_subelements()
        if len(lhs_exprs) != len(rhs_exprs):
            return False
        return all(self._is_syntactically_equal(lhs_expr, rhs_expr)
                   for lhs_expr, rhs_expr in zip(lhs_exprs, rhs_exprs))

    def transform_variadic_type_expansion(self, expr: ir0.VariadicTypeExpansion, writer: transform_ir0.Writer):
        old_in_variadic_type_expansion = self.in_variadic_type_expansion
        self.in_variadic_type_expansion = True
        result = super().transform_variadic_type_expansion(expr, writer)
        self.in_variadic_type_expansion = old_in_variadic_type_expansion
        return result

    def transform_class_member_access(self, class_member_access: ir0.ClassMemberAccess, writer: transform_ir0.Writer):
        if (isinstance(class_member_access.expr, ir0.TemplateInstantiation)
            and isinstance(class_member_access.expr.template_expr, ir0.AtomicTypeLiteral)):
            if class_member_access.expr.template_expr.cpp_type == 'GetFirstError':
                args = self.transform_exprs(class_member_access.expr.args, original_parent_element=class_member_access.expr, writer=writer)
                return self.transform_get_first_error(args)

        return super().transform_class_member_access(class_member_access, writer)

    def _can_remove_subexpression(self, expr: ir0.Expr):
        # If we're in a variadic type expr, we can't remove variadic sub-exprs (not in general at least).
        # E.g. BoolList<(F<Ts>::value || true)...> can't be optimized to BoolList<true>
        return not self.in_variadic_type_expansion or not transform_ir0.is_expr_variadic(expr)

    def transform_get_first_error(self, args: List[ir0.Expr]):
        new_args = []
        for arg in args:
            if isinstance(arg, ir0.AtomicTypeLiteral) and arg.cpp_type == 'void':
                pass
            elif (isinstance(arg, ir0.VariadicTypeExpansion)
                  and isinstance(arg.expr, ir0.ClassMemberAccess)
                  and isinstance(arg.expr.expr, ir0.TemplateInstantiation)
                  and isinstance(arg.expr.expr.template_expr, ir0.AtomicTypeLiteral)
                  and arg.expr.expr.template_expr.cpp_type.startswith('Select1stType')
                  and len(arg.expr.expr.args) == 2
                  and isinstance(arg.expr.expr.args[0], ir0.AtomicTypeLiteral)
                  and arg.expr.expr.args[0].cpp_type == 'void'):
                # Select1stType*<void, expr>...
                pass
            else:
                new_args.append(arg)
        return ir0.ClassMemberAccess(class_type_expr=ir0.TemplateInstantiation(template_expr=ir0_builtins.GlobalLiterals.GET_FIRST_ERROR,
                                                                               args=new_args,
                                                                               instantiation_might_trigger_static_asserts=False),
                                     member_type=ir0.TypeType(),
                                     member_name='type')

def perform_expression_simplification(template_defn: ir0.TemplateDefn):
    writer = transform_ir0.ToplevelWriter(iter([]), allow_toplevel_elems=False)
    transformation = _ExpressionSimplificationTransformation()
    transformation.transform_template_defn(template_defn, writer)
    return writer.template_defns, False

def perform_expression_simplification_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]]):
    transformation = _ExpressionSimplificationTransformation()
    writer = transform_ir0.ToplevelWriter(iter([]), allow_toplevel_elems=False)
    toplevel_elems = transformation.transform_template_body_elems(toplevel_elems, writer)
    assert not writer.template_defns
    assert not writer.toplevel_elems
    return toplevel_elems, False
