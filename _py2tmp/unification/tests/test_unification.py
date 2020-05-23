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

from typing import List, Union, Tuple, Dict

import pytest

from _py2tmp.compiler.testing import main
from _py2tmp.unification import TupleExpansion, UnificationStrategy, _unification, _canonicalization, \
    UnificationStrategyForCanonicalization, \
    CanonicalizationFailedException, UnificationFailedException, UnificationAmbiguousException


class Term:
    def __init__(self, name: str, args: Tuple[Union[str, 'Term'], ...]):
        self.name = name
        self.args = args

    def __repr__(self) -> str:
        return '%s(%s)' % (self.name, ', '.join(str(arg) for arg in self.args))

NonTupleExpr = Union[str, Term, TupleExpansion[Term]]
Expr = Union[NonTupleExpr, Tuple[NonTupleExpr, ...]]

class ExampleUnificationStrategy(UnificationStrategyForCanonicalization[Term]):
    def __init__(self, vars_forbidden_on_lhs: List[str]):
        self.vars_forbidden_on_lhs = vars_forbidden_on_lhs

    def is_same_term_excluding_args(self, term1: Term, term2: Term):
        return term1.name == term2.name

    def term_copy_with_args(self, term: Term, new_args: Tuple[Union[str, Term], ...]):
        return Term(term.name, new_args)

    def get_term_args(self, t: Term):
        return t.args

    def can_var_be_on_lhs(self, var: str):
        return var not in self.vars_forbidden_on_lhs

    def term_to_string(self, term: Term) -> str:
        return repr(term)

    def equality_requires_syntactical_equality(self, term: Term) -> bool:
        return True

    def may_be_equal(self, term1: Term, term2: Term) -> bool:
        return True

    def replace_variables_in_expr(self, expr: UnificationStrategy.Expr,
                                  replacements: Dict[str, Tuple[UnificationStrategy.Expr, ...]],
                                  expanded_var_replacements: Dict[str, Tuple[UnificationStrategy.Expr, ...]]) -> UnificationStrategy.Expr:
        if isinstance(expr, str):
            if expr in replacements:
                return replacements[expr]
            if expr in expanded_var_replacements:
                return expanded_var_replacements[expr]
            return expr

        if isinstance(expr, TupleExpansion):
            return TupleExpansion(self.replace_variables_in_expr(expr.expr, replacements, expanded_var_replacements))

        return self.term_copy_with_args(expr,
                                        tuple(self.replace_variables_in_expr(arg, replacements, expanded_var_replacements)
                                              for arg in self.get_term_args(expr)))


# This is not defined as __eq__ to make sure that the unification implementation doesn't rely on TermT's __eq__.
def expr_equals(expr1: Union[str, Term], expr2: Union[str, Term]):
    if isinstance(expr1, str):
        return isinstance(expr2, str) and expr1 == expr2
    if isinstance(expr1, Term):
        return isinstance(expr2, Term) and expr1.name == expr2.name and len(expr1.args) == len(expr2.args) and all(expr_equals(arg1, arg2)
                                                                                                                   for arg1, arg2 in zip(expr1.args, expr2.args))
    raise NotImplementedError('Unexpected expr type: %s' % expr1.__class__.__name__)

def expr_to_str(expr: Expr):
    if isinstance(expr, str):
        return expr
    elif isinstance(expr, TupleExpansion):
        return '%s...' % expr_to_str(expr.expr)
    else:
        return ExampleUnificationStrategy([]).term_to_string(expr)

