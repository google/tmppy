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

from typing import Callable, Dict, Any, List, Union, Tuple

class Type:
    def __init__(self, atomic_type: str): ...

    @staticmethod
    def pointer(other: 'Type') -> 'Type': ...

    @staticmethod
    def reference(other: 'Type') -> 'Type': ...

    @staticmethod
    def rvalue_reference(other: 'Type') -> 'Type': ...

    @staticmethod
    def const(other: 'Type') -> 'Type': ...

    # E.g. Type.function(Type('int'), [Type('float')]) constructs the type 'int(float)'
    @staticmethod
    def function(return_type: 'Type', args: List['Type']) -> 'Type': ...

    # E.g. Type.array(Type('int')) constructs the type 'int[]'
    @staticmethod
    def array(elem_type: 'Type') -> 'Type': ...

    @staticmethod
    def template_instantiation(template_atomic_type: str, args: List['Type']) -> 'Type': ...

    # E.g. Type.template_member(Type('foo'), 'bar', [Type('int')]) constructs the type 'foo::bar<int>'.
    @staticmethod
    def template_member(type: 'Type', member_name: str, args: List['Type']) -> 'Type': ...

    # E.g. Type('foo').bar is the type 'foo::bar'.
    def __getattr__(self, member_name: str) -> 'Type': ...

def match(*types: Type) -> Callable[[Any, ...], Dict[Union[Type, Tuple[Type, ...]], Type]]: ...
