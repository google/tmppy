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
from typing import Dict, List, Optional

from _py2tmp import ir3, ir0, ir2, ir1
from _py2tmp.value_type import ValueType

class ModuleInfo(ValueType):
    def __init__(self,
                 ir3_module: ir3.Module,
                 ir0_header: ir0.Header,
                 ir0_header_before_optimization: Optional[ir0.Header] = None,
                 ir1_module: Optional[ir1.Module] = None,
                 ir2_module: Optional[ir2.Module] = None):
        self.ir3_module = ir3_module
        self.ir2_module = ir2_module
        self.ir1_module = ir1_module
        self.ir0_header_before_optimization = ir0_header_before_optimization
        self.ir0_header = ir0_header

class ObjectFileContent(ValueType):
    def __init__(self, modules_by_name: Dict[str, ModuleInfo]):
        self.modules_by_name = modules_by_name

def merge_object_files(object_files: List[ObjectFileContent]):
    modules_by_name = dict()
    for object_file in object_files:
        for name, module_info in object_file.modules_by_name.items():
            # If there are duplicates we assume that they're the same, we don't check here.
            modules_by_name[name] = module_info
    return ObjectFileContent(modules_by_name)
