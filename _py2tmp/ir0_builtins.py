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
from typing import List, Optional, Sequence

from _py2tmp import ir0

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

class GlobalLiterals:
    VOID = ir0.AtomicTypeLiteral.for_nonlocal_type('void', may_be_alias=False)
    CHAR = ir0.AtomicTypeLiteral.for_nonlocal_type('char', may_be_alias=False)
    SHORT = ir0.AtomicTypeLiteral.for_nonlocal_type('short', may_be_alias=False)
    INT = ir0.AtomicTypeLiteral.for_nonlocal_type('int', may_be_alias=False)
    UNSIGNED = ir0.AtomicTypeLiteral.for_nonlocal_type('unsigned', may_be_alias=False)
    INT32_T = ir0.AtomicTypeLiteral.for_nonlocal_type('int32_t', may_be_alias=False)
    INT64_T = ir0.AtomicTypeLiteral.for_nonlocal_type('int64_t', may_be_alias=False)
    UINT32_T = ir0.AtomicTypeLiteral.for_nonlocal_type('uint32_t', may_be_alias=False)
    UINT64_T = ir0.AtomicTypeLiteral.for_nonlocal_type('uint64_t', may_be_alias=False)
    LONG = ir0.AtomicTypeLiteral.for_nonlocal_type('long', may_be_alias=False)
    FLOAT = ir0.AtomicTypeLiteral.for_nonlocal_type('float', may_be_alias=False)
    DOUBLE = ir0.AtomicTypeLiteral.for_nonlocal_type('double', may_be_alias=False)

    BOOL_LIST = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='BoolList',
                                                            args=[_variadic_bool_arg_type()],
                                                            is_metafunction_that_may_return_error=False,
                                                            may_be_alias=False)

    INT_LIST = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='Int64List',
                                                           args=[_variadic_int64_arg_type()],
                                                           is_metafunction_that_may_return_error=False,
                                                           may_be_alias=False)

    LIST = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='List',
                                                       args=[_variadic_type_arg_type()],
                                                       is_metafunction_that_may_return_error=False,
                                                       may_be_alias=False)

    CHECK_IF_ERROR = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='CheckIfError',
                                                                 args=[_type_arg_type()],
                                                                 is_metafunction_that_may_return_error=False,
                                                                 may_be_alias=False)

    GET_FIRST_ERROR = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='GetFirstError',
                                                                  args=[_variadic_type_arg_type()],
                                                                  is_metafunction_that_may_return_error=False,
                                                                  may_be_alias=False)

    ALWAYS_TRUE_FROM_TYPE = ir0.AtomicTypeLiteral.for_nonlocal_template('AlwaysTrueFromType',
                                                                        args=[_type_arg_type()],
                                                                        is_metafunction_that_may_return_error=False,
                                                                        may_be_alias=False)

    ALWAYS_FALSE_FROM_TYPE = ir0.AtomicTypeLiteral.for_nonlocal_template('AlwaysFalseFromType',
                                                                         args=[_type_arg_type()],
                                                                         is_metafunction_that_may_return_error=False,
                                                                         may_be_alias=False)

    STD_IS_SAME = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::is_same',
                                                              is_metafunction_that_may_return_error=False,
                                                              args=[_type_arg_type(),
                                                                    _type_arg_type()],
                                                              may_be_alias=False)

    STD_PAIR = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::pair',
                                                           is_metafunction_that_may_return_error=False,
                                                           args=[_type_arg_type(), _type_arg_type()],
                                                           may_be_alias=False)

    STD_TUPLE = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='std::tuple',
                                                            is_metafunction_that_may_return_error=False,
                                                            args=[_variadic_type_arg_type()],
                                                            may_be_alias=False)

    BOOL_LIST_TO_SET = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='BoolListToSet',
                                                                   args=[_type_arg_type()],
                                                                   is_metafunction_that_may_return_error=False,
                                                                   may_be_alias=False)
    INT64_LIST_TO_SET = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='Int64ListToSet',
                                                                    args=[_type_arg_type()],
                                                                    is_metafunction_that_may_return_error=False,
                                                                    may_be_alias=False)
    TYPE_LIST_TO_SET = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='TypeListToSet',
                                                                   args=[_type_arg_type()],
                                                                   is_metafunction_that_may_return_error=False,
                                                                   may_be_alias=False)

    ADD_TO_BOOL_SET_HELPER = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='AddToBoolSetHelper',
                                                                         args=[_type_arg_type(),
                                                                               _type_arg_type(),
                                                                               _type_arg_type(),
                                                                               _bool_arg_type()],
                                                                         is_metafunction_that_may_return_error=False,
                                                                         may_be_alias=False)

    ADD_TO_INT64_SET_HELPER = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='AddToInt64SetHelper',
                                                                          args=[_type_arg_type(),
                                                                                _type_arg_type(),
                                                                                _type_arg_type(),
                                                                                _int64_arg_type()],
                                                                          is_metafunction_that_may_return_error=False,
                                                                          may_be_alias=False)

    ADD_TO_TYPE_SET_HELPER = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='AddToTypeSetHelper',
                                                                         args=[_type_arg_type(),
                                                                               _type_arg_type(),
                                                                               _type_arg_type(),
                                                                               _type_arg_type()],
                                                                         is_metafunction_that_may_return_error=False,
                                                                         may_be_alias=False)

    ADD_TO_BOOL_SET = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='AddToBoolSet',
                                                                  args=[_type_arg_type(), _bool_arg_type()],
                                                                  is_metafunction_that_may_return_error=False,
                                                                  may_be_alias=False)

    ADD_TO_INT64_SET = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='AddToInt64Set',
                                                                   args=[_type_arg_type(), _int64_arg_type()],
                                                                   is_metafunction_that_may_return_error=False,
                                                                   may_be_alias=False)

    ADD_TO_TYPE_SET = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='AddToTypeSet',
                                                                  args=[_type_arg_type(), _type_arg_type()],
                                                                  is_metafunction_that_may_return_error=False,
                                                                  may_be_alias=False)

    FOLD_BOOLS_TO_TYPE = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='FoldBoolsToType',
                                                                     args=[_type_arg_type(),
                                                                           _template_template_arg_type(_type_arg_type(),
                                                                                                       _bool_arg_type()),
                                                                           _variadic_bool_arg_type()],
                                                                     is_metafunction_that_may_return_error=True,
                                                                     may_be_alias=False)

    FOLD_INT64S_TO_TYPE = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='FoldInt64sToType',
                                                                      args=[_type_arg_type(),
                                                                            _template_template_arg_type(_type_arg_type(),
                                                                                                        _int64_arg_type()),
                                                                            _variadic_int64_arg_type()],
                                                                      is_metafunction_that_may_return_error=True,
                                                                      may_be_alias=False)

    FOLD_TYPES_TO_TYPE = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='FoldTypesToType',
                                                                     args=[_type_arg_type(),
                                                                           _template_template_arg_type(_type_arg_type(),
                                                                                                       _type_arg_type()),
                                                                           _variadic_type_arg_type()],
                                                                     is_metafunction_that_may_return_error=True,
                                                                     may_be_alias=False)

    INT64_LIST_SUM = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='Int64ListSum',
                                                                 args=[_type_arg_type()],
                                                                 is_metafunction_that_may_return_error=False,
                                                                 may_be_alias=False)

    IS_IN_BOOL_SET = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='IsInBoolSet',
                                                                 args=[_type_arg_type(), _bool_arg_type()],
                                                                 is_metafunction_that_may_return_error=False,
                                                                 may_be_alias=False)

    IS_IN_INT64_SET = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='IsInInt64Set',
                                                                  args=[_type_arg_type(), _int64_arg_type()],
                                                                  is_metafunction_that_may_return_error=False,
                                                                  may_be_alias=False)

    IS_IN_TYPE_SET = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='IsInTypeSet',
                                                                 args=[_type_arg_type(), _type_arg_type()],
                                                                 is_metafunction_that_may_return_error=False,
                                                                 may_be_alias=False)

