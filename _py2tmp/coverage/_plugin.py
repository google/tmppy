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
from types import FrameType, ModuleType
from typing import Set, Optional, Union, Any

from coverage import CoveragePlugin, FileTracer, Coverage
from coverage.parser import PythonParser
from coverage.plugin_support import Plugins
from coverage.python import PythonFileReporter

from _py2tmp.coverage import SourceBranch
from _py2tmp.coverage._is_enabled import set_coverage_collection_enabled


class TmppyCoveragePlugin(CoveragePlugin):
    def _is_hooks_file(self, filename: str):
        set_coverage_collection_enabled()
        return filename.endswith('_py2tmp/coverage/_hooks.py')

    def file_tracer(self, filename: str):
        if not self._is_hooks_file(filename):
            return None
        return TmppyFileTracer()

    def file_reporter(self, filename: str):
        if not self._is_hooks_file(filename):
            return None
        return TmppyFileReporter

class TmppyFileTracer(FileTracer):
    def has_dynamic_source_filename(self) -> bool:
        return True

    def _extract_branch(self, frame: FrameType):
        branch = frame.f_locals['branch']
        assert isinstance(branch, SourceBranch)
        return branch

    def dynamic_source_filename(self, filename: str, frame: FrameType):
        branch = self._extract_branch(frame)
        return branch.file_name

    def line_number_range(self, frame: FrameType):
        branch = self._extract_branch(frame)
        if branch.source_line > 0:
            return branch.source_line, branch.source_line
        else:
            return -1, -1

class _FakeByteParser:
    def __init__(self, num_lines: int):
        self.num_lines = num_lines

    def _find_statements(self) -> Set[int]:
        return set(range(self.num_lines))

def _extract_all_branches(python_source: str):
    parser = PythonParser(text=python_source)
    # This is a hack to force-disable Python optimization, otherwise Python will optimize away statements like
    # "if False: ..." and that would cause unexpected diffs in the coverage branches. Even when passing optimize=0 to
    # compile().
    parser._byte_parser = _FakeByteParser(num_lines=len(python_source.splitlines())+1)
    parser.parse_source()
    return parser.arcs()

class TmppyFileReporter(PythonFileReporter):
    def __init__(self, morf: Union[ModuleType, str], coverage: Optional[Coverage]=None):
        super().__init__(morf=morf, coverage=coverage)

    def __repr__(self) -> str:
        return "<TmppyFileReporter {0!r}>".format(self.filename)

    @property
    def parser(self) -> 'TmppyParser':
        """Lazily create a :class:`TmppyParser`."""
        if self._parser is None:
            self._parser = TmppyParser(
                filename=self.filename,
                exclude=self.coverage._exclude_regex('exclude'),
            )
            self._parser.parse_source()
        return self._parser

class TmppyParser(PythonParser):
    @property
    def byte_parser(self) -> _FakeByteParser:
        """Create a ByteParser on demand."""
        if not self._byte_parser:
            # We override the real byte parser with this fake so that we can report coverage on lines that Python
            # would optimize out in bytecode (e.g. "if False: ...")
            self._byte_parser = _FakeByteParser(len(self.lines) + 1)
        return self._byte_parser

def coverage_init(reg: Plugins, options: Any):
    reg.add_file_tracer(TmppyCoveragePlugin())
