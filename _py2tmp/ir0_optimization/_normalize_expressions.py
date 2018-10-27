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
from typing import Optional, Iterator

from _py2tmp.ir0 import ir, Transformation


class NormalizeExpressionsTransformation(Transformation):
    def __init__(self, identifier_generator: Optional[Iterator[str]]):
        super().__init__(identifier_generator=identifier_generator)

    def transform_expr(self, expr: ir.Expr, split_nontrivial_exprs=True) -> ir.Expr:
        if split_nontrivial_exprs and not isinstance(expr, ir.AtomicTypeLiteral):
            expr = super().transform_expr(expr)
            var = self.writer.new_constant_or_typedef(expr, self.identifier_generator)
            return var
        else:
            return expr

    def transform_pattern(self, expr: ir.Expr):
        return expr

    def transform_constant_def(self, constant_def: ir.ConstantDef):
        self.writer.write(ir.ConstantDef(name=constant_def.name,
                                         expr=self.transform_expr(constant_def.expr, split_nontrivial_exprs=False)))

    def transform_typedef(self, typedef: ir.Typedef):
        self.writer.write(ir.Typedef(name=typedef.name,
                                     expr=self.transform_expr(typedef.expr, split_nontrivial_exprs=False),
                                     description=typedef.description,
                                     template_args=typedef.template_args))
