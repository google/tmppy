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
from contextlib import contextmanager
from typing import Union, Mapping, Optional, Iterator, Tuple

from _py2tmp.ir0 import ir
from _py2tmp.ir0._is_variadic import is_expr_variadic
from _py2tmp.ir0._writers import Writer, ToplevelWriter, TemplateBodyWriter


# noinspection PyMethodMayBeStatic
class Transformation:
    def __init__(self, identifier_generator: Optional[Iterator[str]] = None):
        self.writer: Optional[Writer] = None
        self.identifier_generator = identifier_generator

    def transform_header(self, header: ir.Header) -> ir.Header:
        writer = ToplevelWriter()
        with self.set_writer(writer):
            for template_defn in header.template_defns:
                self.transform_template_defn(template_defn)
            for elem in header.toplevel_content:
                self.transform_toplevel_elem(elem)
            check_if_error_specializations = tuple(self.transform_template_specialization(specialization)
                                                   for specialization in header.check_if_error_specializations)

        return ir.Header(template_defns=tuple(writer.template_defns),
                         toplevel_content=tuple(writer.toplevel_elems),
                         public_names=header.public_names,
                         split_template_name_by_old_name_and_result_element_name=header.split_template_name_by_old_name_and_result_element_name,
                         check_if_error_specializations=check_if_error_specializations)

    def transform_toplevel_elem(self, elem: Union[ir.StaticAssert, ir.ConstantDef, ir.Typedef]):
        if isinstance(elem, ir.StaticAssert):
            self.transform_static_assert(elem)
        elif isinstance(elem, ir.ConstantDef):
            self.transform_constant_def(elem)
        elif isinstance(elem, ir.Typedef):
            self.transform_typedef(elem)
        elif isinstance(elem, ir.NoOpStmt):
            self.transform_no_op_stmt(elem)
        else:
            raise NotImplementedError('Unexpected elem: ' + elem.__class__.__name__)

    def transform_template_defn(self, template_defn: ir.TemplateDefn):
        args = tuple(self.transform_template_arg_decl(arg_decl) for arg_decl in template_defn.args)
        template_specialization = self.transform_template_specialization(template_defn.main_definition) if template_defn.main_definition is not None else None
        specializations = tuple(self.transform_template_specialization(specialization)
                                for specialization in template_defn.specializations)
        self.writer.write(ir.TemplateDefn(args=args,
                                          main_definition=template_specialization,
                                          specializations=specializations,
                                          name=template_defn.name,
                                          description=template_defn.description,
                                          result_element_names=template_defn.result_element_names))

    def transform_static_assert(self, static_assert: ir.StaticAssert):
        expr = self.transform_expr(static_assert.expr)
        self.writer.write(ir.StaticAssert(expr=expr,
                                          message=static_assert.message))

    def transform_no_op_stmt(self, stmt: ir.NoOpStmt):
        self.writer.write(stmt)

    def transform_constant_def(self, constant_def: ir.ConstantDef):
        expr = self.transform_expr(constant_def.expr)
        self.writer.write(ir.ConstantDef(name=constant_def.name, expr=expr))

    def transform_typedef(self, typedef: ir.Typedef):
        expr = self.transform_expr(typedef.expr)
        self.writer.write(ir.Typedef(name=typedef.name,
                                     expr=expr,
                                     description=typedef.description,
                                     template_args=tuple(self.transform_template_arg_decl(arg_decl)
                                                         for arg_decl in typedef.template_args)))

    def transform_template_arg_decl(self, arg_decl: ir.TemplateArgDecl) -> ir.TemplateArgDecl:
        return arg_decl

    def transform_template_body_elems(self,
                                      elems: Tuple[ir.TemplateBodyElement, ...]) -> Tuple[ir.TemplateBodyElement, ...]:
        body_writer = TemplateBodyWriter(self.writer.toplevel_writer) if self.writer else TemplateBodyWriter(None)
        with self.set_writer(body_writer):
            for elem in elems:
                self.transform_template_body_elem(elem)
        return tuple(body_writer.elems)

    def transform_template_specialization(self, specialization: ir.TemplateSpecialization) -> ir.TemplateSpecialization:
        if specialization.patterns is not None:
            patterns = tuple(self.transform_pattern(pattern)
                             for pattern in specialization.patterns)
        else:
            patterns = None

        args = tuple(self.transform_template_arg_decl(arg_decl) for arg_decl in specialization.args)
        body = self.transform_template_body_elems(specialization.body)
        return ir.TemplateSpecialization(args=args,
                                         patterns=patterns,
                                         body=body,
                                         is_metafunction=specialization.is_metafunction)

    def transform_pattern(self, expr: ir.Expr) -> ir.Expr:
        return self.transform_expr(expr)

    def transform_expr(self, expr: ir.Expr) -> ir.Expr:
        if isinstance(expr, ir.Literal):
            return self.transform_literal(expr)
        elif isinstance(expr, ir.AtomicTypeLiteral):
            return self.transform_type_literal(expr)
        elif isinstance(expr, ir.ClassMemberAccess):
            return self.transform_class_member_access(expr)
        elif isinstance(expr, ir.NotExpr):
            return self.transform_not_expr(expr)
        elif isinstance(expr, ir.UnaryMinusExpr):
            return self.transform_unary_minus_expr(expr)
        elif isinstance(expr, ir.ComparisonExpr):
            return self.transform_comparison_expr(expr)
        elif isinstance(expr, ir.Int64BinaryOpExpr):
            return self.transform_int64_binary_op_expr(expr)
        elif isinstance(expr, ir.BoolBinaryOpExpr):
            return self.transform_bool_binary_op_expr(expr)
        elif isinstance(expr, ir.TemplateInstantiation):
            return self.transform_template_instantiation(expr)
        elif isinstance(expr, ir.PointerTypeExpr):
            return self.transform_pointer_type_expr(expr)
        elif isinstance(expr, ir.ReferenceTypeExpr):
            return self.transform_reference_type_expr(expr)
        elif isinstance(expr, ir.RvalueReferenceTypeExpr):
            return self.transform_rvalue_reference_type_expr(expr)
        elif isinstance(expr, ir.ConstTypeExpr):
            return self.transform_const_type_expr(expr)
        elif isinstance(expr, ir.ArrayTypeExpr):
            return self.transform_array_type_expr(expr)
        elif isinstance(expr, ir.FunctionTypeExpr):
            return self.transform_function_type_expr(expr)
        elif isinstance(expr, ir.VariadicTypeExpansion):
            return self.transform_variadic_type_expansion(expr)
        else:
            raise NotImplementedError('Unexpected expr: ' + expr.__class__.__name__)

    def transform_exprs(self, exprs: Tuple[ir.Expr, ...], original_parent_element: ir.Expr) -> Tuple[ir.Expr, ...]:
        return tuple(self.transform_expr(expr) for expr in exprs)

    def transform_template_body_elem(self, elem: Union[ir.TemplateDefn, ir.StaticAssert, ir.ConstantDef, ir.Typedef]):
        if isinstance(elem, ir.TemplateDefn):
            self.transform_template_defn(elem)
        elif isinstance(elem, ir.StaticAssert):
            self.transform_static_assert(elem)
        elif isinstance(elem, ir.ConstantDef):
            self.transform_constant_def(elem)
        elif isinstance(elem, ir.Typedef):
            self.transform_typedef(elem)
        elif isinstance(elem, ir.NoOpStmt):
            self.transform_no_op_stmt(elem)
        else:
            raise NotImplementedError('Unexpected elem: ' + elem.__class__.__name__)

    def transform_literal(self, literal: ir.Literal) -> ir.Expr:
        return literal

    def transform_type_literal(self, type_literal: ir.AtomicTypeLiteral) -> ir.Expr:
        return ir.AtomicTypeLiteral(cpp_type=type_literal.cpp_type,
                                    is_metafunction_that_may_return_error=type_literal.is_metafunction_that_may_return_error,
                                    expr_type=type_literal.expr_type,
                                    is_local=type_literal.is_local,
                                    may_be_alias=type_literal.may_be_alias,
                                    is_variadic=type_literal.is_variadic)

    def transform_class_member_access(self, class_member_access: ir.ClassMemberAccess) -> ir.Expr:
        class_type_expr = self.transform_expr(class_member_access.inner_expr)
        return ir.ClassMemberAccess(inner_expr=class_type_expr,
                                    member_name=class_member_access.member_name,
                                    expr_type=class_member_access.expr_type)

    def transform_not_expr(self, not_expr: ir.NotExpr) -> ir.Expr:
        expr = self.transform_expr(not_expr.inner_expr)
        return ir.NotExpr(expr)

    def transform_unary_minus_expr(self, unary_minus: ir.UnaryMinusExpr) -> ir.Expr:
        expr = self.transform_expr(unary_minus.inner_expr)
        return ir.UnaryMinusExpr(expr)

    def transform_comparison_expr(self, comparison: ir.ComparisonExpr) -> ir.Expr:
        lhs, rhs = self.transform_exprs((comparison.lhs, comparison.rhs), comparison)
        return ir.ComparisonExpr(lhs=lhs, rhs=rhs, op=comparison.op)

    def transform_int64_binary_op_expr(self, binary_op: ir.Int64BinaryOpExpr) -> ir.Expr:
        lhs, rhs = self.transform_exprs((binary_op.lhs, binary_op.rhs), binary_op)
        return ir.Int64BinaryOpExpr(lhs=lhs, rhs=rhs, op=binary_op.op)

    def transform_bool_binary_op_expr(self, binary_op: ir.BoolBinaryOpExpr) -> ir.Expr:
        lhs, rhs = self.transform_exprs((binary_op.lhs, binary_op.rhs), binary_op)
        return ir.BoolBinaryOpExpr(lhs=lhs, rhs=rhs, op=binary_op.op)

    def transform_template_instantiation(self, template_instantiation: ir.TemplateInstantiation) -> ir.Expr:
        [template_expr, *args] = self.transform_exprs((template_instantiation.template_expr, *template_instantiation.args), template_instantiation)
        return ir.TemplateInstantiation(template_expr=template_expr,
                                        args=tuple(args),
                                        instantiation_might_trigger_static_asserts=template_instantiation.instantiation_might_trigger_static_asserts)

    def transform_pointer_type_expr(self, expr: ir.PointerTypeExpr):
        expr = self.transform_expr(expr.type_expr)
        return ir.PointerTypeExpr(expr)

    def transform_reference_type_expr(self, expr: ir.ReferenceTypeExpr):
        expr = self.transform_expr(expr.type_expr)
        return ir.ReferenceTypeExpr(expr)

    def transform_rvalue_reference_type_expr(self, expr: ir.RvalueReferenceTypeExpr):
        expr = self.transform_expr(expr.type_expr)
        return ir.RvalueReferenceTypeExpr(expr)

    def transform_const_type_expr(self, expr: ir.ConstTypeExpr):
        expr = self.transform_expr(expr.type_expr)
        return ir.ConstTypeExpr(expr)

    def transform_array_type_expr(self, expr: ir.ArrayTypeExpr):
        expr = self.transform_expr(expr.type_expr)
        return ir.ArrayTypeExpr(expr)

    def transform_function_type_expr(self, expr: ir.FunctionTypeExpr):
        result = self.transform_exprs((expr.return_type_expr, *expr.arg_exprs), expr)
        [return_type_expr, *arg_exprs] = result
        return ir.FunctionTypeExpr(return_type_expr=return_type_expr, arg_exprs=tuple(arg_exprs))

    def transform_variadic_type_expansion(self, expr: ir.VariadicTypeExpansion):
        expr = self.transform_expr(expr.inner_expr)
        if is_expr_variadic(expr):
            return ir.VariadicTypeExpansion(expr)
        else:
            # This is not just an optimization, it's an error to have a VariadicTypeExpansion() that doesn't contain
            # any variadic var refs.
            return expr

    @contextmanager
    def set_writer(self, new_writer: Optional[Writer]):
        old_writer = self.writer
        self.writer = new_writer
        yield
        self.writer = old_writer

