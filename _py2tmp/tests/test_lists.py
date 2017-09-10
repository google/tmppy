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
def test_empty_list_error():
    def f(x: bool):
        return []  # error: Empty lists are not currently supported.

@assert_conversion_fails
def test_list_expression_different_types_error():
    from tmppy import Type
    def f(x: bool):
        return [
            x,  # note: A previous list element with type bool was here.
            Type('int')  # error: Found different types in list elements, this is not supported. The type of this element was Type instead of bool
        ]

@assert_conversion_fails
def test_list_of_functions_error():
    def f(x: bool):
        return x
    def g(x: bool):
        return [  # error: Creating lists of functions is not supported. The elements of this list have type: \(bool\) -> bool
            f
        ]
