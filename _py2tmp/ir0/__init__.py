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

from . import ir as ir0
from ._visitor import Visitor
from ._transformation import Transformation, Writer, ToplevelWriter, TemplateBodyWriter, NameReplacementTransformation
from ._is_variadic import is_expr_variadic
from ._builtin_literals import GlobalLiterals, GLOBAL_LITERALS_BY_NAME, select1st_literal
from ._template_dependency_graph import compute_template_dependency_graph
