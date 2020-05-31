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
from typing import Iterator, Tuple, Dict

from _py2tmp.compiler.output_files import ObjectFileContent
from _py2tmp.compiler.stages import header_to_cpp
from _py2tmp.ir0 import ir0
from _py2tmp.ir0_optimization import optimize_header


def compute_merged_header_for_linking(main_module_name: str,
                                      object_file_content: ObjectFileContent,
                                      identifier_generator: Iterator[str],
                                      coverage_collection_enabled: bool):
    template_defns = []
    check_if_error_specializations = []
    toplevel_content = []
    split_template_name_by_old_name_and_result_element_name: Dict[Tuple[str, str], str] = dict()

    for module_info in object_file_content.modules_by_name.values():
        template_defns += module_info.ir0_header.template_defns
        check_if_error_specializations += module_info.ir0_header.check_if_error_specializations
        toplevel_content += module_info.ir0_header.toplevel_content
        for key, value in module_info.ir0_header.split_template_name_by_old_name_and_result_element_name:
            split_template_name_by_old_name_and_result_element_name[key] = value

    # template <typename>
    # struct CheckIfError {
    #   using type = void;
    # };
    check_if_error_template_main_definition = ir0.TemplateSpecialization(args=(ir0.TemplateArgDecl(expr_type=ir0.TypeType(),
                                                                                                   name='T',
                                                                                                   is_variadic=False),),
                                                                         patterns=None,
                                                                         body=(ir0.Typedef(name='type',
                                                                                           expr=ir0.AtomicTypeLiteral.for_nonlocal_type('void', may_be_alias=False)),),
                                                                         is_metafunction=True)

    template_defns.append(ir0.TemplateDefn(main_definition=check_if_error_template_main_definition,
                                           specializations=tuple(check_if_error_specializations),
                                           name='CheckIfError',
                                           description='',
                                           result_element_names=frozenset(('type',))))

    public_names = object_file_content.modules_by_name[main_module_name].ir0_header.public_names.union(['CheckIfError'])

    merged_header = ir0.Header(template_defns=tuple(template_defns),
                               check_if_error_specializations=(),
                               toplevel_content=tuple(toplevel_content),
                               split_template_name_by_old_name_and_result_element_name=tuple((k, v)
                                                                                             for k, v in split_template_name_by_old_name_and_result_element_name.items()),
                               public_names=public_names)

    if coverage_collection_enabled:
        return merged_header

    return optimize_header(header=merged_header,
                           context_object_file_content=ObjectFileContent({}),
                           identifier_generator=identifier_generator,
                           linking_final_header=True)

def link(main_module_name: str,
         object_file_content: ObjectFileContent,
         coverage_collection_enabled: bool):
    def identifier_generator_fun() -> Iterator[str]:
        for i in itertools.count():
            yield 'TmppyInternal_' + str(i)
    identifier_generator = identifier_generator_fun()

    header = compute_merged_header_for_linking(main_module_name, object_file_content, identifier_generator, coverage_collection_enabled=coverage_collection_enabled)
    return header_to_cpp(header, identifier_generator, coverage_collection_enabled=coverage_collection_enabled)
