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

import itertools
import re
import _py2tmp.lowir as lowir
import _py2tmp.ir as ir
import _py2tmp.utils as utils
from typing import List, Tuple, Optional, Iterator, Union, Callable, Dict

class Writer:
    def new_id(self) -> str: ...  # pragma: no cover

    def write(self, elem: Union[lowir.TemplateDefn, lowir.StaticAssert, lowir.ConstantDef, lowir.Typedef]): ...  # pragma: no cover

    def get_is_instance_template_name_for_error(self, error_name: str) -> str: ...  # pragma: no cover

class ToplevelWriter(Writer):
    def __init__(self, identifier_generator: Iterator[str]):
        self.identifier_generator = identifier_generator
        self.elems = []  # type: List[Union[lowir.TemplateDefn, lowir.StaticAssert, lowir.ConstantDef, lowir.Typedef]]
        self.holder_template_name_for_error = dict()  # type: Dict[str, str]
        self.is_instance_template_name_for_error = dict()  # type: Dict[str, str]

    def new_id(self):
        return next(self.identifier_generator)

    def write(self, elem: Union[lowir.TemplateDefn, lowir.StaticAssert, lowir.ConstantDef, lowir.Typedef]):
        self.elems.append(elem)

    def set_holder_template_name_for_error(self,
                                           error_name: str,
                                           error_holder_name: str):
        self.holder_template_name_for_error[error_name] = error_holder_name

    def get_holder_template_name_for_error(self, error_name: str):
        return self.holder_template_name_for_error[error_name]

    def set_is_instance_template_name_for_error(self,
                                                error_name: str,
                                                is_instance_template_name: str):
        self.is_instance_template_name_for_error[error_name] = is_instance_template_name

    def get_is_instance_template_name_for_error(self, error_name: str):
        return self.is_instance_template_name_for_error[error_name]

class TemplateBodyWriter(Writer):
    def __init__(self,
                 writer: Writer,
                 parent_arbitrary_arg: lowir.TemplateArgDecl,
                 parent_return_type: Optional[lowir.ExprType]):
        self.writer = writer
        self.elems = []  # type: List[Union[lowir.StaticAssert, lowir.ConstantDef, lowir.Typedef]]
        self.parent_arbitrary_arg = parent_arbitrary_arg
        self.parent_return_type = parent_return_type
        self.result_body_elements_written = False

    def new_id(self):
        return self.writer.new_id()

    def write(self, elem: Union[lowir.TemplateDefn, lowir.StaticAssert, lowir.ConstantDef, lowir.Typedef]):
        if isinstance(elem, lowir.TemplateDefn):
            self.writer.write(elem)
        else:
            self.elems.append(elem)

    def write_result_body_elements(self,
                                   result_expr: Optional[lowir.Expr],
                                   error_expr: Optional[lowir.Expr]):
        assert self.parent_return_type
        assert result_expr or error_expr
        if error_expr:
            assert error_expr.kind == lowir.ExprKind.TYPE

        if self.result_body_elements_written:
            # If there are multiple "return statements" in a single specialization only the first one counts.
            return
        self.result_body_elements_written = True

        if self.parent_return_type.kind == lowir.ExprKind.BOOL:
            self.write(lowir.ConstantDef(name='value',
                                         expr=result_expr or lowir.Literal(value=True, kind=lowir.ExprKind.BOOL),
                                         type=self.parent_return_type))
        elif self.parent_return_type.kind == lowir.ExprKind.INT64:
            self.write(lowir.ConstantDef(name='value',
                                         expr=result_expr or lowir.Literal(value=0, kind=lowir.ExprKind.INT64),
                                         type=self.parent_return_type))
        else:
            self.write(lowir.Typedef(name='type',
                                     expr=result_expr or lowir.TypeLiteral.for_nonlocal_type('void'),
                                     type=self.parent_return_type if result_expr else lowir.TypeType()))

        if error_expr is None:
            error_expr = lowir.TypeLiteral.for_nonlocal_type('void')
        self.write(lowir.Typedef(name='error',
                                 expr=error_expr,
                                 type=lowir.TypeType()))

    def create_sibling_writer(self,
                              parent_arbitrary_arg: lowir.TemplateArgDecl,
                              parent_return_type: lowir.ExprType):
        return TemplateBodyWriter(self.writer,
                                  parent_arbitrary_arg=parent_arbitrary_arg,
                                  parent_return_type=parent_return_type)

    def get_is_instance_template_name_for_error(self, error_name: str):
        return self.writer.get_is_instance_template_name_for_error(error_name)

def type_to_low_ir(type: ir.ExprType):
    if isinstance(type, ir.BoolType):
        return lowir.BoolType()
    elif isinstance(type, ir.IntType):
        return lowir.Int64Type()
    elif isinstance(type, ir.TypeType):
        return lowir.TypeType()
    elif isinstance(type, ir.CustomType):
        return lowir.TypeType()
    elif isinstance(type, ir.ListType):
        return lowir.TypeType()
    elif isinstance(type, ir.ErrorOrVoidType):
        return lowir.TypeType()
    elif isinstance(type, ir.FunctionType):
        return function_type_to_low_ir(type)
    elif isinstance(type, ir.BottomType):
        return lowir.TypeType()
    else:
        raise NotImplementedError('Unexpected type: %s' % str(type.__class__))

def function_type_to_low_ir(fun_type: ir.FunctionType):
    return lowir.TemplateType(argtypes=[type_to_low_ir(arg)
                                        for arg in fun_type.argtypes])

