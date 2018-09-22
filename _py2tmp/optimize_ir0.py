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
from _py2tmp import ir0, utils, transform_ir0, ir0_to_cpp, unify_ir0
import networkx as nx
from typing import List, Tuple, Union, Dict, Set, Iterator, Callable

DEFAULT_VERBOSE_SETTING = False

class ConfigurationKnobs:
    # If this is >=0, the number of optimization steps is capped to this value.
    max_num_optimization_steps = -1
    optimization_step_counter = 0
    reached_max_num_remaining_loops_counter = 0
    verbose = DEFAULT_VERBOSE_SETTING

GLOBAL_INLINEABLE_TEMPLATES_BY_NAME = {
    'std::is_same': ir0.TemplateDefn(name='std::is_same',
                                     description='',
                                     result_element_names=['value'],
                                     args=[ir0.TemplateArgDecl(name='T', type=ir0.TypeType()),
                                           ir0.TemplateArgDecl(name='U', type=ir0.TypeType())],
                                     main_definition=ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(name='T', type=ir0.TypeType()),
                                                                                      ir0.TemplateArgDecl(name='U', type=ir0.TypeType())],
                                                                                patterns=None,
                                                                                body=[ir0.ConstantDef(name='value',
                                                                                                      expr=ir0.Literal(False))],
                                                                                is_metafunction=True),
                                     specializations=[ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(name='T', type=ir0.TypeType())],
                                                                                 patterns=[ir0.AtomicTypeLiteral.for_local(cpp_type='T', type=ir0.TypeType()),
                                                                                           ir0.AtomicTypeLiteral.for_local(cpp_type='T', type=ir0.TypeType())],
                                                                                 body=[ir0.ConstantDef(name='value',
                                                                                                       expr=ir0.Literal(True))],
                                                                                 is_metafunction=True)]),
}

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
                       optimization: Callable[[], Tuple[ir0.TemplateDefn, bool]],
                       optimization_name: str,
                       other_context: Callable[[], str] = lambda: ''):
    if ConfigurationKnobs.max_num_optimization_steps == 0:
        return template_defn, False
    ConfigurationKnobs.optimization_step_counter += 1
    if ConfigurationKnobs.max_num_optimization_steps > 0:
        ConfigurationKnobs.max_num_optimization_steps -= 1

    new_template_defn, needs_another_loop = optimization()

    if ConfigurationKnobs.verbose:
        original_cpp = template_defn_to_cpp(template_defn, identifier_generator)
        optimized_cpp = template_defn_to_cpp(new_template_defn, identifier_generator)
        compare_optimized_cpp_to_original(original_cpp, optimized_cpp, optimization_name=optimization_name, other_context=other_context())

    return new_template_defn, needs_another_loop

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
        original_cpp = template_body_elems_to_cpp(toplevel_elems, identifier_generator)
        optimized_cpp = template_body_elems_to_cpp(new_toplevel_elems, identifier_generator)
        compare_optimized_cpp_to_original(original_cpp, optimized_cpp, optimization_name=optimization_name, other_context=other_context())

    return new_toplevel_elems, needs_another_loop

class NormalizeExpressionsTransformation(transform_ir0.Transformation):
    def __init__(self):
        super().__init__()

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
  NormalizeExpressionsTransformation().transform_template_defn(template_defn, writer)
  [new_template_defn] = writer.template_defns

  return new_template_defn, False

def normalize_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                             identifier_generator: Iterator[str]):
  '''Converts template_defn to an equivalent TemplateDefn where all expressions contain 0 or 1 operations.

  Unlike other constants/typedefs, the exprs that initialize "result" and "error" will always have 0 operations.
  '''
  writer = transform_ir0.ToplevelWriter(identifier_generator, allow_template_defns=False)
  for toplevel_elem in toplevel_elems:
    transformation = NormalizeExpressionsTransformation()
    transformation.transform_toplevel_elem(toplevel_elem, writer)

  return writer.toplevel_elems, False

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
    def __init__(self):
        super().__init__()

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
                                                                                 toplevel_writer,
                                                                                 specialization.is_metafunction),
                                        is_metafunction=specialization.is_metafunction)

    def _transform_template_body_elems(self,
                                       elems: List[ir0.TemplateBodyElement],
                                       result_element_names: Tuple[str],
                                       template_specialization_args: Tuple[ir0.TemplateArgDecl],
                                       toplevel_writer: transform_ir0.ToplevelWriter,
                                       is_metafunction: bool):
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
            transform_ir0.NameReplacementTransformation(replacements).transform_template_body_elem(elem, writer)
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
            elif replacement in result_element_names:
              # We've eliminated the assignment to the result var against another result var, so we need to emit an
              # extra "assignment" assigning a result element to another.

              if replacement in type_by_name:
                  type = type_by_name[replacement]
              elif result_elem_name in type_by_name:
                  type = type_by_name[result_elem_name]
              else:
                  raise NotImplementedError('Unable to determine type. This should never happen.')

              additional_result_elems.append(create_var_to_var_assignment(lhs=result_elem_name,
                                                                          rhs=replacement,
                                                                          type=type))
            elif replacement in arg_names:
              # We've eliminated the assignment to the result var against the definition of an argument.
              # So we need to add it back.
              additional_result_elems.append(create_var_to_var_assignment(lhs=result_elem_name,
                                                                          rhs=replacement,
                                                                          type=type_by_name[replacement]))
            else:
              replacements2[replacement] = result_elem_name

        result_elems = transform_ir0.NameReplacementTransformation(replacements2).transform_template_body_elems(result_elems,
                                                                                                                toplevel_writer)

        result_elems = result_elems + additional_result_elems

        if is_metafunction and result_elems:
            assert (any(isinstance(elem, ir0.Typedef) and elem.name == 'type'
                        for elem in result_elems)
                    or any(isinstance(elem, ir0.ConstantDef) and elem.name == 'value'
                           for elem in result_elems)), 'type_by_name == %s\nreplacements2 == %s\nbody was:\n%s' % (
                type_by_name,
                replacements2,
                '\n'.join(utils.ir_to_string(elem)
                          for elem in result_elems))
        return result_elems

    def _transform_toplevel_elems(self,
                                  elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                  identifier_generator: Iterator[str]):

      name_by_expr = dict()  # type: Dict[ir0.Expr, str]
      replacements = dict()  # type: Dict[str, str]
      type_by_name = dict()  # type: Dict[str, ir0.ExprType]

      result_elems = []
      for elem in elems:
        writer = transform_ir0.ToplevelWriter(identifier_generator, allow_template_defns=False)
        transform_ir0.NameReplacementTransformation(replacements).transform_toplevel_elem(elem, writer)
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
  transformation = CommonSubexpressionEliminationTransformation()
  transformation.transform_template_defn(template_defn, writer)
  [template_defn] = writer.template_defns
  return template_defn, False

