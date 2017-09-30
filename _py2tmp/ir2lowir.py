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

def expr_to_low_ir(expr: ir.Expr, identifier_generator: Iterator[str]) -> Tuple[List[lowir.TemplateDefn], lowir.Expr]:
    if isinstance(expr, ir.VarReference):
        return [], var_reference_to_low_ir(expr)
    elif isinstance(expr, ir.MatchExpr):
        return match_expr_to_low_ir(expr, identifier_generator)
    elif isinstance(expr, ir.BoolLiteral):
        return [], bool_literal_to_low_ir(expr)
    elif isinstance(expr, ir.IntLiteral):
        return [], int_literal_to_low_ir(expr)
    elif isinstance(expr, ir.TypeLiteral):
        return [], type_literal_to_low_ir(expr)
    elif isinstance(expr, ir.ListExpr):
        return [], list_expr_to_low_ir(expr)
    elif isinstance(expr, ir.FunctionCall):
        return [], function_call_to_low_ir(expr)
    elif isinstance(expr, ir.EqualityComparison):
        return [], equality_comparison_to_low_ir(expr)
    elif isinstance(expr, ir.AttributeAccessExpr):
        return [], attribute_access_expr_to_low_ir(expr)
    elif isinstance(expr, ir.NotExpr):
        return [], not_expr_to_low_ir(expr)
    elif isinstance(expr, ir.UnaryMinusExpr):
        return [], unary_minus_expr_to_low_ir(expr)
    elif isinstance(expr, ir.IntComparisonExpr):
        return [], int_comparison_expr_to_low_ir(expr)
    elif isinstance(expr, ir.IntBinaryOpExpr):
        return [], int_binary_op_expr_to_low_ir(expr)
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

def _create_metafunction_call(template_expr: lowir.Expr,
                              args: List[lowir.Expr],
                              arg_types: List[lowir.ExprType],
                              member_kind: lowir.ExprKind):
    assert template_expr.kind == lowir.ExprKind.TEMPLATE
    if member_kind in (lowir.ExprKind.BOOL, lowir.ExprKind.INT64):
        member_name = 'value'
    else:
        member_name = 'type'
    template_instantiation_expr = lowir.TemplateInstantiation(template_expr=template_expr,
                                                              args=args,
                                                              arg_types=arg_types,
                                                              instantiation_might_trigger_static_asserts=True)
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

def match_expr_to_low_ir(match_expr: ir.MatchExpr, identifier_generator: Iterator[str]):
    forwarded_args = []  # type: List[ir.VarReference]
    forwarded_args_names = set()
    for match_case in match_expr.match_cases:
        local_vars = set(match_case.matched_var_names)
        for var in ir.get_free_variables_in_stmts(match_case.stmts):
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
        dummy_param_name = next(identifier_generator)
        forwarded_args_decls = [lowir.TemplateArgDecl(type=lowir.TypeType(),
                                                      name=dummy_param_name)]
        forwarded_args_exprs = [lowir.TypeLiteral.for_nonlocal(cpp_type='void',
                                                               kind=lowir.ExprKind.TYPE)]
        forwarded_args_patterns = [lowir.TemplateArgPatternLiteral(cxx_pattern=dummy_param_name)]
        forwarded_args_types = [lowir.TypeType()]

    matched_vars = [var_reference_to_low_ir(var)
                    for var in match_expr.matched_vars]
    matched_vars_types = [type_to_low_ir(var.type)
                          for var in match_expr.matched_vars]

    main_definition = None
    specializations = []
    helper_functions = []
    for match_case in match_expr.match_cases:
        specialization_arg_decls = forwarded_args_decls + [lowir.TemplateArgDecl(type=lowir.TypeType(), name=arg_name)
                                                           for arg_name in match_case.matched_var_names]

        specialization_patterns = forwarded_args_patterns + [lowir.TemplateArgPatternLiteral(cxx_pattern=pattern)
                                                             for pattern in match_case.type_patterns]

        other_helper_functions, stmts = stmts_to_low_ir(match_case.stmts,
                                                        parent_continuation=None,
                                                        identifier_generator=identifier_generator,
                                                        parent_arbitrary_arg=_select_arbitrary_parent_arg(specialization_arg_decls),
                                                        parent_return_type=match_case.return_type)
        helper_functions += other_helper_functions

        if match_case.is_main_definition():
            assert not main_definition
            main_definition = _create_metafunction_specialization(args=specialization_arg_decls,
                                                                  patterns=None,
                                                                  body=stmts)
        else:
            specializations.append(_create_metafunction_specialization(args=specialization_arg_decls,
                                                                       patterns=specialization_patterns,
                                                                       body=stmts))

    args_decls = forwarded_args_decls + [lowir.TemplateArgDecl(type=lowir.TypeType(), name='')
                                         for _ in match_expr.matched_vars]

    args_exprs = forwarded_args_exprs + matched_vars
    arg_types = forwarded_args_types + matched_vars_types

    helper_function = lowir.TemplateDefn(args=args_decls,
                                         main_definition=main_definition,
                                         specializations=specializations,
                                         name=next(identifier_generator))

    helper_function_reference = lowir.TypeLiteral.for_nonlocal(kind=lowir.ExprKind.TEMPLATE,
                                                               cpp_type=helper_function.name)
    expression = _create_metafunction_call(template_expr=helper_function_reference,
                                           args=args_exprs,
                                           arg_types=arg_types,
                                           member_kind=type_to_low_ir(match_expr.type).kind)

    return helper_functions + [helper_function], expression

