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

@assert_conversion_fails
def test_global_variable_error():
    x = 1  # error: This Python construct is not supported in TMPPy

@assert_conversion_fails
def test_reference_to_undefined_identifier_error():
    '''
    def f(x: bool):
        return undefined_identifier  # error: Reference to undefined variable/function
    '''

@assert_conversion_fails
def test_unsupported_statement_error():
    def f(x: bool):
        for y in [x]:  # error: Unsupported statement.
            return y

@assert_compilation_succeeds()
def test_add_pointer_multiple_example():
    from tmppy import Type
    def add_pointer_multiple(t: Type, n: int) -> Type:
        if n == 0:
            return t
        else:
            return add_pointer_multiple(Type.pointer(t), n-1)
    assert add_pointer_multiple(Type('int'), 0) == Type('int')
    assert add_pointer_multiple(Type('int'), 2) == Type.pointer(Type.pointer(Type('int')))
    assert add_pointer_multiple(Type.pointer(Type('int')), 2) == Type.pointer(Type.pointer(Type.pointer(Type('int'))))