GLOBAL_LITERALS_BY_NAME = {x.cpp_type: x
                           for x in GlobalLiterals.__dict__.values()
                           if isinstance(x, ir0.AtomicTypeLiteral)}

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
    return ir0.TemplateInstantiation(template_expr=GlobalLiterals.BOOL_LIST,
                                     args=args,
                                     instantiation_might_trigger_static_asserts=False)

def _int_list_of(*args: ir0.Expr):
    return ir0.TemplateInstantiation(template_expr=GlobalLiterals.INT_LIST,
                                     args=args,
                                     instantiation_might_trigger_static_asserts=False)

def _type_list_of(*args: ir0.Expr):
    return ir0.TemplateInstantiation(template_expr=GlobalLiterals.LIST,
                                     args=args,
                                     instantiation_might_trigger_static_asserts=False)

def _get_first_error(*args: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.GET_FIRST_ERROR,
                              args=args,
                              instantiation_might_trigger_static_asserts=False,
                              member_name='type',
                              member_type=ir0.TypeType())

def _is_same(lhs: ir0.Expr, rhs: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.STD_IS_SAME,
                              args=[lhs, rhs],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='value',
                              member_type=ir0.BoolType())

def _int64_list_sum(l: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.INT64_LIST_SUM,
                              args=[l],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='value',
                              member_type=ir0.Int64Type())

