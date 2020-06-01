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

from typing import Iterator, Any, Callable, Tuple

import networkx as nx

from _py2tmp.compiler.output_files import ObjectFileContent
from _py2tmp.compiler.stages import template_defn_to_cpp_simple, toplevel_elem_to_cpp_simple
from _py2tmp.ir0 import compute_template_dependency_graph
from _py2tmp.ir0 import ir
from _py2tmp.ir0_optimization._configuration_knobs import ConfigurationKnobs
from _py2tmp.ir0_optimization._local_optimizations import perform_local_optimizations_on_template_defn, \
    perform_local_optimizations_on_toplevel_elems
from _py2tmp.ir0_optimization._optimization_execution import apply_elem_optimization, describe_template_defns, \
    combine_optimizations, optimize_list, describe_headers
from _py2tmp.ir0_optimization._recalculate_template_instantiation_can_trigger_static_asserts_info import \
    recalculate_template_instantiation_can_trigger_static_asserts_info
from _py2tmp.ir0_optimization._remove_unused_toplevel_elems import remove_unused_toplevel_elems
from _py2tmp.ir0_optimization._split_template_defn_with_multiple_outputs import \
    split_template_defn_with_multiple_outputs, replace_metafunction_calls_with_split_template_calls
from _py2tmp.ir0_optimization._template_instantiation_inlining import perform_template_inlining, \
    perform_template_inlining_on_toplevel_elems
from _py2tmp.ir0_optimization.replace_templates_with_templated_using_declarations import \
    move_template_args_to_using_declarations
from _py2tmp.utils import compute_condensation_in_topological_order


def _calculate_max_num_optimization_loops(size: int):
    # This is just a heuristic. We want to make enough loops to fully optimize the code but without looping forever
    # when there are mutually-recursive functions.
    return size * 10 + 40

def _optimize_header_first_pass(header: ir.Header,
                                identifier_generator: Iterator[str],
                                context_object_file_content: ObjectFileContent):
    if header.split_template_name_by_old_name_and_result_element_name:
        # This happens when linking. We already did all the needed splits, no need for more (and we don't want to
        # overwrite split_template_name_by_old_name_and_result_element_name).
        return header

    split_template_name_by_old_name_and_result_element_name = {key: value
                                                               for module_info in context_object_file_content.modules_by_name.values()
                                                               for key, value in module_info.ir0_header.split_template_name_by_old_name_and_result_element_name}

    new_template_defns = []
    for template_defn in header.template_defns:
        results, needs_another_loop = apply_elem_optimization((template_defn,),
                                                              lambda: split_template_defn_with_multiple_outputs(template_defn,
                                                                                                                split_template_name_by_old_name_and_result_element_name,
                                                                                                                identifier_generator),
                                                              lambda template_defns: describe_template_defns(template_defns, identifier_generator),
                                                              optimization_name='split_template_defn_with_specializations_and_multiple_outputs()')
        assert not needs_another_loop

        for result in results:
            new_template_defns.append(result)

    [header], _ = apply_elem_optimization(
        (header,),
        lambda:  ((replace_metafunction_calls_with_split_template_calls(header,
                                                                        new_template_defns,
                                                                        split_template_name_by_old_name_and_result_element_name),),
                  False),
        lambda header: describe_headers([header], identifier_generator),
        optimization_name='replace_metafunction_calls_with_split_template_calls')
    return header

def _iterate_optimization(ir: Any,
                          optimize: Callable[[Any], Tuple[Any, bool]],
                          size: int,
                          describe_optimization_target: Callable[[Any], str]):
    needs_another_loop = True
    max_num_remaining_loops = _calculate_max_num_optimization_loops(size)
    while needs_another_loop and max_num_remaining_loops:
        max_num_remaining_loops -= 1
        ir, needs_another_loop = optimize(ir)

    if not max_num_remaining_loops:
        ConfigurationKnobs.reached_max_num_remaining_loops_counter += 1
        print('Hit max_num_remaining_loops == %s while optimizing:\n%s' % (_calculate_max_num_optimization_loops(size),
                                                                           describe_optimization_target(ir)))

    return ir

