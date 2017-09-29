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

import _py2tmp.lowir as lowir
import _py2tmp.ir as ir
import _py2tmp.utils as utils
from typing import List, Tuple, Optional, Iterator, Union

def type_to_low_ir(type: ir.ExprType):
    if isinstance(type, ir.BoolType):
        return lowir.BoolType()
    elif isinstance(type, ir.IntType):
        return lowir.Int64Type()
    elif isinstance(type, ir.TypeType):
        return lowir.TypeType()
    elif isinstance(type, ir.ListType):
        return lowir.TypeType()
    elif isinstance(type, ir.FunctionType):
        return function_type_to_low_ir(type)
    else:
        raise NotImplementedError('Unexpected type: %s' % str(type.__class__))

def function_type_to_low_ir(fun_type: ir.FunctionType):
    return lowir.TemplateType(argtypes=[type_to_low_ir(arg)
                                        for arg in fun_type.argtypes])

def expr_to_low_ir(expr: ir.Expr, cxx_identifier_generator: Iterator[str]) \
        -> Tuple[List[lowir.TemplateDefn], lowir.Expr]:
    if isinstance(expr, ir.VarReference):
        return [], var_reference_to_low_ir(expr)
    elif isinstance(expr, ir.MatchExpr):
        return match_expr_to_low_ir(expr, cxx_identifier_generator)
    elif isinstance(expr, ir.BoolLiteral):
        return [], bool_literal_to_low_ir(expr)
    elif isinstance(expr, ir.IntLiteral):
        return [], int_literal_to_low_ir(expr)
    elif isinstance(expr, ir.TypeLiteral):
        return [], type_literal_to_low_ir(expr)
    elif isinstance(expr, ir.ListExpr):
        return list_expr_to_low_ir(expr, cxx_identifier_generator)
    elif isinstance(expr, ir.FunctionCall):
        return function_call_to_low_ir(expr, cxx_identifier_generator)
    elif isinstance(expr, ir.EqualityComparison):
        return equality_comparison_to_low_ir(expr, cxx_identifier_generator)
    elif isinstance(expr, ir.AttributeAccessExpr):
        return attribute_access_expr_to_low_ir(expr, cxx_identifier_generator)
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def function_arg_decl_to_low_ir(decl: ir.FunctionArgDecl):
    return lowir.TemplateArgDecl(type=type_to_low_ir(decl.type),
                                 name=decl.name)

def var_reference_to_low_ir(var: ir.VarReference):
    if var.is_global_function:
        return lowir.TypeLiteral.for_nonlocal(cpp_type=var.name,
                                              kind=type_to_low_ir(var.type).kind)
    else:
        return lowir.TypeLiteral.for_local(cpp_type=var.name,
                                           type=type_to_low_ir(var.type))

def _create_metafunction_call(template_expr: lowir.Expr, args: List[lowir.Expr], member_kind: lowir.ExprKind):
    assert template_expr.kind == lowir.ExprKind.TEMPLATE
    if member_kind in (lowir.ExprKind.BOOL, lowir.ExprKind.INT64):
        member_name = 'value'
    else:
        member_name = 'type'
    template_instantiation_expr = lowir.TemplateInstantiation(template_expr=template_expr, args=args)
    return lowir.ClassMemberAccess(class_type_expr=template_instantiation_expr,
                                   member_name=member_name,
                                   member_kind=member_kind)

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