def perform_common_subexpression_normalization_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                                                 identifier_generator: Iterator[str]):
  transformation = CommonSubexpressionEliminationTransformation()
  return transformation._transform_toplevel_elems(toplevel_elems, identifier_generator), False

class VariadicVarReplacementNotPossibleException(Exception):
    pass

class ReplaceVarWithExprTransformation(transform_ir0.Transformation):
    def __init__(self, replacement_expr_by_var: Dict[str, Union[ir0.Expr, List[ir0.Expr]]], variadic_vars_with_expansion_in_progress: Set[str] = set()):
        super().__init__()
        self.replacement_expr_by_var = replacement_expr_by_var
        self.variadic_vars_with_expansion_in_progress = variadic_vars_with_expansion_in_progress

    def transform_variadic_type_expansion(self, expr: ir0.VariadicTypeExpansion, writer: transform_ir0.Writer):
        variadic_vars_to_expand = {var.cpp_type
                                   for var in expr.get_free_vars()
                                   if var.type == ir0.VariadicType() and var.cpp_type not in self.variadic_vars_with_expansion_in_progress}
        previous_variadic_vars_with_expansion_in_progress = self.variadic_vars_with_expansion_in_progress
        self.variadic_vars_with_expansion_in_progress = previous_variadic_vars_with_expansion_in_progress.union(variadic_vars_to_expand)

        values_by_variadic_var_to_expand = {var: self.replacement_expr_by_var[var]
                                            for var in variadic_vars_to_expand
                                            if var in self.replacement_expr_by_var}

        transformed_exprs = []
        if values_by_variadic_var_to_expand:
            self._check_variadic_var_replacement(values_by_variadic_var_to_expand)

            num_values_to_expand = len(next(iter(values_by_variadic_var_to_expand.values())))
            assert all(len(values) == num_values_to_expand
                       for values in values_by_variadic_var_to_expand.values())
            for i in range(0, num_values_to_expand):
                child_replacement_expr_by_var = self.replacement_expr_by_var.copy()
                for var, values in values_by_variadic_var_to_expand.items():
                    child_replacement_expr_by_var[var] = values[i]
                child_transformation = ReplaceVarWithExprTransformation(child_replacement_expr_by_var)
                transformed_expr = child_transformation.transform_expr(expr.expr, writer)
                for expr1 in (transformed_expr if isinstance(transformed_expr, list) else [transformed_expr]):
                    transformed_exprs.append(expr1)
        else:
            transformed_expr = self.transform_expr(expr.expr, writer)
            for expr in (transformed_expr if isinstance(transformed_expr, list) else [transformed_expr]):
                transformed_exprs.append(expr)

        self.variadic_vars_with_expansion_in_progress = previous_variadic_vars_with_expansion_in_progress

        results = []
        for expr in transformed_exprs:
            for var in expr.get_free_vars():
                if var.type == ir0.VariadicType() and not var.cpp_type in self.variadic_vars_with_expansion_in_progress:
                    results.append(ir0.VariadicTypeExpansion(expr))
                    break
            else:
                results.append(expr)

        return results

    def transform_type_literal(self, type_literal: ir0.AtomicTypeLiteral, writer: transform_ir0.Writer):
        if type_literal.cpp_type in self.replacement_expr_by_var:
            result = self.replacement_expr_by_var[type_literal.cpp_type]
            if isinstance(result, list):
                [result] = result
            return result
        return type_literal

    def transform_exprs(self, exprs: List[ir0.Expr], parent_element_type, writer):
        if parent_element_type in (ir0.TemplateInstantiation, ir0.FunctionTypeExpr):
            results = []
            for expr in exprs:
                expr_or_expr_list = self.transform_expr(expr, writer)
                for expr in (expr_or_expr_list if isinstance(expr_or_expr_list, list) else [expr_or_expr_list]):
                    results.append(expr)
            return results
        else:
            return super().transform_exprs(exprs, parent_element_type, writer)

    def _compute_variadic_pattern(self, values: Union[ir0.Expr, List[ir0.Expr]], strict: bool):
        if not isinstance(values, list):
            values = [values]
        for value in values:
            if isinstance(value, ir0.VariadicTypeExpansion) and isinstance(value.expr, ir0.AtomicTypeLiteral):
                if strict:
                    yield value.expr.cpp_type
                else:
                    # We just check that there's a corresponding variadic type expansion, but not necessarily for the
                    # same var.
                    yield 1
            else:
                yield None

    def _check_variadic_var_replacement(self,
                                        values_by_variadic_var_to_expand: Dict[str, Union[ir0.Expr, List[ir0.Expr]]]):
        num_values_to_expand_in_first_replacement = len(next(iter(values_by_variadic_var_to_expand.values())))
        if not all(len(values) == num_values_to_expand_in_first_replacement
                   for values in values_by_variadic_var_to_expand.values()):
            # We can't perform the replacement syntactically, even if it might make sense semantically.
            # E.g. we can't replace Ts={Xs...}, Us={Ys..., float} in "std::pair<Ts, Us>...".
            raise VariadicVarReplacementNotPossibleException('We can\'t perform the replacement syntactically, even if it might make sense semantically. '
                                                             'num_values_to_expand_in_first_replacement = %s, values_by_variadic_var_to_expand = %s' % (
                num_values_to_expand_in_first_replacement, str(values_by_variadic_var_to_expand)))

        values_lists = [list(values) for values in values_by_variadic_var_to_expand.values()]
        while values_lists[0]:
            # If no front items are variadic expansions, we can disregard those and check the rest.
            for values in values_lists:
                value = values[0]
                if isinstance(value, ir0.VariadicTypeExpansion) and isinstance(value, ir0.AtomicTypeLiteral):
                    break
            else:
                values_lists = [values[1:] for values in values_lists]
                continue

            # And same for the last ones.
            for values in values_lists:
                value = values[-1]
                if isinstance(value, ir0.VariadicTypeExpansion) and isinstance(value, ir0.AtomicTypeLiteral):
                    break
            else:
                values_lists = [values[:-1] for values in values_lists]
                continue

            # If all value lists start with the same variadic type expansion, we can disregard that.
            if isinstance(values_lists[0][0], ir0.VariadicTypeExpansion) and isinstance(values_lists[0][0].expr, ir0.AtomicTypeLiteral):
                var = values_lists[0][0].expr.cpp_type
                for values in values_lists:
                    value = values[0]
                    if not (isinstance(value, ir0.VariadicTypeExpansion) and isinstance(value.expr, ir0.AtomicTypeLiteral) and value.expr.cpp_type == var):
                        break
                else:
                    values_lists = [values[1:] for values in values_lists]
                    continue

            # And same at the end.
            if isinstance(values_lists[0][-1], ir0.VariadicTypeExpansion) and isinstance(values_lists[0][-1].expr, ir0.AtomicTypeLiteral):
                var = values_lists[0][-1].expr.cpp_type
                for values in values_lists:
                    value = values[-1]
                    if not (isinstance(value, ir0.VariadicTypeExpansion) and isinstance(value.expr, ir0.AtomicTypeLiteral) and value.expr.cpp_type == var):
                        break
                else:
                    values_lists = [values[:-1] for values in values_lists]
                    continue

            # We have excluded all begin/end values that we can.
            break

        for values in values_lists:
            num_expansions = sum(1
                                 for value in values
                                 if isinstance(value, ir0.VariadicTypeExpansion))
            if num_expansions > 1:
                # We can perform the replacement syntactically, but it doesn't make sense semantically.
                # E.g. when replacing Ts={int, Xs...}, Us={Ys..., float} in "std::pair<Ts, Us>..." we can't output
                # "std::pair<int, Ys>..., std::pair<Xs, float>...", it would be wrong.
                raise VariadicVarReplacementNotPossibleException('We can perform the replacement syntactically, but it doesn\'t make sense semantically')

