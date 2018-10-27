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

class _UnificationContext:
    def __init__(self,
                 expr_expr_equations: List[Tuple[List[_NonListExpr],
                                                 List[_NonListExpr]]],
                 context_var_expr_equations: Dict[str, _NonListExpr],
                 strategy: UnificationStrategy[TermT]):
        self.expr_expr_equations = expr_expr_equations
        self.context_var_expr_equations = context_var_expr_equations
        self.strategy = strategy
        self.expanded_non_syntactically_comparable_expr: Optional[_NonListExpr] = None
        # Each (var, expr) entry here represents an equation: var=expr
        self.var_expr_equations: Dict[str, _NonListExpr] = dict()
        # Each (var, exprs) entry here represents an equation: ListExpansion(var)=exprs
        self.expanded_var_expr_equations: Dict[str, List[_NonListExpr]] = dict()

def unify(initial_expr_expr_equations: List[Tuple[_Expr, _Expr]],
          context_var_expr_equations: Dict[str, _NonListExpr],
          strategy: UnificationStrategy[TermT]) -> Tuple[Dict[str, Union[str, _Expr]],
                                                         Dict[str, List[_NonListExpr]]]:

    context = _UnificationContext(expr_expr_equations=[(ensure_list(lhs), ensure_list(rhs))
                                                       for lhs, rhs in initial_expr_expr_equations],
                                  context_var_expr_equations=context_var_expr_equations,
                                  strategy=strategy)

    while context.expr_expr_equations:
        lhs_list, rhs_list = context.expr_expr_equations.pop()
        _process_list_list_equation(lhs_list, rhs_list, context)

    return context.var_expr_equations, context.expanded_var_expr_equations


def _process_list_list_equation(lhs_list: List[_NonListExpr], rhs_list: List[_NonListExpr], context: _UnificationContext):
    if not (len(lhs_list) == 1 and (isinstance(lhs_list[0], str) or (isinstance(lhs_list[0], ListExpansion)
                                                                     and isinstance(lhs_list[0].expr, str)))):
        lhs_list, rhs_list = rhs_list, lhs_list

    if len(lhs_list) == 1 and (isinstance(lhs_list[0], str) or (isinstance(lhs_list[0], ListExpansion)
                                                                and isinstance(lhs_list[0].expr, str))):
        [lhs] = lhs_list
        _process_var_expr_equation(lhs, rhs_list, context)
        return

    if len(lhs_list) == 1 and len(rhs_list) == 1 and not isinstance(lhs_list[0], ListExpansion) and not isinstance(rhs_list[0], ListExpansion):
        [lhs] = lhs_list
        [rhs] = rhs_list
        assert not isinstance(lhs, str)
        assert not isinstance(rhs, str)
        _process_term_term_equation(lhs, rhs, context)
        return

    removed_something = False

    while (lhs_list and rhs_list
           and ((not isinstance(lhs_list[0], ListExpansion) and not isinstance(rhs_list[0], ListExpansion))
                or (isinstance(lhs_list[0], ListExpansion)
                    and isinstance(rhs_list[0], ListExpansion)
                    and isinstance(lhs_list[0].expr, str)
                    and isinstance(rhs_list[0].expr, str)
                    and lhs_list[0].expr == rhs_list[0].expr))):
        # We can match the first element.
        context.expr_expr_equations.append(([lhs_list[0]], [rhs_list[0]]))
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
        context.expr_expr_equations.append(([lhs_list[-1]], [rhs_list[-1]]))
        lhs_list = lhs_list[:-1]
        rhs_list = rhs_list[:-1]
        removed_something = True

    if not lhs_list and not rhs_list:
        # We already matched everything.
        return

    strategy = context.strategy
    if not any(isinstance(lhs, ListExpansion)
               for lhs in lhs_list) \
            and not any(isinstance(rhs, ListExpansion)
                        for rhs in rhs_list):
        # There are no list expansions but one of the two sides still has unmatched elems.
        if context.expanded_non_syntactically_comparable_expr:
            raise UnificationAmbiguousException('Deduced %s = %s, which differ in length and have no list vars\nAfter expanding a non-syntactically-comparable expr:\n%s' % (
                exprs_to_string(strategy, lhs_list), exprs_to_string(strategy, rhs_list), expr_to_string(strategy, context.expanded_non_syntactically_comparable_expr)))
        else:
            raise UnificationFailedException('Deduced %s = %s, which differ in length and have no list vars' % (
                exprs_to_string(strategy, lhs_list), exprs_to_string(strategy, rhs_list)))

    if removed_something:
        # We put back the trimmed lists and re-process them from the start (we might have a var-expr or term-term
        # equation now).
        context.expr_expr_equations.append((lhs_list, rhs_list))
        return

    if not rhs_list:
        rhs_list, lhs_list = lhs_list, rhs_list

    if not lhs_list:
        for arg in rhs_list:
            if isinstance(arg, ListExpansion) and isinstance(arg.expr, str):
                # If we always pick this branch in the loop, it's an equality of the form:
                # [] = [*l1, ... *ln]
                context.expr_expr_equations.append(([arg], []))
            else:
                if context.expanded_non_syntactically_comparable_expr:
                    raise UnificationAmbiguousException()
                else:
                    raise UnificationFailedException()
        return

    # E.g. in these cases:
    # ['x', 'y', *l1] = [*l2, 'z']
    # [*l1, *l2] = [*l3, *l4]
    # ['x', *l1] = [*l2, *l3]
    raise UnificationAmbiguousException('Deduced %s = %s' % (
        exprs_to_string(strategy, lhs_list), exprs_to_string(strategy, rhs_list)))


