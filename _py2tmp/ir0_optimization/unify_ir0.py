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
from enum import Enum
from typing import List, Tuple, Set, Optional, Iterable, Union, MutableMapping, Mapping, Dict

from bidict import bidict

from _py2tmp import ir0, transform_ir0, ir0_to_cpp, utils
from _py2tmp.ir0_optimization import unification
import traceback

from _py2tmp.ir0_optimization.replace_var_with_expr import replace_var_with_expr_in_expr
from _py2tmp.ir0_optimization.unification import UnificationStrategy


def _unpack_if_variable(expr: ir0.Expr,
                        var_names: Set[str],
                        literal_expr_by_unique_name: MutableMapping[str, ir0.AtomicTypeLiteral]):
    if isinstance(expr, ir0.VariadicTypeExpansion):
        return unification.ListExpansion(_unpack_if_variable(expr.expr, var_names, literal_expr_by_unique_name))

    if isinstance(expr, ir0.AtomicTypeLiteral) and expr.cpp_type in var_names:
        # We keep track of the expr so that we can re-pack this later.
        # If there are multiple they must be the same.
        if expr.cpp_type in literal_expr_by_unique_name:
            assert expr == literal_expr_by_unique_name[expr.cpp_type]
        else:
            literal_expr_by_unique_name[expr.cpp_type] = expr

        return expr.cpp_type
    else:
        return expr

def _pack_if_variable(var_or_expr: Union[str, ir0.Expr, unification.ListExpansion[ir0.Expr]],
                      literal_expr_by_unique_name: Mapping[str, ir0.AtomicTypeLiteral]) -> Union[ir0.Expr, List[ir0.Expr]]:
    assert not isinstance(var_or_expr, list)
    if isinstance(var_or_expr, str):
        return literal_expr_by_unique_name[var_or_expr]
    elif isinstance(var_or_expr, unification.ListExpansion):
        return ir0.VariadicTypeExpansion(_pack_if_variable(var_or_expr.expr, literal_expr_by_unique_name))
    else:
        return var_or_expr

