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

from _py2tmp.compiler.testing import main, assert_compilation_succeeds, assert_conversion_fails

@assert_compilation_succeeds()
def test_match_success():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                Type('double'),
            Type.pointer(Type.function(Type('int'), [U])):
                U,
            Type.pointer(Type.function(Type('float'), [U])):
                U,
        })
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')]))) == Type('int')

@assert_compilation_succeeds()
def test_match_in_assignment_success():
    from tmppy import Type, match
    def f(x: Type):
        result = match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                Type('double'),
            Type.pointer(Type.function(Type('int'), [T])):
                T,
            Type.pointer(Type.function(Type('float'), [T])):
                T,
        })
        return result
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')]))) == Type('int')

@assert_compilation_succeeds()
def test_match_calling_function_success():
    from tmppy import Type, match
    def id(x: Type):
        return x
    def f(x: Type):
        result = match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                Type('double'),
            Type.pointer(Type.function(Type('int'), [T])):
                id(T),
            Type.pointer(Type.function(Type('float'), [T])):
                T,
        })
        return result
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')]))) == Type('int')

@assert_compilation_succeeds()
def test_match_multiple_success():
    from tmppy import Type, match
    def f(y: Type):
        return match(Type.pointer(Type('int')), y)(lambda T, U: {
            (T, U):
                False,
            (Type.pointer(T), Type.pointer(U)):
                True,
        })
    assert f(Type.pointer(Type.pointer(Type('double'))))

@assert_compilation_succeeds()
def test_match_with_capture_success():
    from tmppy import Type, match
    def f(x: Type, y: Type):
        return match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                Type('double'),
            Type.pointer(Type.function(Type('int'), [T])):
                y,
            Type.pointer(Type.function(Type('float'), [T])):
                T,
        })
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')])), Type('bool')) == Type('bool')

@assert_compilation_succeeds()
def test_nested_match_success():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T, U: {
            T:
                Type('double'),
            Type.pointer(Type.function(T, [U])):
                match(T, U)(lambda V: {
                    (Type('int'), V):
                        V,
                    (Type('float'), V):
                        Type('bool'),
                }),
        })
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')]))) == Type('int')

@assert_compilation_succeeds()
def test_nested_match_with_capture_outer_only():
    from tmppy import Type, match
    def f(x: Type, y: Type):
        return match(x)(lambda T, U: {
            T:
                y,
            Type.pointer(Type.function(T, [U])):
                match(T, U)(lambda V: {
                    (Type('int'), V):
                        V,
                    (Type('float'), V):
                        Type('bool'),
                }),
        })
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')])), Type('bool')) == Type('int')


@assert_compilation_succeeds()
def test_nested_match_with_capture():
    from tmppy import Type, match
    def f(x: Type, y: Type):
        return match(x)(lambda T, U: {
            T:
                y,
            Type.pointer(Type.function(T, [U])):
                match(T, U)(lambda V: {
                    (Type('int'), V):
                        y,
                    (Type('float'), V):
                        Type('bool'),
                }),
        })
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')])), Type('bool')) == Type('bool')

@assert_compilation_succeeds()
def test_match_with_equality_comparison_success():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                Type('double') == Type('int'),
            Type.pointer(Type.function(Type('int'), [T])):
                T == Type('int'),
            Type.pointer(Type.function(Type('float'), [T])):
                T == Type('int'),
        })
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')])))

@assert_compilation_succeeds()
def test_match_with_function_expr_call():
    from tmppy import Type, match
    def g(x: Type):
        return x
    def h(x: Type):
        return g
    def f(x: Type):
        return match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                h(T)(Type('double')),
            Type.pointer(Type.function(Type('int'), [T])):
                T,
            Type.pointer(Type.function(Type('float'), [T])):
                T,
        })
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')]))) == Type('int')

@assert_compilation_succeeds()
def test_match_with_list_expr_call():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                [Type('double')],
            Type.pointer(Type.function(Type('int'), [T])):
                [T],
            Type.pointer(Type.function(Type('float'), [T])):
                [T],
        })
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')]))) == [Type('int')]

@assert_compilation_succeeds()
def test_match_with_set_expr_call():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                {Type('double')},
            Type.pointer(Type.function(Type('int'), [T])):
                {T},
            Type.pointer(Type.function(Type('float'), [T])):
                {T},
        })
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')]))) == {Type('int')}

@assert_compilation_succeeds()
def test_match_with_int_expr_call():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                1,
            Type.pointer(Type.function(Type('int'), [T])):
                2,
            Type.pointer(Type.function(Type('float'), [T])):
                3,
        })
    assert f(Type.pointer(Type.function(Type('int'), [Type('int')]))) == 2

