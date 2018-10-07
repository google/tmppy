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
from _py2tmp import ir0, ir0_to_cpp, utils
from _py2tmp.ir0_optimization.configuration_knobs import ConfigurationKnobs

def apply_optimization(template_defn: ir0.TemplateDefn,
                       identifier_generator: Iterator[str],
                       optimization: Callable[[], Tuple[List[ir0.TemplateDefn], bool]],
                       optimization_name: str,
                       other_context: Callable[[], str] = lambda: ''):
    if ConfigurationKnobs.max_num_optimization_steps == 0:
        return [template_defn], False
    ConfigurationKnobs.optimization_step_counter += 1
    if ConfigurationKnobs.max_num_optimization_steps > 0:
        ConfigurationKnobs.max_num_optimization_steps -= 1

    new_template_defns, needs_another_loop = optimization()

    if ConfigurationKnobs.verbose:
        original_cpp = template_defn_to_cpp(template_defn, identifier_generator)
        optimized_cpp = ''.join(template_defn_to_cpp(new_template_defn, identifier_generator)
                                for new_template_defn in new_template_defns)
        _compare_optimized_cpp_to_original(original_cpp, optimized_cpp, optimization_name=optimization_name, other_context=other_context())

    return new_template_defns, needs_another_loop

def apply_toplevel_elems_optimization(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                      identifier_generator: Iterator[str],
                                      optimization: Callable[[], Tuple[List[ir0.TemplateBodyElement], bool]],
                                      optimization_name: str,
                                      other_context: Callable[[], str] = lambda: ''):
    if ConfigurationKnobs.max_num_optimization_steps == 0:
        return toplevel_elems, False
    ConfigurationKnobs.optimization_step_counter += 1
    if ConfigurationKnobs.max_num_optimization_steps > 0:
        ConfigurationKnobs.max_num_optimization_steps -= 1

    new_toplevel_elems, needs_another_loop = optimization()

    if ConfigurationKnobs.verbose:
        original_cpp = _template_body_elems_to_cpp(toplevel_elems, identifier_generator)
        optimized_cpp = _template_body_elems_to_cpp(new_toplevel_elems, identifier_generator)
        _compare_optimized_cpp_to_original(original_cpp, optimized_cpp, optimization_name=optimization_name, other_context=other_context())

    return new_toplevel_elems, needs_another_loop

def template_defn_to_cpp(template_defn: ir0.TemplateDefn, identifier_generator: Iterator[str]):
    writer = ir0_to_cpp.ToplevelWriter(identifier_generator)
    ir0_to_cpp.template_defn_to_cpp(template_defn, enclosing_function_defn_args=[], writer=writer)
    return utils.clang_format(''.join(writer.strings))

def _template_body_elems_to_cpp(elems: List[ir0.TemplateBodyElement],
                                identifier_generator: Iterator[str]):
    elems_except_template_defns = []
    for elem in elems:
        if not isinstance(elem, ir0.TemplateDefn):
            assert isinstance(elem, (ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef))
            elems_except_template_defns.append(elem)
    return ir0_to_cpp.header_to_cpp(ir0.Header(template_defns=[elem
                                                               for elem in elems
                                                               if isinstance(elem, ir0.TemplateDefn)],
                                               toplevel_content=elems_except_template_defns,
                                               public_names=set(),
                                               split_template_name_by_old_name_and_result_element_name=dict()),
                                    identifier_generator)

def _expr_to_cpp(expr: ir0.Expr):
    writer = ir0_to_cpp.ToplevelWriter(identifier_generator=iter([]))
    return ir0_to_cpp.expr_to_cpp(expr, enclosing_function_defn_args=[], writer=writer)

def _compare_optimized_cpp_to_original(original_cpp: str, optimized_cpp: str, optimization_name: str, other_context: str = ''):
    if original_cpp != optimized_cpp:
        diff = ''.join(difflib.unified_diff(original_cpp.splitlines(True),
                                            optimized_cpp.splitlines(True),
                                            fromfile='before.h',
                                            tofile='after.h'))
        print('Original C++:\n' + original_cpp + '\n' + other_context
              + 'After ' + optimization_name + ':\n' + optimized_cpp + '\n'
              + 'Diff:\n' + diff + '\n')