class NameReplacementTransformation(Transformation):
    def __init__(self, replacements: Mapping[str, str]):
        super().__init__()
        self.replacements = replacements

    def transform_type_literal(self, type_literal: ir.AtomicTypeLiteral):
        return ir.AtomicTypeLiteral(cpp_type=self.replacements.get(type_literal.cpp_type, type_literal.cpp_type),
                                    is_local=type_literal.is_local,
                                    is_metafunction_that_may_return_error=type_literal.is_metafunction_that_may_return_error,
                                    expr_type=type_literal.expr_type,
                                    may_be_alias=type_literal.may_be_alias,
                                    is_variadic=type_literal.is_variadic)

    def transform_constant_def(self, constant_def: ir.ConstantDef):
        self.writer.write(ir.ConstantDef(name=self._transform_name(constant_def.name),
                                         expr=self.transform_expr(constant_def.expr)))

    def transform_typedef(self, typedef: ir.Typedef):
        self.writer.write(ir.Typedef(name=self._transform_name(typedef.name),
                                     expr=self.transform_expr(typedef.expr),
                                     description=typedef.description,
                                     template_args=typedef.template_args))

    def transform_template_defn(self, template_defn: ir.TemplateDefn):
        self.writer.write(
            ir.TemplateDefn(args=tuple(self.transform_template_arg_decl(arg_decl) for arg_decl in template_defn.args),
                            main_definition=self.transform_template_specialization(template_defn.main_definition)
                                           if template_defn.main_definition is not None else None,
                            specializations=tuple(self.transform_template_specialization(specialization)
                                                  for specialization in template_defn.specializations),
                            name=self._transform_name(template_defn.name),
                            description=template_defn.description,
                            result_element_names=template_defn.result_element_names))

    def transform_template_arg_decl(self, arg_decl: ir.TemplateArgDecl):
        return ir.TemplateArgDecl(expr_type=arg_decl.expr_type,
                                  name=self._transform_name(arg_decl.name),
                                  is_variadic=arg_decl.is_variadic)

    def _transform_name(self, name: str):
        if name in self.replacements:
            return self.replacements[name]
        else:
            return name
