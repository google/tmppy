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
import dataclasses
from typing import Optional, Iterator, Tuple

from _py2tmp.ir0 import ir, Transformation


class RemoveNoOpStmtsTransformation(Transformation):
    def __init__(self, identifier_generator: Optional[Iterator[str]]):
        super().__init__(identifier_generator=identifier_generator)

    def transform_header(self, header: ir.Header) -> ir.Header:
        header = super().transform_header(header)
        return dataclasses.replace(header,
                                   toplevel_content=self.transform_template_body_elems(header.toplevel_content))

    def transform_template_body_elems(self,
                                      elems: Tuple[ir.TemplateBodyElement, ...]) -> Tuple[ir.TemplateBodyElement, ...]:
        return tuple(elem for elem in elems if not isinstance(elem, ir.NoOpStmt))
