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
import importlib.util as importlib_util
import itertools
from functools import lru_cache
from typing import List, Optional, Sequence

import typed_ast.ast3 as ast

from _py2tmp import ir0, ir0_builtin_literals
from _py2tmp.ir0_optimization import configuration_knobs


def _type_arg_decl(name: str):
    return ir0.TemplateArgDecl(expr_type=ir0.TypeType(), name=name, is_variadic=False)

def _bool_arg_decl(name: str):
    return ir0.TemplateArgDecl(expr_type=ir0.BoolType(), name=name, is_variadic=False)

def _int64_arg_decl(name: str):
    return ir0.TemplateArgDecl(expr_type=ir0.Int64Type(), name=name, is_variadic=False)

def _variadic_type_arg_decl(name: str):
    return ir0.TemplateArgDecl(expr_type=ir0.TypeType(), name=name, is_variadic=True)

def _variadic_bool_arg_decl(name: str):
    return ir0.TemplateArgDecl(expr_type=ir0.BoolType(), name=name, is_variadic=True)

def _variadic_int64_arg_decl(name: str):
    return ir0.TemplateArgDecl(expr_type=ir0.Int64Type(), name=name, is_variadic=True)

def _template_template_arg_decl(name: str, *args: ir0.TemplateArgType):
    return ir0.TemplateArgDecl(expr_type=ir0.TemplateType(args), name=name, is_variadic=False)

def _type_arg_type():
    return ir0.TemplateArgType(expr_type=ir0.TypeType(), is_variadic=False)

def _bool_arg_type():
    return ir0.TemplateArgType(expr_type=ir0.BoolType(), is_variadic=False)

def _int64_arg_type():
    return ir0.TemplateArgType(expr_type=ir0.Int64Type(), is_variadic=False)

def _variadic_type_arg_type():
    return ir0.TemplateArgType(expr_type=ir0.TypeType(), is_variadic=True)

def _variadic_bool_arg_type():
    return ir0.TemplateArgType(expr_type=ir0.BoolType(), is_variadic=True)

def _variadic_int64_arg_type():
    return ir0.TemplateArgType(expr_type=ir0.Int64Type(), is_variadic=True)

def _template_template_arg_type(*args: ir0.TemplateArgType):
    return ir0.TemplateArgType(expr_type=ir0.TemplateType(args), is_variadic=False)

def _metafunction_call(template_expr: ir0.Expr,
                       args: Sequence[ir0.Expr],
                       instantiation_might_trigger_static_asserts: bool,
                       member_name: str,
                       member_type: ir0.ExprType):
    return ir0.ClassMemberAccess(class_type_expr=ir0.TemplateInstantiation(template_expr=template_expr,
                                                                           args=args,
                                                                           instantiation_might_trigger_static_asserts=instantiation_might_trigger_static_asserts),
                                 member_name=member_name,
                                 member_type=member_type)

def _local_metafunction_call(template_var_name: str,
                             arg_types: Sequence[ir0.TemplateArgType],
                             args: Sequence[ir0.Expr],
                             instantiation_might_trigger_static_asserts: bool,
                             member_name: str,
                             member_type: ir0.ExprType):
    return _metafunction_call(template_expr=ir0.AtomicTypeLiteral.for_local(template_var_name, ir0.TemplateType(args=arg_types), is_variadic=False),
                              args=args,
                              instantiation_might_trigger_static_asserts=instantiation_might_trigger_static_asserts,
                              member_name=member_name,
                              member_type=member_type)

def _bool_list_of(*args: ir0.Expr):
    return ir0.TemplateInstantiation(template_expr=ir0_builtin_literals.GlobalLiterals.BOOL_LIST,
                                     args=args,
                                     instantiation_might_trigger_static_asserts=False)

def _int_list_of(*args: ir0.Expr):
    return ir0.TemplateInstantiation(template_expr=ir0_builtin_literals.GlobalLiterals.INT_LIST,
                                     args=args,
                                     instantiation_might_trigger_static_asserts=False)

def _type_list_of(*args: ir0.Expr):
    return ir0.TemplateInstantiation(template_expr=ir0_builtin_literals.GlobalLiterals.LIST,
                                     args=args,
                                     instantiation_might_trigger_static_asserts=False)

