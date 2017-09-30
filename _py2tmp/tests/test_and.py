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

@assert_conversion_fails
def test_and_toplevel_error():
    assert True and True  # error: The "and" operator is only supported in functions, not at toplevel.

@assert_compilation_succeeds
def test_and_true_true():
    def f(x: int):
        return True
    def g(x: int):
        return True
    def h(x: int):
        assert f(5) and g(5)
        return True
    assert h(3)

@assert_compilation_succeeds
def test_and_true_false():
    def f(x: int):
        return True
    def g(x: int):
        return False
    def h(x: int):
        assert (f(5) and g(5)) == False
        return True
    assert h(3)

@assert_compilation_succeeds
def test_and_false_true():
    def f(x: int):
        return False
    def g(x: int):
        assert False
        return True
    def h(x: int):
        assert (f(5) and g(5)) == False
        return True
    assert h(3)

@assert_compilation_succeeds
def test_and_false_false():
    def f(x: int):
        return False
    def g(x: int):
        assert False
        return False
    def h(x: int):
        assert (f(5) and g(5)) == False
        return True