def expr_to_low_ir(expr: ir.Expr, writer: Writer) -> Tuple[Optional[lowir.Expr], Optional[lowir.Expr]]:
    if isinstance(expr, ir.VarReference):
        return var_reference_to_low_ir(expr), None
    elif isinstance(expr, ir.MatchExpr):
        assert isinstance(writer, TemplateBodyWriter)
        return match_expr_to_low_ir(expr, writer)
    elif isinstance(expr, ir.BoolLiteral):
        return bool_literal_to_low_ir(expr)
    elif isinstance(expr, ir.IntLiteral):
        return int_literal_to_low_ir(expr)
    elif isinstance(expr, ir.TypeLiteral):
        return type_literal_to_low_ir(expr)
    elif isinstance(expr, ir.ListExpr):
        return list_expr_to_low_ir(expr)
    elif isinstance(expr, ir.FunctionCall):
        return function_call_to_low_ir(expr, writer)
    elif isinstance(expr, ir.EqualityComparison):
        return equality_comparison_to_low_ir(expr, writer)
    elif isinstance(expr, ir.AttributeAccessExpr):
        return attribute_access_expr_to_low_ir(expr)
    elif isinstance(expr, ir.NotExpr):
        return not_expr_to_low_ir(expr)
    elif isinstance(expr, ir.UnaryMinusExpr):
        return unary_minus_expr_to_low_ir(expr)
    elif isinstance(expr, ir.IntComparisonExpr):
        return int_comparison_expr_to_low_ir(expr)
    elif isinstance(expr, ir.IntBinaryOpExpr):
        return int_binary_op_expr_to_low_ir(expr)
    elif isinstance(expr, ir.ListConcatExpr):
        return list_concat_expr_to_low_ir(expr, writer)
    elif isinstance(expr, ir.IsInstanceExpr):
        return is_instance_expr_to_low_ir(expr, writer)
    elif isinstance(expr, ir.SafeUncheckedCast):
        return safe_unchecked_cast_expr_to_low_ir(expr), None
    elif isinstance(expr, ir.ListComprehensionExpr):
        return list_comprehension_expr_to_low_ir(expr, writer)
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def function_arg_decl_to_low_ir(decl: ir.FunctionArgDecl):
    return lowir.TemplateArgDecl(type=type_to_low_ir(decl.type),
                                 name=decl.name)

def var_reference_to_low_ir(var: ir.VarReference):
    if var.is_global_function:
        assert type_to_low_ir(var.type).kind == lowir.ExprKind.TEMPLATE
        return lowir.TypeLiteral.for_nonlocal_template(cpp_type=var.name,
                                                       is_metafunction_that_may_return_error=True)
    else:
        return lowir.TypeLiteral.for_local(cpp_type=var.name,
                                           type=type_to_low_ir(var.type))

def _create_metafunction_call(template_expr: lowir.Expr,
                              args: List[lowir.Expr],
                              arg_types: List[lowir.ExprType],
                              member_kind: lowir.ExprKind,
                              writer: Writer):
    assert template_expr.kind == lowir.ExprKind.TEMPLATE
    if member_kind in (lowir.ExprKind.BOOL, lowir.ExprKind.INT64):
        member_name = 'value'
    else:
        member_name = 'type'
    template_instantiation_expr = lowir.TemplateInstantiation(template_expr=template_expr,
                                                              args=args,
                                                              arg_types=arg_types,
                                                              instantiation_might_trigger_static_asserts=True)
    if isinstance(writer, ToplevelWriter) and (not isinstance(template_expr, lowir.TypeLiteral)
                                               or template_expr.is_metafunction_that_may_return_error):
        # using T = CheckIfError<F<x, y>::error>::type;
        check_if_error_template_instantiation_expr = lowir.TemplateInstantiation(template_expr=lowir.TypeLiteral.for_nonlocal_template(cpp_type='CheckIfError',
                                                                                                                                       is_metafunction_that_may_return_error=False),
                                                                                 args=[lowir.ClassMemberAccess(class_type_expr=template_instantiation_expr,
                                                                                                               member_name='error',
                                                                                                               member_kind=lowir.ExprKind.TYPE)],
                                                                                 arg_types=[lowir.TypeType()],
                                                                                 instantiation_might_trigger_static_asserts=True)
        writer.write(lowir.Typedef(name=writer.new_id(),
                                   expr=lowir.ClassMemberAccess(class_type_expr=check_if_error_template_instantiation_expr,
                                                                member_name='type',
                                                                member_kind=lowir.ExprKind.TYPE),
                                   type=lowir.TypeType()))
    result_expr = lowir.ClassMemberAccess(class_type_expr=template_instantiation_expr,
                                          member_name=member_name,
                                          member_kind=member_kind)
    error_expr = lowir.ClassMemberAccess(class_type_expr=template_instantiation_expr,
                                         member_name='error',
                                         member_kind=lowir.ExprKind.TYPE)
    return result_expr, error_expr

def _create_metafunction_specialization(args: List[lowir.TemplateArgDecl],
                                        patterns: Optional[List[lowir.TemplateArgPatternLiteral]],
                                        body: List[Union[lowir.StaticAssert, lowir.ConstantDef, lowir.Typedef]]):

    # patterns==None means that this is not actually a specialization (it's the main definition).
    # Instead, patterns==[] means that this is a full specialization.
    if patterns is not None:
        patterns_set = set(pattern_literal.cxx_pattern
                           for pattern_literal in patterns)
        args_set = {arg.name for arg in args}
        if args_set == patterns_set:
            # This specializes nothing, so it's the main definition. Keeping the explicit patterns would cause
            # C++ compilation errors, so we remove them.
            patterns = None

    return lowir.TemplateSpecialization(args=args, patterns=patterns, body=body)