def _get_first_error(*args: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.GET_FIRST_ERROR,
                              args=args,
                              instantiation_might_trigger_static_asserts=False,
                              member_name='type',
                              member_type=ir0.TypeType())

def _is_same(lhs: ir0.Expr, rhs: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.STD_IS_SAME,
                              args=[lhs, rhs],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='value',
                              member_type=ir0.BoolType())

def _int64_list_sum(l: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.INT64_LIST_SUM,
                              args=[l],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='value',
                              member_type=ir0.Int64Type())

def _add_to_bool_set_helper(all_false_list_if_not_present: ir0.Expr, all_false_list: ir0.Expr, s: ir0.Expr, b: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.ADD_TO_BOOL_SET_HELPER,
                              args=[all_false_list_if_not_present,
                                    all_false_list,
                                    s,
                                    b],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='type',
                              member_type=ir0.TypeType())

def _add_to_int64_set_helper(all_false_list_if_not_present: ir0.Expr, all_false_list: ir0.Expr, s: ir0.Expr, n: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.ADD_TO_INT64_SET_HELPER,
                              args=[all_false_list_if_not_present,
                                    all_false_list,
                                    s,
                                    n],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='type',
                              member_type=ir0.TypeType())

def _add_to_type_set_helper(all_false_list_if_not_present: ir0.Expr, all_false_list: ir0.Expr, s: ir0.Expr, t: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.ADD_TO_TYPE_SET_HELPER,
                              args=[all_false_list_if_not_present,
                                    all_false_list,
                                    s,
                                    t],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='type',
                              member_type=ir0.TypeType())

def _fold_bools_to_type(acc: ir0.Expr, f: ir0.Expr, bs: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.FOLD_BOOLS_TO_TYPE,
                              args=[acc, f, bs],
                              instantiation_might_trigger_static_asserts=True,
                              member_name='type',
                              member_type=ir0.TypeType())

def _fold_int64s_to_type(acc: ir0.Expr, f: ir0.Expr, ns: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.FOLD_INT64S_TO_TYPE,
                              args=[acc, f, ns],
                              instantiation_might_trigger_static_asserts=True,
                              member_name='type',
                              member_type=ir0.TypeType())

def _fold_types_to_type(acc: ir0.Expr, f: ir0.Expr, ts: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.FOLD_TYPES_TO_TYPE,
                              args=[acc, f, ts],
                              instantiation_might_trigger_static_asserts=True,
                              member_name='type',
                              member_type=ir0.TypeType())

def _always_true_from_type(t: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.ALWAYS_TRUE_FROM_TYPE,
                              args=[t],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='value',
                              member_type=ir0.BoolType())

def _always_false_from_type(t: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.ALWAYS_FALSE_FROM_TYPE,
                              args=[t],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='value',
                              member_type=ir0.BoolType())

def _is_in_bool_set(b: ir0.Expr, s: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.IS_IN_BOOL_LIST,
                              args=[b, s],
                              instantiation_might_trigger_static_asserts=False,
                              member_type=ir0.BoolType(),
                              member_name='value')

def _is_in_int64_set(n: ir0.Expr, s: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.IS_IN_INT64_LIST,
                              args=[n, s],
                              instantiation_might_trigger_static_asserts=False,
                              member_type=ir0.BoolType(),
                              member_name='value')

def _is_in_type_set(t: ir0.Expr, s: ir0.Expr):
    return _metafunction_call(template_expr=ir0_builtin_literals.GlobalLiterals.IS_IN_TYPE_LIST,
                              args=[t, s],
                              instantiation_might_trigger_static_asserts=False,
                              member_type=ir0.BoolType(),
                              member_name='value')

def _local_bool(cpp_type: str):
    return ir0.AtomicTypeLiteral.for_local(cpp_type, ir0.BoolType(), is_variadic=False)

def _local_int(cpp_type: str):
    return ir0.AtomicTypeLiteral.for_local(cpp_type, ir0.Int64Type(), is_variadic=False)

def _local_type(cpp_type: str):
    return ir0.AtomicTypeLiteral.for_local(cpp_type, ir0.TypeType(), is_variadic=False)

def _local_variadic_bool(cpp_type: str):
    return ir0.AtomicTypeLiteral.for_local(cpp_type, ir0.BoolType(), is_variadic=True)

