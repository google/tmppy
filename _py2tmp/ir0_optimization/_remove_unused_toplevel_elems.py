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

import networkx as nx

from _py2tmp.ir0 import ir


def remove_unused_toplevel_elems(header: ir.Header, linking_final_header: bool):
    toplevel_elem_names = {elem.name
                           for elem in itertools.chain(header.toplevel_content, header.template_defns)
                           if not isinstance(elem, (ir.StaticAssert, ir.NoOpStmt))}

    public_names = header.public_names
    if not linking_final_header:
        public_names = public_names.union(split_name
                                          for _, split_name in header.split_template_name_by_old_name_and_result_element_name)

    elem_dependency_graph = nx.DiGraph()
    for elem in itertools.chain(header.template_defns, header.toplevel_content):
        if isinstance(elem, (ir.TemplateDefn, ir.ConstantDef, ir.Typedef)):
            elem_name = elem.name
        else:
            # We'll use a dummy name for non-template toplevel elems.
            elem_name = ''

        elem_dependency_graph.add_node(elem_name)

        if elem_name in public_names or (isinstance(elem, (ir.ConstantDef, ir.Typedef)) and any(isinstance(expr, ir.TemplateInstantiation) and expr.instantiation_might_trigger_static_asserts
                                                                                                for expr in elem.transitive_subexpressions)):
            # We also add an edge from the node '' to all toplevel defns that must remain, so that we can use '' as a source below.
            elem_dependency_graph.add_edge('', elem_name)

        for identifier in elem.referenced_identifiers:
            if identifier in toplevel_elem_names:
                elem_dependency_graph.add_edge(elem_name, identifier)

    elem_dependency_graph.add_node('')
    used_elem_names = nx.single_source_shortest_path(elem_dependency_graph, source='').keys()

    return ir.Header(template_defns=tuple(template_defn for template_defn in header.template_defns if
                                          template_defn.name in used_elem_names),
                     toplevel_content=tuple(elem for elem in header.toplevel_content if
                                            isinstance(elem, (ir.StaticAssert, ir.NoOpStmt)) or elem.name in used_elem_names),
                     public_names=header.public_names,
                     split_template_name_by_old_name_and_result_element_name=header.split_template_name_by_old_name_and_result_element_name,
                     check_if_error_specializations=header.check_if_error_specializations)