def _add_to_bool_set_helper(all_false_list_if_not_present: ir0.Expr, all_false_list: ir0.Expr, s: ir0.Expr, b: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.ADD_TO_BOOL_SET_HELPER,
                              args=[all_false_list_if_not_present,
                                    all_false_list,
                                    s,
                                    b],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='type',
                              member_type=ir0.TypeType())

def _add_to_int64_set_helper(all_false_list_if_not_present: ir0.Expr, all_false_list: ir0.Expr, s: ir0.Expr, n: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.ADD_TO_INT64_SET_HELPER,
                              args=[all_false_list_if_not_present,
                                    all_false_list,
                                    s,
                                    n],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='type',
                              member_type=ir0.TypeType())

def _add_to_type_set_helper(all_false_list_if_not_present: ir0.Expr, all_false_list: ir0.Expr, s: ir0.Expr, t: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.ADD_TO_TYPE_SET_HELPER,
                              args=[all_false_list_if_not_present,
                                    all_false_list,
                                    s,
                                    t],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='type',
                              member_type=ir0.TypeType())

def _fold_bools_to_type(acc: ir0.Expr, f: ir0.Expr, bs: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.FOLD_BOOLS_TO_TYPE,
                              args=[acc, f, bs],
                              instantiation_might_trigger_static_asserts=True,
                              member_name='type',
                              member_type=ir0.TypeType())

def _fold_int64s_to_type(acc: ir0.Expr, f: ir0.Expr, ns: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.FOLD_INT64S_TO_TYPE,
                              args=[acc, f, ns],
                              instantiation_might_trigger_static_asserts=True,
                              member_name='type',
                              member_type=ir0.TypeType())

def _fold_types_to_type(acc: ir0.Expr, f: ir0.Expr, ts: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.FOLD_TYPES_TO_TYPE,
                              args=[acc, f, ts],
                              instantiation_might_trigger_static_asserts=True,
                              member_name='type',
                              member_type=ir0.TypeType())

def _always_true_from_type(t: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.ALWAYS_TRUE_FROM_TYPE,
                              args=[t],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='value',
                              member_type=ir0.BoolType())

def _always_false_from_type(t: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.ALWAYS_FALSE_FROM_TYPE,
                              args=[t],
                              instantiation_might_trigger_static_asserts=False,
                              member_name='value',
                              member_type=ir0.BoolType())

def _is_in_bool_set(s: ir0.Expr, b: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.IS_IN_BOOL_SET,
                              args=[s, b],
                              instantiation_might_trigger_static_asserts=False,
                              member_type=ir0.BoolType(),
                              member_name='value')

