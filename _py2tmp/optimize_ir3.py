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
from _py2tmp import ir3, transform_ir3
import networkx as nx
from typing import List, Tuple, Union, Dict, Set, Iterator, Callable

class GetReferencedGlobalFunctionNamesTransformation(transform_ir3.Transformation):
    def __init__(self):
        self.referenced_global_function_names = set()

    def transform_var_reference(self, expr: ir3.VarReference):
        if expr.is_global_function:
          self.referenced_global_function_names.add(expr.name)
        return expr

def get_referenced_global_function_names(function_defn: ir3.FunctionDefn):
    transformation = GetReferencedGlobalFunctionNamesTransformation()
    transformation.transform_function_defn(function_defn)
    return transformation.referenced_global_function_names

class FunctionContainsRaiseStmt(transform_ir3.Transformation):
    def __init__(self):
        self.found_raise_stmt = False

    def transform_raise_stmt(self, stmt: ir3.RaiseStmt):
        self.found_raise_stmt = True
        return stmt

def function_contains_raise_stmt(function_defn: ir3.FunctionDefn):
    transformation = FunctionContainsRaiseStmt()
    transformation.transform_function_defn(function_defn)
    return transformation.found_raise_stmt

class ApplyFunctionCanThrowInfo(transform_ir3.Transformation):
    def __init__(self, function_can_throw: Dict[str, bool]):
        self.function_can_throw = function_can_throw

    def transform_var_reference(self, var: ir3.VarReference):
        is_function_that_may_throw = var.is_function_that_may_throw
        if is_function_that_may_throw and var.is_global_function and not self.function_can_throw[var.name]:
          is_function_that_may_throw = False
        return ir3.VarReference(type=var.type,
                                name=var.name,
                                is_global_function=var.is_global_function,
                                is_function_that_may_throw=is_function_that_may_throw)

    def transform_function_call(self, expr: ir3.FunctionCall):
      may_throw = expr.may_throw
      fun_expr = self.transform_expr(expr.fun_expr)
      if may_throw and isinstance(fun_expr, ir3.VarReference) and fun_expr.is_global_function and not fun_expr.is_function_that_may_throw:
        may_throw = False
      return ir3.FunctionCall(fun_expr=fun_expr,
                              args=[self.transform_expr(arg)
                                    for arg in expr.args],
                              may_throw=may_throw)

def apply_function_can_throw_info(module: ir3.Module, function_can_throw: Dict[str, bool]):
    return ApplyFunctionCanThrowInfo(function_can_throw).transform_module(module)

def recalculate_function_can_throw_info(module: ir3.Module):
  if not module.function_defns:
    return module

  function_dependency_graph = nx.DiGraph()

  function_defn_by_name = {function_defn.name: function_defn
                           for function_defn in module.function_defns}

  for function_defn in module.function_defns:
    function_dependency_graph.add_node(function_defn.name)

    for global_function_name in get_referenced_global_function_names(function_defn):
      if global_function_name in function_defn_by_name.keys():
        function_dependency_graph.add_edge(function_defn.name, global_function_name)

  condensed_graph = nx.condensation(function_dependency_graph)
  assert isinstance(condensed_graph, nx.DiGraph)

  function_dependency_graph_transitive_closure = nx.transitive_closure(function_dependency_graph)
  assert isinstance(function_dependency_graph_transitive_closure, nx.DiGraph)

  # Determine which connected components can throw.
  condensed_node_can_throw = defaultdict(lambda: False)
  for connected_component_index in nx.topological_sort(condensed_graph, reverse=True):
    condensed_node = condensed_graph.node[connected_component_index]

    # If a function in this connected component can throw, the whole component can throw.
    for function_name in condensed_node['members']:
      if function_contains_raise_stmt(function_defn_by_name[function_name]):
        condensed_node_can_throw[connected_component_index] = True

    # If a function in this connected component calls a function in a connected component that can throw, this
    # connected component can also throw.
    for called_condensed_node_index in condensed_graph.successors(connected_component_index):
      if condensed_node_can_throw[called_condensed_node_index]:
        condensed_node_can_throw[connected_component_index] = True

  function_can_throw = dict()
  for connected_component_index in condensed_graph:
    for function_name in condensed_graph.node[connected_component_index]['members']:
      function_can_throw[function_name] = condensed_node_can_throw[connected_component_index]

  return apply_function_can_throw_info(module, function_can_throw)

def optimize_module(module: ir3.Module):
    module = recalculate_function_can_throw_info(module)
    return module