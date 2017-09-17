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
