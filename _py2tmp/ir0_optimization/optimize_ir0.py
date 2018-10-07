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
from typing import Iterator

import networkx as nx

from _py2tmp import ir0, utils, ir0_to_cpp
from _py2tmp.ir0_optimization.configuration_knobs import ConfigurationKnobs
from _py2tmp.ir0_optimization.local_optimizations import perform_local_optimizations_on_template_defn, perform_local_optimizations_on_toplevel_elems
from _py2tmp.ir0_optimization.optimization_execution import apply_optimization
from _py2tmp.ir0_optimization.recalculate_template_instantiation_can_trigger_static_asserts_info import recalculate_template_instantiation_can_trigger_static_asserts_info
from _py2tmp.ir0_optimization.split_template_defn_with_multiple_outputs import split_template_defn_with_multiple_outputs, replace_metafunction_calls_with_split_template_calls
from _py2tmp.ir0_optimization.template_dependency_graph import compute_template_dependency_graph
from _py2tmp.ir0_optimization.template_instantiation_inlining import perform_template_inlining, perform_template_inlining_on_toplevel_elems


def _calculate_max_num_optimization_loops(num_templates_in_connected_component):
    # This is just a heuristic. We want to make enough loops to fully optimize the code but without looping forever
    # when there are mutually-recursive functions.
    return num_templates_in_connected_component * 20 + 20

def _optimize_header_first_pass(header: ir0.Header, identifier_generator: Iterator[str]):
    assert not header.split_template_name_by_old_name_and_result_element_name

    from _py2tmp import ir0_builtins
    split_template_name_by_old_name_and_result_element_name = ir0_builtins.get_split_template_name_by_old_name_and_result_element_name().copy()

    new_template_defns = []
    for template_defn in header.template_defns:
        results, needs_another_loop = apply_optimization(template_defn,
                                                         identifier_generator,
                                                         optimization=lambda: split_template_defn_with_multiple_outputs(template_defn,
                                                                                                                        split_template_name_by_old_name_and_result_element_name,
                                                                                                                        identifier_generator),
                                                         optimization_name='split_template_defn_with_specializations_and_multiple_outputs()')
        assert not needs_another_loop

        for result in results:
            new_template_defns.append(result)

    return replace_metafunction_calls_with_split_template_calls(header,
                                                                identifier_generator,
                                                                new_template_defns,
                                                                split_template_name_by_old_name_and_result_element_name)

