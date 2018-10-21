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

from typing import List, Optional

from _py2tmp.ir1 import ir


class Writer:
    def write(self, elem: ir.Union[ir.FunctionDefn, ir.Assignment, ir.Assert, ir.CustomType, ir.CheckIfErrorDefn, ir.UnpackingAssignment, ir.CheckIfErrorStmt]): ...  # pragma: no cover

class FunWriter(Writer):
    def __init__(self):
        self.elems = []  # type: List[ir.Union[ir.FunctionDefn, ir.Assignment, ir.Assert, ir.CustomType, ir.CheckIfErrorDefn, ir.UnpackingAssignment, ir.CheckIfErrorStmt]]

    def write(self, elem: ir.Union[ir.FunctionDefn, ir.Assignment, ir.Assert, ir.CustomType, ir.CheckIfErrorDefn, ir.UnpackingAssignment, ir.CheckIfErrorStmt]):
        self.elems.append(elem)

class StmtWriter(Writer):
    def __init__(self,
                 fun_writer: FunWriter,
                 current_fun_return_type: Optional[ir.ExprType]):
        self.fun_writer = fun_writer
        self.current_fun_return_type = current_fun_return_type
        self.stmts = []  # type: List[ir.Stmt]

    def write(self, elem: ir.Union[ir.FunctionDefn, ir.CustomType, ir.CheckIfErrorDefn, ir.Stmt]):
        if isinstance(elem, ir.Stmt):
            self.stmts.append(elem)
        else:
            self.fun_writer.write(elem)