def _local_variadic_int(cpp_type: str):
    return ir0.AtomicTypeLiteral.for_local(cpp_type, ir0.Int64Type(), is_variadic=True)

def _local_variadic_type(cpp_type: str):
    return ir0.AtomicTypeLiteral.for_local(cpp_type, ir0.TypeType(), is_variadic=True)

def _specialization(args: List[ir0.TemplateArgDecl],
                    body_prefix: List[ir0.TemplateBodyElement] = [],
                    patterns: Optional[List[ir0.Expr]] = None,
                    value_expr: Optional[ir0.Expr] = None,
                    type_expr: Optional[ir0.Expr] = None,
                    error_expr: Optional[ir0.Expr] = None):
    assert (value_expr is None) != (type_expr is None)
    if error_expr:
        body_prefix = body_prefix + [ir0.Typedef(name='error', expr=error_expr)]
    if value_expr:
        if value_expr.expr_type.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
            stmt = ir0.ConstantDef(name='value', expr=value_expr)
        else:
            stmt = ir0.Typedef(name='value', expr=value_expr)
        return ir0.TemplateSpecialization(args=args,
                                          patterns=patterns,
                                          body=body_prefix + [stmt],
                                          is_metafunction=True)
    if type_expr:
        return ir0.TemplateSpecialization(args=args,
                                          patterns=patterns,
                                          body=body_prefix + [ir0.Typedef(name='type',
                                                                          expr=type_expr)],
                                          is_metafunction=True)

class _BuiltinTemplatesHolder:
    initialized = False
    initializing = False
    BUILTIN_TEMPLATES: List[ir0.TemplateDefn] = []
    identifier_generator = None
    split_template_name_by_old_name_and_result_element_name = dict()

def _define_template(main_definition: Optional[ir0.TemplateSpecialization],
                     specializations: Sequence[ir0.TemplateSpecialization],
                     name: str,
                     result_element_name: str,
                     args: Optional[Sequence[ir0.TemplateArgDecl]] = None,
                     has_error: bool = False):
    _BuiltinTemplatesHolder.BUILTIN_TEMPLATES.append(ir0.TemplateDefn(main_definition=main_definition,
                                                                      specializations=specializations,
                                                                      name=name,
                                                                      description='',
                                                                      result_element_names=[result_element_name] + (['error'] if has_error else []),
                                                                      args=args))

def _define_template_with_no_specializations(name: str,
                                             args: List[ir0.TemplateArgDecl],
                                             body_prefix: List[ir0.TemplateBodyElement] = [],
                                             value_expr: Optional[ir0.Expr] = None,
                                             type_expr: Optional[ir0.Expr] = None,
                                             error_expr: Optional[ir0.Expr] = None):
    assert (value_expr is None) != (type_expr is None)
    if value_expr:
        _define_template(main_definition=_specialization(args=args,
                                                         patterns=None,
                                                         body_prefix=body_prefix,
                                                         value_expr=value_expr,
                                                         error_expr=error_expr),
                         specializations=[],
                         name=name,
                         result_element_name='value',
                         has_error=(error_expr is not None))
    if type_expr:
        _define_template(main_definition=_specialization(args=args,
                                                         patterns=None,
                                                         body_prefix=body_prefix,
                                                         type_expr=type_expr,
                                                         error_expr=error_expr),
                         specializations=[],
                         name=name,
                         result_element_name='type',
                         has_error=(error_expr is not None))

def _define_template_with_single_specialization(name: str,
                                                main_definition_args: List[ir0.TemplateArgDecl],
                                                specialization_args: List[ir0.TemplateArgDecl],
                                                patterns: List[ir0.Expr],
                                                body_prefix: List[ir0.TemplateBodyElement] = [],
                                                value_expr: Optional[ir0.Expr] = None,
                                                type_expr: Optional[ir0.Expr] = None,
                                                error_expr: Optional[ir0.Expr] = None):
    assert (value_expr is None) != (type_expr is None)
    if value_expr:
        _define_template(main_definition=None,
                         args=main_definition_args,
                         specializations=[_specialization(args=specialization_args,
                                                          patterns=patterns,
                                                          body_prefix=body_prefix,
                                                          value_expr=value_expr,
                                                          error_expr=error_expr)],
                         name=name,
                         result_element_name='value',
                         has_error=(error_expr is not None))
    if type_expr:
        _define_template(main_definition=None,
                         args=main_definition_args,
                         specializations=[_specialization(args=specialization_args,
                                                          patterns=patterns,
                                                          body_prefix=body_prefix,
                                                          type_expr=type_expr,
                                                          error_expr=error_expr)],
                         name=name,
                         result_element_name='type',
                         has_error=(error_expr is not None))

