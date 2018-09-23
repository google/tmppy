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

from typing import List, Tuple, Set, Optional, Iterable, Union, Dict
from _py2tmp import ir0, utils

class Writer:
    def write(self, elem: Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]): ...  # pragma: no cover

    def write_toplevel_elem(self, elem: Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]): ...  # pragma: no cover

    def new_id(self) -> str: ...  # pragma: no cover

    def new_constant_or_typedef(self, expr: ir0.Expr) -> ir0.AtomicTypeLiteral:
        id = self.new_id()
        if expr.expr_type.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
            self.write(ir0.ConstantDef(name=id, expr=expr))
        elif expr.expr_type.kind in (ir0.ExprKind.TYPE, ir0.ExprKind.TEMPLATE):
            self.write(ir0.Typedef(name=id, expr=expr))
        else:
            # TODO: consider handling VARIADIC_TYPE too.
            raise NotImplementedError('Unexpected kind: ' + str(expr.expr_type.kind))

        return ir0.AtomicTypeLiteral.for_local(cpp_type=id, expr_type=expr.expr_type)

    def get_toplevel_writer(self) -> 'ToplevelWriter': ...  # pragma: no cover

class ToplevelWriter(Writer):
    def __init__(self, identifier_generator: Iterable[str], allow_toplevel_elems: bool = True, allow_template_defns: bool = True):
        self.identifier_generator = identifier_generator
        self.template_defns = []  # type: List[ir0.TemplateDefn]
        self.toplevel_elems = []  # type: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]]
        self.allow_toplevel_elems = allow_toplevel_elems
        self.allow_template_defns = allow_template_defns

    def write(self, elem: ir0.TemplateBodyElement):
        if isinstance(elem, ir0.TemplateDefn):
            assert self.allow_template_defns
            self.template_defns.append(elem)
        else:
            assert self.allow_toplevel_elems
            self.toplevel_elems.append(elem)

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

    def write_toplevel_elem(self, elem: ir0.TemplateBodyElement):
        self.toplevel_writer.write(elem)

    def write(self, elem: ir0.TemplateBodyElement):
        self.elems.append(elem)

    def get_toplevel_writer(self):
        return self.toplevel_writer

