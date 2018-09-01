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
from collections import defaultdict

import itertools

from _py2tmp import ir0, utils, transform_ir0, ir0_to_cpp
import networkx as nx
from typing import List, Tuple, Union, Dict, Set, Iterator, Callable

def template_defn_to_cpp(template_defn: ir0.TemplateDefn, identifier_generator: Iterator[str]):
  writer = ir0_to_cpp.ToplevelWriter(identifier_generator)
  ir0_to_cpp.template_defn_to_cpp(template_defn, enclosing_function_defn_args=[], writer=writer)
  return utils.clang_format(''.join(writer.strings))

def template_body_elems_to_cpp(elems: List[ir0.TemplateBodyElement],
                               identifier_generator: Iterator[str]):
  result = ir0_to_cpp.header_to_cpp(ir0.Header(template_defns=[elem
                                                               for elem in elems
                                                               if isinstance(elem, ir0.TemplateDefn)],
                                               toplevel_content=[elem
                                                                 for elem in elems
                                                                 if not isinstance(elem, ir0.TemplateDefn)],
                                               public_names=set()),
                                    identifier_generator)
  return utils.clang_format(result)

def expr_to_cpp(expr: ir0.Expr):
  writer = ir0_to_cpp.ToplevelWriter(identifier_generator=iter([]))
  return ir0_to_cpp.expr_to_cpp(expr, enclosing_function_defn_args=[], writer=writer)

def compare_optimized_cpp_to_original(original_cpp: str, optimized_cpp: str, optimization_name: str, other_context: str = ''):
    if original_cpp != optimized_cpp:
        diff = ''.join(difflib.unified_diff(original_cpp.splitlines(True),
                                            optimized_cpp.splitlines(True),
                                            fromfile='before.h',
                                            tofile='after.h'))
        print('Original C++:\n' + original_cpp + '\n' + other_context
              + 'After ' + optimization_name + ':\n' + optimized_cpp + '\n'
              + 'Diff:\n' + diff + '\n')

def apply_optimization(template_defn: ir0.TemplateDefn,
                       identifier_generator: Iterator[str],
                       optimization: Callable[[], ir0.TemplateDefn],
                       optimization_name: str,
                       verbose: bool,
                       other_context: Callable[[], str] = lambda: ''):
    new_template_defn = optimization()

    if verbose:
        original_cpp = template_defn_to_cpp(template_defn, identifier_generator)
        optimized_cpp = template_defn_to_cpp(new_template_defn, identifier_generator)
        compare_optimized_cpp_to_original(original_cpp, optimized_cpp, optimization_name=optimization_name, other_context=other_context())

    return new_template_defn

def apply_toplevel_elems_optimization(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                      identifier_generator: Iterator[str],
                                      optimization: Callable[[], List[ir0.TemplateBodyElement]],
                                      optimization_name: str,
                                      verbose: bool,
                                      other_context: Callable[[], str] = lambda: ''):
  new_toplevel_elems = optimization()

  if verbose:
    original_cpp = template_body_elems_to_cpp(toplevel_elems, identifier_generator)
    optimized_cpp = template_body_elems_to_cpp(new_toplevel_elems, identifier_generator)
    compare_optimized_cpp_to_original(original_cpp, optimized_cpp, optimization_name=optimization_name, other_context=other_context())

  return new_toplevel_elems


class ExprSimplifyingTransformation(transform_ir0.Transformation):
    def transform_expr(self, expr: ir0.Expr, writer: transform_ir0.Writer, split_nontrivial_exprs=True) -> ir0.Expr:
        if split_nontrivial_exprs and not isinstance(expr, ir0.AtomicTypeLiteral):
            expr = super().transform_expr(expr, writer)
            var = writer.new_constant_or_typedef(expr)
            return var
        else:
            return expr

    def transform_pattern(self, expr: ir0.Expr, writer: transform_ir0.Writer):
        return expr

    def transform_constant_def(self, constant_def: ir0.ConstantDef, writer: transform_ir0.Writer):
        writer.write(ir0.ConstantDef(name=constant_def.name,
                                     expr=self.transform_expr(constant_def.expr, writer, split_nontrivial_exprs=False)))

    def transform_typedef(self, typedef: ir0.Typedef, writer: transform_ir0.Writer):
        writer.write(ir0.Typedef(name=typedef.name,
                                 expr=self.transform_expr(typedef.expr, writer, split_nontrivial_exprs=False)))

