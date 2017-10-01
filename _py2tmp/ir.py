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

from typing import List, Iterable, Optional, Union, Dict

class ExprType:
    def __str__(self) -> str: ...  # pragma: no cover

    def __eq__(self, other) -> bool: ...  # pragma: no cover

class BoolType(ExprType):
    def __str__(self):
        return 'bool'

    def __eq__(self, other):
        return isinstance(other, BoolType)

class IntType(ExprType):
    def __str__(self):
        return 'int'

    def __eq__(self, other):
        return isinstance(other, IntType)

class TypeType(ExprType):
    def __str__(self):
        return 'Type'

    def __eq__(self, other):
        return isinstance(other, TypeType)

class FunctionType(ExprType):
    def __init__(self, argtypes: List[ExprType], returns: ExprType):
        self.argtypes = argtypes
        self.returns = returns

    def __str__(self):
        return "(%s) -> %s" % (
            ', '.join(str(arg)
                      for arg in self.argtypes),
            str(self.returns))

    def __eq__(self, other):
        return isinstance(other, FunctionType) and self.__dict__ == other.__dict__

class ListType(ExprType):
    def __init__(self, elem_type: ExprType):
        assert not isinstance(elem_type, FunctionType)
        self.elem_type = elem_type

    def __str__(self):
        return "List[%s]" % str(self.elem_type)

    def __eq__(self, other):
        return isinstance(other, ListType) and self.__dict__ == other.__dict__

class CustomTypeArgDecl:
    def __init__(self, name: str, type: ExprType):
        self.name = name
        self.type = type

    def __eq__(self, other):
        return isinstance(other, CustomTypeArgDecl) and self.__dict__ == other.__dict__

class CustomType(ExprType):
    def __init__(self, name: str, arg_types: List[CustomTypeArgDecl]):
        self.name = name
        self.arg_types = arg_types

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, CustomType) and self.__dict__ == other.__dict__

class Expr:
    def __init__(self, type: ExprType):
        self.type = type

    # Note: it's the caller's responsibility to de-duplicate VarReference objects that reference the same symbol, if
    # desired.
    def get_free_variables(self) -> 'Iterable[VarReference]': ...  # pragma: no cover

class FunctionArgDecl:
    def __init__(self, type: ExprType, name: str = ''):
        self.type = type
        self.name = name

class VarReference(Expr):
    def __init__(self, type: ExprType, name: str, is_global_function: bool):
        super().__init__(type=type)
        assert name
        self.name = name
        self.is_global_function = is_global_function

    def get_free_variables(self):
        if not self.is_global_function:
            yield self

class MatchCase:
    def __init__(self,
                 type_patterns: List[str],
                 matched_var_names: List[str],
                 stmts: List['Stmt'],
                 return_type: ExprType):
        self.type_patterns = type_patterns
        self.matched_var_names = matched_var_names
        self.stmts = stmts
        self.return_type = return_type

    def is_main_definition(self):
        return set(self.type_patterns) == set(self.matched_var_names)

class MatchExpr(Expr):
    def __init__(self, matched_vars: List[VarReference], match_cases: List[MatchCase]):
        assert matched_vars
        assert match_cases
        for match_case in match_cases:
            assert len(match_case.type_patterns) == len(matched_vars)
            assert match_case.return_type == match_cases[0].return_type
        super().__init__(type=match_cases[0].return_type)
        self.matched_vars = matched_vars
        self.match_cases = match_cases

        assert len([match_case
                    for match_case in match_cases
                    if match_case.is_main_definition()]) <= 1

    def get_free_variables(self):
        for expr in self.matched_vars:
            for var in expr.get_free_variables():
                yield var
        for match_case in self.match_cases:
            local_vars = set(match_case.matched_var_names)
            for var in get_free_variables_in_stmts(match_case.stmts):
                if var.name not in local_vars:
                    yield var

class BoolLiteral(Expr):
    def __init__(self, value: bool):
        super().__init__(BoolType())
        self.value = value

    def get_free_variables(self):
        if False:
            yield

class TypeLiteral(Expr):
    def __init__(self, cpp_type: str):
        super().__init__(type=TypeType())
        self.cpp_type = cpp_type

    def get_free_variables(self):
        if False:
            yield

class ListExpr(Expr):
    def __init__(self, elem_type: ExprType, elems: List[VarReference]):
        assert not isinstance(elem_type, FunctionType)
        super().__init__(type=ListType(elem_type))
        self.elem_type = elem_type
        self.elems = elems

    def get_free_variables(self):
        for expr in self.elems:
            for var in expr.get_free_variables():
                yield var

class FunctionCall(Expr):
    def __init__(self, fun: VarReference, args: List[VarReference]):
        assert isinstance(fun.type, FunctionType)
        assert len(fun.type.argtypes) == len(args)
        super().__init__(type=fun.type.returns)
        self.fun = fun
        self.args = args

    def get_free_variables(self):
        for var in self.fun.get_free_variables():
            yield var
        for expr in self.args:
            for var in expr.get_free_variables():
                yield var

