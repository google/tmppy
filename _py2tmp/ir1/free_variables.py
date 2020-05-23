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
import itertools
from contextlib import contextmanager
from typing import List, Set, Dict, Union, Generator, Tuple, Iterable

from _py2tmp.ir1 import ir
from _py2tmp.ir1._visitor import Visitor


class _GetFreeVariablesVisitor(Visitor):
    def __init__(self) -> None:
        self.local_var_names: Set[str] = set()
        self.free_vars_by_name: Dict[str, Union[ir.VarReference, ir.VarReferencePattern]] = dict()

    def visit_assignment(self, stmt: ir.Assignment):
        self.visit_expr(stmt.rhs)
        self.local_var_names.add(stmt.lhs.name)
        if stmt.lhs2:
            self.local_var_names.add(stmt.lhs2.name)

    def visit_unpacking_assignment(self, stmt: ir.UnpackingAssignment):
        self.visit_expr(stmt.rhs)
        for var in stmt.lhs_list:
            self.local_var_names.add(var.name)

    def visit_match_expr(self, expr: ir.MatchExpr):
        for matched_var in expr.matched_vars:
            self.visit_expr(matched_var)
        for match_case in expr.match_cases:
            with self.open_scope():
                for var in itertools.chain(match_case.matched_var_names, match_case.matched_variadic_var_names):
                    self.local_var_names.add(var)
                self.visit_match_case(match_case)

    def visit_var_reference(self, expr: ir.VarReference):
        if not expr.is_global_function and expr.name not in self.local_var_names:
            self.free_vars_by_name[expr.name] = expr

    def visit_var_reference_pattern(self, expr: ir.VarReferencePattern):
        if not expr.is_global_function and expr.name not in self.local_var_names:
            self.free_vars_by_name[expr.name] = expr

    def visit_list_comprehension_expr(self, expr: ir.ListComprehensionExpr):
        self.visit_expr(expr.list_var)
        with self.open_scope():
            self.local_var_names.add(expr.loop_var.name)
            self.visit_expr(expr.result_elem_expr)

    @contextmanager
    def open_scope(self) -> Generator[None, None, None]:
        old_names = self.local_var_names.copy()
        yield
        self.local_var_names = old_names

def get_unique_free_variables_in_stmts(stmts: Iterable[ir.Stmt]) -> Tuple[ir.VarReference, ...]:
    visitor = _GetFreeVariablesVisitor()
    visitor.visit_stmts(stmts)
    return tuple(sorted(visitor.free_vars_by_name.values(), key=lambda var: var.name))

def get_unique_free_variables_in_expr(expr: ir.Expr) -> Tuple[ir.VarReference, ...]:
    visitor = _GetFreeVariablesVisitor()
    visitor.visit_expr(expr)
    return tuple(sorted(visitor.free_vars_by_name.values(), key=lambda var: var.name))
