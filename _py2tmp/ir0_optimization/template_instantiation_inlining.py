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
from functools import lru_cache
from typing import Dict, Iterator, Set, List, Union
from _py2tmp import ir0, transform_ir0, ir0_builtins, ir0_to_cpp
from _py2tmp.ir0_optimization import unify_ir0
from _py2tmp.ir0_optimization.compute_non_expanded_variadic_vars import compute_non_expanded_variadic_vars
from _py2tmp.ir0_optimization.configuration_knobs import ConfigurationKnobs
from _py2tmp.ir0_optimization.local_optimizations import perform_local_optimizations_on_toplevel_elems, perform_local_optimizations_on_template_defn
from _py2tmp.ir0_optimization.optimization_execution import apply_optimization, apply_toplevel_elems_optimization,  template_defn_to_cpp
from _py2tmp.ir0_optimization.replace_var_with_expr import replace_var_with_expr_in_template_body_elements, VariadicVarReplacementNotPossibleException, replace_var_with_expr_in_expr

_select1st_type_and_name = [
    (ir0.BoolType(), 'Bool'),
    (ir0.Int64Type(), 'Int64'),
    (ir0.TypeType(), 'Type'),
]

TEMPLATE_DEFNS_DEFINED_AS_IR0 = [
    ir0.TemplateDefn(name='std::is_same',
                     description='',
                     result_element_names=['value'],
                     args=[ir0.TemplateArgDecl(name='T', expr_type=ir0.TypeType(), is_variadic=False),
                           ir0.TemplateArgDecl(name='U', expr_type=ir0.TypeType(), is_variadic=False)],
                     main_definition=ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(name='T', expr_type=ir0.TypeType(), is_variadic=False),
                                                                      ir0.TemplateArgDecl(name='U', expr_type=ir0.TypeType(), is_variadic=False)],
                                                                patterns=None,
                                                                body=[ir0.ConstantDef(name='value',
                                                                                      expr=ir0.Literal(False))],
                                                                is_metafunction=True),
                     specializations=[ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(name='T', expr_type=ir0.TypeType(), is_variadic=False)],
                                                                 patterns=[ir0.AtomicTypeLiteral.for_local(cpp_type='T', expr_type=ir0.TypeType(), is_variadic=False),
                                                                           ir0.AtomicTypeLiteral.for_local(cpp_type='T', expr_type=ir0.TypeType(), is_variadic=False)],
                                                                 body=[ir0.ConstantDef(name='value',
                                                                                       expr=ir0.Literal(True))],
                                                                 is_metafunction=True)]),
    ir0.TemplateDefn(name='std::add_pointer',
                     description='',
                     result_element_names=['type'],
                     main_definition=ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(name='T', expr_type=ir0.TypeType(), is_variadic=False)],
                                                                patterns=None,
                                                                body=[ir0.Typedef(name='type',
                                                                                  expr=ir0.PointerTypeExpr(ir0.AtomicTypeLiteral.for_local('T', ir0.TypeType(), is_variadic=False)))],
                                                                is_metafunction=True),
                     specializations=[]),

    ir0.TemplateDefn(name='std::remove_pointer',
                     description='',
                     result_element_names=['type'],
                     args=[ir0.TemplateArgDecl(name='T', expr_type=ir0.TypeType(), is_variadic=False)],
                     main_definition=ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(name='T', expr_type=ir0.TypeType(), is_variadic=False)],
                                                                patterns=None,
                                                                body=[ir0.Typedef(name='type',
                                                                                  expr=ir0.AtomicTypeLiteral.for_local('T', ir0.TypeType(), is_variadic=False))],
                                                                is_metafunction=True),
                     specializations=[ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(name='T', expr_type=ir0.TypeType(), is_variadic=False)],
                                                                 patterns=[ir0.PointerTypeExpr(ir0.AtomicTypeLiteral.for_local(cpp_type='T', expr_type=ir0.TypeType(), is_variadic=False))],
                                                                 body=[ir0.Typedef(name='type',
                                                                                   expr=ir0.AtomicTypeLiteral.for_local('T', ir0.TypeType(), is_variadic=False))],
                                                                 is_metafunction=True)]),

    # This must be here because it's used in ir0_to_cpp so we can't remove this even if there are no remaining
    # references in IR0.
    # template <bool>
    # struct AlwaysTrueFromBool {
    #   static constexpr bool value = true;
    # };
    ir0.TemplateDefn(name='AlwaysTrueFromBool',
                     description='',
                     main_definition=ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(name='b', expr_type=ir0.BoolType(), is_variadic=False)],
                                                                patterns=None,
                                                                body=[ir0.ConstantDef(name='value',
                                                                                      expr=ir0.Literal(True))],
                                                                is_metafunction=True),
                     result_element_names=['value'],
                     specializations=[]),

    # This must be here because it's used in ir0_to_cpp so we can't remove this even if there are no remaining
    # references in IR0.
    # template <int64_t>
    # struct AlwaysTrueFromInt64 {
    #   static constexpr bool value = true;
    # };
    ir0.TemplateDefn(name='AlwaysTrueFromInt64',
                     description='',
                     main_definition=ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(name='n', expr_type=ir0.Int64Type(), is_variadic=False)],
                                                                patterns=None,
                                                                body=[ir0.ConstantDef(name='value',
                                                                                      expr=ir0.Literal(True))],
                                                                is_metafunction=True),
                     result_element_names=['value'],
                     specializations=[]),

    # This must be here because it's used in ir0_to_cpp so we can't remove this even if there are no remaining
    # references in IR0.
    # template <typename>
    # struct AlwaysTrueFromType {
    #   static constexpr bool value = true;
    # };
    ir0.TemplateDefn(name='AlwaysTrueFromType',
                     description='',
                     main_definition=ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(name='T', expr_type=ir0.TypeType(), is_variadic=False)],
                                                                patterns=None,
                                                                body=[ir0.ConstantDef(name='value',
                                                                                      expr=ir0.Literal(True))],
                                                                is_metafunction=True),
                     result_element_names=['value'],
                     specializations=[]),
] + [ir0.TemplateDefn(name='Select1st%s%s' % (name1, name2),
                      description='',
                      args=[ir0.TemplateArgDecl(expr_type=type1, name='X', is_variadic=False),
                            ir0.TemplateArgDecl(expr_type=type2, name='Y', is_variadic=False)],
                      specializations=[],
                      result_element_names=['value'],
                      main_definition=ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(expr_type=type1, name='X', is_variadic=False),
                                                                       ir0.TemplateArgDecl(expr_type=type2, name='Y', is_variadic=False)],
                                                                 patterns=None,
                                                                 is_metafunction=True,
                                                                 body=[(ir0.Typedef if type1.kind == ir0.ExprKind.TYPE else ir0.ConstantDef)(name='value',
                                                                                                                                             expr=ir0.AtomicTypeLiteral.for_local(cpp_type='X', expr_type=type1, is_variadic=False))]))
     for type1, name1 in _select1st_type_and_name
     for type2, name2 in _select1st_type_and_name
]

