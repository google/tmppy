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
from dataclasses import dataclass
from typing import Any

import pytest

from _py2tmp.compiler.output_files import load_object_files, ObjectFileContent


def pytest_addoption(parser: Any):
    group = parser.getgroup("tmppy")
    group.addoption(
        "--tmppyc_files",
        action="store",
        dest="tmppyc_files",
        default="",
        help='*.tmppyc files used by tests (comma-separated list).',
    )
    parser.addini(
        name='tmppyc_files',
        help='*.tmppyc files used by tests (comma-separated list).',
        type='pathlist'
    )

@dataclass(frozen=True)
class TmppyFixture:
    tmppyc_files: ObjectFileContent

@pytest.fixture()
def tmppy(request) -> TmppyFixture:
    if request.config.getoption('tmppyc_files'):
        tmppyc_files = request.config.getoption('tmppyc_files').split(',')
    elif request.config.getini('tmppyc_files'):
        tmppyc_files = request.config.getini('tmppyc_files')
    else:
        raise ValueError('You must specify the *.tmppyc files needed by tests in tmppyc_files.')
    return TmppyFixture(load_object_files(tuple(tmppyc_files)))
