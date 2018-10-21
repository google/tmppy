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
import pickle
from typing import List

import typed_ast.ast3 as ast

from _py2tmp.compiler.stages import module_ast_to_ir3, module_to_ir2, module_to_ir0
from _py2tmp.compiler.output_files import ObjectFileContent, ModuleInfo, merge_object_files
from _py2tmp.ir0_optimization import optimize_header
from _py2tmp.ir3_optimization import optimize_module


def compile(file_name: str,
            context_object_files: List[str],
            include_intermediate_irs_for_debugging: bool,
            module_name: str):
    with open(file_name) as file:
        tmppy_source_code = file.read()

    object_file_contents = []
    for context_module_file_name in context_object_files:
        with open(context_module_file_name, 'rb') as file:
            object_file_contents.append(pickle.loads(file.read()))

    return compile_source_code(module_name=module_name,
                               file_name=file_name,
                               source_code=tmppy_source_code,
                               include_intermediate_irs_for_debugging=include_intermediate_irs_for_debugging,
                               context_object_file_content=merge_object_files(object_file_contents))

def compile_source_code(module_name: str,
                        source_code: str,
                        context_object_file_content: ObjectFileContent,
                        include_intermediate_irs_for_debugging: bool,
                        file_name: str = '<unknown>'):

    source_ast = ast.parse(source_code, filename=file_name)

    unique_identifier_prefix = 'tmppy_internal_'+ module_name.replace('.', '_') + '_x'

    def identifier_generator_fun():
        for i in itertools.count():
            yield unique_identifier_prefix + str(i)

    identifier_generator = iter(identifier_generator_fun())
    module_ir3 = module_ast_to_ir3(source_ast,
                                   file_name,
                                   source_code.splitlines(),
                                   identifier_generator,
                                   context_object_file_content)
    module_ir3 = optimize_module(module_ir3, context_object_file_content)
    module_ir2 = module_to_ir2(module_ir3, identifier_generator)
    non_optimized_header = module_to_ir0(module_ir2, identifier_generator)
    optimized_header = optimize_header(header=non_optimized_header,
                                       identifier_generator=identifier_generator,
                                       context_object_file_content=context_object_file_content,
                                       linking_final_header=False)

    if include_intermediate_irs_for_debugging:
        module_info = ModuleInfo(ir0_header=optimized_header,
                                 ir0_header_before_optimization=non_optimized_header,
                                 ir2_module=module_ir2,
                                 ir3_module=module_ir3)
    else:
        module_info = ModuleInfo(ir0_header=optimized_header,
                                 ir3_module=module_ir3)

    modules_by_name = {module_name: (module_info
                                     if module_info.ir3_module is None
                                     else ModuleInfo(ir3_module=None,
                                                     ir2_module=module_info.ir2_module,
                                                     ir0_header_before_optimization=module_info.ir0_header_before_optimization,
                                                     ir0_header=module_info.ir0_header))
                       for module_name, module_info in context_object_file_content.modules_by_name.items()}
    modules_by_name[module_name] = module_info

    return ObjectFileContent(modules_by_name)
