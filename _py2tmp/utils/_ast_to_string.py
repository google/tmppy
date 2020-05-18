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

import ast


def ast_to_string(ast_node, line_indent=''):
    next_line_indent = line_indent + '  '

    if isinstance(ast_node, ast.AST):
        return (ast_node.__class__.__name__
                + '('
                + ','.join('\n' + next_line_indent + field_name + ' = ' + ast_to_string(child_node, next_line_indent)
                           for field_name, child_node in ast.iter_fields(ast_node))
                + ')')
    elif isinstance(ast_node, list):
        return ('['
                + ','.join('\n' + next_line_indent + ast_to_string(child_node, next_line_indent)
                           for child_node in ast_node)
                + ']')
    else:
        return repr(ast_node)