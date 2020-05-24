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

from _py2tmp.compiler.testing import main, assert_compilation_succeeds, assert_conversion_fails, assert_compilation_fails_with_static_assert_error

@assert_conversion_fails
def test_empty_list_expression_error():
    def f(x: bool):
        return []  # error: Untyped empty lists are not supported. Please import empty_list from pytmp and then write e.g. empty_list\(int\) to create an empty list of ints.

@assert_conversion_fails
def test_empty_list_no_arguments_error():
    from tmppy import empty_list
    def f(x: bool):
        return empty_list() # error: empty_list\(\) takes 1 argument. Got: 0

@assert_conversion_fails
def test_empty_list_too_many_arguments_error():
    from tmppy import empty_list
    def f(x: bool):
        return empty_list(bool, bool) # error: empty_list\(\) takes 1 argument. Got: 2

@assert_compilation_succeeds()
def test_empty_list_success():
    from tmppy import empty_list
    assert empty_list(bool) == empty_list(bool)

@assert_conversion_fails
def test_empty_list_with_value_argument_error():
    from tmppy import empty_list
    def f(x: bool):
        return empty_list(1) # error: Unsupported type declaration.

@assert_conversion_fails
def test_empty_list_keyword_argument_error():
    from tmppy import empty_list
    def f(x: bool):
        return empty_list(bool,
                          x=x) # error: Keyword arguments are not supported.

@assert_conversion_fails
def test_list_expression_different_types_error():
    from tmppy import Type
    def f(x: bool):
        return [
            x,  # note: A previous list element with type bool was here.
            Type('int')  # error: Found different types in list elements, this is not supported. The type of this element was Type instead of bool
        ]

@assert_conversion_fails
def test_list_of_functions_error():
    def f(x: bool):
        return x
    def g(x: bool):
        return [  # error: Creating lists of functions is not supported. The elements of this list have type: \(bool\) -> bool
            f
        ]

@assert_compilation_succeeds()
def test_list_of_bools_ok():
    assert [True, False] == [True, False]

@assert_compilation_succeeds()
def test_list_of_ints_ok():
    assert [1, 2, 5] == [1, 2, 5]

@assert_compilation_succeeds()
def test_int_list_concat_ok():
    assert [1] + [2, 3] == [1, 2, 3]

@assert_compilation_succeeds()
def test_int_list_concat_lhs_empty_ok():
    from tmppy import empty_list
    assert empty_list(int) + [2, 3] == [2, 3]

@assert_compilation_succeeds()
def test_int_list_concat_rhs_empty_ok():
    from tmppy import empty_list
    assert [2, 3] + empty_list(int) == [2, 3]

@assert_compilation_succeeds()
def test_int_list_concat_both_empty_ok():
    from tmppy import empty_list
    assert empty_list(int) + empty_list(int) == empty_list(int)

@assert_compilation_succeeds()
def test_bool_list_concat_ok():
    assert [True] + [False, True] == [True, False, True]

@assert_compilation_succeeds()
def test_bool_list_concat_lhs_empty_ok():
    from tmppy import empty_list
    assert empty_list(bool) + [False, True] == [False, True]

@assert_compilation_succeeds()
def test_bool_list_concat_rhs_empty_ok():
    from tmppy import empty_list
    assert [False, True] + empty_list(bool) == [False, True]

@assert_compilation_succeeds()
def test_bool_list_concat_both_empty_ok():
    from tmppy import empty_list
    assert empty_list(bool) + empty_list(bool) == empty_list(bool)

@assert_compilation_succeeds()
def test_type_list_concat_ok():
    from tmppy import Type
    assert [Type('int')] + [Type('float'), Type('double')] == [Type('int'), Type('float'), Type('double')]

@assert_compilation_succeeds()
def test_type_list_concat_lhs_empty_ok():
    from tmppy import Type, empty_list
    assert empty_list(Type) + [Type('float'), Type('double')] == [Type('float'), Type('double')]

