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

from _py2tmp import ir0
from _py2tmp import ir0_to_cpp
from typing import List
from _py2tmp.testing.utils import main

def type_expr_to_cpp(expr: ir0.Expr):
    writer = ir0_to_cpp.ToplevelWriter(identifier_generator=iter([]))
    ir0_to_cpp.type_expr_to_cpp(expr, enclosing_function_defn_args=[], writer=writer)
    return ''.join(writer.strings)

def literal(cpp_type: str):
    return ir0.AtomicTypeLiteral.for_nonlocal_type(cpp_type, may_be_alias=False)

def template(cpp_type: str, num_args: int):
    return ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type,
                                                       arg_types=[ir0.TypeType()] * num_args,
                                                       is_metafunction_that_may_return_error=False,
                                                       may_be_alias=False)

def pointer(expr: ir0.Expr):
    return ir0.PointerTypeExpr(expr)

def const(expr: ir0.Expr):
    return ir0.ConstTypeExpr(expr)

def fun(return_type_expr: ir0.Expr, arg_exprs: List[ir0.Expr]):
    return ir0.FunctionTypeExpr(return_type_expr, arg_exprs)

def funptr(return_type_expr: ir0.Expr, arg_exprs: List[ir0.Expr]):
    return pointer(fun(return_type_expr, arg_exprs))

def ref(expr: ir0.Expr):
    return ir0.ReferenceTypeExpr(expr)

def rref(expr: ir0.Expr):
    return ir0.RvalueReferenceTypeExpr(expr)

def array(expr: ir0.Expr):
    return ir0.ArrayTypeExpr(expr)

def tmp_instantiation(template_expr: ir0.Expr, args: List[ir0.Expr]):
    return ir0.TemplateInstantiation(template_expr, args, instantiation_might_trigger_static_asserts=False)

def type_member_access(class_expr: ir0.Expr, member_name: str):
    return ir0.ClassMemberAccess(class_type_expr=class_expr,
                                 member_name=member_name,
                                 member_type=ir0.TypeType())

def template_member_access(class_expr: ir0.Expr, member_name: str, num_args: int):
    return ir0.ClassMemberAccess(class_type_expr=class_expr,
                                 member_name=member_name,
                                 member_type=ir0.TemplateType(argtypes=[ir0.TypeType()] * num_args))

def int_member_access(class_expr: ir0.Expr, member_name: str):
    return ir0.ClassMemberAccess(class_type_expr=class_expr,
                                 member_name=member_name,
                                 member_type=ir0.Int64Type())

def bool_member_access(class_expr: ir0.Expr, member_name: str):
    return ir0.ClassMemberAccess(class_type_expr=class_expr,
                                 member_name=member_name,
                                 member_type=ir0.BoolType())

Foo = literal('Foo')
X = literal('X')
X1 = literal('X1')
X2 = literal('X2')
X3 = literal('X3')
X4 = literal('X4')
Y = literal('Y')

def test_type_expr_to_cpp_atomic_type():
    assert type_expr_to_cpp(Foo) == 'Foo'

def test_type_expr_to_cpp_pointer_type():
    expr = pointer(X)
    assert type_expr_to_cpp(expr) == 'X*'

def test_type_expr_to_cpp_const_pointer():
    expr = const(pointer(X))
    assert type_expr_to_cpp(expr) == 'X* const '

def test_type_expr_to_cpp_pointer_const():
    expr = pointer(const(X))
    assert type_expr_to_cpp(expr) == 'X const *'

def test_type_expr_to_cpp_const_pointer_const():
    expr = const(pointer(const(X)))
    assert type_expr_to_cpp(expr) == 'X const * const '

def test_type_expr_to_cpp_const_reference():
    expr = const(ref(X))
    assert type_expr_to_cpp(expr) == 'X & const '

def test_type_expr_to_cpp_reference_to_const():
    expr = ref(const(X))
    assert type_expr_to_cpp(expr) == 'X const  &'

def test_type_expr_to_cpp_const_reference_to_const():
    expr = const(ref(const(X)))
    assert type_expr_to_cpp(expr) == 'X const  & const '

def test_type_expr_to_cpp_const_rvalue_reference():
    expr = const(rref(X))
    assert type_expr_to_cpp(expr) == 'X && const '

def test_type_expr_to_cpp_rvalue_reference_to_const():
    expr = rref(const(X))
    assert type_expr_to_cpp(expr) == 'X const  &&'

def test_type_expr_to_cpp_const_rvalue_reference_to_const():
    expr = const(rref(const(X)))
    assert type_expr_to_cpp(expr) == 'X const  && const '

def test_type_expr_to_cpp_const_array():
    expr = const(array(X))
    assert type_expr_to_cpp(expr) == 'X[] const '

def test_type_expr_to_cpp_array_of_const():
    expr = array(const(X))
    assert type_expr_to_cpp(expr) == 'X const []'

def test_type_expr_to_cpp_const_array_of_const():
    expr = const(array(const(X)))
    assert type_expr_to_cpp(expr) == 'X const [] const '

def test_type_expr_to_cpp_function_type_no_args():
    expr = fun(Y, [])
    assert type_expr_to_cpp(expr) == 'Y ()'

def test_type_expr_to_cpp_function_type_one_arg():
    expr = fun(Y, [X])
    assert type_expr_to_cpp(expr) == 'Y (X)'

def test_type_expr_to_cpp_function_type_two_args():
    expr = fun(Y, [X1, X2])
    assert type_expr_to_cpp(expr) == 'Y (X1, X2)'

def test_type_expr_to_cpp_function_pointer():
    expr = pointer(fun(Y, [X1]))
    assert type_expr_to_cpp(expr) == 'Y(*) (X1)'