def normalize_template_defn(template_defn: ir0.TemplateDefn, identifier_generator: Iterator[str]):
  '''Converts template_defn to an equivalent TemplateDefn where all expressions contain 0 or 1 operations.

  Unlike other constants/typedefs, the exprs that initialize "result" and "error" will always have 0 operations.
  '''
  writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False)
  ExprSimplifyingTransformation().transform_template_defn(template_defn, writer)
  [new_template_defn] = writer.template_defns

  return new_template_defn

def normalize_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                             identifier_generator: Iterator[str]):
  '''Converts template_defn to an equivalent TemplateDefn where all expressions contain 0 or 1 operations.

  Unlike other constants/typedefs, the exprs that initialize "result" and "error" will always have 0 operations.
  '''
  writer = transform_ir0.ToplevelWriter(identifier_generator, allow_template_defns=False)
  for toplevel_elem in toplevel_elems:
    ExprSimplifyingTransformation().transform_toplevel_elem(toplevel_elem, writer)

  return writer.toplevel_elems

def create_var_to_var_assignment(lhs: str, rhs: str, type: ir0.ExprType):
  if type.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
    return ir0.ConstantDef(name=lhs,
                           expr=ir0.AtomicTypeLiteral.for_local(cpp_type=rhs,
                                                          type=type))
  elif type.kind in (ir0.ExprKind.TYPE, ir0.ExprKind.TEMPLATE):
    return ir0.Typedef(name=lhs,
                       expr=ir0.AtomicTypeLiteral.for_local(cpp_type=rhs,
                                                      type=type))
  else:
    # TODO: consider handling VARIADIC_TYPE too.
    raise NotImplementedError('Unexpected kind: %s' % str(type.kind))

