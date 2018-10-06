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

from _py2tmp import ir0, transform_ir0

class _ComputeNonExpandedVariadicVarsTransformation(transform_ir0.Transformation):
    def __init__(self):
        super().__init__(generates_transformed_ir=False)
        self.result = dict()

    def transform_variadic_type_expansion(self, expr: ir0.VariadicTypeExpansion, writer: transform_ir0.Writer):
        # No need to visit `expr`. Any variadic var inside it is already expanded anyway.
        return

    def transform_type_literal(self, type_literal: ir0.AtomicTypeLiteral, writer: transform_ir0.Writer):
        if type_literal.is_variadic:
            self.result[type_literal.cpp_type] = type_literal

def compute_non_expanded_variadic_vars(expr: ir0.Expr):
    transformation = _ComputeNonExpandedVariadicVarsTransformation()
    transformation.transform_expr(expr, transform_ir0.ToplevelWriter(iter([])))
    return transformation.result