def _getGloballyInlineableTemplatesByName():
    template_defns = TEMPLATE_DEFNS_DEFINED_AS_IR0 + ir0_builtins.get_builtin_templates()
    return {template_defn.name: template_defn
            for template_defn in template_defns}

class _TemplateInstantiationInliningTransformation(transform_ir0.Transformation):
    def __init__(self, inlineable_templates_by_name: Dict[str, ir0.TemplateDefn]):
        super().__init__()
        self.needs_another_loop = False
        self.inlineable_templates_by_name = inlineable_templates_by_name.copy()
        self.parent_template_specialization_definitions = dict()

    def transform_template_specialization(self, specialization: ir0.TemplateSpecialization, writer: transform_ir0.Writer):
        old_parent_template_specialization_definitions = self.parent_template_specialization_definitions
        self.parent_template_specialization_definitions = dict()
        result = super().transform_template_specialization(specialization, writer)
        self.parent_template_specialization_definitions = old_parent_template_specialization_definitions
        return result

    def transform_constant_def(self, constant_def: ir0.ConstantDef, writer: transform_ir0.Writer):
        super().transform_constant_def(constant_def, writer)

        if isinstance(writer, transform_ir0.ToplevelWriter):
            result = writer.toplevel_elems[-1]
        else:
            assert isinstance(writer, transform_ir0.TemplateBodyWriter)
            result = writer.elems[-1]

        assert isinstance(result, ir0.ConstantDef)
        self.parent_template_specialization_definitions[result.name] = result.expr

    def transform_typedef(self, typedef: ir0.Typedef, writer: transform_ir0.Writer):
        super().transform_typedef(typedef, writer)

        if isinstance(writer, transform_ir0.ToplevelWriter):
            result = writer.toplevel_elems[-1]
        else:
            assert isinstance(writer, transform_ir0.TemplateBodyWriter)
            result = writer.elems[-1]

        assert isinstance(result, ir0.Typedef)
        self.parent_template_specialization_definitions[result.name] = result.expr

    def transform_class_member_access(self, class_member_access: ir0.ClassMemberAccess, writer: transform_ir0.Writer):
        assert isinstance(writer, transform_ir0.TemplateBodyWriter)
        class_member_access = super().transform_class_member_access(class_member_access, writer)
        assert isinstance(class_member_access, ir0.ClassMemberAccess)
        if (isinstance(class_member_access.expr, ir0.TemplateInstantiation)
                and isinstance(class_member_access.expr.template_expr, ir0.AtomicTypeLiteral)
                and class_member_access.expr.template_expr.cpp_type in self.inlineable_templates_by_name):
            template_instantiation = class_member_access.expr
            template_defn_to_inline = self.inlineable_templates_by_name[template_instantiation.template_expr.cpp_type]
        elif (isinstance(class_member_access.expr, ir0.TemplateInstantiation)
              and isinstance(class_member_access.expr.template_expr, ir0.AtomicTypeLiteral)
              and class_member_access.expr.template_expr.cpp_type in _getGloballyInlineableTemplatesByName()):
            template_instantiation = class_member_access.expr
            template_defn_to_inline = _getGloballyInlineableTemplatesByName()[template_instantiation.template_expr.cpp_type]
        else:
            return class_member_access

        toplevel_writer = writer.get_toplevel_writer()
        unification = unify_ir0.unify_template_instantiation_with_definition(template_instantiation,
                                                                             self.parent_template_specialization_definitions,
                                                                             class_member_access.member_name,
                                                                             template_defn_to_inline,
                                                                             toplevel_writer.identifier_generator,
                                                                             verbose=ConfigurationKnobs.verbose)
        if not unification:
            return class_member_access

        if isinstance(unification, ir0.Expr):
            self.needs_another_loop = True
            return _ensure_remains_variadic_if_it_was(original_expr=class_member_access, transformed_expr=unification)

        specialization, value_by_pattern_variable, value_by_expanded_pattern_variable = unification
        assert len(value_by_pattern_variable) + len(value_by_expanded_pattern_variable) == len(specialization.args)

        new_value_by_pattern_variable: Dict[str, ir0.Expr] = dict()
        for var, exprs in value_by_pattern_variable:
            assert isinstance(var, ir0.AtomicTypeLiteral)
            if isinstance(exprs, list):
                [exprs] = exprs
            assert not isinstance(exprs, list)
            assert not isinstance(exprs, ir0.VariadicTypeExpansion)
            new_value_by_pattern_variable[var.cpp_type] = exprs
        value_by_pattern_variable = new_value_by_pattern_variable

        new_value_by_expanded_pattern_variable: Dict[str, List[ir0.Expr]] = dict()
        for var, exprs in value_by_expanded_pattern_variable:
            if isinstance(var, ir0.AtomicTypeLiteral):
                if not isinstance(exprs, list):
                    exprs = [exprs]
                for expr in exprs:
                    assert not isinstance(expr, list)
                new_value_by_expanded_pattern_variable[var.cpp_type] = exprs
            else:
                assert isinstance(var, ir0.VariadicTypeExpansion) and isinstance(var.expr, ir0.AtomicTypeLiteral)
                assert isinstance(exprs, list)

                new_value_by_expanded_pattern_variable[var.expr.cpp_type] = exprs
        value_by_expanded_pattern_variable = new_value_by_expanded_pattern_variable

        tmp_writer = transform_ir0.ToplevelWriter(toplevel_writer.identifier_generator,
                                                  allow_toplevel_elems=False,
                                                  allow_template_defns=toplevel_writer.allow_template_defns)
        body = []
        result_expr = None
        for elem in specialization.body:
            if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)) and elem.name == class_member_access.member_name:
                assert not result_expr
                result_expr = elem.expr
            else:
                body.append(elem)

        assert result_expr

        new_var_name_by_old_var_name = dict()
        for elem in body:
            if isinstance(elem, ir0.TemplateDefn):
                new_var_name_by_old_var_name[elem.name] = writer.new_id()
            elif isinstance(elem, ir0.ConstantDef):
                new_var_name_by_old_var_name[elem.name] = writer.new_id()
            elif isinstance(elem, ir0.Typedef):
                new_var_name_by_old_var_name[elem.name] = writer.new_id()
            elif isinstance(elem, ir0.StaticAssert):
                pass
            else:
                raise NotImplementedError('Unexpected elem: ' + elem.__class__.__name__)

        transformation = transform_ir0.NameReplacementTransformation(new_var_name_by_old_var_name)
        body = transformation.transform_template_body_elems(body, tmp_writer)
        result_expr = transformation.transform_expr(result_expr, tmp_writer)

        try:
            body = replace_var_with_expr_in_template_body_elements(body, value_by_pattern_variable, value_by_expanded_pattern_variable)
            for elem in body:
                if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)) and compute_non_expanded_variadic_vars(elem.expr):
                    raise VariadicVarReplacementNotPossibleException('Needed to replace a non-variadic var with an expr with non-expanded variadic vars in a non-result ConstantDef/Typedef')
            result_expr = replace_var_with_expr_in_expr(result_expr, value_by_pattern_variable, value_by_expanded_pattern_variable)
        except VariadicVarReplacementNotPossibleException as e:
            [message] = e.args
            # We thought we could perform the inlining but we actually can't.
            if ConfigurationKnobs.verbose:
                print('VariadicVarReplacementNotPossibleException raised for template %s (reason: %s), we can\'t inline that.' % (template_instantiation.template_expr.cpp_type, message))
            return class_member_access

        result_expr = _ensure_remains_variadic_if_it_was(original_expr=class_member_access,
                                                         transformed_expr=result_expr)
        if (isinstance(result_expr, ir0.ClassMemberAccess)
                and isinstance(result_expr.expr, ir0.TemplateInstantiation)
                and isinstance(result_expr.expr.template_expr, ir0.AtomicTypeLiteral)
                and result_expr.expr.template_expr.cpp_type.startswith('Select1st')
                and isinstance(class_member_access.expr, ir0.TemplateInstantiation)
                and isinstance(class_member_access.expr.template_expr, ir0.AtomicTypeLiteral)
                and (class_member_access.expr.template_expr.cpp_type.startswith('Select1st')
                     # TODO: make this more precise. This is meant to match the Always*From* templates.
                     or class_member_access.expr.template_expr.cpp_type.startswith('Always'))):
            return class_member_access

        self.needs_another_loop = True
        if ConfigurationKnobs.verbose:
            print('Inlining template defn: %s' % template_defn_to_inline.name)

        for elem in body:
            transformation.transform_template_body_elem(elem, writer)

        return result_expr