def match_expr_to_low_ir(match_expr: ir.MatchExpr, cxx_identifier_generator: Iterator[str]):
    forwarded_args = []  # type: List[ir.VarReference]
    forwarded_args_names = set()
    for match_case in match_expr.match_cases:
        local_vars = set(match_case.matched_var_names)
        for var in match_case.expr.get_free_variables():
            if var.name not in local_vars and var.name not in forwarded_args_names:
                forwarded_args_names.add(var.name)
                forwarded_args.append(var)

    forwarded_args_decls = [lowir.TemplateArgDecl(type=type_to_low_ir(var_ref.type), name=var_ref.name)
                            for var_ref in forwarded_args]
    forwarded_args_patterns = [lowir.TemplateArgPatternLiteral(cxx_pattern=var_ref.name)
                               for var_ref in forwarded_args]
    forwarded_args_exprs = [lowir.TypeLiteral.for_local(cpp_type=var_ref.name,
                                                        type=type_to_low_ir(var_ref.type))
                            for var_ref in forwarded_args]

    helper_functions = []
    matched_exprs = []
    for expr in match_expr.matched_exprs:
        other_helper_functions, expr = expr_to_low_ir(expr, cxx_identifier_generator)
        helper_functions += other_helper_functions
        matched_exprs.append(expr)

    main_definition = None
    specializations = []
    for match_case in match_expr.match_cases:
        specialization_arg_decls = forwarded_args_decls + [lowir.TemplateArgDecl(type=lowir.TypeType(), name=arg_name)
                                                           for arg_name in match_case.matched_var_names]

        specialization_patterns = forwarded_args_patterns + [lowir.TemplateArgPatternLiteral(cxx_pattern=pattern)
                                                             for pattern in match_case.type_patterns]

        other_helper_functions, return_stmt = return_stmt_to_low_ir(return_stmt=ir.ReturnStmt(match_case.expr),
                                                                    cxx_identifier_generator=cxx_identifier_generator)
        helper_functions += other_helper_functions

        function_specialization = _create_metafunction_specialization(args=specialization_arg_decls,
                                                                      patterns=specialization_patterns,
                                                                      body=[return_stmt])

        if match_case.is_main_definition():
            assert not main_definition
            main_definition = function_specialization
        else:
            specializations.append(function_specialization)

    args_decls = forwarded_args_decls + [lowir.TemplateArgDecl(type=lowir.TypeType(), name='')
                                         for _ in match_expr.matched_exprs]

    args_exprs = forwarded_args_exprs + matched_exprs

    helper_function = lowir.TemplateDefn(args=args_decls,
                                         main_definition=main_definition,
                                         specializations=specializations,
                                         name=next(cxx_identifier_generator))

    helper_function_reference = lowir.TypeLiteral.for_nonlocal(kind=lowir.ExprKind.TEMPLATE,
                                                               cpp_type=helper_function.name)
    expression = _create_metafunction_call(template_expr=helper_function_reference,
                                           args=args_exprs,
                                           member_kind=type_to_low_ir(match_expr.type).kind)

    return helper_functions + [helper_function], expression

def bool_literal_to_low_ir(literal: ir.BoolLiteral):
    return lowir.Literal(value=literal.value, kind=lowir.ExprKind.BOOL)

def int_literal_to_low_ir(literal: ir.IntLiteral):
    return lowir.Literal(value=literal.value, kind=lowir.ExprKind.INT64)

def type_literal_to_low_ir(literal: ir.TypeLiteral):
    return lowir.TypeLiteral.for_nonlocal(cpp_type=literal.cpp_type, kind=type_to_low_ir(literal.type).kind)

def list_expr_to_low_ir(list_expr: ir.ListExpr, cxx_identifier_generator: Iterator[str]):
    helper_fns = []
    exprs = []
    for expr in list_expr.elem_exprs:
        other_helper_fns, expr = expr_to_low_ir(expr, cxx_identifier_generator)
        helper_fns += other_helper_fns
        exprs.append(expr)

    elem_kind = type_to_low_ir(list_expr.elem_type).kind
    if elem_kind == lowir.ExprKind.BOOL:
        list_template = lowir.TypeLiteral.for_nonlocal('BoolList', kind=lowir.ExprKind.TEMPLATE)
    elif elem_kind == lowir.ExprKind.INT64:
        list_template = lowir.TypeLiteral.for_nonlocal('Int64List', kind=lowir.ExprKind.TEMPLATE)
    elif elem_kind == lowir.ExprKind.TYPE:
        list_template = lowir.TypeLiteral.for_nonlocal('List', kind=lowir.ExprKind.TEMPLATE)
    else:
        raise NotImplementedError('elem_kind: %s' % elem_kind)

    return helper_fns, lowir.TemplateInstantiation(template_expr=list_template,
                                                   args=exprs)

def function_call_to_low_ir(call_expr: ir.FunctionCall, cxx_identifier_generator: Iterator[str]):
    helper_fns, fun_expr = expr_to_low_ir(call_expr.fun_expr, cxx_identifier_generator)
    args = []
    for arg in call_expr.args:
        other_helper_fns, arg = expr_to_low_ir(arg, cxx_identifier_generator)
        helper_fns += other_helper_fns
        args.append(arg)

    assert isinstance(call_expr.fun_expr.type, ir.FunctionType)
    metafunction_call_expr = _create_metafunction_call(template_expr=fun_expr,
                                                       args=args,
                                                       member_kind=type_to_low_ir(call_expr.fun_expr.type.returns).kind)

    return helper_fns, metafunction_call_expr

