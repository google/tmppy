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

from typing import List, Set, Optional, Iterable, Union, Dict, Hashable, Tuple
from enum import Enum
import re
from _py2tmp import utils

class ExprKind(Enum):
    BOOL = 1
    INT64 = 2
    TYPE = 3
    TEMPLATE = 4

class ExprType(utils.ValueType):
    def __init__(self, kind: ExprKind):
        self.kind = kind

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
        self.argtypes = tuple(argtypes)

class Expr(utils.ValueType):
    def __init__(self, type: ExprType):
        self.type = type

    def references_any_of(self, variables: Set[str]) -> bool: ...  # pragma: no cover

    def get_free_vars(self) -> Iterable['TypeLiteral']: ...  # pragma: no cover

    def get_referenced_identifiers(self) -> Iterable[str]: ...  # pragma: no cover

class TemplateBodyElement:
    def get_referenced_identifiers(self) -> Iterable[str]: ...  # pragma: no cover

class StaticAssert(TemplateBodyElement):
    def __init__(self, expr: Expr, message: str):
        assert isinstance(expr.type, BoolType)
        self.expr = expr
        self.message = message

    def get_referenced_identifiers(self):
        for identifier in self.expr.get_referenced_identifiers():
            yield identifier

class ConstantDef(TemplateBodyElement):
    def __init__(self, name: str, expr: Expr):
        assert isinstance(expr.type, (BoolType, Int64Type))
        self.name = name
        self.expr = expr

    def get_referenced_identifiers(self):
        for identifier in self.expr.get_referenced_identifiers():
            yield identifier

class Typedef(TemplateBodyElement):
    def __init__(self, name: str, expr: Expr):
        assert isinstance(expr.type, (TypeType, TemplateType))
        self.name = name
        self.expr = expr

    def get_referenced_identifiers(self):
        for identifier in self.expr.get_referenced_identifiers():
            yield identifier

class TemplateArgDecl:
    def __init__(self, type: ExprType, name: str = ''):
        self.type = type
        self.name = name

_non_identifier_char_pattern = re.compile('[^a-zA-Z0-9_]+')

def _extract_identifiers(s: str):
    for match in re.split(_non_identifier_char_pattern, s):
        if match and not match[0] in '0123456789':
            yield match

class TemplateSpecialization:
    def __init__(self,
                 args: List[TemplateArgDecl],
                 patterns: 'Optional[List[TemplateArgPatternLiteral]]',
                 body: List[TemplateBodyElement]):
        self.args = tuple(args)
        self.patterns = tuple(patterns) if patterns is not None else None
        self.body = tuple(body)

    def get_referenced_identifiers(self):
        if self.patterns:
            for type_pattern in self.patterns:
                for identifier in _extract_identifiers(type_pattern.cxx_pattern):
                    yield identifier
        for elem in self.body:
            for identifier in elem.get_referenced_identifiers():
                yield identifier

class TemplateDefn(TemplateBodyElement):
    def __init__(self,
                 args: List[TemplateArgDecl],
                 main_definition: Optional[TemplateSpecialization],
                 specializations: List[TemplateSpecialization],
                 name: str,
                 description: str,
                 result_element_names: List[str]):
        assert main_definition or specializations
        assert not main_definition or main_definition.patterns is None
        assert '\n' not in description
        self.name = name
        self.args = tuple(args)
        self.main_definition = main_definition
        self.specializations = tuple(specializations)
        self.description = description
        self.result_element_names = tuple(sorted(result_element_names))

    def get_referenced_identifiers(self):
        if self.main_definition:
            for identifier in self.main_definition.get_referenced_identifiers():
                yield identifier
        for specialization in self.specializations:
            for identifier in specialization.get_referenced_identifiers():
                yield identifier

class Literal(Expr):
    def __init__(self, value: Union[bool, int]):
        if isinstance(value, bool):
            type = BoolType()
        elif isinstance(value, int):
            type = Int64Type()
        else:
            raise NotImplementedError('Unexpected value: ' + repr(value))
        super().__init__(type)
        self.value = value

    def references_any_of(self, variables: Set[str]):
        return False

    def get_free_vars(self):
        if False:
            yield

    def get_referenced_identifiers(self):
        if False:
            yield

class TypeLiteral(Expr):
    def __init__(self,
                 cpp_type: str,
                 is_local: bool,
                 is_metafunction_that_may_return_error: bool,
                 referenced_locals: List['TypeLiteral'],
                 type: ExprType):
        if is_local:
            assert not referenced_locals
        assert not (is_metafunction_that_may_return_error and not isinstance(type, TemplateType))
        super().__init__(type=type)
        self.cpp_type = cpp_type
        self.is_local = is_local
        self.type = type
        self.is_metafunction_that_may_return_error = is_metafunction_that_may_return_error
        self.referenced_locals = tuple(referenced_locals)

    @staticmethod
    def for_local(cpp_type: str,
                  type: ExprType):
        return TypeLiteral(cpp_type=cpp_type,
                           is_local=True,
                           type=type,
                           is_metafunction_that_may_return_error=(type.kind == ExprKind.TEMPLATE),
                           referenced_locals=[])

    @staticmethod
    def for_nonlocal(cpp_type: str,
                     type: ExprType,
                     is_metafunction_that_may_return_error: bool,
                     referenced_locals: List['TypeLiteral']):
        return TypeLiteral(cpp_type=cpp_type,
                           is_local=False,
                           type=type,
                           is_metafunction_that_may_return_error=is_metafunction_that_may_return_error,
                           referenced_locals=referenced_locals)

    @staticmethod
    def for_nonlocal_type(cpp_type: str):
        return TypeLiteral.for_nonlocal(cpp_type=cpp_type,
                                        type=TypeType(),
                                        is_metafunction_that_may_return_error=False,
                                        referenced_locals=[])

    @staticmethod
    def for_nonlocal_template(cpp_type: str,
                              arg_types: List[ExprType],
                              is_metafunction_that_may_return_error: bool):
        return TypeLiteral.for_nonlocal(cpp_type=cpp_type,
                                        type=TemplateType(arg_types),
                                        is_metafunction_that_may_return_error=is_metafunction_that_may_return_error,
                                        referenced_locals=[])

    @staticmethod
    def from_nonlocal_template_defn(template_defn: TemplateDefn,
                                    is_metafunction_that_may_return_error: bool):
        return TypeLiteral.for_nonlocal_template(cpp_type=template_defn.name,
                                                 arg_types=[arg.type for arg in template_defn.args],
                                                 is_metafunction_that_may_return_error=is_metafunction_that_may_return_error)

    def references_any_of(self, variables: Set[str]):
        return any(local_var.cpp_type in variables
                   for local_var in self.referenced_locals)

    def get_free_vars(self):
        if self.is_local:
            yield self
        for local_var in self.referenced_locals:
            yield local_var

    def get_referenced_identifiers(self):
        for identifier in _extract_identifiers(self.cpp_type):
            yield identifier