def _ensure_remains_variadic_if_it_was(original_expr: ir0.Expr, transformed_expr: ir0.Expr):
    non_expanded_vars_in_original = compute_non_expanded_variadic_vars(original_expr)
    if not non_expanded_vars_in_original:
        # No non-expanded variadic vars in the original expr, nothing to do.
        return transformed_expr

    if compute_non_expanded_variadic_vars(transformed_expr):
        # The transformed expr already contains non-expanded variadic vars, nothing to do.
        return transformed_expr

    variadic_var = next(iter(non_expanded_vars_in_original.values()))

    kind_to_string = {
        ir0.ExprKind.BOOL: 'Bool',
        ir0.ExprKind.INT64: 'Int64',
        ir0.ExprKind.TYPE: 'Type',
    }
    select1st_literal = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='Select1st%s%s' % (kind_to_string[transformed_expr.expr_type.kind], kind_to_string[variadic_var.expr_type.kind]),
                                                                    args=[ir0.TemplateArgType(expr_type=transformed_expr.expr_type, is_variadic=False),
                                                                          ir0.TemplateArgType(expr_type=variadic_var.expr_type, is_variadic=False)],
                                                                    is_metafunction_that_may_return_error=False,
                                                                    may_be_alias=False)
    return ir0.ClassMemberAccess(class_type_expr=ir0.TemplateInstantiation(template_expr=select1st_literal,
                                                                           args=[transformed_expr, variadic_var],
                                                                           instantiation_might_trigger_static_asserts=False),
                                 member_type=transformed_expr.expr_type,
                                 member_name='value')

