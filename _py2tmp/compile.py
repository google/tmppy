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
from typing import List, Optional
import typed_ast.ast3 as ast

from _py2tmp import ast_to_ir3, ir3_optimization, ir3_to_ir2, ir2_to_ir1, ir1_to_ir0, ir0_optimization
from _py2tmp.tmppy_object_file import ObjectFileContent, ModuleInfo

def _module_name_from_filename(file_name: str):
    return file_name.replace('/', '.')

def compile(file_name: str,
            context_object_files: List[str],
            unique_identifier_prefix: str,
            include_intermediate_irs_for_debugging: bool,
            module_name: Optional[str] = None):
    if not module_name:
        module_name = _module_name_from_filename(file_name)
    with open(file_name) as file:
        tmppy_source_code = file.read()

    context_modules_by_name = dict()
    for context_module_file_name in context_object_files:
        with open(context_module_file_name) as file:
            context_modules_by_name[_module_name_from_filename(context_module_file_name)] = ModuleInfo.from_json(file.read())

    return compile_source_code(module_name=module_name,
                               file_name=file_name,
                               source_code=tmppy_source_code,
                               unique_identifier_prefix=unique_identifier_prefix,
                               include_intermediate_irs_for_debugging=include_intermediate_irs_for_debugging,
                               context_object_file_content=ObjectFileContent(context_modules_by_name))

def compile_source_code(module_name: str,
                        source_code: str,
                        context_object_file_content: ObjectFileContent,
                        unique_identifier_prefix: str,
                        include_intermediate_irs_for_debugging: bool,
                        file_name: str = '<unknown>'):

    source_ast = ast.parse(source_code, filename=file_name)

    def identifier_generator_fun():
        for i in itertools.count():
            yield unique_identifier_prefix + str(i)

    identifier_generator = iter(identifier_generator_fun())
    module_ir3 = ast_to_ir3.module_ast_to_ir3(source_ast,
                                              file_name,
                                              source_code.splitlines(),
                                              identifier_generator)
    module_ir3 = ir3_optimization.optimize_module(module_ir3)
    module_ir2 = ir3_to_ir2.module_to_ir2(module_ir3, identifier_generator)
    module_ir1 = ir2_to_ir1.module_to_ir1(module_ir2)
    non_optimized_header = ir1_to_ir0.module_to_ir0(module_ir1, identifier_generator)
    optimized_header = ir0_optimization.optimize_header(header=non_optimized_header,
                                                        identifier_generator=identifier_generator,
                                                        context_object_file_content=context_object_file_content,
                                                        linking_final_header=False)

    if include_intermediate_irs_for_debugging:
        module_info = ModuleInfo(ir0_header=optimized_header,
                                 ir0_header_before_optimization=non_optimized_header,
                                 ir1_module=module_ir1,
                                 ir2_module=module_ir2,
                                 ir3_module=module_ir3)
    else:
        module_info = ModuleInfo(ir0_header=optimized_header,
                                 ir3_module=module_ir3)

    return ObjectFileContent({module_name: module_info})