def unify(expr_expr_equations: List[Tuple[Expr, Expr]],
          canonicalize: bool,
          vars_forbidden_on_lhs: List[str] = ()):
    strategy = ExampleUnificationStrategy(vars_forbidden_on_lhs)
    var_expr_equations, expanded_var_expr_equations = _unification.unify(expr_expr_equations, dict(), strategy)

    result_dict = dict()
    if canonicalize:
        var_expr_equations = _canonicalization.canonicalize(var_expr_equations, expanded_var_expr_equations, strategy)
        for lhs, rhs in var_expr_equations:
            if isinstance(lhs, TupleExpansion):
                result_dict['%s...' % lhs.expr] = '[' + ', '.join(expr_to_str(rhs_elem)
                                                                  for rhs_elem in rhs) + ']'
            else:
                result_dict[lhs] = expr_to_str(rhs)
    else:
        for lhs, rhs in var_expr_equations.items():
            result_dict[lhs] = expr_to_str(rhs)
        for lhs, rhs in expanded_var_expr_equations.items():
            result_dict['%s...' % lhs] = '[' + ', '.join(expr_to_str(rhs_elem)
                                                         for rhs_elem in rhs) + ']'

    return result_dict

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['x']),
])
def test_unify_no_equalities(canonicalize, vars_forbidden_on_lhs):
    equations = unify([], canonicalize)
    assert equations == {}

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['x']),
])
def test_unify_trivial_variable_equality(canonicalize, vars_forbidden_on_lhs):
    equations = unify([
        ('x', 'x'),
    ], canonicalize, vars_forbidden_on_lhs)
    assert equations == {}

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['x', 'y']),
])
def test_unify_trivial_term_equality(canonicalize, vars_forbidden_on_lhs):
    equations = unify([
        (Term('f', ('x', 'y')), Term('f', ('x', 'y'))),
    ], canonicalize)
    assert equations == {}

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['x', 'y']),
])
def test_unify_terms_with_different_arg_number_error(canonicalize, vars_forbidden_on_lhs):
    with pytest.raises(UnificationFailedException):
        unify([
            (Term('f', ('x',)), Term('f', ('x', 'y'))),
        ], canonicalize)

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['x']),
])
def test_unify_terms_with_different_name_error(canonicalize, vars_forbidden_on_lhs):
    with pytest.raises(UnificationFailedException):
        unify([
            (Term('f', ('x',)), Term('g', ('x',))),
        ], canonicalize)

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['y']),
])
def test_unify_one_equality_variable(canonicalize, vars_forbidden_on_lhs):
    equations = unify([
        ('x', 'y'),
    ], canonicalize)
    assert equations == {
        'x': 'y',
    }

def test_unify_one_equality_variable_flipped_due_to_lhs_var_constraint():
    equations = unify([
        ('x', 'y'),
    ], canonicalize=True, vars_forbidden_on_lhs=['x'])
    assert equations == {
        'y': 'x',
    }

def test_unify_one_equality_variable_impossible_due_to_lhs_var_constraint():
    with pytest.raises(CanonicalizationFailedException):
        unify([
            ('x', 'y'),
        ], canonicalize=True, vars_forbidden_on_lhs=['x', 'y'])

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['y', 'z']),
])
def test_unify_one_equality_term(canonicalize, vars_forbidden_on_lhs):
    equations = unify([
        ('x', Term('f', ('y', 'z'))),
    ], canonicalize)
    assert equations == {
        'x': 'f(y, z)',
    }

def test_unify_one_equality_term_impossible_due_to_lhs_var_constraint():
    with pytest.raises(CanonicalizationFailedException):
        unify([
            ('x', Term('f', ('y', 'z'))),
        ], canonicalize=True, vars_forbidden_on_lhs=['x'])

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['y', 'z']),
])
def test_unify_one_equality_term_swapped(canonicalize, vars_forbidden_on_lhs):
    equations = unify([
        (Term('f', ('y', 'z')), 'x'),
    ], canonicalize)
    assert equations == {
        'x': 'f(y, z)',
    }

def test_unify_one_equality_term_swapped_impossible_due_to_lhs_var_constraint():
    with pytest.raises(CanonicalizationFailedException):
        unify([
            (Term('f', ('y', 'z')), 'x'),
        ], canonicalize=True, vars_forbidden_on_lhs=['x'])

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['y', 'z', 'n']),
])
def test_unify_two_equalities_no_substitution(canonicalize, vars_forbidden_on_lhs):
    equations = unify([
        ('x', Term('f', ('y', 'z'))),
        ('k', Term('g', ('n',))),
    ], canonicalize)
    assert equations == {
        'x': 'f(y, z)',
        'k': 'g(n)',
    }

@pytest.mark.parametrize('vars_forbidden_on_lhs', [['x'], ['k']])
def test_unify_two_equalities_no_substitution_impossible_due_to_lhs_var_constraint(vars_forbidden_on_lhs):
    with pytest.raises(CanonicalizationFailedException):
        unify([
            ('x', Term('f', ('y', 'z'))),
            ('k', Term('g', ('n',))),
        ], canonicalize=True, vars_forbidden_on_lhs=vars_forbidden_on_lhs)

@pytest.mark.parametrize('vars_forbidden_on_lhs', [
    [],
    ['n', 'z'],
])
def test_unify_two_equalities_with_substitution(vars_forbidden_on_lhs):
    equations = unify([
        ('x', Term('f', ('y', 'z'))),
        ('y', Term('g', ('n',))),
    ], canonicalize=True, vars_forbidden_on_lhs=vars_forbidden_on_lhs)
    assert equations == {
        'x': 'f(g(n), z)',
        'y': 'g(n)',
    }