def _is_in_int64_set(s: ir0.Expr, n: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.IS_IN_INT64_SET,
                              args=[s, n],
                              instantiation_might_trigger_static_asserts=False,
                              member_type=ir0.BoolType(),
                              member_name='value')

def _is_in_type_set(s: ir0.Expr, t: ir0.Expr):
    return _metafunction_call(template_expr=GlobalLiterals.IS_IN_TYPE_SET,
                              args=[s, t],
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

BUILTIN_TEMPLATES: List[ir0.TemplateDefn] = []

def _define_template(main_definition: Optional[ir0.TemplateSpecialization],
                     specializations: Sequence[ir0.TemplateSpecialization],
                     name: str,
                     result_element_name: str,
                     args: Optional[Sequence[ir0.TemplateArgDecl]] = None,
                     has_error: bool = False):
    BUILTIN_TEMPLATES.append(ir0.TemplateDefn(main_definition=main_definition,
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

# template <typename>
# struct AlwaysFalseFromType {
#   static constexpr bool value = false;
# };
_define_template_with_no_specializations(name='AlwaysFalseFromType',
                                         args=[_type_arg_decl('T')],
                                         value_expr=ir0.Literal(False))

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

# template <typename L>
# struct BoolListAll;
#
# template <bool... bs>
# struct BoolListAll<BoolList<bs...>> {
#   static constexpr bool value = std::is_same<BoolList<bs...>, BoolList<(bs || true)...>>::value;
# };
_define_template_with_single_specialization(name='BoolListAll',
                                            main_definition_args=[_type_arg_decl('L')],
                                            specialization_args=[_variadic_bool_arg_decl('bs')],
                                            patterns=[_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs')))],
                                            value_expr=_is_same(_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs'))),
                                                                _bool_list_of(ir0.VariadicTypeExpansion(ir0.BoolBinaryOpExpr(_local_variadic_bool('bs'),
                                                                                                                             ir0.Literal(True),
                                                                                                                             op='||')))))

# template <typename L>
# struct BoolListAny;
#
# template <bool... bs>
# struct BoolListAny<BoolList<bs...>> {
#   static constexpr bool value = !std::is_same<BoolList<bs...>, BoolList<(bs && false)...>>::value;
# };
_define_template_with_single_specialization(name='BoolListAny',
                                            main_definition_args=[_type_arg_decl('L')],
                                            specialization_args=[_variadic_bool_arg_decl('bs')],
                                            patterns=[_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs')))],
                                            value_expr=ir0.NotExpr(_is_same(_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs'))),
                                                                            _bool_list_of(ir0.VariadicTypeExpansion(ir0.BoolBinaryOpExpr(_local_variadic_bool('bs'),
                                                                                                                                         ir0.Literal(False),
                                                                                                                                         op='&&'))))))



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
                                                 type_expr=GlobalLiterals.VOID),
                 specializations=[_specialization(args=[_variadic_type_arg_decl('Ts')],
                                                  patterns=[GlobalLiterals.VOID,
                                                            ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))],
                                                  type_expr=_get_first_error(ir0.VariadicTypeExpansion(_local_variadic_type('Ts')))),
                                  _specialization(args=[_type_arg_decl('T'),
                                                        _variadic_type_arg_decl('Ts')],
                                                  patterns=[_local_type('T'),
                                                            ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))],
                                                  type_expr=_local_type('T'))])

# template <typename AllFalseListIfNotPresent, typename AllFalseList, typename S, bool b>
# struct AddToBoolSetHelper {
#   using type = S;
# };
#
# template <typename AllFalseList, bool... bs, bool b>
# struct AddToBoolSetHelper<AllFalseList, AllFalseList, BoolList<bs...>, b> {
#   using type = BoolList<bs..., b>;
# };
_define_template(name='AddToBoolSetHelper',
                 result_element_name='type',
                 main_definition=_specialization(args=[_type_arg_decl('AllFalseListIfNotPresent'),
                                                       _type_arg_decl('AllFalseList'),
                                                       _type_arg_decl('S'),
                                                       _bool_arg_decl('b')],
                                                 type_expr=_local_type('S')),
                 specializations=[_specialization(args=[_type_arg_decl('AllFalseList'),
                                                        _variadic_bool_arg_decl('bs'),
                                                        _bool_arg_decl('b')],
                                                  patterns=[_local_type('AllFalseList'),
                                                            _local_type('AllFalseList'),
                                                            _bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs'))),
                                                            _local_bool('b')],
                                                  type_expr=_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs')),
                                                                          _local_bool('b')))])

