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
from _py2tmp.ir0 import ir
from _py2tmp.ir0._visitor import Visitor


class _ComputeIsVariadicVisitor(Visitor):
    def __init__(self):
        self.is_variadic = False
        
    def visit_variadic_type_expansion(self, expr: ir.VariadicTypeExpansion):
        # No need to visit `expr`. Any variadic var inside it is already expanded anyway.
        pass

    def visit_type_literal(self, type_literal: ir.AtomicTypeLiteral):
        self.is_variadic |= type_literal.is_variadic

def is_expr_variadic(expr: ir.Expr):
    visitor = _ComputeIsVariadicVisitor()
    visitor.visit_expr(expr)
    return visitor.is_variadic
