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

from typing import List, Set, Optional, Iterable, Union
from enum import Enum

class ExprKind(Enum):
    BOOL = 1
    INT64 = 2
    TYPE = 3
    TEMPLATE = 4

class ExprType:
    def __init__(self, kind: ExprKind):
        self.kind = kind

    def __eq__(self, other) -> bool: ...  # pragma: no cover

class BoolType(ExprType):
    def __init__(self):
        super().__init__(kind=ExprKind.BOOL)

class Int64Type(ExprType):
    def __init__(self):
        super().__init__(kind=ExprKind.INT64)

class TypeType(ExprType):
    def __init__(self):
        super().__init__(kind=ExprKind.TYPE)

class TemplateType(ExprType):
    def __init__(self, argtypes: List[ExprType]):
        super().__init__(kind=ExprKind.TEMPLATE)
        self.argtypes = argtypes

class Expr:
    def __init__(self, kind: ExprKind):
        self.kind = kind

    def references_any_of(self, variables: Set[str]) -> bool: ...  # pragma: no cover

    def get_free_vars(self) -> Iterable['TypeLiteral']: ...  # pragma: no cover

class TemplateBodyElement:
    pass

class StaticAssert(TemplateBodyElement):
    def __init__(self, expr: Expr, message: str):
        assert expr.kind == ExprKind.BOOL
        self.expr = expr
        self.message = message

class ConstantDef(TemplateBodyElement):
    def __init__(self, name: str, expr: Expr, type: ExprType):
        assert expr.kind == type.kind
        assert isinstance(type, BoolType) or isinstance(type, Int64Type)
        self.name = name
        self.expr = expr
        self.type = type

class Typedef(TemplateBodyElement):
    def __init__(self, name: str, expr: Expr, type: ExprType):
        assert type.kind == expr.kind, '%s vs %s' % (type.kind, expr.kind)
        assert type.kind in (ExprKind.TYPE, ExprKind.TEMPLATE)
        self.name = name
        self.expr = expr
        self.type = type

class TemplateArgDecl:
    def __init__(self, type: ExprType, name: str = ''):
        self.type = type
        self.name = name

class TemplateSpecialization:
    def __init__(self,
                 args: List[TemplateArgDecl],
                 patterns: 'Optional[List[TemplateArgPatternLiteral]]',
                 body: List[TemplateBodyElement]):
        self.args = args
        self.patterns = patterns
        self.body = body

class TemplateDefn(TemplateBodyElement):
    def __init__(self,
                 args: List[TemplateArgDecl],
                 main_definition: Optional[TemplateSpecialization],
                 specializations: List[TemplateSpecialization],
                 name: Optional[str] = None):
        assert main_definition or specializations
        assert not main_definition or main_definition.patterns is None
        self.name = name
        self.args = args
        self.main_definition = main_definition
        self.specializations = specializations

class Literal(Expr):
    def __init__(self, value, kind: ExprKind):
        super().__init__(kind)
        assert value in (True, False) or isinstance(value, int)
        self.value = value

    def references_any_of(self, variables: Set[str]):
        return False

    def get_free_vars(self):
        if False:
            yield

class TypeLiteral(Expr):
    def __init__(self,
                 cpp_type: str,
                 is_local: bool,
                 is_metafunction_that_may_return_error: bool,
                 kind: Optional[ExprKind] = None,
                 type: Optional[ExprType] = None):
        if is_local:
            assert type
        assert not (type and kind)
        if type:
            kind = type.kind
        assert not (is_metafunction_that_may_return_error and kind != ExprKind.TEMPLATE)
        super().__init__(kind=kind)
        self.cpp_type = cpp_type
        self.is_local = is_local
        self.type = type
        self.is_metafunction_that_may_return_error = is_metafunction_that_may_return_error

    @staticmethod
    def for_local(cpp_type: str, type: ExprType):
        return TypeLiteral(cpp_type=cpp_type,
                           is_local=True,
                           type=type,
                           is_metafunction_that_may_return_error=(type.kind == ExprKind.TEMPLATE))

    @staticmethod
    def for_nonlocal(cpp_type: str, kind: ExprKind, is_metafunction_that_may_return_error: bool):
        return TypeLiteral(cpp_type=cpp_type,
                           is_local=False,
                           kind=kind,
                           is_metafunction_that_may_return_error=is_metafunction_that_may_return_error)

    @staticmethod
    def for_nonlocal_type(cpp_type: str):
        return TypeLiteral.for_nonlocal(cpp_type=cpp_type,
                                        kind=ExprKind.TYPE,
                                        is_metafunction_that_may_return_error=False)

    @staticmethod
    def for_nonlocal_template(cpp_type: str, is_metafunction_that_may_return_error: bool):
        return TypeLiteral.for_nonlocal(cpp_type=cpp_type,
                                        kind=ExprKind.TEMPLATE,
                                        is_metafunction_that_may_return_error=is_metafunction_that_may_return_error)

    def references_any_of(self, variables: Set[str]):
        return False

    def get_free_vars(self):
        if self.is_local:
            yield self

