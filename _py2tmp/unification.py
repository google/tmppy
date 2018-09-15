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

from typing import List, TypeVar, Generic, Union, Dict, Set, Tuple
import networkx as nx

class UnificationFailedException(Exception):
    pass

TermT = TypeVar('TermT')

class UnificationStrategy(Generic[TermT]):
    Expr = Union[str, TermT]

    # Checks if term1 is equal to term2 excluding args.
    def is_same_term_excluding_args(self, term1: TermT, term2: TermT) -> bool: ...

    # Gets the args of a term.
    def get_term_args(self, term: TermT) -> List[Expr]: ...

    # Returns a copy of `term` with the given new args.
    # This is only called if canonicalize=True is passed to unify()
    def term_copy_with_args(self, term: TermT, new_args: List[Expr]) -> TermT: ...

def unify(expr_expr_equations: List[Tuple[Union[str, TermT], Union[str, TermT]]],
          strategy: UnificationStrategy[TermT],
          canonicalize: bool = False) \
        -> Dict[str, Union[str, TermT]]:
    var_expr_equations = _convert_to_var_expr_equations(expr_expr_equations, strategy)
    if canonicalize:
        var_expr_equations = _canonicalize_var_expr_equations(var_expr_equations, strategy)
    return var_expr_equations

_Expr = Union[str, TermT]

def _convert_to_var_expr_equations(expr_expr_equations: List[Tuple[_Expr, _Expr]],
                                   strategy: UnificationStrategy[TermT]):
    var_expr_equations: Dict[str, TermT] = dict()

    expr_expr_equations = expr_expr_equations.copy()
    while expr_expr_equations:
        lhs, rhs = expr_expr_equations.pop()

        if not isinstance(lhs, str):
            lhs, rhs = rhs, lhs

        if isinstance(lhs, str):
            if isinstance(rhs, str) and lhs == rhs:
                continue

            if lhs in var_expr_equations:
                expr_expr_equations.append((var_expr_equations[lhs], rhs))
                continue

            if isinstance(rhs, str):
                if rhs in var_expr_equations:
                    expr_expr_equations.append((lhs, var_expr_equations[rhs]))
                    continue

            _occurence_check(lhs, rhs, strategy, var_expr_equations)
            var_expr_equations[lhs] = rhs
            continue

        if strategy.is_same_term_excluding_args(lhs, rhs):
            lhs_args = strategy.get_term_args(lhs)
            rhs_args = strategy.get_term_args(rhs)
            if len(lhs_args) == len(rhs_args):
                for lhs_arg, rhs_arg in zip(lhs_args, rhs_args):
                    expr_expr_equations.append((lhs_arg, rhs_arg))
                continue

        raise UnificationFailedException()


    return var_expr_equations

def _occurence_check(var1: str,
                     expr1: _Expr,
                     strategy: UnificationStrategy[TermT],
                     var_expr_equations: Dict[str, _Expr]):
    var_expr_pairs_to_check = [(var1, expr1)]
    while var_expr_pairs_to_check:
        var, expr = var_expr_pairs_to_check.pop()
        if isinstance(expr, str):
            if var == expr:
                raise UnificationFailedException()
            if expr in var_expr_equations:
                var_expr_pairs_to_check.append((var, var_expr_equations[expr]))
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

def _replace_variables_in_expr(expr: _Expr,
                               replacements: Dict[str, _Expr],
                               strategy: UnificationStrategy[TermT]):
    if isinstance(expr, str):
        if expr in replacements:
            return replacements[expr]
        else:
            return expr

    return strategy.term_copy_with_args(expr, [_replace_variables_in_expr(arg, replacements, strategy)
                                               for arg in strategy.get_term_args(expr)])

def _canonicalize_var_expr_equations(var_expr_equations: Dict[str, _Expr],
                                     strategy: UnificationStrategy[TermT]):
    if not var_expr_equations:
        return dict()

    # A graph that has all variables on the LHS of equations as nodes and an edge var1->var2 if we have the equation
    # var1=expr and var2 appears in expr.
    vars_dependency_graph = nx.DiGraph()
    for lhs, rhs in var_expr_equations.items():
        for var in _get_free_variables(rhs, strategy):
            vars_dependency_graph.add_edge(lhs, var)

    # Invariant:
    # assert not any(key in _get_free_variables(value, strategy)
    #                for key in canonical_var_expr_equations.keys()
    #                for value in canonical_var_expr_equations.values())
    canonical_var_expr_equations: Dict[str, TermT] = dict()

    for var in reversed(list(nx.topological_sort(vars_dependency_graph))):
        expr = var_expr_equations.get(var)
        if expr is None:
            continue
        expr = _replace_variables_in_expr(expr, canonical_var_expr_equations, strategy)
        canonical_var_expr_equations[var] = expr

    return canonical_var_expr_equations
