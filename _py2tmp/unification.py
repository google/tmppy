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

from typing import List, TypeVar, Generic, Union, Dict, Set, Tuple, Iterable
import networkx as nx

class UnificationFailedException(Exception):
    pass

class UnificationAmbiguousException(Exception):
    pass

TermT = TypeVar('TermT')

class UnificationStrategy(Generic[TermT]):
    Expr = Union[str, TermT]

    # Checks if term1 is equal to term2 excluding args.
    def is_same_term_excluding_args(self, term1: TermT, term2: TermT) -> bool: ...

    # Gets the args of a term.
    def get_term_args(self, term: TermT) -> List[Expr]: ...

    # Returns true if `var` is a list var.
    # List vars are considered implicitly expanded within terms, e.g. f(x, y) is considered as f(*x, y) if x is a list
    # var.
    def is_list_var(self, var: str) -> bool: ...

_NonListExpr = Union[str, TermT]
_Expr = Union[_NonListExpr, List[_NonListExpr]]

def _ensure_list(x: _Expr) -> List[_NonListExpr]:
    if isinstance(x, list):
        return x
    else:
        return [x]

def unify(expr_expr_equations: List[Tuple[_Expr, _Expr]],
          strategy: UnificationStrategy[TermT]) -> Dict[str, Union[str, _Expr]]:
    var_expr_equations: Dict[str, List[_NonListExpr]] = dict()

    expr_expr_equations: List[Tuple[List[_NonListExpr], List[_NonListExpr]]] = \
        [(_ensure_list(lhs), _ensure_list(rhs))
         for lhs, rhs in expr_expr_equations]

    while expr_expr_equations:
        lhs_list, rhs_list = expr_expr_equations.pop()

        if not (len(lhs_list) == 1 and isinstance(lhs_list[0], str)):
            lhs_list, rhs_list = rhs_list, lhs_list

        if len(lhs_list) == 1 and isinstance(lhs_list[0], str):
            [lhs] = lhs_list
            if len(rhs_list) == 1 and isinstance(rhs_list[0], str) and lhs == rhs_list[0]:
                continue

            if lhs in var_expr_equations:
                expr_expr_equations.append((var_expr_equations[lhs], rhs_list))
                continue

            if len(rhs_list) == 1 and isinstance(rhs_list[0], str):
                if rhs_list[0] in var_expr_equations:
                    expr_expr_equations.append(([lhs], var_expr_equations[rhs_list[0]]))
                    continue

            for rhs in rhs_list:
                _occurence_check(lhs, rhs, strategy, var_expr_equations)
            var_expr_equations[lhs] = rhs_list
            continue

        if len(lhs_list) == 1 and len(rhs_list) == 1:
            [lhs] = lhs_list
            [rhs] = rhs_list
            assert not isinstance(lhs, str)
            assert not isinstance(rhs, str)
            if not strategy.is_same_term_excluding_args(lhs, rhs):
                raise UnificationFailedException()
            lhs_args = strategy.get_term_args(lhs)
            rhs_args = strategy.get_term_args(rhs)
            expr_expr_equations.append((lhs_args, rhs_args))
            continue

        while (lhs_list and rhs_list
               and ((not (isinstance(lhs_list[0], str) and strategy.is_list_var(lhs_list[0]))
                     and not (isinstance(rhs_list[0], str) and strategy.is_list_var(rhs_list[0])))
                    or lhs_list[0] == rhs_list[0])):
            # We can match the first element.
            expr_expr_equations.append(([lhs_list[0]], [rhs_list[0]]))
            lhs_list = lhs_list[1:]
            rhs_list = rhs_list[1:]

        while (lhs_list and rhs_list
                and ((not (isinstance(lhs_list[-1], str) and strategy.is_list_var(lhs_list[-1]))
                      and not (isinstance(rhs_list[-1], str) and strategy.is_list_var(rhs_list[-1])))
                     or lhs_list[-1] == rhs_list[-1])):
            # We can match the last element.
            expr_expr_equations.append(([lhs_list[-1]], [rhs_list[-1]]))
            lhs_list = lhs_list[:-1]
            rhs_list = rhs_list[:-1]

        if not lhs_list and not rhs_list:
            # We already matched everything.
            continue

        if not any(isinstance(arg, str) and strategy.is_list_var(arg)
                   for arg in lhs_list) \
                and not any(isinstance(arg, str) and strategy.is_list_var(arg)
                                       for arg in rhs_list):
            # There are no list args but one of the two sides still has unmatched elems.
            raise UnificationFailedException()

        if len(rhs_list) == 1 and isinstance(rhs_list[0], str) and strategy.is_list_var(rhs_list[0]):
            rhs_list, lhs_list = lhs_list, rhs_list

        if len(lhs_list) == 1 and isinstance(lhs_list[0], str) and strategy.is_list_var(lhs_list[0]):
            # This is an equality of the form [*l]=[...]
            expr_expr_equations.append(([lhs_list[0]], list(rhs_list)))
            continue

        if not rhs_list:
            rhs_list, lhs_list = lhs_list, rhs_list

        if not lhs_list:
            for arg in rhs_list:
                if isinstance(arg, str) and strategy.is_list_var(arg):
                    # If we always pick this branch in the loop, it's an equality of the form:
                    # [] = [*l1, ... *ln]
                    expr_expr_equations.append(([arg], []))
                else:
                    raise UnificationFailedException()
            continue

        if rhs_list and (([expr for expr in lhs_list if isinstance(expr, str) and strategy.is_list_var(expr)] == [lhs_list[-1]]
                          and [expr for expr in rhs_list if isinstance(expr, str) and strategy.is_list_var(expr)] == [rhs_list[0]])
                         or ([expr for expr in lhs_list if isinstance(expr, str) and strategy.is_list_var(expr)] == [lhs_list[0]]
                             and [expr for expr in rhs_list if isinstance(expr, str) and strategy.is_list_var(expr)] == [rhs_list[-1]])):
            # E.g. ['x', 'y', *l1] = [*l2, 'z']
            # We could continue the unification here if we defined a new var to represent the intersection of l1
            # and l2.
            # TODO: implement this if it ever happens.
            raise NotImplementedError()

        # E.g. in these cases:
        # [*l1, *l2] = [*l3, *l4]
        # ['x', *l1] = [*l2, *l3]
        raise UnificationAmbiguousException()

    return var_expr_equations

