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

from typing import List, Union, Dict, Iterator, Sequence
from _py2tmp import ir0, utils, transform_ir0

def _create_var_to_var_assignment(lhs: str, rhs: str, expr_type: ir0.ExprType):
    if expr_type.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
        return ir0.ConstantDef(name=lhs,
                               expr=ir0.AtomicTypeLiteral.for_local(cpp_type=rhs,
                                                                    expr_type=expr_type,
                                                                    is_variadic=False))
    elif expr_type.kind in (ir0.ExprKind.TYPE, ir0.ExprKind.TEMPLATE):
        return ir0.Typedef(name=lhs,
                           expr=ir0.AtomicTypeLiteral.for_local(cpp_type=rhs,
                                                                expr_type=expr_type,
                                                                is_variadic=False))
    else:
        raise NotImplementedError('Unexpected kind: %s' % str(expr_type.kind))

class _CommonSubexpressionEliminationTransformation(transform_ir0.Transformation):
    def __init__(self):
        super().__init__()

    def transform_template_defn(self, template_defn: ir0.TemplateDefn, writer: transform_ir0.Writer):
        writer.write(ir0.TemplateDefn(args=template_defn.args,
                                      main_definition=self._transform_template_specialization(template_defn.main_definition, template_defn.result_element_names, writer) if template_defn.main_definition is not None else None,
                                      specializations=[self._transform_template_specialization(specialization, template_defn.result_element_names, writer) for specialization in template_defn.specializations],
                                      name=template_defn.name,
                                      description=template_defn.description,
                                      result_element_names=template_defn.result_element_names))

    def _transform_template_specialization(self,
                                           specialization: ir0.TemplateSpecialization,
                                           result_element_names: Sequence[str],
                                           writer: transform_ir0.Writer) -> ir0.TemplateSpecialization:
        toplevel_writer = writer.get_toplevel_writer()

        return ir0.TemplateSpecialization(args=specialization.args,
                                          patterns=specialization.patterns,
                                          body=self._transform_template_body_elems(specialization.body,
                                                                                   result_element_names,
                                                                                   specialization.args,
                                                                                   toplevel_writer,
                                                                                   specialization.is_metafunction),
                                          is_metafunction=specialization.is_metafunction)

    def _transform_template_body_elems(self,
                                       elems: List[ir0.TemplateBodyElement],
                                       result_element_names: Sequence[str],
                                       template_specialization_args: Sequence[ir0.TemplateArgDecl],
                                       toplevel_writer: transform_ir0.ToplevelWriter,
                                       is_metafunction: bool):
        name_by_expr = dict()  # type: Dict[ir0.Expr, str]
        replacements = dict()  # type: Dict[str, str]
        type_by_name = dict()  # type: Dict[str, ir0.ExprType]

        # First we process all args, so that we'll remove assignments of the form:
        # x1 = arg1
        for arg in template_specialization_args:
            name_by_expr[ir0.AtomicTypeLiteral.for_local(cpp_type=arg.name,
                                                         expr_type=arg.expr_type,
                                                         is_variadic=arg.is_variadic)] = arg.name
            type_by_name[arg.name] = arg.expr_type

        result_elems = []
        for elem in elems:
            writer = transform_ir0.TemplateBodyWriter(toplevel_writer)
            transform_ir0.NameReplacementTransformation(replacements).transform_template_body_elem(elem, writer)
            [elem] = writer.elems

            if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)) and elem.expr in name_by_expr:
                replacements[elem.name] = name_by_expr[elem.expr]
                type_by_name[elem.name] = elem.expr.expr_type
            else:
                result_elems.append(elem)
                if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)):
                    name_by_expr[elem.expr] = elem.name

        additional_result_elems = []

        # This second pass will rename "result elements" back to the correct names if they were deduped.
        replacements2 = dict()
        arg_names = {arg.name for arg in template_specialization_args}
        for result_elem_name in result_element_names:
            if result_elem_name in replacements:
                replacement = replacements[result_elem_name]
                if replacement in replacements2:
                    # We've already added a replacement in `replacements2`, so we need to emit an extra "assignment" assigning
                    # a result element to another.
                    additional_result_elems.append(_create_var_to_var_assignment(lhs=result_elem_name,
                                                                                 rhs=replacements2[replacement],
                                                                                 expr_type=type_by_name[replacement]))
                elif replacement in result_element_names:
                    # We've eliminated the assignment to the result var against another result var, so we need to emit an
                    # extra "assignment" assigning a result element to another.

                    if replacement in type_by_name:
                        expr_type = type_by_name[replacement]
                    elif result_elem_name in type_by_name:
                        expr_type = type_by_name[result_elem_name]
                    else:
                        raise NotImplementedError('Unable to determine type. This should never happen.')

                    additional_result_elems.append(_create_var_to_var_assignment(lhs=result_elem_name,
                                                                                 rhs=replacement,
                                                                                 expr_type=expr_type))
                elif replacement in arg_names:
                    # We've eliminated the assignment to the result var against the definition of an argument.
                    # So we need to add it back.
                    additional_result_elems.append(_create_var_to_var_assignment(lhs=result_elem_name,
                                                                                 rhs=replacement,
                                                                                 expr_type=type_by_name[replacement]))
                else:
                    replacements2[replacement] = result_elem_name

        result_elems = transform_ir0.NameReplacementTransformation(replacements2).transform_template_body_elems(result_elems,
                                                                                                                toplevel_writer)

        result_elems = result_elems + additional_result_elems

        if is_metafunction and result_elems:
            assert (any(isinstance(elem, ir0.Typedef) and elem.name in ('type', 'error', 'value')
                        for elem in result_elems)
                    or any(isinstance(elem, ir0.ConstantDef) and elem.name == 'value'
                           for elem in result_elems)), 'type_by_name == %s\nreplacements2 == %s\nbody was:\n%s' % (
                type_by_name,
                replacements2,
                '\n'.join(utils.ir_to_string(elem)
                          for elem in result_elems))
        return result_elems

    def _transform_toplevel_elems(self,
                                  elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                  identifier_generator: Iterator[str]):

        name_by_expr = dict()  # type: Dict[ir0.Expr, str]
        replacements = dict()  # type: Dict[str, str]
        type_by_name = dict()  # type: Dict[str, ir0.ExprType]

        result_elems = []
        for elem in elems:
            writer = transform_ir0.ToplevelWriter(identifier_generator, allow_template_defns=False)
            transform_ir0.NameReplacementTransformation(replacements).transform_toplevel_elem(elem, writer)
            [elem] = writer.toplevel_elems

            if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)) and elem.expr in name_by_expr:
                replacements[elem.name] = name_by_expr[elem.expr]
                type_by_name[elem.name] = elem.expr.expr_type
            else:
                result_elems.append(elem)
                if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)):
                    name_by_expr[elem.expr] = elem.name

        return result_elems

def perform_common_subexpression_normalization(template_defn: ir0.TemplateDefn,
                                               identifier_generator: Iterator[str]):
    writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False)
    transformation = _CommonSubexpressionEliminationTransformation()
    transformation.transform_template_defn(template_defn, writer)
    return writer.template_defns, False

def perform_common_subexpression_normalization_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                                                 identifier_generator: Iterator[str]):
    transformation = _CommonSubexpressionEliminationTransformation()
    return transformation._transform_toplevel_elems(toplevel_elems, identifier_generator), False
