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

class ValueType:
    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def _key(self):
        return tuple(sorted(self.__dict__.items()))

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self._key())

    def __repr__(self):
        return self.__str__()
