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
from typing import Tuple, Union, Dict, Optional, List

from _py2tmp.unification import UnificationAmbiguousException, UnificationFailedException
from _py2tmp.unification._strategy import TermT, UnificationStrategy, TupleExpansion
from _py2tmp.unification._utils import ensure_tuple, exprs_to_string, expr_to_string

_NonTupleExpr = Union[str, TermT]
_Expr = Union[_NonTupleExpr, Tuple[_NonTupleExpr]]

class _UnificationContext:
    def __init__(self,
                 expr_expr_equations: List[Tuple[Tuple[_NonTupleExpr, ...],
                                                 Tuple[_NonTupleExpr, ...]]],
                 context_var_expr_equations: Dict[str, _NonTupleExpr],
                 strategy: UnificationStrategy[TermT]):
        self.expr_expr_equations = expr_expr_equations
        self.context_var_expr_equations = context_var_expr_equations
        self.strategy = strategy
        self.expanded_non_syntactically_comparable_expr: Optional[_NonTupleExpr] = None
        # Each (var, expr) entry here represents an equation: var=expr
        self.var_expr_equations: Dict[str, _NonTupleExpr] = dict()
        # Each (var, exprs) entry here represents an equation: TupleExpansion(var)=exprs
        self.expanded_var_expr_equations: Dict[str, Tuple[_NonTupleExpr, ...]] = dict()

def unify(initial_expr_expr_equations: List[Tuple[_Expr, _Expr]],
          context_var_expr_equations: Dict[str, _NonTupleExpr],
          strategy: UnificationStrategy[TermT]) -> Tuple[Dict[str, Union[str, _Expr]],
                                                         Dict[str, Tuple[_NonTupleExpr, ...]]]:

    context = _UnificationContext(expr_expr_equations=[(ensure_tuple(lhs), ensure_tuple(rhs))
                                                       for lhs, rhs in initial_expr_expr_equations],
                                  context_var_expr_equations=context_var_expr_equations,
                                  strategy=strategy)

    while context.expr_expr_equations:
        lhs_tuple, rhs_tuple = context.expr_expr_equations.pop()
        _process_tuple_tuple_equation(lhs_tuple, rhs_tuple, context)

    return context.var_expr_equations, context.expanded_var_expr_equations


def _process_tuple_tuple_equation(lhs_tuple: Tuple[_NonTupleExpr], rhs_tuple: Tuple[_NonTupleExpr], context: _UnificationContext):
    if not (len(lhs_tuple) == 1 and (isinstance(lhs_tuple[0], str) or (isinstance(lhs_tuple[0], TupleExpansion)
                                                                     and isinstance(lhs_tuple[0].expr, str)))):
        lhs_tuple, rhs_tuple = rhs_tuple, lhs_tuple

    if len(lhs_tuple) == 1 and (isinstance(lhs_tuple[0], str) or (isinstance(lhs_tuple[0], TupleExpansion)
                                                                and isinstance(lhs_tuple[0].expr, str))):
        [lhs] = lhs_tuple
        _process_var_expr_equation(lhs, rhs_tuple, context)
        return

    if len(lhs_tuple) == 1 and len(rhs_tuple) == 1 and not isinstance(lhs_tuple[0], TupleExpansion) and not isinstance(rhs_tuple[0], TupleExpansion):
        [lhs] = lhs_tuple
        [rhs] = rhs_tuple
        assert not isinstance(lhs, str)
        assert not isinstance(rhs, str)
        _process_term_term_equation(lhs, rhs, context)
        return

    removed_something = False

    while (lhs_tuple and rhs_tuple
           and ((not isinstance(lhs_tuple[0], TupleExpansion) and not isinstance(rhs_tuple[0], TupleExpansion))
                or (isinstance(lhs_tuple[0], TupleExpansion)
                    and isinstance(rhs_tuple[0], TupleExpansion)
                    and isinstance(lhs_tuple[0].expr, str)
                    and isinstance(rhs_tuple[0].expr, str)
                    and lhs_tuple[0].expr == rhs_tuple[0].expr))):
        # We can match the first element.
        context.expr_expr_equations.append(((lhs_tuple[0],), (rhs_tuple[0],)))
        lhs_tuple = lhs_tuple[1:]
        rhs_tuple = rhs_tuple[1:]
        removed_something = True

    while (lhs_tuple and rhs_tuple
           and ((not isinstance(lhs_tuple[-1], TupleExpansion) and not isinstance(rhs_tuple[-1], TupleExpansion))
                or (isinstance(lhs_tuple[-1], TupleExpansion)
                    and isinstance(rhs_tuple[-1], TupleExpansion)
                    and isinstance(lhs_tuple[-1].expr, str)
                    and isinstance(rhs_tuple[-1].expr, str)
                    and lhs_tuple[-1].expr == rhs_tuple[-1].expr))):
        # We can match the last element.
        context.expr_expr_equations.append(((lhs_tuple[-1],), (rhs_tuple[-1],)))
        lhs_tuple = lhs_tuple[:-1]
        rhs_tuple = rhs_tuple[:-1]
        removed_something = True

    if not lhs_tuple and not rhs_tuple:
        # We already matched everything.
        return

    strategy = context.strategy
    if not any(isinstance(lhs, TupleExpansion)
               for lhs in lhs_tuple) \
            and not any(isinstance(rhs, TupleExpansion)
                        for rhs in rhs_tuple):
        # There are no tuple expansions but one of the two sides still has unmatched elems.
        if context.expanded_non_syntactically_comparable_expr:
            raise UnificationAmbiguousException('Deduced %s = %s, which differ in length and have no tuple vars\nAfter expanding a non-syntactically-comparable expr:\n%s' % (
                exprs_to_string(strategy, lhs_tuple), exprs_to_string(strategy, rhs_tuple), expr_to_string(strategy, context.expanded_non_syntactically_comparable_expr)))
        else:
            raise UnificationFailedException('Deduced %s = %s, which differ in length and have no tuple vars' % (
                exprs_to_string(strategy, lhs_tuple), exprs_to_string(strategy, rhs_tuple)))

    if removed_something:
        # We put back the trimmed tuples and re-process them from the start (we might have a var-expr or term-term
        # equation now).
        context.expr_expr_equations.append((lhs_tuple, rhs_tuple))
        return

    if not rhs_tuple:
        rhs_tuple, lhs_tuple = lhs_tuple, rhs_tuple

    if not lhs_tuple:
        for arg in rhs_tuple:
            if isinstance(arg, TupleExpansion) and isinstance(arg.expr, str):
                # If we always pick this branch in the loop, it's an equality of the form:
                # [] = [*l1, ... *ln]
                context.expr_expr_equations.append(((arg,), ()))
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
        exprs_to_string(strategy, lhs_tuple), exprs_to_string(strategy, rhs_tuple)))


