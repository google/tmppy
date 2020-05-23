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
from typing import Union, Set, Iterable, Callable, Tuple

import pytest

from _py2tmp.ir0 import ir0
from _py2tmp.compiler.testing import main
from _py2tmp.ir0_optimization._unify import UnificationResultKind, _unify as unify_ir0, UnificationResult


def identifier_generator_fun() -> Iterable[str]:
    for i in itertools.count():
        yield 'X_%s' % i

def _unify(exprs: Tuple[ir0.Expr, ...],
           patterns: Tuple[ir0.Expr, ...],
           expr_variables: Set[str],
           pattern_variables: Set[str]) -> UnificationResult:
    return unify_ir0(exprs, dict(), patterns, expr_variables, pattern_variables, iter(identifier_generator_fun()), verbose=True)

def literal(value: Union[bool, int]):
    return ir0.Literal(value)

def type_literal(cpp_type: str):
    return ir0.AtomicTypeLiteral.for_nonlocal_type(cpp_type, may_be_alias=False)

def local_type_literal(cpp_type: str):
    return ir0.AtomicTypeLiteral.for_local(cpp_type, expr_type=ir0.TypeType(), is_variadic=False)

@pytest.mark.parametrize('expr_generator', [
    lambda: ir0.Literal(1),
    lambda: ir0.AtomicTypeLiteral.for_nonlocal_type('int', may_be_alias=False),
    lambda: ir0.PointerTypeExpr(type_literal('int')),
    lambda: ir0.ReferenceTypeExpr(type_literal('int')),
    lambda: ir0.RvalueReferenceTypeExpr(type_literal('int')),
    lambda: ir0.ConstTypeExpr(type_literal('int')),
    lambda: ir0.ArrayTypeExpr(type_literal('int')),
    lambda: ir0.FunctionTypeExpr(type_literal('int'), ()),
    lambda: ir0.FunctionTypeExpr(type_literal('int'), (type_literal('float'),)),
    lambda: ir0.ComparisonExpr(literal(1), literal(2), op='=='),
    lambda: ir0.Int64BinaryOpExpr(literal(1), literal(2), op='+'),
    lambda: ir0.BoolBinaryOpExpr(literal(True), literal(False), op='||'),
    lambda: ir0.NotExpr(literal(True)),
    lambda: ir0.UnaryMinusExpr(literal(1)),
    lambda: ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::vector',
                                                                                                args=(),
                                                                                                is_metafunction_that_may_return_error=False,
                                                                                                may_be_alias=False),
                                      args=(),
                                      instantiation_might_trigger_static_asserts=False),
    lambda: ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::vector',
                                                                                                args=(ir0.TemplateArgType(ir0.TypeType(), is_variadic=False),),
                                                                                                is_metafunction_that_may_return_error=False,
                                                                                                may_be_alias=False),
                                      args=(type_literal('int'),),
                                      instantiation_might_trigger_static_asserts=False),
    lambda: ir0.ClassMemberAccess(inner_expr=type_literal('MyClass'), member_name='value_type', expr_type=ir0.TypeType()),
], ids = [
    'Literal',
    'AtomicTypeLiteral',
    'PointerTypeExpr',
    'ReferenceTypeExpr',
    'RvalueReferenceTypeExpr',
    'ConstTypeExpr',
    'ArrayTypeExpr',
    'FunctionTypeExpr (no args)',
    'FunctionTypeExpr (1 arg)',
    'ComparisonExpr',
    'Int64BinaryOpExpr',
    'BoolBinaryOpExpr',
    'NotExpr',
    'UnaryMinusExpr',
    'TemplateInstantiation (no args)',
    'TemplateInstantiation (1 arg)',
    'ClassMemberAccess',
])
def test_unify_ir0_trivial_term_equality(expr_generator: Callable[[], ir0.Expr]):
    result = _unify((expr_generator(),), (expr_generator(),), expr_variables=set(), pattern_variables=set())
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == ()
    assert result.value_by_expanded_pattern_variable == ()

