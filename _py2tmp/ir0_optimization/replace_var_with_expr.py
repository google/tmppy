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
from typing import List, Union, Dict, Set, Optional
from _py2tmp import ir0, transform_ir0, ir0_to_cpp
from _py2tmp.ir0_optimization.compute_non_expanded_variadic_vars import compute_non_expanded_variadic_vars

class VariadicVarReplacementNotPossibleException(Exception):
    pass

class _ReplaceVarWithExprTransformation(transform_ir0.Transformation):
    def __init__(self,
                 replacement_expr_by_var: Dict[str, Union[ir0.Expr, List[ir0.Expr]]],
                 replacement_expr_by_expanded_var: Dict[str, Union[ir0.Expr, List[ir0.Expr]]],
                 variadic_vars_with_expansion_in_progress: Set[str] = set()):
        super().__init__()
        self.replacement_expr_by_var = replacement_expr_by_var
        self.replacement_expr_by_expanded_var = replacement_expr_by_expanded_var
        self.variadic_vars_with_expansion_in_progress = variadic_vars_with_expansion_in_progress

    def transform_variadic_type_expansion(self, expr: ir0.VariadicTypeExpansion, writer: transform_ir0.Writer):
        variadic_vars_to_expand = compute_non_expanded_variadic_vars(expr.expr).keys()
        previous_variadic_vars_with_expansion_in_progress = self.variadic_vars_with_expansion_in_progress
        self.variadic_vars_with_expansion_in_progress = previous_variadic_vars_with_expansion_in_progress.union(variadic_vars_to_expand)

        values_by_variadic_var_to_expand = {var: self.replacement_expr_by_var[var]
                                            for var in variadic_vars_to_expand
                                            if var in self.replacement_expr_by_var}
        values_by_expanded_variadic_var_to_expand = {var: self.replacement_expr_by_expanded_var[var]
                                                     for var in variadic_vars_to_expand
                                                     if var in self.replacement_expr_by_expanded_var}

        transformed_exprs = []
        if values_by_variadic_var_to_expand or values_by_expanded_variadic_var_to_expand:
            self._check_variadic_var_replacement(values_by_variadic_var_to_expand, values_by_expanded_variadic_var_to_expand)

            (num_values_to_expand,) = {(len(values) if isinstance(values, list) else 1)
                                       for values in itertools.chain(values_by_variadic_var_to_expand.values(), values_by_expanded_variadic_var_to_expand.values())}

            for i in range(0, num_values_to_expand):
                child_replacement_expr_by_var = self.replacement_expr_by_var.copy()
                child_replacement_expr_by_expanded_var = self.replacement_expr_by_expanded_var.copy()
                for var, values in values_by_variadic_var_to_expand.items():
                    if not isinstance(values, list):
                        values = [values]
                    child_replacement_expr_by_var[var] = values[i]
                for var, values in values_by_expanded_variadic_var_to_expand.items():
                    if not isinstance(values, list):
                        values = [values]
                    child_replacement_expr_by_expanded_var[var] = values[i]
                child_transformation = _ReplaceVarWithExprTransformation(child_replacement_expr_by_var, child_replacement_expr_by_expanded_var, self.variadic_vars_with_expansion_in_progress)
                transformed_expr = child_transformation.transform_expr(expr.expr, writer)
                for expr1 in (transformed_expr if isinstance(transformed_expr, list) else [transformed_expr]):
                    transformed_exprs.append(expr1)

            if len(transformed_exprs) == 1:
                if compute_non_expanded_variadic_vars(transformed_exprs[0]):
                    transformed_exprs = [ir0.VariadicTypeExpansion(transformed_exprs[0])]
            else:
                if any(compute_non_expanded_variadic_vars(expr) for expr in transformed_exprs):
                    raise VariadicVarReplacementNotPossibleException('Found non-expanded variadic vars after expanding one to multiple elements')
        else:
            transformed_expr = self.transform_expr(expr.expr, writer)
            if isinstance(transformed_expr, list):
                [transformed_expr] = transformed_expr

            assert not isinstance(transformed_expr, list)
            transformed_exprs.append(ir0.VariadicTypeExpansion(transformed_expr))

        self.variadic_vars_with_expansion_in_progress = previous_variadic_vars_with_expansion_in_progress

        return transformed_exprs

    def transform_type_literal(self, type_literal: ir0.AtomicTypeLiteral, writer: transform_ir0.Writer):
        if type_literal.cpp_type in self.replacement_expr_by_var:
            result = self.replacement_expr_by_var[type_literal.cpp_type]
        elif type_literal.cpp_type in self.replacement_expr_by_expanded_var:
            result = self.replacement_expr_by_expanded_var[type_literal.cpp_type]
        else:
            return type_literal

        if isinstance(result, list) and len(result) == 1:
            [result] = result

        if not type_literal.is_variadic and self.variadic_vars_with_expansion_in_progress:
            if any(compute_non_expanded_variadic_vars(expr)
                   for expr in (result if isinstance(result, list) else [result])):
                raise VariadicVarReplacementNotPossibleException('The replacement would cause a non-variadic var to be replaced with a variadic expr')

        return result

    def transform_exprs(self, exprs: List[ir0.Expr], original_parent_element: Optional[ir0.Expr], writer):
        if isinstance(original_parent_element, (ir0.TemplateInstantiation, ir0.FunctionTypeExpr)):
            results = []
            for expr in exprs:
                expr_or_expr_list = self.transform_expr(expr, writer)
                for expr in (expr_or_expr_list if isinstance(expr_or_expr_list, list) else [expr_or_expr_list]):
                    assert isinstance(expr, ir0.Expr)
                    results.append(expr)
            return results
        else:
            results = []
            for expr_or_expr_list in super().transform_exprs(exprs, original_parent_element, writer):
                for expr in (expr_or_expr_list if isinstance(expr_or_expr_list, list) else [expr_or_expr_list]):
                    assert isinstance(expr, ir0.Expr)
                    assert not isinstance(expr, ir0.VariadicTypeExpansion)
                    results.append(expr)

            if len(results) != len(exprs):
                raise VariadicVarReplacementNotPossibleException('The replacement caused a different number of child exprs in a %s. Was %s, now %s' % (original_parent_element.__class__.__name__, len(exprs), len(results)))

            return results

    def _compute_variadic_pattern(self, values: Union[ir0.Expr, List[ir0.Expr]], strict: bool):
        if not isinstance(values, list):
            values = [values]
        for value in values:
            if isinstance(value, ir0.VariadicTypeExpansion) and isinstance(value.expr, ir0.AtomicTypeLiteral):
                if strict:
                    yield value.expr.cpp_type
                else:
                    # We just check that there's a corresponding variadic type expansion, but not necessarily for the
                    # same var.
                    yield 1
            else:
                yield None

    def _check_variadic_var_replacement(self,
                                        values_by_variadic_var_to_expand: Dict[str, Union[ir0.Expr, List[ir0.Expr]]],
                                        values_by_expanded_variadic_var_to_expand: Dict[str, Union[ir0.Expr, List[ir0.Expr]]]):
        first_replacement = (next(iter(values_by_variadic_var_to_expand.values()))
                             if values_by_variadic_var_to_expand
                             else next(iter(values_by_expanded_variadic_var_to_expand.values())))
        if not isinstance(first_replacement, list):
            first_replacement = [first_replacement]
        num_values_to_expand_in_first_replacement = len(first_replacement)
        if not all((len(values) if isinstance(values, list) else 1) == num_values_to_expand_in_first_replacement
                   for values in itertools.chain(values_by_variadic_var_to_expand.values(), values_by_expanded_variadic_var_to_expand.values())):
            # We can't perform the replacement syntactically, even if it might make sense semantically.
            # E.g. we can't replace Ts={Xs...}, Us={Ys..., float} in "std::pair<Ts, Us>...".
            raise VariadicVarReplacementNotPossibleException('We can\'t perform the replacement syntactically, even if it might make sense semantically. '
                                                             'num_values_to_expand_in_first_replacement = %s, values_by_variadic_var_to_expand = %s, values_by_expanded_variadic_var_to_expand = %s' % (
                                                                 num_values_to_expand_in_first_replacement,
                                                                 str(values_by_variadic_var_to_expand),
                                                                 str(values_by_expanded_variadic_var_to_expand)))

        values_lists = [[values] if isinstance(values, ir0.Expr) else list(values)
                        for values in itertools.chain(values_by_variadic_var_to_expand.values(), values_by_expanded_variadic_var_to_expand.values())]
        while values_lists[0]:
            # If no front items are variadic expansions, we can disregard those and check the rest.
            for values in values_lists:
                value = values[0]
                if isinstance(value, ir0.VariadicTypeExpansion) and isinstance(value, ir0.AtomicTypeLiteral):
                    break
            else:
                values_lists = [values[1:] for values in values_lists]
                continue

            # And same for the last ones.
            for values in values_lists:
                value = values[-1]
                if isinstance(value, ir0.VariadicTypeExpansion) and isinstance(value, ir0.AtomicTypeLiteral):
                    break
            else:
                values_lists = [values[:-1] for values in values_lists]
                continue

            # If all value lists start with the same variadic type expansion, we can disregard that.
            if isinstance(values_lists[0][0], ir0.VariadicTypeExpansion) and isinstance(values_lists[0][0].expr, ir0.AtomicTypeLiteral):
                var = values_lists[0][0].expr.cpp_type
                for values in values_lists:
                    value = values[0]
                    if not (isinstance(value, ir0.VariadicTypeExpansion) and isinstance(value.expr, ir0.AtomicTypeLiteral) and value.expr.cpp_type == var):
                        break
                else:
                    values_lists = [values[1:] for values in values_lists]
                    continue

            # And same at the end.
            if isinstance(values_lists[0][-1], ir0.VariadicTypeExpansion) and isinstance(values_lists[0][-1].expr, ir0.AtomicTypeLiteral):
                var = values_lists[0][-1].expr.cpp_type
                for values in values_lists:
                    value = values[-1]
                    if not (isinstance(value, ir0.VariadicTypeExpansion) and isinstance(value.expr, ir0.AtomicTypeLiteral) and value.expr.cpp_type == var):
                        break
                else:
                    values_lists = [values[:-1] for values in values_lists]
                    continue

            # We have excluded all begin/end values that we can.
            break

        for values in values_lists:
            num_expansions = sum(1
                                 for value in values
                                 if isinstance(value, ir0.VariadicTypeExpansion))
            if num_expansions > 1:
                # We can perform the replacement syntactically, but it doesn't make sense semantically.
                # E.g. when replacing Ts={int, Xs...}, Us={Ys..., float} in "std::pair<Ts, Us>..." we can't output
                # "std::pair<int, Ys>..., std::pair<Xs, float>...", it would be wrong.
                raise VariadicVarReplacementNotPossibleException('We can perform the replacement syntactically, but it doesn\'t make sense semantically')