# template <typename S, bool b>
# struct AddToBoolSet;
#
# template <bool... bs, bool b>
# struct AddToBoolSet<BoolList<bs...>, b> {
#   using type = typename AddToBoolSetHelper<BoolList<(bs == b)...>,
#                                            BoolList<(bs && false)...>,
#                                            BoolList<bs...>,
#                                            b>::type;
# };
_define_template_with_single_specialization(name='AddToBoolSet',
                                            main_definition_args=[_type_arg_decl('S'),
                                                                  _bool_arg_decl('b')],
                                            specialization_args=[_variadic_bool_arg_decl('bs'),
                                                                 _bool_arg_decl('b')],
                                            patterns=[_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs'))),
                                                      _local_bool('b')],
                                            type_expr=_add_to_bool_set_helper(_bool_list_of(ir0.VariadicTypeExpansion(ir0.ComparisonExpr(lhs=_local_variadic_bool('bs'),
                                                                                                                                         rhs=_local_bool('b'),
                                                                                                                                         op='=='))),
                                                                              _bool_list_of(ir0.VariadicTypeExpansion(ir0.BoolBinaryOpExpr(lhs=_local_variadic_bool('bs'),
                                                                                                                                           rhs=ir0.Literal(False),
                                                                                                                                           op='&&'))),
                                                                              _bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs'))),
                                                                              _local_bool('b')))


# template <typename AllFalseListIfNotPresent, typename AllFalseList, typename S, int64_t n>
# struct AddToInt64SetHelper {
#   using type = S;
# };
# template <typename AllFalseList, int64_t... ns, int64_t n>
# struct AddToInt64SetHelper<AllFalseList, AllFalseList, Int64List<ns...>, n> {
#   using type = Int64List<ns..., n>;
# };
#
_define_template(name='AddToInt64SetHelper',
                 result_element_name='type',
                 main_definition=_specialization(args=[_type_arg_decl('AllFalseListIfNotPresent'),
                                                       _type_arg_decl('AllFalseList'),
                                                       _type_arg_decl('S'),
                                                       _int64_arg_decl('n')],
                                                 type_expr=_local_type('S')),
                 specializations=[_specialization(args=[_type_arg_decl('AllFalseList'),
                                                        _variadic_int64_arg_decl('ns'),
                                                        _int64_arg_decl('n')],
                                                  patterns=[_local_type('AllFalseList'),
                                                            _local_type('AllFalseList'),
                                                            _int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns'))),
                                                            _local_int('n')],
                                                  type_expr=_int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns')),
                                                                         _local_int('n')))])

# template <typename S, int64_t n>
# struct AddToInt64Set;
#
# template <int64_t... ns, int64_t n>
# struct AddToInt64Set<Int64List<ns...>, n> {
#   using type = typename AddToInt64SetHelper<BoolList<(ns == n)...>,
#                                             BoolList<(ns != ns)...>,
#                                             Int64List<ns...>,
#                                             n>::type;
# };
_define_template_with_single_specialization(name='AddToInt64Set',
                                            main_definition_args=[_type_arg_decl('S'),
                                                                  _int64_arg_decl('n')],
                                            specialization_args=[_variadic_int64_arg_decl('ns'),
                                                                 _int64_arg_decl('n')],
                                            patterns=[_int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns'))),
                                                      _local_int('n')],
                                            type_expr=_add_to_int64_set_helper(_bool_list_of(ir0.VariadicTypeExpansion(ir0.ComparisonExpr(lhs=_local_variadic_int('ns'),
                                                                                                                                          rhs=_local_int('n'),
                                                                                                                                          op='=='))),
                                                                               _bool_list_of(ir0.VariadicTypeExpansion(ir0.ComparisonExpr(lhs=_local_variadic_int('ns'),
                                                                                                                                          rhs=_local_variadic_int('ns'),
                                                                                                                                          op='!='))),
                                                                               _int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns'))),
                                                                               _local_int('n')))

