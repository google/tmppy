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
from typing import Set, Dict

from _py2tmp.ir2 import ir
from _py2tmp.ir2._visitor import Visitor


class _GetFreeVariablesVisitor(Visitor):
    def __init__(self):
        self.free_variables_by_name: Dict[str, ir.VarReference] = dict()
        self.bound_variable_names: Set[str] = set()

    def visit_var_reference(self, var_reference: ir.VarReference):
        if not var_reference.is_global_function:
            self.free_variables_by_name[var_reference.name] = var_reference

    def visit_match_expr(self, match_expr: ir.MatchExpr):
        for expr in match_expr.matched_exprs:
            self.visit_expr(expr)
        for expr in match_expr.match_cases:
            with self.add_local_variable_names(set(expr.matched_var_names)):
                self.visit_match_case(expr)

    def visit_list_comprehension(self, expr: ir.ListComprehension):
        self.visit_expr(expr.list_expr)
        with self.add_local_variable_names({expr.loop_var.name}):
            self.visit_expr(expr.result_elem_expr)

    def visit_set_comprehension(self, expr: ir.SetComprehension):
        self.visit_expr(expr.set_expr)
        with self.add_local_variable_names({expr.loop_var.name}):
            self.visit_expr(expr.result_elem_expr)

    @contextmanager
    def add_local_variable_names(self, new_names: Set[str]):
        old_names = self.bound_variable_names
        self.bound_variable_names = self.bound_variable_names.union(new_names)
        yield
        self.bound_variable_names = old_names


def get_free_variables(expr: ir.Expr):
    visitor = _GetFreeVariablesVisitor()
    visitor.visit_expr(expr)
    return visitor.free_variables_by_name