class EqualityComparison(Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference):
        super().__init__(type=BoolType())
        assert lhs.type == rhs.type, '%s vs %s' % (str(lhs.type), str(rhs.type))
        assert not isinstance(lhs.type, FunctionType)
        self.lhs = lhs
        self.rhs = rhs

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

class AttributeAccessExpr(Expr):
    def __init__(self, var: VarReference, attribute_name: str, type: ExprType):
        super().__init__(type=type)
        assert isinstance(var.type, (TypeType, CustomType))
        self.var = var
        self.attribute_name = attribute_name
        self.type = type

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

class IntLiteral(Expr):
    def __init__(self, value: int):
        super().__init__(type=IntType())
        self.value = value

    def get_free_variables(self):
        if False:
            yield

class NotExpr(Expr):
    def __init__(self, var: VarReference):
        assert var.type == BoolType()
        super().__init__(type=BoolType())
        self.var = var

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

class UnaryMinusExpr(Expr):
    def __init__(self, var: VarReference):
        assert var.type == IntType()
        super().__init__(type=IntType())
        self.var = var

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

class IntComparisonExpr(Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference, op: str):
        assert lhs.type == IntType()
        assert rhs.type == IntType()
        assert op in ('<', '>', '<=', '>=')
        super().__init__(type=BoolType())
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

class IntBinaryOpExpr(Expr):
    def __init__(self, lhs: VarReference, rhs: VarReference, op: str):
        assert lhs.type == IntType()
        assert rhs.type == IntType()
        assert op in ('+', '-', '*', '//', '%')
        super().__init__(type=IntType())
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

    def get_free_variables(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_variables():
                yield var

class ReturnTypeInfo:
    def __init__(self, type: Optional[ExprType], always_returns: bool):
        # When expr_type is None, the statement never returns.
        # expr_type can't be None if always_returns is True.
        self.type = type
        self.always_returns = always_returns

class Stmt:
    def get_return_type(self) -> ReturnTypeInfo: ...  # pragma: no cover

    # Note: it's the caller's responsibility to de-duplicate VarReference objects that reference the same symbol, if
    # desired.
    def get_free_variables(self) -> 'Iterable[VarReference]': ...  # pragma: no cover

class Assert(Stmt):
    def __init__(self, var: VarReference, message: str):
        assert isinstance(var.type, BoolType)
        self.var = var
        self.message = message

    def get_return_type(self):
        return ReturnTypeInfo(type=None, always_returns=False)

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

class Assignment(Stmt):
    def __init__(self, lhs: VarReference, rhs: Expr):
        assert lhs.type == rhs.type
        self.lhs = lhs
        self.rhs = rhs

    def get_return_type(self):
        return ReturnTypeInfo(type=None, always_returns=False)

    def get_free_variables(self):
        for var in self.rhs.get_free_variables():
            yield var

class ReturnStmt(Stmt):
    def __init__(self, var: VarReference):
        self.var = var

    def get_return_type(self):
        return ReturnTypeInfo(type=self.var.type, always_returns=True)

    def get_free_variables(self):
        for var in self.var.get_free_variables():
            yield var

class IfStmt(Stmt):
    def __init__(self, cond: VarReference, if_stmts: List[Stmt], else_stmts: List[Stmt]):
        assert cond.type == BoolType()
        assert if_stmts
        self.cond = cond
        self.if_stmts = if_stmts
        self.else_stmts = else_stmts

    def get_return_type(self):
        if_return_type_info = self.if_stmts[-1].get_return_type()
        if self.else_stmts:
            else_return_type_info = self.else_stmts[-1].get_return_type()
        else:
            else_return_type_info = ReturnTypeInfo(type=None, always_returns=False)

        if if_return_type_info.type:
            assert not else_return_type_info.type or if_return_type_info.type == else_return_type_info.type
            type = if_return_type_info.type
        elif else_return_type_info.type:
            type = else_return_type_info.type
        else:
            type = None
        return ReturnTypeInfo(type=type,
                              always_returns=if_return_type_info.always_returns and else_return_type_info.always_returns)

    def get_free_variables(self):
        for var in self.cond.get_free_variables():
            yield var
        for stmts in (self.if_stmts, self.else_stmts):
            for var in get_free_variables_in_stmts(stmts):
                yield var

class FunctionDefn:
    def __init__(self,
                 name: str,
                 args: List[FunctionArgDecl],
                 body: List[Stmt],
                 return_type: ExprType):
        self.name = name
        self.args = args
        self.body = body
        self.return_type = return_type

class Module:
    def __init__(self, body: List[Union[FunctionDefn, Assignment, Assert, CustomType]]):
        self.body = body

def get_free_variables_in_stmts(stmts: List[Stmt]):
    local_var_names = set()
    for stmt in stmts:
        for var in stmt.get_free_variables():
            if var.name not in local_var_names:
                yield var
        if isinstance(stmt, Assignment):
            local_var_names.add(stmt.lhs.name)