def equality_comparison_to_low_ir(comparison_expr: ir.EqualityComparison, cxx_identifier_generator: Iterator[str]):
    lhs_helper_fns, lhs = expr_to_low_ir(comparison_expr.lhs, cxx_identifier_generator)
    rhs_helper_fns, rhs = expr_to_low_ir(comparison_expr.rhs, cxx_identifier_generator)
    if lhs.kind == lowir.ExprKind.TYPE:
        std_is_same = lowir.TypeLiteral.for_nonlocal(cpp_type='std::is_same',
                                                     kind=lowir.ExprKind.TEMPLATE)
        comparison_expr = _create_metafunction_call(template_expr=std_is_same,
                                                    args=[lhs, rhs],
                                                    member_kind=lowir.ExprKind.BOOL)
    else:
        comparison_expr = lowir.EqualityComparison(lhs=lhs, rhs=rhs)
    return lhs_helper_fns + rhs_helper_fns, comparison_expr

def attribute_access_expr_to_low_ir(attribute_access_expr: ir.AttributeAccessExpr, cxx_identifier_generator: Iterator[str]):
    helper_fns, class_expr = expr_to_low_ir(attribute_access_expr.expr, cxx_identifier_generator)
    assert class_expr.kind == lowir.ExprKind.TYPE
    return helper_fns, lowir.ClassMemberAccess(class_type_expr=class_expr,
                                               member_name=attribute_access_expr.attribute_name,
                                               member_kind=lowir.ExprKind.TYPE)

def assert_to_low_ir(assert_stmt: ir.Assert, cxx_identifier_generator: Iterator[str]):
    helper_fns, expr = expr_to_low_ir(assert_stmt.expr, cxx_identifier_generator)
    return helper_fns, lowir.StaticAssert(expr=expr, message=assert_stmt.message)

def assignment_to_low_ir(assignment: ir.Assignment, cxx_identifier_generator: Iterator[str]):
    lhs = var_reference_to_low_ir(assignment.lhs)
    helper_fns, rhs = expr_to_low_ir(assignment.rhs, cxx_identifier_generator)

    low_ir_type = type_to_low_ir(assignment.lhs.type)
    if low_ir_type.kind in (lowir.ExprKind.BOOL, lowir.ExprKind.INT64):
        element = lowir.ConstantDef(name=lhs.cpp_type, expr=rhs, type=low_ir_type)
    else:
        element = lowir.Typedef(name=lhs.cpp_type, expr=rhs, type=low_ir_type)

    return helper_fns, element

def _create_result_body_element(expr: lowir.Expr, expr_type: lowir.ExprType):
    if expr.kind in (lowir.ExprKind.BOOL, lowir.ExprKind.INT64):
        return lowir.ConstantDef(name='value', expr=expr, type=expr_type)
    else:
        return lowir.Typedef(name='type', expr=expr, type=expr_type)

def return_stmt_to_low_ir(return_stmt: ir.ReturnStmt, cxx_identifier_generator: Iterator[str]):
    helper_fns, expr = expr_to_low_ir(return_stmt.expr, cxx_identifier_generator)
    expr_type = type_to_low_ir(return_stmt.expr.type)

    return helper_fns, _create_result_body_element(expr, expr_type)

def _get_free_vars_in_elements(elements: List[lowir.TemplateBodyElement]):
    free_var_names = set()
    bound_var_names = set()
    free_vars = []
    for element in elements:
        if isinstance(element, lowir.StaticAssert) or isinstance(element, lowir.ConstantDef) or isinstance(element, lowir.Typedef):
            for var in element.expr.get_free_vars():
                if not var.cpp_type in bound_var_names and not var.cpp_type in free_var_names:
                    free_var_names.add(var.cpp_type)
                    free_vars.append(var)
        else:
            raise NotImplementedError('Unexpected element type: %s' % str(element.__class__))
        if isinstance(element, lowir.ConstantDef) or isinstance(element, lowir.Typedef):
            bound_var_names.add(element.name)
    return free_vars

