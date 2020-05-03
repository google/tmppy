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

from _py2tmp.compiler.testing import main, assert_compilation_succeeds, assert_compilation_fails_with_static_assert_error, assert_conversion_fails, assert_compilation_fails_with_generic_error

@assert_compilation_succeeds()
def test_simple_assertion():
    from tmppy import Type
    assert Type('int') == Type('int')

@assert_compilation_succeeds()
def test_assertion_in_function():
    from tmppy import Type
    def f(x: bool):
        assert Type('int') == Type('int')
        return x
    assert f(True) == True

@assert_compilation_succeeds()
def test_assertion_with_function_call_in_function():
    from tmppy import Type
    def f(x: Type):
        return x
    def g(x: bool):
        assert f(Type('int')) == Type('int')
        return x
    assert g(True) == True

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_simple_assertion_error():
    from tmppy import Type
    assert Type('int') == Type('float')

@assert_compilation_fails_with_generic_error('The expected error')
def test_simple_assertion_error_custom_message():
    from tmppy import Type
    assert Type('int') == Type('float'), 'The expected error'

@assert_compilation_succeeds()
def test_unconditional_false_assertion_bool_param_function_never_called_ok():
    def f(x: bool):
        assert False == True
        return x

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_unconditional_false_assertion_bool_param_function_called_error():
    def f(x: bool):
        assert False == True
        return x
    assert f(True) == True

@assert_compilation_succeeds()
def test_unconditional_true_assertion_bool_param_function_called_ok():
    def f(x: bool):
        assert False == False
        return x
    assert f(True) == True

@assert_compilation_succeeds()
def test_unconditional_false_assertion_int_param_function_never_called_ok():
    def f(x: int):
        assert False == True
        return x

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_unconditional_false_assertion_int_param_function_called_error():
    def f(x: int):
        assert False == True
        return x
    assert f(15) == 15

@assert_compilation_succeeds()
def test_unconditional_true_assertion_int_param_function_called_ok():
    def f(x: int):
        assert False == False
        return x
    assert f(15) == 15

@assert_compilation_succeeds()
def test_unconditional_false_assertion_type_param_function_never_called_ok():
    from tmppy import Type
    def f(x: Type):
        assert False == True
        return x

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_unconditional_false_assertion_type_param_function_called_error():
    from tmppy import Type
    def f(x: Type):
        assert False == True
        return x
    assert f(Type('int')) == Type('int')

@assert_compilation_succeeds()
def test_unconditional_true_assertion_type_param_function_called_ok():
    from tmppy import Type
    def f(x: Type):
        assert False == False
        return x
    assert f(Type('int')) == Type('int')

@assert_compilation_succeeds()
def test_unconditional_false_assertion_function_param_function_never_called_ok():
    from typing import Callable
    def f(x: Callable[[bool], bool]):
        assert False == True
        return True

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_unconditional_false_assertion_function_param_function_called_error():
    from typing import Callable
    def f(x: Callable[[bool], bool]):
        assert False == True
        return True
    def g(x: bool):
        return x
    assert f(g) == True

@assert_compilation_succeeds()
def test_unconditional_true_assertion_function_param_function_called_ok():
    from typing import Callable
    def f(x: Callable[[bool], bool]):
        assert False == False
        return True
    def g(x: bool):
        return x
    assert f(g) == True


@assert_compilation_succeeds()
def test_assert_false_in_function_call_with_constant_args_never_called_bool_bool_ok():
    def f(x: bool):
        assert False
        return True
    def g(x: bool):
        return f(True)

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_assert_false_in_function_call_with_constant_args_called_bool_bool_error():
    def f(x: bool):
        assert False
        return True
    def g(x: bool):
        return f(True)
    assert g(True)


@assert_compilation_succeeds()
def test_assert_false_in_function_call_with_constant_args_never_called_bool_int_ok():
    def f(x: bool):
        assert False
        return True
    def g(x: int):
        return f(True)

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_assert_false_in_function_call_with_constant_args_called_bool_int_error():
    def f(x: bool):
        assert False
        return True
    def g(x: int):
        return f(True)
    assert g(1)

@assert_compilation_succeeds()
def test_assert_false_in_function_call_with_constant_args_never_called_bool_type_ok():
    from tmppy import Type
    def f(x: bool):
        assert False
        return True
    def g(x: Type):
        return f(True)

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_assert_false_in_function_call_with_constant_args_called_bool_type_error():
    from tmppy import Type
    def f(x: bool):
        assert False
        return True
    def g(x: Type):
        return f(True)
    assert g(Type('float'))

@assert_compilation_succeeds()
def test_assert_false_in_function_call_with_constant_args_never_called_int_bool_ok():
    def f(x: int):
        assert False
        return True
    def g(x: bool):
        return f(1)

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_assert_false_in_function_call_with_constant_args_called_int_bool_error():
    def f(x: int):
        assert False
        return True
    def g(x: bool):
        return f(1)
    assert g(True)


@assert_compilation_succeeds()
def test_assert_false_in_function_call_with_constant_args_never_called_int_int_ok():
    def f(x: int):
        assert False
        return True
    def g(x: int):
        return f(1)

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_assert_false_in_function_call_with_constant_args_called_int_int_error():
    def f(x: int):
        assert False
        return True
    def g(x: int):
        return f(1)
    assert g(1)

@assert_compilation_succeeds()
def test_assert_false_in_function_call_with_constant_args_never_called_int_type_ok():
    from tmppy import Type
    def f(x: int):
        assert False
        return True
    def g(x: Type):
        return f(1)

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_assert_false_in_function_call_with_constant_args_called_int_type_error():
    from tmppy import Type
    def f(x: int):
        assert False
        return True
    def g(x: Type):
        return f(1)
    assert g(Type('float'))

@assert_compilation_succeeds()
def test_assert_false_in_function_call_with_constant_args_never_called_type_bool_ok():
    from tmppy import Type
    def f(x: Type):
        assert False
        return True
    def g(x: bool):
        return f(Type('double'))

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_assert_false_in_function_call_with_constant_args_called_type_bool_error():
    from tmppy import Type
    def f(x: Type):
        assert False
        return True
    def g(x: bool):
        return f(Type('double'))
    assert g(True)

@assert_compilation_succeeds()
def test_assert_false_in_function_call_with_constant_args_never_called_type_int_ok():
    from tmppy import Type
    def f(x: Type):
        assert False
        return True
    def g(x: int):
        return f(Type('double'))

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_assert_false_in_function_call_with_constant_args_called_type_int_error():
    from tmppy import Type
    def f(x: Type):
        assert False
        return True
    def g(x: int):
        return f(Type('double'))
    assert g(1)

@assert_compilation_succeeds()
def test_assert_false_in_function_call_with_constant_args_never_called_type_type_ok():
    from tmppy import Type
    def f(x: Type):
        assert False
        return True
    def g(x: Type):
        return f(Type('double'))

@assert_compilation_fails_with_static_assert_error('TMPPy assertion failed:')
def test_assert_false_in_function_call_with_constant_args_called_type_type_error():
    from tmppy import Type
    def f(x: Type):
        assert False
        return True
    def g(x: Type):
        return f(Type('double'))
    assert g(Type('float'))

@assert_conversion_fails
def test_assert_expression_wrong_type():
    assert 1  # error: The value passed to assert must have type bool, but got a value with type int.

if __name__== '__main__':
    main()
