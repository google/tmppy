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
from contextlib import contextmanager
from typing import Iterator


class Writer:
    def new_id(self) -> str: ...  # pragma: no cover

    def write_toplevel_elem(self, s: str): ...  # pragma: no cover

    def write_template_body_elem(self, s: str): ...  # pragma: no cover

    def create_child_writer(self) -> 'TemplateElemWriter': ...  # pragma: no cover

    @property
    def toplevel_writer(self) -> 'ToplevelWriter': ...  # pragma: no cover

class ToplevelWriter(Writer):
    def __init__(self, identifier_generator: Iterator[str]):
        self.identifier_generator = identifier_generator
        self.strings = []

    def new_id(self):
        return next(self.identifier_generator)

    def write_toplevel_elem(self, s: str):
        self.strings.append(s)

    def write_template_body_elem(self, s: str):
        self.write_toplevel_elem(s)

    def write_expr_fragment(self, s: str):
        self.write_toplevel_elem(s)

    def create_child_writer(self):
        return TemplateElemWriter(self)

    @property
    def toplevel_writer(self):
        return self

class TemplateElemWriter(Writer):
    def __init__(self, toplevel_writer: ToplevelWriter):
        self._toplevel_writer = toplevel_writer
        self.strings = []

    def new_id(self):
        return self.toplevel_writer.new_id()

    def write_toplevel_elem(self, s: str):
        self.toplevel_writer.write_toplevel_elem(s)

    def write_template_body_elem(self, s: str):
        self.strings.append(s)

    def write_expr_fragment(self, s: str):
        self.strings.append(s)

    def create_child_writer(self):
        return TemplateElemWriter(self.toplevel_writer)

    @property
    def toplevel_writer(self):
        return self._toplevel_writer

class ExprWriter(Writer):
    def __init__(self, parent_writer: Writer):
        self.parent_writer = parent_writer
        self.strings = []
        self.is_in_pattern = parent_writer.is_in_pattern if isinstance(parent_writer, ExprWriter) else False

    def new_id(self):
        return self.parent_writer.new_id()

    def write_toplevel_elem(self, s: str):
        self.parent_writer.write_toplevel_elem(s)

    def write_template_body_elem(self, s: str):
        self.parent_writer.write_template_body_elem(s)

    def write_expr_fragment(self, s: str):
        self.strings.append(s)

    def create_child_writer(self):
        raise NotImplementedError('This is not supported at the expression level')

    @property
    def toplevel_writer(self):
        return self.parent_writer.toplevel_writer

    @contextmanager
    def enter_pattern_context(self):
        self.is_in_pattern = True
        yield
        self.is_in_pattern = False