class CommonSubexpressionEliminationTransformation(transform_ir0.Transformation):
    def transform_template_defn(self, template_defn: ir0.TemplateDefn, writer: transform_ir0.Writer):
      writer.write(ir0.TemplateDefn(args=template_defn.args,
                                    main_definition=self._transform_template_specialization(template_defn.main_definition, template_defn.result_element_names, writer) if template_defn.main_definition is not None else None,
                                    specializations=[self._transform_template_specialization(specialization, template_defn.result_element_names, writer) for specialization in template_defn.specializations],
                                    name=template_defn.name,
                                    description=template_defn.description,
                                    result_element_names=template_defn.result_element_names))

    def _transform_template_specialization(self,
                                           specialization: ir0.TemplateSpecialization,
                                           result_element_names: Tuple[str],
                                           writer: transform_ir0.Writer) -> ir0.TemplateSpecialization:
      toplevel_writer = writer.get_toplevel_writer()

      return ir0.TemplateSpecialization(args=specialization.args,
                                        patterns=specialization.patterns,
                                        body=self._transform_template_body_elems(specialization.body,
                                                                                 result_element_names,
                                                                                 specialization.args,
                                                                                 toplevel_writer))

    def _transform_template_body_elems(self,
                                       elems: List[ir0.TemplateBodyElement],
                                       result_element_names: Tuple[str],
                                       template_specialization_args: Tuple[ir0.TemplateArgDecl],
                                       toplevel_writer: transform_ir0.ToplevelWriter):

        name_by_expr = dict()  # type: Dict[ir0.Expr, str]
        replacements = dict()  # type: Dict[str, str]
        type_by_name = dict()  # type: Dict[str, ir0.ExprType]

        # First we process all args, so that we'll remove assignments of the form:
        # x1 = arg1
        for arg in template_specialization_args:
          name_by_expr[ir0.AtomicTypeLiteral.for_local(cpp_type=arg.name,
                                                 type=arg.type)] = arg.name
          type_by_name[arg.name] = arg.type

        result_elems = []
        for elem in elems:
            writer = transform_ir0.TemplateBodyWriter(toplevel_writer)
            NameReplacementTransformation(replacements).transform_template_body_elem(elem, writer)
            [elem] = writer.elems

            if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)) and elem.expr in name_by_expr:
                replacements[elem.name] = name_by_expr[elem.expr]
                type_by_name[elem.name] = elem.expr.type
            else:
                result_elems.append(elem)
                if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)):
                    name_by_expr[elem.expr] = elem.name

        additional_result_elems = []

        # This second pass will rename "result elements" back to the correct names if they were deduped.
        replacements2 = dict()
        arg_names = {arg.name for arg in template_specialization_args}
        for result_elem_name in result_element_names:
          if result_elem_name in replacements:
            replacement = replacements[result_elem_name]
            if replacement in replacements2:
              # We've already added a replacement in `replacements2`, so we need to emit an extra "assignment" assigning
              # a result element to another.
              additional_result_elems.append(create_var_to_var_assignment(lhs=result_elem_name,
                                                                          rhs=replacements2[replacement],
                                                                          type=type_by_name[replacement]))
            elif replacement in arg_names:
              # We've eliminated the assignment to the result var against the definition of an argument.
              # So we need to add it back.
              additional_result_elems.append(create_var_to_var_assignment(lhs=result_elem_name,
                                                                          rhs=replacement,
                                                                          type=type_by_name[replacement]))
            else:
              replacements2[replacement] = result_elem_name

        result_elems = NameReplacementTransformation(replacements2).transform_template_body_elems(result_elems,
                                                                                                  toplevel_writer)

        return result_elems + additional_result_elems

    def _transform_toplevel_elems(self,
                                  elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                  identifier_generator: Iterator[str]):

      name_by_expr = dict()  # type: Dict[ir0.Expr, str]
      replacements = dict()  # type: Dict[str, str]
      type_by_name = dict()  # type: Dict[str, ir0.ExprType]

      result_elems = []
      for elem in elems:
        writer = transform_ir0.ToplevelWriter(identifier_generator, allow_template_defns=False)
        NameReplacementTransformation(replacements).transform_toplevel_elem(elem, writer)
        [elem] = writer.toplevel_elems

        if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)) and elem.expr in name_by_expr:
          replacements[elem.name] = name_by_expr[elem.expr]
          type_by_name[elem.name] = elem.expr.type
        else:
          result_elems.append(elem)
          if isinstance(elem, (ir0.ConstantDef, ir0.Typedef)):
            name_by_expr[elem.expr] = elem.name

      return result_elems

def perform_common_subexpression_normalization(template_defn: ir0.TemplateDefn,
                                               identifier_generator: Iterator[str]):
  writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False)
  CommonSubexpressionEliminationTransformation().transform_template_defn(template_defn, writer)
  [template_defn] = writer.template_defns
  return template_defn

def perform_common_subexpression_normalization_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                                                 identifier_generator: Iterator[str]):
  return CommonSubexpressionEliminationTransformation()._transform_toplevel_elems(toplevel_elems, identifier_generator)

class ReplaceVarWithExprTransformation(transform_ir0.Transformation):
    def __init__(self, var: str, replacement_expr: ir0.Expr):
        self.var = var
        self.replacement_expr = replacement_expr

    def transform_type_literal(self, type_literal: ir0.AtomicTypeLiteral, writer: transform_ir0.Writer):
        if type_literal.cpp_type == self.var:
            return self.replacement_expr

        if self.var not in type_literal.get_referenced_identifiers():
            return type_literal

        if isinstance(self.replacement_expr, ir0.AtomicTypeLiteral):
            referenced_locals = []
            for referenced_local in type_literal.referenced_locals:
                if referenced_local.cpp_type != self.var:
                    referenced_locals.append(referenced_local)
            for referenced_local in self.replacement_expr.referenced_locals:
                referenced_locals.append(referenced_local)
            return ir0.AtomicTypeLiteral(cpp_type=utils.replace_identifiers(type_literal.cpp_type, {self.var: self.replacement_expr.cpp_type}),
                                   is_local=type_literal.is_local and self.replacement_expr.is_local,
                                   is_metafunction_that_may_return_error=type_literal.is_metafunction_that_may_return_error or self.replacement_expr.is_metafunction_that_may_return_error,
                                   referenced_locals=referenced_locals,
                                   type=type_literal.type)

        # TODO: implement this.
        raise NotImplementedError('The replacement of "%s" with "%s" in "%s" is not implemented yet.' % (self.var, expr_to_cpp(self.replacement_expr), type_literal.cpp_type))

