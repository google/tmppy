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

from enum import Enum
from typing import List, Tuple, Set, Optional, Iterable, Union, Dict

from bidict import bidict

from _py2tmp import ir0, transform_ir0, unification

def _unpack_if_variable(expr: ir0.Expr,
                        var_names: Set[str],
                        is_variadic: Dict[str, bool],
                        literal_expr_by_unique_name: Dict[str, ir0.AtomicTypeLiteral]):
    variadic = False
    if isinstance(expr, ir0.VariadicTypeExpansion) and isinstance(expr.expr, ir0.AtomicTypeLiteral) and expr.expr.cpp_type in var_names:
        expr = expr.expr
        variadic = True
    if isinstance(expr, ir0.AtomicTypeLiteral) and expr.cpp_type in var_names:
        # We keep track of the expr so that we can re-pack this later.
        # If there are multiple they must be the same.
        if expr.cpp_type in literal_expr_by_unique_name:
            assert expr == literal_expr_by_unique_name[expr.cpp_type]
        else:
            literal_expr_by_unique_name[expr.cpp_type] = expr
        if expr.cpp_type in is_variadic:
            assert variadic == is_variadic[expr.cpp_type]
        else:
            is_variadic[expr.cpp_type] = variadic

        return expr.cpp_type
    else:
        return expr

def _pack_if_variable(var_or_expr: Union[str, ir0.Expr, List[Union[str, ir0.Expr]]],
                      is_variadic: Dict[str, bool],
                      literal_expr_by_unique_name: Dict[str, ir0.AtomicTypeLiteral]) -> Union[ir0.Expr, List[ir0.Expr]]:
    assert not isinstance(var_or_expr, list)
    if isinstance(var_or_expr, str):
        if is_variadic[var_or_expr]:
            return ir0.VariadicTypeExpansion(literal_expr_by_unique_name[var_or_expr])
        else:
            return literal_expr_by_unique_name[var_or_expr]
    else:
        return var_or_expr

class _ExprUnificationStrategy(unification.UnificationStrategyForCanonicalization[ir0.Expr]):
    def __init__(self,
                 var_names: Set[str],
                 pattern_var_names: Set[str],
                 is_variadic: Dict[str, bool],
                 literal_expr_by_unique_name: Dict[str, ir0.AtomicTypeLiteral]):
        self.var_names = var_names
        self.pattern_var_names = pattern_var_names
        self.is_variadic = is_variadic
        self.literal_expr_by_unique_name = literal_expr_by_unique_name

    def is_same_term_excluding_args(self, term1: ir0.Expr, term2: ir0.Expr):
        return term1.is_same_expr_excluding_subexpressions(term2)

    def get_term_args(self, term: ir0.Expr) -> List[Union[str, ir0.Expr]]:
        return [_unpack_if_variable(expr, self.var_names, self.is_variadic, self.literal_expr_by_unique_name)
                for expr in term.get_direct_subexpressions()]

    def term_copy_with_args(self, term: ir0.Expr, new_args: List[Union[str, ir0.Expr]]) -> ir0.Expr:
        return term.copy_with_subexpressions([_pack_if_variable(arg, self.is_variadic, self.literal_expr_by_unique_name)
                                              for arg in new_args])

    def can_var_be_on_lhs(self, var: str) -> bool:
        return var in self.pattern_var_names

    def is_list_var(self, var: str) -> bool:
        return self.is_variadic[var]


def _replace_var_names_in_expr(expr: Union[ir0.Expr, List[ir0.Expr]], new_name_by_old_name: Dict[str, str]):
    if isinstance(expr, list):
        return [_replace_var_names_in_expr(elem, new_name_by_old_name)
                for elem in expr]
    transformation = transform_ir0.NameReplacementTransformation(new_name_by_old_name)
    writer = transform_ir0.ToplevelWriter(identifier_generator=iter([]))
    expr = transformation.transform_expr(expr, writer)
    assert not writer.template_defns
    assert not writer.toplevel_elems
    return expr

class UnificationResultKind(Enum):
    CERTAIN = 1
    POSSIBLE = 2
    IMPOSSIBLE = 3

class UnificationResult:
    def __init__(self,
                 kind: UnificationResultKind,
                 pattern_var_expr_equations: Optional[List[Tuple[ir0.AtomicTypeLiteral, List[ir0.Expr]]]] = None):
        assert (pattern_var_expr_equations is not None) == (kind == UnificationResultKind.CERTAIN)
        self.kind = kind
        self.value_by_pattern_variable = pattern_var_expr_equations