class Transformation:
    def __init__(self, generates_transformed_ir=True):
        self.generates_transformed_ir = generates_transformed_ir

    def transform_header(self, header: ir0.Header, identifier_generator: Iterable[str]) -> ir0.Header:
        writer = ToplevelWriter(identifier_generator)
        for template_defn in header.template_defns:
            self.transform_template_defn(template_defn, writer)

        for elem in header.toplevel_content:
            self.transform_toplevel_elem(elem, writer)

        if self.generates_transformed_ir:
            return ir0.Header(template_defns=writer.template_defns,
                              toplevel_content=writer.toplevel_elems,
                              public_names=header.public_names)

    def transform_toplevel_elem(self, elem: Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef], writer: Writer):
        if isinstance(elem, ir0.StaticAssert):
            self.transform_static_assert(elem, writer)
        elif isinstance(elem, ir0.ConstantDef):
            self.transform_constant_def(elem, writer)
        elif isinstance(elem, ir0.Typedef):
            self.transform_typedef(elem, writer)
        else:
            raise NotImplementedError('Unexpected elem: ' + elem.__class__.__name__)

    def transform_template_defn(self, template_defn: ir0.TemplateDefn, writer: Writer):
        args = [self.transform_template_arg_decl(arg_decl) for arg_decl in template_defn.args]
        template_specialization = self.transform_template_specialization(template_defn.main_definition,
                                                                         writer) if template_defn.main_definition is not None else None
        specializations = [self.transform_template_specialization(specialization, writer) for specialization in
                            template_defn.specializations]
        if self.generates_transformed_ir:
            writer.write(ir0.TemplateDefn(args=args,
                                          main_definition=template_specialization,
                                          specializations=specializations,
                                          name=template_defn.name,
                                          description=template_defn.description,
                                          result_element_names=template_defn.result_element_names))

    def transform_static_assert(self, static_assert: ir0.StaticAssert, writer: Writer):
        expr = self.transform_expr(static_assert.expr, writer)
        if self.generates_transformed_ir:
            writer.write(ir0.StaticAssert(expr=expr,
                                          message=static_assert.message))

    def transform_constant_def(self, constant_def: ir0.ConstantDef, writer: Writer):
        expr = self.transform_expr(constant_def.expr, writer)
        if self.generates_transformed_ir:
            writer.write(ir0.ConstantDef(name=constant_def.name, expr=expr))

    def transform_typedef(self, typedef: ir0.Typedef, writer: Writer):
        expr = self.transform_expr(typedef.expr, writer)
        if self.generates_transformed_ir:
            writer.write(ir0.Typedef(name=typedef.name, expr=expr))

    def transform_template_arg_decl(self, arg_decl: ir0.TemplateArgDecl) -> ir0.TemplateArgDecl:
        if self.generates_transformed_ir:
            return arg_decl

    def transform_template_body_elems(self,
                                      elems: List[ir0.TemplateBodyElement],
                                      writer: ToplevelWriter) -> List[ir0.TemplateBodyElement]:
        body_writer = TemplateBodyWriter(writer)
        for elem in elems:
            self.transform_template_body_elem(elem, body_writer)
        if self.generates_transformed_ir:
            return body_writer.elems

    def transform_template_specialization(self, specialization: ir0.TemplateSpecialization, writer: Writer) -> ir0.TemplateSpecialization:
        toplevel_writer = writer.get_toplevel_writer()

        if specialization.patterns is not None:
            patterns = [self.transform_pattern(pattern, writer)
                        for pattern in specialization.patterns]
        else:
            patterns = None

        args = [self.transform_template_arg_decl(arg_decl) for arg_decl in specialization.args]
        body = self.transform_template_body_elems(specialization.body, toplevel_writer)
        if self.generates_transformed_ir:
            return ir0.TemplateSpecialization(args=args,
                                              patterns=patterns,
                                              body=body,
                                              is_metafunction=specialization.is_metafunction)

    def transform_pattern(self, expr: ir0.Expr, writer: Writer) -> ir0.Expr:
        return self.transform_expr(expr, writer)

    def transform_expr(self, expr: ir0.Expr, writer: Writer) -> ir0.Expr:
        if isinstance(expr, ir0.Literal):
            return self.transform_literal(expr, writer)
        elif isinstance(expr, ir0.AtomicTypeLiteral):
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
        elif isinstance(expr, ir0.PointerTypeExpr):
            return self.transform_pointer_type_expr(expr, writer)
        elif isinstance(expr, ir0.ReferenceTypeExpr):
            return self.transform_reference_type_expr(expr, writer)
        elif isinstance(expr, ir0.RvalueReferenceTypeExpr):
            return self.transform_rvalue_reference_type_expr(expr, writer)
        elif isinstance(expr, ir0.ConstTypeExpr):
            return self.transform_const_type_expr(expr, writer)
        elif isinstance(expr, ir0.ArrayTypeExpr):
            return self.transform_array_type_expr(expr, writer)
        elif isinstance(expr, ir0.FunctionTypeExpr):
            return self.transform_function_type_expr(expr, writer)
        elif isinstance(expr, ir0.VariadicTypeExpansion):
            return self.transform_variadic_type_expansion(expr, writer)
        else:
            raise NotImplementedError('Unexpected expr: ' + expr.__class__.__name__)

    def transform_exprs(self, exprs: List[ir0.Expr], parent_element_type, writer: Writer) -> List[ir0.Expr]:
        exprs = [self.transform_expr(expr, writer) for expr in exprs]
        if self.generates_transformed_ir:
            return exprs

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
        if self.generates_transformed_ir:
            return literal

    def transform_type_literal(self, type_literal: ir0.AtomicTypeLiteral, writer: Writer) -> ir0.Expr:
        return self._transform_type_literal_default_impl(type_literal, writer)

    def _transform_type_literal_default_impl(self, type_literal: ir0.AtomicTypeLiteral, writer: Writer) -> ir0.AtomicTypeLiteral:
        if self.generates_transformed_ir:
            return ir0.AtomicTypeLiteral(cpp_type=type_literal.cpp_type,
                                         is_metafunction_that_may_return_error=type_literal.is_metafunction_that_may_return_error,
                                         expr_type=type_literal.expr_type,
                                         is_local=type_literal.is_local,
                                         may_be_alias=type_literal.may_be_alias)

    def transform_class_member_access(self, class_member_access: ir0.ClassMemberAccess, writer: Writer) -> ir0.Expr:
        class_type_expr = self.transform_expr(class_member_access.expr, writer)
        if self.generates_transformed_ir:
            return ir0.ClassMemberAccess(class_type_expr=class_type_expr,
                                         member_name=class_member_access.member_name,
                                         member_type=class_member_access.expr_type)

    def transform_not_expr(self, not_expr: ir0.NotExpr, writer: Writer) -> ir0.Expr:
        expr = self.transform_expr(not_expr.expr, writer)
        if self.generates_transformed_ir:
            return ir0.NotExpr(expr)

    def transform_unary_minus_expr(self, unary_minus: ir0.UnaryMinusExpr, writer: Writer) -> ir0.Expr:
        expr = self.transform_expr(unary_minus.expr, writer)
        if self.generates_transformed_ir:
            return ir0.UnaryMinusExpr(expr)

    def transform_comparison_expr(self, comparison: ir0.ComparisonExpr, writer: Writer) -> ir0.Expr:
        exprs = self.transform_exprs([comparison.lhs, comparison.rhs], ir0.ComparisonExpr, writer)
        if self.generates_transformed_ir:
            lhs, rhs = exprs
            return ir0.ComparisonExpr(lhs=lhs, rhs=rhs, op=comparison.op)

    def transform_int64_binary_op_expr(self, binary_op: ir0.Int64BinaryOpExpr, writer: Writer) -> ir0.Expr:
        exprs = self.transform_exprs([binary_op.lhs, binary_op.rhs], ir0.Int64BinaryOpExpr, writer)
        if self.generates_transformed_ir:
            lhs, rhs = exprs
            return ir0.Int64BinaryOpExpr(lhs=lhs, rhs=rhs, op=binary_op.op)

    def transform_template_instantiation(self, template_instantiation: ir0.TemplateInstantiation, writer: Writer) -> ir0.Expr:
        result = self.transform_exprs([template_instantiation.template_expr, *template_instantiation.args], ir0.TemplateInstantiation, writer)
        if self.generates_transformed_ir:
            [template_expr, *args] = result
            return ir0.TemplateInstantiation(template_expr=template_expr,
                                             args=args,
                                             instantiation_might_trigger_static_asserts=template_instantiation.instantiation_might_trigger_static_asserts)

    def transform_pointer_type_expr(self, expr: ir0.PointerTypeExpr, writer: Writer):
        expr = self.transform_expr(expr.type_expr, writer)
        if self.generates_transformed_ir:
            return ir0.PointerTypeExpr(expr)

    def transform_reference_type_expr(self, expr: ir0.ReferenceTypeExpr, writer: Writer):
        expr = self.transform_expr(expr.type_expr, writer)
        if self.generates_transformed_ir:
            return ir0.ReferenceTypeExpr(expr)

    def transform_rvalue_reference_type_expr(self, expr: ir0.RvalueReferenceTypeExpr, writer: Writer):
        expr = self.transform_expr(expr.type_expr, writer)
        if self.generates_transformed_ir:
            return ir0.RvalueReferenceTypeExpr(expr)

    def transform_const_type_expr(self, expr: ir0.ConstTypeExpr, writer: Writer):
        expr = self.transform_expr(expr.type_expr, writer)
        if self.generates_transformed_ir:
            return ir0.ConstTypeExpr(expr)

    def transform_array_type_expr(self, expr: ir0.ArrayTypeExpr, writer: Writer):
        expr = self.transform_expr(expr.type_expr, writer)
        if self.generates_transformed_ir:
            return ir0.ArrayTypeExpr(expr)

    def transform_function_type_expr(self, expr: ir0.FunctionTypeExpr, writer: Writer):
        result = self.transform_exprs([expr.return_type_expr, *expr.arg_exprs], ir0.FunctionTypeExpr, writer)
        if self.generates_transformed_ir:
            [return_type_expr, *arg_exprs] = result
            return ir0.FunctionTypeExpr(return_type_expr=return_type_expr, arg_exprs=arg_exprs)

    def transform_variadic_type_expansion(self, expr: ir0.VariadicTypeExpansion, writer: Writer):
        expr = self.transform_expr(expr.expr, writer)
        if self.generates_transformed_ir:
            return ir0.VariadicTypeExpansion(expr)