def perform_template_inlining(template_defn: ir0.TemplateDefn,
                              inlineable_refs: Set[str],
                              template_defn_by_name: Dict[str, ir0.TemplateDefn],
                              identifier_generator: Iterator[str]):
    template_defn, needs_another_loop1 = perform_local_optimizations_on_template_defn(template_defn,
                                                                                      identifier_generator,
                                                                                      inline_template_instantiations_with_multiple_references=True)

    def perform_optimization():
        if ConfigurationKnobs.verbose:
            print('Considering inlining templates: %s in template: %s' % (inlineable_refs, template_defn.name))
        transformation = _TemplateInstantiationInliningTransformation({template_name: template_defn_by_name[template_name]
                                                                       for template_name in inlineable_refs})

        writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False)
        transformation.transform_template_defn(template_defn, writer)
        return writer.template_defns, transformation.needs_another_loop

    [template_defn], needs_another_loop2 = apply_optimization(template_defn,
                                                              identifier_generator,
                                                              optimization=perform_optimization,
                                                              optimization_name='TemplateInstantiationInliningTransformation',
                                                              other_context=lambda: 'Potentially inlineable template(s):\n' + ''.join(template_defn_to_cpp(template_defn_by_name[template_name], identifier_generator)
                                                                                                                                      for template_name in inlineable_refs) + '\n')

    return template_defn, needs_another_loop1 or needs_another_loop2