# template <typename L1, typename L2>
# struct TypeListConcat;
#
# template <typename... Ts, typename... Us>
# struct TypeListConcat<List<Ts...>, List<Us...>> {
#   using type = List<Ts..., Us...>;
# };
_define_template_with_single_specialization(name='TypeListConcat',
                                            main_definition_args=[_type_arg_decl('L1'),
                                                                  _type_arg_decl('L2')],
                                            specialization_args=[_variadic_type_arg_decl('Ts'),
                                                                 _variadic_type_arg_decl('Us')],
                                            patterns=[_type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))),
                                                      _type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Us')))],
                                            type_expr=_type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Ts')),
                                                                    ir0.VariadicTypeExpansion(_local_variadic_type('Us'))))

# template <typename L1, typename L2>
# struct Int64ListConcat;
#
# template <int64_t... ns, int64_t... ms>
# struct Int64ListConcat<Int64List<ns...>, Int64List<ms...>> {
#   using type = Int64List<ns..., ms...>;
# };
_define_template_with_single_specialization(name='Int64ListConcat',
                                            main_definition_args=[_type_arg_decl('L1'),
                                                                  _type_arg_decl('L2')],
                                            specialization_args=[_variadic_int64_arg_decl('ns'),
                                                                 _variadic_int64_arg_decl('ms')],
                                            patterns=[_int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns'))),
                                                      _int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ms')))],
                                            type_expr=_int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns')),
                                                                   ir0.VariadicTypeExpansion(_local_variadic_int('ms'))))

# template <typename L1, typename L2>
# struct BoolListConcat;
#
# template <bool... bs1, bool... bs2>
# struct BoolListConcat<BoolList<bs1...>, BoolList<bs2...>> {
#   using type = BoolList<bs1..., bs2...>;
# };
_define_template_with_single_specialization(name='BoolListConcat',
                                            main_definition_args=[_type_arg_decl('L1'),
                                                                  _type_arg_decl('L2')],
                                            specialization_args=[_variadic_bool_arg_decl('bs1'),
                                                                 _variadic_bool_arg_decl('bs2')],
                                            patterns=[_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs1'))),
                                                      _bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs2')))],
                                            type_expr=_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs1')),
                                                                    ir0.VariadicTypeExpansion(_local_variadic_bool('bs2'))))

# template <typename L>
# struct Int64ListSum {
#   static constexpr int64_t value = 0;
# };
#
# template <int64_t n, int64_t... ns>
# struct Int64ListSum<Int64List<n, ns...>> {
#   static constexpr int64_t value = n + Int64ListSum<Int64List<ns...>>::value;
# };
_define_template(name='Int64ListSum',
                 result_element_name='value',
                 main_definition=_specialization(args=[_type_arg_decl('L')],
                                                 value_expr=ir0.Literal(0)),
                 specializations=[_specialization(args=[_int64_arg_decl('n'),
                                                        _variadic_int64_arg_decl('ns')],
                                                  patterns=[_int_list_of(_local_int('n'), ir0.VariadicTypeExpansion(_local_variadic_int('ns')))],
                                                  value_expr=ir0.Int64BinaryOpExpr(lhs=_local_int('n'),
                                                                                   rhs=_int64_list_sum(_int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns')))),
                                                                                   op='+'))])


# template <typename... Ts>
# struct GetFirstError {
#   using type = void;
# };
#
# template <typename... Ts>
# struct GetFirstError<void, Ts...> {
#   using type = typename GetFirstError<Ts...>::type;
# };
#
# template <typename T, typename... Ts>
# struct GetFirstError<T, Ts...> {
#   using type = T;
# };
_define_template(name='GetFirstError',
                 result_element_name='type',
                 main_definition=_specialization(args=[_variadic_type_arg_decl('Ts')],
                                                 type_expr=ir0_builtin_literals.GlobalLiterals.VOID),
                 specializations=[_specialization(args=[_variadic_type_arg_decl('Ts')],
                                                  patterns=[ir0_builtin_literals.GlobalLiterals.VOID,
                                                            ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))],
                                                  type_expr=_get_first_error(ir0.VariadicTypeExpansion(_local_variadic_type('Ts')))),
                                  _specialization(args=[_type_arg_decl('T'),
                                                        _variadic_type_arg_decl('Ts')],
                                                  patterns=[_local_type('T'),
                                                            ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))],
                                                  type_expr=_local_type('T'))])

