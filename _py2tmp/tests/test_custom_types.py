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

@assert_compilation_succeeds
def test_custom_class_simple_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    assert MyType(True, 15).x

@assert_compilation_succeeds
def test_custom_class_fields_assigned_in_different_order_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.y = y
            self.x = x
    assert MyType(True, 15).x

@assert_compilation_succeeds
def test_custom_class_constructor_using_keyword_args_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    assert MyType(x=True, y=15).x

@assert_compilation_succeeds
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

@assert_compilation_succeeds
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

@assert_compilation_succeeds
def test_custom_class_variable_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    def f(b: bool):
        v = MyType(True, 15)
        return v.x
    assert f(True)

@assert_compilation_succeeds
def test_custom_class_as_function_param_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    def f(u: MyType):
        return u.x
    assert f(MyType(True, 15))

@assert_compilation_succeeds
def test_custom_class_as_function_return_value_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    def f(b: bool):
        return MyType(b, 15)
    assert f(True).x

@assert_compilation_succeeds
def test_custom_class_equal_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    assert MyType(True, 15) == MyType(True, 15)

@assert_compilation_succeeds
def test_custom_class_first_field_not_equal_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    assert MyType(True, 15) != MyType(False, 15)

@assert_compilation_succeeds
def test_custom_class_second_field_not_equal_success():
    class MyType:
        def __init__(self, x: bool, y: int):
            self.x = x
            self.y = y
    assert MyType(True, 15) != MyType(True, 17)

@assert_conversion_fails
def test_custom_class_with_same_name_as_previous_function_error():
    def X(b: bool):  # note: The previous declaration was here.
        return b
    class X:  # error: X was already defined in this scope.
        def __init__(self, x: bool):
            self.x = x

@assert_conversion_fails
def test_function_with_same_name_as_previous_custom_class_error():
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
    from tmppy import match, TypePattern
    class X:
        def __init__(self, x: bool):
            self.x = x
    def f(b: bool):
        return match(X(True))({  # error: All arguments passed to match must have type Type, but an argument with type X was specified.
            TypePattern('T'):
                lambda T: T,
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

@assert_compilation_succeeds
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
