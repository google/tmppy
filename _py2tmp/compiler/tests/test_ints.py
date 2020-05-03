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
def test_int_success():
    assert 15 == 15

@assert_conversion_fails
def test_float_constant_error():
    def f(x: bool):
        return 15.0  # error: Floating-point values are not supported.

@assert_conversion_fails
def test_complex_constant_error():
    def f(x: bool):
        return 15j  # error: Complex values are not supported.

@assert_compilation_succeeds()
def test_int_max_success():
    def f(x: bool):
        return 9223372036854775807

@assert_conversion_fails
def test_int_max_plus_one_error():
    def f(x: bool):
        return 9223372036854775808  # error: int value out of bounds: values greater than 2\^63-1 are not supported.

@assert_compilation_succeeds()
def test_int_min_success():
    def f(x: bool):
        return -9223372036854775807

@assert_conversion_fails
def test_int_min_minus_one_error():
    def f(x: bool):
        return -9223372036854775808  # error: int value out of bounds: values lower than -2\^63\+1 are not supported.

@assert_compilation_succeeds()
def test_int_unary_minus_success():
    def f(x: int):
        return -x
    assert f(3) == -3
    assert f(f(3)) == 3

@assert_conversion_fails
def test_bool_unary_minus_error():
    def f(x: bool):
        return -x  # error: The "-" operator is only supported for ints, but this value has type bool.

@assert_compilation_succeeds()
def test_int_plus_success():
    assert 2 + 3 == 5

@assert_conversion_fails
def test_int_plus_bool_error():
    assert (2 +
            True  # error: The "\+" operator is only supported for ints and lists, but this value has type bool.
            == 5)

@assert_conversion_fails
def test_bool_plus_int_error():
    assert (True  # error: The "\+" operator is only supported for ints and lists, but this value has type bool.
            + 2 == 5)

@assert_compilation_succeeds()
def test_int_minus_success():
    assert 2 - 3 == -1

@assert_conversion_fails
def test_int_minus_bool_error():
    assert (2 -
            True  # error: The "-" operator is only supported for ints, but this value has type bool.
            == 5)

@assert_conversion_fails
def test_bool_minus_int_error():
    assert (True  # error: The "-" operator is only supported for ints, but this value has type bool.
            - 2 == 5)

@assert_compilation_succeeds()
def test_int_multiplication_success():
    assert 2 * 3 == 6

@assert_conversion_fails
def test_int_bool_multiplication_error():
    assert (2 *
            True   # error: The "\*" operator is only supported for ints, but this value has type bool.
            == 5)

@assert_conversion_fails
def test_bool_int_multiplication_error():
    assert (True   # error: The "\*" operator is only supported for ints, but this value has type bool.
            * 2 == 5)

@assert_compilation_succeeds()
def test_int_division_success():
    assert 7 // 3 == 2

@assert_conversion_fails
def test_int_bool_division_error():
    assert (2 //
            True  # error: The "//" operator is only supported for ints, but this value has type bool.
            == 5)

@assert_conversion_fails
def test_bool_int_division_error():
    assert (True  # error: The "//" operator is only supported for ints, but this value has type bool.
            // 2 == 5)

@assert_compilation_succeeds()
def test_int_modulus_success():
    assert 7 % 3 == 1

@assert_conversion_fails
def test_int_bool_modulus_error():
    assert (2 %
            True  # error: The "%" operator is only supported for ints, but this value has type bool.
            == 5)

@assert_conversion_fails
def test_bool_int_modulus_error():
    assert (True  # error: The "%" operator is only supported for ints, but this value has type bool.
            % 2 == 5)

@assert_compilation_succeeds()
def test_int_equals_when_less_than():
    assert not 1 == 3

@assert_compilation_succeeds()
def test_int_equals_when_equal():
    assert 1 == 1

@assert_compilation_succeeds()
def test_int_equals_when_greater_than():
    assert not 3 == 1

@assert_compilation_succeeds()
def test_int_not_equals_when_less_than():
    assert 1 != 3

@assert_compilation_succeeds()
def test_int_not_equals_when_equal():
    assert not 1 != 1

@assert_compilation_succeeds()
def test_int_not_equals_when_greater_than():
    assert 3 != 1

@assert_compilation_succeeds()
def test_int_less_than_when_less_than():
    assert 1 < 3

@assert_compilation_succeeds()
def test_int_less_than_when_equal():
    assert not 1 < 1

@assert_compilation_succeeds()
def test_int_less_than_when_greater_than():
    assert not 3 < 1

@assert_conversion_fails
def test_int_less_than_bool_error():
    assert (1 <
            True)  # error: The "<" operator is only supported for ints, but this value has type bool.

@assert_conversion_fails
def test_bool_less_than_int_error():
    assert (True  # error: The "<" operator is only supported for ints, but this value has type bool.
            < 1)

@assert_compilation_succeeds()
def test_int_greater_than_when_less_than():
    assert not 1 > 3

@assert_compilation_succeeds()
def test_int_greater_than_when_equal():
    assert not 1 > 1

@assert_compilation_succeeds()
def test_int_greater_than_when_greater_than():
    assert 3 > 1

@assert_conversion_fails
def test_int_greater_than_bool_error():
    assert (1 >
            True)  # error: The ">" operator is only supported for ints, but this value has type bool.

@assert_conversion_fails
def test_bool_greater_than_int_error():
    assert (True  # error: The ">" operator is only supported for ints, but this value has type bool.
            > 1)

@assert_compilation_succeeds()
def test_int_less_than_or_equal_to_when_less_than():
    assert 1 <= 3

@assert_compilation_succeeds()
def test_int_less_than_or_equal_to_when_equal():
    assert 1 <= 1

@assert_compilation_succeeds()
def test_int_less_than_or_equal_to_when_greater_than():
    assert not 3 <= 1

@assert_conversion_fails
def test_int_less_than_or_equal_to_bool_error():
    assert (1 <=
            True)  # error: The "<=" operator is only supported for ints, but this value has type bool.

@assert_conversion_fails
def test_bool_less_than_or_equal_to_int_error():
    assert (True  # error: The "<=" operator is only supported for ints, but this value has type bool.
            <= 1)

@assert_compilation_succeeds()
def test_int_greater_than_or_equal_to_when_less_than():
    assert not 1 >= 3

@assert_compilation_succeeds()
def test_int_greater_than_or_equal_to_when_equal():
    assert 1 >= 1

@assert_compilation_succeeds()
def test_int_greater_than_or_equal_to_when_greater_than():
    assert 3 >= 1

@assert_conversion_fails
def test_int_greater_than_or_equal_to_bool_error():
    assert (1 >=
            True)  # error: The ">=" operator is only supported for ints, but this value has type bool.

@assert_conversion_fails
def test_bool_greater_than_or_equal_to_int_error():
    assert (True  # error: The ">=" operator is only supported for ints, but this value has type bool.
            >= 1)

if __name__== '__main__':
    main()