@pytest.mark.parametrize('expr1,expr2', [
    (ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local('Ts', expr_type=ir0.TypeType(), is_variadic=True)),
     ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local('Us', expr_type=ir0.TypeType(), is_variadic=True))),
])
def test_unify_ir0_term_equality_variadic_type_expansion(expr1: ir0.Expr, expr2: ir0.Expr):
    result = _unify((expr1,), (expr2,), expr_variables={'Ts'}, pattern_variables={'Us'})
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == (
        (ir0.AtomicTypeLiteral.for_local('Us', expr_type=ir0.TypeType(), is_variadic=True),
         ir0.AtomicTypeLiteral.for_local('Ts', expr_type=ir0.TypeType(), is_variadic=True)),
    )
    assert result.value_by_expanded_pattern_variable == ()

@pytest.mark.parametrize('expr1,expr2', [
    (ir0.Literal(1), ir0.Literal(2)),
    (ir0.AtomicTypeLiteral.for_nonlocal_type('int', may_be_alias=False),
     ir0.AtomicTypeLiteral.for_nonlocal_type('float', may_be_alias=False)),
    (ir0.AtomicTypeLiteral.for_nonlocal_template('std::vector', args=(), is_metafunction_that_may_return_error=False, may_be_alias=False),
     ir0.AtomicTypeLiteral.for_nonlocal_template('std::list', args=(), is_metafunction_that_may_return_error=False, may_be_alias=False)),
], ids = [
    'Literal, different value',
    'AtomicTypeLiteral.for_nonlocal_type, different cpp_type',
    'AtomicTypeLiteral.for_nonlocal_template, different cpp_type',
])
def test_unify_ir0_term_equality_fails_different_direct_values_in_term_syntactically_comparable_expr(expr1: ir0.Expr, expr2: ir0.Expr):
    result = _unify((expr1,), (expr2,), expr_variables=set(), pattern_variables=set())
    assert result.kind == UnificationResultKind.IMPOSSIBLE

@pytest.mark.parametrize('expr1,expr2', [
    (ir0.AtomicTypeLiteral.for_nonlocal_template('std::vector', args=(), is_metafunction_that_may_return_error=False, may_be_alias=False),
     ir0.AtomicTypeLiteral.for_nonlocal_template('std::vector', args=(ir0.TemplateArgType(ir0.TypeType(), is_variadic=False),), is_metafunction_that_may_return_error=False, may_be_alias=False)),
    (ir0.AtomicTypeLiteral.for_nonlocal_template('std::vector', args=(), is_metafunction_that_may_return_error=False, may_be_alias=False),
     ir0.AtomicTypeLiteral.for_nonlocal_template('std::vector', args=(), is_metafunction_that_may_return_error=True, may_be_alias=False)),
    (ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::vector',
                                                                                         args=(),
                                                                                         is_metafunction_that_may_return_error=False,
                                                                                         may_be_alias=False),
                               args=(),
                               instantiation_might_trigger_static_asserts=False),
     ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::vector',
                                                                                         args=(),
                                                                                         is_metafunction_that_may_return_error=False,
                                                                                         may_be_alias=False),
                               args=(),
                               instantiation_might_trigger_static_asserts=True)),
], ids = [
    'AtomicTypeLiteral.for_nonlocal_template, different arg_types',
    'AtomicTypeLiteral.for_nonlocal_template, different is_metafunction_that_may_return_error',
    'TemplateInstantiation, different instantiation_might_trigger_static_asserts',
])
def test_unify_ir0_term_equality_fails_different_direct_values_in_term_syntactically_comparable_expr_not_affecting_equality(expr1: ir0.Expr, expr2: ir0.Expr):
    result = _unify((expr1,), (expr2,), expr_variables=set(), pattern_variables=set())
    assert result.kind == UnificationResultKind.CERTAIN

