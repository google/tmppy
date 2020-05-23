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

from typing import TypeVar, Generic, Union, Dict, Tuple

TermT = TypeVar('TermT')

class TupleExpansion(Generic[TermT]):
    def __init__(self, expr: Union[str, TermT]):
        self.expr = expr

class UnificationStrategy(Generic[TermT]):
    Expr = Union[str, TermT, TupleExpansion[TermT]]

    # Checks if term1 is equal to term2 excluding args.
    def is_same_term_excluding_args(self, term1: TermT, term2: TermT) -> bool: ...

    # Gets the args of a term.
    def get_term_args(self, term: TermT) -> Tuple[Expr, ...]: ...

    # Returns a string representation of the term, used in exception messages.
    def term_to_string(self, term: TermT) -> str: ...

    def equality_requires_syntactical_equality(self, term: TermT) -> bool: ...

    # Given term1, term2 such that:
    # * not is_same_term_excluding_args(term1, term2)
    # * not equality_requires_syntactical_equality(term1) or not equality_requires_syntactical_equality(term2)
    # if this returns False they are definitely different, otherwise we don't know.
    def may_be_equal(self, term1: TermT, term2: TermT) -> bool: ...

class UnificationStrategyForCanonicalization(Generic[TermT], UnificationStrategy[TermT]):
    def replace_variables_in_expr(self,
                                  expr: UnificationStrategy.Expr,
                                  replacements: Dict[str, Tuple[UnificationStrategy.Expr, ...]],
                                  expanded_var_replacements: Dict[str, Tuple[UnificationStrategy.Expr, ...]]) \
            -> UnificationStrategy.Expr: ...

    # Returns true if the var is allowed to be in the LHS of an equation in the result.
    def can_var_be_on_lhs(self, str) -> bool: ...
