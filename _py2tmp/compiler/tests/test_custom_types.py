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
from dataclasses import dataclass

from _py2tmp.compiler.testing import main, assert_compilation_succeeds, assert_conversion_fails

@assert_compilation_succeeds()
def test_custom_class_simple_success():
    from dataclasses import dataclass
    @dataclass
    class MyType:
        x: bool
        y: int
    assert MyType(True, 15).x

@assert_compilation_succeeds()
def test_custom_class_constructor_using_keyword_args_success():
    @dataclass
    class MyType:
        x: bool
        y: int
    assert MyType(x=True, y=15).x

@assert_compilation_succeeds()
def test_custom_class_constructor_using_keyword_args_fields_in_different_order_success():
    @dataclass
    class MyType:
        x: bool
        y: int
    assert MyType(y=15, x=True).x

@assert_conversion_fails
def test_custom_class_constructor_using_mix_of_keyword_and_non_keyword_args_error():
    @dataclass
    class MyType:
        x: bool
        y: int
    assert MyType(True, y=15).x  # error: Function calls with a mix of keyword and non-keyword arguments are not supported. Please choose either style.

@assert_compilation_succeeds()
def test_custom_class_used_as_function_success():
    @dataclass
    class MyType:
        x: bool
        y: int
    def f(b: bool):
        return MyType
    def g(b: bool):
        return f(b)(True, 15).x
    assert g(False)

@assert_compilation_succeeds()
def test_custom_class_variable_success():
    @dataclass
    class MyType:
        x: bool
        y: int
    def f(b: bool):
        v = MyType(True, 15)
        return v.x
    assert f(True)

@assert_compilation_succeeds()
def test_custom_class_as_function_param_success():
    @dataclass
    class MyType:
        x: bool
        y: int
    def f(u: MyType):
        return u.x
    assert f(MyType(True, 15))

@assert_compilation_succeeds()
def test_custom_class_as_function_return_value_success():
    @dataclass
    class MyType:
        x: bool
        y: int
    def f(b: bool):
        return MyType(b, 15)
    assert f(True).x

@assert_conversion_fails
def test_custom_class_with_same_name_as_previous_function_error():
    def X(b: bool):  # note: The previous declaration was here.
        return b
    @dataclass
    class X:  # error: X was already defined in this scope.
        x: bool

@assert_conversion_fails
def test_constructor_with_same_name_as_previous_custom_class_error():
    @dataclass
    class X:  # note: The previous declaration was here.
        x: bool
    def X(b: bool):  # error: X was already defined in this scope.
        return b

@assert_conversion_fails
def test_variable_with_same_name_as_previous_custom_class_error():
    @dataclass
    class X:  # note: The previous declaration was here.
        x: bool
    def f(b: bool):
        X = b  # error: X was already defined in this scope.
        return b

@assert_conversion_fails
def test_custom_type_match_error():
    from tmppy import match
    @dataclass
    class X:
        x: bool
    def f(b: bool):
        return match(X(True))(  # error: All arguments passed to match must have type Type, but an argument with type X was specified.
            lambda x: {
                x: x,
            })

@assert_conversion_fails
def test_custom_type_declared_as_return_type_before_definition_error():
    '''
    def f(b: bool) -> X:  # error: Unsupported \\(or undefined\\) type: X
        return True
    @dataclass
    class X:
        x: bool
    '''

@assert_conversion_fails
def test_constructor_call_wrong_number_of_arguments():
    @dataclass
    class X:  # note: The definition of X was here
        x: bool
    def g(x: bool):
        return X(x, x)  # error: Argument number mismatch in function call to X: got 2 arguments, expected 1

@assert_conversion_fails
def test_constructor_call_wrong_argument_type():
    from tmppy import Type
    @dataclass
    class X:  # note: The definition of X was here
        x: bool
    def g(
            x: Type):  # note: The definition of x was here
        return X(x)  # error: Type mismatch for argument 0: expected type bool but was: Type

@assert_conversion_fails
def test_constructor_call_wrong_argument_type_expression():
    from tmppy import Type
    @dataclass
    class X:  # note: The definition of X was here
        x: bool
    def g(x: Type):
        return X([x])  # error: Type mismatch for argument 0: expected type bool but was: List\[Type\]

