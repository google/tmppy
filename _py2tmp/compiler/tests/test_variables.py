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
def test_bool_variable_success():
    def f(x: bool):
        y = x
        return y
    assert f(True) == True

@assert_compilation_succeeds()
def test_int_variable_success():
    def f(x: int):
        y = x
        return y
    assert f(3) == 3

@assert_compilation_succeeds()
def test_type_variable_success():
    from tmppy import Type
    def f(x: Type):
        y = x
        return y
    assert f(Type('int')) == Type('int')

@assert_compilation_succeeds()
def test_function_variable_success():
    from tmppy import Type
    from typing import Callable
    def f(x: Callable[[Type], Type]):
        y = x
        return y(Type('int'))
    def g(x: Type):
        return x
    assert f(g) == Type('int')

@assert_compilation_succeeds()
def test_meta_meta_function_variable_success():
    from tmppy import Type
    def f1(x: Type):
        return Type('int')
    def f2(x: bool):
        return f1
    def f3(x: Type):
        return f2
    def f4(x: Type):
        return f3
    assert f4(Type('float'))(Type('int'))(True)(Type('int')) == Type('int')

@assert_conversion_fails
def test_variable_reassigned_error():
    def f(x: bool):
        y = x  # note: The previous declaration was here.
        y = x  # error: y was already defined in this scope.
        return y

@assert_conversion_fails
def test_augmented_assignment_error():
    def f(x: bool):
        y = x
        y += x # error: Augmented assignments are not supported.
        return y

@assert_conversion_fails
def test_assignment_with_type_annotation_error():
    '''
    def f(x: bool):
        y: bool = x  # error: Assignments with type annotations are not supported.
        return y
    '''

@assert_conversion_fails
def test_assignment_with_type_comment_error():
    def f(x: bool):
        y = x  # type: bool # error: Type comments in assignments are not supported.
        return y

@assert_conversion_fails
def test_multi_assignment_error():
    def f(x: bool):
        y = z = x  # error: Multi-assignment is not supported.
        return y

@assert_conversion_fails
def test_assignment_to_expression_error():
    def f(x: bool):
        x[0] = x  # error: Assignment not supported.
        return x

@assert_compilation_succeeds()
def test_function_arg_named_type_ok():
    from tmppy import Type
    def f(type: Type):
        return Type('float')
    assert f(Type('int')) == Type('float')

@assert_compilation_succeeds()
def test_function_arg_named_value_ok():
    def f(value: int):
        return 2
    assert f(1) == 2

@assert_compilation_succeeds()
def test_function_arg_named_error_in_function_returning_type_ok():
    from tmppy import Type
    def f(error: Type):
        return Type('float')
    assert f(Type('int')) == Type('float')

@assert_compilation_succeeds()
def test_function_arg_named_error_in_function_returning_value_ok():
    from tmppy import Type
    def f(error: Type):
        return 2
    assert f(Type('int')) == 2

@assert_compilation_succeeds()
def test_variable_named_type_ok():
    from tmppy import Type
    def f(b: bool):
        type = Type('int')
        return Type('float')
    assert f(True) == Type('float')

@assert_compilation_succeeds()
def test_variable_named_value_ok():
    def f(b: bool):
        value = 1
        return 2
    assert f(True) == 2

@assert_compilation_succeeds()
def test_variable_named_error_in_function_returning_type_ok():
    from tmppy import Type
    def f(b: bool):
        error = Type('int')
        return Type('float')
    assert f(True) == Type('float')

@assert_compilation_succeeds()
def test_variable_named_error_in_function_returning_value_ok():
    def f(b: bool):
        error = 1
        return 2
    assert f(True) == 2

@assert_compilation_succeeds()
def test_caught_exception_named_type_ok():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, type1: Type):
            self.message = 'Something went wrong'
            self.type1 = type1
    def f(x: Type):
        try:
            raise MyError(x)
        except MyError as type:
            return type.type1
    assert f(Type('int')) == Type('int')

@assert_compilation_succeeds()
def test_caught_exception_named_value_ok():
    class MyError(Exception):
        def __init__(self, n: int):
            self.message = 'Something went wrong'
            self.n = n
    def f(n: int):
        try:
            raise MyError(n)
        except MyError as error:
            return error.n
    assert f(15) == 15

@assert_compilation_succeeds()
def test_caught_exception_named_error_in_function_returning_type_ok():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, type1: Type):
            self.message = 'Something went wrong'
            self.type1 = type1
    def f(x: Type):
        try:
            raise MyError(x)
        except MyError as type:
            return type.type1
    assert f(Type('int')) == Type('int')

@assert_compilation_succeeds()
def test_caught_exception_named_error_in_function_returning_value_ok():
    class MyError(Exception):
        def __init__(self, n: int):
            self.message = 'Something went wrong'
            self.n = n
    def f(n: int):
        try:
            raise MyError(n)
        except MyError as error:
            return error.n
    assert f(15) == 15

@assert_compilation_succeeds()
def test_match_variable_named_type_ok():
    from tmppy import Type, match
    def f(b: bool):
        return match(Type('int'))(lambda type: {
            type:
                Type.pointer(type),
        })
    assert f(True) == Type.pointer(Type('int'))

@assert_compilation_succeeds()
def test_match_variable_named_value_ok():
    from tmppy import Type, match
    def f(b: bool):
        return match(Type('int'))(lambda value: {
            value:
                15,
        })
    assert f(True) == 15

@assert_compilation_succeeds()
def test_match_variable_named_error_in_match_returning_type_ok():
    from tmppy import Type, match
    def f(b: bool):
        return match(Type('int'))(lambda error: {
            error:
                Type.pointer(error),
        })
    assert f(True) == Type.pointer(Type('int'))

@assert_compilation_succeeds()
def test_match_variable_named_error_in_match_returning_value_ok():
    from tmppy import Type, match
    def f(b: bool):
        return match(Type('int'))(lambda error: {
            error:
                15,
        })
    assert f(True) == 15

if __name__== '__main__':
    main()
