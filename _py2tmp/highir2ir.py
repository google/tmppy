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

import _py2tmp.ir as ir
import _py2tmp.highir as highir
from typing import List, Tuple, Iterator

def type_to_ir(type: highir.ExprType):
    if isinstance(type, highir.BoolType):
        return ir.BoolType()
    elif isinstance(type, highir.IntType):
        return ir.IntType()
    elif isinstance(type, highir.TypeType):
        return ir.TypeType()
    elif isinstance(type, highir.ListType):
        return ir.ListType(elem_type=type_to_ir(type.elem_type))
    elif isinstance(type, highir.FunctionType):
        return ir.FunctionType(argtypes=[type_to_ir(arg)
                                         for arg in type.argtypes],
                               returns=type_to_ir(type.returns))
    else:
        raise NotImplementedError('Unexpected type: %s' % str(type.__class__))

def expr_to_ir(expr: highir.Expr, identifier_generator: Iterator[str]) \
        -> Tuple[List[ir.Stmt], ir.VarReference]:
    if isinstance(expr, highir.VarReference):
        return [], var_reference_to_ir(expr)
    elif isinstance(expr, highir.MatchExpr):
        stmts, expr = match_expr_to_ir(expr, identifier_generator)
    elif isinstance(expr, highir.BoolLiteral):
        stmts, expr = bool_literal_to_ir(expr)
    elif isinstance(expr, highir.IntLiteral):
        stmts, expr = int_literal_to_ir(expr)
    elif isinstance(expr, highir.TypeLiteral):
        stmts, expr = type_literal_to_ir(expr)
    elif isinstance(expr, highir.ListExpr):
        stmts, expr = list_expr_to_ir(expr, identifier_generator)
    elif isinstance(expr, highir.FunctionCall):
        stmts, expr = function_call_to_ir(expr, identifier_generator)
    elif isinstance(expr, highir.EqualityComparison):
        stmts, expr = equality_comparison_to_ir(expr, identifier_generator)
    elif isinstance(expr, highir.AttributeAccessExpr):
        stmts, expr = attribute_access_expr_to_ir(expr, identifier_generator)
    elif isinstance(expr, highir.AndExpr):
        stmts, expr = and_expr_to_ir(expr, identifier_generator)
    elif isinstance(expr, highir.OrExpr):
        stmts, expr = or_expr_to_ir(expr, identifier_generator)
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

    var = ir.VarReference(type=expr.type,
                          name=next(identifier_generator),
                          is_global_function=False)
    stmts.append(ir.Assignment(lhs=var, rhs=expr))

    return stmts, var

def function_arg_decl_to_ir(decl: highir.FunctionArgDecl):
    return ir.FunctionArgDecl(type=type_to_ir(decl.type),
                              name=decl.name)

def var_reference_to_ir(var: highir.VarReference):
    return ir.VarReference(type=type_to_ir(var.type),
                           name=var.name,
                           is_global_function=var.is_global_function)

def match_case_to_ir(match_case: highir.MatchCase, identifier_generator: Iterator[str]):
    stmts, var = expr_to_ir(match_case.expr, identifier_generator)  # type: Tuple[List[ir.Stmt], ir.VarReference]
    stmts.append(ir.ReturnStmt(var))
    return ir.MatchCase(type_patterns=match_case.type_patterns,
                        matched_var_names=match_case.matched_var_names,
                        stmts=stmts,
                        return_type=var.type)

def match_expr_to_ir(match_expr: highir.MatchExpr, identifier_generator: Iterator[str]):
    stmts = []
    matched_vars = []
    for expr in match_expr.matched_exprs:
        additional_stmts, var = expr_to_ir(expr, identifier_generator)
        stmts += additional_stmts
        matched_vars.append(var)

    match_cases = [match_case_to_ir(match_case, identifier_generator)
                   for match_case in match_expr.match_cases]

    return stmts, ir.MatchExpr(matched_vars, match_cases)

def bool_literal_to_ir(literal: highir.BoolLiteral):
    return [], ir.BoolLiteral(value=literal.value)

def int_literal_to_ir(literal: highir.IntLiteral):
    return [], ir.IntLiteral(value=literal.value)

def type_literal_to_ir(literal: highir.TypeLiteral):
    return [], ir.TypeLiteral(cpp_type=literal.cpp_type)

def list_expr_to_ir(list_expr: highir.ListExpr, identifier_generator: Iterator[str]):
    stmts = []
    elem_vars = []
    for elem_expr in list_expr.elem_exprs:
        other_stmts, var = expr_to_ir(elem_expr, identifier_generator)
        stmts += other_stmts
        elem_vars.append(var)
    return stmts, ir.ListExpr(elem_type=type_to_ir(list_expr.elem_type),
                              elems=elem_vars)

def function_call_to_ir(call_expr: highir.FunctionCall, identifier_generator: Iterator[str]):
    stmts, fun = expr_to_ir(call_expr.fun_expr, identifier_generator)
    args = []
    for arg_expr in call_expr.args:
        other_stmts, arg_var = expr_to_ir(arg_expr, identifier_generator)
        stmts += other_stmts
        args.append(arg_var)
    return stmts, ir.FunctionCall(fun=fun, args=args)