def test_type_expr_to_cpp_const_function_type():
    expr = const(fun(Y, [X1]))
    assert type_expr_to_cpp(expr) == 'Y( const ) (X1)'

def test_type_expr_to_cpp_function_type_reference():
    expr = ref(fun(Y, [X1]))
    assert type_expr_to_cpp(expr) == 'Y( &) (X1)'

def test_type_expr_to_cpp_function_type_rvalue_reference():
    expr = rref(fun(Y, [X1]))
    assert type_expr_to_cpp(expr) == 'Y( &&) (X1)'

def test_type_expr_to_cpp_function_type_array():
    expr = array(fun(Y, [X1]))
    assert type_expr_to_cpp(expr) == 'Y([]) (X1)'

def test_type_expr_to_cpp_function_returning_function():
    expr = funptr(funptr(funptr(funptr(Y, [X1]), [X2]), [X3]), [X4])
    assert type_expr_to_cpp(expr) == 'Y(*(*(*(*) (X4)) (X3)) (X2)) (X1)'

def test_type_expr_to_cpp_function_returning_const_function():
    expr = funptr(const(funptr(Y, [X1])), [X2])
    assert type_expr_to_cpp(expr) == 'Y(* const (*) (X2)) (X1)'

def test_type_expr_to_cpp_function_with_function_arg():
    expr = funptr(X1, [funptr(X2, [funptr(X3, [funptr(X4, [Y])])])])
    assert type_expr_to_cpp(expr) == 'X1(*) (X2(*) (X3(*) (X4(*) (Y))))'

def test_type_expr_to_cpp_function_with_const_function_arg():
    expr = funptr(X1, [const(funptr(X2, [Y]))])
    assert type_expr_to_cpp(expr) == 'X1(*) (X2(* const ) (Y))'

def test_type_expr_to_cpp_template_instantiation_no_args():
    MyTemplate = template('MyTemplate', num_args=0)
    expr = tmp_instantiation(MyTemplate, [])
    assert type_expr_to_cpp(expr) == 'MyTemplate<>'

def test_type_expr_to_cpp_template_instantiation_one_arg():
    MyTemplate = template('MyTemplate', num_args=1)
    expr = tmp_instantiation(MyTemplate, [X])
    assert type_expr_to_cpp(expr) == 'MyTemplate<X>'

def test_type_expr_to_cpp_template_instantiation_two_args():
    MyTemplate = template('MyTemplate', num_args=2)
    expr = tmp_instantiation(MyTemplate, [X1, X2])
    assert type_expr_to_cpp(expr) == 'MyTemplate<X1, X2>'

def test_type_expr_to_cpp_template_instantiation_with_function_type():
    MyTemplate = template('MyTemplate', num_args=1)
    expr = tmp_instantiation(MyTemplate, [fun(X1, [X2])])
    assert type_expr_to_cpp(expr) == 'MyTemplate<X1 (X2)>'

def test_type_expr_to_cpp_template_instantiation_as_arg_of_function_type():
    MyTemplate = template('MyTemplate', num_args=1)
    expr = fun(X1, [tmp_instantiation(MyTemplate, [X2])])
    assert type_expr_to_cpp(expr) == 'X1 (MyTemplate<X2>)'

def test_type_expr_to_cpp_template_instantiation_as_return_type_of_function_type():
    MyTemplate = template('MyTemplate', num_args=1)
    expr = fun(tmp_instantiation(MyTemplate, [X2]), [Y])
    assert type_expr_to_cpp(expr) == 'MyTemplate<X2> (Y)'

def test_type_expr_to_cpp_template_instantiation_pointer():
    MyTemplate = template('MyTemplate', num_args=2)
    expr = pointer(tmp_instantiation(MyTemplate, [X1, X2]))
    assert type_expr_to_cpp(expr) == 'MyTemplate<X1, X2>*'

def test_type_expr_to_cpp_type_member_access():
    expr = type_member_access(X, 'some_type')
    assert type_expr_to_cpp(expr) == 'typename X::some_type'

def test_type_expr_to_cpp_type_member_access_nested():
    expr = type_member_access(type_member_access(X, 'some_type'), 'other_type')
    assert type_expr_to_cpp(expr) == 'typename X::some_type::other_type'

def test_type_expr_to_cpp_template_member_access():
    expr = tmp_instantiation(template_member_access(Y, 'some_type', num_args=2),
                             [X1, X2])
    assert type_expr_to_cpp(expr) == 'typename Y::template some_type<X1, X2>'

def test_type_expr_to_cpp_member_access_on_template():
    MyTemplate = template('MyTemplate', num_args=2)
    expr = type_member_access(tmp_instantiation(MyTemplate, [X1, X2]), 'some_type')
    assert type_expr_to_cpp(expr) == 'typename MyTemplate<X1, X2>::some_type'

def test_type_expr_to_cpp_type_member_access_pointer():
    expr = pointer(type_member_access(X, 'some_type'))
    assert type_expr_to_cpp(expr) == 'typename X::some_type*'

def test_type_expr_to_cpp_int_member_access():
    expr = int_member_access(X, 'some_number')
    assert type_expr_to_cpp(expr) == 'X::some_number'

def test_type_expr_to_cpp_member_access_as_arg_of_function_type():
    expr = fun(Y, [type_member_access(X, 'some_type')])
    assert type_expr_to_cpp(expr) == 'Y (typename X::some_type)'

def test_type_expr_to_cpp_member_access_as_return_type_of_function_type():
    expr = fun(type_member_access(X, 'some_type'), [Y])
    assert type_expr_to_cpp(expr) == 'typename X::some_type (Y)'

if __name__== '__main__':
    main(__file__)
