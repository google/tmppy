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

import typing
from typing import TypeVar, Callable, Dict, Any, List

class Type:
    def __init__(self, s, **kwargs: 'Type'):
        self.s = s

    def __str__(self):
        return "Type(%s)" % self.s

    def matches(self, str) -> 'typing.List[Type]': ...

    def __getattr__(self, item) -> 'Type': ...

class TypePattern():
    def __init__(self, *p: str, **kwargs):
        pass

T = TypeVar('T')

def match(arg: Type, *args: Type) -> Callable[[Dict[TypePattern, Callable[Any, T]]], T]: ...