@assert_compilation_succeeds()
def test_match_main_definition_uses_param_success():
    from tmppy import Type, match, empty_list
    def f(x: Type):
        return match(x)(lambda T: {
            T:
                T,
            Type.pointer(Type.function(Type('int'), empty_list(Type))):
                Type('bool'),
        })
    assert f(Type('int')) == Type('int')

@assert_compilation_succeeds()
def test_reference_type_expr_as_match_expr_matched_success():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type.reference(T):
                T,
            T:
                Type('double'),
        })
    assert f(Type.reference(Type('int'))) == Type('int')

@assert_compilation_succeeds(always_allow_toplevel_static_asserts_after_optimization=True)
def test_reference_type_expr_as_match_expr_not_matched_success():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type.reference(T):
                T,
            T:
                Type('double'),
        })
    assert f(Type.rvalue_reference(Type('int'))) == Type('double')

@assert_compilation_succeeds()
def test_rvalue_reference_type_expr_as_match_expr_matched_success():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type.rvalue_reference(T):
                T,
            T:
                Type('double'),
        })
    assert f(Type.rvalue_reference(Type('int'))) == Type('int')

@assert_compilation_succeeds()
def test_rvalue_reference_type_expr_as_match_expr_not_matched_success():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type.rvalue_reference(T):
                T,
            T:
                Type('double'),
        })
    assert f(Type.pointer(Type('int'))) == Type('double')

@assert_compilation_succeeds()
def test_const_type_expr_as_match_expr_matched_success():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type.const(T):
                T,
            T:
                Type('double'),
        })
    assert f(Type.const(Type('int'))) == Type('int')

@assert_compilation_succeeds()
def test_const_type_expr_as_match_expr_not_matched_success():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type.const(T):
                T,
            T:
                Type('double'),
        })
    assert f(Type.pointer(Type('int'))) == Type('double')

@assert_compilation_succeeds()
def test_array_type_expr_as_match_expr_matched_success():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type.array(T):
                T,
            T:
                Type('double'),
        })
    assert f(Type.array(Type('int'))) == Type('int')

@assert_compilation_succeeds()
def test_array_type_expr_as_match_expr_not_matched_success():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type.array(T):
                T,
            T:
                Type('double'),
        })
    assert f(Type.pointer(Type('int'))) == Type('double')

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_template_instantiation_type_expr_as_match_expr_matched_success():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type.template_instantiation('std::tuple', [T, Type('float')]):
                T,
            T:
                Type('double'),
        })
    assert f(Type.template_instantiation('std::tuple', [Type('int'), Type('float')])) == Type('int')

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_template_instantiation_type_expr_as_match_expr_not_matched_success():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type.template_instantiation('std::tuple', [T, Type('float')]):
                T,
            T:
                Type('double'),
        })
    assert f(Type.template_instantiation('std::tuple', [Type('int'), Type('void')])) == Type('double')

@assert_compilation_succeeds()
def test_match_expr_with_trivial_specialization_and_no_free_variables():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda T: {
            Type('int'):
                Type('int'),
            T:
                Type('double'),
        })
    assert f(Type('void')) == Type('double')

@assert_conversion_fails
def test_match_keyword_argument_in_match_exprs():
    from tmppy import Type, match
    def f(x: Type):
        return match(x,
                     wrong_arg=True)(  # error: Keyword arguments are not allowed in match
            lambda T, U: {
                Type.pointer(Type.function(T, [U])):
                    Type('double'),
                Type.pointer(Type.function(Type('int'), [T])):
                    T,
            })

@assert_conversion_fails
def test_match_vararg_in_match_exprs():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(
            lambda *T: { # error: Malformed match\(\): vararg lambda arguments are not supported
                T: T,
            })

@assert_conversion_fails
def test_match_keyword_argument_in_match_mapping():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                Type('double'),
            Type.pointer(Type.function(Type('int'), [T])):
                T,
        },
        wrong_arg=True)  # error: Keyword arguments are not allowed in match

@assert_conversion_fails
def test_match_multiple_arguments_in_mapping():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T, U: {  # error: Malformed match\(\)
            Type.pointer(Type.function(T, [U])):
                Type('double'),
            Type.pointer(Type.function(Type('int'), [T])):
                T,
        },
        {})

@assert_conversion_fails
def test_match_non_dict_argument_in_mapping():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(  # error: Malformed match\(\)
            Type('int'))