class TemplateArgPatternLiteral:
    def __init__(self, cxx_pattern: str = None):
        self.cxx_pattern = cxx_pattern

class UnaryExpr(Expr):
    def __init__(self, expr: Expr, result_type: ExprType):
        super().__init__(type=result_type)
        self.expr = expr

    def references_any_of(self, variables: Set[str]):
        return self.expr.references_any_of(variables)

    def get_free_vars(self):
        for var in self.expr.get_free_vars():
            yield var

    def get_referenced_identifiers(self):
        for identifier in self.expr.get_referenced_identifiers():
            yield identifier

class BinaryExpr(Expr):
    def __init__(self, lhs: Expr, rhs: Expr, result_type: ExprType):
        super().__init__(type=result_type)
        self.lhs = lhs
        self.rhs = rhs

    def references_any_of(self, variables: Set[str]):
        return self.lhs.references_any_of(variables) or self.rhs.references_any_of(variables)

    def get_free_vars(self):
        for expr in (self.lhs, self.rhs):
            for var in expr.get_free_vars():
                yield var

    def get_referenced_identifiers(self):
        for expr in (self.lhs, self.rhs):
            for identifier in expr.get_referenced_identifiers():
                yield identifier

class ComparisonExpr(BinaryExpr):
    def __init__(self, lhs: Expr, rhs: Expr, op: str):
        assert lhs.type == rhs.type
        if isinstance(lhs.type, BoolType):
            assert op == '=='
        elif isinstance(lhs.type, Int64Type):
            assert op in ('==', '!=', '<', '>', '<=', '>=')
        else:
            raise NotImplementedError('Unexpected type: %s' % str(lhs.type))
        super().__init__(lhs, rhs, result_type=BoolType())
        self.op = op

class Int64BinaryOpExpr(BinaryExpr):
    def __init__(self, lhs: Expr, rhs: Expr, op: str):
        super().__init__(lhs, rhs, result_type=Int64Type())
        assert isinstance(lhs.type, Int64Type)
        assert isinstance(rhs.type, Int64Type)
        assert op in ('+', '-', '*', '/', '%')
        self.op = op

class TemplateInstantiation(Expr):
    def __init__(self,
                 template_expr: Expr,
                 args: List[Expr],
                 instantiation_might_trigger_static_asserts: bool):
        assert isinstance(template_expr.type, TemplateType)
        assert len(template_expr.type.argtypes) == len(args), 'template_expr.type.argtypes: %s, args: %s' % (template_expr.type.argtypes, args)
        for arg_type, arg_expr in zip(template_expr.type.argtypes, args):
            assert arg_expr.type == arg_type, '%s vs %s' % (str(arg_expr.type), str(arg_type))
        super().__init__(type=TypeType())
        self.template_expr = template_expr
        self.args = tuple(args)
        self.instantiation_might_trigger_static_asserts = instantiation_might_trigger_static_asserts

    def references_any_of(self, variables: Set[str]):
        return self.template_expr.references_any_of(variables) or any(expr.references_any_of(variables)
                                                                      for expr in self.args)

    def get_free_vars(self):
        for exprs in ((self.template_expr,), self.args):
            for expr in exprs:
                for var in expr.get_free_vars():
                    yield var

    def get_referenced_identifiers(self):
        for exprs in ((self.template_expr,), self.args):
            for expr in exprs:
                for identifier in expr.get_referenced_identifiers():
                    yield identifier

class ClassMemberAccess(UnaryExpr):
    def __init__(self, class_type_expr: Expr, member_name: str, member_type: ExprType):
        super().__init__(class_type_expr, result_type=member_type)
        self.member_name = member_name

class NotExpr(UnaryExpr):
    def __init__(self, expr: Expr):
        super().__init__(expr, result_type=BoolType())

class UnaryMinusExpr(UnaryExpr):
    def __init__(self, expr: Expr):
        super().__init__(expr, result_type=Int64Type())

class Header:
    def __init__(self,
                 template_defns: List[TemplateDefn],
                 toplevel_content: List[Union[StaticAssert, ConstantDef, Typedef]],
                 public_names: Set[str]):
        self.template_defns = template_defns
        self.toplevel_content = tuple(toplevel_content)
        self.public_names = public_names
