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
import pickle
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from _py2tmp.ir2 import ir2
from _py2tmp.ir1 import ir1
from _py2tmp.ir0 import ir0

@dataclass(frozen=True)
class ModuleInfo:
    ir2_module: Optional[ir2.Module]
    ir0_header: ir0.Header
    ir0_header_before_optimization: Optional[ir0.Header] = None
    ir1_module: Optional[ir1.Module] = None

@dataclass(frozen=True)
class ObjectFileContent:
    modules_by_name: Dict[str, ModuleInfo]

def merge_object_files(object_files: List[ObjectFileContent]):
    modules_by_name = dict()
    for object_file in object_files:
        for name, module_info in object_file.modules_by_name.items():
            if name not in modules_by_name or modules_by_name[name].ir2_module is None:
                modules_by_name[name] = module_info
    return ObjectFileContent(modules_by_name)

@lru_cache()
def load_object_files(object_file_paths: Tuple[str, ...]) -> ObjectFileContent:
    object_file_contents = []
    for context_module_file_name in object_file_paths:
        with open(context_module_file_name, 'rb') as file:
            object_file_contents.append(pickle.loads(file.read()))

    return merge_object_files(object_file_contents)
