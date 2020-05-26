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
import itertools
from typing import Dict, Iterator, Set, List, Union, AbstractSet, Tuple

from _py2tmp.compiler.stages import expr_to_cpp_simple, template_defn_to_cpp_simple
from _py2tmp.compiler.output_files import ObjectFileContent
from _py2tmp.ir0 import ir
from _py2tmp.ir0 import select1st_literal
from _py2tmp.ir0_optimization._configuration_knobs import ConfigurationKnobs
from _py2tmp.ir0 import NameReplacementTransformation, ToplevelWriter, Transformation, \
    TemplateBodyWriter
from _py2tmp.ir0_optimization._compute_non_expanded_variadic_vars import compute_non_expanded_variadic_vars
from _py2tmp.ir0_optimization._local_optimizations import perform_local_optimizations_on_template_defn, \
    perform_local_optimizations_on_toplevel_elems
from _py2tmp.ir0_optimization._optimization_execution import apply_elem_optimization, describe_template_defns, \
    describe_toplevel_elems
from _py2tmp.ir0_optimization._replace_var_with_expr import replace_var_with_expr_in_template_body_elements, \
    VariadicVarReplacementNotPossibleException, replace_var_with_expr_in_expr
from _py2tmp.ir0_optimization._unify import unify_template_instantiation_with_definition

_select1st_type_and_name = [
    (ir.BoolType(), 'Bool'),
    (ir.Int64Type(), 'Int64'),
    (ir.TypeType(), 'Type'),
]