class TemplateArgPatternLiteral:
    def __init__(self, cxx_pattern: str = None):
        self.cxx_pattern = cxx_pattern

class ComparisonExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr, op: str):
        super().__init__(kind=ExprKind.BOOL)
        assert lhs.kind == rhs.kind
        assert lhs.kind in (ExprKind.BOOL, ExprKind.INT64)
        assert op in ('==', '!=', '<', '>', '<=', '>=')
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

    def references_any_of(self, variables: Set[str]):
        return self.lhs.references_any_of(variables) or self.rhs.references_any_of(variables)

    def get_free_vars(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_vars():
                yield var

class Int64BinaryOpExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr, op: str):
        super().__init__(kind=ExprKind.INT64)
        assert lhs.kind == ExprKind.INT64
        assert rhs.kind == ExprKind.INT64
        assert op in ('+', '-', '*', '/', '%')
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

    def references_any_of(self, variables: Set[str]):
        return self.lhs.references_any_of(variables) or self.rhs.references_any_of(variables)

    def get_free_vars(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_vars():
                yield var

class TemplateInstantiation(Expr):
    def __init__(self,
                 template_expr: Expr,
                 args: List[Expr],
                 arg_types: List[ExprType],
                 instantiation_might_trigger_static_asserts: bool):
        assert template_expr.kind == ExprKind.TEMPLATE
        assert arg_types or not instantiation_might_trigger_static_asserts
        assert not arg_types or len(arg_types) == len(args)
        super().__init__(kind=ExprKind.TYPE)
        self.template_expr = template_expr
        self.args = args
        self.arg_types = arg_types
        self.instantiation_might_trigger_static_asserts = instantiation_might_trigger_static_asserts

    def references_any_of(self, variables: Set[str]):
        return self.template_expr.references_any_of(variables) or any(expr.references_any_of(variables)
                                                                      for expr in self.args)

    def get_free_vars(self):
        for exprs in ((self.template_expr,), self.args):
            for expr in exprs:
                for var in expr.get_free_vars():
                    yield var

class ClassMemberAccess(Expr):
    def __init__(self, class_type_expr: Expr, member_name: str, member_kind: ExprKind):
        super().__init__(kind=member_kind)
        self.class_type_expr = class_type_expr
        self.member_name = member_name
        self.member_kind = member_kind

    def references_any_of(self, variables: Set[str]):
        return self.class_type_expr.references_any_of(variables)

    def get_free_vars(self):
        for var in self.class_type_expr.get_free_vars():
            yield var

class NotExpr(Expr):
    def __init__(self, expr: Expr):
        super().__init__(kind=ExprKind.BOOL)
        self.expr = expr

    def references_any_of(self, variables: Set[str]):
        return self.expr.references_any_of(variables)

    def get_free_vars(self):
        for var in self.expr.get_free_vars():
            yield var

class UnaryMinusExpr(Expr):
    def __init__(self, expr: Expr):
        super().__init__(kind=ExprKind.INT64)
        self.expr = expr

    def references_any_of(self, variables: Set[str]):
        return self.expr.references_any_of(variables)

    def get_free_vars(self):
        for var in self.expr.get_free_vars():
            yield var

class Header:
    def __init__(self, content: List[Union[TemplateDefn, StaticAssert, ConstantDef, Typedef]]):
        self.content = content