def replace_var_with_expr(elem: ir0.TemplateBodyElement, var: str, expr: ir0.Expr) -> ir0.TemplateBodyElement:
    toplevel_writer = transform_ir0.ToplevelWriter(identifier_generator=[], allow_template_defns=False, allow_toplevel_elems=False)
    writer = transform_ir0.TemplateBodyWriter(toplevel_writer)
    ReplaceVarWithExprTransformation(var, expr).transform_template_body_elem(elem, writer)
    [elem] = writer.elems
    return elem

class CanTriggerStaticAsserts(transform_ir0.Transformation):
  def __init__(self):
    self.can_trigger_static_asserts = False

  def transform_static_assert(self, static_assert: ir0.StaticAssert, writer: transform_ir0.Writer):
    self.can_trigger_static_asserts = True
    return static_assert

  def transform_template_instantiation(self,
                                       template_instantiation: ir0.TemplateInstantiation,
                                       writer: transform_ir0.Writer):
    self.can_trigger_static_asserts |= template_instantiation.instantiation_might_trigger_static_asserts
    return template_instantiation

  def transform_template_specialization(self,
                                        specialization: ir0.TemplateSpecialization,
                                        writer: transform_ir0.Writer):
    # We don't recurse in inner templates, we assume that evaluating the template definition itself doesn't trigger
    # static asserts (even though the template might trigger assertions when instantiated).
    return specialization

def _elem_can_trigger_static_asserts(stmt: ir0.TemplateBodyElement):
    writer = transform_ir0.ToplevelWriter(identifier_generator=iter([]))
    transformation = CanTriggerStaticAsserts()
    transformation.transform_template_body_elems([stmt], writer)
    return transformation.can_trigger_static_asserts