@pytest.mark.parametrize('expr1,expr2', [
    (ir0.AtomicTypeLiteral.for_local('int', expr_type=ir0.TypeType(), is_variadic=False),
     ir0.AtomicTypeLiteral.for_local('float', expr_type=ir0.TypeType(), is_variadic=False)),
    (ir0.AtomicTypeLiteral.for_local('int', expr_type=ir0.TypeType(), is_variadic=False),
     ir0.AtomicTypeLiteral.for_local('int', expr_type=ir0.TypeType(), is_variadic=True)),
    (ir0.AtomicTypeLiteral.for_nonlocal_type('X', may_be_alias=True),
     ir0.AtomicTypeLiteral.for_nonlocal_type('Y', may_be_alias=True)),
    (ir0.AtomicTypeLiteral.for_nonlocal_template('F', args=(), is_metafunction_that_may_return_error=False, may_be_alias=True),
     ir0.AtomicTypeLiteral.for_nonlocal_template('G', args=(), is_metafunction_that_may_return_error=False, may_be_alias=True)),
    (ir0.ComparisonExpr(literal(1), literal(2), op='=='),
     ir0.ComparisonExpr(literal(1), literal(2), op='!=')),
    (ir0.Int64BinaryOpExpr(literal(1), literal(2), op='+'),
     ir0.Int64BinaryOpExpr(literal(1), literal(2), op='-')),
    (ir0.BoolBinaryOpExpr(literal(True), literal(False), op='||'),
     ir0.BoolBinaryOpExpr(literal(True), literal(False), op='&&')),
    (ir0.ClassMemberAccess(inner_expr=type_literal('MyClass'), member_name='value_type', expr_type=ir0.TypeType()),
     ir0.ClassMemberAccess(inner_expr=type_literal('MyClass'), member_name='pointer_type', expr_type=ir0.TypeType())),
], ids = [
    'AtomicTypeLiteral.for_local(), different cpp_type',
    'AtomicTypeLiteral.for_local(), different type',
    'AtomicTypeLiteral.for_nonlocal_type, different cpp_type',
    'AtomicTypeLiteral.for_nonlocal_template, different cpp_type',
    'ComparisonExpr, different op',
    'Int64BinaryOpExpr, different op',
    'BoolBinaryOpExpr, different op',
    'ClassMemberAccess, different member_name',
])
def test_unify_ir0_term_equality_fails_different_direct_values_in_term_non_syntactically_comparable_expr(expr1: ir0.Expr, expr2: ir0.Expr):
    result = _unify((expr1,), (expr2,), expr_variables=set(), pattern_variables=set())
    assert result.kind == UnificationResultKind.POSSIBLE

@pytest.mark.parametrize('expr1,expr2', [
    (ir0.AtomicTypeLiteral.for_nonlocal_type('X', may_be_alias=True),
     ir0.AtomicTypeLiteral.for_nonlocal_type('X', may_be_alias=False)),
    (ir0.AtomicTypeLiteral.for_nonlocal_template('F', args=(), is_metafunction_that_may_return_error=False, may_be_alias=True),
     ir0.AtomicTypeLiteral.for_nonlocal_template('F', args=(ir0.TemplateArgType(ir0.TypeType(), is_variadic=False),), is_metafunction_that_may_return_error=False, may_be_alias=True)),
    (ir0.AtomicTypeLiteral.for_nonlocal_template('F', args=(), is_metafunction_that_may_return_error=False, may_be_alias=True),
     ir0.AtomicTypeLiteral.for_nonlocal_template('F', args=(), is_metafunction_that_may_return_error=True, may_be_alias=True)),
    (ir0.AtomicTypeLiteral.for_nonlocal_template('F', args=(), is_metafunction_that_may_return_error=False, may_be_alias=True),
     ir0.AtomicTypeLiteral.for_nonlocal_template('F', args=(), is_metafunction_that_may_return_error=False, may_be_alias=False)),
    (ir0.ClassMemberAccess(inner_expr=type_literal('MyClass'), member_name='value_type', expr_type=ir0.TypeType()),
     ir0.ClassMemberAccess(inner_expr=type_literal('MyClass'), member_name='value_type', expr_type=ir0.Int64Type())),
], ids = [
    'AtomicTypeLiteral.for_nonlocal_type, different may_be_alias',
    'AtomicTypeLiteral.for_nonlocal_template, different arg_types',
    'AtomicTypeLiteral.for_nonlocal_template, different is_metafunction_that_may_return_error',
    'AtomicTypeLiteral.for_nonlocal_template, different may_be_alias',
    'ClassMemberAccess, different expr_type',
])
def test_unify_ir0_term_equality_fails_different_direct_values_in_term_non_syntactically_comparable_expr_not_affecting_equality(expr1: ir0.Expr, expr2: ir0.Expr):
    result = _unify((expr1,), (expr2,), expr_variables=set(), pattern_variables=set())
    assert result.kind == UnificationResultKind.CERTAIN

@pytest.mark.parametrize('expr_variables,pattern_variables', [
    (set(), {'T'}),
    ({'T'}, {'T'}),
])
def test_unify_ir0_same_type_variable_name_considered_different_from_pattern_variable(expr_variables: Set[str], pattern_variables: Set[str]):
    result = _unify((local_type_literal('T'),), (local_type_literal('T'),), expr_variables, pattern_variables)
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == (
        (local_type_literal('T'), local_type_literal('T')),
    )