def match_expr_to_low_ir(match_expr: ir.MatchExpr,
                         writer: TemplateBodyWriter):
    forwarded_args = []  # type: List[ir.VarReference]
    forwarded_args_names = set()
    for match_case in match_expr.match_cases:
        local_vars = set(match_case.matched_var_names)
        for var in match_case.expr.get_free_variables():
            if var.name not in local_vars and var.name not in forwarded_args_names:
                forwarded_args_names.add(var.name)
                forwarded_args.append(var)

    if forwarded_args or all(match_case.matched_var_names
                             for match_case in match_expr.match_cases):
        forwarded_args_decls = [lowir.TemplateArgDecl(type=type_to_low_ir(var_ref.type), name=var_ref.name)
                                for var_ref in forwarded_args]
        forwarded_args_exprs = [lowir.TypeLiteral.for_local(cpp_type=var_ref.name,
                                                            type=type_to_low_ir(var_ref.type))
                                for var_ref in forwarded_args]
        forwarded_args_patterns = [lowir.TemplateArgPatternLiteral(cxx_pattern=var_ref.name)
                                   for var_ref in forwarded_args]
        forwarded_args_types = [type_to_low_ir(var_ref.type)
                                for var_ref in forwarded_args]
    else:
        # We must add a dummy parameter so that the specialization isn't a full specialization.
        dummy_param_name = writer.new_id()
        forwarded_args_decls = [lowir.TemplateArgDecl(type=lowir.TypeType(),
                                                      name=dummy_param_name)]
        forwarded_args_exprs = [lowir.TypeLiteral.for_nonlocal_type('void')]
        forwarded_args_patterns = [lowir.TemplateArgPatternLiteral(cxx_pattern=dummy_param_name)]
        forwarded_args_types = [lowir.TypeType()]

    matched_vars = [var_reference_to_low_ir(var)
                    for var in match_expr.matched_vars]
    matched_vars_types = [type_to_low_ir(var.type)
                          for var in match_expr.matched_vars]

    main_definition = None
    specializations = []
    for match_case in match_expr.match_cases:
        specialization_arg_decls = forwarded_args_decls + [lowir.TemplateArgDecl(type=lowir.TypeType(), name=arg_name)
                                                           for arg_name in match_case.matched_var_names]

        specialization_patterns = forwarded_args_patterns + [lowir.TemplateArgPatternLiteral(cxx_pattern=pattern)
                                                             for pattern in match_case.type_patterns]

        match_case_writer = TemplateBodyWriter(writer,
                                               parent_arbitrary_arg=writer.parent_arbitrary_arg,
                                               parent_return_type=type_to_low_ir(match_case.expr.type))

        lowir_expr, error_expr = expr_to_low_ir(match_case.expr, match_case_writer)
        match_case_writer.write_result_body_elements(result_expr=lowir_expr,
                                                     error_expr=error_expr)

        if match_case.is_main_definition():
            assert not main_definition
            main_definition = _create_metafunction_specialization(args=specialization_arg_decls,
                                                                  patterns=None,
                                                                  body=match_case_writer.elems)
        else:
            specializations.append(_create_metafunction_specialization(args=specialization_arg_decls,
                                                                       patterns=specialization_patterns,
                                                                       body=match_case_writer.elems))

    args_decls = forwarded_args_decls + [lowir.TemplateArgDecl(type=lowir.TypeType(), name='')
                                         for _ in match_expr.matched_vars]

    args_exprs = forwarded_args_exprs + matched_vars
    arg_types = forwarded_args_types + matched_vars_types

    helper_function = lowir.TemplateDefn(args=args_decls,
                                         main_definition=main_definition,
                                         specializations=specializations,
                                         name=writer.new_id())
    writer.write(helper_function)

    helper_function_reference = lowir.TypeLiteral.for_nonlocal_template(cpp_type=helper_function.name,
                                                                        is_metafunction_that_may_return_error=True)
    return _create_metafunction_call(template_expr=helper_function_reference,
                                     args=args_exprs,
                                     arg_types=arg_types,
                                     member_kind=type_to_low_ir(match_expr.type).kind,
                                     writer=writer)

def bool_literal_to_low_ir(literal: ir.BoolLiteral):
    return lowir.Literal(value=literal.value, kind=lowir.ExprKind.BOOL), None

def int_literal_to_low_ir(literal: ir.IntLiteral):
    return lowir.Literal(value=literal.value, kind=lowir.ExprKind.INT64), None

def type_literal_to_low_ir(literal: ir.TypeLiteral):
    kind = type_to_low_ir(literal.type).kind
    replacements = dict()
    for arg_name, arg_expr in sorted(literal.args.items(), key=lambda item: item[0]):
        arg_literal = var_reference_to_low_ir(arg_expr)
        assert isinstance(arg_literal.type, lowir.TypeType)
        assert arg_literal.kind == lowir.ExprKind.TYPE
        assert not arg_literal.is_metafunction_that_may_return_error
        replacements[arg_name] = arg_literal.cpp_type
    expr = lowir.TypeLiteral.for_nonlocal(cpp_type=utils.replace_identifiers(literal.cpp_type, replacements),
                                          kind=kind,
                                          is_metafunction_that_may_return_error=(kind == lowir.ExprKind.TEMPLATE))
    return expr, None

def list_expr_to_low_ir(list_expr: ir.ListExpr):
    exprs = [var_reference_to_low_ir(elem)
             for elem in list_expr.elems]

    elem_kind = type_to_low_ir(list_expr.elem_type).kind
    if elem_kind == lowir.ExprKind.BOOL:
        list_template = lowir.TypeLiteral.for_nonlocal_template('BoolList', is_metafunction_that_may_return_error=False)
    elif elem_kind == lowir.ExprKind.INT64:
        list_template = lowir.TypeLiteral.for_nonlocal_template('Int64List', is_metafunction_that_may_return_error=False)
    elif elem_kind == lowir.ExprKind.TYPE:
        list_template = lowir.TypeLiteral.for_nonlocal_template('List', is_metafunction_that_may_return_error=False)
    else:
        raise NotImplementedError('elem_kind: %s' % elem_kind)

    expr = lowir.TemplateInstantiation(template_expr=list_template,
                                       arg_types=[],
                                       instantiation_might_trigger_static_asserts=False,
                                       args=exprs)
    return expr, None

