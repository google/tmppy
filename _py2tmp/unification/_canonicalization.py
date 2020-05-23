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

from typing import List, Union, Dict, Set, Tuple

import networkx as nx

from _py2tmp.unification import CanonicalizationFailedException
from _py2tmp.unification._strategy import TermT, UnificationStrategy, TupleExpansion, \
    UnificationStrategyForCanonicalization
from _py2tmp.unification._utils import expr_to_string, exprs_to_string
from _py2tmp.utils import compute_condensation_in_topological_order

_NonTupleExpr = Union[str, TermT]
_Expr = Union[_NonTupleExpr, Tuple[_NonTupleExpr, ...]]

def canonicalize(var_expr_equations: Dict[str, _NonTupleExpr],
                 expanded_var_expr_equations: Dict[str, Tuple[_NonTupleExpr, ...]],
                 strategy: UnificationStrategyForCanonicalization[TermT]) -> List[Tuple[Union[str, TupleExpansion[TermT]],
                                                                                        Tuple[_NonTupleExpr, ...]]]:
    if not var_expr_equations and not expanded_var_expr_equations:
        return []

    var_expr_equations = var_expr_equations.copy()
    expanded_var_expr_equations = expanded_var_expr_equations.copy()

    # A graph that has all variables on the LHS of equations as nodes and an edge var1->var2 if we have the equation
    # var1=expr and var2 appears in expr.
    vars_dependency_graph = nx.DiGraph()
    for lhs, rhs in var_expr_equations.items():
        vars_dependency_graph.add_node(lhs)
        for var in _get_free_variables(rhs, strategy):
            vars_dependency_graph.add_edge(lhs, var)
        if isinstance(rhs, str):
            # This is a var-var equation. We also add an edge for the flipped equation.
            # That's going to cause a cycle, but we'll deal with the cycle below once we know if any other vars are
            # part of the cycle.
            vars_dependency_graph.add_edge(rhs, lhs)
    for lhs, rhs_list in expanded_var_expr_equations.items():
        vars_dependency_graph.add_node(lhs)
        for rhs_expr in rhs_list:
            for var in _get_free_variables(rhs_expr, strategy):
                vars_dependency_graph.add_edge(lhs, var)
        if len(rhs_list) == 1 and isinstance(rhs_list[0], TupleExpansion) and isinstance(rhs_list[0].expr, str):
            # This is a var-var equation. We also add an edge for the flipped equation.
            # That's going to cause a cycle, but we'll deal with the cycle below once we know if any other vars are
            # part of the cycle.
            vars_dependency_graph.add_edge(rhs_list[0].expr, lhs)

    for vars_in_connected_component in reversed(list(
            compute_condensation_in_topological_order(vars_dependency_graph))):
        vars_in_connected_component = vars_in_connected_component.copy()

        if len(vars_in_connected_component) == 1:
            [var] = vars_in_connected_component
            if var in var_expr_equations:
                # We can't flip the equation for this var since it's a "var=term" or "var=TupleExpansion(...)" equation.
                assert not isinstance(var_expr_equations[var], str)
                if not strategy.can_var_be_on_lhs(var):
                    raise CanonicalizationFailedException('Deduced equation that can\'t be flipped with LHS-forbidden var: %s = %s' % (
                        var, expr_to_string(strategy, var_expr_equations[var])))
            elif var in expanded_var_expr_equations:
                # We can't flip the equation for this var since it's a "TupleExpansion(var)=var2" or "TupleExpansion(var)=term" equation.
                assert not (len(expanded_var_expr_equations[var]) == 1
                            and isinstance(expanded_var_expr_equations[var][0], TupleExpansion)
                            and isinstance(expanded_var_expr_equations[var][0].expr, str))
                if not strategy.can_var_be_on_lhs(var):
                    raise CanonicalizationFailedException('Deduced equation that can\'t be flipped with LHS-forbidden var: TupleExpansion(%s) = %s' % (
                        var, exprs_to_string(strategy, expanded_var_expr_equations[var])))
            else:
                # This var is just part of a larger term in some other equation.
                assert not next(vars_dependency_graph.successors(var), None)
        else:
            assert len(vars_in_connected_component) > 1
            # We have a loop.
            # If any expression of the loop is a term with syntactic equality, unification would be impossible because
            # we can deduce var1=expr1 in which expr1 is not just var1 and var1 appears in expr1.
            # But in this case unify() would have failed.
            # If any expression of the loop is a term with non-syntactic equality, the unification is ambiguous.
            for var in vars_in_connected_component:
                if var in var_expr_equations:
                    if not (isinstance(var_expr_equations[var], str) or (isinstance(var_expr_equations[var], TupleExpansion)
                                                                         and isinstance(var_expr_equations[var].expr, str))):
                        raise CanonicalizationFailedException()
                if var in expanded_var_expr_equations:
                    if not (len(expanded_var_expr_equations[var]) == 1
                            and (isinstance(expanded_var_expr_equations[var][0], str)
                                 or (isinstance(expanded_var_expr_equations[var][0], TupleExpansion)
                                     and isinstance(expanded_var_expr_equations[var][0].expr, str)))):
                        raise CanonicalizationFailedException()

            [is_expanded_var] = {var in expanded_var_expr_equations
                                 for var in vars_in_connected_component
                                 if var in var_expr_equations or var in expanded_var_expr_equations}

            # So here we can assume that all exprs in the loop are variables, i.e. the loop is of the form
            # var1=var2=...=varN. So we have a choice of what var to put on the RHS.
            vars_in_rhs = tuple(var
                                for var in vars_in_connected_component
                                if not strategy.can_var_be_on_lhs(var))
            if len(vars_in_rhs) == 0:
                # Any var would do. We pick the max just to make this function deterministic.
                rhs_var = max(*vars_in_connected_component)
            elif len(vars_in_rhs) == 1:
                # This is the only one we can pick.
                [rhs_var] = vars_in_rhs
            else:
                # We need at least n-1 distinct LHS vars but we don't have enough vars allowed on the LHS.
                raise CanonicalizationFailedException('Found var equality chain that can\'t be canonicalized due to multiple LHS-forbidden vars: %s' % ', '.join(vars_in_rhs))

            # Now we remove all equations defining these vars and the corresponding edges in the graph.
            for var in vars_in_connected_component:
                if var in var_expr_equations:
                    del var_expr_equations[var]
                if var in expanded_var_expr_equations:
                    del expanded_var_expr_equations[var]
                for successor in list(vars_dependency_graph.successors(var)):
                    vars_dependency_graph.remove_edge(var, successor)

            # And finally we add the rearranged equations.
            for var in vars_in_connected_component:
                if var != rhs_var:
                    if is_expanded_var:
                        expanded_var_expr_equations[var] = (TupleExpansion(rhs_var),)
                    else:
                        var_expr_equations[var] = rhs_var
                    vars_dependency_graph.add_edge(var, rhs_var)

    # Invariant:
    # assert not any(key in _get_free_variables(value, strategy)
    #                for key in itertools.chain(canonical_var_expr_equations.keys(), canonical_expanded_var_expr_equations.keys())
    #                for value in itertools.chain(canonical_var_expr_equations.values(), canonical_expanded_var_expr_equations.values()))
    canonical_var_expr_equations: Dict[str, Union[_NonTupleExpr, Tuple[_NonTupleExpr, ...]]] = dict()
    canonical_expanded_var_expr_equations: Dict[str, Union[_NonTupleExpr, Tuple[_NonTupleExpr, ...]]] = dict()

    for var in reversed(list(nx.lexicographical_topological_sort(vars_dependency_graph))):
        expr = var_expr_equations.get(var)
        if expr is not None:
            expr = strategy.replace_variables_in_expr(expr, canonical_var_expr_equations, canonical_expanded_var_expr_equations)
            canonical_var_expr_equations[var] = expr
            assert var not in expanded_var_expr_equations

        expr_list = expanded_var_expr_equations.get(var)
        if expr_list is not None:
            expr_list = _replace_variables_in_exprs(expr_list, canonical_var_expr_equations, canonical_expanded_var_expr_equations, strategy)
            canonical_expanded_var_expr_equations[var] = expr_list
            assert isinstance(expr_list, tuple)
            assert var not in var_expr_equations

    return [*((var, expr) for var, expr in canonical_var_expr_equations.items()),
            *((TupleExpansion(var), expr) for var, expr in expanded_var_expr_equations.items())]