@assert_conversion_fails
def test_match_no_match_exprs_error():
    from tmppy import Type, match
    def f(x: Type):
        return match()(lambda T: {  # error: Found match\(\) with no arguments; it must have at least 1 argument.
            T:
                T,
        })

@assert_conversion_fails
def test_match_no_mappings_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda:
            {})  # error: An empty mapping dict was passed to match\(\), but at least 1 mapping is required.

@assert_conversion_fails
def test_match_bool_expr_error():
    from tmppy import match
    def f(x: bool):
        return match(x)(lambda T: {  # error: All arguments passed to match must have type Type, but an argument with type bool was specified.
            T:
                T,
        })

@assert_conversion_fails
def test_match_function_expr_error():
    from tmppy import Type, match
    from typing import Callable
    def f(x: Callable[[Type], Type]):
        return match(x)(lambda T: {  # error: All arguments passed to match must have type Type, but an argument with type \(Type\) -> Type was specified.
            T:
                T,
        })

@assert_conversion_fails
def test_match_key_expr_not_type_pattern():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(  # note: The corresponding match\(\) was here
            lambda: {
                True:  # error: Type patterns must have type Type but this pattern has type bool
                    15,
            })

@assert_conversion_fails
def test_match_value_expr_not_lambda():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)({  # error: Malformed match\(\)
            Type('int'):
                Type('int'),
        })

@assert_conversion_fails
def test_match_value_expr_lambda_not_returning_dict():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(  # error: Malformed match\(\)
            lambda: 15)

@assert_conversion_fails
def test_match_pattern_with_no_arguments_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(  # note: The corresponding match\(\) was here
            lambda: {
                ():  # error: 0 type patterns were provided, while 1 were expected
                    Type('int'),
            })

@assert_conversion_fails
def test_match_pattern_argument_type_mismatch_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(
            True)( # error: All arguments passed to match must have type Type, but an argument with type bool was specified.
            lambda T: {
                T:
                    T,
            })

@assert_conversion_fails
def test_match_pattern_with_type_expr():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T: {
            x:
                T,  # error: T was used in the result of this match branch but not in any of its patterns
        })

@assert_conversion_fails
def test_match_mappings_with_different_types_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T, U: {
            Type.pointer(Type.function(T, [U])):
                Type('double'),  # note: A previous branch returning a Type was here.
            Type.pointer(Type.function(Type('int'), [T])):
                True,  # error: All branches in a match\(\) must return the same type, but this branch returns a bool while a previous branch in this match expression returns a Type
        })

@assert_conversion_fails
def test_match_multiple_mappings_that_specialize_nothing():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda T, U: {
            T:  # note: A previous specialization that specializes nothing was here
                Type('double'),
            U:  # error: Found multiple specializations that specialize nothing
                Type('int'),
        })

@assert_conversion_fails
def test_match_lambda_var_not_in_pattern_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda Baz:  # error: The lambda argument Baz was not used in any pattern, it should be removed.
            {
            Type('Bar'):
                Type('double'),
        })

@assert_conversion_fails
def test_match_expr_containing_comparison_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            1 < 2:  # error: Comparisons are not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_attribute_access_error():
    from tmppy import Type, match
    @dataclass
    class MyType:
        x: bool
    def f(m: MyType):
        return match(Type('int'))(lambda T: {
            m.x:  # error: Attribute access is not allowed in match patterns
                T,
        })

