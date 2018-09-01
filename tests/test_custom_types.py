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

from py2tmp.testing import *

@assert_compilation_succeeds()
def test_custom_class_simple_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    assert MyType(True, 15).x

@assert_compilation_succeeds()
def test_custom_class_fields_assigned_in_different_order_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.y = y
            self.x = x
    assert MyType(True, 15).x

@assert_compilation_succeeds()
def test_custom_class_constructor_using_keyword_args_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    assert MyType(x=True, y=15).x

@assert_compilation_succeeds()
def test_custom_class_constructor_using_keyword_args_fields_in_different_order_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    assert MyType(y=15, x=True).x

@assert_conversion_fails
def test_custom_class_constructor_using_mix_of_keyword_and_non_keyword_args_error():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    assert MyType(True, y=15).x  # error: Function calls with a mix of keyword and non-keyword arguments are not supported. Please choose either style.

@assert_compilation_succeeds()
def test_custom_class_used_as_function_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    def f(b: bool):
        return MyType
    def g(b: bool):
        return f(b)(True, 15).x
    assert g(False)

@assert_compilation_succeeds()
def test_custom_class_variable_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    def f(b: bool):
        v = MyType(True, 15)
        return v.x
    assert f(True)

@assert_compilation_succeeds()
def test_custom_class_as_function_param_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    def f(u: MyType):
        return u.x
    assert f(MyType(True, 15))

@assert_compilation_succeeds()
def test_custom_class_as_function_return_value_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    def f(b: bool):
        return MyType(b, 15)
    assert f(True).x

@assert_conversion_fails
def test_custom_class_with_same_name_as_previous_function_error():
    def X(b: bool):  # note: The previous declaration was here.
        return b
    class X:  # error: X was already defined in this scope.
        def __init__(self, x: bool):
            self.x = x

@assert_conversion_fails
def test_constructor_with_same_name_as_previous_custom_class_error():
    class X:  # note: The previous declaration was here.
        def __init__(self, x: bool):
            self.x = x
    def X(b: bool):  # error: X was already defined in this scope.
        return b

@assert_conversion_fails
def test_variable_with_same_name_as_previous_custom_class_error():
    class X:  # note: The previous declaration was here.
        def __init__(self, x: bool):
            self.x = x
    def f(b: bool):
        X = b  # error: X was already defined in this scope.
        return b

@assert_conversion_fails
def test_custom_type_match_error():
    from tmppy import match
    class X:
        def __init__(self, x: bool):
            self.x = x
    def f(b: bool):
        return match(X(True))(  # error: All arguments passed to match must have type Type, but an argument with type X was specified.
            lambda x: {
                x: x,
            })

@assert_conversion_fails
def test_custom_type_declared_as_return_type_before_definition_error():
    '''
    def f(b: bool) -> X:  # error: Unsupported \(or undefined\) type: X
        return True
    class X:
        def __init__(self, x: bool):
            self.x = x
    '''

@assert_conversion_fails
def test_constructor_call_wrong_number_of_arguments():
    class X:
        def __init__(self, x: bool):  # note: The definition of X.__init__ was here
            self.x = x
    def g(x: bool):
        return X(x, x)  # error: Argument number mismatch in function call to X: got 2 arguments, expected 1

@assert_conversion_fails
def test_constructor_call_wrong_argument_type():
    from tmppy import Type
    class X:
        def __init__(self,
                     x: bool):  # note: The definition of x was here
            self.x = x
    def g(
            x: Type):  # note: The definition of x was here
        return X(x)  # error: Type mismatch for argument 0: expected type bool but was: Type

@assert_conversion_fails
def test_constructor_call_wrong_argument_type_expression():
    from tmppy import Type
    class X:
        def __init__(self,
                     x: bool):  # note: The definition of x was here
            self.x = x
    def g(x: Type):
        return X([x])  # error: Type mismatch for argument 0: expected type bool but was: List\[Type\]

