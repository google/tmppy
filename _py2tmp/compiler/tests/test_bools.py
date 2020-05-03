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

from _py2tmp.compiler.testing import main, assert_compilation_succeeds, assert_conversion_fails

@assert_compilation_succeeds()
def test_not_false():
    assert not False

@assert_compilation_succeeds()
def test_not_true():
    assert (not True) == False

@assert_compilation_succeeds()
def test_not_equal():
    assert (not True) != True

@assert_conversion_fails
def test_not_int_error():
    assert not 1  # error: The "not" operator is only supported for booleans, but this value has type int.

@assert_conversion_fails
def test_and_toplevel_error():
    assert True and True  # error: The "and" operator is only supported in functions, not at toplevel.

@assert_compilation_succeeds()
def test_and_true_true():
    def f(x: int):
        return True
    def g(x: int):
        return True
    def h(x: int):
        assert f(5) and g(5)
        return True
    assert h(3)

@assert_compilation_succeeds()
def test_and_true_false():
    def f(x: int):
        return True
    def g(x: int):
        return False
    def h(x: int):
        assert (f(5) and g(5)) == False
        return True
    assert h(3)

@assert_compilation_succeeds()
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

@assert_compilation_succeeds()
def test_and_false_false():
    def f(x: int):
        return False
    def g(x: int):
        assert False
        return False
    def h(x: int):
        assert (f(5) and g(5)) == False
        return True

@assert_conversion_fails
def test_and_bool_int_error():
    def h(x: int):
        assert (True and
                1)  # error: The "and" operator is only supported for booleans, but this value has type int.
        return True

@assert_conversion_fails
def test_and_int_bool_error():
    def h(x: int):
        assert (1  # error: The "and" operator is only supported for booleans, but this value has type int.
                and True)
        return True

@assert_conversion_fails
def test_or_toplevel_error():
    assert True or False  # error: The "or" operator is only supported in functions, not at toplevel.

@assert_compilation_succeeds()
def test_or_false_false():
    def f(x: int):
        return False
    def g(x: int):
        return False
    def h(x: int):
        assert (f(5) or g(5)) == False
        return True
    assert h(3)

@assert_compilation_succeeds()
def test_or_false_true():
    def f(x: int):
        return False
    def g(x: int):
        return True
    def h(x: int):
        assert f(5) or g(5)
        return True
    assert h(3)

@assert_compilation_succeeds()
def test_or_true_false():
    def f(x: int):
        return True
    def g(x: int):
        assert False
        return False
    def h(x: int):
        assert f(5) or g(5)
        return True
    assert h(3)

@assert_compilation_succeeds()
def test_or_true_true():
    def f(x: int):
        return True
    def g(x: int):
        assert False
        return True
    def h(x: int):
        assert f(5) or g(5)
        return True
    assert h(3)

@assert_conversion_fails
def test_or_bool_int_error():
    def h(x: int):
        assert (True or
                1)  # error: The "or" operator is only supported for booleans, but this value has type int.
        return True

@assert_conversion_fails
def test_or_int_bool_error():
    def h(x: int):
        assert (1  # error: The "or" operator is only supported for booleans, but this value has type int.
                or True)
        return True

if __name__== '__main__':
    main()