@assert_compilation_succeeds()
def test_type_list_concat_rhs_empty_ok():
    from tmppy import Type, empty_list
    assert [Type('float'), Type('double')] + empty_list(Type) == [Type('float'), Type('double')]

@assert_compilation_succeeds()
def test_type_list_concat_both_empty_ok():
    from tmppy import Type, empty_list
    assert empty_list(Type) + empty_list(Type) == empty_list(Type)

@assert_compilation_succeeds()
def test_custom_type_list_concat_ok():
    @dataclass
    class Int:
        n: int
    assert [Int(1)] + [Int(2), Int(3)] == [Int(1), Int(2), Int(3)]

@assert_compilation_succeeds()
def test_custom_type_list_concat_lhs_empty_ok():
    from tmppy import empty_list
    @dataclass
    class Int:
        n: int
    assert empty_list(Int) + [Int(2), Int(3)] == [Int(2), Int(3)]

@assert_compilation_succeeds()
def test_custom_type_list_concat_rhs_empty_ok():
    from tmppy import empty_list
    @dataclass
    class Int:
        n: int
    assert [Int(2), Int(3)] + empty_list(Int) == [Int(2), Int(3)]

@assert_compilation_succeeds()
def test_custom_type_list_concat_both_empty_ok():
    from tmppy import empty_list
    @dataclass
    class Int:
        n: int
    assert empty_list(Int) + empty_list(Int) == empty_list(Int)

@assert_conversion_fails
def test_int_list_concat_error():
    assert 1 + [1]  # error: Type mismatch: the LHS of "\+" has type int but the RHS has type List\[int\].

@assert_conversion_fails
def test_list_int_concat_error():
    assert [1] + 1  # error: Type mismatch: the LHS of "\+" has type List\[int\] but the RHS has type int.

@assert_compilation_succeeds()
def test_list_comprehension_bool_to_bool_ok():
    assert [not x for x in [True, False, False]] == [False, True, True]

@assert_compilation_succeeds()
def test_list_comprehension_bool_to_const_bool_ok():
    assert [True for x in [True, False, False]] == [True, True, True]

@assert_compilation_succeeds()
def test_list_comprehension_bool_to_int_ok():
    def f(b: bool):
        if b:
            return 5
        else:
            return -1
    assert [f(x) for x in [True, False]] == [5, -1]

@assert_compilation_succeeds()
def test_list_comprehension_bool_to_const_int_ok():
    def f(b: bool):
        if b:
            return 5
        else:
            return -1
    assert [1 for x in [True, False]] == [1, 1]

@assert_compilation_succeeds()
def test_list_comprehension_bool_to_type_ok():
    from tmppy import Type
    def f(b: bool):
        if b:
            return Type('int')
        else:
            return Type('float')
    assert [f(x) for x in [True, False]] == [Type('int'), Type('float')]

@assert_compilation_succeeds()
def test_list_comprehension_bool_to_const_type_ok():
    from tmppy import Type
    def f(b: bool):
        if b:
            return Type('int')
        else:
            return Type('float')
    assert [Type('int') for x in [True, False]] == [Type('int'), Type('int')]

@assert_compilation_succeeds()
def test_list_comprehension_bool_to_custom_type_ok():
    @dataclass
    class Bool:
        b: bool
    assert [Bool(x) for x in [True, False]] == [Bool(True), Bool(False)]

@assert_compilation_succeeds()
def test_list_comprehension_bool_to_const_custom_type_ok():
    @dataclass
    class Bool:
        b: bool
    assert [Bool(True) for x in [True, False]] == [Bool(True), Bool(True)]

@assert_compilation_succeeds()
def test_list_comprehension_int_to_bool_ok():
    assert [x <= 2 for x in [1, 2, 3]] == [True, True, False]

@assert_compilation_succeeds()
def test_list_comprehension_int_to_const_bool_ok():
    assert [True for x in [1, 2, 3]] == [True, True, True]

@assert_compilation_succeeds()
def test_list_comprehension_int_to_const_int_ok():
    assert [5 for x in [1, 2, 3]] == [5, 5, 5]