@assert_conversion_fails
def test_constructor_call_additional_and_missing_keyword_arguments():
    class X:
        def __init__(self,  # note: The definition of X.__init__ was here
                     foo: bool,  # note: The definition of foo was here
                     bar: bool):  # note: The definition of bar was here
            self.foo = foo
            self.bar = bar
    def g(x: bool):
        return X(fooz=x, barz=x)  # error: Incorrect arguments in call to X. Missing arguments: \{bar, foo\}. Specified arguments that don't exist: \{barz, fooz\}

@assert_conversion_fails
def test_constructor_call_additional_keyword_arguments():
    class X:
        def __init__(self, foo: bool):  # note: The definition of X.__init__ was here
            self.foo = foo
    def g(x: bool):
        return X(foo=x, bar=x, baz=x)  # error: Incorrect arguments in call to X. Specified arguments that don't exist: \{bar, baz\}

@assert_conversion_fails
def test_constructor_call_missing_keyword_arguments():
    class X:
        def __init__(self,
                     foo: bool,  # note: The definition of foo was here
                     bar: bool,
                     baz: bool):  # note: The definition of baz was here
            self.foo = foo
            self.bar = bar
            self.baz = baz
    def g(x: bool):
        return X(bar=x)  # error: Incorrect arguments in call to X. Missing arguments: \{baz, foo\}

@assert_conversion_fails
def test_constructor_call_wrong_keyword_argument_type():
    from tmppy import Type
    class X:
        def __init__(self,
                     x: bool):  # note: The definition of x was here
            self.x = x
    def g(
            x: Type):  # note: The definition of x was here
        return X(x=x)  # error: Type mismatch for argument x: expected type bool but was: Type

@assert_conversion_fails
def test_constructor_call_wrong_keyword_argument_type_expression():
    from tmppy import Type
    class X:
        def __init__(self,
                     x: bool):  # note: The definition of x was here
            self.x = x
    def g(x: Type):
        return X(x=[x])  # error: Type mismatch for argument x: expected type bool but was: List\[Type\]

@assert_compilation_succeeds()
def test_constructor_call_keyword_argument_success():
    from tmppy import Type
    from typing import List
    class X:
        def __init__(self, foo: bool, bar: Type, baz: List[bool]):
            self.foo = foo
            self.bar = bar
            self.baz = baz
    def g(x: bool):
        return X(bar=Type('int'), foo=True, baz=[x])
    assert g(True).foo == True

@assert_conversion_fails
def test_constructor_call_keyword_and_non_keyword_arguments_error():
    from tmppy import Type
    from typing import List
    class X:
        def __init__(self, foo: bool, bar: Type, baz: List[bool]):
            self.foo = foo
            self.bar = bar
            self.baz = baz
    def g(x: bool):
        return X(True, bar=Type('int'), baz=[x])  # error: Function calls with a mix of keyword and non-keyword arguments are not supported. Please choose either style.

@assert_conversion_fails
def test_custom_class_access_to_undefined_field_error():
    class MyType:  # note: MyType was defined here.
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    assert MyType(True, 15).z  # error: Values of type "MyType" don't have the attribute "z". The available attributes for this type are: \{"x", "y"\}.

@assert_conversion_fails
def test_custom_class_with_base_class_error():
    class MyType(
        int):  # error: "Exception" is the only supported base class.
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y

@assert_conversion_fails
def test_custom_class_with_keyword_class_arguments_error():
    class MyType(x=1):  # error: Keyword class arguments are not supported.
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y

@assert_conversion_fails
def test_custom_class_with_decorator_error():
    @staticmethod  # error: Class decorators are not supported.
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y

@assert_conversion_fails
def test_custom_class_with_no_init_error():
    class MyType:  # error: Custom classes must contain an __init__ method \(and nothing else\).
        pass

@assert_conversion_fails
def test_custom_class_with_no_init_with_other_method_error():
    class MyType:  # error: Custom classes must contain an __init__ method \(and nothing else\).
        def f(self):
            return True