def replace_var_with_expr(elem: ir0.TemplateBodyElement, var: str, expr: ir0.Expr) -> ir0.TemplateBodyElement:
    toplevel_writer = transform_ir0.ToplevelWriter(identifier_generator=[], allow_template_defns=False, allow_toplevel_elems=False)
    writer = transform_ir0.TemplateBodyWriter(toplevel_writer)
    ReplaceVarWithExprTransformation({var: expr}).transform_template_body_elem(elem, writer)
    [elem] = writer.elems
    return elem

class CanTriggerStaticAsserts(transform_ir0.Transformation):
  def __init__(self):
      super().__init__(generates_transformed_ir=False)
      self.can_trigger_static_asserts = False

  def transform_static_assert(self, static_assert: ir0.StaticAssert, writer: transform_ir0.Writer):
      self.can_trigger_static_asserts = True

  def transform_template_instantiation(self,
                                       template_instantiation: ir0.TemplateInstantiation,
                                       writer: transform_ir0.Writer):
      self.can_trigger_static_asserts |= template_instantiation.instantiation_might_trigger_static_asserts

  def transform_template_specialization(self,
                                        specialization: ir0.TemplateSpecialization,
                                        writer: transform_ir0.Writer):
      # We don't recurse in inner templates, we assume that evaluating the template definition itself doesn't trigger
      # static asserts (even though the template might trigger assertions when instantiated).
      return