@assert_compilation_succeeds()
def test_list_comprehension_int_to_const_type_ok():
    from tmppy import Type
    assert [Type('float') for x in [1, -1, 0]] == [Type('float'), Type('float'), Type('float')]

@assert_compilation_succeeds()
def test_list_comprehension_int_to_custom_type_ok():
    @dataclass
    class Int:
        n: int
    assert [Int(x) for x in [1, -1, 0, 2]] == [Int(1), Int(-1), Int(0), Int(2)]

@assert_compilation_succeeds()
def test_list_comprehension_int_to_const_custom_type_ok():
    @dataclass
    class Int:
        n: int
    assert [Int(3) for x in [1, -1, 0]] == [Int(3), Int(3), Int(3)]

@assert_compilation_succeeds()
def test_list_comprehension_type_to_bool_ok():
    from tmppy import Type
    assert [x == Type('int') for x in [Type('int'), Type('float'), Type('int')]] == [True, False, True]

@assert_compilation_succeeds()
def test_list_comprehension_type_to_const_bool_ok():
    from tmppy import Type
    assert [True for x in [Type('int'), Type('float'), Type('int')]] == [True, True, True]

@assert_compilation_succeeds()
def test_list_comprehension_type_to_int_ok():
    from tmppy import Type
    def f(x: Type):
        if x == Type('int'):
            return 5
        elif x == Type('float'):
            return 7
        else:
            return -1
    assert [f(x) for x in [Type('int'), Type('float'), Type('double')]] == [5, 7, -1]

@assert_compilation_succeeds()
def test_list_comprehension_type_to_const_int_ok():
    from tmppy import Type
    assert [5 for x in [Type('int'), Type('float'), Type('double')]] == [5, 5, 5]

@assert_compilation_succeeds()
def test_list_comprehension_type_to_type_ok():
    from tmppy import Type
    def f(x: Type):
        if x == Type('int'):
            return Type.pointer(Type('int'))
        elif x == Type('float'):
            return Type.pointer(Type('float'))
        else:
            return Type('void')
    assert [f(x) for x in [Type('int'), Type('float'), Type('double')]] == [Type.pointer(Type('int')), Type.pointer(Type('float')), Type('void')]

@assert_compilation_succeeds()
def test_list_comprehension_type_to_const_type_ok():
    from tmppy import Type
    assert [Type('float') for x in [Type('int'), Type('float'), Type('double')]] == [Type('float'), Type('float'), Type('float')]

@assert_compilation_succeeds()
def test_list_comprehension_type_to_custom_type_ok():
    from tmppy import Type
    @dataclass
    class TypeWrapper:
        x: Type
    assert [TypeWrapper(x) for x in [Type('int'), Type('float'), Type('float')]] == [TypeWrapper(Type('int')), TypeWrapper(Type('float')), TypeWrapper(Type('float'))]

@assert_compilation_succeeds()
def test_list_comprehension_type_to_const_custom_type_ok():
    from tmppy import Type
    @dataclass
    class TypeWrapper:
        x: Type
    assert [TypeWrapper(Type('double')) for x in [Type('int'), Type('float'), Type('float')]] == [TypeWrapper(Type('double')), TypeWrapper(Type('double')), TypeWrapper(Type('double'))]

@assert_compilation_succeeds()
def test_list_comprehension_in_function_using_function_arg_ok():
    def f(k: int):
        return [x * k for x in [1, k, 3]]
    assert f(2) == [2, 4, 6]

@assert_compilation_succeeds()
def test_list_comprehension_in_function_using_function_variable_ok():
    def f(b: bool):
        k = 2
        return [x * k for x in [1, k, 3]]
    assert f(True) == [2, 4, 6]

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_list_comprehension_from_bool_list_throws_toplevel():
    from tmppy import empty_list
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        if b:
            raise MyError(True)
        return True
    assert [f(x) for x in [True, False, False]] == empty_list(bool)