@pytest.mark.parametrize('expr_variables,pattern_variables', [
    ({'T'}, set()),
    (set(), set()),
])
def test_unify_ir0_same_type_variable_name_considered_different_from_pattern_local(expr_variables: Set[str], pattern_variables: Set[str]):
    result = _unify((local_type_literal('T'),), (local_type_literal('T'),), expr_variables, pattern_variables)
    assert result.kind == UnificationResultKind.POSSIBLE

@pytest.mark.parametrize('expr1,expr2', [
    (ir0.PointerTypeExpr(type_literal('int')),
     ir0.PointerTypeExpr(type_literal('float'))),
    (ir0.ConstTypeExpr(type_literal('int')),
     ir0.ConstTypeExpr(type_literal('float'))),
    (ir0.ArrayTypeExpr(type_literal('int')),
     ir0.ArrayTypeExpr(type_literal('float'))),
    (ir0.FunctionTypeExpr(type_literal('int'), ()),
     ir0.FunctionTypeExpr(type_literal('float'), ())),
    (ir0.FunctionTypeExpr(type_literal('int'), (type_literal('float'),)),
     ir0.FunctionTypeExpr(type_literal('int'), (type_literal('double'),))),
    (ir0.FunctionTypeExpr(type_literal('int'), ()),
     ir0.FunctionTypeExpr(type_literal('int'), (type_literal('double'),))),
    (ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::vector',
                                                                                         args=(),
                                                                                         is_metafunction_that_may_return_error=False,
                                                                                         may_be_alias=False),
                               args=(),
                               instantiation_might_trigger_static_asserts=False),
     ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::list',
                                                                                         args=(),
                                                                                         is_metafunction_that_may_return_error=False,
                                                                                         may_be_alias=False),
                               args=(),
                               instantiation_might_trigger_static_asserts=False)),
    (ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::vector',
                                                                                         args=(ir0.TemplateArgType(ir0.TypeType(), is_variadic=False),),
                                                                                         is_metafunction_that_may_return_error=False,
                                                                                         may_be_alias=False),
                               args=(type_literal('int'),),
                               instantiation_might_trigger_static_asserts=False),
     ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::vector',
                                                                                         args=(ir0.TemplateArgType(ir0.TypeType(), is_variadic=False),),
                                                                                         is_metafunction_that_may_return_error=False,
                                                                                         may_be_alias=False),
                               args=(type_literal('float'),),
                               instantiation_might_trigger_static_asserts=False)),
], ids=[
    'PointerTypeExpr',
    'ConstTypeExpr',
    'ArrayTypeExpr',
    'FunctionTypeExpr, different return_type_expr',
    'FunctionTypeExpr, different arg_exprs values',
    'FunctionTypeExpr, different arg_exprs length',
    'TemplateInstantiation, different template_expr',
    'TemplateInstantiation, different args',
])
def test_unify_ir0_term_equality_fails_different_subexpressions_syntactically_comparable(expr1: ir0.Expr, expr2: ir0.Expr):
    result = _unify((expr1,), (expr2,), expr_variables=set(), pattern_variables=set())
    assert result.kind == UnificationResultKind.IMPOSSIBLE

@pytest.mark.parametrize('expr1,expr2', [
    (ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::vector',
                                                                                         args=(),
                                                                                         is_metafunction_that_may_return_error=False,
                                                                                         may_be_alias=False),
                               args=(),
                               instantiation_might_trigger_static_asserts=False),
     ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::vector',
                                                                                         args=(),
                                                                                         is_metafunction_that_may_return_error=False,
                                                                                         may_be_alias=False),
                               args=(),
                               instantiation_might_trigger_static_asserts=True)),
], ids=[
    'TemplateInstantiation, different instantiation_might_trigger_static_asserts',
])
def test_unify_ir0_term_equality_fails_different_subexpressions_syntactically_comparable_not_affecting_equality(expr1: ir0.Expr, expr2: ir0.Expr):
    result = _unify((expr1,), (expr2,), expr_variables=set(), pattern_variables=set())
    assert result.kind == UnificationResultKind.CERTAIN

