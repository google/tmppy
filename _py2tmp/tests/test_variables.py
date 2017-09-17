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
def test_bool_variable_success():
    def f(x: bool):
        y = x
        return y
    assert f(True) == True

@assert_compilation_succeeds
def test_type_variable_success():
    from tmppy import Type
    def f(x: Type):
        y = x
        return y
    assert f(Type('int')) == Type('int')

@assert_compilation_succeeds
def test_function_variable_success():
    from tmppy import Type
    from typing import Callable
    def f(x: Callable[[Type], Type]):
        y = x
        return y(Type('int'))
    def g(x: Type):
        return x
    assert f(g) == Type('int')

@assert_compilation_succeeds
def test_meta_meta_function_variable_success():
    from tmppy import Type
    def f1(x: Type):
        return Type('int')
    def f2(x: bool):
        return f1
    def f3(x: Type):
        return f2
    def f4(x: Type):
        return f3
    assert f4(Type('float'))(Type('int'))(True)(Type('int')) == Type('int')

@assert_conversion_fails
def test_variable_reassigned_error():
    def f(x: bool):
        y = x  # note: The previous declaration was here.
        y = x  # error: y was already defined in this scope.
        return y