def perform_template_inlining_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                                inlineable_refs: Set[str],
                                                template_defn_by_name: Dict[str, ir0.TemplateDefn],
                                                identifier_generator: Iterator[str]):
    toplevel_elems, needs_another_loop1 = perform_local_optimizations_on_toplevel_elems(toplevel_elems,
                                                                                        identifier_generator,
                                                                                        inline_template_instantiations_with_multiple_references=True)

    def perform_optimization():
        if ConfigurationKnobs.verbose:
            print('Considering inlining templates: %s in toplevel elems' % inlineable_refs)
        transformation = _TemplateInstantiationInliningTransformation({template_name: template_defn_by_name[template_name]
                                                                       for template_name in inlineable_refs})

        writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False, allow_template_defns=False)
        elems = transformation.transform_template_body_elems(toplevel_elems, writer)

        return elems, transformation.needs_another_loop

    toplevel_elems, needs_another_loop2 = apply_toplevel_elems_optimization(toplevel_elems,
                                                                            identifier_generator,
                                                                            optimization=perform_optimization,
                                                                            optimization_name='TemplateInstantiationInliningTransformation',
                                                                            other_context=lambda: 'Potentially inlineable template(s):\n' + ''.join(
                                                                                template_defn_to_cpp(template_defn_by_name[template_name],
                                                                                                     identifier_generator)
                                                                                for template_name in inlineable_refs) + '\n')
    return toplevel_elems, needs_another_loop1 or needs_another_loop2