def equality_comparison_to_ir(comparison_expr: highir.EqualityComparison, identifier_generator: Iterator[str]):
    lhs_stmts, lhs = expr_to_ir(comparison_expr.lhs, identifier_generator)
    rhs_stmts, rhs = expr_to_ir(comparison_expr.rhs, identifier_generator)

    return lhs_stmts + rhs_stmts, ir.EqualityComparison(lhs=lhs, rhs=rhs)

def attribute_access_expr_to_ir(attribute_access_expr: highir.AttributeAccessExpr, identifier_generator: Iterator[str]):
    stmts, var = expr_to_ir(attribute_access_expr.expr, identifier_generator)
    return stmts, ir.AttributeAccessExpr(var=var, attribute_name=attribute_access_expr.attribute_name)

def and_expr_to_ir(expr, identifier_generator):
    lhs_stmts, lhs_var = expr_to_ir(expr.lhs, identifier_generator)
    rhs_stmts, rhs_var = expr_to_ir(expr.rhs, identifier_generator)

    # y = f() and g()
    #
    # becomes:
    #
    # if f():
    #   x = g()
    # else:
    #   x = False
    # y = x

    var = ir.VarReference(type=ir.BoolType(),
                          name=next(identifier_generator),
                          is_global_function=False)

    rhs_stmts.append(ir.Assignment(lhs=var, rhs=rhs_var))

    lhs_stmts.append(ir.IfStmt(cond=lhs_var,
                               if_stmts=rhs_stmts,
                               else_stmts=[ir.Assignment(lhs=var,
                                                         rhs=ir.BoolLiteral(value=False))]))

    return lhs_stmts, var

def or_expr_to_ir(expr, identifier_generator):
    lhs_stmts, lhs_var = expr_to_ir(expr.lhs, identifier_generator)
    rhs_stmts, rhs_var = expr_to_ir(expr.rhs, identifier_generator)

    # y = f() or g()
    #
    # becomes:
    #
    # if f():
    #   x = True
    # else:
    #   x = g()
    # y = x

    var = ir.VarReference(type=ir.BoolType(),
                          name=next(identifier_generator),
                          is_global_function=False)

    rhs_stmts.append(ir.Assignment(lhs=var, rhs=rhs_var))

    lhs_stmts.append(ir.IfStmt(cond=lhs_var,
                               if_stmts=[ir.Assignment(lhs=var,
                                                       rhs=ir.BoolLiteral(value=True))],
                               else_stmts=rhs_stmts))

    return lhs_stmts, var

def assert_to_ir(assert_stmt: highir.Assert, identifier_generator: Iterator[str]):
    stmts, var = expr_to_ir(assert_stmt.expr, identifier_generator)
    return stmts, ir.Assert(var=var, message=assert_stmt.message)

def assignment_to_ir(assignment: highir.Assignment, identifier_generator: Iterator[str]):
    stmts, var = expr_to_ir(assignment.rhs, identifier_generator)
    return stmts, ir.Assignment(lhs=var_reference_to_ir(assignment.lhs),
                                rhs=var)

def return_stmt_to_ir(return_stmt: highir.ReturnStmt, identifier_generator: Iterator[str]):
    stmts, var = expr_to_ir(return_stmt.expr, identifier_generator)
    return stmts, ir.ReturnStmt(var=var)

def if_stmt_to_ir(if_stmt: highir.IfStmt,
                  identifier_generator: Iterator[str]):
    cond_stmts, cond = expr_to_ir(if_stmt.cond_expr, identifier_generator)
    if_stmts = stmts_to_ir(if_stmt.if_stmts, identifier_generator)
    else_stmts = stmts_to_ir(if_stmt.else_stmts, identifier_generator)
    return cond_stmts, ir.IfStmt(cond=cond, if_stmts=if_stmts, else_stmts=else_stmts)

def stmts_to_ir(stmts: List[highir.Stmt],
                identifier_generator: Iterator[str]):
    expanded_stmts = []
    for stmt in stmts:
        if isinstance(stmt, highir.IfStmt):
            stmts, stmt = if_stmt_to_ir(stmt, identifier_generator)
        elif isinstance(stmt, highir.Assignment):
            stmts, stmt = assignment_to_ir(stmt, identifier_generator)
        elif isinstance(stmt, highir.ReturnStmt):
            stmts, stmt = return_stmt_to_ir(stmt, identifier_generator)
        elif isinstance(stmt, highir.Assert):
            stmts, stmt = assert_to_ir(stmt, identifier_generator)
        else:
            raise NotImplementedError('Unexpected statement: %s' % str(stmt.__class__))

        expanded_stmts += stmts
        expanded_stmts.append(stmt)

    return expanded_stmts

def function_defn_to_ir(function_defn: highir.FunctionDefn, identifier_generator: Iterator[str]):
    body = stmts_to_ir(function_defn.body, identifier_generator)
    return ir.FunctionDefn(name=function_defn.name,
                           args=[function_arg_decl_to_ir(arg) for arg in function_defn.args],
                           body=body,
                           return_type=type_to_ir(function_defn.return_type))


def module_to_ir(module: highir.Module, identifier_generator: Iterator[str]):
    function_defns = [function_defn_to_ir(function_defn, identifier_generator)
                      for function_defn in module.function_defns]
    return ir.Module(body=function_defns + stmts_to_ir(module.assertions, identifier_generator))