def _get_free_variables(expr: _Expr,
                        strategy: UnificationStrategy[TermT]):
    exprs_to_process: List[Union[str, TermT]] = [expr]
    variables: Set[str] = set()
    while exprs_to_process:
        expr = exprs_to_process.pop()
        if isinstance(expr, str):
            variables.add(expr)
        elif isinstance(expr, TupleExpansion):
            exprs_to_process.append(expr.expr)
        else:
            for arg_expr in strategy.get_term_args(expr):
                exprs_to_process.append(arg_expr)
    return variables

def _get_list_expansions(expr: _Expr,
                         strategy: UnificationStrategy[TermT]):
    exprs_to_process: List[Union[str, TermT]] = [expr]
    list_expansions: List[TupleExpansion] = []
    while exprs_to_process:
        expr = exprs_to_process.pop()
        if isinstance(expr, TupleExpansion):
            list_expansions.append(expr)
        elif not isinstance(expr, str):
            for arg_expr in strategy.get_term_args(expr):
                exprs_to_process.append(arg_expr)
    return tuple(list_expansions)

def _replace_variables_in_exprs(exprs: Tuple[_Expr, ...],
                                replacements: Dict[str, _Expr],
                                expanded_var_replacements: Dict[str, _Expr],
                                strategy: UnificationStrategyForCanonicalization[TermT]):
    results = []
    for expr in exprs:
        result = strategy.replace_variables_in_expr(expr, replacements, expanded_var_replacements)
        if isinstance(result, tuple):
            for expr1 in result:
                results.append(expr1)
        else:
            results.append(result)
    return tuple(results)