class CanonicalizationFailedException(Exception):
    pass

class UnificationStrategyForCanonicalization(Generic[TermT], UnificationStrategy[TermT]):
    # Returns a copy of `term` with the given new args.
    def term_copy_with_args(self, term: TermT, new_args: List[UnificationStrategy.Expr]) -> TermT: ...

    # Returns true if the var is allowed to be in the LHS of an equation in the result.
    def can_var_be_on_lhs(self, str) -> bool: ...

def canonicalize(var_expr_equations: Dict[str, List[_NonListExpr]],
                 strategy: UnificationStrategyForCanonicalization[TermT]) -> Dict[str, List[_NonListExpr]]:
    if not var_expr_equations:
        return dict()

    var_expr_equations = var_expr_equations.copy()

    # A graph that has all variables on the LHS of equations as nodes and an edge var1->var2 if we have the equation
    # var1=expr and var2 appears in expr.
    vars_dependency_graph = nx.DiGraph()
    for lhs, rhs_list in var_expr_equations.items():
        vars_dependency_graph.add_node(lhs)
        for rhs_expr in rhs_list:
            for var in _get_free_variables(rhs_expr, strategy):
                vars_dependency_graph.add_edge(lhs, var)
        if len(rhs_list) == 1 and isinstance(rhs_list[0], str):
            # This is a var-var equation. We also add an edge for the flipped equation.
            # That's going to cause a cycle, but we'll deal with the cycle below once we know if any other vars are
            # part of the cycle.
            vars_dependency_graph.add_edge(rhs_list[0], lhs)

    condensed_graph = nx.condensation(vars_dependency_graph)
    assert isinstance(condensed_graph, nx.DiGraph)

    for connected_component_index in reversed(list(nx.topological_sort(condensed_graph))):
        vars_in_connected_component = condensed_graph.node[connected_component_index]['members'].copy()

        if len(vars_in_connected_component) == 1:
            [var] = vars_in_connected_component
            if var in var_expr_equations:
                # We can't flip the equation for this var since it's a "var=term" equation.
                assert not isinstance(var_expr_equations[var], str)
                if not strategy.can_var_be_on_lhs(var):
                    raise CanonicalizationFailedException()
            else:
                # This var is just part of a larger term in some other equation.
                assert not vars_dependency_graph.successors(var)
        else:
            assert len(vars_in_connected_component) > 1
            # We have a loop.
            # If any expression of the loop is a term, unification would be impossible because we can deduce var1=expr1
            # in which expr1 is not just var1 and var1 appears in expr1.
            # But in this case unify() would have failed, so here we can assume that all exprs in the loop are
            # variables, i.e. the loop is of the form var1=var2=...=varN.
            for var in vars_in_connected_component:
                if var in var_expr_equations:
                    assert len(var_expr_equations[var]) == 1 and isinstance(var_expr_equations[var][0], str)

            # We have a choice of what var to put on the RHS.
            vars_in_rhs = [var
                           for var in vars_in_connected_component
                           if not strategy.can_var_be_on_lhs(var)]
            if len(vars_in_rhs) == 0:
                # Any var would do. We pick the max just to make this function deterministic.
                rhs_var = max(*vars_in_connected_component)
            elif len(vars_in_rhs) == 1:
                # This is the only one we can pick.
                [rhs_var] = vars_in_rhs
            else:
                # We need at least n-1 distinct LHS vars but we don't have enough vars allowed on the LHS.
                raise CanonicalizationFailedException()

            # Now we remove all equations defining these vars and the corresponding edges in the graph.
            for var in vars_in_connected_component:
                if var in var_expr_equations:
                    del var_expr_equations[var]
                for successor in vars_dependency_graph.successors(var):
                    vars_dependency_graph.remove_edge(var, successor)

            # And finally we add the rearranged equations.
            for var in vars_in_connected_component:
                if var != rhs_var:
                    var_expr_equations[var] = [rhs_var]
                    vars_dependency_graph.add_edge(var, rhs_var)

    # Invariant:
    # assert not any(key in _get_free_variables(value, strategy)
    #                for key in canonical_var_expr_equations.keys()
    #                for value in canonical_var_expr_equations.values())
    canonical_var_expr_equations: Dict[str, List[_NonListExpr]] = dict()

    for var in reversed(list(nx.topological_sort(vars_dependency_graph))):
        expr_list = var_expr_equations.get(var)
        if expr_list is None:
            continue
        expr_list = _replace_variables_in_exprs(expr_list, canonical_var_expr_equations, strategy)
        canonical_var_expr_equations[var] = expr_list

    return canonical_var_expr_equations