class _ExprUnificationStrategy(unification.UnificationStrategyForCanonicalization[ir0.Expr]):
    def __init__(self,
                 var_names: Set[str],
                 pattern_var_names: Set[str],
                 literal_expr_by_unique_name: MutableMapping[str, ir0.AtomicTypeLiteral]):
        self.var_names = var_names
        self.pattern_var_names = pattern_var_names
        self.literal_expr_by_unique_name = literal_expr_by_unique_name

    def is_same_term_excluding_args(self, term1: ir0.Expr, term2: ir0.Expr):
        return term1.is_same_expr_excluding_subexpressions(term2)

    def get_term_args(self, term: ir0.Expr) -> List[Union[str, ir0.Expr]]:
        return [_unpack_if_variable(expr, self.var_names, self.literal_expr_by_unique_name)
                for expr in term.get_direct_subexpressions()]

    def replace_variables_in_expr(self, expr: UnificationStrategy.Expr,
                                  replacements: Dict[str, List[UnificationStrategy.Expr]],
                                  expanded_var_replacements: Dict[str, List[UnificationStrategy.Expr]]) -> UnificationStrategy.Expr:
        replacements = {var: ([_pack_if_variable(value, self.literal_expr_by_unique_name) for value in values]
                              if isinstance(values, list)
                              else _pack_if_variable(values, self.literal_expr_by_unique_name))
                        for var, values in replacements.items()}
        expanded_var_replacements = {var: ([_pack_if_variable(value, self.literal_expr_by_unique_name) for value in values]
                                           if isinstance(values, list)
                                           else _pack_if_variable(values, self.literal_expr_by_unique_name))
                                     for var, values in expanded_var_replacements.items()}
        expr = replace_var_with_expr_in_expr(expr=_pack_if_variable(expr, self.literal_expr_by_unique_name),
                                             replacement_expr_by_var=replacements,
                                             replacement_expr_by_expanded_var=expanded_var_replacements)
        if isinstance(expr, list):
            return [_unpack_if_variable(expr1,
                                        self.var_names,
                                        self.literal_expr_by_unique_name)
                    for expr1 in expr]
        else:
            return _unpack_if_variable(expr,
                                       self.var_names,
                                       self.literal_expr_by_unique_name)

    def can_var_be_on_lhs(self, var: str) -> bool:
        return var in self.pattern_var_names

    def term_to_string(self, term: ir0.Expr):
        return '"' + ir0_to_cpp.expr_to_cpp_simple(term) + '"\n' + utils.ir_to_string(term)

    def equality_requires_syntactical_equality(self, term: ir0.Expr):
        return {
            ir0.Literal: lambda t: True,
            ir0.PointerTypeExpr: lambda t: True,
            ir0.ConstTypeExpr: lambda t: True,
            ir0.ArrayTypeExpr: lambda t: True,
            ir0.FunctionTypeExpr: lambda t: True,
            ir0.TemplateInstantiation: lambda t: True,
            # This is False because different expansions might expand to the same things (even a different number of
            # them).
            ir0.VariadicTypeExpansion: lambda t: False,
            # These are False because they operate on values, not types, the result can be expressed with a literal too.
            ir0.ComparisonExpr: lambda t: False,
            ir0.Int64BinaryOpExpr: lambda t: False,
            ir0.BoolBinaryOpExpr: lambda t: False,
            ir0.NotExpr: lambda t: False,
            ir0.UnaryMinusExpr: lambda t: False,
            # This is False in general because the result can be any type/value, but it's true in the special case of
            # nonlocal classes/templates (note: this assumes that they are actually classes/templates, not just
            # possibly-templated using declarations).
            ir0.AtomicTypeLiteral: lambda t: not t.is_local and not t.may_be_alias,
            # This is False because the result can be any type/value
            ir0.ClassMemberAccess: lambda t: False,
            # These two are False because of collapsing: std::is_same<int&, (int&) &&>
            ir0.ReferenceTypeExpr: lambda t: False,
            ir0.RvalueReferenceTypeExpr: lambda t: False,
        }[term.__class__](term)

    def may_be_equal(self, term1: ir0.Expr, term2: ir0.Expr):
        assert not self.is_same_term_excluding_args(term1, term2)
        assert not self.equality_requires_syntactical_equality(term1) or not self.equality_requires_syntactical_equality(term2)

        if not self.equality_requires_syntactical_equality(term1) and not self.equality_requires_syntactical_equality(term2):
            return True

        if self.equality_requires_syntactical_equality(term2):
            term2, term1 = term1, term2

        assert self.equality_requires_syntactical_equality(term1)
        assert not self.equality_requires_syntactical_equality(term2)

        if term2.__class__ in (ir0.ReferenceTypeExpr, ir0.RvalueReferenceTypeExpr) and term1.__class__ !=ir0.AtomicTypeLiteral:
            # A reference/rvalue-reference can't be equal to a non-reference, non-atomic expr.
            return False

        return True

def _replace_var_names_in_expr(expr: Union[ir0.Expr, List[ir0.Expr]], new_name_by_old_name: Mapping[str, str]):
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
                 pattern_var_expr_equations: Optional[List[Tuple[ir0.AtomicTypeLiteral,
                                                                 List[ir0.Expr]]]] = None,
                 value_by_expanded_pattern_variable: Optional[List[Tuple[ir0.AtomicTypeLiteral,
                                                                         List[ir0.Expr]]]] = None):
        assert (pattern_var_expr_equations is not None) == (kind == UnificationResultKind.CERTAIN)
        self.kind = kind
        self.value_by_pattern_variable = pattern_var_expr_equations
        self.value_by_expanded_pattern_variable = value_by_expanded_pattern_variable

