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

@assert_compilation_succeeds()
def test_exception_raised_and_caught_success():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong'
            self.b = b
            self.x = x
    def f(b: bool):
        if b:
            raise MyError(b, Type.pointer(Type('int')))
        return Type('float')
    def g(b: bool):
        try:
            x = f(b)
            return x
        except MyError as e:
            assert e.b == b
            assert e.x == Type.pointer(Type('int'))
            return Type('double')
    assert g(True) == Type('double')

@assert_compilation_succeeds()
def test_exception_raised_and_caught_same_block_success():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong'
            self.b = b
            self.x = x
    def f(b: bool):
        try:
            raise MyError(b, Type.pointer(Type('int')))
        except MyError as e:
            assert e.b == b
            assert e.x == Type.pointer(Type('int'))
            return Type('double')
    assert f(True) == Type('double')

@assert_compilation_fails_with_static_assert_error('Something went wrong 1')
def test_catch_does_not_catch_other_exception():
    from tmppy import Type
    class MyError1(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong 1'
            self.b = b
            self.x = x
    class MyError2(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong 2'
            self.b = b
            self.x = x
    def f(b: bool):
        if b:
            raise MyError1(b, Type.pointer(Type('int')))
        return Type('float')
    def g(b: bool):
        try:
            x = f(b)
            return x
        except MyError2 as e:
            assert e.b == b
            assert e.x == Type.pointer(Type('int'))
            return Type('double')
    assert g(True) == Type('double')

@assert_compilation_fails_with_static_assert_error('Something went wrong 1')
def test_catch_does_not_catch_other_exception_same_block():
    from tmppy import Type
    class MyError1(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong 1'
            self.b = b
            self.x = x
    class MyError2(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong 2'
            self.b = b
            self.x = x
    def f(b: bool):
        try:
            raise MyError1(b, Type.pointer(Type('int')))
        except MyError2 as e:
            assert e.b == b
            assert e.x == Type.pointer(Type('int'))
            return Type('double')
    assert f(True) == Type('double')

# TODO: add support for this.
@assert_conversion_fails
def test_exception_type_with_no_args_error():
    class MyError(Exception):
        def __init__(self):  # error: Custom types must have at least 1 constructor argument \(and field\).
            self.message = 'Something went wrong'

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_exception_raised_and_not_caught_error():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong'
            self.b = b
            self.x = x
    def f(b: bool) -> bool:
        raise MyError(b, Type.pointer(Type('int')))
    assert f(True)

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_exception_raised_and_not_caught_with_branch_error():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong'
            self.b = b
            self.x = x
    def f(b: bool):
        if b:
            raise MyError(b, Type.pointer(Type('int')))
        return 1
    assert f(True) == 15

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_exception_raised_and_not_caught_from_another_function_error():
    from tmppy import Type
    class MyError(Exception):
        def __init__(self, b: bool, x: Type):
            self.message = 'Something went wrong'
            self.b = b
            self.x = x
    def f(b: bool) -> bool:
        raise MyError(b, Type.pointer(Type('int')))
    def g(b: bool) -> bool:
        return f(b)
    assert g(True)

@assert_compilation_succeeds()
def test_function_that_always_raises_an_exception_no_type_annotation_ok():
    class MyError(Exception):
        def __init__(self, x: bool):
            self.message = 'Something went wrong'
            self.x = x
    def f(b: bool):
        raise MyError(True)
    def g(b: bool):
        try:
            _ = f(True)
            return False
        except MyError as e:
            return e.x
    assert g(True)

@assert_compilation_succeeds()
def test_function_that_always_raises_an_exception_with_type_annotation_ok():
    class MyError(Exception):
        def __init__(self, x: bool):
            self.message = 'Something went wrong'
            self.x = x
    def f(b: bool) -> int:
        raise MyError(True)
    def g(b: bool):
        try:
            _ = f(True)
            return False
        except MyError as e:
            return e.x
    assert g(True)

@assert_compilation_succeeds()
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

@assert_compilation_succeeds()
def test_var_defined_in_try_and_except_used_after_ok():
    class MyError(Exception):
        def __init__(self, x: bool):
            self.message = 'Something went wrong'
            self.x = x
    def f(b: bool):
        try:
            x = True
        except MyError as e:
            x = False
        return x
    assert f(True)

@assert_compilation_succeeds()
def test_var_defined_in_try_except_always_returns_used_after_ok():
    class MyError(Exception):
        def __init__(self, x: bool):
            self.message = 'Something went wrong'
            self.x = x
    def f(b: bool):
        try:
            x = True
        except MyError as e:
            return False
        return x
    assert f(True)

@assert_compilation_succeeds()
def test_var_defined_in_except_try_always_returns_used_after_ok():
    class MyError(Exception):
        def __init__(self, x: bool):
            self.message = 'Something went wrong'
            self.x = x
    def f(b: bool):
        try:
            return True
        except MyError as e:
            x = False
        return x
    assert f(True)

@assert_conversion_fails
def test_raise_from_error():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        raise MyError(True) from 1  # error: "raise ... from ..." is not supported. Use a plain "raise ..." instead.

@assert_conversion_fails
def test_raise_custom_type_not_exception_error():
    @dataclass
    class MyType:  # note: The type MyType was defined here.
        b: bool
    def f(b: bool):
        raise MyType(True)  # error: Can't raise an exception of type "MyType", because it's not a subclass of Exception.

@assert_conversion_fails
def test_raise_not_custom_type_error():
    from tmppy import Type
    def f(b: bool):
        raise Type('int')  # error: Can't raise an exception of type "Type", because it's not a subclass of Exception.

@assert_conversion_fails
def test_try_except_in_if_error():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        if True:
            try:  # error: try-except blocks are only supported at top-level in functions \(not e.g. inside if-else statements\).
                return 1
            except MyError as e:
                return 1
        return 1

@assert_conversion_fails
def test_try_except_in_else_error():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        if True:
            return 1
        else:
            try:  # error: try-except blocks are only supported at top-level in functions \(not e.g. inside if-else statements\).
                return 1
            except MyError as e:
                return 1

@assert_conversion_fails
def test_try_except_in_try_error():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            try:  # error: try-except blocks are only supported at top-level in functions \(not e.g. inside if-else statements\).
                return 1
            except MyError as e:
                return 1
        except MyError as e:
            return 1

@assert_conversion_fails
def test_try_except_in_except_error():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            return 1
        except MyError as e:
            try:  # error: try-except blocks are only supported at top-level in functions \(not e.g. inside if-else statements\).
                return 1
            except MyError as e:
                return 1

@assert_compilation_succeeds()
def test_try_except_after_if_ok():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        if b:
            return 1
        try:
            x = 2
        except MyError as e:
            x = 3
        return x
    assert f(False) == 2

@assert_conversion_fails
def test_try_with_no_except_error():
    def f(b: bool):
        try:  # error: "try" blocks must have an "except" clause.
            return 1
        finally:
            pass

@assert_conversion_fails
def test_try_with_multiple_excepts_error():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    class OtherError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something else went wrong'
            self.b = b
    def f(b: bool):
        try:
            return 1
        except MyError as e:
            return 2
        except OtherError as e:  # error: "try" blocks with multiple "except" clauses are not currently supported.
            return 3

@assert_conversion_fails
def test_try_except_with_no_exception_type():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            return 1
        except:  # error: "except" clauses must be of the form: except SomeType as some_var
            return 2

@assert_conversion_fails
def test_try_except_with_no_specific_exception_type():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            return 1
        except Exception as e:  # error: Catching all exceptions is not supported, you must catch a specific exception type.
            return 2

@assert_conversion_fails
def test_try_except_with_no_as():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            return 1
        except MyError:  # error: "except" clauses must be of the form: except SomeType as some_var
            return 2

@assert_conversion_fails
def test_try_except_with_finally_error():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            return 1
        except MyError as e:
            return 2
        finally:
            return 3  # error: "finally" clauses are not supported.

@assert_conversion_fails
def test_try_except_with_else_error():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            return 1
        except MyError as e:
            return 2
        else:
            return 3  # error: "else" clauses are not supported in try-except.

@assert_conversion_fails
def test_type_with_multiple_base_classes_error():
    class MyError(Exception, int):  # error: Multiple base classes are not supported.
        def __init__(self, b: bool):
            self.b = b

@assert_conversion_fails
def test_exception_type_with_no_message_error():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.b = b  # error: Unexpected statement. The first statement in the constructor of an exception class must be of the form: self.message = '...'.

@assert_compilation_succeeds()
def test_try_except_followed_by_stmts_with_no_free_vars():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            raise MyError(True)
        except MyError as e:
            x = 1
        return 2
    assert f(True) == 2

@assert_compilation_succeeds()
def test_try_except_where_try_maybe_returns():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            if b:
                return 1
        except MyError as e:
            return 2
        return 3
    assert f(True) == 1
    assert f(False) == 3

@assert_compilation_succeeds()
def test_try_except_where_try_maybe_throws():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            if b:
                raise MyError(True)
        except MyError as e:
            return 1
        return 2
    assert f(True) == 1
    assert f(False) == 2

@assert_compilation_succeeds()
def test_try_except_where_except_maybe_returns():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b: bool):
        try:
            raise MyError(b)
        except MyError as e:
            if e.b:
                return 1
        return 2
    assert f(True) == 1
    assert f(False) == 2

@assert_compilation_succeeds()
def test_try_except_where_except_maybe_throws():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def g(b: bool):
        try:
            raise MyError(b)
        except MyError as e:
            if e.b:
                raise e
        return 2
    def f(b: bool):
        try:
            return g(b)
        except MyError as e:
            return 1
    assert f(True) == 1
    assert f(False) == 2

@assert_compilation_succeeds()
def test_try_except_where_both_try_and_except_maybe_return():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def f(b1: bool, b2: bool):
        try:
            if b1:
                raise MyError(b2)
        except MyError as e:
            if e.b:
                return 1
        return 2
    assert f(True, True) == 1
    assert f(True, False) == 2
    assert f(False, True) == 2
    assert f(False, False) == 2

@assert_compilation_succeeds()
def test_try_except_where_both_try_and_except_maybe_throw():
    class MyError(Exception):
        def __init__(self, b: bool):
            self.message = 'Something went wrong'
            self.b = b
    def g(b1: bool, b2: bool):
        try:
            if b1:
                raise MyError(b2)
        except MyError as e:
            if e.b:
                raise e
        return 1
    def f(b1: bool, b2: bool):
        try:
            return g(b1, b2)
        except MyError as e:
            return 2
    assert f(True, True) == 2
    assert f(True, False) == 1
    assert f(False, True) == 1
    assert f(False, False) == 1

if __name__== '__main__':
    main()
