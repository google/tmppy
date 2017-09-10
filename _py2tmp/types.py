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

from enum import Enum
from typing import List

class ExprKind(Enum):
    BOOL = 1
    TYPE = 2
    TEMPLATE = 3

class ExprType:
    def __init__(self, kind: ExprKind):
        self.kind = kind

    def __str__(self) -> str: ... # pragma: no cover

    def __eq__(self, other) -> bool: ... # pragma: no cover

class BoolType(ExprType):
    def __init__(self):
        super().__init__(kind=ExprKind.BOOL)

    def __str__(self):
        return 'bool'

    def __eq__(self, other):
        return isinstance(other, BoolType)

class TypeType(ExprType):
    def __init__(self):
        super().__init__(kind=ExprKind.TYPE)

    def __str__(self):
        return 'Type'

    def __eq__(self, other):
        return isinstance(other, TypeType)

class FunctionType(ExprType):
    def __init__(self, argtypes: List[ExprType], returns: ExprType):
        super().__init__(kind=ExprKind.TEMPLATE)
        self.argtypes = argtypes
        self.returns = returns

    def __str__(self):
        return "(%s) -> %s" % (
            ', '.join(str(arg)
                      for arg in self.argtypes),
            str(self.returns))

    def __eq__(self, other):
        return isinstance(other, FunctionType) and self.__dict__ == other.__dict__

class ListType(ExprType):
    def __init__(self, elem_type: ExprType):
        super().__init__(kind=ExprKind.TYPE)
        assert elem_type.kind != ExprKind.TEMPLATE
        self.elem_type = elem_type

    def __str__(self):
        return "List[%s]" % str(self.elem_type)

    def __eq__(self, other):
        return isinstance(other, ListType) and self.__dict__ == other.__dict__
