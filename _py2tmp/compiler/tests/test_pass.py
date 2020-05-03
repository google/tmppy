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
def test_pass_toplevel():
    pass

@assert_compilation_succeeds()
def test_pass_in_function_body():
    def f(n: int):
        pass
        return n
    assert f(42) == 42

@assert_compilation_succeeds()
def test_pass_in_if_with_other_stmts():
    def f(n: int):
        if True:
            pass
            return n
        else:
            return 3
    assert f(42) == 42

@assert_compilation_succeeds()
def test_pass_in_if_alone():
    def f(n: int):
        if True:
            pass
        else:
            return 3
        return n
    assert f(42) == 42

@assert_compilation_succeeds()
def test_pass_in_else_with_other_stmts():
    def f(n: int):
        if False:
            return 3
        else:
            pass
            return n
    assert f(42) == 42

@assert_compilation_succeeds()
def test_pass_in_else_alone():
    def f(n: int):
        if False:
            return 3
        else:
            pass
        return n
    assert f(42) == 42

@assert_compilation_succeeds()
def test_pass_in_try_with_other_stmts():
    class MyError(Exception):
        def __init__(self, n: int):
            self.message = 'Something happened'
            self.n = n
    def f(n: int):
        try:
            pass
            if n == 42:
                raise MyError(42)
        except MyError as e:
            return 3
        return 4
    assert f(42) == 3

@assert_compilation_succeeds()
def test_pass_in_try_alone():
    class MyError(Exception):
        def __init__(self, n: int):
            self.message = 'Something happened'
            self.n = n
    def f(n: int):
        try:
            pass
        except MyError as e:
            return 1
        return 2
    assert f(42) == 2

@assert_compilation_succeeds()
def test_pass_in_except_with_other_stmts():
    class MyError(Exception):
        def __init__(self, n: int):
            self.message = 'Something happened'
            self.n = n
    def f(n: int):
        try:
            if n == 42:
                raise MyError(42)
        except MyError as e:
            pass
            return 3
        return 4
    assert f(42) == 3

@assert_compilation_succeeds()
def test_pass_in_except_alone():
    class MyError(Exception):
        def __init__(self, n: int):
            self.message = 'Something happened'
            self.n = n
    def f(n: int):
        try:
            raise MyError(42)
        except MyError as e:
            pass
        return 4
    assert f(42) == 4

if __name__== '__main__':
    main()