@assert_conversion_fails
def test_constructor_call_additional_and_missing_keyword_arguments():
    @dataclass
    class X:  # note: The definition of X was here
        foo: bool
        bar: bool
    def g(x: bool):
        return X(fooz=x, barz=x)  # error: Incorrect arguments in call to X. Missing arguments: \{bar, foo\}. Specified arguments that don't exist: \{barz, fooz\}

@assert_conversion_fails
def test_constructor_call_additional_keyword_arguments():
    @dataclass
    class X:  # note: The definition of X was here
        foo: bool
    def g(x: bool):
        return X(foo=x, bar=x, baz=x)  # error: Incorrect arguments in call to X. Specified arguments that don't exist: \{bar, baz\}

@assert_conversion_fails
def test_constructor_call_missing_keyword_arguments():
    @dataclass
    class X:  # note: The definition of X was here
        foo: bool
        bar: bool
        baz: bool
    def g(x: bool):
        return X(bar=x)  # error: Incorrect arguments in call to X. Missing arguments: \{baz, foo\}

@assert_conversion_fails
def test_constructor_call_wrong_keyword_argument_type():
    from tmppy import Type
    @dataclass
    class X:  # note: The definition of X was here
        x: bool
    def g(
            x: Type):  # note: The definition of x was here
        return X(x=x)  # error: Type mismatch for argument x: expected type bool but was: Type

@assert_conversion_fails
def test_constructor_call_wrong_keyword_argument_type_expression():
    from tmppy import Type
    @dataclass
    class X:  # note: The definition of X was here
        x: bool
    def g(x: Type):
        return X(x=[x])  # error: Type mismatch for argument x: expected type bool but was: List\[Type\]

@assert_compilation_succeeds()
def test_constructor_call_keyword_argument_success():
    from tmppy import Type
    from typing import List
    @dataclass
    class X:
        foo: bool
        bar: Type
        baz: List[bool]
    def g(x: bool):
        return X(bar=Type('int'), foo=True, baz=[x])
    assert g(True).foo == True

@assert_conversion_fails
def test_constructor_call_keyword_and_non_keyword_arguments_error():
    from tmppy import Type
    from typing import List
    @dataclass
    class X:
        foo: bool
        bar: Type
        baz: List[bool]
    def g(x: bool):
        return X(True, bar=Type('int'), baz=[x])  # error: Function calls with a mix of keyword and non-keyword arguments are not supported. Please choose either style.

@assert_conversion_fails
def test_custom_class_access_to_undefined_field_error():
    @dataclass
    class MyType:  # note: MyType was defined here.
        x: bool
        y: int
    assert MyType(True, 15).z  # error: Values of type "MyType" don't have the attribute "z". The available attributes for this type are: \{"x", "y"\}.

@assert_conversion_fails
def test_custom_class_with_base_class_error():
    @dataclass
    class MyType(
        int):  # error: "Exception" is the only supported base class.
        x: bool
        y: int

@assert_conversion_fails
def test_custom_class_with_keyword_class_arguments_error():
    @dataclass
    class MyType(x=1):  # error: Keyword class arguments are not supported.
        x: bool

@assert_conversion_fails
def test_custom_class_with_decorator_error():
    @staticmethod  # error: "@dataclass" is the only supported class decorator.
    class MyType:
        x: bool
        y: int

@assert_conversion_fails
def test_custom_class_with_no_dataclass_annotation_error():
    class MyType:  # error: Custom classes must either inherit from Exception or be decorated with @dataclass.
        pass

@assert_conversion_fails
def test_custom_class_with_method_error():
    @dataclass
    class MyType:
        def f(self):  # error: Dataclasses can contain only typed field assignments \(and no other statements\).
            return True

@assert_conversion_fails
def test_custom_type_multiple_parameters_with_same_name_error():
    '''
    @dataclass
    class MyType:
        x: bool  # note: A previous field with name "x" was declared here.
        x: bool  # error: Found multiple dataclass fields with name "x".
    '''

@assert_conversion_fails
def test_field_with_no_type_annotation_error():
    @dataclass
    class MyType:
        x = 0  # error: Dataclasses can contain only typed field assignments \(and no other statements\).

@assert_conversion_fails
def test_custom_type_with_no_fields_error():
    @dataclass
    class MyType:
        pass  # error: Dataclasses can contain only typed field assignments \(and no other statements\).

@assert_conversion_fails
def test_custom_type_default_argument_error():
    @dataclass
    class MyType:
        x: bool = True  # error: Dataclass field defaults are not supported.

if __name__== '__main__':
    main()