@assert_compilation_succeeds()
def test_list_comprehension_from_bool_list_throws_in_function_caught_success():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        if b:
            raise MyError(True)
        return True
    def g(b: bool):
        try:
            return [f(x) for x in [True, False, False]]
        except MyError as e:
            return [e.b]
    assert g(True) == [True]

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_list_comprehension_from_int_list_throws_toplevel():
    from tmppy import empty_list
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(n: int):
        if n == 1:
            raise MyError(True)
        return True
    assert [f(x) for x in [0, 1, 2]] == empty_list(bool)

@assert_compilation_succeeds()
def test_list_comprehension_from_int_list_throws_in_function_caught_success():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(n: int):
        if n == 1:
            raise MyError(True)
        return True
    def g(b: bool):
        try:
            return [f(x) for x in [0, 1, 2]]
        except MyError as e:
            return [e.b]
    assert g(True) == [True]

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_list_comprehension_from_type_list_throws_toplevel():
    from tmppy import empty_list, Type
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(x: Type):
        if x == Type('float'):
            raise MyError(True)
        return True
    assert [f(x) for x in [Type('int'), Type('float'), Type('double')]] == empty_list(bool)

@assert_compilation_succeeds()
def test_list_comprehension_from_type_list_throws_in_function_caught_success():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(x: Type):
        if x == Type('float'):
            raise MyError(True)
        return True
    def g(b: bool):
        try:
            return [f(x) for x in [Type('int'), Type('float'), Type('double')]]
        except MyError as e:
            return [e.b]
    assert g(True) == [True]

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_list_comprehension_from_custom_type_list_throws_toplevel():
    from tmppy import empty_list
    @dataclass
    class Int:
        n: int
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(x: Int):
        if x == Int(1):
            raise MyError(True)
        return True
    assert [f(x) for x in [Int(0), Int(1), Int(2)]] == empty_list(bool)

@assert_compilation_succeeds()
def test_list_comprehension_from_custom_type_list_throws_in_function_caught_success():
    @dataclass
    class Int:
        n: int
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(x: Int):
        if x == Int(1):
            raise MyError(True)
        return True
    def g(b: bool):
        try:
            return [f(x) for x in [Int(0), Int(1), Int(2)]]
        except MyError as e:
            return [e.b]
    assert g(True) == [True]

@assert_conversion_fails
def test_list_comprehension_with_multiple_for_clauses_error():
    assert [y for x in [[1], [2]] for y in x]  # error: List comprehensions with multiple "for" clauses are not currently supported.

@assert_conversion_fails
def test_list_comprehension_with_if_clause_error():
    assert [x for x in [1, 2] if x != 1]  # error: "if" clauses in list comprehensions are not currently supported.

@assert_conversion_fails
def test_list_comprehension_with_unpacking_error():
    assert [x for [x, y] in [[1, 2]]]  # error: Only list comprehensions of the form \[... for var_name in ...\] are supported.

@assert_conversion_fails
def test_list_comprehension_with_non_list():
    assert [x for x in 1]  # error: The RHS of a list comprehension should be a list, but this value has type "int".

@assert_conversion_fails
def test_list_comprehension_with_non_list_var():
    def f(b: bool):
        n = 1  # note: n was defined here
        return [x for x in n]  # error: The RHS of a list comprehension should be a list, but this value has type "int".

@assert_conversion_fails
def test_list_comprehension_transforming_to_function_list_error():
    def f(b: bool):
        return b
    assert [f for x in [1, 2]]  # error: Creating lists of functions is not supported. The elements of this list have type: \(bool\) -> bool

@assert_compilation_succeeds()
def test_list_comprehension_forwarding_existing_param():
    from tmppy import Type
    def f(b: bool):
        return [Type('double') for x in [1, 2]]
    assert f(True) == [Type('double'), Type('double')]

@assert_compilation_succeeds()
def test_sum_success():
    assert sum([5, 1, 34]) == 40

@assert_compilation_succeeds()
def test_sum_empty_list_success():
    from tmppy import empty_list
    assert sum(empty_list(int)) == 0

