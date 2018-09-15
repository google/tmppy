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
from typing import Iterable, List, Dict, Union, Tuple

import pytest

from _py2tmp import unification

class Term:
    def __init__(self, name: str, args: List[Union[str, 'Term']]):
        self.name = name
        self.args = args

    def __str__(self):
        return '%s(%s)' % (self.name, ', '.join(str(arg) for arg in self.args))

Expr = Union[str, Term]

class ExampleUnificationStrategy(unification.UnificationStrategy[Term]):
    def is_same_term_excluding_args(self, term1: Term, term2: Term) -> bool:
        return term1.name == term2.name

    def term_copy_with_args(self, term: Term, new_args: List[Union[str, Term]]) -> Term:
        return Term(term.name, new_args)

    def get_term_args(self, t: Term):
        return t.args

EXAMPLE_UNIFICATION_STRATEGY = ExampleUnificationStrategy()

# This is not defined as __eq__ to make sure that the unification implementation doesn't rely on TermT's __eq__.
def expr_equals(expr1: Union[str, Term], expr2: Union[str, Term]):
    if isinstance(expr1, str):
        return isinstance(expr2, str) and expr1 == expr2
    if isinstance(expr1, Term):
        return isinstance(expr2, Term) and expr1.name == expr2.name and len(expr1.args) == len(expr2.args) and all(expr_equals(arg1, arg2)
                                                                                                                   for arg1, arg2 in zip(expr1.args, expr2.args))
    raise NotImplementedError('Unexpected expr type: %s' % expr1.__class__.__name__)

def unify(expr_expr_equations: List[Tuple[Expr, Expr]], canonicalize: bool):
    var_expr_equations = unification.unify(expr_expr_equations, EXAMPLE_UNIFICATION_STRATEGY, canonicalize=canonicalize)
    return {lhs: str(rhs)
            for lhs, rhs in var_expr_equations.items()}

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_no_equalities(canonicalize):
    equations = unify([], canonicalize)
    assert equations == {}

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_trivial_variable_equality(canonicalize):
    equations = unify([
        ('x', 'x'),
    ], canonicalize)
    assert equations == {}

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_trivial_term_equality(canonicalize):
    equations = unify([
        (Term('f', ['x', 'y']), Term('f', ['x', 'y'])),
    ], canonicalize)
    assert equations == {}

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_terms_with_different_arg_number_error(canonicalize):
    with pytest.raises(unification.UnificationFailedException):
        unify([
            (Term('f', ['x']), Term('f', ['x', 'y'])),
        ], canonicalize)

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_terms_with_different_name_error(canonicalize):
    with pytest.raises(unification.UnificationFailedException):
        unify([
            (Term('f', ['x']), Term('g', ['x'])),
        ], canonicalize)

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_one_equality_variable(canonicalize):
    equations = unify([
        ('x', 'y'),
    ], canonicalize)
    assert equations == {
        'x': 'y',
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_one_equality_term(canonicalize):
    equations = unify([
        ('x', Term('f', ['y', 'z'])),
    ], canonicalize)
    assert equations == {
        'x': 'f(y, z)',
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_one_equality_term_swapped(canonicalize):
    equations = unify([
        (Term('f', ['y', 'z']), 'x'),
    ], canonicalize)
    assert equations == {
        'x': 'f(y, z)',
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_unify_two_equalities_no_substitution(canonicalize):
    equations = unify([
        ('x', Term('f', ['y', 'z'])),
        ('k', Term('g', ['n'])),
    ], canonicalize)
    assert equations == {
        'x': 'f(y, z)',
        'k': 'g(n)',
    }

def test_unify_two_equalities_with_substitution():
    equations = unify([
        ('x', Term('f', ['y', 'z'])),
        ('y', Term('g', ['n'])),
    ], canonicalize=True)
    assert equations == {
        'x': 'f(g(n), z)',
        'y': 'g(n)',
    }

def test_unify_two_equalities_with_substitution_not_performed_without_canonicalize():
    equations = unify([
        ('x', Term('f', ['y', 'z'])),
        ('y', Term('g', ['n'])),
    ], canonicalize=False)
    assert equations == {
        'x': 'f(y, z)',
        'y': 'g(n)',
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_equality_loop_length_two_impossible(canonicalize):
    with pytest.raises(unification.UnificationFailedException):
        unify([
            ('x', Term('f', ['y'])),
            ('y', 'x'),
        ], canonicalize)

@pytest.mark.parametrize('canonicalize', [True, False])
def test_equality_loop_length_three_impossible(canonicalize):
    with pytest.raises(unification.UnificationFailedException):
        unify([
            ('x', 'z'),
            ('y', Term('f', ['x'])),
            ('y', 'z'),
        ], canonicalize)

@pytest.mark.parametrize('canonicalize', [True, False])
def test_variable_equality_loop_length_two(canonicalize):
    equations = unify([
        ('x', 'y'),
        ('y', 'x'),
    ], canonicalize)
    assert equations == {
        'y': 'x',
    }

@pytest.mark.parametrize('canonicalize', [True, False])
def test_variable_equality_loop_length_three_ok(canonicalize):
    equations = unify([
        ('x', 'y'),
        ('y', 'z'),
        ('z', 'x'),
    ], canonicalize)
    assert equations == {
        'y': 'x',
        'z': 'x',
    }

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
        ('y', Term('g', ['n'])),
        ('x', Term('f', ['y', 'z'])),
    ], canonicalize=False)
    assert equations == {
        'x': 'f(y, z)',
        'y': 'g(n)',
    }

def test_unify_two_equalities_with_substitution_other_order_with_canonicalization():
    equations = unify([
        ('y', Term('g', ['n'])),
        ('x', Term('f', ['y', 'z'])),
    ], canonicalize=True)
    assert equations == {
        'x': 'f(g(n), z)',
        'y': 'g(n)',
    }