class ConstantFoldingTransformation(transform_ir0.Transformation):
    def __init__(self, inline_template_instantiations_with_multiple_references: bool):
        super().__init__()
        self.inline_template_instantiations_with_multiple_references = inline_template_instantiations_with_multiple_references

    def transform_template_defn(self, template_defn: ir0.TemplateDefn, writer: transform_ir0.Writer):
      writer.write(ir0.TemplateDefn(args=template_defn.args,
                                    main_definition=self._transform_template_specialization(template_defn.main_definition,
                                                                                            template_defn.result_element_names)
                                        if template_defn.main_definition is not None else None,
                                    specializations=[self._transform_template_specialization(specialization,
                                                                                             template_defn.result_element_names)
                                                     for specialization in template_defn.specializations],
                                    name=template_defn.name,
                                    description=template_defn.description,
                                    result_element_names=template_defn.result_element_names))

    def _transform_template_specialization(self,
                                          specialization: ir0.TemplateSpecialization,
                                          result_element_names: Tuple[str]) -> ir0.TemplateSpecialization:
      return ir0.TemplateSpecialization(args=specialization.args,
                                        patterns=specialization.patterns,
                                        body=self._transform_template_body_elems(specialization.body,
                                                                                 result_element_names))

    def _transform_template_body_elems(self,
                                       stmts: Tuple[ir0.TemplateBodyElement],
                                       result_element_names: Tuple[str]):
        stmts = list(stmts)

        # stmt[var_name_to_defining_stmt_index['x']] is the stmt that defines 'x'
        var_name_to_defining_stmt_index = {stmt.name: i
                                           for i, stmt in enumerate(stmts)
                                           if isinstance(stmt, (ir0.ConstantDef, ir0.Typedef))}

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
        referenced_var_list_by_stmt_index = [[] for stmt in stmts]
        for i, stmt in enumerate(stmts):
            for identifier in stmt.get_referenced_identifiers():
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
        can_trigger_static_asserts_by_stmt_index = [_elem_can_trigger_static_asserts(stmt)
                                                    for stmt in stmts]
        was_inlined_by_stmt_index = [False for stmt in stmts]

        # Disregard "uses" of vars in useless stmts that will be eliminated.
        already_useless_stmt_indexes = [i
                                        for i, stmt in enumerate(stmts)
                                        if isinstance(stmt, (ir0.ConstantDef, ir0.Typedef))
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
            if (isinstance(stmt, (ir0.ConstantDef, ir0.Typedef))
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
                assert isinstance(defining_stmt, (ir0.ConstantDef, ir0.Typedef))

                can_inline_var = (not can_trigger_static_asserts_by_stmt_index[defining_stmt_index]
                                  or all(not can_trigger_static_asserts_by_stmt_index[crossed_stmt_index]
                                             # If all references have been inlined, we won't emit this assignment; so we
                                             # can disregard it in the crossing calculation.
                                             or (isinstance(stmts[crossed_stmt_index], (ir0.ConstantDef, ir0.Typedef))
                                                 and remaining_uses_of_var[stmts[crossed_stmt_index].name] == 0
                                                 and was_inlined_by_stmt_index[crossed_stmt_index])
                                         for crossed_stmt_index in range(defining_stmt_index + 1, i)))

                if self.inline_template_instantiations_with_multiple_references and isinstance(defining_stmt.expr, ir0.TemplateInstantiation):
                    want_to_inline_var = True
                elif isinstance(defining_stmt.expr, ir0.Literal):
                    want_to_inline_var = True
                elif isinstance(defining_stmt.expr, ir0.AtomicTypeLiteral) and len(list(defining_stmt.expr.get_referenced_identifiers())) <= 1:
                    want_to_inline_var = True
                else:
                    want_to_inline_var = (remaining_uses_of_var[var] == 1)

                if not (can_inline_var and want_to_inline_var):
                    referenced_var_list.pop()
                    continue

                # Actually inline `var' into `stmt`.
                try:
                  stmt = replace_var_with_expr(stmt, var, defining_stmt.expr)
                except NotImplementedError as e:
                  # TODO: remove this once ReplaceVarWithExprTransformation is implemented for the general case (see the
                  # TODO there).
                  referenced_var_list.pop()
                  continue

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

                can_trigger_static_asserts_by_stmt_index[i] = can_trigger_static_asserts_by_stmt_index[i] or _elem_can_trigger_static_asserts(defining_stmt)

        return [stmt
                for stmt in stmts
                if stmt is not None]

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

def perform_constant_folding(template_defn: ir0.TemplateDefn,
                             identifier_generator: Iterator[str],
                             inline_template_instantiations_with_multiple_references: bool):
  writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False)
  transformation = ConstantFoldingTransformation(inline_template_instantiations_with_multiple_references=inline_template_instantiations_with_multiple_references)
  transformation.transform_template_defn(template_defn, writer)
  [template_defn] = writer.template_defns
  return template_defn

def perform_constant_folding_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                               identifier_generator: Iterator[str],
                                               inline_template_instantiations_with_multiple_references: bool):
  transformation = ConstantFoldingTransformation(inline_template_instantiations_with_multiple_references=inline_template_instantiations_with_multiple_references)
  toplevel_elems = transformation._transform_template_body_elems(toplevel_elems, result_element_names=tuple())
  return toplevel_elems

def perform_local_optimizations_on_template_defn(template_defn: ir0.TemplateDefn,
                                                 identifier_generator: Iterator[str],
                                                 inline_template_instantiations_with_multiple_references: bool,
                                                 verbose: bool):
    template_defn = apply_optimization(template_defn,
                                       identifier_generator,
                                       optimization=lambda: normalize_template_defn(template_defn, identifier_generator),
                                       optimization_name='normalize_template_defn()',
                                       verbose=verbose)

    template_defn = apply_optimization(template_defn,
                                       identifier_generator,
                                       optimization=lambda: perform_common_subexpression_normalization(template_defn, identifier_generator),
                                       optimization_name='perform_common_subexpression_normalization()',
                                       verbose=verbose)

    template_defn = apply_optimization(template_defn,
                                       identifier_generator,
                                       optimization=lambda: perform_constant_folding(template_defn,
                                                                                     identifier_generator,
                                                                                     inline_template_instantiations_with_multiple_references),
                                       optimization_name='perform_constant_folding()',
                                       verbose=verbose)

    return template_defn

