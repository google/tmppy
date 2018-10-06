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

    IS_IN_BOOL_LIST = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='IsInBoolList',
                                                                  args=[_bool_arg_type(), _type_arg_type()],
                                                                  is_metafunction_that_may_return_error=False,
                                                                  may_be_alias=False)

    IS_IN_INT64_LIST = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='IsInInt64List',
                                                                   args=[_int64_arg_type(), _type_arg_type()],
                                                                   is_metafunction_that_may_return_error=False,
                                                                   may_be_alias=False)

    IS_IN_TYPE_LIST = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='IsInTypeList',
                                                                  args=[_type_arg_type(), _type_arg_type()],
                                                                  is_metafunction_that_may_return_error=False,
                                                                  may_be_alias=False)

def select1st_literal(lhs_type: ir0.ExprType, rhs_type: ir0.ExprType):
    kind_to_string = {
        ir0.ExprKind.BOOL: 'Bool',
        ir0.ExprKind.INT64: 'Int64',
        ir0.ExprKind.TYPE: 'Type',
    }
    return ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type='Select1st%s%s' % (kind_to_string[lhs_type.kind],
                                                                                   kind_to_string[rhs_type.kind]),
                                                       args=[ir0.TemplateArgType(expr_type=lhs_type, is_variadic=False),
                                                             ir0.TemplateArgType(expr_type=rhs_type, is_variadic=False)],
                                                       is_metafunction_that_may_return_error=False,
                                                       may_be_alias=False)


GLOBAL_LITERALS_BY_NAME = {x.cpp_type: x
                           for x in GlobalLiterals.__dict__.values()
                           if isinstance(x, ir0.AtomicTypeLiteral)}
