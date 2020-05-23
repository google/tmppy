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
from typing import Set, Dict, Tuple

from _py2tmp.compiler.stages import expr_to_cpp_simple
from _py2tmp.ir0 import ir0, Visitor, Transformation, ir


def _is_trivial_pattern(arg_decl: ir0.TemplateArgDecl, pattern: ir0.Expr):
    if isinstance(pattern, ir0.AtomicTypeLiteral):
        return arg_decl.name == pattern.cpp_type
    elif isinstance(pattern, ir0.VariadicTypeExpansion) and isinstance(pattern.inner_expr, ir0.AtomicTypeLiteral):
        return arg_decl.is_variadic and arg_decl.name == pattern.inner_expr.cpp_type
    else:
        return False

def _determine_template_arg_indexes_that_can_be_moved_to_typedef_args(template_defn: ir0.TemplateDefn):
    arguments_with_non_trivial_patterns = set()
    contains_only_simple_typedefs = True

    for specialization in template_defn.all_definitions:
        contains_only_simple_typedefs &= all(isinstance(elem, ir0.Typedef) and not elem.template_args
                                             for elem in specialization.body)
        if specialization.patterns:
            for arg_decl, pattern in zip(template_defn.args, specialization.patterns):
                if not _is_trivial_pattern(arg_decl, pattern):
                    arguments_with_non_trivial_patterns.add(arg_decl.name)
            if len(template_defn.args) != len(specialization.patterns):
                assert template_defn.args[-1].is_variadic, 'Template defn args: %s, patterns: %s' % ({arg.name for arg in template_defn.args},
                                                                                                     [expr_to_cpp_simple(expr)
                                                                                                      for expr in specialization.patterns])
                arguments_with_non_trivial_patterns.add(template_defn.args[-1].name)

    if contains_only_simple_typedefs:
        if len(arguments_with_non_trivial_patterns) == 0:
            # So that there's always at least 1 template argument.
            arguments_with_non_trivial_patterns.add(template_defn.args[0].name)

        return {arg_index
                for arg_index, arg in enumerate(template_defn.args)
                if arg.name not in arguments_with_non_trivial_patterns}
    else:
        return set()

class _DetermineTemplatesThatCanBeReplaced(Visitor):
    def __init__(self) -> None:
        self.all_defined_template_names: Set[str] = set()
        self.template_names_that_cant_be_replaced: Set[str] = set()
        self.movable_arg_indexes_by_template_name: Dict[str, Set[int]] = dict()

    def visit_template_defn(self, template_defn: ir0.TemplateDefn):
        super().visit_template_defn(template_defn)
        self.all_defined_template_names.add(template_defn.name)
        arg_indexes = _determine_template_arg_indexes_that_can_be_moved_to_typedef_args(template_defn)

        if arg_indexes:
            self.movable_arg_indexes_by_template_name[template_defn.name] = arg_indexes
        else:
            self.template_names_that_cant_be_replaced.add(template_defn.name)

    def visit_header(self, header: ir0.Header):
        super().visit_header(header)
        for template_name in header.public_names:
            self.template_names_that_cant_be_replaced.add(template_name)

    def visit_class_member_access(self, class_member_access: ir0.ClassMemberAccess):
        if (isinstance(class_member_access.inner_expr, ir0.TemplateInstantiation)
                and isinstance(class_member_access.inner_expr.template_expr, ir0.AtomicTypeLiteral)):
            # This metafunction call can be transformed to use a templated using declaration, so we don't visit the
            # AtomicTypeLiteral.
            super().visit_exprs(class_member_access.inner_expr.args)
        else:
            super().visit_class_member_access(class_member_access)

    def visit_type_literal(self, type_literal: ir0.AtomicTypeLiteral):
        if isinstance(type_literal.expr_type, ir0.TemplateType) and not type_literal.is_local:
            self.template_names_that_cant_be_replaced.add(type_literal.cpp_type)

