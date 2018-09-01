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
def test_import_unsupported_module():
    from os import path  # error: The only modules that can be imported in TMPPy are: tmppy, typing

@assert_conversion_fails
def test_import_unsupported_symbol():
    from typing import MutableSequence  # error: The only supported imports from typing are: Callable, List, Set.

@assert_conversion_fails
def test_import_module_as_alias_error():
    import typing as x  # error: TMPPy only supports imports of the form "from some_module import some_symbol, some_other_symbol".

@assert_conversion_fails
def test_import_symbol_as_alias_error():
    from typing import Type as x  # error: TMPPy only supports imports of the form "from some_module import some_symbol, some_other_symbol".

@assert_compilation_succeeds()
def test_import_multiple_ok():
    from typing import List, Callable