class NameReplacementTransformation(Transformation):
    def __init__(self, replacements: Dict[str, str]):
        super().__init__()
        self.replacements = replacements

    def transform_type_literal(self, type_literal: ir0.AtomicTypeLiteral, writer: Writer):
        return ir0.AtomicTypeLiteral(cpp_type=self.replacements.get(type_literal.cpp_type, type_literal.cpp_type),
                                     is_local=type_literal.is_local,
                                     is_metafunction_that_may_return_error=type_literal.is_metafunction_that_may_return_error,
                                     expr_type=type_literal.expr_type,
                                     may_be_alias=type_literal.may_be_alias)

    def transform_constant_def(self, constant_def: ir0.ConstantDef, writer: Writer):
        writer.write(ir0.ConstantDef(name=self._transform_name(constant_def.name),
                                     expr=self.transform_expr(constant_def.expr, writer)))

    def transform_typedef(self, typedef: ir0.Typedef, writer: Writer):
        writer.write(ir0.Typedef(name=self._transform_name(typedef.name),
                                 expr=self.transform_expr(typedef.expr, writer)))

    def transform_template_defn(self, template_defn: ir0.TemplateDefn, writer: Writer):
        writer.write(ir0.TemplateDefn(args=[self.transform_template_arg_decl(arg_decl) for arg_decl in template_defn.args],
                                      main_definition=self.transform_template_specialization(template_defn.main_definition, writer)
                                          if template_defn.main_definition is not None else None,
                                      specializations=[self.transform_template_specialization(specialization, writer)
                                                       for specialization in template_defn.specializations],
                                      name=self._transform_name(template_defn.name),
                                      description=template_defn.description,
                                      result_element_names=template_defn.result_element_names))

    def transform_template_arg_decl(self, arg_decl: ir0.TemplateArgDecl):
        return ir0.TemplateArgDecl(expr_type=arg_decl.expr_type,
                                   name=self._transform_name(arg_decl.name))

    def _transform_name(self, name: str):
        if name in self.replacements:
            return self.replacements[name]
        else:
            return name