def bool_literal_to_low_ir(literal: ir.BoolLiteral):
    return lowir.Literal(value=literal.value, kind=lowir.ExprKind.BOOL)

def int_literal_to_low_ir(literal: ir.IntLiteral):
    return lowir.Literal(value=literal.value, kind=lowir.ExprKind.INT64)

def type_literal_to_low_ir(literal: ir.TypeLiteral):
    return lowir.TypeLiteral.for_nonlocal(cpp_type=literal.cpp_type, kind=type_to_low_ir(literal.type).kind)

def list_expr_to_low_ir(list_expr: ir.ListExpr):
    exprs = [var_reference_to_low_ir(elem)
             for elem in list_expr.elems]

    elem_kind = type_to_low_ir(list_expr.elem_type).kind
    if elem_kind == lowir.ExprKind.BOOL:
        list_template = lowir.TypeLiteral.for_nonlocal('BoolList', kind=lowir.ExprKind.TEMPLATE)
    elif elem_kind == lowir.ExprKind.INT64:
        list_template = lowir.TypeLiteral.for_nonlocal('Int64List', kind=lowir.ExprKind.TEMPLATE)
    elif elem_kind == lowir.ExprKind.TYPE:
        list_template = lowir.TypeLiteral.for_nonlocal('List', kind=lowir.ExprKind.TEMPLATE)
    else:
        raise NotImplementedError('elem_kind: %s' % elem_kind)

    return lowir.TemplateInstantiation(template_expr=list_template,
                                       arg_types=[],
                                       instantiation_might_trigger_static_asserts=False,
                                       args=exprs)

def function_call_to_low_ir(call_expr: ir.FunctionCall):
    fun = var_reference_to_low_ir(call_expr.fun)
    args = [var_reference_to_low_ir(arg)
            for arg in call_expr.args]
    arg_types = [type_to_low_ir(arg.type)
                 for arg in call_expr.args]

    assert isinstance(call_expr.fun.type, ir.FunctionType)
    metafunction_call_expr = _create_metafunction_call(template_expr=fun,
                                                       args=args,
                                                       arg_types=arg_types,
                                                       member_kind=type_to_low_ir(call_expr.fun.type.returns).kind)

    return metafunction_call_expr

def equality_comparison_to_low_ir(comparison_expr: ir.EqualityComparison):
    lhs = var_reference_to_low_ir(comparison_expr.lhs)
    rhs = var_reference_to_low_ir(comparison_expr.rhs)
    if lhs.kind == lowir.ExprKind.TYPE:
        std_is_same = lowir.TypeLiteral.for_nonlocal(cpp_type='std::is_same',
                                                     kind=lowir.ExprKind.TEMPLATE)
        comparison_expr = _create_metafunction_call(template_expr=std_is_same,
                                                    args=[lhs, rhs],
                                                    arg_types=[type_to_low_ir(comparison_expr.lhs.type),
                                                               type_to_low_ir(comparison_expr.rhs.type)],
                                                    member_kind=lowir.ExprKind.BOOL)
    else:
        comparison_expr = lowir.ComparisonExpr(lhs=lhs, rhs=rhs, op='==')
    return comparison_expr

def attribute_access_expr_to_low_ir(attribute_access_expr: ir.AttributeAccessExpr):
    class_expr = var_reference_to_low_ir(attribute_access_expr.var)
    assert class_expr.kind == lowir.ExprKind.TYPE
    return lowir.ClassMemberAccess(class_type_expr=class_expr,
                                   member_name=attribute_access_expr.attribute_name,
                                   member_kind=lowir.ExprKind.TYPE)

def not_expr_to_low_ir(not_expr: ir.NotExpr):
    return lowir.NotExpr(expr=var_reference_to_low_ir(not_expr.var))