@pytest.mark.parametrize('expr1,expr2', [
    (ir0.ReferenceTypeExpr(type_literal('int')),
     ir0.ReferenceTypeExpr(type_literal('float'))),
    (ir0.RvalueReferenceTypeExpr(type_literal('int')),
     ir0.RvalueReferenceTypeExpr(type_literal('float'))),
    (ir0.ComparisonExpr(literal(1), literal(2), op='=='),
     ir0.ComparisonExpr(literal(3), literal(2), op='==')),
    (ir0.ComparisonExpr(literal(1), literal(2), op='=='),
     ir0.ComparisonExpr(literal(1), literal(3), op='==')),
    (ir0.Int64BinaryOpExpr(literal(1), literal(2), op='+'),
     ir0.Int64BinaryOpExpr(literal(3), literal(2), op='+')),
    (ir0.Int64BinaryOpExpr(literal(1), literal(2), op='+'),
     ir0.Int64BinaryOpExpr(literal(1), literal(3), op='+')),
    (ir0.BoolBinaryOpExpr(literal(True), literal(True), op='&&'),
     ir0.BoolBinaryOpExpr(literal(False), literal(True), op='&&')),
    (ir0.BoolBinaryOpExpr(literal(True), literal(True), op='&&'),
     ir0.BoolBinaryOpExpr(literal(True), literal(False), op='&&')),
    (ir0.NotExpr(literal(True)),
     ir0.NotExpr(literal(False))),
    (ir0.UnaryMinusExpr(literal(1)),
     ir0.UnaryMinusExpr(literal(2))),
    (ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local('Ts', expr_type=ir0.TypeType(), is_variadic=True)),
     ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local('Us', expr_type=ir0.TypeType(), is_variadic=True))),
    (ir0.ClassMemberAccess(inner_expr=type_literal('MyClass'), member_name='value_type', expr_type=ir0.TypeType()),
     ir0.ClassMemberAccess(inner_expr=type_literal('OtherClass'), member_name='value_type', expr_type=ir0.TypeType())),
], ids=[
    'ReferenceTypeExpr',
    'RvalueReferenceTypeExpr',
    'ComparisonExpr, different lhs',
    'ComparisonExpr, different rhs',
    'Int64BinaryOpExpr, different lhs',
    'Int64BinaryOpExpr, different rhs',
    'BoolBinaryOpExpr, different lhs',
    'BoolBinaryOpExpr, different rhs',
    'NotExpr',
    'UnaryMinusExpr',
    'VariadicTypeExpansion',
    'ClassMemberAccess',
])
def test_unify_ir0_term_equality_fails_different_subexpressions_not_syntactically_comparable(expr1: ir0.Expr, expr2: ir0.Expr):
    result = _unify((expr1,), (expr2,), expr_variables=set(), pattern_variables=set())
    assert result.kind == UnificationResultKind.POSSIBLE

def test_unify_ir0_certain_nontrivial() -> None:
    result = _unify((ir0.PointerTypeExpr(type_literal('int')),),
                    (ir0.PointerTypeExpr(local_type_literal('T')),),
                    expr_variables=set(), pattern_variables={'T'})
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == (
        (local_type_literal('T'), type_literal('int')),
    )
    assert result.value_by_expanded_pattern_variable == ()

def test_unify_ir0_certain_nontrivial_multiple_equalities() -> None:
    result = _unify((ir0.PointerTypeExpr(type_literal('int')), ir0.PointerTypeExpr(type_literal('int')),),
                    (ir0.PointerTypeExpr(local_type_literal('T')), ir0.PointerTypeExpr(local_type_literal('T')),),
                    expr_variables=set(), pattern_variables={'T'})
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == (
        (local_type_literal('T'), type_literal('int')),
    )
    assert result.value_by_expanded_pattern_variable == ()

def test_unify_ir0_certain_nontrivial_with_local() -> None:
    result = _unify((ir0.PointerTypeExpr(local_type_literal('X')),),
                    (ir0.PointerTypeExpr(local_type_literal('T')),),
                    expr_variables=set(), pattern_variables={'T'})
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == (
        (local_type_literal('T'), local_type_literal('X')),
    )
    assert result.value_by_expanded_pattern_variable == ()

def test_unify_ir0_certain_nontrivial_with_local_variable() -> None:
    result = _unify((ir0.PointerTypeExpr(local_type_literal('X')),),
                    (ir0.PointerTypeExpr(local_type_literal('T')),),
                    expr_variables={'X'}, pattern_variables={'T'})
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == (
        (local_type_literal('T'), local_type_literal('X')),
    )
    assert result.value_by_expanded_pattern_variable == ()

