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

@assert_compilation_fails_with_generic_error('error: static assertion failed: Something went wrong')
def test_exception_raised_and_not_caught_error():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong'
            self.b = b
            self.x = x
    def f(b: bool) -> bool:
        raise MyError(b, Type('int*'))
    assert f(True)

@assert_compilation_fails_with_generic_error('error: static assertion failed: Something went wrong')
def test_exception_raised_and_not_caught_with_branch_error():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong'
            self.b = b
            self.x = x
    def f(b: bool):
        if b:
            raise MyError(b, Type('int*'))
        return 1
    assert f(True) == 15

@assert_compilation_fails_with_generic_error('error: static assertion failed: Something went wrong')
def test_exception_raised_and_not_caught_from_another_function_error():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong'
            self.b = b
            self.x = x
    def f(b: bool) -> bool:
        raise MyError(b, Type('int*'))
    def g(b: bool) -> bool:
        return f(b)
    assert g(True)

@assert_compilation_succeeds
def test_exception_returned_ok():
    class MyError(Exception):
        def __init__(self, x: bool):
            self.message = 'Something went wrong'
            self.x = x
    def f(b: bool):
        return MyError(True)
    def g(b: bool):
        x = f(b)
        return True
    assert g(True)