def replace_var_with_expr_in_template_body_element(elem: ir0.TemplateBodyElement,
                                                   var: str,
                                                   expr: ir0.Expr) \
        -> ir0.TemplateBodyElement:
    toplevel_writer = transform_ir0.ToplevelWriter(identifier_generator=[], allow_template_defns=False, allow_toplevel_elems=False)
    writer = transform_ir0.TemplateBodyWriter(toplevel_writer)
    _ReplaceVarWithExprTransformation({var: expr}, dict()).transform_template_body_elem(elem, writer)
    [elem] = writer.elems
    return elem

def replace_var_with_expr_in_template_body_elements(elems: List[ir0.TemplateBodyElement],
                                                    replacement_expr_by_var: Dict[str, Union[ir0.Expr, List[ir0.Expr]]],
                                                    replacement_expr_by_expanded_var: Dict[str, Union[ir0.Expr, List[ir0.Expr]]]) \
        -> List[ir0.TemplateBodyElement]:
    toplevel_writer = transform_ir0.ToplevelWriter(identifier_generator=[], allow_template_defns=False, allow_toplevel_elems=False)
    return _ReplaceVarWithExprTransformation(replacement_expr_by_var, replacement_expr_by_expanded_var).transform_template_body_elems(elems, toplevel_writer)

def replace_var_with_expr_in_expr(expr: ir0.Expr,
                                  replacement_expr_by_var: Dict[str, Union[ir0.Expr, List[ir0.Expr]]],
                                  replacement_expr_by_expanded_var: Dict[str, Union[ir0.Expr, List[ir0.Expr]]]) \
        -> Union[ir0.Expr, List[ir0.Expr]]:
    toplevel_writer = transform_ir0.ToplevelWriter(identifier_generator=[], allow_template_defns=False, allow_toplevel_elems=False)
    result = _ReplaceVarWithExprTransformation(replacement_expr_by_var,
                                               replacement_expr_by_expanded_var).transform_expr(expr,
                                                                                                toplevel_writer)
    return result