def if_stmt_to_low_ir(if_stmt: ir.IfStmt,
                      continuation: Optional[lowir.TemplateBodyElement],
                      cxx_identifier_generator: Iterator[str],
                      parent_arbitrary_arg: lowir.TemplateArgDecl,
                      parent_return_type: lowir.ExprType):
    helper_fns, cond_expr = expr_to_low_ir(if_stmt.cond_expr, cxx_identifier_generator)

    if_branch_helper_fns, if_branch_fun_body = stmts_to_low_ir(if_stmt.if_stmts, continuation, cxx_identifier_generator, parent_arbitrary_arg, parent_return_type)

    if if_stmt.else_stmts:
        else_branch_helper_fns, else_branch_fun_body = stmts_to_low_ir(if_stmt.else_stmts, continuation, cxx_identifier_generator, parent_arbitrary_arg, parent_return_type)
    else:
        else_branch_helper_fns = []
        assert continuation
        else_branch_fun_body = [continuation]

    forwarded_vars = _get_free_vars_in_elements(if_branch_fun_body + else_branch_fun_body + [continuation
                                                                                             for continuation in [continuation]
                                                                                             if continuation])

    forwarded_vars_args = [lowir.TemplateArgDecl(type=var.type, name=var.cpp_type)
                           for var in forwarded_vars]
    forwarded_vars_patterns = [lowir.TemplateArgPatternLiteral(cxx_pattern=var.cpp_type)
                               for var in forwarded_vars]
    forwarded_vars_exprs = [lowir.TypeLiteral.for_local(cpp_type=var.cpp_type,
                                                        type=var.type)
                            for var in forwarded_vars]
    if not forwarded_vars:
        # We need to add a dummy template parameter, otherwise the true/false specializations will be full specializations
        # and the C++ compiler will eagerly evaluate them, even if they would never be instantiated (triggering e.g.
        # any assertions in that code).
        forwarded_vars_args.append(parent_arbitrary_arg)
        forwarded_vars_patterns.append(lowir.TemplateArgPatternLiteral(cxx_pattern=parent_arbitrary_arg.name))
        forwarded_vars_exprs.append(lowir.TypeLiteral.for_local(cpp_type=parent_arbitrary_arg.name,
                                                                type=parent_arbitrary_arg.type))

    if_branch_specialization = _create_metafunction_specialization(args=forwarded_vars_args,
                                                                   patterns=forwarded_vars_patterns + [lowir.TemplateArgPatternLiteral('true')],
                                                                   body=if_branch_fun_body)
    else_branch_specialization = _create_metafunction_specialization(args=forwarded_vars_args,
                                                                     patterns=forwarded_vars_patterns + [lowir.TemplateArgPatternLiteral('false')],
                                                                     body=else_branch_fun_body)

    fun_defn = lowir.TemplateDefn(main_definition=None,
                                  name=next(cxx_identifier_generator),
                                  args=forwarded_vars_args + [lowir.TemplateArgDecl(type=lowir.BoolType())],
                                  specializations=[if_branch_specialization, else_branch_specialization])
    function_call_expr = _create_metafunction_call(lowir.TypeLiteral.for_nonlocal(cpp_type=fun_defn.name,
                                                                                  kind=lowir.ExprKind.TEMPLATE),
                                                   args=forwarded_vars_exprs + [cond_expr],
                                                   member_kind=parent_return_type.kind)

    function_call_result_element = _create_result_body_element(function_call_expr, expr_type=parent_return_type)

    return (helper_fns + if_branch_helper_fns + else_branch_helper_fns + [fun_defn]), function_call_result_element

