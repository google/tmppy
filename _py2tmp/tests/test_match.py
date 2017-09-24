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
def test_match_success():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern('T(*)(U)'):
                lambda T, U:
                    Type('double'),
            TypePattern('int(*)(T)'):
                lambda T:
                    T,
            TypePattern('float(*)(T)'):
                lambda T:
                    T,
        })
    assert f(Type('int(*)(int)')) == Type('int')

@assert_compilation_succeeds
def test_match_in_assignment_success():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        result = match(x)({
            TypePattern('T(*)(U)'):
                lambda T, U:
                    Type('double'),
            TypePattern('int(*)(T)'):
                lambda T:
                    T,
            TypePattern('float(*)(T)'):
                lambda T:
                    T,
        })
        return result
    assert f(Type('int(*)(int)')) == Type('int')

@assert_compilation_succeeds
def test_match_calling_function_success():
    from tmppy import Type, TypePattern, match
    def id(x: Type):
        return x
    def f(x: Type):
        result = match(x)({
            TypePattern('T(*)(U)'):
                lambda T, U:
                    Type('double'),
            TypePattern('int(*)(T)'):
                lambda T:
                    id(T),
            TypePattern('float(*)(T)'):
                lambda T:
                    T,
        })
        return result
    assert f(Type('int(*)(int)')) == Type('int')

@assert_compilation_succeeds
def test_match_multiple_success():
    from tmppy import Type, TypePattern, match
    def f(y: Type):
        return match(Type('int*'), y)({
            TypePattern('T', 'U'):
                lambda T, U:
                    False,
            TypePattern('T*', 'U*'):
                lambda T, U:
                    True,
        })
    assert f(Type('double**'))

@assert_compilation_succeeds
def test_match_with_capture_success():
    from tmppy import Type, TypePattern, match
    def f(x: Type, y: Type):
        return match(x)({
            TypePattern('T(*)(U)'):
                lambda T, U:
                    Type('double'),
            TypePattern('int(*)(T)'):
                lambda T:
                    y,
            TypePattern('float(*)(T)'):
                lambda T:
                    T,
        })
    assert f(Type('int(*)(int)'), Type('bool')) == Type('bool')

@assert_compilation_succeeds
def test_nested_match_success():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern('T'):
                lambda T:
                    Type('double'),
            TypePattern('T(*)(U)'):
                lambda T, U:
                    match(T, U)({
                        TypePattern('int', 'V'):
                            lambda V:
                                V,
                        TypePattern('float', 'V'):
                            lambda V:
                                Type('bool'),
                    }),
        })
    assert f(Type('int(*)(int)')) == Type('int')

@assert_compilation_succeeds
def test_nested_match_with_capture_outer_only():
    from tmppy import Type, TypePattern, match
    def f(x: Type, y: Type):
        return match(x)({
            TypePattern('T'):
                lambda T:
                    y,
            TypePattern('T(*)(U)'):
                lambda T, U:
                    match(T, U)({
                        TypePattern('int', 'V'):
                            lambda V:
                                V,
                        TypePattern('float', 'V'):
                            lambda V:
                                Type('bool'),
                    }),
        })
    assert f(Type('int(*)(int)'), Type('bool')) == Type('int')


@assert_compilation_succeeds
def test_nested_match_with_capture():
    from tmppy import Type, TypePattern, match
    def f(x: Type, y: Type):
        return match(x)({
            TypePattern('T'):
                lambda T:
                    y,
            TypePattern('T(*)(U)'):
                lambda T, U:
                    match(T, U)({
                        TypePattern('int', 'V'):
                            lambda V:
                                y,
                        TypePattern('float', 'V'):
                            lambda V:
                                Type('bool'),
                    }),
        })
    assert f(Type('int(*)(int)'), Type('bool')) == Type('bool')

@assert_compilation_succeeds
def test_match_with_equality_comparison_success():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern('T(*)(U)'):
                lambda T, U:
                    Type('double') == Type('int'),
            TypePattern('int(*)(T)'):
                lambda T:
                    T == Type('int'),
            TypePattern('float(*)(T)'):
                lambda T:
                    T == Type('int'),
        })
    assert f(Type('int(*)(int)'))

@assert_compilation_succeeds
def test_match_with_function_expr_call():
    from tmppy import Type, TypePattern, match
    def g(x: Type):
        return x
    def h(x: Type):
        return g
    def f(x: Type):
        return match(x)({
            TypePattern('T(*)(U)'):
                lambda T, U:
                    h(T)(Type('double')),
            TypePattern('int(*)(T)'):
                lambda T:
                    T,
            TypePattern('float(*)(T)'):
                lambda T:
                    T,
        })
    assert f(Type('int(*)(int)')) == Type('int')