TEMPLATE_DEFNS_DEFINED_AS_IR0 = [
    ir.TemplateDefn(name='std::is_same',
                    description='',
                    result_element_names=frozenset(('value',)),
                    args=(ir.TemplateArgDecl(name='T', expr_type=ir.TypeType(), is_variadic=False),
                          ir.TemplateArgDecl(name='U', expr_type=ir.TypeType(), is_variadic=False)),
                    main_definition=ir.TemplateSpecialization(args=(
                         ir.TemplateArgDecl(name='T', expr_type=ir.TypeType(), is_variadic=False),
                         ir.TemplateArgDecl(name='U', expr_type=ir.TypeType(), is_variadic=False)),
                                                                patterns=None,
                                                                body=(ir.ConstantDef(name='value',
                                                                                     expr=ir.Literal(False)),),
                                                                is_metafunction=True),
                    specializations=(ir.TemplateSpecialization(args=(ir.TemplateArgDecl(name='T', expr_type=ir.TypeType(), is_variadic=False),),
                                                               patterns=(ir.AtomicTypeLiteral.for_local(cpp_type='T', expr_type=ir.TypeType(), is_variadic=False),
                                                                         ir.AtomicTypeLiteral.for_local(cpp_type='T', expr_type=ir.TypeType(), is_variadic=False)),
                                                               body=(ir.ConstantDef(name='value',
                                                                                    expr=ir.Literal(True)),),
                                                               is_metafunction=True),)),
    ir.TemplateDefn(name='std::add_pointer',
                    description='',
                    result_element_names=frozenset(('type',)),
                    main_definition=ir.TemplateSpecialization(args=(ir.TemplateArgDecl(name='T', expr_type=ir.TypeType(), is_variadic=False),),
                                                              patterns=None,
                                                              body=(ir.Typedef(name='type',
                                                                               expr=ir.PointerTypeExpr(
                                                                                    ir.AtomicTypeLiteral.for_local('T', ir.TypeType(), is_variadic=False))),),
                                                              is_metafunction=True),
                    specializations=()),

    ir.TemplateDefn(name='std::remove_pointer',
                    description='',
                    result_element_names=frozenset(('type',)),
                    args=(ir.TemplateArgDecl(name='T', expr_type=ir.TypeType(), is_variadic=False),),
                    main_definition=ir.TemplateSpecialization(args=(ir.TemplateArgDecl(name='T', expr_type=ir.TypeType(), is_variadic=False),),
                                                              patterns=None,
                                                              body=(ir.Typedef(name='type',
                                                                               expr=ir.AtomicTypeLiteral.for_local('T', ir.TypeType(), is_variadic=False)),),
                                                              is_metafunction=True),
                    specializations=(ir.TemplateSpecialization(args=(ir.TemplateArgDecl(name='T', expr_type=ir.TypeType(), is_variadic=False),),
                                                                 patterns=(ir.PointerTypeExpr(
                                                                     ir.AtomicTypeLiteral.for_local(cpp_type='T', expr_type=ir.TypeType(), is_variadic=False)),),
                                                                 body=(ir.Typedef(name='type',
                                                                                  expr=ir.AtomicTypeLiteral.for_local('T', ir.TypeType(), is_variadic=False)),),
                                                                 is_metafunction=True),)),

    # This must be here because it's used in ir0_to_cpp so we can't remove this even if there are no remaining
    # references in ir.
    # template <bool>
    # struct AlwaysTrueFromBool {
    #   static constexpr bool value = true;
    # };
    ir.TemplateDefn(name='AlwaysTrueFromBool',
                    description='',
                    main_definition=ir.TemplateSpecialization(args=(ir.TemplateArgDecl(name='b', expr_type=ir.BoolType(), is_variadic=False),),
                                                              patterns=None,
                                                              body=(ir.ConstantDef(name='value',
                                                                                   expr=ir.Literal(True)),),
                                                              is_metafunction=True),
                    result_element_names=frozenset(('value',)),
                    specializations=()),

    # This must be here because it's used in ir0_to_cpp so we can't remove this even if there are no remaining
    # references in ir.
    # template <int64_t>
    # struct AlwaysTrueFromInt64 {
    #   static constexpr bool value = true;
    # };
    ir.TemplateDefn(name='AlwaysTrueFromInt64',
                    description='',
                    main_definition=ir.TemplateSpecialization(args=(ir.TemplateArgDecl(name='n', expr_type=ir.Int64Type(), is_variadic=False),),
                                                              patterns=None,
                                                              body=(ir.ConstantDef(name='value',
                                                                                   expr=ir.Literal(True)),),
                                                              is_metafunction=True),
                    result_element_names=frozenset(('value',)),
                    specializations=()),

    # This must be here because it's used in ir0_to_cpp so we can't remove this even if there are no remaining
    # references in ir.
    # template <typename>
    # struct AlwaysTrueFromType {
    #   static constexpr bool value = true;
    # };
    ir.TemplateDefn(name='AlwaysTrueFromType',
                    description='',
                    main_definition=ir.TemplateSpecialization(args=(ir.TemplateArgDecl(name='T', expr_type=ir.TypeType(), is_variadic=False),),
                                                              patterns=None,
                                                              body=(ir.ConstantDef(name='value',
                                                                                   expr=ir.Literal(True)),),
                                                              is_metafunction=True),
                    result_element_names=frozenset(('value',)),
                    specializations=()),
] + [ir.TemplateDefn(name='Select1st%s%s' % (name1, name2),
                     description='',
                     args=(ir.TemplateArgDecl(expr_type=type1, name='X', is_variadic=False),
                           ir.TemplateArgDecl(expr_type=type2, name='Y', is_variadic=False)),
                     specializations=(),
                     result_element_names=frozenset(('value',)),
                     main_definition=ir.TemplateSpecialization(args=(
                          ir.TemplateArgDecl(expr_type=type1, name='X', is_variadic=False),
                          ir.TemplateArgDecl(expr_type=type2, name='Y', is_variadic=False)),
                                                                 patterns=None,
                                                                 is_metafunction=True,
                                                                 body=((ir.Typedef if type1.kind == ir.ExprKind.TYPE else ir.ConstantDef)(name='value',
                                                                                                                                          expr=ir.AtomicTypeLiteral.for_local(cpp_type='X',
                                                                                                                                                                              expr_type=type1,
                                                                                                                                                                              is_variadic=False)),)))
     for type1, name1 in _select1st_type_and_name
     for type2, name2 in _select1st_type_and_name
]

def _with_global_inlineable_templates(context_object_file_content: ObjectFileContent,
                                      local_inlineable_templates: List[ir.TemplateDefn]):
    result = {template_defn.name: template_defn
              for module_info in context_object_file_content.modules_by_name.values()
              for template_defn in module_info.ir0_header.template_defns}
    for template_defn in itertools.chain(local_inlineable_templates, TEMPLATE_DEFNS_DEFINED_AS_IR0):
        result[template_defn.name] = template_defn
    return result

