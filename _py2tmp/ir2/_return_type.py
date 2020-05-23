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
from typing import Optional, Tuple, Sequence

from _py2tmp.ir2 import ir
from _py2tmp.ir2._visitor import Visitor

def _combine_return_type_of_branches(branch1_stmts: Tuple[ir.Stmt, ...], branch2_stmts: Tuple[ir.Stmt, ...]):
    branch1_return_type_info = get_return_type(branch1_stmts)
    branch2_return_type_info = get_return_type(branch2_stmts)

    if branch1_return_type_info.expr_type:
        assert not branch2_return_type_info.expr_type or branch1_return_type_info.expr_type == branch2_return_type_info.expr_type
        expr_type = branch1_return_type_info.expr_type
    elif branch2_return_type_info.expr_type:
        expr_type = branch2_return_type_info.expr_type
    else:
        expr_type = None
    return ReturnTypeInfo(expr_type=expr_type,
                          always_returns=branch1_return_type_info.always_returns and branch2_return_type_info.always_returns)

class _GetReturnTypeVisitor(Visitor):
    def __init__(self):
        self.result = ReturnTypeInfo(expr_type=None, always_returns=False)

    def visit_expr(self, expr: ir.Expr):
        pass

    def visit_raise_stmt(self, stmt: ir.RaiseStmt):
        self.result.always_returns = True

    def visit_return_stmt(self, stmt: ir.ReturnStmt):
        self.result.always_returns = True
        self.result.return_type = stmt.expr.expr_type

    def visit_if_stmt(self, stmt: ir.IfStmt):
        self.result = _combine_return_type_of_branches(stmt.if_stmts, stmt.else_stmts)

    def visit_try_except_stmt(self, stmt: ir.TryExcept):
        self.result = _combine_return_type_of_branches(stmt.try_body, stmt.except_body)

class ReturnTypeInfo:
    def __init__(self, expr_type: Optional[ir.ExprType], always_returns: bool):
        # When expr_type is None, the statement never returns.
        # expr_type can't be None if always_returns is True.
        self.expr_type = expr_type
        self.always_returns = always_returns

def get_return_type(stmts: Sequence[ir.Stmt]):
    visitor = _GetReturnTypeVisitor()
    if stmts:
        visitor.visit_stmt(stmts[-1])
    return visitor.result