@assert_conversion_fails
def test_sum_bool_list_error():
    assert sum([True, False]) == 40  # error: The argument of sum\(\) must have type List\[int\] or Set\[int\]. Got type: List\[bool\]

@assert_conversion_fails
def test_sum_bool_list_error_using_var():
    def f(b: bool):
        l = [True, False]  # note: l was defined here
        assert sum(l) == 40  # error: The argument of sum\(\) must have type List\[int\] or Set\[int\]. Got type: List\[bool\]

@assert_conversion_fails
def test_sum_with_keyword_argument_error():
    assert sum([True, False], start=0) == 40  # error: Keyword arguments are not supported.

@assert_conversion_fails
def test_sum_with_multiple_arguments_error():
    assert sum([True, False], 0) == 40  # error: sum\(\) takes 1 argument. Got: 2

@assert_compilation_succeeds()
def test_all_success_returns_true():
    assert all([True, True, True]) == True

@assert_compilation_succeeds()
def test_all_success_returns_false():
    assert all([True, False, True]) == False

@assert_compilation_succeeds()
def test_all_empty_list_success():
    from tmppy import empty_list
    assert all(empty_list(bool)) == True

@assert_conversion_fails
def test_all_int_list_error():
    assert all([1, 3]) == True  # error: The argument of all\(\) must have type List\[bool\] or Set\[bool\]. Got type: List\[int\]

@assert_conversion_fails
def test_all_int_list_error_using_var():
    def f(b: bool):
        l = [1, 3]  # note: l was defined here
        assert all(l) == True  # error: The argument of all\(\) must have type List\[bool\] or Set\[bool\]. Got type: List\[int\]

@assert_conversion_fails
def test_all_with_keyword_argument_error():
    assert all([True, False], x=True) == True  # error: Keyword arguments are not supported.

@assert_conversion_fails
def test_all_with_multiple_arguments_error():
    assert all([True, False], True) == True  # error: all\(\) takes 1 argument. Got: 2

@assert_compilation_succeeds()
def test_any_success_returns_false():
    assert any([False, False, False]) == False

@assert_compilation_succeeds()
def test_any_success_returns_false():
    assert any([False, True, False]) == True

@assert_compilation_succeeds()
def test_any_empty_list_success():
    from tmppy import empty_list
    assert any(empty_list(bool)) == False

@assert_conversion_fails
def test_any_int_list_error():
    assert any([1, 3]) == True  # error: The argument of any\(\) must have type List\[bool\] or Set\[bool\]. Got type: List\[int\]

@assert_conversion_fails
def test_any_int_list_error_using_var():
    def f(b: bool):
        l = [1, 3]  # note: l was defined here
        assert any(l) == True  # error: The argument of any\(\) must have type List\[bool\] or Set\[bool\]. Got type: List\[int\]

@assert_conversion_fails
def test_any_with_keyword_argument_error():
    assert any([True, False], x=True) == True  # error: Keyword arguments are not supported.

@assert_conversion_fails
def test_any_with_multiple_arguments_error():
    assert any([True, False], True) == True  # error: any\(\) takes 1 argument. Got: 2

@assert_compilation_succeeds()
def test_list_unpacking_as_tuple_success():
    def f(b: bool):
        return [10, 20, 30, 40]
    def g(b1: bool):
        a, b, c, d = f(b1)
        return b
    assert g(True) == 20

@assert_compilation_succeeds()
def test_list_unpacking_as_list_success_int():
    def f(b: bool):
        return [10, 20, 30, 40]
    def g(b1: bool):
        [a, b, c, d] = f(b1)
        return b
    assert g(True) == 20

@assert_compilation_succeeds()
def test_list_unpacking_as_list_success_bool():
    def f(b: bool):
        return [True, False, True]
    def g(b1: bool):
        [a, b, c] = f(b1)
        return b
    assert g(True) == False

