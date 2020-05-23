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
from typing import List, Dict, Set, Sequence, FrozenSet, Tuple

from _py2tmp.ir0 import ir, Transformation
from _py2tmp.ir0_optimization._recalculate_template_instantiation_can_trigger_static_asserts_info import elem_can_trigger_static_asserts
from _py2tmp.ir0_optimization._replace_var_with_expr import replace_var_with_expr_in_template_body_element
from _py2tmp.utils import ir_to_string


class ConstantFoldingTransformation(Transformation):
    def __init__(self, inline_template_instantiations_with_multiple_references: bool):
        super().__init__()
        self.inline_template_instantiations_with_multiple_references = inline_template_instantiations_with_multiple_references

    def transform_template_defn(self, template_defn: ir.TemplateDefn):
        self.writer.write(ir.TemplateDefn(args=template_defn.args,
                                          main_definition=self._transform_template_specialization(template_defn.main_definition,
                                                                                                  template_defn.result_element_names)
                                           if template_defn.main_definition is not None else None,
                                          specializations=tuple(self._transform_template_specialization(specialization,
                                                                                                        template_defn.result_element_names)
                                                                for specialization in template_defn.specializations),
                                          name=template_defn.name,
                                          description=template_defn.description,
                                          result_element_names=template_defn.result_element_names))

    def _transform_template_specialization(self,
                                           specialization: ir.TemplateSpecialization,
                                           result_element_names: FrozenSet[str]) -> ir.TemplateSpecialization:
        return ir.TemplateSpecialization(args=specialization.args,
                                         patterns=specialization.patterns,
                                         body=self.transform_template_body_elems(specialization.body,
                                                                                 result_element_names),
                                         is_metafunction=specialization.is_metafunction)

    def transform_template_body_elems(self,
                                      stmts: Sequence[ir.TemplateBodyElement],
                                      result_element_names: FrozenSet[str] = frozenset()) -> Tuple[ir.TemplateBodyElement]:
        stmts = list(stmts)

        # stmt[var_name_to_defining_stmt_index['x']] is the stmt that defines 'x'
        var_name_to_defining_stmt_index = {stmt.name: i
                                           for i, stmt in enumerate(stmts)
                                           if isinstance(stmt, (ir.ConstantDef, ir.Typedef))}

        # remaining_uses_of_var_by_stmt_index[i]['x'] is the number of remaining VarReferences referencing 'x' in
        # stmts[i].
        remaining_uses_of_var_by_stmt_index = [defaultdict(lambda: 0)
                                               for stmt in stmts]
        # remaining_uses_of_var['x'] = sum(uses['x'] for uses in remaining_uses_of_var_by_stmt_index), possibly +1 if
        # it's a result element (e.g. "type").
        remaining_uses_of_var = defaultdict(lambda: 0)
        # referenced_vars_by_stmt_index[i] are all the names of vars referenced in stmt[i]
        referenced_vars_by_stmt_index = [set() for stmt in stmts]
        # referenced_var_list_by_stmt_index[i] are all the names of vars referenced in stmt[i], in order (but only with
        # the first occurrence of each var)
        referenced_var_list_by_stmt_index: List[List[str]] = [[] for stmt in stmts]
        for i, stmt in enumerate(stmts):
            for identifier in stmt.referenced_identifiers:
                if identifier in var_name_to_defining_stmt_index:
                    remaining_uses_of_var[identifier] = remaining_uses_of_var[identifier] + 1
                    remaining_uses_of_var_by_stmt_index[i][identifier] = remaining_uses_of_var_by_stmt_index[i][identifier] + 1
                    if identifier not in referenced_vars_by_stmt_index[i]:
                        referenced_vars_by_stmt_index[i].add(identifier)
                        referenced_var_list_by_stmt_index[i].append(identifier)

        for var in result_element_names:
            if var in var_name_to_defining_stmt_index:
                remaining_uses_of_var[var] = remaining_uses_of_var[var] + 1

        # can_trigger_static_asserts_by_stmt_index[i] describes whether stmts[i] can trigger static asserts.
        can_trigger_static_asserts_by_stmt_index = [elem_can_trigger_static_asserts(stmt)
                                                    for stmt in stmts]
        was_inlined_by_stmt_index = [False for stmt in stmts]

        # Disregard "uses" of vars in useless stmts that will be eliminated.
        already_useless_stmt_indexes = [i
                                        for i, stmt in enumerate(stmts)
                                        if isinstance(stmt, (ir.ConstantDef, ir.Typedef))
                                        and remaining_uses_of_var[stmt.name] == 0
                                        and not can_trigger_static_asserts_by_stmt_index[i]]
        for i in already_useless_stmt_indexes:
            for indirectly_unused_var in referenced_var_list_by_stmt_index[i]:
                assert isinstance(indirectly_unused_var, str)
                self._decrease_remaining_uses(remaining_uses_of_var,
                                              remaining_uses_of_var_by_stmt_index,
                                              referenced_vars_by_stmt_index,
                                              var_name_to_defining_stmt_index,
                                              can_trigger_static_asserts_by_stmt_index,
                                              was_inlined_by_stmt_index,
                                              indirectly_unused_var,
                                              i,
                                              remaining_uses_of_var_by_stmt_index[i][indirectly_unused_var])


        # Start inlining (from the last statement to the first)
        for i, stmt in reversed(list(enumerate(stmts))):
            if (isinstance(stmt, (ir.ConstantDef, ir.Typedef))
                    and remaining_uses_of_var[stmt.name] == 0
                    and (not can_trigger_static_asserts_by_stmt_index[i]
                         or was_inlined_by_stmt_index[i])):
                # All references have been inlined and this statement can't trigger static asserts, no need to emit this
                # assignment.
                stmts[i] = None
                continue

            referenced_var_list = referenced_var_list_by_stmt_index[i]
            while referenced_var_list:
                var = referenced_var_list[-1]
                defining_stmt_index = var_name_to_defining_stmt_index[var]
                defining_stmt = stmts[defining_stmt_index]
                assert isinstance(defining_stmt, (ir.ConstantDef, ir.Typedef))

                can_inline_var = (not can_trigger_static_asserts_by_stmt_index[defining_stmt_index]
                                  or all(not can_trigger_static_asserts_by_stmt_index[crossed_stmt_index]
                                         # If all references have been inlined, we won't emit this assignment; so we
                                         # can disregard it in the crossing calculation.
                                         or (isinstance(stmts[crossed_stmt_index], (ir.ConstantDef, ir.Typedef))
                                             and remaining_uses_of_var[stmts[crossed_stmt_index].name] == 0
                                             and was_inlined_by_stmt_index[crossed_stmt_index])
                                         for crossed_stmt_index in range(defining_stmt_index + 1, i)))

                if self.inline_template_instantiations_with_multiple_references and isinstance(defining_stmt.expr, ir.TemplateInstantiation):
                    want_to_inline_var = True
                elif isinstance(defining_stmt.expr, ir.Literal):
                    want_to_inline_var = True
                elif isinstance(defining_stmt.expr, ir.AtomicTypeLiteral) and len(list(defining_stmt.expr.referenced_identifiers)) <= 1:
                    want_to_inline_var = True
                else:
                    want_to_inline_var = (remaining_uses_of_var[var] == 1)

                if not (can_inline_var and want_to_inline_var):
                    referenced_var_list.pop()
                    continue

                # Actually inline `var' into `stmt`.
                stmt = replace_var_with_expr_in_template_body_element(stmt, var, defining_stmt.expr)
                stmts[i] = stmt
                num_replacements = remaining_uses_of_var_by_stmt_index[i][var]

                for var2, num_uses_in_replacement_expr in remaining_uses_of_var_by_stmt_index[defining_stmt_index].items():
                    remaining_uses_of_var[var2] = remaining_uses_of_var[var2] + num_uses_in_replacement_expr * num_replacements
                    remaining_uses_of_var_by_stmt_index[i][var2] = remaining_uses_of_var_by_stmt_index[i][var2] + num_uses_in_replacement_expr * num_replacements

                if num_replacements > 0:
                    was_inlined_by_stmt_index[defining_stmt_index] = True
                    self._decrease_remaining_uses(remaining_uses_of_var,
                                                  remaining_uses_of_var_by_stmt_index,
                                                  referenced_vars_by_stmt_index,
                                                  var_name_to_defining_stmt_index,
                                                  can_trigger_static_asserts_by_stmt_index,
                                                  was_inlined_by_stmt_index,
                                                  var=var,
                                                  from_stmt_index=i,
                                                  by=num_replacements)

                referenced_var_list_by_stmt_index[i].pop()
                referenced_vars_by_stmt_index[i].remove(var)
                for var in referenced_var_list_by_stmt_index[defining_stmt_index]:
                    if var not in referenced_vars_by_stmt_index[i]:
                        referenced_vars_by_stmt_index[i].add(var)
                        referenced_var_list_by_stmt_index[i].append(var)

                can_trigger_static_asserts_by_stmt_index[i] = can_trigger_static_asserts_by_stmt_index[i] or elem_can_trigger_static_asserts(defining_stmt)

        return tuple(stmt
                     for stmt in stmts
                     if stmt is not None)

    def _decrease_remaining_uses(self,
                                 remaining_uses_of_var: Dict[str, int],
                                 remaining_uses_of_var_by_stmt_index: List[Dict[str, int]],
                                 referenced_vars_by_stmt_index: List[Set[str]],
                                 var_name_to_defining_stmt_index: Dict[str, int],
                                 can_trigger_static_asserts_by_stmt_index: List[bool],
                                 was_inlined_by_stmt_index: List[bool],
                                 var: str,
                                 from_stmt_index: int,
                                 by: int):
        assert by > 0
        remaining_uses_of_var[var] -= by
        remaining_uses_of_var_by_stmt_index[from_stmt_index][var] -= by

        stmt_index_defining_var = var_name_to_defining_stmt_index[var]

        if remaining_uses_of_var[var] == 0 and (
                not can_trigger_static_asserts_by_stmt_index[stmt_index_defining_var]
                or was_inlined_by_stmt_index[stmt_index_defining_var]):
            # The assignment to `var` will be eliminated. So we also need to decrement the uses of the variables referenced
            # in this assignment.
            for referenced_var in referenced_vars_by_stmt_index[stmt_index_defining_var]:
                self._decrease_remaining_uses(remaining_uses_of_var,
                                              remaining_uses_of_var_by_stmt_index,
                                              referenced_vars_by_stmt_index,
                                              var_name_to_defining_stmt_index,
                                              can_trigger_static_asserts_by_stmt_index,
                                              was_inlined_by_stmt_index,
                                              var=referenced_var,
                                              from_stmt_index=stmt_index_defining_var,
                                              by=remaining_uses_of_var_by_stmt_index[stmt_index_defining_var][referenced_var])