def test_unify_two_equalities_with_substitution_not_performed_without_canonicalize():
    equations = unify([
        ('x', Term('f', ('y', 'z'))),
        ('y', Term('g', ('n',))),
    ], canonicalize=False)
    assert equations == {
        'x': 'f(y, z)',
        'y': 'g(n)',
    }

@pytest.mark.parametrize('vars_forbidden_on_lhs', [
    ['x'],
    ['y'],
])
def test_unify_two_equalities_with_substitution_impossible_due_to_lhs_var_constraint(vars_forbidden_on_lhs):
    with pytest.raises(CanonicalizationFailedException):
        unify([
            ('x', Term('f', ('y', 'z'))),
            ('y', Term('g', ('n',))),
        ], canonicalize=True, vars_forbidden_on_lhs=vars_forbidden_on_lhs)

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['x', 'y']),
])
def test_equality_loop_length_two_impossible(canonicalize, vars_forbidden_on_lhs):
    with pytest.raises(UnificationFailedException):
        unify([
            ('x', Term('f', ('y',))),
            ('y', 'x'),
        ], canonicalize, vars_forbidden_on_lhs)

@pytest.mark.parametrize('canonicalize,vars_forbidden_on_lhs', [
    (False, []),
    (True, []),
    (True, ['x', 'y', 'z']),
])
def test_equality_loop_length_three_impossible(canonicalize, vars_forbidden_on_lhs):
    with pytest.raises(UnificationFailedException):
        unify([
            ('x', 'z'),
            ('y', Term('f', ('x',))),
            ('y', 'z'),
        ], canonicalize, vars_forbidden_on_lhs)

def test_variable_equality_loop_length_two_without_canonicalization():
    equations = unify([
        ('x', 'y'),
        ('y', 'x'),
    ], canonicalize=False)
    assert equations == {
        'y': 'x',
    }

@pytest.mark.parametrize('vars_forbidden_on_lhs', [
    [],
    ['y'],
])
def test_variable_equality_loop_length_two_with_canonicalization(vars_forbidden_on_lhs):
    equations = unify([
        ('x', 'y'),
        ('y', 'x'),
    ], canonicalize=True, vars_forbidden_on_lhs=vars_forbidden_on_lhs)
    assert equations == {
        'x': 'y',
    }

def test_variable_equality_loop_length_two_with_canonicalization_flipped_due_to_lhs_var_constraint():
    equations = unify([
        ('x', 'y'),
        ('y', 'x'),
    ], canonicalize=True, vars_forbidden_on_lhs=['x'])
    assert equations == {
        'y': 'x',
    }

def test_variable_equality_loop_length_two_with_canonicalization_impossible_due_to_lhs_var_constraint():
    with pytest.raises(CanonicalizationFailedException):
        unify([
            ('x', 'y'),
            ('y', 'x'),
        ], canonicalize=True, vars_forbidden_on_lhs=['x', 'y'])

def test_variable_equality_loop_length_three_ok_without_canonicalization():
    equations = unify([
        ('x', 'y'),
        ('y', 'z'),
        ('z', 'x'),
    ], canonicalize=False)
    assert equations == {
        'y': 'x',
        'z': 'x',
    }

@pytest.mark.parametrize('vars_forbidden_on_lhs', [
    [],
    ['z'],
])
def test_variable_equality_loop_length_three_ok_with_canonicalization(vars_forbidden_on_lhs):
    equations = unify([
        ('x', 'y'),
        ('y', 'z'),
        ('z', 'x'),
    ], canonicalize=True, vars_forbidden_on_lhs=vars_forbidden_on_lhs)
    assert equations == {
        'x': 'z',
        'y': 'z',
    }

def test_variable_equality_loop_length_three_ok_with_canonicalization_rearranged_due_to_lhs_var_constraint1():
    equations = unify([
        ('x', 'y'),
        ('y', 'z'),
        ('z', 'x'),
    ], canonicalize=True, vars_forbidden_on_lhs=['x'])
    assert equations == {
        'z': 'x',
        'y': 'x',
    }

def test_variable_equality_loop_length_three_ok_with_canonicalization_rearranged_due_to_lhs_var_constraint2():
    equations = unify([
        ('x', 'y'),
        ('y', 'z'),
        ('z', 'x'),
    ], canonicalize=True, vars_forbidden_on_lhs=['y'])
    assert equations == {
        'x': 'y',
        'z': 'y',
    }