# template <typename Acc, template <typename Acc1, bool b1> class F, bool... bs>
# struct FoldBoolsToType {
#   using type = Acc;
# };
#
# template <typename Acc, template <typename Acc1, bool b1> class F, bool b, bool... bs>
# struct FoldBoolsToType<Acc, F, b, bs...> {
#   using type = typename FoldBoolsToType<typename F<Acc, b>::type,
#                                         F,
#                                         bs...>::type;
# };
_define_template(name='FoldBoolsToType',
                 result_element_name='type',
                 main_definition=_specialization(args=[_type_arg_decl('Acc'),
                                                       _template_template_arg_decl('F', _type_arg_type(), _bool_arg_type()),
                                                       _variadic_bool_arg_decl('bs')],
                                                 type_expr=_local_type('Acc')),
                 specializations=[_specialization(args=[_type_arg_decl('Acc'),
                                                        _template_template_arg_decl('F', _type_arg_type(), _bool_arg_type()),
                                                        _bool_arg_decl('b'),
                                                        _variadic_bool_arg_decl('bs')],
                                                  patterns=[_local_type('Acc'),
                                                            ir0.AtomicTypeLiteral.for_local('F', ir0.TemplateType([_type_arg_type(), _bool_arg_type()]), is_variadic=False),
                                                            _local_bool('b'),
                                                            ir0.VariadicTypeExpansion(_local_variadic_bool('bs'))],
                                                  type_expr=_fold_bools_to_type(_local_metafunction_call('F',
                                                                                                         arg_types=[_type_arg_type(), _bool_arg_type()],
                                                                                                         args=[_local_type('Acc'),
                                                                                                               _local_bool('b')],
                                                                                                         instantiation_might_trigger_static_asserts=True,
                                                                                                         member_name='type',
                                                                                                         member_type=ir0.TypeType()),
                                                                                ir0.AtomicTypeLiteral.for_local('F', ir0.TemplateType([_type_arg_type(), _bool_arg_type()]), is_variadic=False),
                                                                                ir0.VariadicTypeExpansion(_local_variadic_bool('bs'))))])



