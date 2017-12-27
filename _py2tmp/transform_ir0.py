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

from typing import List, Set, Optional, Iterable, Union, Dict
from _py2tmp import ir0

class Writer:
    def write(self, elem: Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]): ...  # pragma: no cover

    def write_toplevel_elem(self, elem: Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]): ...  # pragma: no cover

    def new_id(self) -> str: ...  # pragma: no cover

    def new_constant_or_typedef(self, expr: ir0.Expr) -> ir0.TypeLiteral:
        assert expr.type.kind != ir0.ExprKind.TEMPLATE

        id = self.new_id()

        # TODO: remove.
        assert id is not None

        if expr.type.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
            self.write(ir0.ConstantDef(name=id, expr=expr))
        elif expr.type.kind == ir0.ExprKind.TYPE:
            self.write(ir0.Typedef(name=id, expr=expr))
        else:
            raise NotImplementedError('Unexpected kind: ' + str(expr.type.kind))

        return ir0.TypeLiteral.for_local(cpp_type=id, type=expr.type)

    def get_toplevel_writer(self) -> 'ToplevelWriter': ...  # pragma: no cover

class ToplevelWriter(Writer):
    def __init__(self, identifier_generator: Iterable[str]):
        self.identifier_generator = identifier_generator
        self.elems = []  # type: List[Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]]

    def write(self, elem: Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]):
        self.elems.append(elem)

    def new_id(self):
        return next(self.identifier_generator)

    def get_toplevel_writer(self):
        return self

class TemplateBodyWriter(Writer):
    def __init__(self, toplevel_writer: ToplevelWriter):
        self.toplevel_writer = toplevel_writer
        self.elems = []  # type: List[ir0.TemplateBodyElement]

    def new_id(self):
        return self.toplevel_writer.new_id()

    def write_toplevel_elem(self, elem: Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]):
        self.toplevel_writer.write(elem)

    def write(self, elem: ir0.TemplateBodyElement):
        self.elems.append(elem)

    def get_toplevel_writer(self):
        return self.toplevel_writer