class _TemplateInstantiationInliningTransformation(Transformation):
    def __init__(self,
                 local_inlineable_templates: List[ir.TemplateDefn],
                 context_object_file_content: ObjectFileContent,
                 identifier_generator: Iterator[str]):
        super().__init__(identifier_generator=identifier_generator)
        self.needs_another_loop = False
        self.inlineable_templates_by_name = _with_global_inlineable_templates(context_object_file_content, local_inlineable_templates)
        self.parent_template_specialization_definitions = dict()
        self.root_template_defn_name = None

    def transform_template_defn(self, template_defn: ir.TemplateDefn):
        self.root_template_defn_name = template_defn.name
        return super().transform_template_defn(template_defn)

    def transform_template_specialization(self, specialization: ir.TemplateSpecialization):
        old_parent_template_specialization_definitions = self.parent_template_specialization_definitions
        self.parent_template_specialization_definitions = dict()
        result = super().transform_template_specialization(specialization)
        self.parent_template_specialization_definitions = old_parent_template_specialization_definitions
        return result

    def transform_constant_def(self, constant_def: ir.ConstantDef):
        super().transform_constant_def(constant_def)

        if isinstance(self.writer, ToplevelWriter):
            result = self.writer.toplevel_elems[-1]
        else:
            assert isinstance(self.writer, TemplateBodyWriter)
            result = self.writer.elems[-1]

        assert isinstance(result, ir.ConstantDef)
        self.parent_template_specialization_definitions[result.name] = result.expr

    def transform_typedef(self, typedef: ir.Typedef):
        super().transform_typedef(typedef)

        if isinstance(self.writer, ToplevelWriter):
            result = self.writer.toplevel_elems[-1]
        else:
            assert isinstance(self.writer, TemplateBodyWriter)
            result = self.writer.elems[-1]

        assert isinstance(result, ir.Typedef)
        self.parent_template_specialization_definitions[result.name] = result.expr

    def transform_class_member_access(self, class_member_access: ir.ClassMemberAccess):
        class_member_access = super().transform_class_member_access(class_member_access)
        assert isinstance(class_member_access, ir.ClassMemberAccess)
        if (isinstance(class_member_access.inner_expr, ir.TemplateInstantiation)
                and isinstance(class_member_access.inner_expr.template_expr, ir.AtomicTypeLiteral)
                and class_member_access.inner_expr.template_expr.cpp_type in self.inlineable_templates_by_name):
            template_defn_to_inline = self.inlineable_templates_by_name[class_member_access.inner_expr.template_expr.cpp_type]
        else:
            return class_member_access

        unification = unify_template_instantiation_with_definition(class_member_access.inner_expr,
                                                                   self.parent_template_specialization_definitions,
                                                                   class_member_access.member_name,
                                                                   template_defn_to_inline,
                                                                   self.identifier_generator,
                                                                   verbose=ConfigurationKnobs.verbose)
        if not unification:
            return class_member_access

        if isinstance(unification, ir.Expr):
            self.needs_another_loop = True
            return _ensure_remains_variadic_if_it_was(original_expr=class_member_access, transformed_expr=unification)

        # noinspection PyTupleAssignmentBalance
        specialization, value_by_pattern_variable, value_by_expanded_pattern_variable = unification
        assert len(value_by_pattern_variable) + len(value_by_expanded_pattern_variable) == len(specialization.args)

        new_value_by_pattern_variable: Dict[str, ir.Expr] = dict()
        for var, exprs in value_by_pattern_variable:
            assert isinstance(var, ir.AtomicTypeLiteral)
            if isinstance(exprs, tuple):
                [exprs] = exprs
            assert not isinstance(exprs, tuple)
            assert not isinstance(exprs, ir.VariadicTypeExpansion)
            new_value_by_pattern_variable[var.cpp_type] = exprs
        value_by_pattern_variable = new_value_by_pattern_variable

        new_value_by_expanded_pattern_variable: Dict[str, Tuple[ir.Expr, ...]] = dict()
        for var, exprs in value_by_expanded_pattern_variable:
            if isinstance(var, ir.AtomicTypeLiteral):
                if not isinstance(exprs, tuple):
                    exprs = (exprs,)
                for expr in exprs:
                    assert not isinstance(expr, tuple)
                new_value_by_expanded_pattern_variable[var.cpp_type] = exprs
            else:
                assert isinstance(var, ir.VariadicTypeExpansion) and isinstance(var.inner_expr, ir.AtomicTypeLiteral)
                assert isinstance(exprs, tuple)

                new_value_by_expanded_pattern_variable[var.inner_expr.cpp_type] = exprs
        value_by_expanded_pattern_variable = new_value_by_expanded_pattern_variable

        body = []
        result_expr = None
        for elem in specialization.body:
            if isinstance(elem, (ir.ConstantDef, ir.Typedef)) and elem.name == class_member_access.member_name:
                assert not result_expr
                result_expr = elem.expr
            else:
                body.append(elem)

        assert result_expr

        new_var_name_by_old_var_name = dict()
        for elem in body:
            if isinstance(elem, ir.TemplateDefn):
                new_var_name_by_old_var_name[elem.name] = next(self.identifier_generator)
            elif isinstance(elem, ir.ConstantDef):
                new_var_name_by_old_var_name[elem.name] = next(self.identifier_generator)
            elif isinstance(elem, ir.Typedef):
                new_var_name_by_old_var_name[elem.name] = next(self.identifier_generator)
            elif isinstance(elem, ir.StaticAssert):
                pass
            elif isinstance(elem, ir.NoOpStmt):
                pass
            else:
                raise NotImplementedError('Unexpected elem: ' + elem.__class__.__name__)

        transformation = NameReplacementTransformation(new_var_name_by_old_var_name)
        body = transformation.transform_template_body_elems(tuple(body))
        result_expr = transformation.transform_expr(result_expr)

        try:
            body = replace_var_with_expr_in_template_body_elements(body, value_by_pattern_variable, value_by_expanded_pattern_variable)
            for elem in body:
                if isinstance(elem, (ir.ConstantDef, ir.Typedef)) and compute_non_expanded_variadic_vars(elem.expr):
                    raise VariadicVarReplacementNotPossibleException('Needed to replace a non-variadic var with an expr with non-expanded variadic vars in a non-result ConstantDef/Typedef')
            result_expr = replace_var_with_expr_in_expr(result_expr, value_by_pattern_variable, value_by_expanded_pattern_variable)
        except VariadicVarReplacementNotPossibleException as e:
            [message] = e.args
            # We thought we could perform the inlining but we actually can't.
            if ConfigurationKnobs.verbose:
                print('VariadicVarReplacementNotPossibleException raised for template %s (reason: %s), we can\'t inline that.' % (class_member_access.inner_expr.template_expr.cpp_type, message))
            return class_member_access

        result_expr = _ensure_remains_variadic_if_it_was(original_expr=class_member_access,
                                                         transformed_expr=result_expr)
        if (isinstance(result_expr, ir.ClassMemberAccess)
                and isinstance(result_expr.inner_expr, ir.TemplateInstantiation)
                and isinstance(result_expr.inner_expr.template_expr, ir.AtomicTypeLiteral)
                and result_expr.inner_expr.template_expr.cpp_type.startswith('Select1st')
                and isinstance(class_member_access.inner_expr, ir.TemplateInstantiation)
                and isinstance(class_member_access.inner_expr.template_expr, ir.AtomicTypeLiteral)
                and (class_member_access.inner_expr.template_expr.cpp_type.startswith('Select1st')
                     # TODO: make this more precise. This is meant to match the Always*From* templates.
                     or class_member_access.inner_expr.template_expr.cpp_type.startswith('Always'))):
            return class_member_access

        self.needs_another_loop = True
        if ConfigurationKnobs.verbose:
            print('Inlining template defn: %s into %s' % (template_defn_to_inline.name, self.root_template_defn_name or expr_to_cpp_simple(class_member_access)))

        for elem in body:
            with transformation.set_writer(self.writer):
                transformation.transform_template_body_elem(elem)

        return result_expr