# template <typename AllFalseListIfNotPresent, typename AllFalseList, typename S, typename T>
# struct AddToTypeSetHelper {
#   using type = S;
# };
#
# template <typename AllFalseList, typename... Ts, typename T>
# struct AddToTypeSetHelper<AllFalseList, AllFalseList, List<Ts...>, T> {
#   using type = List<Ts..., T>;
# };
_define_template(name='AddToTypeSetHelper',
                 result_element_name='type',
                 main_definition=_specialization(args=[_type_arg_decl('AllFalseListIfNotPresent'),
                                                       _type_arg_decl('AllFalseList'),
                                                       _type_arg_decl('S'),
                                                       _type_arg_decl('T')],
                                                 type_expr=_local_type('S')),
                 specializations=[_specialization(args=[_type_arg_decl('AllFalseList'),
                                                        _variadic_type_arg_decl('Ts'),
                                                        _type_arg_decl('T')],
                                                  patterns=[_local_type('AllFalseList'),
                                                            _local_type('AllFalseList'),
                                                            _type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))),
                                                            _local_type('T')],
                                                  type_expr=_type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Ts')),
                                                                          _local_type('T')))])


# template <typename S, typename T>
# struct AddToTypeSet;
#
# template <typename... Ts, typename T>
# struct AddToTypeSet<List<Ts...>, T> {
#   using type = typename AddToTypeSetHelper<BoolList<std::is_same<Ts, T>::value...>,
#                                            BoolList<AlwaysFalseFromType<Ts>::value...>,
#                                            List<Ts...>,
#                                            T>::type;
# };
_define_template_with_single_specialization(name='AddToTypeSet',
                                            main_definition_args=[_type_arg_decl('S'),
                                                                  _type_arg_decl('T')],
                                            specialization_args=[_variadic_type_arg_decl('Ts'),
                                                                 _type_arg_decl('T')],
                                            patterns=[_type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))),
                                                      _local_type('T')],
                                            type_expr=_add_to_type_set_helper(_bool_list_of(ir0.VariadicTypeExpansion(_is_same(_local_variadic_type('Ts'),
                                                                                                                               _local_type('T')))),
                                                                              _bool_list_of(ir0.VariadicTypeExpansion(_always_false_from_type(_local_variadic_type('Ts')))),
                                                                              _type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))),
                                                                              _local_type('T')))

# template <typename S, bool b>
# struct IsInBoolSet;
#
# template <bool... bs, bool b>
# struct IsInBoolSet<BoolList<bs...>, b> {
#   static constexpr bool value = !std::is_same<BoolList<(bs == b)...>,
#                                               BoolList<(bs && false)...>
#                                               >::value;
# };

_define_template_with_single_specialization(name='IsInBoolSet',
                                            main_definition_args=[_type_arg_decl('S'),
                                                                  _bool_arg_decl('b')],
                                            specialization_args=[_variadic_bool_arg_decl('bs'),
                                                                 _bool_arg_decl('b')],
                                            patterns=[_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs'))),
                                                      _local_bool('b')],
                                            value_expr=ir0.NotExpr(_is_same(_bool_list_of(ir0.VariadicTypeExpansion(ir0.ComparisonExpr(lhs=_local_variadic_bool('bs'),
                                                                                                                                       rhs=_local_bool('b'),
                                                                                                                                       op='=='))),
                                                                            _bool_list_of(ir0.VariadicTypeExpansion(ir0.BoolBinaryOpExpr(lhs=_local_variadic_bool('bs'),
                                                                                                                                         rhs=ir0.Literal(False),
                                                                                                                                         op='&&'))))))

