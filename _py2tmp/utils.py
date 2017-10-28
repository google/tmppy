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

import re
import subprocess
from enum import Enum

import typed_ast.ast3 as ast

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

def ir_to_string(ir_elem, line_indent=''):
    next_line_indent = line_indent + '  '

    if ir_elem is None:
        return 'None'
    elif isinstance(ir_elem, (str, bool, Enum)):
        return repr(ir_elem)
    elif isinstance(ir_elem, list):
        return ('['
                + ','.join('\n' + next_line_indent + ir_to_string(child_node, next_line_indent)
                           for child_node in ir_elem)
                + ']')
    else:
        return (ir_elem.__class__.__name__
                + '('
                + ','.join('\n' + next_line_indent + field_name + ' = ' + ir_to_string(child_node, next_line_indent)
                           for field_name, child_node in ir_elem.__dict__.items())
                + ')')

def clang_format(cxx_source: str, code_style='LLVM') -> str:
    command = ['clang-format',
               '-assume-filename=file.h',
               "-style={BasedOnStyle: %s, MaxEmptyLinesToKeep: 0, KeepEmptyLinesAtTheStartOfBlocks: false}"
               % code_style
               ]
    try:
        p = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True)
        stdout, stderr = p.communicate(cxx_source)
    except Exception:  # pragma: no cover
        raise Exception("Error while executing %s" % command)
    if p.returncode != 0:  # pragma: no cover
        raise Exception('clang-format exited with error code %s. Command was: %s. Error:\n%s' % (p.returncode, command, stderr))
    assert isinstance(stdout, str)
    return stdout

def replace_identifiers(cpp_type, replacements):
    last_index = 0
    result_parts = []
    for match in re.finditer(r'[a-zA-Z_][a-zA-Z_0-9]*', cpp_type):
        result_parts.append(cpp_type[last_index:match.start()])
        identifier = match.group(0)
        if identifier in replacements:
            result_parts.append(replacements[identifier])
        else:
            result_parts.append(identifier)
        last_index = match.end()
    result_parts.append(cpp_type[last_index:])
    return ''.join(result_parts)