def function_call_to_low_ir(call_expr: ir.FunctionCall, writer: Writer):
    fun = var_reference_to_low_ir(call_expr.fun)
    args = [var_reference_to_low_ir(arg)
            for arg in call_expr.args]
    arg_types = [type_to_low_ir(arg.type)
                 for arg in call_expr.args]
    if not args:
        args = [lowir.TypeLiteral.for_nonlocal_type('void')]
        arg_types = [lowir.TypeType()]

    assert isinstance(call_expr.fun.type, ir.FunctionType)
    return _create_metafunction_call(template_expr=fun,
                                     args=args,
                                     arg_types=arg_types,
                                     member_kind=type_to_low_ir(call_expr.fun.type.returns).kind,
                                     writer=writer)

def equality_comparison_to_low_ir(comparison_expr: ir.EqualityComparison, writer: Writer):
    lhs = var_reference_to_low_ir(comparison_expr.lhs)
    rhs = var_reference_to_low_ir(comparison_expr.rhs)
    if lhs.kind == lowir.ExprKind.TYPE:
        std_is_same = lowir.TypeLiteral.for_nonlocal_template(cpp_type='std::is_same',
                                                              is_metafunction_that_may_return_error=False)
        comparison_expr, comparison_error_expr = _create_metafunction_call(template_expr=std_is_same,
                                                                           args=[lhs, rhs],
                                                                           arg_types=[type_to_low_ir(comparison_expr.lhs.type),
                                                                                      type_to_low_ir(comparison_expr.rhs.type)],
                                                                           member_kind=lowir.ExprKind.BOOL,
                                                                           writer=writer)
    else:
        comparison_expr = lowir.ComparisonExpr(lhs=lhs, rhs=rhs, op='==')
        comparison_error_expr = None
    return comparison_expr, comparison_error_expr

def attribute_access_expr_to_low_ir(attribute_access_expr: ir.AttributeAccessExpr):
    class_expr = var_reference_to_low_ir(attribute_access_expr.var)
    assert class_expr.kind == lowir.ExprKind.TYPE
    expr = lowir.ClassMemberAccess(class_type_expr=class_expr,
                                   member_name=attribute_access_expr.attribute_name,
                                   member_kind=type_to_low_ir(attribute_access_expr.type).kind)
    return expr, None

def not_expr_to_low_ir(not_expr: ir.NotExpr):
    return lowir.NotExpr(expr=var_reference_to_low_ir(not_expr.var)), None

def unary_minus_expr_to_low_ir(expr: ir.UnaryMinusExpr):
    return lowir.UnaryMinusExpr(expr=var_reference_to_low_ir(expr.var)), None

def int_comparison_expr_to_low_ir(expr: ir.IntComparisonExpr):
    lhs = var_reference_to_low_ir(expr.lhs)
    rhs = var_reference_to_low_ir(expr.rhs)
    return lowir.ComparisonExpr(lhs=lhs, rhs=rhs, op=expr.op), None

def int_binary_op_expr_to_low_ir(expr: ir.IntBinaryOpExpr):
    lhs = var_reference_to_low_ir(expr.lhs)
    rhs = var_reference_to_low_ir(expr.rhs)
    cpp_op = {
        '+': '+',
        '-': '-',
        '*': '*',
        '//': '/',
        '%': '%',
    }[expr.op]
    return lowir.Int64BinaryOpExpr(lhs=lhs, rhs=rhs, op=cpp_op), None

def list_concat_expr_to_low_ir(expr: ir.ListConcatExpr, writer: Writer):
    lhs = var_reference_to_low_ir(expr.lhs)
    rhs = var_reference_to_low_ir(expr.rhs)
    assert isinstance(expr.type, ir.ListType)
    elem_kind = type_to_low_ir(expr.type.elem_type).kind
    type = type_to_low_ir(expr.type)
    list_concat_cpp_type = {
        lowir.ExprKind.BOOL: 'BoolListConcat',
        lowir.ExprKind.INT64: 'Int64ListConcat',
        lowir.ExprKind.TYPE: 'TypeListConcat',
    }[elem_kind]
    return _create_metafunction_call(template_expr=lowir.TypeLiteral.for_nonlocal_template(cpp_type=list_concat_cpp_type,
                                                                                           is_metafunction_that_may_return_error=False),
                                     args=[lhs, rhs],
                                     arg_types=[type, type],
                                     member_kind=type.kind,
                                     writer=writer)

def is_instance_expr_to_low_ir(expr: ir.IsInstanceExpr, writer: Writer):
    is_instance_of_type_template = lowir.TypeLiteral.for_nonlocal_template(cpp_type=writer.get_is_instance_template_name_for_error(expr.checked_type.name),
                                                                           is_metafunction_that_may_return_error=False)
    return _create_metafunction_call(template_expr=is_instance_of_type_template,
                                     args=[var_reference_to_low_ir(expr.var)],
                                     arg_types=[type_to_low_ir(expr.var.type)],
                                     member_kind=lowir.ExprKind.BOOL,
                                     writer=writer)

def safe_unchecked_cast_expr_to_low_ir(expr: ir.SafeUncheckedCast):
    assert type_to_low_ir(expr.var.type).kind == type_to_low_ir(expr.type).kind
    return var_reference_to_low_ir(ir.VarReference(type=expr.type,
                                                   name=expr.var.name,
                                                   is_global_function=expr.var.is_global_function,
                                                   is_function_that_may_throw=expr.var.is_function_that_may_throw))

