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

from typing import List, Union, Iterator
from _py2tmp import ir0, transform_ir0

class _NormalizeExpressionsTransformation(transform_ir0.Transformation):
    def __init__(self):
        super().__init__()

    def transform_expr(self, expr: ir0.Expr, writer: transform_ir0.Writer, split_nontrivial_exprs=True) -> ir0.Expr:
        if split_nontrivial_exprs and not isinstance(expr, ir0.AtomicTypeLiteral):
            expr = super().transform_expr(expr, writer)
            var = writer.new_constant_or_typedef(expr)
            return var
        else:
            return expr

    def transform_pattern(self, expr: ir0.Expr, writer: transform_ir0.Writer):
        return expr

    def transform_constant_def(self, constant_def: ir0.ConstantDef, writer: transform_ir0.Writer):
        writer.write(ir0.ConstantDef(name=constant_def.name,
                                     expr=self.transform_expr(constant_def.expr, writer, split_nontrivial_exprs=False)))

    def transform_typedef(self, typedef: ir0.Typedef, writer: transform_ir0.Writer):
        writer.write(ir0.Typedef(name=typedef.name,
                                 expr=self.transform_expr(typedef.expr, writer, split_nontrivial_exprs=False)))

def normalize_template_defn(template_defn: ir0.TemplateDefn, identifier_generator: Iterator[str]):
    '''Converts template_defn to an equivalent TemplateDefn where all expressions contain 0 or 1 operations.

    Unlike other constants/typedefs, the exprs that initialize "result" and "error" will always have 0 operations.
    '''
    writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False)
    _NormalizeExpressionsTransformation().transform_template_defn(template_defn, writer)

    return writer.template_defns, False

def normalize_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                             identifier_generator: Iterator[str]):
    '''Converts template_defn to an equivalent TemplateDefn where all expressions contain 0 or 1 operations.

    Unlike other constants/typedefs, the exprs that initialize "result" and "error" will always have 0 operations.
    '''
    writer = transform_ir0.ToplevelWriter(identifier_generator, allow_template_defns=False)
    for toplevel_elem in toplevel_elems:
        transformation = _NormalizeExpressionsTransformation()
        transformation.transform_toplevel_elem(toplevel_elem, writer)

    return writer.toplevel_elems, False