def _ensure_remains_variadic_if_it_was(original_expr: ir.Expr, transformed_expr: ir.Expr):
    non_expanded_vars_in_original = compute_non_expanded_variadic_vars(original_expr)
    if not non_expanded_vars_in_original:
        # No non-expanded variadic vars in the original expr, nothing to do.
        return transformed_expr

    if compute_non_expanded_variadic_vars(transformed_expr):
        # The transformed expr already contains non-expanded variadic vars, nothing to do.
        return transformed_expr

    variadic_var = next(iter(non_expanded_vars_in_original.values()))

    return ir.ClassMemberAccess(inner_expr=ir.TemplateInstantiation(template_expr=select1st_literal(transformed_expr.expr_type, variadic_var.expr_type),
                                                                    args=(transformed_expr, variadic_var),
                                                                    instantiation_might_trigger_static_asserts=False),
                                expr_type=transformed_expr.expr_type,
                                member_name='value')

def perform_template_inlining(template_defn: ir.TemplateDefn,
                              inlineable_refs: Set[str],
                              template_defn_by_name: Dict[str, ir.TemplateDefn],
                              identifier_generator: Iterator[str],
                              context_object_file_content: ObjectFileContent):
    template_defn, needs_another_loop1 = perform_local_optimizations_on_template_defn(template_defn,
                                                                                      identifier_generator,
                                                                                      inline_template_instantiations_with_multiple_references=True)

    def perform_optimization() -> Tuple[Tuple[ir.TemplateDefn, ...], bool]:
        if ConfigurationKnobs.verbose:
            print('Considering inlining templates: %s in template: %s' % (inlineable_refs, template_defn.name))
        transformation = _TemplateInstantiationInliningTransformation([template_defn_by_name[template_name]
                                                                       for template_name in inlineable_refs],
                                                                      context_object_file_content,
                                                                      identifier_generator)
        writer = ToplevelWriter(allow_toplevel_elems=False)
        with transformation.set_writer(writer):
            transformation.transform_template_defn(template_defn)
        return tuple(writer.template_defns), transformation.needs_another_loop

    [template_defn], needs_another_loop2 = apply_elem_optimization((template_defn,),
                                                                   perform_optimization,
                                                                   lambda template_defns: describe_template_defns(template_defns, identifier_generator),
                                                                   optimization_name='TemplateInstantiationInliningTransformation',
                                                                   other_context=lambda: 'Potentially inlineable template(s):\n' + ''.join(template_defn_to_cpp_simple(template_defn_by_name[template_name], identifier_generator)
                                                                                                                                           for template_name in inlineable_refs) + '\n')

    return template_defn, needs_another_loop1 or needs_another_loop2