class ApplyTemplateInstantiationCanTriggerStaticAssertsInfo(transform_ir0.Transformation):
    def __init__(self, template_instantiation_can_trigger_static_asserts: Dict[str, bool]):
        super().__init__()
        self.template_instantiation_can_trigger_static_asserts = template_instantiation_can_trigger_static_asserts

    def transform_template_instantiation(self, template_instantiation: ir0.TemplateInstantiation, writer: transform_ir0.Writer):
        if isinstance(template_instantiation.template_expr, ir0.AtomicTypeLiteral):
            instantiation_might_trigger_static_asserts = self.template_instantiation_can_trigger_static_asserts.get(template_instantiation.template_expr.cpp_type,
                                                                                                                    template_instantiation.instantiation_might_trigger_static_asserts)
            return ir0.TemplateInstantiation(template_expr=self.transform_expr(template_instantiation.template_expr, writer),
                                             args=self.transform_exprs(template_instantiation.args, ir0.TemplateInstantiation, writer),
                                             instantiation_might_trigger_static_asserts=instantiation_might_trigger_static_asserts)

        return super().transform_template_instantiation(template_instantiation, writer)

def apply_template_instantiation_can_trigger_static_asserts_info(header: ir0.Header, template_instantiation_can_trigger_static_asserts: Dict[str, bool]):
    return ApplyTemplateInstantiationCanTriggerStaticAssertsInfo(template_instantiation_can_trigger_static_asserts).transform_header(header, identifier_generator=iter([]))

class TemplateDefnContainsStaticAssertStmt(transform_ir0.Transformation):
    def __init__(self):
        super().__init__(generates_transformed_ir=False)
        self.found_static_assert_stmt = False

    def transform_static_assert(self, static_assert: ir0.StaticAssert, writer: transform_ir0.Writer):
        self.found_static_assert_stmt = True

def template_defn_contains_static_assert_stmt(template_defn: ir0.TemplateDefn):
    transformation = TemplateDefnContainsStaticAssertStmt()
    transformation.transform_template_defn(template_defn, transform_ir0.ToplevelWriter(identifier_generator=iter([])))
    return transformation.found_static_assert_stmt

def recalculate_template_instantiation_can_trigger_static_asserts_info(header: ir0.Header):
    if not header.template_defns:
        return header

    template_defn_by_name = {template_defn.name: template_defn
                             for template_defn in header.template_defns}
    template_defn_dependency_graph = compute_template_dependency_graph(header, template_defn_by_name)

    condensed_graph = nx.condensation(template_defn_dependency_graph)
    assert isinstance(condensed_graph, nx.DiGraph)

    template_defn_dependency_graph_transitive_closure = nx.transitive_closure(template_defn_dependency_graph)
    assert isinstance(template_defn_dependency_graph_transitive_closure, nx.DiGraph)

    # Determine which connected components can trigger static assert errors.
    condensed_node_can_trigger_static_asserts = defaultdict(lambda: False)
    for connected_component_index in reversed(list(nx.topological_sort(condensed_graph))):
        condensed_node = condensed_graph.node[connected_component_index]

        # If a template defn in this connected component can trigger a static assert, the whole component can.
        for template_defn_name in condensed_node['members']:
            if template_defn_contains_static_assert_stmt(template_defn_by_name[template_defn_name]):
                condensed_node_can_trigger_static_asserts[connected_component_index] = True

        # If a template defn in this connected component references a template defn in a connected component that can
        # trigger static asserts, this connected component can also trigger them.
        for called_condensed_node_index in condensed_graph.successors(connected_component_index):
            if condensed_node_can_trigger_static_asserts[called_condensed_node_index]:
                condensed_node_can_trigger_static_asserts[connected_component_index] = True

    template_defn_can_trigger_static_asserts = dict()
    for connected_component_index in condensed_graph:
        for template_defn_name in condensed_graph.node[connected_component_index]['members']:
            template_defn_can_trigger_static_asserts[template_defn_name] = condensed_node_can_trigger_static_asserts[connected_component_index]

    return apply_template_instantiation_can_trigger_static_asserts_info(header, template_defn_can_trigger_static_asserts)

def _elem_can_trigger_static_asserts(stmt: ir0.TemplateBodyElement):
    writer = transform_ir0.ToplevelWriter(identifier_generator=iter([]))
    transformation = CanTriggerStaticAsserts()
    transformation.transform_template_body_elems([stmt], writer)
    return transformation.can_trigger_static_asserts

def _expr_can_trigger_static_asserts(expr: ir0.Expr):
    writer = transform_ir0.ToplevelWriter(identifier_generator=iter([]))
    transformation = CanTriggerStaticAsserts()
    transformation.transform_expr(expr, writer)
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
                                                                                 result_element_names),
                                        is_metafunction=specialization.is_metafunction)

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
                stmt = replace_var_with_expr(stmt, var, defining_stmt.expr)
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