def _occurence_check(var1: str,
                     expr1: _Expr,
                     strategy: UnificationStrategy[TermT],
                     var_expr_equations: Dict[str, List[_NonListExpr]]):
    var_expr_pairs_to_check = [(var1, expr1)]
    while var_expr_pairs_to_check:
        var, expr = var_expr_pairs_to_check.pop()
        if isinstance(expr, str):
            if var == expr:
                raise UnificationFailedException()
            if expr in var_expr_equations:
                for elem in var_expr_equations[expr]:
                    var_expr_pairs_to_check.append((var, elem))
        else:
            for arg in strategy.get_term_args(expr):
                var_expr_pairs_to_check.append((var, arg))

def _get_free_variables(expr: _Expr,
                        strategy: UnificationStrategy[TermT]):
    exprs_to_process: List[Union[str, TermT]] = [expr]
    variables: Set[str] = set()
    while exprs_to_process:
        expr = exprs_to_process.pop()
        if isinstance(expr, str):
            variables.add(expr)
        else:
            for arg_expr in strategy.get_term_args(expr):
                exprs_to_process.append(arg_expr)
    return variables

def _replace_variables_in_exprs(exprs: List[_Expr],
                                replacements: Dict[str, _Expr],
                                strategy: UnificationStrategyForCanonicalization[TermT]):
    return [result_expr
            for expr in exprs
            for result_expr in _replace_variables_in_expr(expr, replacements, strategy)]

def _replace_variables_in_expr(expr: _Expr,
                               replacements: Dict[str, List[_NonListExpr]],
                               strategy: UnificationStrategyForCanonicalization[TermT]) -> Iterable[_Expr]:
    if isinstance(expr, str):
        if expr in replacements:
            return replacements[expr]
        else:
            return [expr]

    return [strategy.term_copy_with_args(expr,
                                         _replace_variables_in_exprs(strategy.get_term_args(expr),
                                                                     replacements,
                                                                     strategy))]