def unary_minus_expr_to_low_ir(expr: ir.UnaryMinusExpr):
    return lowir.UnaryMinusExpr(expr=var_reference_to_low_ir(expr.var))

def int_comparison_expr_to_low_ir(expr: ir.IntComparisonExpr):
    lhs = var_reference_to_low_ir(expr.lhs)
    rhs = var_reference_to_low_ir(expr.rhs)
    return lowir.ComparisonExpr(lhs=lhs, rhs=rhs, op=expr.op)

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
    return lowir.Int64BinaryOpExpr(lhs=lhs, rhs=rhs, op=cpp_op)

def assert_to_low_ir(assert_stmt: ir.Assert):
    expr = var_reference_to_low_ir(assert_stmt.var)
    return lowir.StaticAssert(expr=expr, message=assert_stmt.message)

def assignment_to_low_ir(assignment: ir.Assignment, identifier_generator: Iterator[str]):
    lhs = var_reference_to_low_ir(assignment.lhs)
    helper_fns, rhs = expr_to_low_ir(assignment.rhs, identifier_generator)

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

def return_stmt_to_low_ir(return_stmt: ir.ReturnStmt):
    var = var_reference_to_low_ir(return_stmt.var)
    expr_type = type_to_low_ir(return_stmt.var.type)

    return [], _create_result_body_element(var, expr_type)

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
                      continuation: Optional[lowir.TemplateBodyElement],
                      identifier_generator: Iterator[str],
                      parent_arbitrary_arg: lowir.TemplateArgDecl,
                      parent_return_type: lowir.ExprType):
    cond_expr = var_reference_to_low_ir(if_stmt.cond)

    if_branch_helper_fns, if_branch_fun_body = stmts_to_low_ir(if_stmt.if_stmts, continuation, identifier_generator, parent_arbitrary_arg, parent_return_type)

    if if_stmt.else_stmts:
        else_branch_helper_fns, else_branch_fun_body = stmts_to_low_ir(if_stmt.else_stmts, continuation, identifier_generator, parent_arbitrary_arg, parent_return_type)
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
    forwarded_vars_types = [var.type
                            for var in forwarded_vars]
    if not forwarded_vars:
        # We need to add a dummy template parameter, otherwise the true/false specializations will be full specializations
        # and the C++ compiler will eagerly evaluate them, even if they would never be instantiated (triggering e.g.
        # any assertions in that code).
        forwarded_vars_args.append(parent_arbitrary_arg)
        forwarded_vars_patterns.append(lowir.TemplateArgPatternLiteral(cxx_pattern=parent_arbitrary_arg.name))
        forwarded_vars_exprs.append(lowir.TypeLiteral.for_local(cpp_type=parent_arbitrary_arg.name,
                                                                type=parent_arbitrary_arg.type))
        forwarded_vars_types.append(parent_arbitrary_arg.type)

    if_branch_specialization = _create_metafunction_specialization(args=forwarded_vars_args,
                                                                   patterns=forwarded_vars_patterns + [lowir.TemplateArgPatternLiteral('true')],
                                                                   body=if_branch_fun_body)
    else_branch_specialization = _create_metafunction_specialization(args=forwarded_vars_args,
                                                                     patterns=forwarded_vars_patterns + [lowir.TemplateArgPatternLiteral('false')],
                                                                     body=else_branch_fun_body)

    fun_defn = lowir.TemplateDefn(main_definition=None,
                                  name=next(identifier_generator),
                                  args=forwarded_vars_args + [lowir.TemplateArgDecl(type=lowir.BoolType())],
                                  specializations=[if_branch_specialization, else_branch_specialization])
    function_call_expr = _create_metafunction_call(lowir.TypeLiteral.for_nonlocal(cpp_type=fun_defn.name,
                                                                                  kind=lowir.ExprKind.TEMPLATE),
                                                   args=forwarded_vars_exprs + [cond_expr],
                                                   arg_types=forwarded_vars_types + [type_to_low_ir(if_stmt.cond.type)],
                                                   member_kind=parent_return_type.kind)

    function_call_result_element = _create_result_body_element(function_call_expr, expr_type=parent_return_type)

    return (if_branch_helper_fns + else_branch_helper_fns + [fun_defn]), function_call_result_element