class _ApplyReplacement(Transformation):
    def __init__(self,
                 movable_arg_indexes_by_template_name: Dict[str, Set[int]]):
        super().__init__()
        self.movable_arg_indexes_by_template_name = movable_arg_indexes_by_template_name
        self.movable_arg_indexes_in_current_template: Set[int] = set()
        self.additional_typedef_args_in_current_template: Tuple[ir0.TemplateArgDecl, ...] = ()
        self.locals_to_instantiate: Set[str] = set()

    def transform_template_defn(self, template_defn: ir0.TemplateDefn):
        if template_defn.name not in self.movable_arg_indexes_by_template_name:
            super().transform_template_defn(template_defn)
            return

        assert not self.movable_arg_indexes_in_current_template
        assert not self.additional_typedef_args_in_current_template
        self.movable_arg_indexes_in_current_template = self.movable_arg_indexes_by_template_name[template_defn.name]
        self.additional_typedef_args_in_current_template = tuple(arg_decl
                                                                 for index, arg_decl in enumerate(template_defn.args)
                                                                 if index in self.movable_arg_indexes_in_current_template)
        args = tuple(arg_decl
                     for index, arg_decl in enumerate(template_defn.args)
                     if index not in self.movable_arg_indexes_in_current_template)


        template_specialization = self.transform_template_specialization(template_defn.main_definition) if template_defn.main_definition is not None else None
        specializations = tuple(self.transform_template_specialization(specialization)
                                for specialization in template_defn.specializations)

        self.writer.write(ir.TemplateDefn(args=args,
                                          main_definition=template_specialization,
                                          specializations=specializations,
                                          name=template_defn.name,
                                          description=template_defn.description,
                                          result_element_names=template_defn.result_element_names))

        self.movable_arg_indexes_in_current_template = set()
        self.additional_typedef_args_in_current_template = ()
        self.locals_to_instantiate = set()

    def transform_template_specialization(self, specialization: ir.TemplateSpecialization):
        if specialization.patterns is not None:
            patterns = [pattern
                        for index, pattern in enumerate(specialization.patterns)
                        if not index in self.movable_arg_indexes_in_current_template]
        else:
            patterns = None

        args = tuple(self.transform_template_arg_decl(arg_decl)
                     for index, arg_decl in enumerate(specialization.args)
                     if not index in self.movable_arg_indexes_in_current_template)

        body = self.transform_template_body_elems(specialization.body)
        return ir.TemplateSpecialization(args=args,
                                         patterns=patterns,
                                         body=body,
                                         is_metafunction=specialization.is_metafunction)

    def transform_typedef(self, typedef: ir.Typedef):
        expr = self.transform_expr(typedef.expr)
        if self.additional_typedef_args_in_current_template:
            assert not typedef.template_args
            self.locals_to_instantiate.add(typedef.name)
            self.writer.write(ir.Typedef(name=typedef.name,
                                         expr=expr,
                                         description=typedef.description,
                                         template_args=self.additional_typedef_args_in_current_template))
        else:
            self.writer.write(ir.Typedef(name=typedef.name,
                                         expr=expr,
                                         description=typedef.description,
                                         template_args=typedef.template_args))

    def transform_type_literal(self, type_literal: ir.AtomicTypeLiteral):
        if self.additional_typedef_args_in_current_template and type_literal.cpp_type in self.locals_to_instantiate:
            assert isinstance(type_literal.expr_type, ir0.TypeType)
            # X5 -> X5<T, U>,  if X5 is defined by a local typedef and we're moving {X,U} to be typedef template args
            # instead of args of the template defn.
            return ir0.TemplateInstantiation(template_expr=ir.AtomicTypeLiteral.for_local(cpp_type=type_literal.cpp_type,
                                                                                          expr_type=ir0.TemplateType(tuple(ir0.TemplateArgType(expr_type=arg.expr_type,
                                                                                                                                               is_variadic=arg.is_variadic)
                                                                                                                           for arg in self.additional_typedef_args_in_current_template)),
                                                                                          is_variadic=False),
                                             args=tuple(ir0.AtomicTypeLiteral.for_local(cpp_type=arg.name,
                                                                                        expr_type=arg.expr_type,
                                                                                        is_variadic=arg.is_variadic)
                                                        for arg in self.additional_typedef_args_in_current_template),
                                             instantiation_might_trigger_static_asserts=False)
        else:
            return type_literal

    def transform_class_member_access(self, class_member_access: ir0.ClassMemberAccess):
        if (isinstance(class_member_access.inner_expr, ir0.TemplateInstantiation)
                and isinstance(class_member_access.inner_expr.template_expr, ir0.AtomicTypeLiteral)
                and class_member_access.inner_expr.template_expr.cpp_type in self.movable_arg_indexes_by_template_name):
            assert isinstance(class_member_access.inner_expr.template_expr.expr_type, ir0.TemplateType)
            # F<X, Y>::type -> F<X>::type<Y>  (if X is used in non-trivial patterns and Y isn't)

            args = self.transform_exprs(class_member_access.inner_expr.args, class_member_access.inner_expr)

            movable_arg_indexes = self.movable_arg_indexes_by_template_name[class_member_access.inner_expr.template_expr.cpp_type]
            template_instantiation_arg_exprs = tuple(arg
                                                     for index, arg in enumerate(args)
                                                     if index not in movable_arg_indexes)
            typedef_instantiation_arg_exprs = tuple(arg
                                                    for index, arg in enumerate(args)
                                                    if index in movable_arg_indexes)
            typedef_instantiation_arg_types = tuple(arg_type
                                                    for index, arg_type in enumerate(class_member_access.inner_expr.template_expr.expr_type.args)
                                                    if index in movable_arg_indexes)

            template_instantiation = ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=class_member_access.inner_expr.template_expr.cpp_type,
                                                                                                                         args=tuple(arg
                                                                                                                                    for index, arg in enumerate(class_member_access.inner_expr.template_expr.expr_type.args)
                                                                                                                                    if index not in movable_arg_indexes),
                                                                                                                         is_metafunction_that_may_return_error=class_member_access.inner_expr.template_expr.is_metafunction_that_may_return_error,
                                                                                                                         may_be_alias=True),
                                                               args=template_instantiation_arg_exprs,
                                                               instantiation_might_trigger_static_asserts=class_member_access.inner_expr.instantiation_might_trigger_static_asserts)

            new_class_member_access = ir0.ClassMemberAccess(inner_expr=template_instantiation,
                                                            member_name=class_member_access.member_name,
                                                            expr_type=ir0.TemplateType(typedef_instantiation_arg_types))

            return ir0.TemplateInstantiation(template_expr=new_class_member_access,
                                             args=typedef_instantiation_arg_exprs,
                                             instantiation_might_trigger_static_asserts=class_member_access.inner_expr.instantiation_might_trigger_static_asserts)
        else:
            return super().transform_class_member_access(class_member_access)

def move_template_args_to_using_declarations(header: ir0.Header):
    visitor = _DetermineTemplatesThatCanBeReplaced()
    visitor.visit_header(header)

    transformation = _ApplyReplacement(movable_arg_indexes_by_template_name={template_name: arg_indexes
                                                                             for template_name, arg_indexes in visitor.movable_arg_indexes_by_template_name.items()
                                                                             if template_name not in visitor.template_names_that_cant_be_replaced})
    return transformation.transform_header(header)