def perform_local_optimizations_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                                  identifier_generator: Iterator[str],
                                                  inline_template_instantiations_with_multiple_references: bool,
                                                  verbose: bool):
  toplevel_elems = apply_toplevel_elems_optimization(toplevel_elems,
                                                     identifier_generator,
                                                     optimization=lambda: normalize_toplevel_elems(toplevel_elems, identifier_generator),
                                                     optimization_name='normalize_toplevel_elems()',
                                                     verbose=verbose)

  toplevel_elems = apply_toplevel_elems_optimization(toplevel_elems,
                                                     identifier_generator,
                                                     optimization=lambda: perform_common_subexpression_normalization_on_toplevel_elems(toplevel_elems, identifier_generator),
                                                     optimization_name='perform_common_subexpression_normalization_on_toplevel_elems()',
                                                     verbose=verbose)

  toplevel_elems = apply_toplevel_elems_optimization(toplevel_elems,
                                                     identifier_generator,
                                                     optimization=lambda: perform_constant_folding_on_toplevel_elems(toplevel_elems,
                                                                                                                     identifier_generator,
                                                                                                                     inline_template_instantiations_with_multiple_references),
                                                     optimization_name='perform_constant_folding_on_toplevel_elems()',
                                                     verbose=verbose)

  return toplevel_elems

class NameReplacementTransformation(transform_ir0.Transformation):
    def __init__(self, replacements: Dict[str, str]):
        super().__init__()
        self.replacements = replacements

    def transform_type_literal(self, type_literal: ir0.AtomicTypeLiteral, writer: transform_ir0.Writer):
        return ir0.AtomicTypeLiteral(cpp_type=utils.replace_identifiers(type_literal.cpp_type, self.replacements),
                                     is_local=type_literal.is_local,
                                     is_metafunction_that_may_return_error=type_literal.is_metafunction_that_may_return_error,
                                     type=type_literal.type)

    def transform_constant_def(self, constant_def: ir0.ConstantDef, writer: transform_ir0.Writer):
        writer.write(ir0.ConstantDef(name=self._transform_name(constant_def.name),
                                     expr=self.transform_expr(constant_def.expr, writer)))

    def transform_typedef(self, typedef: ir0.Typedef, writer: transform_ir0.Writer):
        writer.write(ir0.Typedef(name=self._transform_name(typedef.name),
                                 expr=self.transform_expr(typedef.expr, writer)))

    def transform_template_defn(self, template_defn: ir0.TemplateDefn, writer: transform_ir0.Writer):
        writer.write(ir0.TemplateDefn(args=[self.transform_template_arg_decl(arg_decl) for arg_decl in template_defn.args],
                                      main_definition=self.transform_template_specialization(template_defn.main_definition, writer)
                                          if template_defn.main_definition is not None else None,
                                      specializations=[self.transform_template_specialization(specialization, writer)
                                                       for specialization in template_defn.specializations],
                                      name=self._transform_name(template_defn.name),
                                      description=template_defn.description,
                                      result_element_names=template_defn.result_element_names))

    def transform_template_arg_decl(self, arg_decl: ir0.TemplateArgDecl):
        return ir0.TemplateArgDecl(type=arg_decl.type,
                                   name=self._transform_name(arg_decl.name))

    def _transform_name(self, name: str):
        if name in self.replacements:
            return self.replacements[name]
        else:
            return name