@assert_compilation_succeeds()
def test_list_unpacking_as_list_success_type():
    from tmppy import Type
    def f(b: bool):
        return [Type('int'), Type('float'), Type('double')]
    def g(b1: bool):
        [a, b, c] = f(b1)
        return b
    assert g(True) == Type('float')

@assert_conversion_fails
def test_list_unpacking_as_tuple_not_a_list_error():
    def f(b: bool):
        return 10
    def g(b1: bool):
        a, b, c = f(b1)  # error: Unpacking requires a list on the RHS, but the value on the RHS has type int
        return b

@assert_conversion_fails
def test_list_unpacking_as_list_not_a_list_error():
    def f(b: bool):
        return 10
    def g(b1: bool):
        [a, b, c] = f(b1)  # error: Unpacking requires a list on the RHS, but the value on the RHS has type int
        return b

@assert_conversion_fails
def test_list_unpacking_as_tuple_multiple_levels_not_supported():
    def f(b: bool):
        return 10
    def g(b1: bool):
        a, (b, c) = f(b1)  # error: This kind of unpacking assignment is not supported. Only unpacking assignments of the form x,y=... or \[x,y\]=... are supported.
        return b

@assert_conversion_fails
def test_list_unpacking_as_list_multiple_levels_not_supported():
    def f(b: bool):
        return 10
    def g(b1: bool):
        [a, [b, c]] = f(b1)  # error: This kind of unpacking assignment is not supported. Only unpacking assignments of the form x,y=... or \[x,y\]=... are supported.
        return b

# TODO: we could report a better error message.
@assert_conversion_fails
def test_list_unpacking_as_tuple_at_toplevel_error():
    def f(b: bool):
        return [1, 2, 3]
    a, b, c = f(True)  # error: This Python construct is not supported in TMPPy

# TODO: we could report a better error message.
@assert_conversion_fails
def test_list_unpacking_as_list_at_toplevel_error():
    def f(b: bool):
        return [1, 2, 3]
    [a, b, c] = f(True)  # error: This Python construct is not supported in TMPPy

@assert_compilation_fails_with_static_assert_error('unexpected number of elements in the TMPPy list unpacking at:')
def test_list_unpacking_as_tuple_wrong_number_of_elements_error():
    def f(b: bool):
        return [10, 20, 30, 40]
    def g(b1: bool):
        a, b, c = f(b1)
        return b
    assert g(True) == 20

@assert_compilation_fails_with_static_assert_error('unexpected number of elements in the TMPPy list unpacking at:')
def test_list_unpacking_as_list_wrong_number_of_elements_error():
    def f(b: bool):
        return [10, 20, 30, 40]
    def g(b1: bool):
        [a, b, c] = f(b1)
        return b
    assert g(True) == 20

@assert_compilation_succeeds()
def test_bool_list_in_empty():
    from tmppy import empty_list
    assert not (False in empty_list(bool))

@assert_compilation_succeeds()
def test_int_list_in_empty():
    from tmppy import empty_list
    assert not (1 in empty_list(int))

@assert_compilation_succeeds()
def test_type_list_in_empty():
    from tmppy import Type, empty_list
    assert not (Type('int') in empty_list(Type))

@assert_compilation_succeeds()
def test_bool_list_in_not_present():
    assert not (False in [True])

@assert_compilation_succeeds()
def test_int_list_in_not_present():
    assert not (1 in [2])

@assert_compilation_succeeds()
def test_type_list_in_not_present():
    from tmppy import Type
    assert not (Type('int') in [Type('float')])

@assert_compilation_succeeds()
def test_bool_list_in_present():
    assert False in [False]

@assert_compilation_succeeds()
def test_int_list_in_present():
    assert 5 in [5]

@assert_compilation_succeeds()
def test_type_list_in_present():
    from tmppy import Type
    assert Type('int') in [Type('int')]

@assert_conversion_fails
def test_list_in_type_mismatch():
    def f(b: bool):
        return 1 in [True]  # error: Type mismatch in in: int vs List\[bool\]

if __name__== '__main__':
    main()