def perform_template_inlining_on_toplevel_elems(toplevel_elems: List[Union[ir.StaticAssert, ir.ConstantDef, ir.Typedef]],
                                                inlineable_refs: AbstractSet[str],
                                                template_defn_by_name: Dict[str, ir.TemplateDefn],
                                                identifier_generator: Iterator[str],
                                                context_object_file_content: ObjectFileContent):
    toplevel_elems, needs_another_loop1 = perform_local_optimizations_on_toplevel_elems(toplevel_elems,
                                                                                        identifier_generator,
                                                                                        inline_template_instantiations_with_multiple_references=True)

    def perform_optimization() -> Tuple[Tuple[ir.TemplateBodyElement, ...], bool]:
        if ConfigurationKnobs.verbose:
            print('Considering inlining templates: %s in toplevel elems' % inlineable_refs)
        transformation = _TemplateInstantiationInliningTransformation([template_defn_by_name[template_name]
                                                                       for template_name in inlineable_refs],
                                                                      context_object_file_content,
                                                                      identifier_generator)

        elems = transformation.transform_template_body_elems(toplevel_elems)
        return elems, transformation.needs_another_loop

    toplevel_elems, needs_another_loop2 = apply_elem_optimization(toplevel_elems,
                                                                  perform_optimization,
                                                                  lambda toplevel_elems: describe_toplevel_elems(toplevel_elems, identifier_generator),
                                                                  optimization_name='TemplateInstantiationInliningTransformation',
                                                                  other_context=lambda: 'Potentially inlineable template(s):\n' + ''.join(
                                                                      template_defn_to_cpp_simple(template_defn_by_name[template_name],
                                                                                                  identifier_generator)
                                                                      for template_name in inlineable_refs) + '\n')
    return toplevel_elems, needs_another_loop1 or needs_another_loop2