def _process_var_expr_equation(lhs: Union[str, ListExpansion], rhs_list: List[_NonListExpr], context: _UnificationContext):
    if len(rhs_list) == 1:
        [rhs] = rhs_list
        if isinstance(lhs, str) and isinstance(rhs, str) and lhs == rhs:
            return

        if (isinstance(lhs, ListExpansion) and isinstance(rhs, ListExpansion)
                and isinstance(lhs.expr, str) and isinstance(rhs.expr, str)
                and lhs.expr == rhs.expr):
            return

    if isinstance(lhs, str) and lhs in context.var_expr_equations:
        context.expr_expr_equations.append(([context.var_expr_equations[lhs]], rhs_list))
        return

    if isinstance(lhs, str) and lhs in context.context_var_expr_equations:
        context.expr_expr_equations.append(([context.context_var_expr_equations[lhs]], rhs_list))
        return

    if isinstance(lhs, ListExpansion) and lhs.expr in context.expanded_var_expr_equations:
        context.expr_expr_equations.append((context.expanded_var_expr_equations[lhs.expr], rhs_list))
        return

    assert not (isinstance(lhs, ListExpansion) and lhs.expr in context.context_var_expr_equations)

    if len(rhs_list) == 1 and isinstance(rhs_list[0], str):
        if rhs_list[0] in context.var_expr_equations:
            context.expr_expr_equations.append(([lhs], [context.var_expr_equations[rhs_list[0]]]))
            return
        if rhs_list[0] in context.context_var_expr_equations:
            context.expr_expr_equations.append(([lhs], [context.context_var_expr_equations[rhs_list[0]]]))
            return

    if len(rhs_list) == 1 and isinstance(rhs_list[0], ListExpansion) and isinstance(rhs_list[0].expr, str):
        if rhs_list[0].expr in context.expanded_var_expr_equations:
            context.expr_expr_equations.append(([lhs], context.expanded_var_expr_equations[rhs_list[0].expr]))
            return
        assert rhs_list[0].expr not in context.context_var_expr_equations

    if len(rhs_list) != 1 and not isinstance(lhs, ListExpansion) and not any(isinstance(expr, ListExpansion)
                                                                             for expr in rhs_list):
        # Different number of args and no list expansion to consider.
        strategy = context.strategy
        if context.expanded_non_syntactically_comparable_expr:
            raise UnificationAmbiguousException('Found expr lists of different lengths with no list exprs: %s vs %s\nAfter expanding a non-syntactically-comparable expr:\n%s' % (
                exprs_to_string(strategy, [lhs]), exprs_to_string(strategy, rhs_list), expr_to_string(strategy, context.expanded_non_syntactically_comparable_expr)))
        else:
            raise UnificationFailedException('Found expr lists of different lengths with no list exprs: %s vs %s' % (
                exprs_to_string(strategy, [lhs]), exprs_to_string(strategy, rhs_list)))

    if isinstance(lhs, str):
        for rhs in rhs_list:
            _occurence_check(lhs, rhs, context)
        [rhs] = rhs_list
        context.var_expr_equations[lhs] = rhs
    else:
        assert isinstance(lhs, ListExpansion)
        for rhs in rhs_list:
            _occurence_check(lhs.expr, rhs, context)
        if len(rhs_list) == 1 and isinstance(rhs_list[0], ListExpansion):
            context.var_expr_equations[lhs.expr] = rhs_list[0].expr
        else:
            context.expanded_var_expr_equations[lhs.expr] = rhs_list


