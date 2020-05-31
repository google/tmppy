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

import difflib
from typing import Iterator, Callable, Tuple, List, Union

from _py2tmp.compiler.stages import header_to_cpp
from _py2tmp.ir0 import ir
from _py2tmp.ir0_optimization._configuration_knobs import ConfigurationKnobs

def apply_elem_optimization(elems: Tuple,
                            optimization: Callable[[], Tuple[Tuple, bool]],
                            describe_elems: Callable[[Tuple], str],
                            optimization_name: str,
                            other_context: Callable[[], str] = lambda: ''):
    if ConfigurationKnobs.max_num_optimization_steps == 0:
        return elems, False
    ConfigurationKnobs.optimization_step_counter += 1
    if ConfigurationKnobs.max_num_optimization_steps > 0:
        ConfigurationKnobs.max_num_optimization_steps -= 1

    new_elems, needs_another_loop = optimization()

    if ConfigurationKnobs.verbose:
        original_cpp = describe_elems(elems)
        optimized_cpp = describe_elems(new_elems)

        if original_cpp != optimized_cpp:
            diff = ''.join(difflib.unified_diff(original_cpp.splitlines(True),
                                                optimized_cpp.splitlines(True),
                                                fromfile='before.h',
                                                tofile='after.h'))
            print('Original C++:\n' + original_cpp + '\n' + other_context()
                  + 'After ' + optimization_name + ':\n' + optimized_cpp + '\n'
                  + 'Diff:\n' + diff + '\n')

    return new_elems, needs_another_loop

def describe_headers(headers: List[ir.Header],
                     identifier_generator: Iterator[str]):
    return ''.join(header_to_cpp(header, identifier_generator, coverage_collection_enabled=False)
                   for header in headers)

def describe_template_defns(template_defns: Tuple[ir.TemplateDefn, ...], identifier_generator: Iterator[str]):
    return header_to_cpp(ir.Header(template_defns=template_defns,
                                   check_if_error_specializations=(),
                                   toplevel_content=(),
                                   public_names=frozenset(),
                                   split_template_name_by_old_name_and_result_element_name=()),
                         identifier_generator,
                         coverage_collection_enabled=False)

def describe_toplevel_elems(toplevel_elems: Tuple[Union[ir.StaticAssert, ir.ConstantDef, ir.Typedef], ...],
                            identifier_generator: Iterator[str]):
    return header_to_cpp(ir.Header(template_defns=(),
                                   toplevel_content=toplevel_elems,
                                   public_names=frozenset(),
                                   split_template_name_by_old_name_and_result_element_name=(),
                                   check_if_error_specializations=()),
                         identifier_generator,
                         coverage_collection_enabled=False)

def combine_optimizations(ir, optimizations):
    needs_another_loop = False
    for optimization in optimizations:
        ir, needs_another_loop1 = optimization(ir)
        needs_another_loop |= needs_another_loop1

    return ir, needs_another_loop

def optimize_list(list, optimization):
    needs_another_loop = False
    result_list = []
    for elem in list:
        elem, needs_another_loop1 = optimization(elem)
        needs_another_loop |= needs_another_loop1
        result_list.append(elem)

    return result_list, needs_another_loop