@assert_compilation_succeeds
def test_match_with_list_expr_call():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern('T(*)(U)'):
                lambda T, U:
                    [Type('double')],
            TypePattern('int(*)(T)'):
                lambda T:
                    [T],
            TypePattern('float(*)(T)'):
                lambda T:
                    [T],
        })
    assert f(Type('int(*)(int)')) == [Type('int')]

@assert_compilation_succeeds
def test_match_main_definition_uses_param_success():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern('T'):
                lambda T:
                    T,
            TypePattern('int(*)()'):
                lambda:
                    Type('bool'),
        })
    assert f(Type('int')) == Type('int')

@assert_conversion_fails
def test_match_keyword_argument_in_match_exprs():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x,
                     wrong_arg=True)(  # error: Keyword arguments are not allowed in match
            {
                TypePattern('T(*)(U)'):
                    lambda T, U:
                        Type('double'),
                TypePattern('int(*)(T)'):
                    lambda T:
                        T,
            })

@assert_conversion_fails
def test_match_keyword_argument_in_match_mapping():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern('T(*)(U)'):
                lambda T, U:
                    Type('double'),
            TypePattern('int(*)(T)'):
                lambda T:
                    T,
        },
        wrong_arg=True)  # error: Keyword arguments are not allowed in match

@assert_conversion_fails
def test_match_multiple_arguments_in_mapping():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({  # error: Malformed match\(...\)\({...}\)
            TypePattern('T(*)(U)'):
                lambda T, U:
                    Type('double'),
            TypePattern('int(*)(T)'):
                lambda T:
                    T,
        },
        {})

@assert_conversion_fails
def test_match_non_dict_argument_in_mapping():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)(  # error: Malformed match\(...\)\({...}\)
            Type('int'))

@assert_conversion_fails
def test_match_no_match_exprs_error():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match()({  # error: Found match\(\) with no arguments; it must have at least 1 argument.
            TypePattern('T'):
                lambda T:
                    T,
        })

@assert_conversion_fails
def test_match_no_mappings_error():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)(
            {})  # error: An empty mapping dict was passed to match\(\), but at least 1 mapping is required.

@assert_conversion_fails
def test_match_bool_expr_error():
    from tmppy import Type, TypePattern, match
    def f(x: bool):
        return match(x)({  # error: All arguments passed to match must have type Type, but an argument with type bool was specified.
            TypePattern('T'):
                lambda T:
                    T,
        })

@assert_conversion_fails
def test_match_function_expr_error():
    from tmppy import Type, TypePattern, match
    from typing import Callable
    def f(x: Callable[[Type], Type]):
        return match(x)({  # error: All arguments passed to match must have type Type, but an argument with type \(Type\) -> Type was specified.
            TypePattern('T'):
                lambda T:
                    T,
        })

@assert_conversion_fails
def test_match_key_expr_not_pattern():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            True:  # error: All keys in the dict used in match\(...\)\({...}\) must be of the form TypePattern\(...\).
                lambda T:
                    T,
        })

@assert_conversion_fails
def test_match_value_expr_not_lambda():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern('T'):
                Type('int'),  # error: All values in the dict used in match\(...\)\({...}\) must be lambdas.
        })

@assert_conversion_fails
def test_match_pattern_with_no_arguments_error():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern():  # error: Found TypePattern with no arguments, but the first argument is required.
                lambda T:
                    T,
        })

@assert_conversion_fails
def test_match_pattern_with_keyword_arguments_error():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x, x)({
            TypePattern('T',
                        wrong_arg=x):  # error: Keyword arguments in TypePattern are not supported yet.
                lambda T:
                    T,
        })

@assert_conversion_fails
def test_match_pattern_with_type_expr():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern(x):  # error: The non-keyword arguments of TypePattern must be string literals.
                lambda T:
                    T,
        })

@assert_conversion_fails
def test_match_mappings_with_different_types_error():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern('T(*)(U)'):
                lambda T, U:
                    Type('double'),  # note: A previous lambda returning a Type was here.
            TypePattern('int(*)(T)'):
                lambda T:
                    True,  # error: All lambdas in a match\(...\)\({...}\) expression should return the same type, but this lambda returns a bool while a previous lambda in this match expression returns a Type
        })

@assert_conversion_fails
def test_match_multiple_mappings_that_specialize_nothing():
    from tmppy import Type, TypePattern, match
    def f(x: Type):
        return match(x)({
            TypePattern('T'):  # note: A previous specialization that specializes nothing was here
                lambda T:
                    Type('double'),
            TypePattern('U'):  # error: Found multiple specializations that specialize nothing
                lambda U:
                    Type('double'),
        })

