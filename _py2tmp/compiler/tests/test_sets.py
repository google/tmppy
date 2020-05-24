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
def test_empty_set_no_arguments_error():
    from tmppy import empty_set
    def f(x: bool):
        return empty_set() # error: empty_set\(\) takes 1 argument. Got: 0

@assert_conversion_fails
def test_empty_set_too_many_arguments_error():
    from tmppy import empty_set
    def f(x: bool):
        return empty_set(bool, bool) # error: empty_set\(\) takes 1 argument. Got: 2

@assert_compilation_succeeds()
def test_empty_set_success():
    from tmppy import empty_set
    assert empty_set(bool) == empty_set(bool)

@assert_conversion_fails
def test_empty_set_with_value_argument_error():
    from tmppy import empty_set
    def f(x: bool):
        return empty_set(1) # error: Unsupported type declaration.

@assert_conversion_fails
def test_empty_set_keyword_argument_error():
    from tmppy import empty_set
    def f(x: bool):
        return empty_set(bool,
                          x=x) # error: Keyword arguments are not supported.

@assert_conversion_fails
def test_set_expression_different_types_error():
    from tmppy import Type
    def f(x: bool):
        return {
            x,  # note: A previous set element with type bool was here.
            Type('int')  # error: Found different types in set elements, this is not supported. The type of this element was Type instead of bool
        }

@assert_conversion_fails
def test_set_of_functions_error():
    def f(x: bool):
        return x
    def g(x: bool):
        return {  # error: Creating sets of functions is not supported. The elements of this set have type: \(bool\) -> bool
            f
        }

@assert_compilation_succeeds()
def test_set_of_bools_ok():
    assert {True, False} == {True, False}

@assert_compilation_succeeds()
def test_set_of_bools_with_duplicates_ok():
    assert {True, False, True} == {True, False}

@assert_compilation_succeeds()
def test_set_of_bools_with_different_order_equal():
    assert {True, False} == {False, True}

@assert_compilation_succeeds()
def test_set_of_ints_ok():
    assert {1, 2, 5} == {1, 2, 5}

@assert_compilation_succeeds()
def test_set_of_ints_with_duplicates_ok():
    assert {1, 5, 2, 5} == {1, 2, 5}

@assert_compilation_succeeds()
def test_set_of_ints_with_different_order_equal():
    assert {1, 2, 3} == {3, 2, 1}

@assert_conversion_fails
def test_set_concat_not_supported_error():
    assert {1} + {2, 3} == {1, 2, 3}  # error: The "\+" operator is only supported for ints and lists, but this value has type Set\[int\].

@assert_compilation_succeeds()
def test_set_comprehension_bool_to_bool_ok():
    assert {not x for x in {True, False}} == {True, False}

@assert_compilation_succeeds()
def test_set_comprehension_bool_to_const_bool_ok():
    assert {True for x in {True, False}} == {True}

@assert_compilation_succeeds()
def test_set_comprehension_bool_to_int_ok():
    def f(b: bool):
        if b:
            return 5
        else:
            return -1
    assert {f(x) for x in {True, False}} == {5, -1}

@assert_compilation_succeeds()
def test_set_comprehension_bool_to_const_int_ok():
    def f(b: bool):
        if b:
            return 5
        else:
            return -1
    assert {1 for x in {True, False}} == {1}

@assert_compilation_succeeds()
def test_set_comprehension_bool_to_type_ok():
    from tmppy import Type
    def f(b: bool):
        if b:
            return Type('int')
        else:
            return Type('float')
    assert {f(x) for x in {True, False}} == {Type('int'), Type('float')}

@assert_compilation_succeeds()
def test_set_comprehension_bool_to_const_type_ok():
    from tmppy import Type
    def f(b: bool):
        if b:
            return Type('int')
        else:
            return Type('float')
    assert {Type('int') for x in {True, False}} == {Type('int')}

