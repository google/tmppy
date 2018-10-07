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
from typing import List, Tuple, Iterator, MutableMapping, Dict
from _py2tmp import ir0, transform_ir0

# Splits template instantiations with multiple outputs so that there's only 1 result elem.
# This allows the following inlining passes to inline in more cases.
def split_template_defn_with_multiple_outputs(template_defn: ir0.TemplateDefn,
                                              split_template_name_by_old_name_and_result_element_name: MutableMapping[Tuple[str, str], str],
                                              identifier_generator: Iterator[str]) -> Tuple[List[ir0.TemplateDefn], bool]:
    type_by_result_elem_name = {elem.name: elem.expr.expr_type
                                for specialization in template_defn.get_all_definitions()
                                for elem in specialization.body
                                if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)) and elem.name in template_defn.result_element_names}
    actual_result_elem_names = list(sorted(type_by_result_elem_name.keys()))
    if len(type_by_result_elem_name) <= 1 or any(not specialization.is_metafunction
                                                 for specialization in template_defn.get_all_definitions()):
        return [template_defn], False

    new_template_defns = []
    if template_defn.main_definition:
        args = template_defn.main_definition.args
    else:
        args = template_defn.args
    template_defn_by_result_elem_name = {result_elem: ir0.TemplateDefn(main_definition=template_defn.main_definition,
                                                                       specializations=template_defn.specializations,
                                                                       name=split_template_name_by_old_name_and_result_element_name.setdefault((template_defn.name, result_elem),
                                                                                                                                               next(identifier_generator)),
                                                                           description='Split that generates %s of: %s' % (result_elem, template_defn.description or template_defn.name),
                                                                       result_element_names=[result_elem],
                                                                       args=args)
                                         for result_elem in actual_result_elem_names}
    for new_template_defn in template_defn_by_result_elem_name.values():
        new_template_defns.append(new_template_defn)

    dispatcher_body = []
    for result_elem_name in actual_result_elem_names:
        expr_type = type_by_result_elem_name[result_elem_name]

        if expr_type.kind in (ir0.ExprKind.TYPE, ir0.ExprKind.TEMPLATE):
            stmt_type = ir0.Typedef
        else:
            stmt_type = ir0.ConstantDef

        split_template_literal = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=template_defn_by_result_elem_name[result_elem_name].name,
                                                                             args=args,
                                                                             is_metafunction_that_may_return_error=False,
                                                                             may_be_alias=False)
        dispatcher_body.append(stmt_type(name=result_elem_name,
                                         expr=ir0.ClassMemberAccess(class_type_expr=ir0.TemplateInstantiation(template_expr=split_template_literal,
                                                                                                              args=[ir0.AtomicTypeLiteral.for_local(cpp_type=arg.name,
                                                                                                                                                    expr_type=arg.expr_type,
                                                                                                                                                    is_variadic=arg.is_variadic)
                                                                                                                    for arg in
                                                                                                                    args],
                                                                                                              instantiation_might_trigger_static_asserts=True),
                                                                    member_name=result_elem_name,
                                                                    member_type=expr_type)))

    new_template_defns.append(ir0.TemplateDefn(main_definition=ir0.TemplateSpecialization(args=args,
                                                                                          patterns=None,
                                                                                          body=dispatcher_body,
                                                                                          is_metafunction=True),
                                               specializations=[],
                                               name=template_defn.name,
                                               description=template_defn.description,
                                               result_element_names=actual_result_elem_names,
                                               args=args))
    return new_template_defns, False

class ReplaceMetafunctionCallWithSplitTemplateCallTransformation(transform_ir0.Transformation):
    def __init__(self, split_template_name_by_old_name_and_result_element_name: Dict[Tuple[str, str], str]):
        super().__init__()
        self.split_template_name_by_old_name_and_result_element_name = split_template_name_by_old_name_and_result_element_name

    def transform_class_member_access(self, class_member_access: ir0.ClassMemberAccess, writer: transform_ir0.Writer):
        if (isinstance(class_member_access.expr, ir0.TemplateInstantiation)
                and isinstance(class_member_access.expr.template_expr, ir0.AtomicTypeLiteral)
                and (class_member_access.expr.template_expr.cpp_type, class_member_access.member_name) in self.split_template_name_by_old_name_and_result_element_name):
            split_template_name = self.split_template_name_by_old_name_and_result_element_name[(class_member_access.expr.template_expr.cpp_type, class_member_access.member_name)]
            class_member_access = ir0.ClassMemberAccess(class_type_expr=ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=split_template_name,
                                                                                                                                                            args=class_member_access.expr.template_expr.expr_type.args,
                                                                                                                                                            is_metafunction_that_may_return_error=class_member_access.expr.template_expr.is_metafunction_that_may_return_error,
                                                                                                                                                            may_be_alias=False),
                                                                                                  args=class_member_access.expr.args,
                                                                                                  instantiation_might_trigger_static_asserts=class_member_access.expr.instantiation_might_trigger_static_asserts),
                                                        member_name=class_member_access.member_name,
                                                        member_type=class_member_access.expr_type)
        return super().transform_class_member_access(class_member_access, writer)

def replace_metafunction_calls_with_split_template_calls(header, identifier_generator, new_template_defns,
                                                         split_template_name_by_old_name_and_result_element_name):
    transformation = ReplaceMetafunctionCallWithSplitTemplateCallTransformation(
        split_template_name_by_old_name_and_result_element_name)
    return transformation.transform_header(
        ir0.Header(template_defns=new_template_defns,
                   toplevel_content=header.toplevel_content,
                   public_names=header.public_names,
                   split_template_name_by_old_name_and_result_element_name=split_template_name_by_old_name_and_result_element_name,
                   check_if_error_specializations=header.check_if_error_specializations),
        identifier_generator)