def list_comprehension_expr_to_low_ir(expr: ir.ListComprehensionExpr, writer: Writer):
    captured_vars = [var
                     for var in ir.get_unique_free_variables_in_stmts([ir.ReturnStmt(result=expr.result_elem_expr,
                                                                                     error=None)])
                     if var.name != expr.loop_var.name]

    # TODO: introduce unchecked versions of these and use them when we know that the list comprehension can't result in
    # an error.
    transform_metafunction_name_for_kinds = {
        (lowir.ExprKind.BOOL, lowir.ExprKind.BOOL): 'TransformBoolListToBoolList',
        (lowir.ExprKind.BOOL, lowir.ExprKind.INT64): 'TransformBoolListToInt64List',
        (lowir.ExprKind.BOOL, lowir.ExprKind.TYPE): 'TransformBoolListToTypeList',
        (lowir.ExprKind.INT64, lowir.ExprKind.BOOL): 'TransformInt64ListToBoolList',
        (lowir.ExprKind.INT64, lowir.ExprKind.INT64): 'TransformInt64ListToInt64List',
        (lowir.ExprKind.INT64, lowir.ExprKind.TYPE): 'TransformInt64ListToTypeList',
        (lowir.ExprKind.TYPE, lowir.ExprKind.BOOL): 'TransformTypeListToBoolList',
        (lowir.ExprKind.TYPE, lowir.ExprKind.INT64): 'TransformTypeListToInt64List',
        (lowir.ExprKind.TYPE, lowir.ExprKind.TYPE): 'TransformTypeListToTypeList',
    }

    x_type = type_to_low_ir(expr.loop_var.type)
    result_elem_type = type_to_low_ir(expr.result_elem_expr.type)

    template_arg_decl = lowir.TemplateArgDecl(type=x_type,
                                              name=expr.loop_var.name)
    helper_template_body_writer = TemplateBodyWriter(writer,
                                                     parent_arbitrary_arg=template_arg_decl,
                                                     parent_return_type=result_elem_type)
    result_expr, error_expr = function_call_to_low_ir(expr.result_elem_expr, helper_template_body_writer)
    helper_template_body_writer.write_result_body_elements(result_expr=result_expr, error_expr=error_expr)
    helper_template_defn = lowir.TemplateDefn(name=writer.new_id(),
                                              specializations=[],
                                              args=[template_arg_decl],
                                              main_definition=lowir.TemplateSpecialization(args=[template_arg_decl],
                                                                                           patterns=None,
                                                                                           body=helper_template_body_writer.elems))

    if not captured_vars:
        # z = [f(x)
        #      for x in l]
        #
        # Becomes:
        #
        # template <typename X>
        # struct Helper {
        #   using type = typename f<X>::type;
        # };
        #
        # using Z = typename TransformTypeListToTypeList<L, Helper>::type;

        writer.write(helper_template_defn)
        return _create_metafunction_call(template_expr=lowir.TypeLiteral.for_nonlocal_template(cpp_type=transform_metafunction_name_for_kinds[(x_type.kind, result_elem_type.kind)],
                                                                                               is_metafunction_that_may_return_error=expr.result_elem_expr.fun.is_function_that_may_throw),
                                         args=[var_reference_to_low_ir(expr.list_var),
                                               lowir.TypeLiteral.for_nonlocal_template(cpp_type=helper_template_defn.name,
                                                                                       is_metafunction_that_may_return_error=expr.result_elem_expr.fun.is_function_that_may_throw)],
                                         arg_types=[type_to_low_ir(expr.list_var.type),
                                                    lowir.TemplateType(argtypes=[x_type])],
                                         member_kind=type_to_low_ir(expr.type).kind,
                                         writer=writer)
    else:
        # z = [f(y, x, z)
        #      for x in l]
        #
        # Becomes:
        #
        # template <typename Y, typename Z>
        # struct HelperWrapper {
        #   template <typename X>
        #   struct Helper {
        #     using type = typename f<Y, X, Z>::type;
        #   };
        # };
        #
        # using Z = typename TransformTypeList<L, HelperWrapper<Y, Z>::Helper>::type;

        captured_vars_as_template_args = [lowir.TemplateArgDecl(type=type_to_low_ir(var.type),
                                                                name=var.name)
                                          for var in captured_vars]
        helper_wrapper_template_defn = lowir.TemplateDefn(name=writer.new_id(),
                                                          specializations=[],
                                                          args=captured_vars_as_template_args,
                                                          main_definition=lowir.TemplateSpecialization(args=captured_vars_as_template_args,
                                                                                                       patterns=None,
                                                                                                       body=[helper_template_defn]))

        writer.write(helper_wrapper_template_defn)
        helper_template_expr = lowir.ClassMemberAccess(class_type_expr=lowir.TemplateInstantiation(template_expr=lowir.TypeLiteral.for_nonlocal_template(cpp_type=helper_wrapper_template_defn.name,
                                                                                                                                                         is_metafunction_that_may_return_error=False),
                                                                                                   args=[var_reference_to_low_ir(var)
                                                                                                         for var in captured_vars],
                                                                                                   arg_types=[type_to_low_ir(var.type)
                                                                                                              for var in captured_vars],
                                                                                                   instantiation_might_trigger_static_asserts=True),
                                                       member_name=helper_template_defn.name,
                                                       member_kind=lowir.ExprKind.TEMPLATE)
        return _create_metafunction_call(template_expr=lowir.TypeLiteral.for_nonlocal_template(cpp_type=transform_metafunction_name_for_kinds[(x_type.kind, result_elem_type.kind)],
                                                                                               is_metafunction_that_may_return_error=expr.result_elem_expr.fun.is_function_that_may_throw),
                                         args=[var_reference_to_low_ir(expr.list_var),
                                               helper_template_expr],
                                         arg_types=[type_to_low_ir(expr.list_var.type),
                                                    lowir.TemplateType(argtypes=[x_type])],
                                         member_kind=type_to_low_ir(expr.type).kind,
                                         writer=writer)

def assert_to_low_ir(assert_stmt: ir.Assert, writer: Writer):
    expr = var_reference_to_low_ir(assert_stmt.var)
    writer.write(lowir.StaticAssert(expr=expr, message=assert_stmt.message))

def assignment_to_low_ir(assignment: ir.Assignment, writer: Writer):
    lhs = var_reference_to_low_ir(assignment.lhs)
    rhs, rhs_error = expr_to_low_ir(assignment.rhs, writer)

    low_ir_type = type_to_low_ir(assignment.lhs.type)
    if low_ir_type.kind in (lowir.ExprKind.BOOL, lowir.ExprKind.INT64):
        writer.write(lowir.ConstantDef(name=lhs.cpp_type, expr=rhs, type=low_ir_type))
    else:
        writer.write(lowir.Typedef(name=lhs.cpp_type, expr=rhs, type=low_ir_type))

    if assignment.lhs2:
        lhs2 = var_reference_to_low_ir(assignment.lhs2)
        assert rhs_error.kind == lowir.ExprKind.TYPE
        writer.write(lowir.Typedef(name=lhs2.cpp_type, expr=rhs_error, type=lowir.TypeType()))