@assert_compilation_succeeds()
def test_set_comprehension_bool_to_custom_type_ok():
    @dataclass
    class Bool:
        b: bool
    assert {Bool(x) for x in {True, False}} == {Bool(True), Bool(False)}

@assert_compilation_succeeds()
def test_set_comprehension_bool_to_const_custom_type_ok():
    @dataclass
    class Bool:
        b: bool
    assert {Bool(True) for x in {True, False}} == {Bool(True)}

@assert_compilation_succeeds()
def test_set_comprehension_int_to_bool_ok():
    assert {x <= 2 for x in {1, 2, 3}} == {True, False}

@assert_compilation_succeeds()
def test_set_comprehension_int_to_const_bool_ok():
    assert {True for x in {1, 2, 3}} == {True}

@assert_compilation_succeeds()
def test_set_comprehension_int_to_const_int_ok():
    assert {5 for x in {1, 2, 3}} == {5}

@assert_compilation_succeeds()
def test_set_comprehension_int_to_const_type_ok():
    from tmppy import Type
    assert {Type('float') for x in {1, -1, 0}} == {Type('float')}

@assert_compilation_succeeds()
def test_set_comprehension_int_to_custom_type_ok():
    @dataclass
    class Int:
        n: int
    assert {Int(x) for x in {1, -1, 0, 2}} == {Int(1), Int(-1), Int(0), Int(2)}

@assert_compilation_succeeds()
def test_set_comprehension_int_to_const_custom_type_ok():
    @dataclass
    class Int:
        n: int
    assert {Int(3) for x in {1, -1, 0}} == {Int(3)}

@assert_compilation_succeeds()
def test_set_comprehension_type_to_bool_ok():
    from tmppy import Type
    assert {x == Type('int') for x in {Type('int'), Type('float')}} == {True, False}

@assert_compilation_succeeds()
def test_set_comprehension_type_to_const_bool_ok():
    from tmppy import Type
    assert {True for x in {Type('int'), Type('float'), Type('int')}} == {True}

@assert_compilation_succeeds()
def test_set_comprehension_type_to_int_ok():
    from tmppy import Type
    def f(x: Type):
        if x == Type('int'):
            return 5
        elif x == Type('float'):
            return 7
        else:
            return -1
    assert {f(x) for x in {Type('int'), Type('float'), Type('double')}} == {5, 7, -1}

@assert_compilation_succeeds()
def test_set_comprehension_type_to_const_int_ok():
    from tmppy import Type
    assert {5 for x in {Type('int'), Type('float'), Type('double')}} == {5}

@assert_compilation_succeeds()
def test_set_comprehension_type_to_type_ok():
    from tmppy import Type
    def f(x: Type):
        if x == Type('int'):
            return Type.pointer(Type('int'))
        elif x == Type('float'):
            return Type.pointer(Type('float'))
        else:
            return Type('void')
    assert {f(x) for x in {Type('int'), Type('float'), Type('double')}} == {Type.pointer(Type('int')), Type.pointer(Type('float')), Type('void')}

@assert_compilation_succeeds()
def test_set_comprehension_type_to_const_type_ok():
    from tmppy import Type
    assert {Type('float') for x in {Type('int'), Type('float'), Type('double')}} == {Type('float')}

@assert_compilation_succeeds()
def test_set_comprehension_type_to_custom_type_ok():
    from tmppy import Type
    @dataclass
    class TypeWrapper:
        x: Type
    assert {TypeWrapper(x) for x in {Type('int'), Type('float'), Type('float')}} == {TypeWrapper(Type('int')), TypeWrapper(Type('float'))}

@assert_compilation_succeeds()
def test_set_comprehension_type_to_const_custom_type_ok():
    from tmppy import Type
    @dataclass
    class TypeWrapper:
        x: Type
    assert {TypeWrapper(Type('double')) for x in {Type('int'), Type('float'), Type('float')}} == {TypeWrapper(Type('double'))}