class ExpressionSimplificationTransformation(transform_ir0.Transformation):
    def __init__(self):
        super().__init__()

    def transform_not_expr(self, not_expr: ir0.NotExpr, writer: transform_ir0.Writer) -> ir0.Expr:
        expr = self.transform_expr(not_expr.expr, writer)
        # not True => False
        # not False => True
        if isinstance(expr, ir0.Literal):
            assert isinstance(expr.value, bool)
            return ir0.Literal(not expr.value)
        # not not x => x
        if isinstance(expr, ir0.NotExpr):
            return expr.expr
        return ir0.NotExpr(expr)

    def transform_unary_minus_expr(self, unary_minus: ir0.UnaryMinusExpr, writer: transform_ir0.Writer) -> ir0.Expr:
        expr = self.transform_expr(unary_minus.expr, writer)
        # -(3) => -3
        if isinstance(expr, ir0.Literal):
            assert isinstance(expr.value, int)
            return ir0.Literal(-expr.value)
        # -(x - y) => y - x
        if isinstance(expr, ir0.Int64BinaryOpExpr) and expr.op == '-':
            return ir0.Int64BinaryOpExpr(lhs=expr.rhs, rhs=expr.lhs, op='-')
        return ir0.UnaryMinusExpr(expr)

    def transform_int64_binary_op_expr(self, binary_op: ir0.Int64BinaryOpExpr, writer: transform_ir0.Writer) -> ir0.Expr:
        lhs = binary_op.lhs
        rhs = binary_op.rhs
        op = binary_op.op
        # (x - y) => (x + -y)
        # This pushes down the minus, so that e.g. (x - (-y)) => (x + y).
        if op == '-':
            rhs = ir0.UnaryMinusExpr(rhs)
            op = '+'

        lhs = self.transform_expr(lhs, writer)
        rhs = self.transform_expr(rhs, writer)

        if op == '+' and isinstance(rhs, ir0.UnaryMinusExpr):
            # We could not push down the minus, so switch back to a subtraction.
            op = '-'
            rhs = rhs.expr

        if op == '+':
            # 3 + 5 => 8
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value + rhs.value)
            # 0 + x => x
            if isinstance(lhs, ir0.Literal) and lhs.value == 0:
                return rhs
            # x + 0 => x
            if isinstance(rhs, ir0.Literal) and rhs.value == 0:
                return lhs

        if op == '-':
            # 8 - 5 => 3
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value - rhs.value)
            # 0 - x => -x
            if isinstance(lhs, ir0.Literal) and lhs.value == 0:
                return ir0.UnaryMinusExpr(rhs)
            # x - 0 => x
            if isinstance(rhs, ir0.Literal) and rhs.value == 0:
                return lhs

        if op == '*':
            # 3 * 5 => 15
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value * rhs.value)
            # 0 * x => 0
            if isinstance(lhs, ir0.Literal) and lhs.value == 0:
                return ir0.Literal(0)
            # x * 0 => 0
            if isinstance(rhs, ir0.Literal) and rhs.value == 0:
                return ir0.Literal(0)
            # 1 * x => x
            if isinstance(lhs, ir0.Literal) and lhs.value == 1:
                return rhs
            # x * 1 => x
            if isinstance(rhs, ir0.Literal) and rhs.value == 1:
                return lhs

        if op == '//':
            # 16 // 3 => 5
            if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
                return ir0.Literal(lhs.value // rhs.value)
            # x / 1 => x
            if isinstance(rhs, ir0.Literal) and rhs.value == 1:
                return lhs

        return ir0.Int64BinaryOpExpr(lhs, rhs, op)

    def transform_comparison_expr(self, comparison: ir0.ComparisonExpr, writer: transform_ir0.Writer) -> ir0.Expr:
        lhs = comparison.lhs
        rhs = comparison.rhs
        op = comparison.op

        lhs = self.transform_expr(lhs, writer)
        rhs = self.transform_expr(rhs, writer)

        if isinstance(lhs, ir0.Literal) and isinstance(rhs, ir0.Literal):
            if op == '==':
                return ir0.Literal(lhs.value == rhs.value)
            if op == '!=':
                return ir0.Literal(lhs.value != rhs.value)
            if op == '<':
                return ir0.Literal(lhs.value < rhs.value)
            if op == '<=':
                return ir0.Literal(lhs.value <= rhs.value)
            if op == '>':
                return ir0.Literal(lhs.value > rhs.value)
            if op == '>=':
                return ir0.Literal(lhs.value >= rhs.value)

        if op in ('==', '!=') and self._is_syntactically_equal(lhs, rhs) and not _expr_can_trigger_static_asserts(lhs):
            return {
                '==': ir0.Literal(True),
                '!=': ir0.Literal(False),
            }[op]

        return ir0.ComparisonExpr(lhs, rhs, op)

    def transform_static_assert(self, static_assert: ir0.StaticAssert, writer: transform_ir0.Writer):
        expr = self.transform_expr(static_assert.expr, writer)

        if isinstance(expr, ir0.Literal) and expr.value is True:
            return

        writer.write(ir0.StaticAssert(expr=expr,
                                      message=static_assert.message))

    def _is_syntactically_equal(self, lhs, rhs):
        if not lhs.is_same_expr_excluding_subexpressions(rhs):
            return False
        lhs_exprs = lhs.get_direct_subelements()
        rhs_exprs = rhs.get_direct_subelements()
        if len(lhs_exprs) != len(rhs_exprs):
            return False
        return all(self._is_syntactically_equal(lhs_expr, rhs_expr)
                   for lhs_expr, rhs_expr in zip(lhs_exprs, rhs_exprs))

def perform_constant_folding(template_defn: ir0.TemplateDefn,
                             identifier_generator: Iterator[str],
                             inline_template_instantiations_with_multiple_references: bool):
  writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False)
  transformation = ConstantFoldingTransformation(inline_template_instantiations_with_multiple_references=inline_template_instantiations_with_multiple_references)
  transformation.transform_template_defn(template_defn, writer)
  [template_defn] = writer.template_defns
  return template_defn, False