def _process_term_term_equation(lhs: TermT, rhs: TermT, context: _UnificationContext):
    strategy = context.strategy
    expanding_non_syntactically_comparable_expr = None
    if not strategy.equality_requires_syntactical_equality(lhs):
        expanding_non_syntactically_comparable_expr = lhs
    if not strategy.equality_requires_syntactical_equality(rhs):
        expanding_non_syntactically_comparable_expr = rhs
    if not strategy.is_same_term_excluding_args(lhs, rhs):
        if context.expanded_non_syntactically_comparable_expr or (
                expanding_non_syntactically_comparable_expr and strategy.may_be_equal(lhs, rhs)):
            raise UnificationAmbiguousException(
                'Found different terms (even excluding args):\n%s\n== vs ==\n%s\nAfter expanding a non-syntactically-comparable expr:\n%s' % (
                    strategy.term_to_string(lhs), strategy.term_to_string(rhs),
                    strategy.term_to_string(
                        context.expanded_non_syntactically_comparable_expr or expanding_non_syntactically_comparable_expr)))
        else:
            raise UnificationFailedException('Found different terms (even excluding args):\n%s\n== vs ==\n%s' % (
                strategy.term_to_string(lhs), strategy.term_to_string(rhs)))
    if not context.expanded_non_syntactically_comparable_expr:
        context.expanded_non_syntactically_comparable_expr = expanding_non_syntactically_comparable_expr
    lhs_args = strategy.get_term_args(lhs)
    rhs_args = strategy.get_term_args(rhs)
    context.expr_expr_equations.append((lhs_args, rhs_args))

def _occurence_check(var1: str, expr1: _Expr, context: _UnificationContext):
    strategy = context.strategy
    if isinstance(expr1, str):
        var_expr_pairs_to_check = [(var1, expr1, None)]
    elif isinstance(expr1, ListExpansion):
        if not context.expanded_non_syntactically_comparable_expr:
            context.expanded_non_syntactically_comparable_expr = expr1
        var_expr_pairs_to_check = [(var1, expr1, context.expanded_non_syntactically_comparable_expr)]
    else:
        if not context.expanded_non_syntactically_comparable_expr and not strategy.equality_requires_syntactical_equality(expr1):
            context.expanded_non_syntactically_comparable_expr = expr1
        var_expr_pairs_to_check = [(var1, expr1, context.expanded_non_syntactically_comparable_expr)]

    while var_expr_pairs_to_check:
        var, expr, only_expanded_terms_with_syntactical_equality = var_expr_pairs_to_check.pop()
        if isinstance(expr, str):
            if var == expr:
                if context.expanded_non_syntactically_comparable_expr:
                    raise UnificationAmbiguousException("Ambiguous occurrence check for var %s while checking %s in %s with equations:\n%s\nSince the following non-syntactically-comparable expr has been expanded:\n%s" % (
                        var,
                        var1,
                        expr_to_string(strategy, expr1),
                        {var: expr_to_string(strategy, expr)
                         for var, expr in context.var_expr_equations.items()},
                        expr_to_string(strategy, context.expanded_non_syntactically_comparable_expr)))
                else:
                    raise UnificationFailedException("Failed occurrence check for var %s while checking %s in %s with equations:\n%s" % (
                        var, var1, expr_to_string(strategy, expr1), {var: expr_to_string(strategy, expr)
                                                                     for var, expr in context.var_expr_equations.items()}))
            if expr in context.var_expr_equations:
                var_expr_pairs_to_check.append((var, context.var_expr_equations[expr], only_expanded_terms_with_syntactical_equality))
            if expr in context.expanded_var_expr_equations:
                for elem in context.var_expr_equations[expr]:
                    var_expr_pairs_to_check.append((var, elem, only_expanded_terms_with_syntactical_equality))
            if expr in context.context_var_expr_equations:
                var_expr_pairs_to_check.append((var, context.context_var_expr_equations[expr], only_expanded_terms_with_syntactical_equality))
        elif isinstance(expr, ListExpansion):
            var_expr_pairs_to_check.append((var, expr.expr, False))
        else:
            is_term_with_syntactical_equality = strategy.equality_requires_syntactical_equality(expr)
            for arg in strategy.get_term_args(expr):
                var_expr_pairs_to_check.append((var, arg, only_expanded_terms_with_syntactical_equality and is_term_with_syntactical_equality))