@assert_compilation_succeeds()
def test_set_comprehension_in_function_using_function_arg_ok():
    def f(k: int):
        return {x * k for x in {1, k, 3}}
    assert f(2) == {2, 4, 6}

@assert_compilation_succeeds()
def test_set_comprehension_in_function_using_function_variable_ok():
    def f(b: bool):
        k = 2
        return {x * k for x in {1, k, 3}}
    assert f(True) == {2, 4, 6}

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_set_comprehension_from_bool_set_throws_toplevel():
    from tmppy import empty_set
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        if b:
            raise MyError(True)
        return True
    assert {f(x) for x in {True, False, False}} == empty_set(bool)

@assert_compilation_succeeds()
def test_set_comprehension_from_bool_set_throws_in_function_caught_success():
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
            return {f(x) for x in {True, False}}
        except MyError as e:
            return {e.b}
    assert g(True) == {True}

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_set_comprehension_from_int_set_throws_toplevel():
    from tmppy import empty_set
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(n: int):
        if n == 1:
            raise MyError(True)
        return True
    assert {f(x) for x in {0, 1, 2}} == empty_set(bool)

@assert_compilation_succeeds()
def test_set_comprehension_from_int_set_throws_in_function_caught_success():
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
            return {f(x) for x in {0, 1, 2}}
        except MyError as e:
            return {e.b}
    assert g(True) == {True}

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_set_comprehension_from_type_set_throws_toplevel():
    from tmppy import empty_set, Type
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(x: Type):
        if x == Type('float'):
            raise MyError(True)
        return True
    assert {f(x) for x in {Type('int'), Type('float'), Type('double')}} == empty_set(bool)

@assert_compilation_succeeds()
def test_set_comprehension_from_type_set_throws_in_function_caught_success():
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
            return {f(x) for x in {Type('int'), Type('float'), Type('double')}}
        except MyError as e:
            return {e.b}
    assert g(True) == {True}

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_set_comprehension_from_custom_type_set_throws_toplevel():
    from tmppy import empty_set
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
    assert {f(x) for x in {Int(0), Int(1), Int(2)}} == empty_set(bool)

@assert_compilation_succeeds()
def test_set_comprehension_from_custom_type_set_throws_in_function_caught_success():
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
            return {f(x) for x in {Int(0), Int(1), Int(2)}}
        except MyError as e:
            return {e.b}
    assert g(True) == {True}

@assert_conversion_fails
def test_set_comprehension_with_multiple_for_clauses_error():
    assert {y for x in {{1}, {2}} for y in x}  # error: Set comprehensions with multiple "for" clauses are not currently supported.

@assert_conversion_fails
def test_set_comprehension_with_if_clause_error():
    assert {x for x in {1, 2} if x != 1}  # error: "if" clauses in set comprehensions are not currently supported.

@assert_conversion_fails
def test_set_comprehension_with_unpacking_error():
    assert {x for x, y in {{1, 2}}}  # error: Only set comprehensions of the form {... for var_name in ...} are supported.

@assert_conversion_fails
def test_set_comprehension_with_non_set():
    assert {x for x in 1}  # error: The RHS of a set comprehension should be a set, but this value has type "int".

@assert_conversion_fails
def test_set_comprehension_with_non_set_var():
    def f(b: bool):
        n = 1  # note: n was defined here
        return {x for x in n}  # error: The RHS of a set comprehension should be a set, but this value has type "int".

@assert_conversion_fails
def test_set_comprehension_transforming_to_function_set_error():
    def f(b: bool):
        return b
    assert {f for x in {1, 2}}  # error: Creating sets of functions is not supported. The elements of this set have type: \(bool\) -> bool

@assert_compilation_succeeds()
def test_set_sum_error():
    assert sum({5, 1, 34}) == 40

@assert_compilation_succeeds()
def test_sum_empty_set_success():
    from tmppy import empty_set
    assert sum(empty_set(int)) == 0