def stmts_to_low_ir(stmts: List[ir.Stmt],
                    parent_continuation: Optional[Union[lowir.Typedef, lowir.ConstantDef]],
                    identifier_generator: Iterator[str],
                    parent_arbitrary_arg: lowir.TemplateArgDecl,
                    parent_return_type: lowir.ExprType):
    reversed_helper_fun_defns = []
    reversed_body = []
    for x in reversed(stmts):
        if isinstance(x, ir.Assert):
            other_helper_fns = []
            x = assert_to_low_ir(x)
        elif isinstance(x, ir.Assignment):
            other_helper_fns, x = assignment_to_low_ir(x, identifier_generator)
        elif isinstance(x, ir.ReturnStmt):
            other_helper_fns, x = return_stmt_to_low_ir(x)
        elif isinstance(x, ir.IfStmt):
            if reversed_body:
                body = list(reversed(reversed_body))

                forwarded_vars = _get_free_vars_in_elements(body)

                forwarded_vars_args = [lowir.TemplateArgDecl(type=var.type, name=var.cpp_type)
                                       for var in forwarded_vars]
                forwarded_vars_exprs = [lowir.TypeLiteral.for_local(cpp_type=var.cpp_type,
                                                                    type=var.type)
                                        for var in forwarded_vars]
                forwarded_vars_types = [var.type
                                        for var in forwarded_vars]
                if not forwarded_vars:
                    # We need to add a dummy template parameter, otherwise the true/false specializations will be full
                    # specializations and the C++ compiler will eagerly evaluate them, even if they would never be
                    # instantiated (triggering e.g. any assertions in that code).
                    forwarded_vars_args.append(parent_arbitrary_arg)
                    forwarded_vars_exprs.append(lowir.TypeLiteral.for_local(cpp_type=parent_arbitrary_arg.name,
                                                                            type=parent_arbitrary_arg.type))
                    forwarded_vars_types.append(parent_arbitrary_arg.type)

                continuation_fun_main_definition = _create_metafunction_specialization(args=forwarded_vars_args,
                                                                                       patterns=None,
                                                                                       body=body)

                continuation_fun_defn = lowir.TemplateDefn(main_definition=continuation_fun_main_definition,
                                                           name=next(identifier_generator),
                                                           args=forwarded_vars_args,
                                                           specializations=[])
                continuation_call_expr = _create_metafunction_call(lowir.TypeLiteral.for_nonlocal(cpp_type=continuation_fun_defn.name,
                                                                                                  kind=lowir.ExprKind.TEMPLATE),
                                                                   args=forwarded_vars_exprs,
                                                                   arg_types=forwarded_vars_types,
                                                                   member_kind=parent_return_type.kind)
                continuation = _create_result_body_element(expr=continuation_call_expr,
                                                           expr_type=parent_return_type)
            else:
                continuation = parent_continuation
                continuation_fun_defn = None
            reversed_body = []

            other_helper_fns, x = if_stmt_to_low_ir(x, continuation, identifier_generator, parent_arbitrary_arg, parent_return_type)

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

def _select_arbitrary_parent_arg(args: List[lowir.TemplateArgDecl]):
    assert args
    # Prefer a non-template arg (if any), as that will lead to simpler/smaller generated code.
    for arg in args:
        if arg.type.kind != lowir.ExprKind.TEMPLATE:
            return arg
    return args[0]

def function_defn_to_low_ir(function_defn: ir.FunctionDefn, identifier_generator: Iterator[str]):
    args = [function_arg_decl_to_low_ir(arg)
            for arg in function_defn.args]

    helper_fn_defns, body = stmts_to_low_ir(stmts=function_defn.body,
                                            parent_continuation=None,
                                            identifier_generator=identifier_generator,
                                            parent_arbitrary_arg=_select_arbitrary_parent_arg(args),
                                            parent_return_type=type_to_low_ir(function_defn.return_type))

    main_definition = _create_metafunction_specialization(args=args,
                                                          patterns=None,
                                                          body=body)

    fun_defn = lowir.TemplateDefn(main_definition=main_definition,
                                  name=function_defn.name,
                                  args=args,
                                  specializations=[])

    return helper_fn_defns + [fun_defn]

def module_to_low_ir(module: ir.Module, identifier_generator: Iterator[str]):
    header_content = []
    for toplevel_elem in module.body:
        if isinstance(toplevel_elem, ir.FunctionDefn):
            header_content += function_defn_to_low_ir(toplevel_elem, identifier_generator)
        elif isinstance(toplevel_elem, ir.Assert):
            header_content.append(assert_to_low_ir(toplevel_elem))
        elif isinstance(toplevel_elem, ir.Assignment):
            template_defns, elem = assignment_to_low_ir(toplevel_elem, identifier_generator)
            header_content += template_defns
            header_content.append(elem)
        else:
            raise NotImplementedError('Unexpected toplevel element: %s' % str(toplevel_elem.__class__))

    return lowir.Header(content=header_content)
