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
from _py2tmp import ir0, transform_ir0, ir0_builtin_literals, ir0_to_cpp
from _py2tmp.ir0_optimization.compute_non_expanded_variadic_vars import compute_non_expanded_variadic_vars
from _py2tmp.ir0_optimization.recalculate_template_instantiation_can_trigger_static_asserts_info import expr_can_trigger_static_asserts

class ExpressionSimplificationTransformation(transform_ir0.Transformation):
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

        if op in ('==', '!=') and isinstance(rhs, ir0.Literal) and rhs.expr_type == ir0.BoolType():
            rhs, lhs = lhs, rhs

        if op in ('==', '!=') and isinstance(lhs, ir0.Literal) and lhs.expr_type == ir0.BoolType():
            return {
                ('==', True): lambda: rhs,
                ('==', False): lambda: self.transform_expr(ir0.NotExpr(rhs), writer),
                ('!=', True): lambda: self.transform_expr(ir0.NotExpr(rhs), writer),
                ('!=', False): lambda: rhs,
            }[(op, lhs.value)]()

        return ir0.ComparisonExpr(lhs, rhs, op)

    def transform_static_assert(self, static_assert: ir0.StaticAssert, writer: transform_ir0.Writer):
        expr = self.transform_expr(static_assert.expr, writer)

        if isinstance(expr, ir0.Literal) and expr.value is True:
            return

        writer.write(ir0.StaticAssert(expr=expr,
                                      message=static_assert.message))

    def _is_syntactically_equal(self, lhs: ir0.Expr, rhs: ir0.Expr):
        if not lhs.is_same_expr_excluding_subexpressions(rhs):
            return False
        lhs_exprs = list(lhs.get_direct_subexpressions())
        rhs_exprs = list(rhs.get_direct_subexpressions())
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
            if class_member_access.expr.template_expr.cpp_type == 'std::is_same':
                args = self.transform_exprs(class_member_access.expr.args, original_parent_element=class_member_access.expr, writer=writer)
                return self.transform_is_same(args, writer)
            if class_member_access.expr.template_expr.cpp_type == 'Bool':
                args = self.transform_exprs(class_member_access.expr.args, original_parent_element=class_member_access.expr, writer=writer)
                return self.transform_bool_wrapper(args, writer)
            if class_member_access.expr.template_expr.cpp_type == 'Int64':
                args = self.transform_exprs(class_member_access.expr.args, original_parent_element=class_member_access.expr, writer=writer)
                return self.transform_int64_wrapper(args, writer)
            if class_member_access.expr.template_expr.cpp_type.startswith('Select1st'):
                args = self.transform_exprs(class_member_access.expr.args, original_parent_element=class_member_access.expr, writer=writer)
                return self.transform_select1st(args, writer)

        return super().transform_class_member_access(class_member_access, writer)

    def _can_remove_subexpression(self, expr: ir0.Expr):
        # If we're in a variadic type expr, we can't remove variadic sub-exprs (not in general at least).
        # E.g. List<Bool<(F<Ts>::value || true)>...> can't be optimized to List<Bool<true>> nor List<Bool<true>...>.
        if self.in_variadic_type_expansion and transform_ir0.is_expr_variadic(expr):
            return False

        return True

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
        return ir0.ClassMemberAccess(class_type_expr=ir0.TemplateInstantiation(template_expr=ir0_builtin_literals.GlobalLiterals.GET_FIRST_ERROR,
                                                                               args=new_args,
                                                                               instantiation_might_trigger_static_asserts=False),
                                     member_type=ir0.TypeType(),
                                     member_name='type')

    def transform_is_same(self, args: List[ir0.Expr], writer: transform_ir0.Writer):
        lhs, rhs = args
        if (isinstance(lhs, ir0.TemplateInstantiation) and isinstance(lhs.template_expr, ir0.AtomicTypeLiteral) and not lhs.template_expr.may_be_alias
                and isinstance(rhs, ir0.TemplateInstantiation) and isinstance(rhs.template_expr, ir0.AtomicTypeLiteral) and not rhs.template_expr.may_be_alias
                and lhs.template_expr.cpp_type == rhs.template_expr.cpp_type
                and not any(isinstance(arg, ir0.VariadicTypeExpansion) for arg in lhs.args)
                and not any(isinstance(arg, ir0.VariadicTypeExpansion) for arg in rhs.args)
                and len(lhs.args) == len(rhs.args)
                and lhs.args):

            # std::is_same<List<X1, X2, X3>, List<Y1, Y2, Y3>>::value
            # -> std::is_same<X1, Y1>::value && std::is_same<X2, Y2>::value && std::is_same<X3, Y3>::value
            result = None
            for lhs_arg, rhs_arg in zip(lhs.args, rhs.args):
                assert lhs_arg.expr_type == rhs_arg.expr_type
                if lhs_arg.expr_type == ir0.TypeType():
                    comparison = self._create_is_same_expr(lhs_arg, rhs_arg)
                else:
                    comparison = ir0.ComparisonExpr(lhs_arg, rhs_arg, op='==')
                if result:
                    result = ir0.BoolBinaryOpExpr(lhs=result, rhs=comparison, op='&&')
                else:
                    result = comparison
            return self.transform_expr(result, writer)

        return self._create_is_same_expr(lhs, rhs)

    def _create_is_same_expr(self, lhs, rhs):
        return ir0.ClassMemberAccess(
            class_type_expr=ir0.TemplateInstantiation(template_expr=ir0_builtin_literals.GlobalLiterals.STD_IS_SAME,
                                                      args=[lhs, rhs],
                                                      instantiation_might_trigger_static_asserts=False),
            member_type=ir0.BoolType(),
            member_name='value')

    def transform_bool_wrapper(self, args: List[ir0.Expr], writer: transform_ir0.Writer):
        expr, = args
        # Bool<b>::value -> b
        return expr

    def transform_int64_wrapper(self, args: List[ir0.Expr], writer: transform_ir0.Writer):
        expr, = args
        # Int64<n>::value -> n
        return expr

    def transform_select1st(self, args: List[ir0.Expr], writer: transform_ir0.Writer):
        lhs, rhs = args

        best_var = None
        # First preference to non-expanded variadic vars, to keep the Select1st* expression variadic if it is now.
        for var_name in compute_non_expanded_variadic_vars(rhs):
            [best_var] = (var
                          for var in rhs.get_free_vars()
                          if var.cpp_type == var_name)
            break

        # If there are none, then any non-variadic var is also ok.
        if not best_var:
            for var in rhs.get_free_vars():
                if not var.is_variadic and isinstance(var.expr_type, (ir0.BoolType, ir0.Int64Type, ir0.TypeType)):
                    best_var = var
                    break

        if best_var:
            rhs = best_var

        select1st_literal = ir0_builtin_literals.select1st_literal(lhs.expr_type, rhs.expr_type)
        return ir0.ClassMemberAccess(class_type_expr=ir0.TemplateInstantiation(template_expr=select1st_literal,
                                                                               args=[lhs, rhs],
                                                                               instantiation_might_trigger_static_asserts=False),
                                     member_type=lhs.expr_type,
                                     member_name='value')
