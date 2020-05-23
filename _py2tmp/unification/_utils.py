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
from typing import Union, Tuple

from _py2tmp.unification import UnificationStrategy
from _py2tmp.unification._strategy import TermT, TupleExpansion

_NonListExpr = Union[str, TermT]
_Expr = Union[_NonListExpr, Tuple[_NonListExpr, ...]]

def ensure_tuple(x: _Expr) -> Tuple[_NonListExpr, ...]:
    if isinstance(x, tuple):
        return x
    else:
        return x,

def expr_to_string(strategy: UnificationStrategy[TermT], expr: _NonListExpr):
    if isinstance(expr, str):
        return expr
    elif isinstance(expr, TupleExpansion):
        return '(%s)...' % expr_to_string(strategy, expr.expr)
    else:
        return strategy.term_to_string(expr)

def exprs_to_string(strategy: UnificationStrategy[TermT], exprs: Tuple[_NonListExpr, ...]):
    return '[' + ', '.join(expr_to_string(strategy, expr) for expr in exprs) + ']'
