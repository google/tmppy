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
from typing import List, Union, Dict, Tuple, Optional

from _py2tmp.unification import UnificationAmbiguousException, UnificationFailedException
from _py2tmp.unification._strategy import TermT, UnificationStrategy, ListExpansion
from _py2tmp.unification._utils import ensure_list, exprs_to_string, expr_to_string

_NonListExpr = Union[str, TermT]
_Expr = Union[_NonListExpr, List[_NonListExpr]]

def unify(expr_expr_equations: List[Tuple[_Expr, _Expr]],
          context_var_expr_equations: Dict[str, _NonListExpr],
          strategy: UnificationStrategy[TermT]) -> Tuple[Dict[str, Union[str, _Expr]],
                                                         Dict[str, List[_NonListExpr]]]:
    # Each (var, expr) entry here represents an equation: var=expr
    var_expr_equations: Dict[str, _NonListExpr] = dict()
    # Each (var, exprs) entry here represents an equation: ListExpansion(var)=exprs
    expanded_var_expr_equations: Dict[str, List[_NonListExpr]] = dict()

    expr_expr_equations: List[Tuple[List[_NonListExpr],
                                    List[_NonListExpr]]] = \
        [(ensure_list(lhs), ensure_list(rhs))
         for lhs, rhs in expr_expr_equations]

    expanded_non_syntactically_comparable_expr = None
    while expr_expr_equations:
        lhs_list, rhs_list = expr_expr_equations.pop()

        if not (len(lhs_list) == 1 and (isinstance(lhs_list[0], str) or (isinstance(lhs_list[0], ListExpansion)
                                                                         and isinstance(lhs_list[0].expr, str)))):
            lhs_list, rhs_list = rhs_list, lhs_list

        if len(lhs_list) == 1 and (isinstance(lhs_list[0], str) or (isinstance(lhs_list[0], ListExpansion)
                                                                    and isinstance(lhs_list[0].expr, str))):
            [lhs] = lhs_list
            if len(rhs_list) == 1:
                [rhs] = rhs_list
                if isinstance(lhs, str) and isinstance(rhs, str) and lhs == rhs:
                    continue

                if (isinstance(lhs, ListExpansion) and isinstance(rhs, ListExpansion)
                        and isinstance(lhs.expr, str) and isinstance(rhs.expr, str)
                        and lhs.expr == rhs.expr):
                    continue

            if isinstance(lhs, str) and lhs in var_expr_equations:
                expr_expr_equations.append(([var_expr_equations[lhs]], rhs_list))
                continue

            if isinstance(lhs, str) and lhs in context_var_expr_equations:
                expr_expr_equations.append(([context_var_expr_equations[lhs]], rhs_list))
                continue

            if isinstance(lhs, ListExpansion) and lhs.expr in expanded_var_expr_equations:
                expr_expr_equations.append((expanded_var_expr_equations[lhs.expr], rhs_list))
                continue

            assert not (isinstance(lhs, ListExpansion) and lhs.expr in context_var_expr_equations)

            if len(rhs_list) == 1 and isinstance(rhs_list[0], str):
                if rhs_list[0] in var_expr_equations:
                    expr_expr_equations.append(([lhs], [var_expr_equations[rhs_list[0]]]))
                    continue
                if rhs_list[0] in context_var_expr_equations:
                    expr_expr_equations.append(([lhs], [context_var_expr_equations[rhs_list[0]]]))
                    continue

            if len(rhs_list) == 1 and isinstance(rhs_list[0], ListExpansion) and isinstance(rhs_list[0].expr, str):
                if rhs_list[0].expr in expanded_var_expr_equations:
                    expr_expr_equations.append(([lhs], expanded_var_expr_equations[rhs_list[0].expr]))
                    continue
                assert rhs_list[0].expr not in context_var_expr_equations

            if len(rhs_list) != 1 and not isinstance(lhs, ListExpansion) and not any(isinstance(expr, ListExpansion)
                                                                                     for expr in rhs_list):
                # Different number of args and no list expansion to consider.
                if expanded_non_syntactically_comparable_expr:
                    raise UnificationAmbiguousException('Found expr lists of different lengths with no list exprs: %s vs %s\nAfter expanding a non-syntactically-comparable expr:\n%s' % (
                        exprs_to_string(strategy, lhs_list), exprs_to_string(strategy, rhs_list), expr_to_string(strategy, expanded_non_syntactically_comparable_expr)))
                else:
                    raise UnificationFailedException('Found expr lists of different lengths with no list exprs: %s vs %s' % (
                        exprs_to_string(strategy, lhs_list), exprs_to_string(strategy, rhs_list)))

            if isinstance(lhs, str):
                for rhs in rhs_list:
                    _occurence_check(lhs, rhs, strategy, var_expr_equations, expanded_var_expr_equations, context_var_expr_equations, expanded_non_syntactically_comparable_expr)
                [rhs] = rhs_list
                var_expr_equations[lhs] = rhs
            else:
                assert isinstance(lhs, ListExpansion)
                for rhs in rhs_list:
                    _occurence_check(lhs.expr, rhs, strategy, var_expr_equations, expanded_var_expr_equations, context_var_expr_equations, expanded_non_syntactically_comparable_expr)
                if len(rhs_list) == 1 and isinstance(rhs_list[0], ListExpansion):
                    var_expr_equations[lhs.expr] = rhs_list[0].expr
                else:
                    expanded_var_expr_equations[lhs.expr] = rhs_list
            continue

        if len(lhs_list) == 1 and len(rhs_list) == 1 and not isinstance(lhs_list[0], ListExpansion) and not isinstance(rhs_list[0], ListExpansion):
            [lhs] = lhs_list
            [rhs] = rhs_list
            assert not isinstance(lhs, str)
            assert not isinstance(rhs, str)
            expanding_non_syntactically_comparable_expr = None
            if not strategy.equality_requires_syntactical_equality(lhs):
                expanding_non_syntactically_comparable_expr = lhs
            if not strategy.equality_requires_syntactical_equality(rhs):
                expanding_non_syntactically_comparable_expr = rhs
            if not strategy.is_same_term_excluding_args(lhs, rhs):
                if expanded_non_syntactically_comparable_expr or (expanding_non_syntactically_comparable_expr and strategy.may_be_equal(lhs, rhs)):
                    raise UnificationAmbiguousException('Found different terms (even excluding args):\n%s\n== vs ==\n%s\nAfter expanding a non-syntactically-comparable expr:\n%s' % (
                        strategy.term_to_string(lhs), strategy.term_to_string(rhs), strategy.term_to_string(expanded_non_syntactically_comparable_expr or expanding_non_syntactically_comparable_expr)))
                else:
                    raise UnificationFailedException('Found different terms (even excluding args):\n%s\n== vs ==\n%s' % (
                        strategy.term_to_string(lhs), strategy.term_to_string(rhs)))
            if not expanded_non_syntactically_comparable_expr:
                expanded_non_syntactically_comparable_expr = expanding_non_syntactically_comparable_expr
            lhs_args = strategy.get_term_args(lhs)
            rhs_args = strategy.get_term_args(rhs)
            expr_expr_equations.append((lhs_args, rhs_args))
            continue

        removed_something = False

        while (lhs_list and rhs_list
               and ((not isinstance(lhs_list[0], ListExpansion) and not isinstance(rhs_list[0], ListExpansion))
                    or (isinstance(lhs_list[0], ListExpansion)
                        and isinstance(rhs_list[0], ListExpansion)
                        and isinstance(lhs_list[0].expr, str)
                        and isinstance(rhs_list[0].expr, str)
                        and lhs_list[0].expr == rhs_list[0].expr))):
            # We can match the first element.
            expr_expr_equations.append(([lhs_list[0]], [rhs_list[0]]))
            lhs_list = lhs_list[1:]
            rhs_list = rhs_list[1:]
            removed_something = True

        while (lhs_list and rhs_list
               and ((not isinstance(lhs_list[-1], ListExpansion) and not isinstance(rhs_list[-1], ListExpansion))
                    or (isinstance(lhs_list[-1], ListExpansion)
                        and isinstance(rhs_list[-1], ListExpansion)
                        and isinstance(lhs_list[-1].expr, str)
                        and isinstance(rhs_list[-1].expr, str)
                        and lhs_list[-1].expr == rhs_list[-1].expr))):
            # We can match the last element.
            expr_expr_equations.append(([lhs_list[-1]], [rhs_list[-1]]))
            lhs_list = lhs_list[:-1]
            rhs_list = rhs_list[:-1]
            removed_something = True

        if not lhs_list and not rhs_list:
            # We already matched everything.
            continue

        if not any(isinstance(lhs, ListExpansion)
                   for lhs in lhs_list) \
                and not any(isinstance(rhs, ListExpansion)
                            for rhs in rhs_list):
            # There are no list expansions but one of the two sides still has unmatched elems.
            if expanded_non_syntactically_comparable_expr:
                raise UnificationAmbiguousException('Deduced %s = %s, which differ in length and have no list vars\nAfter expanding a non-syntactically-comparable expr:\n%s' % (
                    exprs_to_string(strategy, lhs_list), exprs_to_string(strategy, rhs_list), expr_to_string(strategy, expanded_non_syntactically_comparable_expr)))
            else:
                raise UnificationFailedException('Deduced %s = %s, which differ in length and have no list vars' % (
                    exprs_to_string(strategy, lhs_list), exprs_to_string(strategy, rhs_list)))

        if removed_something:
            # We put back the trimmed list and re-start running the code at the beginning of the iteration.
            expr_expr_equations.append((lhs_list, rhs_list))
            continue

        if not rhs_list:
            rhs_list, lhs_list = lhs_list, rhs_list

        if not lhs_list:
            for arg in rhs_list:
                if isinstance(arg, ListExpansion) and isinstance(arg.expr, str):
                    # If we always pick this branch in the loop, it's an equality of the form:
                    # [] = [*l1, ... *ln]
                    expr_expr_equations.append(([arg], []))
                else:
                    if expanded_non_syntactically_comparable_expr:
                        raise UnificationAmbiguousException()
                    else:
                        raise UnificationFailedException()
            continue

        # E.g. in these cases:
        # ['x', 'y', *l1] = [*l2, 'z']
        # [*l1, *l2] = [*l3, *l4]
        # ['x', *l1] = [*l2, *l3]
        raise UnificationAmbiguousException('Deduced %s = %s' % (
            exprs_to_string(strategy, lhs_list), exprs_to_string(strategy, rhs_list)))

    return var_expr_equations, expanded_var_expr_equations

