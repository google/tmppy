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
def test_identity():
    def f(x: bool):
        return x
    assert f(True) == True

@assert_compilation_succeeds()
def test_function_call_returning_bool():
    def f(x: bool):
        return x
    def g(the_argument: bool):
        return f(f(the_argument))
    assert g(True) == True

@assert_compilation_succeeds()
def test_function_call_returning_int():
    def f(x: int):
        return x
    def g(the_argument: int):
        return f(f(the_argument))
    assert g(3) == 3

@assert_compilation_succeeds()
def test_function_call_returning_type():
    from tmppy import Type
    def f(x: Type):
        return x
    def g(x: Type):
        return f(f(x))
    assert g(Type('int')) == Type('int')

@assert_compilation_succeeds()
def test_function_call_returning_list():
    from tmppy import Type
    from typing import List
    def f(x: List[Type]):
        return x
    def g(x: List[Type]):
        return f(f(x))
    assert g([Type('int'), Type('float')]) == [Type('int'), Type('float')]

@assert_compilation_succeeds()
def test_function_call_returning_set():
    from tmppy import Type
    from typing import Set
    def f(x: Set[Type]):
        return x
    def g(x: Set[Type]):
        return f(f(x))
    assert g({Type('int'), Type('float')}) == {Type('int'), Type('float')}

@assert_compilation_succeeds()
def test_type_function_passed_as_argument():
    from tmppy import Type
    from typing import List
    from typing import Callable

    def f(x: Type, y: Type):
        return [x, y]
    def g(x: Callable[[Type, Type], List[Type]], y: Type):
        return x(y, y)
    def h(x: Type):
        return g(f, x)
    assert h(Type('int')) == [Type('int'), Type('int')]

@assert_compilation_succeeds()
def test_type_function_passed_as_only_argument():
    from tmppy import Type
    from typing import List
    from typing import Callable

    def f(x: Type, y: Type):
        return [x, y]
    def g(x: Callable[[Type, Type], List[Type]]):
        return x(Type('int'), Type('int'))
    assert g(f) == [Type('int'), Type('int')]

@assert_compilation_succeeds()
def test_bool_function_passed_as_argument():
    from typing import List
    from typing import Callable

    def f(x: bool, y: bool):
        return [x, y]
    def g(x: Callable[[bool, bool], List[bool]], y: bool):
        return x(y, y)
    def h(x: bool):
        return g(f, x)
    assert h(True) == [True, True]

@assert_conversion_fails
def test_function_redefined_with_same_type_error():
    def f(x: bool, y: bool):  # note: The previous declaration was here.
        return x
    def f(x: bool, y: bool):  # error: f was already defined in this scope.
        return y

@assert_conversion_fails
def test_function_redefined_with_different_type_error():
    def f(x: bool):  # note: The previous declaration was here.
        return x
    def f(x: bool, y:bool):  # error: f was already defined in this scope.
        return x

@assert_conversion_fails
def test_function_param_shadows_function_error():
    def f(x: bool):  # note: The previous declaration was here.
        return x
    def g(f: bool):  # error: f was already defined in this scope.
        return f
    assert g(True) == True

@assert_conversion_fails
def test_multiple_parameters_with_same_name_error():
    '''
    def f(x: bool,  # note: The previous declaration was here.
          x: bool):  # error: x was already defined in this scope.
        return undefined_identifier
    '''

@assert_conversion_fails
def test_function_argument_with_type_comment_error():
    def f(x  # type: bool  # error: All function arguments must have a type annotation. Note that type comments are not supported.
          ):
        return x

@assert_conversion_fails
def test_function_argument_with_no_type_annotation_error():
    def f(x):  # error: All function arguments must have a type annotation.
        return x

@assert_conversion_fails
def test_function_no_arguments_error():
    def f():  # error: Functions with no arguments are not supported.
        return []

@assert_conversion_fails
def test_function_varargs_error():
    def f(x: bool, *args):  # error: Function vararg arguments are not supported.
        return []

@assert_conversion_fails
def test_function_kwargs_error():
    def f(x: bool, **kwargs):  # error: Keyword function arguments are not supported.
        return []

@assert_conversion_fails
def test_function_keyword_only_args_error():
    def f(x: bool, *, y: bool):  # error: Keyword-only function arguments are not supported.
        return x

@assert_conversion_fails
def test_function_default_argument_error():
    def f(x: bool = True):  # error: Default values for function arguments are not supported.
        return x

@assert_conversion_fails
def test_function_decorator_error():
    @staticmethod
    def f(x: bool):  # error: Function decorators are not supported.
        return x

@assert_compilation_succeeds()
def test_function_return_type_declaration_success():
    def f(x: bool) -> bool:
        return x
    assert f(True) == True

@assert_conversion_fails
def test_function_return_type_declaration_mismatch_error():
    from tmppy import Type
    def f(x: bool) -> Type:  # error: f declared Type as return type, but the actual return type was bool.
        return x  # note: A bool was returned here

