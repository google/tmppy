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

from typing import List, Union, Iterator, Callable, Tuple

from _py2tmp.ir0 import ir, ToplevelWriter, Transformation
from _py2tmp.ir0_optimization._common_subexpression_elimination import \
    CommonSubexpressionEliminationTransformation
from _py2tmp.ir0_optimization._constant_folding import ConstantFoldingTransformation
from _py2tmp.ir0_optimization._expression_simplification import ExpressionSimplificationTransformation
from _py2tmp.ir0_optimization._normalize_expressions import NormalizeExpressionsTransformation
from _py2tmp.ir0_optimization._optimization_execution import apply_elem_optimization, combine_optimizations, \
    describe_template_defns, describe_toplevel_elems
from _py2tmp.ir0_optimization.remove_no_op_stmts import RemoveNoOpStmtsTransformation


def perform_local_optimizations(elems: List,
                                identifier_generator: Iterator[str],
                                apply_transformation: Callable[[List, Transformation], Tuple[List, bool]],
                                describe_elems: Callable[[List], str],
                                inline_template_instantiations_with_multiple_references: bool):
    optimizations = [
        ('remove_no_op_stmts()', RemoveNoOpStmtsTransformation(identifier_generator)),
        ('normalize_template_defn()', NormalizeExpressionsTransformation(identifier_generator)),
        ('perform_common_subexpression_normalization()', CommonSubexpressionEliminationTransformation()),
        ('perform_constant_folding()', ConstantFoldingTransformation(inline_template_instantiations_with_multiple_references)),
        ('perform_expression_simplification()', ExpressionSimplificationTransformation()),
    ]

    optimizations = [lambda elems,
                            optimization_name=optimization_name,
                            transformation=transformation:
                     apply_elem_optimization(elems,
                                             lambda: apply_transformation(elems, transformation),
                                             describe_elems,
                                             optimization_name)
                     for optimization_name, transformation in optimizations]

    return combine_optimizations(elems, optimizations)

def _transform_template_defns(template_defns: List[ir.TemplateDefn],
                              transformation: Transformation):
    writer = ToplevelWriter(allow_toplevel_elems=False)
    with transformation.set_writer(writer):
        for template_defn in template_defns:
            transformation.transform_template_defn(template_defn)
    return writer.template_defns, False

def perform_local_optimizations_on_template_defn(template_defn: ir.TemplateDefn,
                                                 identifier_generator: Iterator[str],
                                                 inline_template_instantiations_with_multiple_references: bool):
    [template_defn], needs_another_loop = perform_local_optimizations([template_defn],
                                                                      identifier_generator,
                                                                      _transform_template_defns,
                                                                      lambda template_defns: describe_template_defns(template_defns, identifier_generator),
                                                                      inline_template_instantiations_with_multiple_references)
    return template_defn, needs_another_loop

def _transform_toplevel_elems(toplevel_elems: List[Union[ir.StaticAssert, ir.ConstantDef, ir.Typedef]],
                              transformation: Transformation):
    toplevel_elems = transformation.transform_template_body_elems(toplevel_elems)
    return toplevel_elems, False

def perform_local_optimizations_on_toplevel_elems(toplevel_elems: List[Union[
    ir.StaticAssert, ir.ConstantDef, ir.Typedef]],
                                                  identifier_generator: Iterator[str],
                                                  inline_template_instantiations_with_multiple_references: bool):
    return perform_local_optimizations(toplevel_elems,
                                       identifier_generator,
                                       _transform_toplevel_elems,
                                       lambda toplevel_elems: describe_toplevel_elems(toplevel_elems, identifier_generator),
                                       inline_template_instantiations_with_multiple_references)
