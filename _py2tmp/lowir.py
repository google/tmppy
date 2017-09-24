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

from typing import List, Set, Optional, Union
from enum import Enum

class ExprKind(Enum):
    BOOL = 1
    TYPE = 2
    TEMPLATE = 3

class ExprType:
    def __init__(self, kind: ExprKind):
        self.kind = kind

    def __eq__(self, other) -> bool: ... # pragma: no cover

class BoolType(ExprType):
    def __init__(self):
        super().__init__(kind=ExprKind.BOOL)

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

    def references_any_of(self, variables: Set[str]) -> bool: ... # pragma: no cover

class StaticAssert:
    def __init__(self, expr: Expr, message: str):
        assert expr.kind == ExprKind.BOOL
        self.expr = expr
        self.message = message

class ConstantDef:
    def __init__(self, name: str, expr: Expr, type: ExprType):
        assert expr.kind == type.kind
        assert isinstance(type, BoolType)
        self.name = name
        self.expr = expr
        self.type = type

class Typedef:
    def __init__(self, name: str, expr: Expr, type: ExprType):
        assert type.kind == expr.kind
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
                 patterns: 'Optional[List[TypePatternLiteral]]',
                 body: List[Union[StaticAssert, ConstantDef, Typedef]]):
        self.args = args
        self.patterns = patterns
        self.body = body

class TemplateDefn:
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
        assert value in (True, False)
        self.value = value

    def references_any_of(self, variables: Set[str]):
        return False

class TypeLiteral(Expr):
    def __init__(self, cpp_type: str, kind: ExprKind = ExprKind.TYPE):
        super().__init__(kind=kind)
        self.cpp_type = cpp_type

    def references_any_of(self, variables: Set[str]):
        return False

class TypePatternLiteral:
    def __init__(self, cxx_pattern: str = None):
        self.cxx_pattern = cxx_pattern

class EqualityComparison(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        super().__init__(kind=ExprKind.BOOL)
        assert lhs.kind == rhs.kind
        assert lhs.kind in (ExprKind.BOOL, ExprKind.TYPE)
        self.lhs = lhs
        self.rhs = rhs

    def references_any_of(self, variables: Set[str]):
        return self.lhs.references_any_of(variables) or self.rhs.references_any_of(variables)

class TemplateInstantiation(Expr):
    def __init__(self, template_expr: Expr, args: List[Expr]):
        assert template_expr.kind == ExprKind.TEMPLATE
        super().__init__(kind=ExprKind.TYPE)
        self.template_expr = template_expr
        self.args = args

    def references_any_of(self, variables: Set[str]):
        return self.template_expr.references_any_of(variables) or any(expr.references_any_of(variables)
                                                                      for expr in self.args)

class ClassMemberAccess(Expr):
    def __init__(self, class_type_expr: Expr, member_name: str, member_kind: ExprKind):
        super().__init__(kind=member_kind)
        self.class_type_expr = class_type_expr
        self.member_name = member_name
        self.member_kind = member_kind

    def references_any_of(self, variables: Set[str]):
        return self.class_type_expr.references_any_of(variables)

class Header:
    def __init__(self, template_defns: List[TemplateDefn], assertions: List[StaticAssert]):
        self.template_defns = template_defns
        self.assertions = assertions
