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
def test_type_literal_success():
    from tmppy import Type
    assert Type('int') == Type('int')

@assert_conversion_fails
def test_type_literal_no_arguments_error():
    from tmppy import Type
    def f(x: bool):
        return Type()  # error: Type\(\) takes 1 argument. Got: 0

@assert_conversion_fails
def test_type_literal_too_many_arguments_error():
    from tmppy import Type
    def f(x: bool):
        return Type('', '')  # error: Type\(\) takes 1 argument. Got: 2

@assert_conversion_fails
def test_type_literal_argument_with_wrong_type_error():
    from tmppy import Type
    def f(x: bool):
        return Type(x)  # error: The first argument to Type should be a string constant.

@assert_conversion_fails
def test_type_literal_keyword_argument_error():
    from tmppy import Type
    def f(x: bool):
        return Type('int', x=x) # error: Keyword arguments are not supported.
