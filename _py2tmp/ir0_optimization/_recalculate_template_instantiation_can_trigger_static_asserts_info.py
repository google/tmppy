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
from typing import Dict

import networkx as nx

from _py2tmp.ir0 import GLOBAL_LITERALS_BY_NAME, Transformation, Visitor, compute_template_dependency_graph, ir


def _is_global_literal_that_cannot_trigger_static_asserts(literal: ir.AtomicTypeLiteral):
    return literal.cpp_type in GLOBAL_LITERALS_BY_NAME and literal.cpp_type != 'CheckIfError'

class _CanTriggerStaticAsserts(Visitor):
    def __init__(self) -> None:
        self.can_trigger_static_asserts = False

    def visit_static_assert(self, static_assert: ir.StaticAssert):
        self.can_trigger_static_asserts = True

    def visit_template_instantiation(self, template_instantiation: ir.TemplateInstantiation):
        if (isinstance(template_instantiation.template_expr, ir.AtomicTypeLiteral)
                and _is_global_literal_that_cannot_trigger_static_asserts(template_instantiation.template_expr)):
            # Skip this instantiation, we'll set instantiation_might_trigger_static_asserts=False here later
            pass
        else:
            self.can_trigger_static_asserts |= template_instantiation.instantiation_might_trigger_static_asserts

    def visit_template_specialization(self, specialization: ir.TemplateSpecialization):
        # We don't recurse in inner templates, we assume that evaluating the template definition itself doesn't trigger
        # static asserts (even though the template might trigger assertions when instantiated).
        pass

def elem_can_trigger_static_asserts(stmt: ir.TemplateBodyElement):
    visitor = _CanTriggerStaticAsserts()
    visitor.visit_template_body_elems((stmt,))
    return visitor.can_trigger_static_asserts

def expr_can_trigger_static_asserts(expr: ir.Expr):
    visitor = _CanTriggerStaticAsserts()
    visitor.visit_expr(expr)
    return visitor.can_trigger_static_asserts

class _ApplyTemplateInstantiationCanTriggerStaticAssertsInfo(Transformation):
    def __init__(self, template_instantiation_can_trigger_static_asserts: Dict[str, bool]):
        super().__init__()
        self.template_instantiation_can_trigger_static_asserts = template_instantiation_can_trigger_static_asserts

    def transform_template_instantiation(self, template_instantiation: ir.TemplateInstantiation):
        if isinstance(template_instantiation.template_expr, ir.AtomicTypeLiteral):
            if _is_global_literal_that_cannot_trigger_static_asserts(template_instantiation.template_expr):
                instantiation_might_trigger_static_asserts = False
            else:
                instantiation_might_trigger_static_asserts = self.template_instantiation_can_trigger_static_asserts.get(template_instantiation.template_expr.cpp_type,
                                                                                                                        template_instantiation.instantiation_might_trigger_static_asserts)
            return ir.TemplateInstantiation(template_expr=self.transform_expr(template_instantiation.template_expr),
                                            args=self.transform_exprs(template_instantiation.args, template_instantiation),
                                            instantiation_might_trigger_static_asserts=instantiation_might_trigger_static_asserts)

        return super().transform_template_instantiation(template_instantiation)

def _apply_template_instantiation_can_trigger_static_asserts_info(header: ir.Header, template_instantiation_can_trigger_static_asserts: Dict[str, bool]):
    return _ApplyTemplateInstantiationCanTriggerStaticAssertsInfo(template_instantiation_can_trigger_static_asserts).transform_header(header)

class _TemplateDefnContainsStaticAssertStmt(Visitor):
    def __init__(self) -> None:
        self.found_static_assert_stmt = False

    def visit_static_assert(self, static_assert: ir.StaticAssert):
        self.found_static_assert_stmt = True

def _template_defn_contains_static_assert_stmt(template_defn: ir.TemplateDefn):
    visitor = _TemplateDefnContainsStaticAssertStmt()
    visitor.visit_template_defn(template_defn)
    return visitor.found_static_assert_stmt

def recalculate_template_instantiation_can_trigger_static_asserts_info(header: ir.Header):
    if not header.template_defns:
        return header

    template_defn_by_name = {template_defn.name: template_defn
                             for template_defn in header.template_defns}
    template_defn_dependency_graph = compute_template_dependency_graph(header.template_defns, template_defn_by_name)

    condensed_graph = nx.condensation(template_defn_dependency_graph)
    assert isinstance(condensed_graph, nx.DiGraph)

    template_defn_dependency_graph_transitive_closure = nx.transitive_closure(template_defn_dependency_graph)
    assert isinstance(template_defn_dependency_graph_transitive_closure, nx.DiGraph)

    # Determine which connected components can trigger static assert errors.
    condensed_node_can_trigger_static_asserts = defaultdict(lambda: False)
    for connected_component_index in reversed(list(nx.lexicographical_topological_sort(condensed_graph))):
        condensed_node = condensed_graph.nodes[connected_component_index]

        # If a template defn in this connected component can trigger a static assert, the whole component can.
        for template_defn_name in condensed_node['members']:
            if _template_defn_contains_static_assert_stmt(template_defn_by_name[template_defn_name]):
                condensed_node_can_trigger_static_asserts[connected_component_index] = True

        # If a template defn in this connected component references a template defn in a connected component that can
        # trigger static asserts, this connected component can also trigger them.
        for called_condensed_node_index in condensed_graph.successors(connected_component_index):
            if condensed_node_can_trigger_static_asserts[called_condensed_node_index]:
                condensed_node_can_trigger_static_asserts[connected_component_index] = True

    template_defn_can_trigger_static_asserts = dict()
    for connected_component_index in condensed_graph:
        for template_defn_name in condensed_graph.nodes[connected_component_index]['members']:
            template_defn_can_trigger_static_asserts[template_defn_name] = condensed_node_can_trigger_static_asserts[connected_component_index]

    return _apply_template_instantiation_can_trigger_static_asserts_info(header, template_defn_can_trigger_static_asserts)