def test_unify_ir0_certain_nontrivial_with_variadic_type_variable() -> None:
    result = _unify((ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=(type_literal('float'),
                                                                          type_literal('double'),
                                                                          local_type_literal('T'),
                                                                          type_literal('char'),
                                                                          type_literal('void'))),),
                    (ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=(type_literal('float'),
                                                                         type_literal('double'),
                                                                         ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                                                                                   expr_type=ir0.TypeType(), is_variadic=True)),
                                                                         type_literal('void'))),),
                    expr_variables={'T'}, pattern_variables={'Ts'})
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == ()
    assert result.value_by_expanded_pattern_variable == (
        (ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                   expr_type=ir0.TypeType(), is_variadic=True)),
         (local_type_literal('T'),
          type_literal('char'))),
    )

def test_unify_ir0_certain_nontrivial_with_variadic_type_variable_matches_empty_list() -> None:
    result = _unify((ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=()),),
                    (ir0.FunctionTypeExpr(type_literal('int'),
                                          arg_exprs=(ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                                                               expr_type=ir0.TypeType(),
                                                                                                               is_variadic=True)),)),),
                    expr_variables=set(), pattern_variables={'Ts'})
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == ()
    assert result.value_by_expanded_pattern_variable == (
        (ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                   expr_type=ir0.TypeType(), is_variadic=True)),
         ()),
    )

def test_unify_ir0_certain_nontrivial_with_variadic_type_variable_matches_full_nonempty_list() -> None:
    result = _unify((ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=(type_literal('float'),
                                                                          type_literal('double'))),),
                    (ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=(ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                                                                                   expr_type=ir0.TypeType(), is_variadic=True)),)),),
                    expr_variables=set(), pattern_variables={'Ts'})
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == ()
    assert result.value_by_expanded_pattern_variable == (
        (ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                   expr_type=ir0.TypeType(), is_variadic=True)),
         (type_literal('float'),
          type_literal('double'))),
    )

def test_unify_ir0_certain_nontrivial_with_variadic_type_variable_matches_empty_list_suffix() -> None:
    result = _unify((ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=(type_literal('float'),)),),
                    (ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=(type_literal('float'),
                                                                         ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                                                                                   expr_type=ir0.TypeType(), is_variadic=True)))),),
                    expr_variables=set(), pattern_variables={'Ts'})
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == ()
    assert result.value_by_expanded_pattern_variable == (
        (ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                   expr_type=ir0.TypeType(), is_variadic=True)),
         ()),
    )

def test_unify_ir0_certain_nontrivial_with_variadic_type_variable_does_not_match() -> None:
    result = _unify((ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=()),),
                    (ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=(type_literal('float'),
                                                                         ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                                                                                   expr_type=ir0.TypeType(), is_variadic=True)),)),),
                    expr_variables=set(), pattern_variables={'Ts'})
    assert result.kind == UnificationResultKind.IMPOSSIBLE

def test_unify_ir0_variadic_type_variable_matches_multiple_variadics() -> None:
    result = _unify((ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=(type_literal('float'),
                                                                          type_literal('double'),
                                                                          ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                                                                                   expr_type=ir0.TypeType(), is_variadic=True)),
                                                                          type_literal('char'),
                                                                          ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Us',
                                                                                                                                   expr_type=ir0.TypeType(), is_variadic=True)),
                                                                          type_literal('void'),)),),
                    (ir0.FunctionTypeExpr(type_literal('int'), arg_exprs=(type_literal('float'),
                                                                         type_literal('double'),
                                                                         ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Vs',
                                                                                                                                   expr_type=ir0.TypeType(), is_variadic=True)),
                                                                         type_literal('void'),)),),
                    expr_variables={'Ts', 'Us'}, pattern_variables={'Vs'})
    assert result.kind == UnificationResultKind.CERTAIN
    assert result.value_by_pattern_variable == ()
    assert result.value_by_expanded_pattern_variable == (
        (ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Vs',
                                                                   expr_type=ir0.TypeType(), is_variadic=True)),
         (ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Ts',
                                                                    expr_type=ir0.TypeType(), is_variadic=True)),
          type_literal('char'),
          ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type='Us',
                                                                    expr_type=ir0.TypeType(), is_variadic=True)))),
    )

if __name__== '__main__':
    main()
