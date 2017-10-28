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
def test_type_literal_success():
    from tmppy import Type
    assert Type('int') == Type('int')

@assert_compilation_succeeds
def test_type_pointer_literal_success():
    from tmppy import Type
    assert Type('T*', T=Type('int')) == Type('int*')

@assert_compilation_succeeds
def test_type_reference_literal_success():
    from tmppy import Type
    assert Type('T&', T=Type('int')) == Type('int&')

@assert_compilation_succeeds
def test_type_rvalue_reference_literal_success():
    from tmppy import Type
    assert Type('T&&', T=Type('int')) == Type('int&&')

@assert_compilation_succeeds
def test_const_type_literal_success():
    from tmppy import Type
    assert Type('const T', T=Type('int')) == Type('const int')

@assert_compilation_succeeds
def test_type_array_literal_success():
    from tmppy import Type
    assert Type('T[]', T=Type('int')) == Type('int[]')

@assert_compilation_succeeds
def test_type_function_literal_with_no_args_success():
    from tmppy import Type
    assert Type('T()', T=Type('int')) == Type('int()')

@assert_compilation_succeeds
def test_type_function_pointer_literal_with_no_args_success():
    from tmppy import Type
    assert Type('T(*)()', T=Type('int')) == Type('int(*)()')

@assert_compilation_succeeds
def test_type_function_literal_success():
    from tmppy import Type
    assert Type('T(U, V)', T=Type('int'), U=Type('float'), V=Type('double')) == Type('int(float, double)')

@assert_compilation_succeeds
def test_type_function_pointer_literal_success():
    from tmppy import Type
    assert Type('T(*)(U, V)', T=Type('int'), U=Type('float'), V=Type('double')) == Type('int(*)(float, double)')

@assert_conversion_fails
def test_type_literal_no_arguments_error():
    from tmppy import Type
    def f(x: bool):
        return Type()  # error: Type\(\) takes 1 argument. Got: 0

@assert_conversion_fails
def test_type_literal_too_many_arguments_error():
    from tmppy import Type
    def f(x: bool):
        return Type('', '')  # error: Type\(\) takes 1 argument. Got: 2

@assert_conversion_fails
def test_type_literal_argument_with_wrong_type_error():
    from tmppy import Type
    def f(x: bool):
        return Type(x)  # error: The first argument to Type should be a string constant.

@assert_conversion_fails
def test_type_literal_kwargs_arg_not_supported():
    from tmppy import Type
    def f(x: bool):
        y = 1
        return Type(**y)  # error: \*\*kwargs arguments are not supported \(only explicit keyword arguments are\).

@assert_conversion_fails
def test_type_literal_string_arg_error():
    from tmppy import Type
    def f(x: bool):
        return Type('T', T='int')  # error: This kind of expression is not supported.

@assert_conversion_fails
def test_type_literal_int_arg_error():
    from tmppy import Type
    def f(x: bool):
        return Type('T', T=13)  # error: Type mismatch for argument T: expected type Type but was: int

@assert_conversion_fails
def test_type_literal_bool_var_arg_error():
    from tmppy import Type
    def f(x: bool):  # note: The definition of x was here
        return Type('T', T=x)  # error: Type mismatch for argument T: expected type Type but was: bool