def find_matches_in_unification_of_template_instantiation_with_definition(template_instantiation: ir0.TemplateInstantiation,
                                                                          local_var_definitions: Mapping[str, ir0.Expr],
                                                                          template_defn: ir0.TemplateDefn,
                                                                          identifier_generator: Iterable[str],
                                                                          verbose: bool) -> Tuple[List[Tuple[ir0.TemplateSpecialization,
                                                                                                             List[Tuple[ir0.AtomicTypeLiteral, List[ir0.Expr]]],
                                                                                                             List[Tuple[ir0.AtomicTypeLiteral, List[ir0.Expr]]]]],
                                                                                                  List[ir0.TemplateSpecialization]]:
    instantiation_vars = {var.cpp_type
                          for var in template_instantiation.get_free_vars()}

    certain_matches: List[Tuple[ir0.TemplateSpecialization,
                                List[Tuple[ir0.AtomicTypeLiteral,
                                           List[ir0.Expr]]]]] = \
        []
    possible_matches: List[ir0.TemplateSpecialization] = []
    for specialization in template_defn.specializations:
        result = unify(template_instantiation.args,
                       local_var_definitions,
                       specialization.patterns,
                       instantiation_vars,
                       {arg.name
                        for arg in specialization.args},
                       identifier_generator,
                       verbose)
        if result.kind == UnificationResultKind.CERTAIN:
            certain_matches.append((specialization, result.value_by_pattern_variable, result.value_by_expanded_pattern_variable))
        elif result.kind == UnificationResultKind.POSSIBLE:
            possible_matches.append(specialization)

    if template_defn.main_definition and template_defn.main_definition.body:
        patterns = [ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(var.name, var.expr_type, is_variadic=var.is_variadic))
                    if var.is_variadic
                    else ir0.AtomicTypeLiteral.for_local(var.name, var.expr_type, is_variadic=var.is_variadic)
                    for var in template_defn.main_definition.args]
        result = unify(template_instantiation.args,
                       local_var_definitions,
                       patterns,
                       instantiation_vars,
                       {var.name
                        for var in template_defn.main_definition.args},
                       identifier_generator,
                       verbose)
        assert result.kind != UnificationResultKind.IMPOSSIBLE
        if result.kind == UnificationResultKind.CERTAIN:
            certain_matches.append((template_defn.main_definition,
                                    result.value_by_pattern_variable,
                                    result.value_by_expanded_pattern_variable))
        else:
            possible_matches.append(template_defn.main_definition)

    if not certain_matches:
        return [], possible_matches

    might_be_best_match = [True for _ in certain_matches]
    for i, (specialization1, _, _) in enumerate(certain_matches):
        specialization1_arg_vars = {var.name for var in specialization1.args}
        for j, (specialization2, _, _) in enumerate(certain_matches):
            if i != j and might_be_best_match[i] and might_be_best_match[j]:
                specialization2_arg_vars = {var.name for var in specialization2.args}

                # Let's see if we can prove that certain_matches[i] is more strict than certain_matches[j]
                if not specialization1.patterns:
                    might_be_best_match[i] = False
                    continue
                if not specialization2.patterns:
                    might_be_best_match[j] = False
                    continue
                result = unify(specialization1.patterns,
                               dict(),
                               specialization2.patterns,
                               specialization1_arg_vars,
                               specialization2_arg_vars,
                               identifier_generator)
                if result.kind == UnificationResultKind.CERTAIN:
                    might_be_best_match[j] = False

    indexes = [index
               for index, might_be_best in enumerate(might_be_best_match)
               if might_be_best]
    assert indexes

    return [certain_matches[i]
            for i in indexes], possible_matches

def is_syntactically_equal(expr1: ir0.Expr, expr2: ir0.Expr):
    if not expr1.is_same_expr_excluding_subexpressions(expr2):
        return False
    subexpressions1 = list(expr1.get_direct_subexpressions())
    subexpressions2 = list(expr2.get_direct_subexpressions())
    if len(subexpressions1) != len(subexpressions2):
        return False
    return all(is_syntactically_equal(expr1, expr2)
               for expr1, expr2 in zip(subexpressions1, subexpressions2))

