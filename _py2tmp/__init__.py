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

# This file was intentionally left blank.

from _py2tmp.tmppy_object_file import ObjectFileContent, ModuleInfo
from _py2tmp.compile import compile, compile_source_code
from _py2tmp.link import link, compute_merged_header_for_linking
from _py2tmp.ast_to_ir3 import CompilationError
from _py2tmp.ir0_optimization import ConfigurationKnobs, DEFAULT_VERBOSE_SETTING