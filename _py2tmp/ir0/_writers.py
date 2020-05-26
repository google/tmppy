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

from typing import List, Union, Optional, Iterator

from _py2tmp.ir0 import ir


class Writer:
    def __init__(self):
        pass

    def write(self, elem: Union[ir.TemplateDefn, ir.TemplateBodyElement]): ...  # pragma: no cover

    def write_toplevel_elem(self, elem: Union[ir.TemplateDefn, ir.TemplateBodyElement]):
        self.toplevel_writer.write(elem)

    def new_constant_or_typedef(self, expr: ir.Expr, identifier_generator: Iterator[str]) -> ir.AtomicTypeLiteral:
        id = next(identifier_generator)
        if expr.expr_type.kind in (ir.ExprKind.BOOL, ir.ExprKind.INT64):
            self.write(ir.ConstantDef(name=id, expr=expr))
        elif expr.expr_type.kind in (ir.ExprKind.TYPE, ir.ExprKind.TEMPLATE):
            self.write(ir.Typedef(name=id, expr=expr))
        else:
            raise NotImplementedError('Unexpected kind: ' + str(expr.expr_type.kind))

        return ir.AtomicTypeLiteral.for_local(cpp_type=id, expr_type=expr.expr_type, is_variadic=False)

    @property
    def toplevel_writer(self) -> 'ToplevelWriter': ...  # pragma: no cover

class ToplevelWriter(Writer):
    def __init__(self,
                 allow_toplevel_elems: bool = True,
                 allow_template_defns: bool = True):
        super().__init__()
        self.template_defns: List[ir.TemplateDefn] = []
        self.toplevel_elems: List[Union[ir.StaticAssert, ir.ConstantDef, ir.Typedef]] = []
        self.allow_toplevel_elems = allow_toplevel_elems
        self.allow_template_defns = allow_template_defns

    def write(self, elem: Union[ir.StaticAssert, ir.ConstantDef, ir.Typedef]):
        if isinstance(elem, ir.TemplateDefn):
            assert self.allow_template_defns
            self.template_defns.append(elem)
        else:
            assert self.allow_toplevel_elems
            self.toplevel_elems.append(elem)

    @property
    def toplevel_writer(self):
        return self

class TemplateBodyWriter(Writer):
    def __init__(self, toplevel_writer: Optional[ToplevelWriter]):
        super().__init__()
        self._toplevel_writer = toplevel_writer
        self.elems: List[ir.TemplateBodyElement] = []

    def write_toplevel_elem(self, elem: Union[ir.TemplateBodyElement, ir.TemplateDefn]):
        self.toplevel_writer.write(elem)

    def write(self, elem: Union[ir.TemplateBodyElement]):
        self.elems.append(elem)

    @property
    def toplevel_writer(self):
        return self._toplevel_writer
