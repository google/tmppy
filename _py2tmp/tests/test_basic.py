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
def test_identity():
    def f(x : bool):
        return x

@assert_compilation_succeeds
def test_function_call_returning_bool():
    def f(x : bool):
        return x
    def g(the_argument : bool):
        return f(f(the_argument))

@assert_compilation_succeeds
def test_function_call_returning_type():
    from tmppy import Type

    def f(x : Type):
        return x
    def g(x : Type):
        return f(f(x))

@assert_compilation_succeeds
def test_function_call_returning_list():
    from tmppy import Type
    from typing import List

    def f(x : List[Type]):
        return x
    def g(x : List[Type]):
        return f(f(x))

@assert_compilation_succeeds
def test_type_function_passed_as_argument():
    from tmppy import Type
    from typing import List
    from typing import Callable

    def f(x : Type, y : Type):
        return [x, y]
    def g(x : Callable[[Type, Type], List[Type]], y : Type):
        return x(y, y)
    def h(x : Type):
        return g(f, x)

@assert_compilation_succeeds
def test_bool_function_passed_as_argument():
    from typing import List
    from typing import Callable

    def f(x : bool, y : bool):
        return [x, y]
    def g(x : Callable[[bool, bool], List[bool]], y : bool):
        return x(y, y)
    def h(x : bool):
        return g(f, x)

@assert_compilation_succeeds
def test_bool_equals_success():
    def f(x : bool):
        assert True == True, 'The expected error'
        return x

@assert_compilation_fails_with_generic_error('The expected error')
def test_bool_equals_error():
    def f(x : bool):
        assert True == False, 'The expected error'
        return x

@assert_compilation_succeeds
def test_type_equals_success():
    from tmppy import Type

    def f(x : bool):
        assert Type('int') == Type('int'), 'The expected error'
        return x

@assert_compilation_fails_with_generic_error('The expected error')
def test_type_equals_error():
    from tmppy import Type

    def f(x : bool):
        assert Type('int') == Type('float'), 'The expected error'
        return x