class Transformation:
    def transform_header(self, header: ir0.Header, identifier_generator: Iterable[str]) -> ir0.Header:
        writer = ToplevelWriter(identifier_generator)
        for elem in header.content:
            self.transform_toplevel_elem(elem, writer)

        return ir0.Header(content=writer.elems)

    def transform_toplevel_elem(self, elem: Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef], writer: Writer):
        if isinstance(elem, ir0.TemplateDefn):
            self.transform_template_defn(elem, writer)
        elif isinstance(elem, ir0.StaticAssert):
            self.transform_static_assert(elem, writer)
        elif isinstance(elem, ir0.ConstantDef):
            self.transform_constant_def(elem, writer)
        elif isinstance(elem, ir0.Typedef):
            self.transform_typedef(elem, writer)
        else:
            raise NotImplementedError('Unexpected elem: ' + elem.__class__.__name__)

    def transform_template_defn(self, template_defn: ir0.TemplateDefn, writer: Writer):
        writer.write(ir0.TemplateDefn(args=[self.transform_template_arg_decl(arg_decl) for arg_decl in template_defn.args],
                                      main_definition=self.transform_template_specialization(template_defn.main_definition, writer) if template_defn.main_definition is not None else None,
                                      specializations=[self.transform_template_specialization(specialization, writer) for specialization in template_defn.specializations],
                                      name=template_defn.name,
                                      description=template_defn.description))

    def transform_static_assert(self, static_assert: ir0.StaticAssert, writer: Writer):
        writer.write(ir0.StaticAssert(expr=self.transform_expr(static_assert.expr, writer),
                                      message=static_assert.message))

    def transform_constant_def(self, constant_def: ir0.ConstantDef, writer: Writer):
        writer.write(ir0.ConstantDef(name=constant_def.name,
                                     expr=self.transform_expr(constant_def.expr, writer)))

    def transform_typedef(self, typedef: ir0.Typedef, writer: Writer):
        writer.write(ir0.Typedef(name=typedef.name,
                                 expr=self.transform_expr(typedef.expr, writer)))

    def transform_template_arg_decl(self, arg_decl: ir0.TemplateArgDecl) -> ir0.TemplateArgDecl:
        return arg_decl

    def transform_template_body_elems(self, elems: List[ir0.TemplateBodyElement], writer: ToplevelWriter) -> List[ir0.TemplateBodyElement]:
        body_writer = TemplateBodyWriter(writer)
        for elem in elems:
            self.transform_template_body_elem(elem, body_writer)
        return body_writer.elems

    def transform_template_specialization(self, specialization: ir0.TemplateSpecialization, writer: Writer) -> ir0.TemplateSpecialization:
        toplevel_writer = writer.get_toplevel_writer()

        return ir0.TemplateSpecialization(args=[self.transform_template_arg_decl(arg_decl) for arg_decl in specialization.args],
                                          patterns=[self.transform_pattern(pattern) for pattern in specialization.patterns] if specialization.patterns is not None else None,
                                          body=self.transform_template_body_elems(specialization.body, toplevel_writer))

    def transform_expr(self, expr: ir0.Expr, writer: Writer) -> ir0.Expr:
        if isinstance(expr, ir0.Literal):
            return self.transform_literal(expr, writer)
        elif isinstance(expr, ir0.TypeLiteral):
            return self.transform_type_literal(expr, writer)
        elif isinstance(expr, ir0.ClassMemberAccess):
            return self.transform_class_member_access(expr, writer)
        elif isinstance(expr, ir0.NotExpr):
            return self.transform_not_expr(expr, writer)
        elif isinstance(expr, ir0.UnaryMinusExpr):
            return self.transform_unary_minus_expr(expr, writer)
        elif isinstance(expr, ir0.ComparisonExpr):
            return self.transform_comparison_expr(expr, writer)
        elif isinstance(expr, ir0.Int64BinaryOpExpr):
            return self.transform_int64_binary_op_expr(expr, writer)
        elif isinstance(expr, ir0.TemplateInstantiation):
            return self.transform_template_instantiation(expr, writer)
        else:
            raise NotImplementedError('Unexpected expr: ' + expr.__class__.__name__)

    def transform_pattern(self, pattern: ir0.TemplateArgPatternLiteral) -> ir0.TemplateArgPatternLiteral:
        return pattern

    def transform_template_body_elem(self, elem: ir0.TemplateBodyElement, writer: TemplateBodyWriter):
        if isinstance(elem, ir0.TemplateDefn):
            self.transform_template_defn(elem, writer)
        elif isinstance(elem, ir0.StaticAssert):
            self.transform_static_assert(elem, writer)
        elif isinstance(elem, ir0.ConstantDef):
            self.transform_constant_def(elem, writer)
        elif isinstance(elem, ir0.Typedef):
            self.transform_typedef(elem, writer)
        else:
            raise NotImplementedError('Unexpected elem: ' + elem.__class__.__name__)

    def transform_literal(self, literal: ir0.Literal, writer: Writer) -> ir0.Expr:
        return literal

    def transform_type_literal(self, type_literal: ir0.TypeLiteral, writer: Writer) -> ir0.Expr:
        return self._transform_type_literal_default_impl(type_literal, writer)

    def _transform_type_literal_default_impl(self, type_literal: ir0.TypeLiteral, writer: Writer) -> ir0.TypeLiteral:
        return ir0.TypeLiteral(cpp_type=type_literal.cpp_type,
                               is_metafunction_that_may_return_error=type_literal.is_metafunction_that_may_return_error,
                               referenced_locals=[self._transform_type_literal_default_impl(literal, writer)
                                                  for literal in type_literal.referenced_locals],
                               type=type_literal.type,
                               is_local=type_literal.is_local)

    def transform_class_member_access(self, class_member_access: ir0.ClassMemberAccess, writer: Writer) -> ir0.Expr:
        return ir0.ClassMemberAccess(class_type_expr=self.transform_expr(class_member_access.expr, writer),
                                     member_name=class_member_access.member_name,
                                     member_type=class_member_access.type)

    def transform_not_expr(self, not_expr: ir0.NotExpr, writer: Writer) -> ir0.Expr:
        return ir0.NotExpr(self.transform_expr(not_expr.expr, writer))

    def transform_unary_minus_expr(self, unary_minus: ir0.UnaryMinusExpr, writer: Writer) -> ir0.Expr:
        return ir0.UnaryMinusExpr(self.transform_expr(unary_minus.expr, writer))

    def transform_comparison_expr(self, comparison: ir0.ComparisonExpr, writer: Writer) -> ir0.Expr:
        return ir0.ComparisonExpr(lhs=self.transform_expr(comparison.lhs, writer),
                                  rhs=self.transform_expr(comparison.rhs, writer),
                                  op=comparison.op)

    def transform_int64_binary_op_expr(self, binary_op: ir0.Int64BinaryOpExpr, writer: Writer) -> ir0.Expr:
        return ir0.Int64BinaryOpExpr(lhs=self.transform_expr(binary_op.lhs, writer),
                                     rhs=self.transform_expr(binary_op.rhs, writer),
                                     op=binary_op.op)

    def transform_template_instantiation(self, template_instantiation: ir0.TemplateInstantiation, writer: Writer) -> ir0.Expr:
        return ir0.TemplateInstantiation(template_expr=self.transform_expr(template_instantiation.template_expr, writer),
                                         args=[self.transform_expr(arg, writer) for arg in template_instantiation.args],
                                         instantiation_might_trigger_static_asserts=template_instantiation.instantiation_might_trigger_static_asserts)