def _optimize_header_second_pass(header: ir.Header,
                                 identifier_generator: Iterator[str],
                                 context_object_file_content: ObjectFileContent):
    new_template_defns = {elem.name: elem
                          for elem in header.template_defns}

    template_dependency_graph = compute_template_dependency_graph(header.template_defns, new_template_defns)

    template_dependency_graph_transitive_closure = nx.transitive_closure(template_dependency_graph)
    assert isinstance(template_dependency_graph_transitive_closure, nx.DiGraph)

    optimizations = [
        lambda template_defn: perform_template_inlining(template_defn,
                                                        {other_node
                                                         for other_node in template_dependency_graph_transitive_closure.successors(template_defn.name)
                                                         if not template_dependency_graph_transitive_closure.has_edge(other_node, template_defn.name)},
                                                        new_template_defns,
                                                        identifier_generator,
                                                        context_object_file_content),
        lambda template_defn: perform_local_optimizations_on_template_defn(template_defn,
                                                                           identifier_generator,
                                                                           inline_template_instantiations_with_multiple_references=False),
    ]

    for connected_component in reversed(list(
            compute_condensation_in_topological_order(template_dependency_graph))):
        def optimize(template_name: str):
            new_template_defns[template_name], needs_another_loop = combine_optimizations(new_template_defns[template_name], optimizations)
            return None, needs_another_loop

        _iterate_optimization(None,
                              lambda _: optimize_list(sorted(connected_component, key=lambda node: new_template_defns[node].name),
                                                      lambda template_name: optimize(template_name)),
                              len(connected_component),
                              lambda _: '\n'.join(template_defn_to_cpp_simple(new_template_defns[template_name], identifier_generator)
                                                  for template_name in connected_component))



    optimizations = [
        lambda toplevel_content: perform_template_inlining_on_toplevel_elems(toplevel_content,
                                                                             new_template_defns.keys(),
                                                                             new_template_defns,
                                                                             identifier_generator,
                                                                             context_object_file_content),
        lambda toplevel_content: perform_local_optimizations_on_toplevel_elems(toplevel_content,
                                                                               identifier_generator,
                                                                               inline_template_instantiations_with_multiple_references=False),
    ]

    toplevel_content = _iterate_optimization(header.toplevel_content,
                                             lambda toplevel_content: combine_optimizations(toplevel_content, optimizations),
                                             len(header.toplevel_content),
                                             lambda toplevel_content: '\n'.join(toplevel_elem_to_cpp_simple(elem, identifier_generator)
                                                                                for elem in toplevel_content))

    return ir.Header(template_defns=tuple(new_template_defns[template_defn.name]
                                          for template_defn in header.template_defns),
                     toplevel_content=toplevel_content,
                     public_names=header.public_names,
                     split_template_name_by_old_name_and_result_element_name=header.split_template_name_by_old_name_and_result_element_name,
                     check_if_error_specializations=header.check_if_error_specializations)

def _optimize_header_third_pass(header: ir.Header, linking_final_header: bool):
    # We call this directly, not through apply_elem_optimization(), since that would pollute the diagnostics for failed
    # tests and it would significantly slow down the test compilation in non-optimized mode.
    return remove_unused_toplevel_elems(header, linking_final_header)

def optimize_header(header: ir.Header,
                    context_object_file_content: ObjectFileContent,
                    identifier_generator: Iterator[str],
                    linking_final_header: bool):
    if linking_final_header:
        # This is just a performance optimization. Notably this removes any unused builtins, to avoid wasting time
        # optimizing those.
        header = _optimize_header_third_pass(header, linking_final_header)

    header = recalculate_template_instantiation_can_trigger_static_asserts_info(header)
    header = _optimize_header_first_pass(header, identifier_generator, context_object_file_content)
    header = _optimize_header_second_pass(header, identifier_generator, context_object_file_content)
    header = _optimize_header_third_pass(header, linking_final_header)

    if linking_final_header:
        [header], _ = apply_elem_optimization((header,),
                                              lambda: ((move_template_args_to_using_declarations(header),), False),
                                              lambda headers: describe_headers(headers, identifier_generator),
                                              optimization_name='replace_templates_with_templated_using_declarations',
                                              other_context=lambda: '')

    return header
