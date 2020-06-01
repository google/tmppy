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

from py2tmp.testing import main, assert_compilation_succeeds, assert_compilation_fails_with_generic_error, assert_compilation_fails_with_static_assert_error
from py2tmp.testing.pytest_plugin import TmppyFixture


@assert_compilation_succeeds()
def test_f_success(tmppy: TmppyFixture):
    from tmppy import Type
    from extras.examples.example import f
    assert f(Type('int'))

@assert_compilation_fails_with_generic_error('The expected error')
def test_example_assert_failure(tmppy: TmppyFixture):
    from tmppy import Type
    assert Type('int') == Type('float'), 'The expected error'

@assert_compilation_fails_with_static_assert_error('Something went wrong')
def test_example_uncaught_exception(tmppy: TmppyFixture):
    class MyError(Exception):
        def __init__(self, n: int):
            self.message = 'Something went wrong'
            self.n = n
    def f(n: int) -> int:
        raise MyError(n)
    assert f(1) == 0

if __name__== '__main__':
    main()
