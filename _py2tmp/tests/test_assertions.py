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
    def f(x: Type):
        return x
    assert f(Type('int')) == Type('int')

@assert_compilation_fails_with_generic_error('error: static assertion failed: TMPPy assertion failed:')
def test_simple_assertion_error():
    from tmppy import Type
    def f(x: Type):
        return x
    assert f(Type('int')) == Type('float')
