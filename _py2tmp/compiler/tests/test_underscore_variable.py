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

from _py2tmp.compiler.testing import main, assert_compilation_succeeds

@assert_compilation_succeeds()
def test_underscore_variable_in_function():
    def f(b: bool):
        _ = 3
        return 42
    assert f(True) == 42

@assert_compilation_succeeds()
def test_underscore_variable_in_function_multiple():
    def f(b: bool):
        _ = 3
        _ = 4
        return 42
    assert f(True) == 42

@assert_compilation_succeeds()
def test_underscore_variable_in_list_unpacking():
    def f(b: bool):
        [_, x] = [1, 2]
        return x
    assert f(True) == 2

@assert_compilation_succeeds()
def test_underscore_variable_in_list_unpacking_multiple():
    def f(b: bool):
        [_, x, _] = [1, 2, 3]
        return x
    assert f(True) == 2

@assert_compilation_succeeds()
def test_underscore_variable_in_tuple_unpacking():
    def f(b: bool):
        _, x = [1, 2]
        return x
    assert f(True) == 2

@assert_compilation_succeeds()
def test_underscore_variable_in_tuple_unpacking_multiple():
    def f(b: bool):
        _, x, _ = [1, 2, 3]
        return x
    assert f(True) == 2

@assert_compilation_succeeds()
def test_ignore_return_value_of_function_that_throws():
    class MyError(Exception):
        def __init__(self, n: int):
            self.message = 'Something went wrong'
            self.n = n
    def f(b: bool):
        if True:
            raise MyError(42)
        return 1
    def g(b: bool):
        try:
            _ = f(True)
        except MyError as e:
            return 1
        return 2
    assert g(True) == 1

if __name__== '__main__':
    main()