def _process_var_expr_equation(lhs: Union[str, TupleExpansion], rhs_tuple: Tuple[_NonTupleExpr], context: _UnificationContext):
    if len(rhs_tuple) == 1:
        [rhs] = rhs_tuple
        if isinstance(lhs, str) and isinstance(rhs, str) and lhs == rhs:
            return

        if (isinstance(lhs, TupleExpansion) and isinstance(rhs, TupleExpansion)
                and isinstance(lhs.expr, str) and isinstance(rhs.expr, str)
                and lhs.expr == rhs.expr):
            return

    if isinstance(lhs, str) and lhs in context.var_expr_equations:
        context.expr_expr_equations.append(((context.var_expr_equations[lhs],), rhs_tuple))
        return

    if isinstance(lhs, str) and lhs in context.context_var_expr_equations:
        context.expr_expr_equations.append(((context.context_var_expr_equations[lhs],), rhs_tuple))
        return

    if isinstance(lhs, TupleExpansion) and lhs.expr in context.expanded_var_expr_equations:
        context.expr_expr_equations.append((context.expanded_var_expr_equations[lhs.expr], rhs_tuple))
        return

    assert not (isinstance(lhs, TupleExpansion) and lhs.expr in context.context_var_expr_equations)

    if len(rhs_tuple) == 1 and isinstance(rhs_tuple[0], str):
        if rhs_tuple[0] in context.var_expr_equations:
            context.expr_expr_equations.append(((lhs,), (context.var_expr_equations[rhs_tuple[0]],)))
            return
        if rhs_tuple[0] in context.context_var_expr_equations:
            context.expr_expr_equations.append(((lhs,), (context.context_var_expr_equations[rhs_tuple[0]],)))
            return

    if len(rhs_tuple) == 1 and isinstance(rhs_tuple[0], TupleExpansion) and isinstance(rhs_tuple[0].expr, str):
        if rhs_tuple[0].expr in context.expanded_var_expr_equations:
            context.expr_expr_equations.append(((lhs,), context.expanded_var_expr_equations[rhs_tuple[0].expr]))
            return
        assert rhs_tuple[0].expr not in context.context_var_expr_equations

    if len(rhs_tuple) != 1 and not isinstance(lhs, TupleExpansion) and not any(isinstance(expr, TupleExpansion)
                                                                               for expr in rhs_tuple):
        # Different number of args and no tuple expansion to consider.
        strategy = context.strategy
        if context.expanded_non_syntactically_comparable_expr:
            raise UnificationAmbiguousException('Found expr tuples of different lengths with no tuple exprs: %s vs %s\nAfter expanding a non-syntactically-comparable expr:\n%s' % (
                exprs_to_string(strategy, (lhs,)), exprs_to_string(strategy, rhs_tuple), expr_to_string(strategy, context.expanded_non_syntactically_comparable_expr)))
        else:
            raise UnificationFailedException('Found expr tuples of different lengths with no tuple exprs: %s vs %s' % (
                exprs_to_string(strategy, (lhs,)), exprs_to_string(strategy, rhs_tuple)))

    if isinstance(lhs, str):
        for rhs in rhs_tuple:
            _occurence_check(lhs, rhs, context)
        [rhs] = rhs_tuple
        context.var_expr_equations[lhs] = rhs
    else:
        assert isinstance(lhs, TupleExpansion)
        for rhs in rhs_tuple:
            _occurence_check(lhs.expr, rhs, context)
        if len(rhs_tuple) == 1 and isinstance(rhs_tuple[0], TupleExpansion):
            context.var_expr_equations[lhs.expr] = rhs_tuple[0].expr
        else:
            context.expanded_var_expr_equations[lhs.expr] = rhs_tuple


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
    elif isinstance(expr1, TupleExpansion):
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
        elif isinstance(expr, TupleExpansion):
            var_expr_pairs_to_check.append((var, expr.expr, False))
        else:
            is_term_with_syntactical_equality = strategy.equality_requires_syntactical_equality(expr)
            for arg in strategy.get_term_args(expr):
                var_expr_pairs_to_check.append((var, arg, only_expanded_terms_with_syntactical_equality and is_term_with_syntactical_equality))
