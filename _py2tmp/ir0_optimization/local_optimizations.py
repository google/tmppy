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

from typing import List, Union, Iterator

from _py2tmp import ir0
from _py2tmp.ir0_optimization.common_subexpression_elimination import perform_common_subexpression_normalization, perform_common_subexpression_normalization_on_toplevel_elems
from _py2tmp.ir0_optimization.constant_folding import perform_constant_folding, perform_constant_folding_on_toplevel_elems
from _py2tmp.ir0_optimization.expression_simplification import perform_expression_simplification, perform_expression_simplification_on_toplevel_elems
from _py2tmp.ir0_optimization.normalize_expressions import normalize_template_defn, normalize_toplevel_elems
from _py2tmp.ir0_optimization.optimization_execution import apply_template_defn_optimization, apply_toplevel_elems_optimization

def perform_local_optimizations_on_template_defn(template_defn: ir0.TemplateDefn,
                                                 identifier_generator: Iterator[str],
                                                 inline_template_instantiations_with_multiple_references: bool):
    [template_defn], needs_another_loop1 = apply_template_defn_optimization(template_defn,
                                                                            identifier_generator,
                                                                            optimization=lambda: normalize_template_defn(template_defn, identifier_generator),
                                                                            optimization_name='normalize_template_defn()')

    [template_defn], needs_another_loop2 = apply_template_defn_optimization(template_defn,
                                                                            identifier_generator,
                                                                            optimization=lambda: perform_common_subexpression_normalization(template_defn, identifier_generator),
                                                                            optimization_name='perform_common_subexpression_normalization()')

    [template_defn], needs_another_loop3 = apply_template_defn_optimization(template_defn,
                                                                            identifier_generator,
                                                                            optimization=lambda: perform_constant_folding(template_defn,
                                                                                                                          identifier_generator,
                                                                                                                          inline_template_instantiations_with_multiple_references),
                                                                            optimization_name='perform_constant_folding()')

    [template_defn], needs_another_loop4 = apply_template_defn_optimization(template_defn,
                                                                            identifier_generator,
                                                                            optimization=lambda: perform_expression_simplification(template_defn),
                                                                            optimization_name='perform_expression_simplification()')

    return template_defn, any((needs_another_loop1, needs_another_loop2, needs_another_loop3, needs_another_loop4))

def perform_local_optimizations_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                                  identifier_generator: Iterator[str],
                                                  inline_template_instantiations_with_multiple_references: bool):
    toplevel_elems, needs_another_loop1 = apply_toplevel_elems_optimization(toplevel_elems,
                                                                            identifier_generator,
                                                                            optimization=lambda: normalize_toplevel_elems(toplevel_elems, identifier_generator),
                                                                            optimization_name='normalize_toplevel_elems()')

    toplevel_elems, needs_another_loop2 = apply_toplevel_elems_optimization(toplevel_elems,
                                                                            identifier_generator,
                                                                            optimization=lambda: perform_common_subexpression_normalization_on_toplevel_elems(toplevel_elems, identifier_generator),
                                                                            optimization_name='perform_common_subexpression_normalization_on_toplevel_elems()')

    toplevel_elems, needs_another_loop3 = apply_toplevel_elems_optimization(toplevel_elems,
                                                                            identifier_generator,
                                                                            optimization=lambda: perform_constant_folding_on_toplevel_elems(toplevel_elems,
                                                                                                                                            inline_template_instantiations_with_multiple_references),
                                                                            optimization_name='perform_constant_folding_on_toplevel_elems()')

    toplevel_elems, needs_another_loop4 = apply_toplevel_elems_optimization(toplevel_elems,
                                                                            identifier_generator,
                                                                            optimization=lambda: perform_expression_simplification_on_toplevel_elems(toplevel_elems),
                                                                            optimization_name='perform_expression_simplification_on_toplevel_elems()')

    return toplevel_elems, any((needs_another_loop1, needs_another_loop2, needs_another_loop3, needs_another_loop4))