def test_variable_equality_loop_length_three_ok_with_canonicalization_rearranged_due_to_lhs_var_constraint3():
    equations = unify([
        ('x', 'y'),
        ('y', 'z'),
        ('z', 'x'),
    ], canonicalize=True, vars_forbidden_on_lhs=['z'])
    assert equations == {
        'x': 'z',
        'y': 'z',
    }

@pytest.mark.parametrize('vars_forbidden_on_lhs', [
    ['x', 'y'],
    ['y', 'z'],
    ['x', 'z'],
    ['x', 'y', 'z'],
])
def test_variable_equality_loop_length_three_ok_with_canonicalization_impossible_due_to_lhs_var_constraint(vars_forbidden_on_lhs):
    with pytest.raises(CanonicalizationFailedException):
        unify([
            ('x', 'y'),
            ('y', 'z'),
            ('z', 'x'),
        ], canonicalize=True, vars_forbidden_on_lhs=vars_forbidden_on_lhs)

@pytest.mark.parametrize('canonicalize', [True, False])
def test_variable_equality_loop_length_three_other_order_ok(canonicalize):
    equations = unify([
        ('x', 'y'),
        ('y', 'z'),
        ('x', 'z'),
    ], canonicalize)
    assert equations == {
        'x': 'z',
        'y': 'z',
    }

def test_unify_two_equalities_with_substitution_other_order_without_canonicalization():
    equations = unify([
        ('y', Term('g', ('n',))),
        ('x', Term('f', ('y', 'z'))),
    ], canonicalize=False)
    assert equations == {
        'x': 'f(y, z)',
        'y': 'g(n)',
    }

def test_unify_two_equalities_with_substitution_other_order_with_canonicalization():
    equations = unify([
        ('y', Term('g', ('n',))),
        ('x', Term('f', ('y', 'z'))),
    ], canonicalize=True)
    assert equations == {
        'x': 'f(g(n), z)',
        'y': 'g(n)',
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_tuple_var_with_tuple_var(canonicalize):
    equations = unify([
        (TupleExpansion('x'), TupleExpansion('y')),
    ], canonicalize)
    assert equations == {
        'x': 'y'
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_tuple_var_with_empty_tuple(canonicalize):
    equations = unify([
        (TupleExpansion('x'), ()),
    ], canonicalize)
    assert equations == {
        'x...': '[]'
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_tuple_var_with_term(canonicalize):
    equations = unify([
        (TupleExpansion('x'), (Term('f', ('y',)),)),
    ], canonicalize)
    assert equations == {
        'x...': '[f(y)]'
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_tuples_common_prefix(canonicalize):
    equations = unify([
        (('x', 'y', TupleExpansion('z')), ('x', 'y', Term('f', ()), 'k')),
    ], canonicalize)
    assert equations == {
        'z...': '[f(), k]'
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_tuples_common_suffix(canonicalize):
    equations = unify([
        ((TupleExpansion('z'), 'x', 'y'), (Term('f', ()), 'k', 'x', 'y', )),
    ], canonicalize)
    assert equations == {
        'z...': '[f(), k]'
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_tuples_common_prefix_and_suffix(canonicalize):
    equations = unify([
        (('x', TupleExpansion('z'), 'y'), ('x', Term('f', ()), 'k', 'y')),
    ], canonicalize)
    assert equations == {
        'z...': '[f(), k]'
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_tuples_zero_to_many_tuple_vars(canonicalize):
    equations = unify([
        ((), (TupleExpansion('y'), TupleExpansion('z'))),
    ], canonicalize)
    assert equations == {
        'y...': '[]',
        'z...': '[]',
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_tuples_one_to_many_tuple_vars(canonicalize):
    equations = unify([
        ((TupleExpansion('x'),), (Term('f', ()), TupleExpansion('y'), Term('g', ()), TupleExpansion('z'), Term('h', ()))),
    ], canonicalize)
    assert equations == {
        'x...': '[f(), y..., g(), z..., h()]'
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_tuples_many_to_many_tuple_vars(canonicalize):
    with pytest.raises(UnificationAmbiguousException):
        unify([
            ((TupleExpansion('x'), Term('f', ()), TupleExpansion('y')), (TupleExpansion('z'), Term('f', ()), TupleExpansion('k'))),
        ], canonicalize)

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_tuples_many_to_many_tuple_vars_ok_if_same(canonicalize):
    equations = unify([
        ((TupleExpansion('x'), Term('f', ()), TupleExpansion('y')), (TupleExpansion('x'), Term('f', ()), TupleExpansion('y'))),
    ], canonicalize)
    assert equations == {}

if __name__== '__main__':
    main()