class TemplateInstantiationInliningTransformation(transform_ir0.Transformation):
    def __init__(self, inlineable_templates_by_name: Dict[str, ir0.TemplateDefn]):
        super().__init__()
        self.inlineable_templates_by_name = inlineable_templates_by_name

    def transform_class_member_access(self, class_member_access: ir0.ClassMemberAccess, writer: transform_ir0.Writer):
        assert isinstance(writer, transform_ir0.TemplateBodyWriter)
        if (isinstance(class_member_access.expr, ir0.TemplateInstantiation)
                and isinstance(class_member_access.expr.template_expr, ir0.AtomicTypeLiteral)
                and class_member_access.expr.template_expr.cpp_type in self.inlineable_templates_by_name):
            template_instantiation = class_member_access.expr
            template_defn_to_inline = self.inlineable_templates_by_name[template_instantiation.template_expr.cpp_type]
            assert not template_defn_to_inline.specializations
            assert not template_defn_to_inline.main_definition.patterns

            new_var_name_by_old_var_name = dict()  # type: Dict[str, str]
            for arg_decl, arg_expr in zip(template_defn_to_inline.main_definition.args, template_instantiation.args):
                if arg_decl.name:
                    var = writer.new_constant_or_typedef(arg_expr)
                    new_var_name_by_old_var_name[arg_decl.name] = var.cpp_type

            for elem in template_defn_to_inline.main_definition.body:
                if isinstance(elem, ir0.TemplateDefn):
                    new_var_name_by_old_var_name[elem.name] = writer.new_id()
                elif isinstance(elem, ir0.ConstantDef):
                    new_var_name_by_old_var_name[elem.name] = writer.new_id()
                elif isinstance(elem, ir0.Typedef):
                    new_var_name_by_old_var_name[elem.name] = writer.new_id()
                elif isinstance(elem, ir0.StaticAssert):
                    pass
                else:
                    raise NotImplementedError('Unexpected elem: ' + elem.__class__.__name__)

            transformation = NameReplacementTransformation(new_var_name_by_old_var_name)
            for elem in template_defn_to_inline.main_definition.body:
                transformation.transform_template_body_elem(elem, writer)

            return ir0.AtomicTypeLiteral.for_local(cpp_type=new_var_name_by_old_var_name[class_member_access.member_name],
                                             type=class_member_access.type)
        else:
            return super().transform_class_member_access(class_member_access, writer)

def perform_template_inlining(template_defn: ir0.TemplateDefn,
                              inlineable_refs: Set[str],
                              template_defn_by_name: Dict[str, ir0.TemplateDefn],
                              identifier_generator: Iterator[str],
                              verbose: bool):
  template_defn = perform_local_optimizations_on_template_defn(template_defn,
                                                               identifier_generator,
                                                               inline_template_instantiations_with_multiple_references=True,
                                                               verbose=verbose)

  def perform_optimization():
    transformation = TemplateInstantiationInliningTransformation({template_name: template_defn_by_name[template_name]
                                                                  for template_name in inlineable_refs})

    writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False)
    transformation.transform_template_defn(template_defn, writer)
    [new_template_defn] = writer.template_defns
    return new_template_defn

  template_defn = apply_optimization(template_defn,
                                     identifier_generator,
                                     optimization=perform_optimization,
                                     optimization_name='TemplateInstantiationInliningTransformation',
                                     other_context=lambda: 'Inlined template(s):\n' + ''.join(template_defn_to_cpp(template_defn_by_name[template_name], identifier_generator)
                                                                                              for template_name in inlineable_refs) + '\n',
                                     verbose=verbose)

  return template_defn

def perform_template_inlining_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                                inlineable_refs: Set[str],
                                                template_defn_by_name: Dict[str, ir0.TemplateDefn],
                                                identifier_generator: Iterator[str],
                                                verbose: bool):
  toplevel_elems = perform_local_optimizations_on_toplevel_elems(toplevel_elems,
                                                                 identifier_generator,
                                                                 inline_template_instantiations_with_multiple_references=True,
                                                                 verbose=verbose)

  def perform_optimization():
    transformation = TemplateInstantiationInliningTransformation({template_name: template_defn_by_name[template_name]
                                                                  for template_name in inlineable_refs})

    writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False, allow_template_defns=False)
    elems = transformation.transform_template_body_elems(toplevel_elems, writer)

    return elems

  return apply_toplevel_elems_optimization(toplevel_elems,
                                           identifier_generator,
                                           optimization=perform_optimization,
                                           optimization_name='TemplateInstantiationInliningTransformation',
                                           other_context=lambda: 'Inlined template(s):\n' + ''.join(template_defn_to_cpp(template_defn_by_name[template_name], identifier_generator)
                                                                                                    for template_name in inlineable_refs) + '\n',
                                           verbose=verbose)