def perform_constant_folding_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                               inline_template_instantiations_with_multiple_references: bool):
  transformation = ConstantFoldingTransformation(inline_template_instantiations_with_multiple_references=inline_template_instantiations_with_multiple_references)
  toplevel_elems = transformation._transform_template_body_elems(toplevel_elems, result_element_names=tuple())
  return toplevel_elems, False

def perform_expression_simplification(template_defn: ir0.TemplateDefn):
  writer = transform_ir0.ToplevelWriter(iter([]), allow_toplevel_elems=False)
  transformation = ExpressionSimplificationTransformation()
  transformation.transform_template_defn(template_defn, writer)
  [template_defn] = writer.template_defns
  return template_defn, False

def perform_expression_simplification_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]]):
  transformation = ExpressionSimplificationTransformation()
  writer = transform_ir0.ToplevelWriter(iter([]), allow_toplevel_elems=False)
  toplevel_elems = transformation.transform_template_body_elems(toplevel_elems, writer)
  assert not writer.template_defns
  assert not writer.toplevel_elems
  return toplevel_elems, False

def perform_local_optimizations_on_template_defn(template_defn: ir0.TemplateDefn,
                                                 identifier_generator: Iterator[str],
                                                 inline_template_instantiations_with_multiple_references: bool):
    template_defn, needs_another_loop1 = apply_optimization(template_defn,
                                                            identifier_generator,
                                                            optimization=lambda: normalize_template_defn(template_defn, identifier_generator),
                                                            optimization_name='normalize_template_defn()')

    template_defn, needs_another_loop2 = apply_optimization(template_defn,
                                                            identifier_generator,
                                                            optimization=lambda: perform_common_subexpression_normalization(template_defn, identifier_generator),
                                                            optimization_name='perform_common_subexpression_normalization()')

    template_defn, needs_another_loop3 = apply_optimization(template_defn,
                                                            identifier_generator,
                                                            optimization=lambda: perform_constant_folding(template_defn,
                                                                                                          identifier_generator,
                                                                                                          inline_template_instantiations_with_multiple_references),
                                                            optimization_name='perform_constant_folding()')

    template_defn, needs_another_loop4 = apply_optimization(template_defn,
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

class TemplateInstantiationInliningTransformation(transform_ir0.Transformation):
    def __init__(self, inlineable_templates_by_name: Dict[str, ir0.TemplateDefn]):
        super().__init__()
        self.needs_another_loop = False
        self.inlineable_templates_by_name = inlineable_templates_by_name.copy()
        self.parent_template_specialization_definitions = dict()

    def transform_template_specialization(self, specialization: ir0.TemplateSpecialization, writer: transform_ir0.Writer):
        old_parent_template_specialization_definitions = self.parent_template_specialization_definitions
        self.parent_template_specialization_definitions = dict()
        result = super().transform_template_specialization(specialization, writer)
        self.parent_template_specialization_definitions = old_parent_template_specialization_definitions
        return result

    def transform_constant_def(self, constant_def: ir0.ConstantDef, writer: transform_ir0.Writer):
        super().transform_constant_def(constant_def, writer)

        if isinstance(writer, transform_ir0.ToplevelWriter):
            result = writer.toplevel_elems[-1]
        else:
            assert isinstance(writer, transform_ir0.TemplateBodyWriter)
            result = writer.elems[-1]

        assert isinstance(result, ir0.ConstantDef)
        self.parent_template_specialization_definitions[result.name] = result.expr

    def transform_typedef(self, typedef: ir0.Typedef, writer: transform_ir0.Writer):
        super().transform_typedef(typedef, writer)

        if isinstance(writer, transform_ir0.ToplevelWriter):
            result = writer.toplevel_elems[-1]
        else:
            assert isinstance(writer, transform_ir0.TemplateBodyWriter)
            result = writer.elems[-1]

        assert isinstance(result, ir0.Typedef)
        self.parent_template_specialization_definitions[result.name] = result.expr

    def transform_class_member_access(self, class_member_access: ir0.ClassMemberAccess, writer: transform_ir0.Writer):
        assert isinstance(writer, transform_ir0.TemplateBodyWriter)
        class_member_access = super().transform_class_member_access(class_member_access, writer)
        if (isinstance(class_member_access.expr, ir0.TemplateInstantiation)
                and isinstance(class_member_access.expr.template_expr, ir0.AtomicTypeLiteral)
                and class_member_access.expr.template_expr.cpp_type in self.inlineable_templates_by_name):
            template_instantiation = class_member_access.expr
            template_defn_to_inline = self.inlineable_templates_by_name[template_instantiation.template_expr.cpp_type]
        elif (isinstance(class_member_access.expr, ir0.TemplateInstantiation)
                and isinstance(class_member_access.expr.template_expr, ir0.AtomicTypeLiteral)
                and class_member_access.expr.template_expr.cpp_type in GLOBAL_INLINEABLE_TEMPLATES_BY_NAME):
            template_instantiation = class_member_access.expr
            template_defn_to_inline = GLOBAL_INLINEABLE_TEMPLATES_BY_NAME[template_instantiation.template_expr.cpp_type]
        else:
            return class_member_access

        toplevel_writer = writer.get_toplevel_writer()
        unification = unify_ir0.unify_template_instantiation_with_definition(template_instantiation,
                                                                             self.parent_template_specialization_definitions,
                                                                             template_defn_to_inline,
                                                                             toplevel_writer.identifier_generator,
                                                                             verbose=ConfigurationKnobs.verbose)
        if not unification:
            return class_member_access

        specialization, value_by_pattern_variable = unification
        assert len(value_by_pattern_variable) == len(specialization.args)

        value_by_pattern_variable = {(var.cpp_type if isinstance(var, ir0.AtomicTypeLiteral) else var.expr.cpp_type): expr
                                     for var, expr in value_by_pattern_variable}

        tmp_writer = transform_ir0.ToplevelWriter(toplevel_writer.identifier_generator,
                                                  allow_toplevel_elems=False,
                                                  allow_template_defns=toplevel_writer.allow_template_defns)
        transformation = ReplaceVarWithExprTransformation(value_by_pattern_variable)
        try:
            body = transformation.transform_template_body_elems(specialization.body, tmp_writer)
        except VariadicVarReplacementNotPossibleException as e:
            [message] = e.args
            # We thought we could perform the inlining but we actually can't.
            print('VariadicVarReplacementNotPossibleException raised for template %s (reason: %s), we can\'t inline that.' % (template_instantiation.template_expr.cpp_type, message))
            return class_member_access

        new_var_name_by_old_var_name = dict()
        for elem in body:
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

        transformation = transform_ir0.NameReplacementTransformation(new_var_name_by_old_var_name)
        for elem in body:
            transformation.transform_template_body_elem(elem, writer)

        self.needs_another_loop = True
        if ConfigurationKnobs.verbose:
            print('Inlining template defn: %s' % template_defn_to_inline.name)

        assert class_member_access.member_name in new_var_name_by_old_var_name, 'member_name="%s" not found. Names defined in body of template %s: %s; Toplevel elems: %s' % (
            class_member_access.member_name,
            template_defn_to_inline.name,
            ', '.join(new_var_name_by_old_var_name.keys()),
            ', '.join(ir0_to_cpp.toplevel_elem_to_cpp_simple(elem) for elem in body))
        return ir0.AtomicTypeLiteral.for_local(cpp_type=new_var_name_by_old_var_name[class_member_access.member_name],
                                               type=class_member_access.type)

def perform_template_inlining(template_defn: ir0.TemplateDefn,
                              inlineable_refs: Set[str],
                              template_defn_by_name: Dict[str, ir0.TemplateDefn],
                              identifier_generator: Iterator[str]):
  template_defn, needs_another_loop1 = perform_local_optimizations_on_template_defn(template_defn,
                                                                                    identifier_generator,
                                                                                    inline_template_instantiations_with_multiple_references=True)

  def perform_optimization():
    transformation = TemplateInstantiationInliningTransformation({template_name: template_defn_by_name[template_name]
                                                                  for template_name in inlineable_refs})

    writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False)
    transformation.transform_template_defn(template_defn, writer)
    [new_template_defn] = writer.template_defns
    return new_template_defn, transformation.needs_another_loop

  template_defn, needs_another_loop2 = apply_optimization(template_defn,
                                                          identifier_generator,
                                                          optimization=perform_optimization,
                                                          optimization_name='TemplateInstantiationInliningTransformation',
                                                          other_context=lambda: 'Potentially inlineable template(s):\n' + ''.join(template_defn_to_cpp(template_defn_by_name[template_name], identifier_generator)
                                                                                                                                  for template_name in inlineable_refs) + '\n')

  return template_defn, needs_another_loop1 or needs_another_loop2