# template <typename L>
# struct BoolListToSet;
#
# template <bool... bs>
# struct BoolListToSet<BoolList<bs...>> {
#   using type = typename FoldBoolsToType<BoolList<>, AddToBoolSet, bs...>::type;
# };
_define_template_with_single_specialization(name='BoolListToSet',
                                            main_definition_args=[_type_arg_decl('L')],
                                            specialization_args=[_variadic_bool_arg_decl('bs')],
                                            patterns=[_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs')))],
                                            type_expr=_fold_bools_to_type(_bool_list_of(),
                                                                          ir0_builtin_literals.GlobalLiterals.ADD_TO_BOOL_SET,
                                                                          ir0.VariadicTypeExpansion(_local_variadic_bool('bs'))))


# template <typename Acc, template <typename Acc1, int64_t n1> class F, int64_t... ns>
# struct FoldInt64sToType {
#   using type = Acc;
# };
#
# template <typename Acc, template <typename Acc1, int64_t n1> class F, int64_t n, int64_t... ns>
# struct FoldInt64sToType<Acc, F, n, ns...> {
#   using type = typename FoldInt64sToType<typename F<Acc, n>::type,
#                                          F,
#                                          ns...>::type;
# };
_define_template(name='FoldInt64sToType',
                 result_element_name='type',
                 main_definition=_specialization(args=[_type_arg_decl('Acc'),
                                                       _template_template_arg_decl('F', _type_arg_type(), _int64_arg_type()),
                                                       _variadic_int64_arg_decl('ns')],
                                                 type_expr=_local_type('Acc')),
                 specializations=[_specialization(args=[_type_arg_decl('Acc'),
                                                        _template_template_arg_decl('F', _type_arg_type(), _int64_arg_type()),
                                                        _int64_arg_decl('n'),
                                                        _variadic_int64_arg_decl('ns')],
                                                  patterns=[_local_type('Acc'),
                                                            ir0.AtomicTypeLiteral.for_local('F', ir0.TemplateType([_type_arg_type(), _int64_arg_type()]), is_variadic=False),
                                                            _local_int('n'),
                                                            ir0.VariadicTypeExpansion(_local_variadic_int('ns'))],
                                                  type_expr=_fold_int64s_to_type(_local_metafunction_call('F',
                                                                                                          arg_types=[_type_arg_type(), _int64_arg_type()],
                                                                                                          args=[_local_type('Acc'),
                                                                                                                _local_int('n')],
                                                                                                          instantiation_might_trigger_static_asserts=True,
                                                                                                          member_name='type',
                                                                                                          member_type=ir0.TypeType()),
                                                                                 ir0.AtomicTypeLiteral.for_local('F', ir0.TemplateType([_type_arg_type(), _int64_arg_type()]), is_variadic=False),
                                                                                 ir0.VariadicTypeExpansion(_local_variadic_int('ns'))))])

# template <typename L>
# struct Int64ListToSet;
#
# template <int64_t... ns>
# struct Int64ListToSet<Int64List<ns...>> {
#   using type = typename FoldInt64sToType<Int64List<>, AddToInt64Set, ns...>::type;
# };
_define_template_with_single_specialization(name='Int64ListToSet',
                                            main_definition_args=[_type_arg_decl('L')],
                                            specialization_args=[_variadic_int64_arg_decl('ns')],
                                            patterns=[_int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns')))],
                                            type_expr=_fold_int64s_to_type(_int_list_of(),
                                                                           ir0_builtin_literals.GlobalLiterals.ADD_TO_INT64_SET,
                                                                           ir0.VariadicTypeExpansion(_local_variadic_int('ns'))))



# template <typename Acc, template <typename Acc1, typename T1> class F, typename... Ts>
# struct FoldTypesToType {
#   using type = Acc;
# };
#
# template <typename Acc, template <typename Acc1, typename T1> class F, typename T, typename... Ts>
# struct FoldTypesToType<Acc, F, T, Ts...> {
#   using type = typename FoldTypesToType<typename F<Acc, T>::type,
#                                          F,
#                                          Ts...>::type;
# };
_define_template(name='FoldTypesToType',
                 result_element_name='type',
                 main_definition=_specialization(args=[_type_arg_decl('Acc'),
                                                       _template_template_arg_decl('F', _type_arg_type(), _type_arg_type()),
                                                       _variadic_type_arg_decl('Ts')],
                                                 type_expr=_local_type('Acc')),
                 specializations=[_specialization(args=[_type_arg_decl('Acc'),
                                                        _template_template_arg_decl('F', _type_arg_type(), _type_arg_type()),
                                                        _type_arg_decl('T'),
                                                        _variadic_type_arg_decl('Ts')],
                                                  patterns=[_local_type('Acc'),
                                                            ir0.AtomicTypeLiteral.for_local('F', ir0.TemplateType([_type_arg_type(), _type_arg_type()]), is_variadic=False),
                                                            _local_type('T'),
                                                            ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))],
                                                  type_expr=_fold_types_to_type(_local_metafunction_call('F',
                                                                                                         arg_types=[_type_arg_type(), _type_arg_type()],
                                                                                                         args=[_local_type('Acc'),
                                                                                                               _local_type('T')],
                                                                                                         instantiation_might_trigger_static_asserts=True,
                                                                                                         member_name='type',
                                                                                                         member_type=ir0.TypeType()),
                                                                                ir0.AtomicTypeLiteral.for_local('F', ir0.TemplateType([_type_arg_type(), _type_arg_type()]), is_variadic=False),
                                                                                ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))))])