@assert_conversion_fails
def test_function_unreachable_statement_error():
    def f(x: bool):
        return x
        return x  # error: Unreachable statement.

@assert_conversion_fails
def test_function_unsupported_statement_error():
    def f(x: bool):
        y = True  # error: Missing return statement.

@assert_conversion_fails
def test_function_return_statement_with_no_value_error():
    def f(x: bool):
        return  # error: Return statements with no returned expression are not supported.

@assert_conversion_fails
def test_calling_bool_error():
    def f(x: bool):
        return x(x)  # error: Attempting to call an object that is not a function. It has type: bool

@assert_conversion_fails
def test_calling_list_error():
    def f(x: bool):
        y = [x]
        return y(x)  # error: Attempting to call an object that is not a function. It has type: List\[bool\]

@assert_conversion_fails
def test_calling_set_error():
    def f(x: bool):
        y = {x}
        return y(x)  # error: Attempting to call an object that is not a function. It has type: Set\[bool\]

@assert_conversion_fails
def test_calling_type_error():
    from tmppy import Type
    def f(x: bool):
        return Type('int')(x)  # error: Attempting to call an object that is not a function. It has type: Type

@assert_conversion_fails
def test_function_call_wrong_number_of_arguments():
    def f(x: bool):  # note: The definition of f was here
        return x
    def g(x: bool):
        return f(x, x)  # error: Argument number mismatch in function call to f: got 2 arguments, expected 1

@assert_conversion_fails
def test_function_call_wrong_argument_type():
    from tmppy import Type
    def f(  # note: The definition of f was here
            x: bool):
        return x
    def g(x: Type):  # note: The definition of x was here
        return f(x)  # error: Type mismatch for argument 0: expected type bool but was: Type

@assert_conversion_fails
def test_function_call_wrong_argument_type_expression():
    from tmppy import Type
    def f(  # note: The definition of f was here
            x: bool):
        return x
    def g(x: Type):
        return f([x])  # error: Type mismatch for argument 0: expected type bool but was: List\[Type\]

@assert_conversion_fails
def test_function_argument_call_wrong_number_of_arguments():
    from typing import Callable
    def g(f: Callable[[bool], bool],  # note: The definition of f was here
          x: bool):
        return f(x, x)  # error: Argument number mismatch in function call to f: got 2 arguments, expected 1

@assert_conversion_fails
def test_function_argument_call_wrong_argument_type():
    from tmppy import Type
    from typing import Callable
    def g(f: Callable[[bool], bool],  # note: The definition of f was here
          x: Type):  # note: The definition of x was here
        return f(x)  # error: Type mismatch for argument 0: expected type bool but was: Type

@assert_conversion_fails
def test_function_expression_call_wrong_number_of_arguments():
    from typing import Callable
    def g(f: Callable[[bool], Callable[[bool], bool]],
          x: bool):
        return f(True)(x, x)  # error: Argument number mismatch in function call: got 2 arguments, expected 1

@assert_conversion_fails
def test_function_expression_call_wrong_argument_type():
    from tmppy import Type
    from typing import Callable
    def g(f: Callable[[bool], Callable[[bool], bool]],
          x: Type):  # note: The definition of x was here
        return f(True)(x)  # error: Type mismatch for argument 0: expected type bool but was: Type

@assert_conversion_fails
def test_function_call_additional_and_missing_keyword_arguments():
    def f(foo: bool,  # note: The definition of f was here
          bar: bool):
        return foo
    def g(x: bool):
        return f(fooz=x, barz=x) # error: Incorrect arguments in call to f. Missing arguments: {bar, foo}. Specified arguments that don't exist: {barz, fooz}

@assert_conversion_fails
def test_function_call_additional_keyword_arguments():
    def f(foo: bool):  # note: The definition of f was here
        return foo
    def g(x: bool):
        return f(foo=x, bar=x, baz=x) # error: Incorrect arguments in call to f. Specified arguments that don't exist: {bar, baz}

@assert_conversion_fails
def test_function_call_missing_keyword_arguments():
    def f(foo: bool,  # note: The definition of f was here
          bar: bool,
          baz: bool):
        return foo
    def g(x: bool):
        return f(bar=x) # error: Incorrect arguments in call to f. Missing arguments: {baz, foo}

@assert_conversion_fails
def test_function_call_wrong_keyword_argument_type():
    from tmppy import Type
    def f(  # note: The definition of f was here
            x: bool):
        return x
    def g(x: Type):  # note: The definition of x was here
        return f(x=x) # error: Type mismatch for argument x: expected type bool but was: Type

@assert_conversion_fails
def test_function_call_wrong_keyword_argument_type_expression():
    from tmppy import Type
    def f(  # note: The definition of f was here
            x: bool):
        return x
    def g(x: Type):
        return f(x=[x])  # error: Type mismatch for argument x: expected type bool but was: List\[Type\]