def perform_template_inlining_on_toplevel_elems(toplevel_elems: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]],
                                                inlineable_refs: Set[str],
                                                template_defn_by_name: Dict[str, ir0.TemplateDefn],
                                                identifier_generator: Iterator[str]):
  toplevel_elems, needs_another_loop1 = perform_local_optimizations_on_toplevel_elems(toplevel_elems,
                                                                                      identifier_generator,
                                                                                      inline_template_instantiations_with_multiple_references=True)

  def perform_optimization():
    transformation = TemplateInstantiationInliningTransformation({template_name: template_defn_by_name[template_name]
                                                                  for template_name in inlineable_refs})

    writer = transform_ir0.ToplevelWriter(identifier_generator, allow_toplevel_elems=False, allow_template_defns=False)
    elems = transformation.transform_template_body_elems(toplevel_elems, writer)

    return elems, transformation.needs_another_loop

  toplevel_elems, needs_another_loop2 = apply_toplevel_elems_optimization(toplevel_elems,
                                                                          identifier_generator,
                                                                          optimization=perform_optimization,
                                                                          optimization_name='TemplateInstantiationInliningTransformation',
                                                                          other_context=lambda: 'Potentially inlineable template(s):\n' + ''.join(
                                                                              template_defn_to_cpp(template_defn_by_name[template_name],
                                                                                                   identifier_generator)
                                                                              for template_name in inlineable_refs) + '\n')
  return toplevel_elems, needs_another_loop1 or needs_another_loop2

