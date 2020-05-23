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

from _py2tmp.ir0 import ir, Transformation, is_expr_variadic, GlobalLiterals, select1st_literal
from _py2tmp.ir0_optimization._compute_non_expanded_variadic_vars import compute_non_expanded_variadic_vars
from _py2tmp.ir0_optimization._recalculate_template_instantiation_can_trigger_static_asserts_info import expr_can_trigger_static_asserts


class ExpressionSimplificationTransformation(Transformation):
    def __init__(self) -> None:
        super().__init__()
        self.in_variadic_type_expansion = False

    def transform_not_expr(self, not_expr: ir.NotExpr) -> ir.Expr:
        expr = self.transform_expr(not_expr.inner_expr)
        # !true => false
        # !false => true
        if isinstance(expr, ir.Literal):
            assert isinstance(expr.value, bool)
            return ir.Literal(not expr.value)
        # !!x => x
        if isinstance(expr, ir.NotExpr):
            return expr.inner_expr
        # !(x && y) => (!x || !y)
        # !(x || y) => (!x && !y)
        if isinstance(expr, ir.BoolBinaryOpExpr):
            op = {
                '&&': '||',
                '||': '&&',
            }[expr.op]
            return self.transform_expr(
                ir.BoolBinaryOpExpr(lhs=ir.NotExpr(expr.lhs), rhs=ir.NotExpr(expr.rhs), op=op))
        # !(x == y) => x != y
        # !(x != y) => x == y
        # !(x < y) => x >= y
        # !(x <= y) => x > y
        # !(x > y) => x <= y
        # !(x >= y) => x < y
        if isinstance(expr, ir.ComparisonExpr) and expr.op in ('==', '!='):
            op = {
                '==': '!=',
                '!=': '==',
                '<': '>=',
                '<=': '>',
                '>': '<=',
                '>=': '<',
            }[expr.op]
            return ir.ComparisonExpr(expr.lhs, expr.rhs, op)

        return ir.NotExpr(expr)

    def transform_unary_minus_expr(self, unary_minus: ir.UnaryMinusExpr) -> ir.Expr:
        expr = self.transform_expr(unary_minus.inner_expr)
        # -(3) => -3
        if isinstance(expr, ir.Literal):
            assert isinstance(expr.value, int)
            return ir.Literal(-expr.value)
        # -(x - y) => y - x
        if isinstance(expr, ir.Int64BinaryOpExpr) and expr.op == '-':
            return ir.Int64BinaryOpExpr(lhs=expr.rhs, rhs=expr.lhs, op='-')
        return ir.UnaryMinusExpr(expr)

    def transform_int64_binary_op_expr(self, binary_op: ir.Int64BinaryOpExpr) -> ir.Expr:
        lhs = binary_op.lhs
        rhs = binary_op.rhs
        op = binary_op.op
        # (x - y) => (x + -y)
        # This pushes down the minus, so that e.g. (x - (-y)) => (x + y).
        if op == '-':
            rhs = ir.UnaryMinusExpr(rhs)
            op = '+'

        lhs = self.transform_expr(lhs)
        rhs = self.transform_expr(rhs)

        if op == '+' and isinstance(rhs, ir.UnaryMinusExpr):
            # We could not push down the minus, so switch back to a subtraction.
            op = '-'
            rhs = rhs.inner_expr

        if op == '+':
            # 3 + 5 => 8
            if isinstance(lhs, ir.Literal) and isinstance(rhs, ir.Literal):
                return ir.Literal(lhs.value + rhs.value)
            # 0 + x => x
            if isinstance(lhs, ir.Literal) and lhs.value == 0:
                return rhs
            # x + 0 => x
            if isinstance(rhs, ir.Literal) and rhs.value == 0:
                return lhs

        if op == '-':
            # 8 - 5 => 3
            if isinstance(lhs, ir.Literal) and isinstance(rhs, ir.Literal):
                return ir.Literal(lhs.value - rhs.value)
            # 0 - x => -x
            if isinstance(lhs, ir.Literal) and lhs.value == 0:
                return ir.UnaryMinusExpr(rhs)
            # x - 0 => x
            if isinstance(rhs, ir.Literal) and rhs.value == 0:
                return lhs

        if op == '*':
            # 3 * 5 => 15
            if isinstance(lhs, ir.Literal) and isinstance(rhs, ir.Literal):
                return ir.Literal(lhs.value * rhs.value)
            # 0 * x => 0
            if isinstance(lhs, ir.Literal) and lhs.value == 0:
                if self._can_remove_subexpression(rhs):
                    return ir.Literal(0)
            # x * 0 => 0
            if isinstance(rhs, ir.Literal) and rhs.value == 0:
                if self._can_remove_subexpression(lhs):
                    return ir.Literal(0)
            # 1 * x => x
            if isinstance(lhs, ir.Literal) and lhs.value == 1:
                return rhs
            # x * 1 => x
            if isinstance(rhs, ir.Literal) and rhs.value == 1:
                return lhs

        if op == '/':
            # 16 / 3 => 5
            if isinstance(lhs, ir.Literal) and isinstance(rhs, ir.Literal):
                return ir.Literal(lhs.value // rhs.value)
            # x / 1 => x
            if isinstance(rhs, ir.Literal) and rhs.value == 1:
                return lhs

        if op == '%':
            # 16 % 3 => 1
            if isinstance(lhs, ir.Literal) and isinstance(rhs, ir.Literal):
                return ir.Literal(lhs.value % rhs.value)
            # x % 1 => 0
            if isinstance(rhs, ir.Literal) and rhs.value == 1:
                return ir.Literal(0)

        return ir.Int64BinaryOpExpr(lhs, rhs, op)

    def transform_bool_binary_op_expr(self, binary_op: ir.BoolBinaryOpExpr) -> ir.Expr:
        lhs = binary_op.lhs
        rhs = binary_op.rhs
        op = binary_op.op

        lhs = self.transform_expr(lhs)
        rhs = self.transform_expr(rhs)

        if op == '&&':
            # true && false => false
            if isinstance(lhs, ir.Literal) and isinstance(rhs, ir.Literal):
                return ir.Literal(lhs.value and rhs.value)
            # true && x => x
            if isinstance(lhs, ir.Literal) and lhs.value is True:
                return rhs
            # x && true => x
            if isinstance(rhs, ir.Literal) and rhs.value is True:
                return lhs
            # false && x => false
            if isinstance(lhs, ir.Literal) and lhs.value is False:
                if self._can_remove_subexpression(rhs):
                    return ir.Literal(False)
            # x && false => false
            if isinstance(rhs, ir.Literal) and rhs.value is False:
                if self._can_remove_subexpression(lhs):
                    return ir.Literal(False)

        if op == '||':
            # true || false => true
            if isinstance(lhs, ir.Literal) and isinstance(rhs, ir.Literal):
                return ir.Literal(lhs.value or rhs.value)
            # false || x => x
            if isinstance(lhs, ir.Literal) and lhs.value is False:
                return rhs
            # x || false => x
            if isinstance(rhs, ir.Literal) and rhs.value is False:
                return lhs
            # true || x => true
            if isinstance(lhs, ir.Literal) and lhs.value is True:
                if self._can_remove_subexpression(rhs):
                    return ir.Literal(True)
            # x || true => true
            if isinstance(rhs, ir.Literal) and rhs.value is True:
                if self._can_remove_subexpression(lhs):
                    return ir.Literal(True)

        return ir.BoolBinaryOpExpr(lhs, rhs, op)

    def transform_comparison_expr(self, comparison: ir.ComparisonExpr) -> ir.Expr:
        lhs = comparison.lhs
        rhs = comparison.rhs
        op = comparison.op

        lhs = self.transform_expr(lhs)
        rhs = self.transform_expr(rhs)

        if isinstance(lhs, ir.Literal) and isinstance(rhs, ir.Literal):
            if op == '==':
                return ir.Literal(lhs.value == rhs.value)
            if op == '!=':
                return ir.Literal(lhs.value != rhs.value)
            if op == '<':
                return ir.Literal(lhs.value < rhs.value)
            if op == '<=':
                return ir.Literal(lhs.value <= rhs.value)
            if op == '>':
                return ir.Literal(lhs.value > rhs.value)
            if op == '>=':
                return ir.Literal(lhs.value >= rhs.value)

        if op in ('==', '!=') and self._is_syntactically_equal(lhs, rhs) and not expr_can_trigger_static_asserts(lhs):
            if self._can_remove_subexpression(lhs) and self._can_remove_subexpression(rhs):
                return {
                    '==': ir.Literal(True),
                    '!=': ir.Literal(False),
                }[op]

        if op in ('==', '!=') and isinstance(rhs, ir.Literal) and rhs.expr_type == ir.BoolType():
            rhs, lhs = lhs, rhs

        if op in ('==', '!=') and isinstance(lhs, ir.Literal) and lhs.expr_type == ir.BoolType():
            return {
                ('==', True): lambda: rhs,
                ('==', False): lambda: self.transform_expr(ir.NotExpr(rhs)),
                ('!=', True): lambda: self.transform_expr(ir.NotExpr(rhs)),
                ('!=', False): lambda: rhs,
            }[(op, lhs.value)]()

        return ir.ComparisonExpr(lhs, rhs, op)

    def transform_static_assert(self, static_assert: ir.StaticAssert):
        expr = self.transform_expr(static_assert.expr)

        if isinstance(expr, ir.Literal) and expr.value is True:
            return

        self.writer.write(ir.StaticAssert(expr=expr,
                                          message=static_assert.message))

    def _is_syntactically_equal(self, lhs: ir.Expr, rhs: ir.Expr):
        if not lhs.is_same_expr_excluding_subexpressions(rhs):
            return False
        lhs_exprs = list(lhs.direct_subexpressions)
        rhs_exprs = list(rhs.direct_subexpressions)
        if len(lhs_exprs) != len(rhs_exprs):
            return False
        return all(self._is_syntactically_equal(lhs_expr, rhs_expr)
                   for lhs_expr, rhs_expr in zip(lhs_exprs, rhs_exprs))

    def transform_variadic_type_expansion(self, expr: ir.VariadicTypeExpansion):
        old_in_variadic_type_expansion = self.in_variadic_type_expansion
        self.in_variadic_type_expansion = True
        result = super().transform_variadic_type_expansion(expr)
        self.in_variadic_type_expansion = old_in_variadic_type_expansion
        return result

    def transform_class_member_access(self, class_member_access: ir.ClassMemberAccess):
        if (isinstance(class_member_access.inner_expr, ir.TemplateInstantiation)
            and isinstance(class_member_access.inner_expr.template_expr, ir.AtomicTypeLiteral)):

            if class_member_access.inner_expr.template_expr.cpp_type == 'GetFirstError':
                args = self.transform_exprs(class_member_access.inner_expr.args, original_parent_element=class_member_access.inner_expr)
                return self.transform_get_first_error(args)
            if class_member_access.inner_expr.template_expr.cpp_type == 'std::is_same':
                args = self.transform_exprs(class_member_access.inner_expr.args, original_parent_element=class_member_access.inner_expr)
                return self.transform_is_same(args)
            if class_member_access.inner_expr.template_expr.cpp_type.startswith('Select1st'):
                args = self.transform_exprs(class_member_access.inner_expr.args, original_parent_element=class_member_access.inner_expr)
                return self.transform_select1st(args)

        return super().transform_class_member_access(class_member_access)

    def _can_remove_subexpression(self, expr: ir.Expr):
        # If we're in a variadic type expr, we can't remove variadic sub-exprs (not in general at least).
        # E.g. BoolList<(F<Ts>::value || true)...> can't be optimized to BoolList<true>
        if self.in_variadic_type_expansion and is_expr_variadic(expr):
            return False

        return True

    def transform_get_first_error(self, args: Tuple[ir.Expr, ...]):
        new_args = []
        for arg in args:
            if isinstance(arg, ir.AtomicTypeLiteral) and arg.cpp_type == 'void':
                pass
            elif (isinstance(arg, ir.VariadicTypeExpansion)
                  and isinstance(arg.inner_expr, ir.ClassMemberAccess)
                  and isinstance(arg.inner_expr.inner_expr, ir.TemplateInstantiation)
                  and isinstance(arg.inner_expr.inner_expr.template_expr, ir.AtomicTypeLiteral)
                  and arg.inner_expr.inner_expr.template_expr.cpp_type.startswith('Select1stType')
                  and len(arg.inner_expr.inner_expr.args) == 2
                  and isinstance(arg.inner_expr.inner_expr.args[0], ir.AtomicTypeLiteral)
                  and arg.inner_expr.inner_expr.args[0].cpp_type == 'void'):
                # Select1stType*<void, expr>...
                pass
            else:
                new_args.append(arg)
        return ir.ClassMemberAccess(inner_expr=ir.TemplateInstantiation(template_expr=GlobalLiterals.GET_FIRST_ERROR,
                                                                        args=tuple(new_args),
                                                                        instantiation_might_trigger_static_asserts=False),
                                    expr_type=ir.TypeType(),
                                    member_name='type')

    def transform_is_same(self, args: Tuple[ir.Expr, ...]):
        assert len(args) == 2
        lhs, rhs = args
        list_template_names = {'List', 'BoolList', 'Int64List'}
        if (isinstance(lhs, ir.TemplateInstantiation) and isinstance(lhs.template_expr, ir.AtomicTypeLiteral) and lhs.template_expr.cpp_type in list_template_names
                and isinstance(rhs, ir.TemplateInstantiation) and isinstance(rhs.template_expr, ir.AtomicTypeLiteral) and rhs.template_expr.cpp_type in list_template_names
                and lhs.template_expr.cpp_type == rhs.template_expr.cpp_type
                and not any(isinstance(arg, ir.VariadicTypeExpansion) for arg in lhs.args)
                and not any(isinstance(arg, ir.VariadicTypeExpansion) for arg in rhs.args)
                and len(lhs.args) == len(rhs.args)
                and lhs.args):

            # std::is_same<List<X1, X2, X3>, List<Y1, Y2, Y3>>::value
            # -> std::is_same<X1, Y1>::value && std::is_same<X2, Y2>::value && std::is_same<X3, Y3>::value
            if lhs.template_expr.cpp_type == 'List':
                result = None
                for lhs_arg, rhs_arg in zip(lhs.args, rhs.args):
                    if result:
                        result = ir.BoolBinaryOpExpr(lhs=result,
                                                     rhs=self._create_is_same_expr(lhs_arg, rhs_arg),
                                                     op='&&')
                    else:
                        result = self._create_is_same_expr(lhs_arg, rhs_arg)
                return self.transform_expr(result)

            # std::is_same<IntList<n1, n2, n3>, IntList<m1, m2, m3>>::value
            # -> (n1 == m1) && (n2 == m2) && (n3 == m3)
            # (and same for BoolList)
            result = None
            for lhs_arg, rhs_arg in zip(lhs.args, rhs.args):
                if result:
                    result = ir.BoolBinaryOpExpr(lhs=result,
                                                 rhs=ir.ComparisonExpr(lhs_arg, rhs_arg, op='=='),
                                                 op='&&')
                else:
                    result = ir.ComparisonExpr(lhs_arg, rhs_arg, op='==')
            return self.transform_expr(result)

        return self._create_is_same_expr(lhs, rhs)

    def _create_is_same_expr(self, lhs: ir.Expr, rhs: ir.Expr):
        return ir.ClassMemberAccess(
            inner_expr=ir.TemplateInstantiation(template_expr=GlobalLiterals.STD_IS_SAME,
                                                args=(lhs, rhs),
                                                instantiation_might_trigger_static_asserts=False),
            expr_type=ir.BoolType(),
            member_name='value')

    def transform_select1st(self, args: Tuple[ir.Expr, ...]):
        lhs, rhs = args

        best_var = None
        # First preference to non-expanded variadic vars, to keep the Select1st* expression variadic if it is now.
        for var_name in compute_non_expanded_variadic_vars(rhs):
            [best_var] = (var
                          for var in rhs.free_vars
                          if var.cpp_type == var_name)
            break

        # If there are none, then any non-variadic var is also ok.
        if not best_var:
            for var in rhs.free_vars:
                if not var.is_variadic and isinstance(var.expr_type, (ir.BoolType, ir.Int64Type, ir.TypeType)):
                    best_var = var
                    break

        if best_var:
            rhs = best_var

        return ir.ClassMemberAccess(inner_expr=ir.TemplateInstantiation(template_expr=select1st_literal(lhs.expr_type, rhs.expr_type),
                                                                        args=(lhs, rhs),
                                                                        instantiation_might_trigger_static_asserts=False),
                                    expr_type=lhs.expr_type,
                                    member_name='value')