def _optimize_header_second_pass(header: ir0.Header, identifier_generator: Iterator[str]):
    new_template_defns = {elem.name: elem
                          for elem in header.template_defns}

    template_dependency_graph = compute_template_dependency_graph(header.template_defns, new_template_defns)

    template_dependency_graph_transitive_closure = nx.transitive_closure(template_dependency_graph)
    assert isinstance(template_dependency_graph_transitive_closure, nx.DiGraph)

    for connected_component in reversed(list(utils.compute_condensation_in_topological_order(template_dependency_graph))):
        needs_another_loop = True
        max_num_remaining_loops = _calculate_max_num_optimization_loops(len(connected_component))
        while needs_another_loop and max_num_remaining_loops:
            needs_another_loop = False
            max_num_remaining_loops -= 1
            for template_name in sorted(connected_component, key=lambda node: new_template_defns[node].name):
                template_defn = new_template_defns[template_name]

                inlineable_refs = {other_node
                                   for other_node in template_dependency_graph_transitive_closure.successors(template_name)
                                   if not template_dependency_graph_transitive_closure.has_edge(other_node, template_name)}
                template_defn, needs_another_loop1 = perform_template_inlining(template_defn,
                                                                               inlineable_refs,
                                                                               new_template_defns,
                                                                               identifier_generator)
                if needs_another_loop1:
                    needs_another_loop = True

                template_defn, needs_another_loop1 = perform_local_optimizations_on_template_defn(template_defn,
                                                                                                  identifier_generator,
                                                                                                  inline_template_instantiations_with_multiple_references=False)
                if needs_another_loop1:
                    needs_another_loop = True

                new_template_defns[template_name] = template_defn

        if not max_num_remaining_loops:
            ConfigurationKnobs.reached_max_num_remaining_loops_counter += 1
            if ConfigurationKnobs.verbose:
                print('Hit max_num_remaining_loops == %s while optimizing:\n%s' % (_calculate_max_num_optimization_loops(len(connected_component)), '\n'.join(ir0_to_cpp.toplevel_elem_to_cpp_simple(new_template_defns[template_name])
                                                                                                                                                              for template_name in connected_component)))


    new_toplevel_content = header.toplevel_content


    inlineable_refs = set()
    for template_name in new_template_defns.keys():
        template_defn = new_template_defns[template_name]
        # We won't inline templates that contain inner templates, because that would lead to
        #  TemplateDefn toplevel_content elements that may depend on non-TemplateDefn toplevel_content
        #  elements, so we would be unable to perform the usual optimizations that assume that no
        #  TemplateDefn elements don't depend on toplevel_content elements.
        if all(not isinstance(elem, ir0.TemplateDefn)
               for specialization in itertools.chain((template_defn.main_definition,) if template_defn.main_definition else tuple(),
                                                     template_defn.specializations if template_defn.specializations else tuple())
               for elem in specialization.body):
            inlineable_refs.add(template_name)

    needs_another_loop = True
    max_num_remaining_loops = _calculate_max_num_optimization_loops(len(new_toplevel_content))
    additional_toplevel_template_defns = []
    while needs_another_loop and max_num_remaining_loops:
        needs_another_loop = False
        max_num_remaining_loops -= 1

        elems, needs_another_loop1 = perform_template_inlining_on_toplevel_elems(new_toplevel_content,
                                                                                 inlineable_refs,
                                                                                 new_template_defns,
                                                                                 identifier_generator)
        if needs_another_loop1:
            needs_another_loop = True

        additional_toplevel_template_defns += [elem
                                               for elem in elems
                                               if isinstance(elem, ir0.TemplateDefn)]
        new_toplevel_content = [elem
                                for elem in elems
                                if not isinstance(elem, ir0.TemplateDefn)]

        new_toplevel_content, needs_another_loop1 = perform_local_optimizations_on_toplevel_elems(new_toplevel_content,
                                                                                                  identifier_generator,
                                                                                                  inline_template_instantiations_with_multiple_references=False)
        if needs_another_loop1:
            needs_another_loop = True

    if not max_num_remaining_loops:
        ConfigurationKnobs.reached_max_num_remaining_loops_counter += 1
        if ConfigurationKnobs.verbose:
            print('Hit max_num_remaining_loops == %s while optimizing:\n%s' % (_calculate_max_num_optimization_loops(len(new_toplevel_content)), '\n'.join(ir0_to_cpp.toplevel_elem_to_cpp_simple(elem)
                                                                                                                                                           for elem in new_toplevel_content)))

    return ir0.Header(template_defns=[new_template_defns[template_defn.name]
                                      for template_defn in header.template_defns] + additional_toplevel_template_defns,
                      toplevel_content=new_toplevel_content,
                      public_names=header.public_names,
                      split_template_name_by_old_name_and_result_element_name=header.split_template_name_by_old_name_and_result_element_name)

def _optimize_header_third_pass(header: ir0.Header, linking_final_header: bool):
    template_defns_by_name = {elem.name: elem
                              for elem in header.template_defns}

    public_names = header.public_names
    if not linking_final_header:
        public_names = public_names.union(header.split_template_name_by_old_name_and_result_element_name.values())

    template_dependency_graph = nx.DiGraph()
    for elem in itertools.chain(header.template_defns, header.toplevel_content):
        if isinstance(elem, ir0.TemplateDefn):
            elem_name = elem.name
        else:
            # We'll use a dummy name for non-template toplevel elems.
            elem_name = ''

        template_dependency_graph.add_node(elem_name)

        if elem_name in public_names:
            # We also add an edge from the node '' to all public template defns, so that we can use '' as a source below.
            template_dependency_graph.add_edge('', elem_name)

        for identifier in elem.get_referenced_identifiers():
            if identifier in template_defns_by_name.keys():
                template_dependency_graph.add_edge(elem_name, identifier)

    used_templates = nx.single_source_shortest_path(template_dependency_graph, source='').keys()

    return ir0.Header(template_defns=[template_defn
                                      for template_defn in header.template_defns
                                      if template_defn.name in used_templates],
                      toplevel_content=header.toplevel_content,
                      public_names=public_names,
                      split_template_name_by_old_name_and_result_element_name=header.split_template_name_by_old_name_and_result_element_name)

def optimize_header(header: ir0.Header, identifier_generator: Iterator[str], linking_final_header: bool):
    header = recalculate_template_instantiation_can_trigger_static_asserts_info(header)
    header = _optimize_header_first_pass(header, identifier_generator)
    header = _optimize_header_second_pass(header, identifier_generator)
    header = _optimize_header_third_pass(header, linking_final_header)
    return header