@assert_conversion_fails
def test_sum_bool_set_error():
    assert sum({True, False}) == 40  # error: The argument of sum\(\) must have type List\[int\] or Set\[int\]. Got type: Set\[bool\]

@assert_compilation_succeeds()
def test_set_all_success_returns_true():
    assert all({True}) == True

@assert_compilation_succeeds()
def test_set_all_success_returns_false():
    assert all({True, False}) == False

@assert_compilation_succeeds()
def test_all_empty_set_success():
    from tmppy import empty_set
    assert all(empty_set(bool)) == True

@assert_conversion_fails
def test_all_int_set_error():
    assert all({1, 3}) == True  # error: The argument of all\(\) must have type List\[bool\] or Set\[bool\]. Got type: Set\[int\]

@assert_compilation_succeeds()
def test_set_any_success_one_arg_returns_false():
    assert any({False}) == False

@assert_compilation_succeeds()
def test_set_any_success_two_args_returns_false():
    assert any({False, True}) == True

@assert_compilation_succeeds()
def test_any_empty_set_success():
    from tmppy import empty_set
    assert any(empty_set(bool)) == False

@assert_conversion_fails
def test_any_int_set_error():
    assert any({1, 3}) == True  # error: The argument of any\(\) must have type List\[bool\] or Set\[bool\]. Got type: Set\[int\]

@assert_conversion_fails
def test_set_unpacking_as_tuple_error():
    def g(b1: bool):
        a, b = {1, 2}  # error: Unpacking requires a list on the RHS, but the value on the RHS has type Set\[int\]
        return b1

@assert_conversion_fails
def test_set_unpacking_as_list_error():
    def g(b1: bool):
        [a, b] = {1, 2}  # error: Unpacking requires a list on the RHS, but the value on the RHS has type Set\[int\]
        return b1

# TODO: implement this.
@assert_conversion_fails
def test_set_of_sets_equality_error():
    assert {{1, 2}, {3, 4}} != {{1, 2}}  # error: Type not supported in equality comparison: Set\[Set\[int\]\]

# TODO: implement this.
@assert_conversion_fails
def test_list_of_sets_equality_error():
    assert [{1, 2}, {3, 4}] != [{1, 2}]  # error: Type not supported in equality comparison: List\[Set\[int\]\]

# TODO: implement this.
@assert_conversion_fails
def test_custom_type_containing_set_equality_error():
    from typing import Set
    @dataclass
    class MyType:
        s: Set[int]
    assert MyType({1}) == MyType({1})  # error: Type not supported in equality comparison: MyType

@assert_compilation_succeeds()
def test_set_of_lists_ok():
    assert {[1, 2], [3, 4]} != {[1, 2]}

@assert_compilation_succeeds()
def test_bool_set_in_empty():
    from tmppy import empty_set
    assert not (False in empty_set(bool))

@assert_compilation_succeeds()
def test_int_set_in_empty():
    from tmppy import empty_set
    assert not (1 in empty_set(int))

@assert_compilation_succeeds()
def test_type_set_in_empty():
    from tmppy import Type, empty_set
    assert not (Type('int') in empty_set(Type))

@assert_compilation_succeeds()
def test_bool_set_in_not_present():
    assert not (False in {True})

@assert_compilation_succeeds()
def test_int_set_in_not_present():
    assert not (1 in {2})

@assert_compilation_succeeds()
def test_type_set_in_not_present():
    from tmppy import Type
    assert not (Type('int') in {Type('float')})

@assert_compilation_succeeds()
def test_bool_set_in_present():
    assert False in {False}

@assert_compilation_succeeds()
def test_int_set_in_present():
    assert 5 in {5}

@assert_compilation_succeeds()
def test_type_set_in_present():
    from tmppy import Type
    assert Type('int') in {Type('int')}

@assert_conversion_fails
def test_set_in_type_mismatch():
    def f(b: bool):
        return 1 in {True}  # error: Type mismatch in in: int vs Set\[bool\]

if __name__== '__main__':
    main()