# template <typename S1, typename S2>
# struct BoolSetEquals;
#
# template <bool... bs1, bool... bs2>
# struct BoolSetEquals<BoolList<bs1...>, BoolList<bs2...>> {
#   static constexpr bool value =
#       std::is_same<BoolList<IsInBoolSet<BoolList<bs1...>, bs2>::value...,
#                             IsInBoolSet<BoolList<bs2...>, bs1>::value...>,
#                    BoolList<(bs2 || true)...,
#                             (bs1 || true)...>
#                    >::value;
# };
_define_template_with_single_specialization(name='BoolSetEquals',
                                            main_definition_args=[_type_arg_decl('S1'), _type_arg_decl('S2')],
                                            specialization_args=[_variadic_bool_arg_decl('bs1'),
                                                                 _variadic_bool_arg_decl('bs2')],
                                            patterns=[_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs1'))),
                                                      _bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs2')))],
                                            value_expr=_is_same(lhs=_bool_list_of(ir0.VariadicTypeExpansion(_is_in_bool_set(_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs1'))),
                                                                                                                            _local_variadic_bool('bs2'))),
                                                                                  ir0.VariadicTypeExpansion(_is_in_bool_set(_bool_list_of(ir0.VariadicTypeExpansion(_local_variadic_bool('bs2'))),
                                                                                                                            _local_variadic_bool('bs1')))),
                                                                rhs=_bool_list_of(ir0.VariadicTypeExpansion(ir0.BoolBinaryOpExpr(_local_variadic_bool('bs2'),
                                                                                                                                 ir0.Literal(True),
                                                                                                                                 op='||')),
                                                                                  ir0.VariadicTypeExpansion(ir0.BoolBinaryOpExpr(_local_variadic_bool('bs1'),
                                                                                                                                 ir0.Literal(True),
                                                                                                                                 op='||')))))

# template <typename S, int64_t n>
# struct IsInInt64Set;
#
# template <int64_t... ns, int64_t n>
# struct IsInInt64Set<Int64List<ns...>, n> {
#   static constexpr bool value = !std::is_same<BoolList<(ns == n)...>,
#                                               BoolList<(ns != ns)...>
#                                               >::value;
# };

_define_template_with_single_specialization(name='IsInInt64Set',
                                            main_definition_args=[_type_arg_decl('S'),
                                                                  _int64_arg_decl('n')],
                                            specialization_args=[_variadic_int64_arg_decl('ns'),
                                                                 _int64_arg_decl('n')],
                                            patterns=[_int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns'))),
                                                      _local_int('n')],
                                            value_expr=ir0.NotExpr(_is_same(_bool_list_of(ir0.VariadicTypeExpansion(ir0.ComparisonExpr(lhs=_local_variadic_int('ns'),
                                                                                                                                       rhs=_local_int('n'),
                                                                                                                                       op='=='))),
                                                                            _bool_list_of(ir0.VariadicTypeExpansion(ir0.ComparisonExpr(lhs=_local_variadic_int('ns'),
                                                                                                                                       rhs=_local_variadic_int('ns'),
                                                                                                                                       op='!='))))))

# template <typename S1, typename S2>
# struct Int64SetEquals;
#
# template <int64_t... ns1, int64_t... ns2>
# struct Int64SetEquals<Int64List<ns1...>, Int64List<ns2...>> {
#   static constexpr bool value =
#       std::is_same<BoolList<IsInInt64Set<Int64List<ns1...>, ns2>::value...,
#                             IsInInt64Set<Int64List<ns2...>, ns1>::value...>,
#                    BoolList<(ns2 == ns2)...,
#                             (ns1 == ns1)...>
#                    >::value;
# };
_define_template_with_single_specialization(name='Int64SetEquals',
                                            main_definition_args=[_type_arg_decl('S1'), _type_arg_decl('S2')],
                                            specialization_args=[_variadic_int64_arg_decl('ns1'),
                                                                 _variadic_int64_arg_decl('ns2')],
                                            patterns=[_int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns1'))),
                                                      _int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns2')))],
                                            value_expr=_is_same(lhs=_bool_list_of(ir0.VariadicTypeExpansion(_is_in_int64_set(_int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns1'))),
                                                                                                                             _local_variadic_int('ns2'))),
                                                                                  ir0.VariadicTypeExpansion(_is_in_int64_set(_int_list_of(ir0.VariadicTypeExpansion(_local_variadic_int('ns2'))),
                                                                                                                             _local_variadic_int('ns1')))),
                                                                rhs=_bool_list_of(ir0.VariadicTypeExpansion(ir0.ComparisonExpr(_local_variadic_int('ns2'),
                                                                                                                               _local_variadic_int('ns2'),
                                                                                                                               op='==')),
                                                                                  ir0.VariadicTypeExpansion(ir0.ComparisonExpr(_local_variadic_int('ns1'),
                                                                                                                               _local_variadic_int('ns1'),
                                                                                                                               op='==')))))

# template <typename S, typename T>
# struct IsInTypeSet;
#
# template <typename... Ts, typename T>
# struct IsInTypeSet<List<Ts...>, T> {
#   static constexpr bool value = !std::is_same<BoolList<std::is_same<Ts, T>::value...>,
#                                               BoolList<AlwaysFalseFromType<Ts>::value...>
#                                               >::value;
# };
_define_template_with_single_specialization(name='IsInTypeSet',
                                            main_definition_args=[_type_arg_decl('S'),
                                                                  _type_arg_decl('T')],
                                            specialization_args=[_variadic_type_arg_decl('Ts'),
                                                                 _type_arg_decl('T')],
                                            patterns=[_type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))),
                                                      _local_type('T')],
                                            value_expr=ir0.NotExpr(_is_same(_bool_list_of(ir0.VariadicTypeExpansion(_is_same(_local_variadic_type('Ts'),
                                                                                                                             _local_type('T')))),
                                                                            _bool_list_of(ir0.VariadicTypeExpansion(_always_false_from_type(_local_variadic_type('Ts')))))))


