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

from collections import defaultdict
from _py2tmp import ir0, utils, transform_ir0
import networkx as nx
from typing import List, Union, Dict, Set, Iterable

def normalize_template_defn(template_defn: ir0.TemplateDefn, identifier_generator: Iterable[str]):
  '''Converts template_defn to an equivalent TemplateDefn where all expressions contain 0 or 1 operations.

  Unlike other constants/typedefs, the exprs that initialize "result" and "error" will always have 0 operations.
  '''
  # TODO
  return template_defn

def perform_local_optimizations_on_template_defn(template_defn: ir0.TemplateDefn):
  # TODO
  print('perform_local_optimizations_on_template_defn() called for template:', template_defn.name)
  return template_defn

def perform_template_inlining(template_defn: ir0.TemplateDefn,
                              inlineable_refs: Set[str],
                              template_defn_by_name: Dict[str, ir0.TemplateDefn],
                              identifier_generator: Iterable[str]):
  template_defn = normalize_template_defn(template_defn, identifier_generator)
  # TODO
  print('perform_template_inlining() called for template:', template_defn.name, '. Inline-able refs: ', inlineable_refs)
  return template_defn

def optimize_header(header: ir0.Header, identifier_generator: Iterable[str]):
  template_dependency_graph = nx.DiGraph()

  new_template_defns = {elem.name: elem
                        for elem in header.content
                        if isinstance(elem, ir0.TemplateDefn)} # type: Dict[str, ir0.TemplateDefn]

  for elem in header.content:
    if isinstance(elem, ir0.TemplateDefn):
      template_dependency_graph.add_node(elem.name)

      for identifier in elem.get_referenced_identifiers():
        if identifier in new_template_defns.keys():
          template_dependency_graph.add_edge(elem.name, identifier)

  condensed_graph = nx.condensation(template_dependency_graph)
  assert isinstance(condensed_graph, nx.DiGraph)

  template_dependency_graph_transitive_closure = nx.transitive_closure(template_dependency_graph)
  assert isinstance(template_dependency_graph_transitive_closure, nx.DiGraph)

  for connected_component_index in nx.topological_sort(condensed_graph, reverse=True):
    connected_component = condensed_graph.node[connected_component_index]['members']
    for node in connected_component:
      template_defn = new_template_defns[node]

      inlineable_refs = {other_node
                         for other_node in template_dependency_graph.successors(node)
                         if not template_dependency_graph_transitive_closure.has_edge(other_node, node)
                         and not new_template_defns[other_node].specializations}
      if inlineable_refs:
        template_defn = perform_template_inlining(template_defn,
                                                  inlineable_refs,
                                                  new_template_defns,
                                                  identifier_generator)

      template_defn = perform_local_optimizations_on_template_defn(template_defn)
      new_template_defns[node] = template_defn

  new_elems = []
  for elem in header.content:
    if isinstance(elem, ir0.TemplateDefn):
      new_elems.append(new_template_defns[elem.name])
    else:
      new_elems.append(elem)
    
  return ir0.Header(new_elems)