def unify_template_instantiation_with_definition(template_instantiation: ir0.TemplateInstantiation,
                                                 local_var_definitions: Mapping[str, ir0.Expr],
                                                 result_elem_name: str,
                                                 template_defn: ir0.TemplateDefn,
                                                 identifier_generator: Iterable[str],
                                                 verbose: bool) -> Union[None,
                                                                         Tuple[ir0.TemplateSpecialization,
                                                                               Optional[List[Tuple[ir0.AtomicTypeLiteral, List[ir0.Expr]]]]],
                                                                         Tuple[ir0.TemplateSpecialization,
                                                                               Optional[List[Tuple[ir0.AtomicTypeLiteral, List[ir0.Expr]]]]],
                                                                         ir0.Expr]:
    certain_matches, possible_matches = find_matches_in_unification_of_template_instantiation_with_definition(template_instantiation=template_instantiation,
                                                                                                              local_var_definitions=local_var_definitions,
                                                                                                              template_defn=template_defn,
                                                                                                              identifier_generator=identifier_generator,
                                                                                                              verbose=verbose)
    possible_matches = [(specialization, None, None)
                        for specialization in possible_matches]

    if certain_matches or possible_matches:
        result_exprs: List[ir0.Expr] = []
        for specialization, _, _ in itertools.chain(certain_matches, possible_matches):
            if any(isinstance(elem, ir0.StaticAssert)
                   for elem in specialization.body):
                break
            [result_elem] = [elem
                             for elem in specialization.body
                             if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)) and elem.name == result_elem_name]
            assert isinstance(result_elem, (ir0.ConstantDef, ir0.Typedef))
            if any(True for _ in result_elem.expr.get_free_vars()):
                break
            result_exprs.append(result_elem.expr)
        else:
            # If we didn't break out of the loop, it means that all certain/possible matches would lead to a result
            # expr with no free vars.

            first_result_expr = result_exprs[0]
            for expr in result_exprs:
                if not is_syntactically_equal(expr, first_result_expr):
                    break
            else:
                # If we didn't break out of the loop, it means that all certain/possible matches would lead to *the same*
                # result expr with no free vars.
                return first_result_expr

    if possible_matches:
        # This must be stricter than all certain matches (if any) so we can't pick one for sure.
        if verbose:
            print('No unification found for template %s because there was a result with kind POSSIBLE, so we can\'t inline that.' % template_defn.name)
        return None

    if not certain_matches:
        if verbose:
            print('No unification found for template %s because there were no matches with kind==CERTAIN, so we can\'t inline that.' % template_defn.name)
        return None

    if len(certain_matches) == 1:
        return certain_matches[0]

    # We've found multiple specializations that definitely match and aren't stricter than each other.

    # We can't say for certain which one will be chosen (it probably depends on the specific arguments of the caller
    # template).
    if verbose:
        print('No unification found for template %s because there were multiple specializations with kind==CERTAIN and none of them was stricter than the others. Solutions:\n%s' % (
            template_defn.name,
            '\n'.join('{%s}' % ', '.join('%s = [%s]' % (pattern_var.cpp_type, ', '.join(ir0_to_cpp.expr_to_cpp_simple(value) for value in values))
                                                        for pattern_var, values in replacements)
                      for specialization, replacements in certain_matches)))
    return None

