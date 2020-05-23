#!/usr/bin/env python3
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

from typing import Dict, Iterable

import networkx as nx

from _py2tmp.ir0 import ir


def compute_template_dependency_graph(template_defns: Iterable[ir.TemplateDefn], template_defn_by_name: Dict[str, ir.TemplateDefn]):
    template_dependency_graph = nx.DiGraph()
    for template_defn in template_defns:
        template_dependency_graph.add_node(template_defn.name)

        for identifier in template_defn.referenced_identifiers:
            if identifier in template_defn_by_name.keys():
                template_dependency_graph.add_edge(template_defn.name, identifier)
    return template_dependency_graph