# template <typename L>
# struct TypeListToSet;
#
# template <typename... Ts>
# struct TypeListToSet<List<Ts...>> {
#   using type = typename FoldTypesToType<List<>, AddToTypeSet, Ts...>::type;
# };
_define_template_with_single_specialization(name='TypeListToSet',
                                            main_definition_args=[_type_arg_decl('L')],
                                            specialization_args=[_variadic_type_arg_decl('Ts')],
                                            patterns=[_type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Ts')))],
                                            type_expr=_fold_types_to_type(_type_list_of(),
                                                                          ir0_builtin_literals.GlobalLiterals.ADD_TO_TYPE_SET,
                                                                          ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))))

def get_builtin_templates():
    from _py2tmp import ast_to_ir3, ir3_optimization, ir3_to_ir2, ir2_to_ir1, ir1_to_ir0, ir0_optimization

    if _BuiltinTemplatesHolder.initialized or _BuiltinTemplatesHolder.initializing:
        return _BuiltinTemplatesHolder.BUILTIN_TEMPLATES
    _BuiltinTemplatesHolder.initializing = True

    tmppy_builtins_file_name = importlib_util.find_spec('_py2tmp.tmppy_builtins').origin
    with open(tmppy_builtins_file_name) as tmppy_builtins_file:
        _builtins_source = tmppy_builtins_file.read()
    builtins_ast = ast.parse(_builtins_source, filename=tmppy_builtins_file_name)

    def identifier_generator_fun():
        for i in itertools.count():
            yield 'TmppyInternalBuiltin_%s' % i

    identifier_generator = iter(identifier_generator_fun())
    _BuiltinTemplatesHolder.identifier_generator = identifier_generator
    compilation_context = ast_to_ir3.CompilationContext(ast_to_ir3.SymbolTable(),
                                                        ast_to_ir3.SymbolTable(),
                                                        'tmppy_builtins.py',
                                                        _builtins_source.splitlines(),
                                                        identifier_generator)
    module_ir3 = ast_to_ir3.module_ast_to_ir3_internal(builtins_ast, compilation_context)
    module_ir3 = ir3_optimization.optimize_module(module_ir3)
    module_ir2 = ir3_to_ir2.module_to_ir2(module_ir3, identifier_generator)
    module_ir1 = ir2_to_ir1.module_to_ir1(module_ir2)
    non_optimized_header = ir1_to_ir0.module_to_ir0(module_ir1, identifier_generator)
    old_max_num_optimization_steps = configuration_knobs.ConfigurationKnobs.max_num_optimization_steps
    configuration_knobs.ConfigurationKnobs.max_num_optimization_steps = -1
    optimized_header, split_template_name_by_old_name_and_result_element_name = ir0_optimization.optimize_builtin_header(non_optimized_header, identifier_generator)
    configuration_knobs.ConfigurationKnobs.max_num_optimization_steps = old_max_num_optimization_steps
    assert not optimized_header.toplevel_content

    _BuiltinTemplatesHolder.initialized = True
    _BuiltinTemplatesHolder.initializing = False
    _BuiltinTemplatesHolder.BUILTIN_TEMPLATES += [template_defn
                                                  for template_defn in optimized_header.template_defns
                                                  # The right CheckIfError will be generated based on the user code,
                                                  # where there can be custom types.
                                                  if template_defn.name != 'CheckIfError']
    _BuiltinTemplatesHolder.split_template_name_by_old_name_and_result_element_name = split_template_name_by_old_name_and_result_element_name

    return _BuiltinTemplatesHolder.BUILTIN_TEMPLATES

def get_split_template_name_by_old_name_and_result_element_name():
    get_builtin_templates()
    return _BuiltinTemplatesHolder.split_template_name_by_old_name_and_result_element_name

@lru_cache()
def get_builtins_cpp_code():
    from _py2tmp import ir0_to_cpp, utils

    template_defns = get_builtin_templates()
    writer = ir0_to_cpp.ToplevelWriter(_BuiltinTemplatesHolder.identifier_generator)
    writer.write_toplevel_elem('''\
        #include <tmppy/tmppy.h>
        #include <type_traits>
        ''')
    ir0_to_cpp.template_defns_to_cpp(template_defns, writer)
    result = utils.clang_format(''.join(writer.strings))

    # TODO: remove
    #print('Builtins C++ code:\n' + result)

    return result