def custom_type_defn_to_low_ir(custom_type: ir.CustomType, writer: ToplevelWriter):
    # For example, from the following custom type:
    #
    # class MyType:
    #    def __init__(self, x: bool, y: Type):
    #        self.x
    #        self.y
    #
    # We'll generate:
    #
    # template <bool x1, typename y1>
    # struct MyTypeHolder {
    #     static constexpr bool x = x1;
    #     using y = y1;
    # };
    #
    # template <bool x1, typename y1>
    # struct MyType {
    #     using type = MyTypeHolder<x1, y1>;
    #     using error = void;
    # };
    #
    # With different names for the helper identifiers, of course. Only MyType, x and y retain their name.

    holder_template_id = writer.new_id()

    arg_types = []
    arg_decls = []
    for arg in custom_type.arg_types:
        forwarded_arg_name = writer.new_id()
        arg_type = type_to_low_ir(arg.type)
        arg_types.append(arg_type)
        arg_decls.append(lowir.TemplateArgDecl(type=arg_type,
                                               name=forwarded_arg_name))

    holder_template_writer = TemplateBodyWriter(writer,
                                                parent_arbitrary_arg=_select_arbitrary_parent_arg(arg_decls),
                                                parent_return_type=None)
    holder_template_instantiation_args = []
    for arg, arg_decl in zip(custom_type.arg_types, arg_decls):
        lhs_var = ir.VarReference(type=arg.type,
                                  name=arg.name,
                                  is_global_function=False,
                                  is_function_that_may_throw=isinstance(arg.type, ir.FunctionType))
        rhs_var = ir.VarReference(type=arg.type,
                                  name=arg_decl.name,
                                  is_global_function=False,
                                  is_function_that_may_throw=isinstance(arg.type, ir.FunctionType))
        assignment_to_low_ir(ir.Assignment(lhs=lhs_var, rhs=rhs_var),
                             holder_template_writer)
        holder_template_instantiation_args.append(var_reference_to_low_ir(rhs_var))

    holder_template = lowir.TemplateDefn(name=holder_template_id,
                                         args=arg_decls,
                                         specializations=[],
                                         main_definition=lowir.TemplateSpecialization(args=arg_decls,
                                                                                      patterns=None,
                                                                                      body=holder_template_writer.elems))
    writer.write(holder_template)

    constructor_fn_typedef = lowir.Typedef(name='type',
                                           type=lowir.TypeType(),
                                           expr=lowir.TemplateInstantiation(template_expr=lowir.TypeLiteral.for_nonlocal_template(cpp_type=holder_template_id,
                                                                                                                                  is_metafunction_that_may_return_error=False),
                                                                            args=holder_template_instantiation_args,
                                                                            arg_types=arg_types,
                                                                            instantiation_might_trigger_static_asserts=False))
    constructor_fn_error_typedef = lowir.Typedef(name='error',
                                                 type=lowir.TypeType(),
                                                 expr=lowir.TypeLiteral.for_nonlocal_type('void'))
    constructor_fn = lowir.TemplateDefn(name=custom_type.name,
                                        args=arg_decls,
                                        specializations=[],
                                        main_definition=lowir.TemplateSpecialization(args=arg_decls,
                                                                                     patterns=None,
                                                                                     body=[constructor_fn_typedef,
                                                                                           constructor_fn_error_typedef]))
    writer.write(constructor_fn)

    writer.set_holder_template_name_for_error(custom_type.name, holder_template_id)

    is_instance_template = lowir.TemplateDefn(name=writer.new_id(),
                                              args=[lowir.TemplateArgDecl(type=lowir.TypeType())],
                                              main_definition=lowir.TemplateSpecialization(args=[lowir.TemplateArgDecl(type=lowir.TypeType())],
                                                                                           patterns=None,
                                                                                           body=[lowir.ConstantDef(name='value',
                                                                                                                   expr=lowir.Literal(value=False, kind=lowir.ExprKind.BOOL),
                                                                                                                   type=lowir.BoolType())]),
                                              specializations=[lowir.TemplateSpecialization(args=[lowir.TemplateArgDecl(type=type_to_low_ir(arg.type), name=arg.name)
                                                                                                  for arg in custom_type.arg_types],
                                                                                            patterns=[lowir.TemplateArgPatternLiteral('%s<%s>' % (
                                                                                                holder_template_id,
                                                                                                ', '.join(arg.name
                                                                                                          for arg in custom_type.arg_types)))],
                                                                                            body=[lowir.ConstantDef(name='value',
                                                                                                                    expr=lowir.Literal(value=True, kind=lowir.ExprKind.BOOL),
                                                                                                                    type=lowir.BoolType())])])

    writer.write(is_instance_template)
    writer.set_is_instance_template_name_for_error(custom_type.name, is_instance_template.name)

def return_stmt_to_low_ir(return_stmt: ir.ReturnStmt, writer: TemplateBodyWriter):
    if return_stmt.result:
        result_var = var_reference_to_low_ir(return_stmt.result)
    else:
        result_var = None
    if return_stmt.error:
        error_var = var_reference_to_low_ir(return_stmt.error)
    else:
        error_var = None

    writer.write_result_body_elements(result_expr=result_var,
                                      error_expr=error_var)