def compute_template_dependency_graph(header: ir0.Header, template_defn_by_name: Dict[str, ir0.TemplateDefn]):
    template_dependency_graph = nx.DiGraph()
    for template_defn in header.template_defns:
        template_dependency_graph.add_node(template_defn.name)

        for identifier in template_defn.get_referenced_identifiers():
            if identifier in template_defn_by_name.keys():
                template_dependency_graph.add_edge(template_defn.name, identifier)
    return template_dependency_graph

def calculate_max_num_optimization_loops(num_templates_in_connected_component):
    # This is just a heuristic. We want to make enough loops to fully optimize the code but without looping forever
    # when there are mutually-recursive functions.
    return num_templates_in_connected_component * 10 + 10

def optimize_header_first_pass(header: ir0.Header, identifier_generator: Iterator[str]):
    new_template_defns = {elem.name: elem
                          for elem in header.template_defns}

    template_dependency_graph = compute_template_dependency_graph(header, new_template_defns)

    template_dependency_graph_transitive_closure = nx.transitive_closure(template_dependency_graph)
    assert isinstance(template_dependency_graph_transitive_closure, nx.DiGraph)

    for connected_component in reversed(list(utils.compute_condensation_in_topological_order(template_dependency_graph))):
        needs_another_loop = True
        max_num_remaining_loops = calculate_max_num_optimization_loops(len(connected_component))
        while needs_another_loop and max_num_remaining_loops:
            needs_another_loop = False
            max_num_remaining_loops -= 1
            for template_name in sorted(connected_component, key=lambda node: new_template_defns[node].name):
                template_defn = new_template_defns[template_name]
    
                inlineable_refs = {other_node
                                   for other_node in template_dependency_graph.successors(template_name)
                                   if not template_dependency_graph_transitive_closure.has_edge(other_node, template_name)}
                template_defn, needs_another_loop1 = perform_template_inlining(template_defn,
                                                                               inlineable_refs,
                                                                               new_template_defns,
                                                                               identifier_generator)
                if needs_another_loop1:
                    needs_another_loop = True

                template_defn, needs_another_loop1 = perform_local_optimizations_on_template_defn(template_defn,
                                                                                                  identifier_generator,
                                                                                                  inline_template_instantiations_with_multiple_references=False)
                if needs_another_loop1:
                    needs_another_loop = True
                
                new_template_defns[template_name] = template_defn

        if not max_num_remaining_loops:
            ConfigurationKnobs.reached_max_num_remaining_loops_counter += 1


    new_toplevel_content = header.toplevel_content


    inlineable_refs = set()
    for template_name in new_template_defns.keys():
        template_defn = new_template_defns[template_name]
        # We won't inline templates that contain inner templates, because that would lead to
        #  TemplateDefn toplevel_content elements that may depend on non-TemplateDefn toplevel_content
        #  elements, so we would be unable to perform the usual optimizations that assume that no
        #  TemplateDefn elements don't depend on toplevel_content elements.
        if all(not isinstance(elem, ir0.TemplateDefn)
               for specialization in itertools.chain((template_defn.main_definition,) if template_defn.main_definition else tuple(),
                                                     template_defn.specializations if template_defn.specializations else tuple())
               for elem in specialization.body):
            inlineable_refs.add(template_name)

    needs_another_loop = True
    max_num_remaining_loops = calculate_max_num_optimization_loops(len(new_toplevel_content))
    while needs_another_loop and max_num_remaining_loops:
        needs_another_loop = False
        max_num_remaining_loops -= 1
    
        elems, needs_another_loop1 = perform_template_inlining_on_toplevel_elems(new_toplevel_content,
                                                                                 inlineable_refs,
                                                                                 new_template_defns,
                                                                                 identifier_generator)
        if needs_another_loop1:
            needs_another_loop = True

        additional_toplevel_template_defns = [elem
                                              for elem in elems
                                              if isinstance(elem, ir0.TemplateDefn)]
        new_toplevel_content = [elem
                                for elem in elems
                                if not isinstance(elem, ir0.TemplateDefn)]

        new_toplevel_content, needs_another_loop1 = perform_local_optimizations_on_toplevel_elems(new_toplevel_content,
                                                                                                  identifier_generator,
                                                                                                  inline_template_instantiations_with_multiple_references=False)
        if needs_another_loop1:
            needs_another_loop = True

    if not max_num_remaining_loops:
        ConfigurationKnobs.reached_max_num_remaining_loops_counter += 1

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

def optimize_header(header: ir0.Header, identifier_generator: Iterator[str]):
    header = recalculate_template_instantiation_can_trigger_static_asserts_info(header)
    header = optimize_header_first_pass(header, identifier_generator)
    header = optimize_header_second_pass(header)
    return header
