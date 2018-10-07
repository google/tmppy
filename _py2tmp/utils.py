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

import subprocess
from enum import Enum

import networkx as nx
import typed_ast.ast3 as ast

class ValueType:
    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def _key(self):
        return tuple(sorted(self.__dict__.items()))

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self._key())

    def __repr__(self):
        return self.__str__()

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
    elif isinstance(ir_elem, (str, bool, int, Enum)):
        return repr(ir_elem)
    elif isinstance(ir_elem, (list, tuple)):
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
               '-assume-filename=file.cpp',
               '-style=' + str({
                   'BasedOnStyle': code_style,
                   'MaxEmptyLinesToKeep': 0,
                   'KeepEmptyLinesAtTheStartOfBlocks': 'false',
                   'Standard': 'Cpp11'
               })]
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

    if stdout != '' and stdout[-1] != '\n':
        return stdout + '\n'
    else:
        return stdout

def compute_condensation_in_topological_order(dependency_graph: nx.DiGraph, sort_by = lambda x: x):
    if not dependency_graph.number_of_nodes():
        return

    condensed_graph = nx.condensation(dependency_graph)
    assert isinstance(condensed_graph, nx.DiGraph)

    for connected_component_index in nx.topological_sort(condensed_graph, sorted(condensed_graph.nodes_iter(), key=sort_by)):
        yield list(sorted(condensed_graph.node[connected_component_index]['members'], key=sort_by))
