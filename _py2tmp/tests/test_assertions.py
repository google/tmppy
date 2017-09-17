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
def test_simple_assertion():
    from tmppy import Type
    assert Type('int') == Type('int')

@assert_compilation_fails_with_generic_error('error: static assertion failed: TMPPy assertion failed:')
def test_simple_assertion_error():
    from tmppy import Type
    assert Type('int') == Type('float')

@assert_compilation_fails_with_generic_error('The expected error')
def test_simple_assertion_error_custom_message():
    from tmppy import Type
    assert Type('int') == Type('float'), 'The expected error'

@assert_compilation_succeeds
def test_unconditional_false_assertion_bool_param_function_never_called_ok():
    def f(x: bool):
        assert False == True
        return x

@assert_compilation_fails_with_generic_error('error: static assertion failed: TMPPy assertion failed:')
def test_unconditional_false_assertion_bool_param_function_called_error():
    def f(x: bool):
        assert False == True
        return x
    assert f(True) == True

@assert_compilation_succeeds
def test_unconditional_true_assertion_bool_param_function_called_ok():
    def f(x: bool):
        assert False == False
        return x
    assert f(True) == True

@assert_compilation_succeeds
def test_unconditional_false_assertion_type_param_function_never_called_ok():
    from tmppy import Type
    def f(x: Type):
        assert False == True
        return x

@assert_compilation_fails_with_generic_error('error: static assertion failed: TMPPy assertion failed:')
def test_unconditional_false_assertion_type_param_function_called_error():
    from tmppy import Type
    def f(x: Type):
        assert False == True
        return x
    assert f(Type('int')) == Type('int')

@assert_compilation_succeeds
def test_unconditional_true_assertion_type_param_function_called_ok():
    from tmppy import Type
    def f(x: Type):
        assert False == False
        return x
    assert f(Type('int')) == Type('int')

@assert_conversion_fails_with_codegen_error('Unable to convert to C\+\+ an assertion in the function f because it\'s a constant expression and f only has functions as params.')
def test_unconditional_false_assertion_function_param_function_never_called_ok():
    from typing import Callable
    def f(x: Callable[[bool], bool]):
        assert False == True
        return True

@assert_conversion_fails_with_codegen_error('Unable to convert to C\+\+ an assertion in the function f because it\'s a constant expression and f only has functions as params.')
def test_unconditional_false_assertion_function_param_function_called_error():
    from typing import Callable
    def f(x: Callable[[bool], bool]):
        assert False == True
        return True
    def g(x: bool):
        return x
    assert f(g) == True

@assert_conversion_fails_with_codegen_error('Unable to convert to C\+\+ an assertion in the function f because it\'s a constant expression and f only has functions as params.')
def test_unconditional_true_assertion_function_param_function_called_ok():
    from typing import Callable
    def f(x: Callable[[bool], bool]):
        assert False == False
        return True
    def g(x: bool):
        return x
    assert f(g) == True
