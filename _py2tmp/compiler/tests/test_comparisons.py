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

from _py2tmp.compiler.testing import main, assert_compilation_succeeds, assert_compilation_fails_with_static_assert_error, assert_conversion_fails

@assert_compilation_succeeds()
def test_bool_equals_success():
    assert True == True, 'Assertion error'

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_bool_equals_error():
    assert True == False

@assert_compilation_succeeds()
def test_bool_not_equals_success():
    assert True == True, 'Assertion error'

@assert_conversion_fails
def test_equals_different_types():
    from tmppy import Type
    def f(x: bool, y: Type):
        return x == y  # error: Type mismatch in ==: bool vs Type

@assert_conversion_fails
def test_not_equals_different_types():
    from tmppy import Type
    def f(x: bool, y: Type):
        return x != y  # error: Type mismatch in !=: bool vs Type

@assert_conversion_fails
def test_equals_functions_error():
    def f(x: bool):
        return x
    def g(x: bool):
        return f == f  # error: Type not supported in equality comparison: \(bool\) -> bool

@assert_conversion_fails
def test_not_equals_functions_error():
    def f(x: bool):
        return x
    def g(x: bool):
        return f != f  # error: Type not supported in equality comparison: \(bool\) -> bool

@assert_compilation_succeeds()
def test_type_equals_success():
    from tmppy import Type
    assert Type('int') == Type('int')

@assert_compilation_succeeds()
def test_type_not_equal_success():
    from tmppy import Type
    assert Type('int') != Type('float')

@assert_compilation_succeeds()
def test_int_equals_success():
    assert 15 == 15

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_int_equals_error():
    assert 1 == 0

@assert_compilation_succeeds()
def test_int_not_equal_success():
    assert 15 != 3

@assert_compilation_succeeds()
def test_custom_class_equal_success():
    @dataclass
    class MyType:
        x: bool
        y: int
    assert MyType(True, 15) == MyType(True, 15)

@assert_compilation_succeeds()
def test_custom_class_first_field_not_equal_success():
    @dataclass
    class MyType:
        x: bool
        y: int
    assert MyType(True, 15) != MyType(False, 15)

@assert_compilation_succeeds()
def test_custom_class_second_field_not_equal_success():
    @dataclass
    class MyType:
        x: bool
        y: int
    assert MyType(True, 15) != MyType(True, 17)

if __name__== '__main__':
    main()