def stmts_to_low_ir(stmts: List[ir.Stmt],
                    parent_continuation: Optional[Union[lowir.Typedef, lowir.ConstantDef]],
                    cxx_identifier_generator: Iterator[str],
                    parent_arbitrary_arg: lowir.TemplateArgDecl,
                    parent_return_type: lowir.ExprType):
    reversed_helper_fun_defns = []
    reversed_body = []
    for x in reversed(stmts):
        if isinstance(x, ir.Assert):
            other_helper_fns, x = assert_to_low_ir(x, cxx_identifier_generator)
        elif isinstance(x, ir.Assignment):
            other_helper_fns, x = assignment_to_low_ir(x, cxx_identifier_generator)
        elif isinstance(x, ir.ReturnStmt):
            other_helper_fns, x = return_stmt_to_low_ir(x, cxx_identifier_generator)
        elif isinstance(x, ir.IfStmt):
            if reversed_body:
                body = list(reversed(reversed_body))

                forwarded_vars = _get_free_vars_in_elements(body)

                forwarded_vars_args = [lowir.TemplateArgDecl(type=var.type, name=var.cpp_type)
                                       for var in forwarded_vars]
                forwarded_vars_exprs = [lowir.TypeLiteral.for_local(cpp_type=var.cpp_type,
                                                                    type=var.type)
                                        for var in forwarded_vars]
                if not forwarded_vars:
                    # We need to add a dummy template parameter, otherwise the true/false specializations will be full
                    # specializations and the C++ compiler will eagerly evaluate them, even if they would never be
                    # instantiated (triggering e.g. any assertions in that code).
                    forwarded_vars_args.append(parent_arbitrary_arg)
                    forwarded_vars_exprs.append(lowir.TypeLiteral.for_local(cpp_type=parent_arbitrary_arg.name,
                                                                            type=parent_arbitrary_arg.type))

                continuation_fun_main_definition = _create_metafunction_specialization(args=forwarded_vars_args,
                                                                                       patterns=None,
                                                                                       body=body)

                continuation_fun_defn = lowir.TemplateDefn(main_definition=continuation_fun_main_definition,
                                                           name=next(cxx_identifier_generator),
                                                           args=forwarded_vars_args,
                                                           specializations=[])
                continuation_call_expr = _create_metafunction_call(lowir.TypeLiteral.for_nonlocal(cpp_type=continuation_fun_defn.name,
                                                                                                  kind=lowir.ExprKind.TEMPLATE),
                                                                   args=forwarded_vars_exprs,
                                                                   member_kind=parent_return_type.kind)
                continuation = _create_result_body_element(expr=continuation_call_expr,
                                                           expr_type=parent_return_type)
            else:
                continuation = parent_continuation
                continuation_fun_defn = None
            reversed_body = []

            other_helper_fns, x = if_stmt_to_low_ir(x, continuation, cxx_identifier_generator, parent_arbitrary_arg, parent_return_type)

            if continuation_fun_defn:
                # In this case we need a different order: the previous helper functions must be defined before the
                # continuation, not after.
                other_helper_fns = list(itertools.chain(reversed(reversed_helper_fun_defns), [continuation_fun_defn], reversed(other_helper_fns)))
                reversed_helper_fun_defns = []
        else:
            raise NotImplementedError('Unexpected element: %s' % str(x.__class__))
        reversed_helper_fun_defns += reversed(other_helper_fns)
        reversed_body.append(x)

    body = list(reversed(reversed_body))
    if not body or not isinstance(body[-1], (lowir.Typedef, lowir.ConstantDef)) or body[-1].name not in ('type', 'value'):
        body.append(parent_continuation)
    return list(reversed(reversed_helper_fun_defns)), body

def function_defn_to_low_ir(function_defn: ir.FunctionDefn, cxx_identifier_generator: Iterator[str]):
    args = [function_arg_decl_to_low_ir(arg)
            for arg in function_defn.args]

    # Prefer a non-template arg (if any), as that will lead to simpler/smaller generated code.
    for arg in args:
        if arg.type.kind != lowir.ExprKind.TEMPLATE:
            arbitrary_arg = arg
            break
    else:
        arbitrary_arg = args[0]

    helper_fn_defns, body = stmts_to_low_ir(stmts=function_defn.body,
                                            parent_continuation=None,
                                            cxx_identifier_generator=cxx_identifier_generator,
                                            parent_arbitrary_arg=arbitrary_arg,
                                            parent_return_type=type_to_low_ir(function_defn.return_type))

    main_definition = _create_metafunction_specialization(args=args,
                                                          patterns=None,
                                                          body=body)

    fun_defn = lowir.TemplateDefn(main_definition=main_definition,
                                  name=function_defn.name,
                                  args=args,
                                  specializations=[])

    return helper_fn_defns + [fun_defn]

def module_to_low_ir(module: ir.Module, cxx_identifier_generator: Iterator[str]):
    function_defns=[lowf
                    for f in module.function_defns
                    for lowf in function_defn_to_low_ir(f, cxx_identifier_generator)]
    assertions = []
    for assert_stmt in module.assertions:
        other_fn_defs, assert_stmt = assert_to_low_ir(assert_stmt, cxx_identifier_generator)
        function_defns += other_fn_defs
        assertions.append(assert_stmt)

    return lowir.Header(template_defns=function_defns, assertions=assertions)
