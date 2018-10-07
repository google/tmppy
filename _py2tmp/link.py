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
from typing import Iterator

from _py2tmp import ir0, ir0_optimization, ir0_builtins, ir0_to_cpp
from _py2tmp.tmppy_object_file import ObjectFileContent

def compute_merged_header_for_linking(main_module_name: str,
                                      object_file_content: ObjectFileContent,
                                      identifier_generator: Iterator[str]):
    template_defns = []
    check_if_error_specializations = []
    toplevel_content = []
    split_template_name_by_old_name_and_result_element_name = dict()

    module_infos = itertools.chain(object_file_content.modules_by_name.values(), [ir0_builtins.get_module()])

    for module_info in module_infos:
        template_defns += module_info.ir0_header.template_defns
        check_if_error_specializations += module_info.ir0_header.check_if_error_specializations
        toplevel_content += module_info.ir0_header.toplevel_content
        for key, value in module_info.ir0_header.split_template_name_by_old_name_and_result_element_name.items():
            split_template_name_by_old_name_and_result_element_name[key] = value

    # template <typename>
    # struct CheckIfError {
    #   using type = void;
    # };
    check_if_error_template_main_definition = ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(expr_type=ir0.TypeType(),
                                                                                                   name='T',
                                                                                                   is_variadic=False)],
                                                                         patterns=None,
                                                                         body=[ir0.Typedef(name='type',
                                                                                           expr=ir0.AtomicTypeLiteral.for_nonlocal_type('void', may_be_alias=False))],
                                                                         is_metafunction=True)

    template_defns.append(ir0.TemplateDefn(main_definition=check_if_error_template_main_definition,
                                           specializations=check_if_error_specializations,
                                           name='CheckIfError',
                                           description='',
                                           result_element_names=['type']))

    public_names = object_file_content.modules_by_name[main_module_name].ir0_header.public_names.union(['CheckIfError'])

    merged_header = ir0.Header(template_defns=template_defns,
                               check_if_error_specializations=[],
                               toplevel_content=toplevel_content,
                               split_template_name_by_old_name_and_result_element_name=split_template_name_by_old_name_and_result_element_name,
                               public_names=public_names)

    return ir0_optimization.optimize_header(header=merged_header,
                                            context_object_file_content=ObjectFileContent({}),
                                            identifier_generator=identifier_generator,
                                            linking_final_header=True)

def link(main_module_name: str,
         object_file_content: ObjectFileContent,
         unique_identifier_prefix: str):
    def identifier_generator_fun():
        for i in itertools.count():
            yield unique_identifier_prefix + str(i)
    identifier_generator = identifier_generator_fun()

    header = compute_merged_header_for_linking(main_module_name, object_file_content, identifier_generator)
    return ir0_to_cpp.header_to_cpp(header, identifier_generator)