def _occurence_check(var1: str,
                     expr1: _Expr,
                     strategy: UnificationStrategy[TermT],
                     var_expr_equations: Dict[str, _NonListExpr],
                     expanded_var_expr_equations: Dict[str, List[_NonListExpr]],
                     context_var_expr_equations: Dict[str, List[_NonListExpr]],
                     expanded_non_syntactically_comparable_expr: Optional[_NonListExpr]):
    if isinstance(expr1, str):
        var_expr_pairs_to_check = [(var1, expr1, None)]
    elif isinstance(expr1, ListExpansion):
        if not expanded_non_syntactically_comparable_expr:
            expanded_non_syntactically_comparable_expr = expr1
        var_expr_pairs_to_check = [(var1, expr1, expanded_non_syntactically_comparable_expr)]
    else:
        if not expanded_non_syntactically_comparable_expr and not strategy.equality_requires_syntactical_equality(expr1):
            expanded_non_syntactically_comparable_expr = expr1
        var_expr_pairs_to_check = [(var1, expr1, expanded_non_syntactically_comparable_expr)]
    while var_expr_pairs_to_check:
        var, expr, only_expanded_terms_with_syntactical_equality = var_expr_pairs_to_check.pop()
        if isinstance(expr, str):
            if var == expr:
                if expanded_non_syntactically_comparable_expr:
                    raise UnificationAmbiguousException("Ambiguous occurrence check for var %s while checking %s in %s with equations:\n%s\nSince the following non-syntactically-comparable expr has been expanded:\n%s" % (
                        var,
                        var1,
                        expr_to_string(strategy, expr1),
                        {var: expr_to_string(strategy, expr)
                         for var, expr in var_expr_equations.items()},
                        expr_to_string(strategy, expanded_non_syntactically_comparable_expr)))
                else:
                    raise UnificationFailedException("Failed occurrence check for var %s while checking %s in %s with equations:\n%s" % (
                        var, var1, expr_to_string(strategy, expr1), {var: expr_to_string(strategy, expr)
                                                                     for var, expr in var_expr_equations.items()}))
            if expr in var_expr_equations:
                var_expr_pairs_to_check.append((var, var_expr_equations[expr], only_expanded_terms_with_syntactical_equality))
            if expr in expanded_var_expr_equations:
                for elem in var_expr_equations[expr]:
                    var_expr_pairs_to_check.append((var, elem, only_expanded_terms_with_syntactical_equality))
            if expr in context_var_expr_equations:
                var_expr_pairs_to_check.append((var, context_var_expr_equations[expr], only_expanded_terms_with_syntactical_equality))
        elif isinstance(expr, ListExpansion):
            var_expr_pairs_to_check.append((var, expr.expr, False))
        else:
            is_term_with_syntactical_equality = strategy.equality_requires_syntactical_equality(expr)
            for arg in strategy.get_term_args(expr):
                var_expr_pairs_to_check.append((var, arg, only_expanded_terms_with_syntactical_equality and is_term_with_syntactical_equality))