def unify(exprs: List[ir0.Expr],
          patterns: List[ir0.Expr],
          expr_variables: Set[str],
          pattern_variables: Set[str],
          identifier_generator: Iterable[str]) -> UnificationResult:

    # We need to replace local literals before doing the unification, to avoid assuming that e.g. T in an expr
    # is equal to T in a pattern just because they have the same name.

    unique_var_name_by_expr_type_literal_name = bidict({expr_literal.cpp_type: next(identifier_generator)
                                                        for expr in exprs
                                                        for expr_literal in expr.get_free_vars()})
    unique_var_name_by_pattern_type_literal_name = bidict({pattern_literal.cpp_type: next(identifier_generator)
                                                           for pattern in patterns
                                                           for pattern_literal in pattern.get_free_vars()})


    unique_var_names = set()
    for expr_var_name, unique_var_name in unique_var_name_by_expr_type_literal_name.items():
        if expr_var_name in expr_variables:
            unique_var_names.add(unique_var_name)
    for pattern_var_name, unique_var_name in unique_var_name_by_pattern_type_literal_name.items():
        if pattern_var_name in pattern_variables:
            unique_var_names.add(unique_var_name)

    literal_expr_by_unique_name: Dict[str, ir0.AtomicTypeLiteral] = dict()

    lhs = [_replace_var_names_in_expr(expr, unique_var_name_by_expr_type_literal_name)
           for expr in exprs]
    rhs = [_replace_var_names_in_expr(pattern, unique_var_name_by_pattern_type_literal_name)
           for pattern in patterns]

    is_variadic = dict()
    lhs = [_unpack_if_variable(expr, unique_var_names, is_variadic, literal_expr_by_unique_name)
           for expr in lhs]
    rhs = [_unpack_if_variable(pattern, unique_var_names, is_variadic, literal_expr_by_unique_name)
           for pattern in rhs]

    unification_strategy = _ExprUnificationStrategy(unique_var_names,
                                                    unique_var_name_by_pattern_type_literal_name.inv.keys(),
                                                    is_variadic,
                                                    literal_expr_by_unique_name)
    try:
        var_expr_equations = unification.unify([(lhs, rhs)],
                                               unification_strategy)
    except unification.UnificationFailedException:
        return UnificationResult(UnificationResultKind.IMPOSSIBLE)

    try:
        var_expr_equations = unification.canonicalize(var_expr_equations, unification_strategy)
    except unification.CanonicalizationFailedException:
        return UnificationResult(UnificationResultKind.POSSIBLE)

    var_expr_equations = [(_pack_if_variable(var, is_variadic, literal_expr_by_unique_name),
                           [_pack_if_variable(expr, is_variadic, literal_expr_by_unique_name)
                            for expr in exprs])
                          for var, exprs in var_expr_equations.items()]

    # At this point all equations should be of the form var=expr, with var a variable from a pattern and expr containing
    # no vars from patterns.
    for lhs_var, exprs in var_expr_equations:
        if isinstance(lhs_var, ir0.VariadicTypeExpansion):
            lhs_var = lhs_var.expr
        assert lhs_var.cpp_type in unique_var_name_by_pattern_type_literal_name.inv
        for expr in exprs:
            for rhs_var in expr.get_free_vars():
                assert rhs_var.cpp_type not in unique_var_name_by_pattern_type_literal_name.inv

    # We reverse the var renaming done above
    result_var_expr_equations = []
    for var, exprs in var_expr_equations:
        if isinstance(var, ir0.VariadicTypeExpansion):
            result_var_expr_equations.append((_replace_var_names_in_expr(var, unique_var_name_by_pattern_type_literal_name.inv),
                                              [_replace_var_names_in_expr(expr, unique_var_name_by_expr_type_literal_name.inv)
                                               for expr in exprs]))
        else:
            [expr] = exprs
            result_var_expr_equations.append((_replace_var_names_in_expr(var, unique_var_name_by_pattern_type_literal_name.inv),
                                              _replace_var_names_in_expr(expr, unique_var_name_by_expr_type_literal_name.inv)))

    for var, _ in result_var_expr_equations:
        assert isinstance(var, ir0.AtomicTypeLiteral) or (isinstance(var, ir0.VariadicTypeExpansion) and isinstance(var.expr, ir0.AtomicTypeLiteral))

    return UnificationResult(UnificationResultKind.CERTAIN, result_var_expr_equations)
