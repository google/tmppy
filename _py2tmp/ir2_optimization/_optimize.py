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
from _py2tmp.compiler.output_files import ObjectFileContent
from _py2tmp.ir2 import ir2
from _py2tmp.ir2_optimization._recalculate_function_can_throw_info import recalculate_function_can_throw_info


def optimize_module(module: ir2.Module, context_object_file_content: ObjectFileContent):
    module = recalculate_function_can_throw_info(module, context_object_file_content)
    return module