@assert_conversion_fails
def test_function_argument_call_keyword_argument_error():
    from typing import Callable
    def g(f: Callable[[bool], bool],
          x: bool):
        return f(
            foo=x)  # error: Keyword arguments can only be used when calling a specific function or constructing a specific type, not when calling other callable objects. Please switch to non-keyword arguments.

@assert_conversion_fails
def test_function_expression_call_keyword_argument_error():
    from typing import Callable
    def g(f: Callable[[bool], Callable[[bool], bool]],
          x: bool):
        return f(True)(
            x=x) # error: Keyword arguments can only be used when calling a specific function or constructing a specific type, not when calling other callable objects. Please switch to non-keyword arguments.

@assert_compilation_succeeds()
def test_function_call_keyword_argument_success():
    from tmppy import Type
    from typing import List
    def f(foo: bool, bar: Type, baz: List[bool]):
        return foo
    def g(x: bool):
        return f(bar=Type('int'), foo=True, baz=[x])
    assert g(True) == True

@assert_conversion_fails
def test_function_call_keyword_and_non_keyword_arguments_error():
    from tmppy import Type
    from typing import List
    def f(foo: bool, bar: Type, baz: List[bool]):
        return foo
    def g(x: bool):
        return f(True, bar=Type('int'), baz=[x]) # error: Function calls with a mix of keyword and non-keyword arguments are not supported. Please choose either style.

@assert_compilation_succeeds()
def test_function_returning_function_returning_type_success():
    from tmppy import Type
    def f(x: Type):
        return x
    def g(b: bool):
        return f
    def h(x: Type):
        return g(True)(x)
    assert h(Type('int')) == Type('int')

@assert_compilation_succeeds()
def test_function_returning_function_returning_type_with_forward_success():
    from tmppy import Type
    def f(x: Type):
        return x
    def g(b: bool):
        return f
    def g2(b: bool):
        return g(b)
    def h(x: Type):
        return g2(True)(x)
    assert h(Type('int')) == Type('int')

@assert_compilation_succeeds()
def test_function_returning_function_returning_list_success():
    from tmppy import Type
    def f(x: bool):
        return [x]
    def g(b: Type):
        return f
    def h(x: Type):
        return g(x)(True)
    assert h(Type('int')) == [True]

@assert_compilation_succeeds()
def test_function_returning_function_returning_set_success():
    from tmppy import Type
    def f(x: bool):
        return {x}
    def g(b: Type):
        return f
    def h(x: Type):
        return g(x)(True)
    assert h(Type('int')) == {True}

@assert_compilation_succeeds()
def test_function_returning_function_returning_bool_ok():
    from tmppy import Type
    def f(x: bool):
        return x
    def g(b: Type):
        return f
    assert g(Type('int'))(True) == True

@assert_compilation_succeeds()
def test_function_returning_function_returning_int_ok():
    from tmppy import Type
    def f(x: int):
        return x
    def g(b: Type):
        return f
    assert g(Type('int'))(15) == 15

@assert_compilation_succeeds()
def test_function_returning_function_returning_function_ok():
    from tmppy import Type
    def f(x: Type):
        return x
    def g(b: Type):
        return f
    def h(b: Type):
        return g
    assert h(Type('int'))(Type('int'))(Type('bool')) == Type('bool')

@assert_compilation_succeeds()
def test_function_returning_function_returning_function__bool_args_ok():
    def f(b: bool):
        return b
    def g(b: bool):
        return f
    def h(b: bool):
        return g
    assert h(True)(True)(False) == False

@assert_compilation_succeeds()
def test_function_call_to_function_declared_after_with_return_type_decl_ok():
    def f(b: bool):
        return g(b)
    def g(b: bool) -> bool:
        return b
    assert f(True)

@assert_conversion_fails
def test_function_call_to_function_declared_after_without_type_decl_error():
    def f(b: bool):
        return g(b)  # error: Reference to a function whose return type hasn't been determined yet. Please add a return type declaration in g or move its declaration before its use.
    def g(b: bool):  # note: g was defined here
        return b

@assert_compilation_succeeds()
def test_recursive_function_call_with_return_type_decl_ok():
    def fact(n: int) -> int:
        if n == 0:
            return 1
        else:
            return n * fact(n - 1)
    assert fact(4) == 24

@assert_conversion_fails
def test_recursive_function_call_without_return_type_decl_error():
    def fact(n: int):  # note: fact was defined here
        if n == 0:
            return 1
        else:
            return n * fact(n - 1)  # error: Recursive function references are only allowed if the return type is declared explicitly.

@assert_compilation_succeeds()
def test_function_call_with_result_not_assigned():
    class MyError(Exception):
        def __init__(self, n: int):
            self.message = 'Something went wrong'
            self.n = n
    def f(b: bool):
        if True:
            raise MyError(42)
        return 4
    def g(b: bool):
        try:
            f(True)
        except MyError as e:
            return e.n
        return 5
    assert g(True) == 42

if __name__== '__main__':
    main()