def optimize_header_first_pass(header: ir0.Header, identifier_generator: Iterator[str], verbose: bool):
    new_template_defns = {elem.name: elem
                          for elem in header.template_defns}

    template_dependency_graph = nx.DiGraph()
    for template_defn in header.template_defns:
        template_dependency_graph.add_node(template_defn.name)

        for identifier in template_defn.get_referenced_identifiers():
            if identifier in new_template_defns.keys():
                template_dependency_graph.add_edge(template_defn.name, identifier)

    condensed_graph = nx.condensation(template_dependency_graph)
    assert isinstance(condensed_graph, nx.DiGraph)

    template_dependency_graph_transitive_closure = nx.transitive_closure(template_dependency_graph)
    assert isinstance(template_dependency_graph_transitive_closure, nx.DiGraph)

    for connected_component_index in nx.topological_sort(condensed_graph, reverse=True):
        connected_component = condensed_graph.node[connected_component_index]['members']
        for node in sorted(connected_component, key=lambda node: new_template_defns[node].name):
            template_defn = new_template_defns[node]

            inlineable_refs = {other_node
                               for other_node in template_dependency_graph.successors(node)
                               if not template_dependency_graph_transitive_closure.has_edge(other_node, node)
                               and not new_template_defns[other_node].specializations}
            if inlineable_refs:
                template_defn = perform_template_inlining(template_defn,
                                                          inlineable_refs,
                                                          new_template_defns,
                                                          identifier_generator,
                                                          verbose=verbose)

            template_defn = perform_local_optimizations_on_template_defn(template_defn,
                                                                         identifier_generator,
                                                                         inline_template_instantiations_with_multiple_references=False,
                                                                         verbose=verbose)
            new_template_defns[node] = template_defn

    new_toplevel_content = header.toplevel_content
    inlineable_refs = {template_name
                       for template_name in new_template_defns.keys()
                       if not new_template_defns[template_name].specializations
                       # We won't inline templates that contain inner templates, because that would lead to
                       # TemplateDefn toplevel_content elements that may depend on non-TemplateDefn toplevel_content
                       # elements, so we would be unable to perform the usual optimizations that assume that no
                       # TemplateDefn elements don't depend on toplevel_content elements.
                       and not any(isinstance(elem, ir0.TemplateDefn)
                                   for elem in new_template_defns[template_name].main_definition.body)}
    if inlineable_refs:
      elems = perform_template_inlining_on_toplevel_elems(new_toplevel_content,
                                                          inlineable_refs,
                                                          new_template_defns,
                                                          identifier_generator,
                                                          verbose=verbose)
      additional_toplevel_template_defns = [elem
                                            for elem in elems
                                            if isinstance(elem, ir0.TemplateDefn)]
      new_toplevel_content = [elem
                              for elem in elems
                              if not isinstance(elem, ir0.TemplateDefn)]
    else:
      additional_toplevel_template_defns = []

    new_toplevel_content = perform_local_optimizations_on_toplevel_elems(new_toplevel_content,
                                                                         identifier_generator,
                                                                         inline_template_instantiations_with_multiple_references=False,
                                                                         verbose=verbose)

    return ir0.Header(template_defns=[new_template_defns[template_defn.name]
                                      for template_defn in header.template_defns] + additional_toplevel_template_defns,
                      toplevel_content=new_toplevel_content,
                      public_names=header.public_names)

def optimize_header_second_pass(header: ir0.Header):
  template_defns_by_name = {elem.name: elem
                            for elem in header.template_defns}

  template_dependency_graph = nx.DiGraph()
  for elem in itertools.chain(header.template_defns, header.toplevel_content):
    if isinstance(elem, ir0.TemplateDefn):
      elem_name = elem.name
    else:
      # We'll use a dummy name for non-template toplevel elems.
      elem_name = ''

    template_dependency_graph.add_node(elem_name)

    if elem_name in header.public_names:
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
                    public_names=header.public_names)

def optimize_header(header: ir0.Header, identifier_generator: Iterator[str], verbose: bool = False):
    header = optimize_header_first_pass(header, identifier_generator, verbose)
    header = optimize_header_second_pass(header)
    return header