@assert_conversion_fails
def test_custom_class_with_no_init_with_class_constant_error():
    class MyType:  # error: Custom classes must contain an __init__ method \(and nothing else\).
        x = 1

@assert_conversion_fails
def test_custom_class_without_self_param_in_init_and_no_other_params_error():
    '''
    class MyType:
        def __init__():  # error: Expected "self" as first argument of __init__.
            pass
    '''

@assert_conversion_fails
def test_custom_class_without_self_param_in_init_error():
    class MyType:
        def __init__(  # error: Expected "self" as first argument of __init__.
                x: bool):
            pass

@assert_conversion_fails
def test_custom_class_with_type_annotation_on_self_param_error():
    class MyType:
        def __init__(
                self: int,  # error: Type annotations on the "self" argument are not supported.
                x: bool):
            pass

@assert_conversion_fails
def test_custom_class_with_vararg_in_init():
    class MyType:
        def __init__(self,
                     *x: bool):  # error: Vararg arguments are not supported in __init__.
            self.x = x

@assert_conversion_fails
def test_custom_type_multiple_parameters_with_same_name_error():
    '''
    class MyType:
        def __init__(self,
                     x: bool,  # note: A previous argument with name "x" was declared here.
                     x: bool):  # error: Found multiple arguments with name "x".
            pass
    '''

@assert_conversion_fails
def test_constructor_argument_with_type_comment_error():
    class MyType:
        def __init__(self,
                     x  # type: bool  # error: Type comments on arguments are not supported.
          ):
            pass

@assert_conversion_fails
def test_constructor_argument_with_no_type_annotation_error():
    class MyType:
        def __init__(self,
                     x):  # error: All arguments of __init__ \(except "self"\) must have a type annotation.
            pass

@assert_conversion_fails
def test_constructor_no_arguments_error():
    class MyType:
        def __init__(self):  # error: Custom types must have at least 1 constructor argument \(and field\).
            pass

@assert_conversion_fails
def test_constructor_varargs_error():
    class MyType:
        def __init__(self, x: bool,
                     *args):  # error: Vararg arguments are not supported in __init__.
            pass

@assert_conversion_fails
def test_constructor_kwargs_error():
    class MyType:
        def __init__(self, x: bool, **kwargs):  # error: Keyword arguments are not supported in __init__.
            pass

@assert_conversion_fails
def test_constructor_keyword_only_args_error():
    class MyType:
        def __init__(self, x: bool, *,
                     y: bool):  # error: Keyword-only arguments are not supported in __init__.
            pass

@assert_conversion_fails
def test_constructor_default_argument_error():
    class MyType:
        def __init__(self, x: bool = True):  # error: Default arguments are not supported in __init__.
            pass

@assert_conversion_fails
def test_custom_type_unexpected_statement():
    class MyType:
        def __init__(self, x: bool):
            self.x = x
            y = 1  # error: Unexpected statement. All statements in __init__ methods must be of the form "self.some_var = some_var".

@assert_conversion_fails
def test_custom_type_multiple_assignments_for_field_error():
    class MyType:
        def __init__(self, x: bool):
            self.x = x  # note: A previous assignment to "self.x" was here.
            self.x = x  # error: Found multiple assignments to the field "x".

@assert_conversion_fails
def test_custom_type_missing_assignment_for_field_error():
    class MyType:
        def __init__(self, x: bool,
                     y: bool):  # error: All __init__ arguments must be assigned to fields, but "y" was never assigned.
            self.x = x

@assert_conversion_fails
def test_custom_type_argument_assigned_to_field_with_different_name_error():
    class MyType:
        def __init__(self, x: bool, y: bool):
            self.x = y  # error: __init__ arguments must be assigned to a field of the same name, but "y" was assigned to "x".

@assert_conversion_fails
def test_custom_type_non_argument_assigned_to_field_error():
    def f(b: bool):
        return b
    class MyType:
        def __init__(self, y: bool):
            self.f = f  # error: Unsupported assignment. All assigments in __init__ methods must assign a parameter to a field with the same name.
