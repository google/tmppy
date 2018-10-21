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

from typing import List

from tmppy import Type


def AlwaysFalseFromType(x: Type):
    return False

def BoolListAll(l: List[bool]):
    return l == [True for x in l]

def BoolListAny(l: List[bool]):
    return l != [False for x in l]

def IsInBoolList(b: bool, l: List[bool]):
    return any([b == x for x in l])

def IsInInt64List(n: int, l: List[int]):
    return any([n == x for x in l])

def IsInTypeList(x: Type, l: List[Type]):
    return any([x == y for y in l])

def AddToBoolSet(l: List[bool], b: bool):
    if b in l:
        return l
    else:
        return [b] + l

def AddToInt64Set(l: List[int], n: int):
    if n in l:
        return l
    else:
        return [n] + l

def AddToTypeSet(l: List[Type], x: Type):
    if x in l:
        return l
    else:
        return [x] + l

def BoolSetEquals(x: List[bool], y: List[bool]):
    return all([x1 in y for x1 in x]) and all([y1 in x for y1 in y])

def Int64SetEquals(x: List[int], y: List[int]):
    return all([x1 in y for x1 in x]) and all([y1 in x for y1 in y])

def TypeSetEquals(x: List[Type], y: List[Type]):
    return all([x1 in y for x1 in x]) and all([y1 in x for y1 in y])