def _get_free_vars_in_elements(elements: List[lowir.TemplateBodyElement]):
    free_var_names = set()
    bound_var_names = set()
    free_vars = []
    for element in elements:
        if isinstance(element, lowir.StaticAssert) or isinstance(element, lowir.ConstantDef) or isinstance(element, lowir.Typedef):
            for var in element.expr.get_free_vars():
                if var.cpp_type not in bound_var_names and var.cpp_type not in free_var_names:
                    free_var_names.add(var.cpp_type)
                    free_vars.append(var)
        else:
            raise NotImplementedError('Unexpected element type: %s' % str(element.__class__))
        if isinstance(element, lowir.ConstantDef) or isinstance(element, lowir.Typedef):
            bound_var_names.add(element.name)
    return free_vars

def if_stmt_to_low_ir(if_stmt: ir.IfStmt,
                      then_stmts: List[ir.Stmt],
                      write_continuation_fun_call: Optional[Callable[[TemplateBodyWriter], None]],
                      writer: TemplateBodyWriter):

    cond_expr = var_reference_to_low_ir(if_stmt.cond)

    if then_stmts:
        then_writer = writer.create_sibling_writer(writer.parent_arbitrary_arg, writer.parent_return_type)
        stmts_to_low_ir(then_stmts, write_continuation_fun_call, then_writer)

        forwarded_vars = _get_free_vars_in_elements(then_writer.elems)

        forwarded_vars_args = [lowir.TemplateArgDecl(type=var.type, name=var.cpp_type)
                               for var in forwarded_vars]
        forwarded_vars_patterns = [lowir.TemplateArgPatternLiteral(cxx_pattern=var.cpp_type)
                                   for var in forwarded_vars]
        forwarded_vars_exprs = [lowir.TypeLiteral.for_local(cpp_type=var.cpp_type,
                                                            type=var.type)
                                for var in forwarded_vars]
        forwarded_vars_types = [var.type
                                for var in forwarded_vars]
        if not forwarded_vars:
            # We need to add a dummy template parameter, otherwise the "then" template will have no parameters and the C++
            # compiler will eagerly evaluate its body, even if it would never be instantiated (triggering e.g. any
            # assertions in that code).
            forwarded_vars_args.append(then_writer.parent_arbitrary_arg)
            forwarded_vars_patterns.append(lowir.TemplateArgPatternLiteral(cxx_pattern=then_writer.parent_arbitrary_arg.name))
            forwarded_vars_exprs.append(lowir.TypeLiteral.for_local(cpp_type=then_writer.parent_arbitrary_arg.name,
                                                                    type=then_writer.parent_arbitrary_arg.type))
            forwarded_vars_types.append(then_writer.parent_arbitrary_arg.type)

        then_template_defn = lowir.TemplateDefn(name=writer.new_id(),
                                                args=forwarded_vars_args,
                                                main_definition=lowir.TemplateSpecialization(args=forwarded_vars_args,
                                                                                             patterns=None,
                                                                                             body=then_writer.elems),
                                                specializations=[])
        writer.write(then_template_defn)

        then_function_call_expr, then_function_call_error_expr = _create_metafunction_call(lowir.TypeLiteral.for_nonlocal_template(cpp_type=then_template_defn.name,
                                                                                                                                   is_metafunction_that_may_return_error=True),
                                                                                           args=forwarded_vars_exprs,
                                                                                           arg_types=forwarded_vars_types,
                                                                                           member_kind=writer.parent_return_type.kind,
                                                                                           writer=writer)
    else:
        then_function_call_expr = None
        then_function_call_error_expr = None

    if write_continuation_fun_call is None and (then_function_call_expr or then_function_call_error_expr):
        write_continuation_fun_call = lambda writer: writer.write_result_body_elements(result_expr=then_function_call_expr,
                                                                                       error_expr=then_function_call_error_expr)

    if_branch_writer = writer.create_sibling_writer(writer.parent_arbitrary_arg, writer.parent_return_type)
    stmts_to_low_ir(if_stmt.if_stmts, write_continuation_fun_call, if_branch_writer)

    else_branch_writer = writer.create_sibling_writer(writer.parent_arbitrary_arg, writer.parent_return_type)
    if if_stmt.else_stmts:
        stmts_to_low_ir(if_stmt.else_stmts, write_continuation_fun_call, else_branch_writer)
    else:
        write_continuation_fun_call(else_branch_writer)

    forwarded_vars = _get_free_vars_in_elements(if_branch_writer.elems + else_branch_writer.elems)

    forwarded_vars_args = [lowir.TemplateArgDecl(type=var.type, name=var.cpp_type)
                           for var in forwarded_vars]
    forwarded_vars_patterns = [lowir.TemplateArgPatternLiteral(cxx_pattern=var.cpp_type)
                               for var in forwarded_vars]
    forwarded_vars_exprs = [lowir.TypeLiteral.for_local(cpp_type=var.cpp_type,
                                                        type=var.type)
                            for var in forwarded_vars]
    forwarded_vars_types = [var.type
                            for var in forwarded_vars]
    if not forwarded_vars:
        # We need to add a dummy template parameter, otherwise the true/false specializations will be full specializations
        # and the C++ compiler will eagerly evaluate them, even if they would never be instantiated (triggering e.g.
        # any assertions in that code).
        forwarded_vars_args.append(writer.parent_arbitrary_arg)
        forwarded_vars_patterns.append(lowir.TemplateArgPatternLiteral(cxx_pattern=writer.parent_arbitrary_arg.name))
        forwarded_vars_exprs.append(lowir.TypeLiteral.for_local(cpp_type=writer.parent_arbitrary_arg.name,
                                                                type=writer.parent_arbitrary_arg.type))
        forwarded_vars_types.append(writer.parent_arbitrary_arg.type)

    if_branch_specialization = _create_metafunction_specialization(args=forwarded_vars_args,
                                                                   patterns=forwarded_vars_patterns + [lowir.TemplateArgPatternLiteral('true')],
                                                                   body=if_branch_writer.elems)
    else_branch_specialization = _create_metafunction_specialization(args=forwarded_vars_args,
                                                                     patterns=forwarded_vars_patterns + [lowir.TemplateArgPatternLiteral('false')],
                                                                     body=else_branch_writer.elems)

    fun_defn = lowir.TemplateDefn(main_definition=None,
                                  name=writer.new_id(),
                                  args=forwarded_vars_args + [lowir.TemplateArgDecl(type=lowir.BoolType())],
                                  specializations=[if_branch_specialization, else_branch_specialization])
    writer.write(fun_defn)
    function_call_expr, function_call_error_expr = _create_metafunction_call(lowir.TypeLiteral.for_nonlocal_template(cpp_type=fun_defn.name,
                                                                                                                     is_metafunction_that_may_return_error=True),
                                                                             args=forwarded_vars_exprs + [cond_expr],
                                                                             arg_types=forwarded_vars_types + [type_to_low_ir(if_stmt.cond.type)],
                                                                             member_kind=writer.parent_return_type.kind,
                                                                             writer=writer)

    writer.write_result_body_elements(result_expr=function_call_expr,
                                      error_expr=function_call_error_expr)