def unify(initial_exprs: List[ir0.Expr],
          local_var_definitions: Mapping[str, ir0.Expr],
          patterns: List[ir0.Expr],
          expr_variables: Set[str],
          pattern_variables: Set[str],
          identifier_generator: Iterable[str],
          verbose: bool = True) -> UnificationResult:
    # We need to replace local literals before doing the unification, to avoid assuming that e.g. T in an expr
    # is equal to T in a pattern just because they have the same name.

    lhs_type_literal_names = set(local_var_definitions.keys())
    for expr in itertools.chain(initial_exprs, local_var_definitions.values()):
        for expr_literal in expr.get_free_vars():
            lhs_type_literal_names.add(expr_literal.cpp_type)

    unique_var_name_by_expr_type_literal_name = bidict({lhs_type_literal_name: next(identifier_generator)
                                                        for lhs_type_literal_name in lhs_type_literal_names})

    unique_var_name_by_pattern_type_literal_name = bidict({pattern_literal.cpp_type: next(identifier_generator)
                                                           for pattern in patterns
                                                           for pattern_literal in pattern.get_free_vars()})


    unique_var_names = set()
    for expr_var_name, unique_var_name in unique_var_name_by_expr_type_literal_name.items():
        if expr_var_name in expr_variables or expr_var_name in local_var_definitions:
            unique_var_names.add(unique_var_name)
    for pattern_var_name, unique_var_name in unique_var_name_by_pattern_type_literal_name.items():
        if pattern_var_name in pattern_variables:
            unique_var_names.add(unique_var_name)

    literal_expr_by_unique_name: Dict[str, ir0.AtomicTypeLiteral] = dict()

    lhs = [_replace_var_names_in_expr(expr, unique_var_name_by_expr_type_literal_name)
           for expr in initial_exprs]
    rhs = [_replace_var_names_in_expr(pattern, unique_var_name_by_pattern_type_literal_name)
           for pattern in patterns]
    context = [(unique_var_name_by_expr_type_literal_name[local_var_name], _replace_var_names_in_expr(value, unique_var_name_by_expr_type_literal_name))
               for local_var_name, value in local_var_definitions.items()]

    lhs = [_unpack_if_variable(expr, unique_var_names, literal_expr_by_unique_name)
           for expr in lhs]
    rhs = [_unpack_if_variable(pattern, unique_var_names, literal_expr_by_unique_name)
           for pattern in rhs]
    context = {_unpack_if_variable(var, unique_var_names, literal_expr_by_unique_name): _unpack_if_variable(expr, unique_var_names, literal_expr_by_unique_name)
               for var, expr in context}

    unification_strategy = _ExprUnificationStrategy(unique_var_names,
                                                    set(unique_var_name_by_pattern_type_literal_name.inv.keys()),
                                                    literal_expr_by_unique_name)
    try:
        var_expr_equations, expanded_var_expr_equations = unification.unify([(lhs, rhs)],
                                                                            context,
                                                                            unification_strategy)
    except unification.UnificationFailedException:
        if verbose:
            print('unify(exprs=[%s], local_var_definitions={%s}, patterns=[%s], expr_variables=[%s], pattern_variables=[%s], ...):\nUsing name mappings: %s, %s\nReturning IMPOSSIBLE due to exception: %s' % (
                ', '.join(ir0_to_cpp.expr_to_cpp_simple(expr) for expr in initial_exprs),
                ', '.join('%s = %s' % (var, ir0_to_cpp.expr_to_cpp_simple(expr)) for var, expr in local_var_definitions.items()),
                ', '.join(ir0_to_cpp.expr_to_cpp_simple(pattern) for pattern in patterns),
                ', '.join(expr_variable for expr_variable in expr_variables),
                ', '.join(pattern_variable for pattern_variable in pattern_variables),
                unique_var_name_by_expr_type_literal_name,
                unique_var_name_by_pattern_type_literal_name,
                traceback.format_exc()))
        return UnificationResult(UnificationResultKind.IMPOSSIBLE)
    except unification.UnificationAmbiguousException:
        if verbose:
            print('unify(exprs=[%s], local_var_definitions={%s}, patterns=[%s], expr_variables=[%s], pattern_variables=[%s], ...):\nUsing name mappings: %s, %s\nReturning POSSIBLE due to exception: %s' % (
                ', '.join(ir0_to_cpp.expr_to_cpp_simple(expr) for expr in initial_exprs),
                ', '.join('%s = %s' % (var, ir0_to_cpp.expr_to_cpp_simple(expr)) for var, expr in local_var_definitions.items()),
                ', '.join(ir0_to_cpp.expr_to_cpp_simple(pattern) for pattern in patterns),
                ', '.join(expr_variable for expr_variable in expr_variables),
                ', '.join(pattern_variable for pattern_variable in pattern_variables),
                unique_var_name_by_expr_type_literal_name,
                unique_var_name_by_pattern_type_literal_name,
                traceback.format_exc()))
        return UnificationResult(UnificationResultKind.POSSIBLE)
    except AssertionError as e:
        print('unify(exprs=[%s], local_var_definitions={%s}, patterns=[%s], expr_variables=[%s], pattern_variables=[%s], ...):\nUsing name mappings: %s, %s\nAssertionError' % (
            ', '.join(ir0_to_cpp.expr_to_cpp_simple(expr) for expr in initial_exprs),
            ', '.join('%s = %s' % (var, ir0_to_cpp.expr_to_cpp_simple(expr)) for var, expr in local_var_definitions.items()),
            ', '.join(ir0_to_cpp.expr_to_cpp_simple(pattern) for pattern in patterns),
            ', '.join(expr_variable for expr_variable in expr_variables),
            ', '.join(pattern_variable for pattern_variable in pattern_variables),
            unique_var_name_by_expr_type_literal_name,
            unique_var_name_by_pattern_type_literal_name))
        raise

    try:
        var_expr_equations = unification.canonicalize(var_expr_equations, expanded_var_expr_equations, unification_strategy)
    except unification.CanonicalizationFailedException:
        if verbose:
            print('unify(exprs=[%s], local_var_definitions={%s}, patterns=[%s], expr_variables=[%s], pattern_variables=[%s], ...):\nUsing name mappings: %s, %s\nReturning POSSIBLE due to exception: %s' % (
                ', '.join(ir0_to_cpp.expr_to_cpp_simple(expr) for expr in initial_exprs),
                ', '.join('%s = %s' % (var, ir0_to_cpp.expr_to_cpp_simple(expr)) for var, expr in local_var_definitions.items()),
                ', '.join(ir0_to_cpp.expr_to_cpp_simple(pattern) for pattern in patterns),
                ', '.join(expr_variable for expr_variable in expr_variables),
                ', '.join(pattern_variable for pattern_variable in pattern_variables),
                unique_var_name_by_expr_type_literal_name,
                unique_var_name_by_pattern_type_literal_name,
                traceback.format_exc()))
        return UnificationResult(UnificationResultKind.POSSIBLE)
    except AssertionError as e:
        print('unify(exprs=[%s], local_var_definitions={%s}, patterns=[%s], expr_variables=[%s], pattern_variables=[%s], ...):\nUsing name mappings: %s, %s\nvar_expr_equations = %s\nAssertionError' % (
            ', '.join(ir0_to_cpp.expr_to_cpp_simple(expr) for expr in initial_exprs),
            ', '.join('%s = %s' % (var, ir0_to_cpp.expr_to_cpp_simple(expr)) for var, expr in local_var_definitions.items()),
            ', '.join(ir0_to_cpp.expr_to_cpp_simple(pattern) for pattern in patterns),
            ', '.join(expr_variable for expr_variable in expr_variables),
            ', '.join(pattern_variable for pattern_variable in pattern_variables),
            unique_var_name_by_expr_type_literal_name,
            unique_var_name_by_pattern_type_literal_name,
            var_expr_equations))
        raise

    var_expr_equations = [(_pack_if_variable(var, literal_expr_by_unique_name),
                           [_pack_if_variable(expr, literal_expr_by_unique_name) for expr in exprs]
                           if isinstance(exprs, list)
                           else _pack_if_variable(exprs, literal_expr_by_unique_name))
                          for var, exprs in var_expr_equations]

    # At this point all equations should be of the form var=expr, with var a variable from a pattern and expr containing
    # no vars from patterns.
    for lhs_var, exprs in var_expr_equations:
        if isinstance(lhs_var, ir0.VariadicTypeExpansion):
            lhs_var = lhs_var.expr
        if lhs_var.cpp_type in unique_var_name_by_pattern_type_literal_name.inv:
            if isinstance(exprs, list):
                for expr in exprs:
                    for rhs_var in expr.get_free_vars():
                        assert rhs_var.cpp_type not in unique_var_name_by_pattern_type_literal_name.inv
            else:
                for rhs_var in exprs.get_free_vars():
                    assert rhs_var.cpp_type not in unique_var_name_by_pattern_type_literal_name.inv

    # We reverse the var renaming done above
    result_var_expr_equations: List[Tuple[ir0.AtomicTypeLiteral, List[ir0.Expr]]] = []
    result_expanded_var_expr_equations: List[Tuple[ir0.AtomicTypeLiteral, List[ir0.Expr]]] = []
    for var, exprs in var_expr_equations:
        if isinstance(var, ir0.VariadicTypeExpansion):
            assert isinstance(exprs, list)
            result_expanded_var_expr_equations.append((_replace_var_names_in_expr(var, unique_var_name_by_pattern_type_literal_name.inv),
                                                       [_replace_var_names_in_expr(expr, unique_var_name_by_expr_type_literal_name.inv)
                                                        for expr in exprs]))
        else:
            result_var_expr_equations.append((_replace_var_names_in_expr(var, unique_var_name_by_pattern_type_literal_name.inv),
                                              _replace_var_names_in_expr(exprs, unique_var_name_by_expr_type_literal_name.inv)))

    for var, exprs in var_expr_equations:
        for expr in (exprs if isinstance(exprs, list) else (exprs,)):
            if var.expr_type != expr.expr_type:
                if verbose:
                    print('unify(exprs=[%s], local_var_definitions={%s}, patterns=[%s], expr_variables=[%s], pattern_variables=[%s], ...):\nUsing name mappings: %s, %s\nReturning IMPOSSIBLE due to type mismatch:\n%s\nwith type:\n%s\n=== vs ===\n%s\nwith type:\m%s' % (
                        ', '.join(ir0_to_cpp.expr_to_cpp_simple(expr) for expr in initial_exprs),
                        ', '.join('%s = %s' % (var, ir0_to_cpp.expr_to_cpp_simple(expr)) for var, expr in local_var_definitions.items()),
                        ', '.join(ir0_to_cpp.expr_to_cpp_simple(pattern) for pattern in patterns),
                        ', '.join(expr_variable for expr_variable in expr_variables),
                        ', '.join(pattern_variable for pattern_variable in pattern_variables),
                        unique_var_name_by_expr_type_literal_name,
                        unique_var_name_by_pattern_type_literal_name,
                        ir0_to_cpp.expr_to_cpp_simple(var),
                        str(var.expr_type),
                        ir0_to_cpp.expr_to_cpp_simple(expr),
                        str(expr.expr_type)))
                return UnificationResult(UnificationResultKind.IMPOSSIBLE)

    for var, _ in result_var_expr_equations:
        assert isinstance(var, ir0.AtomicTypeLiteral)

    for var, _ in result_expanded_var_expr_equations:
        assert isinstance(var, ir0.VariadicTypeExpansion) and isinstance(var.expr, ir0.AtomicTypeLiteral)

    if verbose:
        print('unify(exprs=[%s], local_var_definitions={%s}, patterns=[%s], expr_variables=[%s], pattern_variables=[%s], ...):\nUsing name mappings: %s, %s\nReturning CERTAIN with result_var_expr_equations:\n%s\nresult_expanded_var_expr_equations:\n%s' % (
            ', '.join(ir0_to_cpp.expr_to_cpp_simple(expr) for expr in initial_exprs),
            ', '.join('%s = %s' % (var, ir0_to_cpp.expr_to_cpp_simple(expr)) for var, expr in local_var_definitions.items()),
            ', '.join(ir0_to_cpp.expr_to_cpp_simple(pattern) for pattern in patterns),
            ', '.join(expr_variable for expr_variable in expr_variables),
            ', '.join(pattern_variable for pattern_variable in pattern_variables),
            unique_var_name_by_expr_type_literal_name,
            unique_var_name_by_pattern_type_literal_name,
            '\n'.join(ir0_to_cpp.expr_to_cpp_simple(var) + ' = [' + ', '.join(ir0_to_cpp.expr_to_cpp_simple(expr)
                                                                              for expr in (exprs if isinstance(exprs, list) else (exprs,))) + ']'
                      for var, exprs in result_var_expr_equations),
            '\n'.join(ir0_to_cpp.expr_to_cpp_simple(var) + ' = [' + ', '.join(ir0_to_cpp.expr_to_cpp_simple(expr)
                                                                              for expr in (exprs if isinstance(exprs, list) else (exprs,))) + ']'
                      for var, exprs in result_expanded_var_expr_equations)))

    return UnificationResult(UnificationResultKind.CERTAIN, result_var_expr_equations, result_expanded_var_expr_equations)