@assert_conversion_fails
def test_match_expr_containing_not_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            not True:  # error: The "not" operator is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_and_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            True and False:  # error: The "and" operator is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_or_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            True or False:  # error: The "or" operator is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_unary_minus_error():
    from tmppy import Type, match
    def f(x: Type):
        n = 5
        return match(x)(lambda: {
            -n:  # error: The "-" operator is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_binary_plus_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            3 + 5:  # error: The "\+" operator is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_binary_minus_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            3 - 5:  # error: The "-" operator is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_multiplication_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            3 * 5:  # error: The "\*" operator is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_division_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            3 // 5:  # error: The "//" operator is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_modulus_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            3 % 5:  # error: The "%" operator is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_list_comprehension_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            [n for n in [1, 2]]:  # error: List comprehensions are not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_set_comprehension_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            {n for n in {1, 2}}:  # error: Set comprehensions are not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_type_template_member():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            Type.template_member():  # error: Type.template_member\(\) is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_sum():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            sum([]):  # error: sum\(\) is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_any():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            any([]):  # error: any\(\) is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_all():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            all([]):  # error: all\(\) is not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_equality_comparison():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            3 == 3:  # error: Comparisons are not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_inequality_comparison():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            3 != 3:  # error: Comparisons are not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_in_error():
    from tmppy import Type, match
    def f(x: Type):
        return match(x)(lambda: {
            1 in [1]:  # error: Comparisons are not allowed in match patterns
                x,
        })

@assert_conversion_fails
def test_match_expr_containing_function_call():
    from tmppy import Type, match
    def g(n: int):
        return Type('int')
    def f(x: Type):
        return match(x)(lambda: {
            g(3):  # error: Function calls are not allowed in match patterns
                x,
        })

@assert_compilation_succeeds()
def test_match_expr_requiring_to_pick_arbitrary_arg():
    from tmppy import Type, match
    def f(b: bool):
        return match(Type('int'))(lambda: {
            Type('int'):
                42,
        })
    assert f(True) == 42

@assert_compilation_succeeds()
def test_match_expr_requiring_to_pick_arbitrary_arg_skipping_function_type():
    from tmppy import Type, match
    from typing import Callable
    def f(g: Callable[[int], int], b: bool):
        return match(Type('int'))(lambda: {
            Type('int'):
                42,
        })
    def h(n: int):
        return n
    assert f(h, True) == 42

@assert_compilation_succeeds()
def test_match_expr_requiring_to_pick_arbitrary_function_type_arg():
    from tmppy import Type, match
    from typing import Callable
    def f(g: Callable[[int], int]):
        return match(Type('int'))(lambda: {
            Type('int'):
                42,
        })
    def h(n: int):
        return n
    assert f(h) == 42

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_match_expr_extract_list_empty():
    from tmppy import Type, match, empty_list
    def unpack_tuple(t: Type):
        return match(t)(lambda Ts: {
            Type.template_instantiation('std::tuple', [*Ts]):
                Ts
        })
    assert unpack_tuple(Type.template_instantiation('std::tuple', empty_list(Type))) \
        == empty_list(Type)

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_match_expr_extract_list():
    from tmppy import Type, match
    def unpack_tuple(t: Type):
        return match(t)(lambda Ts: {
            Type.template_instantiation('std::tuple', [*Ts]):
                Ts
        })
    assert unpack_tuple(Type.template_instantiation('std::tuple', [Type('int'), Type('float'), Type('double')])) \
        == [Type('int'), Type('float'), Type('double')]

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_match_expr_extract_list_used_in_nested_match():
    from tmppy import Type, match
    def unpack_tuple(t: Type):
        return match(t)(lambda Ts: {
            Type.template_instantiation('std::tuple', [*Ts]):
                match(Type('int'))(lambda T: {
                    T:
                        Ts
                })
        })
    assert unpack_tuple(Type.template_instantiation('std::tuple', [Type('int'), Type('float'), Type('double')])) \
        == [Type('int'), Type('float'), Type('double')]

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_match_expr_extract_list_and_front_element():
    from tmppy import Type, match
    def unpack_tuple(t: Type):
        return match(t)(lambda FirstT, Ts: {
            Type.template_instantiation('std::tuple', [FirstT, *Ts]):
                [[FirstT], Ts]
        })
    assert unpack_tuple(Type.template_instantiation('std::tuple', [Type('int'), Type('float'), Type('double'), Type('char')])) \
        == [[Type('int')], [Type('float'), Type('double'), Type('char')]]

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_match_expr_extract_list_and_front_elements():
    from tmppy import Type, match
    def unpack_tuple(t: Type):
        return match(t)(lambda FirstT, SecondT, Ts: {
            Type.template_instantiation('std::tuple', [FirstT, SecondT, *Ts]):
                [[FirstT, SecondT], Ts]
        })
    assert unpack_tuple(Type.template_instantiation('std::tuple', [Type('int'), Type('float'), Type('double'), Type('char')])) \
        == [[Type('int'), Type('float')], [Type('double'), Type('char')]]

@assert_conversion_fails
def test_match_expr_extract_last_element_error():
    from tmppy import Type, match
    def unpack_tuple(t: Type):
        return match(t)(lambda Ts, LastT: {
            Type.template_instantiation('std::tuple', [*Ts, LastT]):  # error: List extraction is only allowed at the end of the list
                [Ts, [LastT]]
        })

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_match_expr_extract_multiple_lists():
    from tmppy import Type, match
    def unpack_tuple_of_tuples(t: Type):
        return match(t)(lambda Ts, Us: {
            Type.template_instantiation('std::tuple',
                                        [Type.template_instantiation('std::tuple', [*Ts]),
                                         Type.template_instantiation('std::tuple', [*Us])]):
                [Ts, Us]
        })
    assert unpack_tuple_of_tuples(Type.template_instantiation('std::tuple',
                                                              [Type.template_instantiation('std::tuple', [Type('int'), Type('float')]),
                                                               Type.template_instantiation('std::tuple', [Type('double')])])) \
        == [[Type('int'), Type('float')], [Type('double')]]

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_match_expr_extract_list_multiple_times_matched():
    from tmppy import Type, match
    def unpack_tuple_of_tuples(t: Type):
        return match(t)(lambda T, Ts: {
            Type.template_instantiation('std::tuple',
                                        [Type.template_instantiation('std::tuple', [*Ts]),
                                         Type.template_instantiation('std::tuple', [Type('int'), *Ts])]):
                Ts,
            T:
                [Type('void')],
        })
    assert unpack_tuple_of_tuples(Type.template_instantiation('std::tuple',
                                                              [Type.template_instantiation('std::tuple', [Type('float'), Type('double')]),
                                                               Type.template_instantiation('std::tuple', [Type('int'), Type('float'), Type('double')])])) \
        == [Type('float'), Type('double')]

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_match_expr_extract_list_multiple_times_matched_without_default_case():
    from tmppy import Type, match
    def unpack_tuple_of_tuples(t: Type):
        return match(t)(lambda Ts: {
            Type.template_instantiation('std::tuple',
                                        [Type.template_instantiation('std::tuple', [*Ts]),
                                         Type.template_instantiation('std::tuple', [Type('int'), *Ts])]):
                Ts,
        })
    assert unpack_tuple_of_tuples(Type.template_instantiation('std::tuple',
                                                              [Type.template_instantiation('std::tuple', [Type('float'), Type('double')]),
                                                               Type.template_instantiation('std::tuple', [Type('int'), Type('float'), Type('double')])])) \
        == [Type('float'), Type('double')]

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <utility>
''')
def test_match_expr_extract_list_multiple_times_not_matched():
    from tmppy import Type, match
    def unpack_tuple_of_tuples(t: Type):
        return match(t)(lambda T, Ts: {
            Type.template_instantiation('std::tuple',
                                        [Type.template_instantiation('std::tuple', [*Ts]),
                                         Type.template_instantiation('std::tuple', [Type('int'), *Ts])]):
                Ts,
            T:
                [Type('void')],
        })
    assert unpack_tuple_of_tuples(Type.template_instantiation('std::tuple',
                                                              [Type.template_instantiation('std::tuple', [Type('float'), Type('double')]),
                                                               Type.template_instantiation('std::tuple', [Type('int'), Type('double'), Type('double')])])) \
        == [Type('void')]

@assert_conversion_fails
def test_match_expr_extract_list_also_used_as_type_before_error():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda X: {
            Type.template_instantiation('std::tuple',
                                        [Type.template_instantiation('std::tuple',
                                                                     [X]),  # note: A previous match as a Type was here
                                         Type.template_instantiation('std::tuple',
                                                                     [*X])]):  # error: List extraction can't be used on X because it was already used to match a Type
                Type('int'),
        })

@assert_conversion_fails
def test_match_expr_extract_list_also_used_as_type_after_error():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda X: {
            Type.template_instantiation('std::tuple',
                                        [Type.template_instantiation('std::tuple',
                                                                     [*X]),  # note: A previous match as a List\[Type\] was here
                                         Type.template_instantiation('std::tuple',
                                                                     [X])]):  # error: Can't match X as a Type because it was already used to match a List\[Type\]
                Type('int'),
        })

@assert_compilation_succeeds()
def test_match_expr_extract_list_also_used_as_type_before_different_branch_ok():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda X: {
            Type.template_instantiation('std::tuple', [Type('int'), X]):
                [X],
            Type.template_instantiation('std::tuple', [*X]):
                X,
        })
    assert f(Type.template_instantiation('std::tuple', [Type('int'), Type('double')])) == [Type('double')]
    assert f(Type.template_instantiation('std::tuple', [Type('double'), Type('int')])) == [Type('double'), Type('int')]

@assert_compilation_succeeds()
def test_match_expr_extract_list_also_used_as_type_after_different_branch_ok():
    from tmppy import Type, match
    def f(t: Type):
        return match(t)(lambda X: {
            Type.template_instantiation('std::tuple', [*X]):
                X,
            Type.template_instantiation('std::tuple', [Type('int'), X]):
                [X],
        })
    assert f(Type.template_instantiation('std::tuple', [Type('int'), Type('double')])) == [Type('double')]
    assert f(Type.template_instantiation('std::tuple', [Type('double'), Type('int')])) == [Type('double'), Type('int')]

if __name__== '__main__':
    main()