def stmts_to_low_ir(stmts: List[ir.Stmt],
                    write_continuation_fun_call: Optional[Callable[[TemplateBodyWriter], None]],
                    writer: Writer):
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, ir.Assert):
            assert_to_low_ir(stmt, writer)
        elif isinstance(stmt, ir.Assignment):
            assignment_to_low_ir(stmt, writer)
        elif isinstance(stmt, ir.ReturnStmt):
            assert isinstance(writer, TemplateBodyWriter)
            return_stmt_to_low_ir(stmt, writer)
        elif isinstance(stmt, ir.IfStmt):
            assert isinstance(writer, TemplateBodyWriter)
            if_stmt_to_low_ir(stmt, stmts[index + 1:], write_continuation_fun_call, writer)
            break
        else:
            raise NotImplementedError('Unexpected statement type: ' + stmt.__class__.__name__)

    if write_continuation_fun_call:
        assert isinstance(writer, TemplateBodyWriter)
        write_continuation_fun_call(writer)

def _select_arbitrary_parent_arg(args: List[lowir.TemplateArgDecl]) -> lowir.TemplateArgDecl:
    assert args
    # Prefer a non-template arg (if any), as that will lead to simpler/smaller generated code.
    for arg in args:
        if arg.type.kind != lowir.ExprKind.TEMPLATE:
            return arg
    return args[0]

def function_defn_to_low_ir(function_defn: ir.FunctionDefn, writer: ToplevelWriter):
    try:
        args = [function_arg_decl_to_low_ir(arg)
                for arg in function_defn.args]
        if args:
            parent_arbitrary_arg = _select_arbitrary_parent_arg(args)
        else:
            parent_arbitrary_arg = lowir.TemplateArgDecl(type=lowir.TypeType(),
                                                         name=writer.new_id())
            args = [parent_arbitrary_arg]

        body_writer = TemplateBodyWriter(writer,
                                         parent_arbitrary_arg=parent_arbitrary_arg,
                                         parent_return_type=type_to_low_ir(function_defn.return_type))
        stmts_to_low_ir(function_defn.body,
                        write_continuation_fun_call=None,
                        writer=body_writer)

        main_definition = _create_metafunction_specialization(args=args,
                                                              patterns=None,
                                                              body=body_writer.elems)

        writer.write(lowir.TemplateDefn(main_definition=main_definition,
                                        name=function_defn.name,
                                        args=args,
                                        specializations=[]))
    except (AssertionError, TypeError) as e:  # pragma: no cover
        print('While converting a function defn to low IR:\n' + str(ir.Module(body=[function_defn])))
        raise e

def check_if_error_defn_to_low_ir(check_if_error_defn: ir.CheckIfErrorDefn, writer: ToplevelWriter):
    # template <typename>
    # struct CheckIfError {
    #   using type = void;
    # };
    main_definition = lowir.TemplateSpecialization(args=[lowir.TemplateArgDecl(type=lowir.TypeType(), name='')],
                                                   patterns=None,
                                                   body=[lowir.Typedef(name='type',
                                                                       expr=lowir.TypeLiteral.for_nonlocal_type('void'),
                                                                       type=lowir.TypeType())])
    # template <int x, bool b, typename T>
    # struct CheckIfError<MyErrorHolder<x, b, T>> {
    #   static_assert(Select1stBoolBool<false, x>::value,
    #                 "<MyError's message>");
    # };
    specializations = [lowir.TemplateSpecialization(args=[lowir.TemplateArgDecl(type=type_to_low_ir(arg_decl.type),
                                                                                name=arg_decl.name)
                                                          for arg_decl in custom_error_type.arg_types],
                                                    patterns=[lowir.TemplateArgPatternLiteral('%s<%s>' % (writer.get_holder_template_name_for_error(custom_error_type.name),
                                                                                                          ', '.join(arg.name
                                                                                                                    for arg in custom_error_type.arg_types)))],
                                                    body=[lowir.StaticAssert(expr=lowir.Literal(value=False,
                                                                                                kind=lowir.ExprKind.BOOL),
                                                                             message=error_message)])
                       for custom_error_type, error_message in check_if_error_defn.error_types_and_messages]
    writer.write(lowir.TemplateDefn(name='CheckIfError',
                                    main_definition=main_definition,
                                    specializations=specializations,
                                    args=main_definition.args))

def module_to_low_ir(module: ir.Module, identifier_generator: Iterator[str]):
    writer = ToplevelWriter(identifier_generator)
    for toplevel_elem in module.body:
        if isinstance(toplevel_elem, ir.FunctionDefn):
            function_defn_to_low_ir(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir.Assert):
            assert_to_low_ir(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir.Assignment):
            assignment_to_low_ir(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir.CustomType):
            custom_type_defn_to_low_ir(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir.CheckIfErrorDefn):
            check_if_error_defn_to_low_ir(toplevel_elem, writer)
        else:
            raise NotImplementedError('Unexpected toplevel element: %s' % str(toplevel_elem.__class__))

    return lowir.Header(content=writer.elems)