# template <typename S1, typename S2>
# struct TypeSetEquals;
#
# template <typename... Ts, typename... Us>
# struct TypeSetEquals<List<Ts...>, List<Us...>> {
#   static constexpr bool value =
#       std::is_same<BoolList<IsInTypeSet<List<Ts...>, Us>::value...,
#                             IsInTypeSet<List<Us...>, Ts>::value...>,
#                    BoolList<AlwaysTrueFromType<Us>::value...,
#                             AlwaysTrueFromType<Ts>::value...>
#                    >::value;
# };
_define_template_with_single_specialization(name='TypeSetEquals',
                                            main_definition_args=[_type_arg_decl('S1'), _type_arg_decl('S2')],
                                            specialization_args=[_variadic_type_arg_decl('Ts'),
                                                                 _variadic_type_arg_decl('Us')],
                                            patterns=[_type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))),
                                                      _type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Us')))],
                                            value_expr=_is_same(lhs=_bool_list_of(ir0.VariadicTypeExpansion(_is_in_type_set(_type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))),
                                                                                                                            _local_variadic_type('Us'))),
                                                                                  ir0.VariadicTypeExpansion(_is_in_type_set(_type_list_of(ir0.VariadicTypeExpansion(_local_variadic_type('Us'))),
                                                                                                                            _local_variadic_type('Ts')))),
                                                                rhs=_bool_list_of(ir0.VariadicTypeExpansion(_always_true_from_type(_local_variadic_type('Us'))),
                                                                                  ir0.VariadicTypeExpansion(_always_true_from_type(_local_variadic_type('Ts'))))))


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
                                                                                _local_type('F'),
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
                                                                          GlobalLiterals.ADD_TO_BOOL_SET,
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
                                                                                 _local_type('F'),
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
                                                                           GlobalLiterals.ADD_TO_INT64_SET,
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
                                                                                _local_type('F'),
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
                                                                          GlobalLiterals.ADD_TO_TYPE_SET,
                                                                          ir0.VariadicTypeExpansion(_local_variadic_type('Ts'))))
