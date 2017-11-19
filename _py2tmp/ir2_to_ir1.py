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

import _py2tmp.ir1 as ir1
import _py2tmp.ir2 as ir2
from typing import List, Iterator, Optional

class Writer:
    def new_id(self) -> str: ...  # pragma: no cover

    def write(self, elem: ir1.Union[ir1.FunctionDefn, ir1.Assignment, ir1.Assert, ir1.CustomType, ir1.CheckIfErrorDefn]): ...  # pragma: no cover

class FunWriter(Writer):
    def __init__(self, identifier_generator: Iterator[str]):
        self.identifier_generator = identifier_generator
        self.elems = []  # type: List[ir1.Union[ir1.FunctionDefn, ir1.Assignment, ir1.Assert, ir1.CustomType, ir1.CheckIfErrorDefn]]

    def new_id(self):
        return next(self.identifier_generator)

    def new_var(self, type: ir1.ExprType, is_global_function: bool = False):
        return ir1.VarReference(type=type,
                                name=self.new_id(),
                                is_global_function=is_global_function,
                                is_function_that_may_throw=isinstance(type, ir1.FunctionType))

    def write(self, elem: ir1.Union[ir1.FunctionDefn, ir1.Assignment, ir1.Assert, ir1.CustomType, ir1.CheckIfErrorDefn]):
        self.elems.append(elem)

class StmtWriter(Writer):
    def __init__(self,
                 fun_writer: FunWriter,
                 current_fun_return_type: Optional[ir1.ExprType]):
        self.fun_writer = fun_writer
        self.current_fun_return_type = current_fun_return_type
        self.stmts = []  # type: List[ir1.Stmt]

    def write(self, elem: ir1.Union[ir1.FunctionDefn, ir1.CustomType, ir1.CheckIfErrorDefn, ir1.Stmt]):
        if isinstance(elem, ir1.Stmt):
            self.stmts.append(elem)
        else:
            self.fun_writer.write(elem)

    def new_id(self):
        return self.fun_writer.new_id()

    def new_var(self, type: ir1.ExprType):
        return self.fun_writer.new_var(type)

def custom_type_to_ir1(type: ir2.CustomType):
    return ir1.CustomType(name=type.name,
                          arg_types=[ir1.CustomTypeArgDecl(name=arg.name, type=type_to_ir1(arg.type))
                                     for arg in type.arg_types])

def type_to_ir1(type: ir2.ExprType):
    if isinstance(type, ir2.BoolType):
        return ir1.BoolType()
    elif isinstance(type, ir2.IntType):
        return ir1.IntType()
    elif isinstance(type, ir2.TypeType):
        return ir1.TypeType()
    elif isinstance(type, ir2.BottomType):
        return ir1.BottomType()
    elif isinstance(type, ir2.ErrorOrVoidType):
        return ir1.ErrorOrVoidType()
    elif isinstance(type, ir2.ListType):
        return ir1.ListType(elem_type=type_to_ir1(type.elem_type))
    elif isinstance(type, ir2.FunctionType):
        return ir1.FunctionType(argtypes=[type_to_ir1(arg)
                                          for arg in type.argtypes],
                                returns=type_to_ir1(type.returns))
    elif isinstance(type, ir2.CustomType):
        return custom_type_to_ir1(type)
    else:
        raise NotImplementedError('Unexpected type: %s' % str(type.__class__))

def expr_to_ir1(expr: ir2.Expr, writer: Writer) -> ir1.Expr:
    if isinstance(expr, ir2.VarReference):
        return var_reference_to_ir1(expr, writer)
    elif isinstance(expr, ir2.MatchExpr):
        assert isinstance(writer, StmtWriter)
        return match_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.BoolLiteral):
        return bool_literal_to_ir1(expr, writer)
    elif isinstance(expr, ir2.IntLiteral):
        return int_literal_to_ir1(expr, writer)
    elif isinstance(expr, ir2.TypeLiteral):
        return type_literal_to_ir1(expr, writer)
    elif isinstance(expr, ir2.ListExpr):
        return list_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.FunctionCall):
        return function_call_to_ir1(expr, writer)
    elif isinstance(expr, ir2.EqualityComparison):
        return equality_comparison_to_ir1(expr, writer)
    elif isinstance(expr, ir2.AttributeAccessExpr):
        return attribute_access_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.NotExpr):
        return not_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.IntComparisonExpr):
        return int_comparison_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.UnaryMinusExpr):
        return unary_minus_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.IntBinaryOpExpr):
        return int_binary_op_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.ListConcatExpr):
        return list_concat_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.ListComprehensionExpr):
        return list_comprehension_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.IsInstanceExpr):
        return is_instance_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.SafeUncheckedCast):
        return safe_unchecked_cast_expr_to_ir1(expr, writer)
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def function_arg_decl_to_ir1(decl: ir2.FunctionArgDecl, writer: StmtWriter):
    return ir1.FunctionArgDecl(type=type_to_ir1(decl.type),
                               name=decl.name)

def var_reference_to_ir1(var: ir2.VarReference, writer: Writer):
    return ir1.VarReference(type=type_to_ir1(var.type),
                            name=var.name,
                            is_global_function=var.is_global_function,
                            is_function_that_may_throw=var.is_function_that_may_throw)

def match_expr_to_ir1(match_expr: ir2.MatchExpr, writer: StmtWriter):
    return ir1.MatchExpr(matched_vars=[var_reference_to_ir1(var, writer)
                                       for var in match_expr.matched_vars],
                         match_cases=[ir1.MatchCase(type_patterns=match_case.type_patterns,
                                                    matched_var_names=match_case.matched_var_names,
                                                    expr=function_call_to_ir1(match_case.expr, writer))
                                      for match_case in match_expr.match_cases])

def bool_literal_to_ir1(literal: ir2.BoolLiteral, writer: Writer):
    return ir1.BoolLiteral(value=literal.value)

def int_literal_to_ir1(literal: ir2.IntLiteral, writer: Writer):
    return ir1.IntLiteral(value=literal.value)

def type_literal_to_ir1(literal: ir2.TypeLiteral, writer: Writer):
    return ir1.TypeLiteral(cpp_type=literal.cpp_type,
                           args={arg_name: expr_to_ir1(arg_expr, writer)
                                 for arg_name, arg_expr in literal.args.items()})

def list_expr_to_ir1(list_expr: ir2.ListExpr, writer: Writer):
    return ir1.ListExpr(elem_type=type_to_ir1(list_expr.elem_type),
                        elems=[var_reference_to_ir1(elem_expr, writer)
                               for elem_expr in list_expr.elems])

def function_call_to_ir1(call_expr: ir2.FunctionCall, writer: Writer):
    return ir1.FunctionCall(fun=var_reference_to_ir1(call_expr.fun, writer),
                            args=[var_reference_to_ir1(arg_expr, writer)
                                  for arg_expr in call_expr.args])

def equality_comparison_to_ir1(comparison_expr: ir2.EqualityComparison, writer: Writer):
    return ir1.EqualityComparison(lhs=var_reference_to_ir1(comparison_expr.lhs, writer),
                                  rhs=var_reference_to_ir1(comparison_expr.rhs, writer))

def attribute_access_expr_to_ir1(attribute_access_expr: ir2.AttributeAccessExpr, writer: Writer):
    return ir1.AttributeAccessExpr(var=var_reference_to_ir1(attribute_access_expr.var, writer),
                                   attribute_name=attribute_access_expr.attribute_name,
                                   type=type_to_ir1(attribute_access_expr.type))

def not_expr_to_ir1(expr: ir2.NotExpr, writer: Writer):
    return ir1.NotExpr(var=var_reference_to_ir1(expr.var, writer))

def int_comparison_expr_to_ir1(expr: ir2.IntComparisonExpr, writer: Writer):
    return ir1.IntComparisonExpr(lhs=var_reference_to_ir1(expr.lhs, writer),
                                 rhs=var_reference_to_ir1(expr.rhs, writer),
                                 op=expr.op)

def unary_minus_expr_to_ir1(expr: ir2.UnaryMinusExpr, writer: Writer):
    return ir1.UnaryMinusExpr(var=var_reference_to_ir1(expr.var, writer))

def int_binary_op_expr_to_ir1(expr: ir2.IntBinaryOpExpr, writer: Writer):
    return ir1.IntBinaryOpExpr(lhs=var_reference_to_ir1(expr.lhs, writer),
                               rhs=var_reference_to_ir1(expr.rhs, writer),
                               op=expr.op)

def list_concat_expr_to_ir1(expr: ir2.ListConcatExpr, writer: Writer):
    return ir1.ListConcatExpr(lhs=var_reference_to_ir1(expr.lhs, writer),
                              rhs=var_reference_to_ir1(expr.rhs, writer))

def list_comprehension_expr_to_ir1(expr: ir2.ListComprehensionExpr, writer: Writer):
    return ir1.ListComprehensionExpr(list_var=var_reference_to_ir1(expr.list_var, writer),
                                     loop_var=var_reference_to_ir1(expr.loop_var, writer),
                                     result_elem_expr=function_call_to_ir1(expr.result_elem_expr, writer))

def is_instance_expr_to_ir1(expr: ir2.IsInstanceExpr, writer: Writer):
    return ir1.IsInstanceExpr(var=var_reference_to_ir1(expr.var, writer),
                              checked_type=custom_type_to_ir1(expr.checked_type))

def safe_unchecked_cast_expr_to_ir1(expr: ir2.SafeUncheckedCast, writer: Writer):
    return ir1.SafeUncheckedCast(var=var_reference_to_ir1(expr.var, writer),
                                 type=custom_type_to_ir1(expr.type))

def assert_to_ir1(assert_stmt: ir2.Assert, writer: Writer):
    writer.write(ir1.Assert(var=var_reference_to_ir1(assert_stmt.var, writer),
                            message=assert_stmt.message))

def assignment_to_ir1(assignment: ir2.Assignment, writer: Writer):
    writer.write(ir1.Assignment(lhs=var_reference_to_ir1(assignment.lhs, writer),
                                lhs2=var_reference_to_ir1(assignment.lhs2, writer) if assignment.lhs2 else None,
                                rhs=expr_to_ir1(assignment.rhs, writer)))

def return_stmt_to_ir1(return_stmt: ir2.ReturnStmt, writer: StmtWriter):
    writer.write(ir1.ReturnStmt(result=var_reference_to_ir1(return_stmt.result, writer) if return_stmt.result else None,
                                error=var_reference_to_ir1(return_stmt.error, writer) if return_stmt.error else None))

def if_stmt_to_ir1(if_stmt: ir2.IfStmt, writer: StmtWriter):
    if_branch_writer = StmtWriter(writer.fun_writer, writer.current_fun_return_type)
    stmts_to_ir1(if_stmt.if_stmts, if_branch_writer)

    else_branch_writer = StmtWriter(writer.fun_writer, writer.current_fun_return_type)
    stmts_to_ir1(if_stmt.else_stmts, else_branch_writer)

    writer.write(ir1.IfStmt(cond=var_reference_to_ir1(if_stmt.cond, writer),
                            if_stmts=if_branch_writer.stmts,
                            else_stmts=else_branch_writer.stmts))

def check_if_error_defn_to_ir1(toplevel_elem: ir2.CheckIfErrorDefn, writer: Writer):
    writer.write(ir1.CheckIfErrorDefn(error_types_and_messages=[(custom_type_to_ir1(error_type), message)
                                                                for error_type, message in toplevel_elem.error_types_and_messages]))

def stmts_to_ir1(stmts: List[ir2.Stmt], writer: StmtWriter):
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, ir2.IfStmt):
            if_stmt_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.Assignment):
            assignment_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.ReturnStmt):
            return_stmt_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.Assert):
            assert_to_ir1(stmt, writer)
        else:
            raise NotImplementedError('Unexpected statement: %s' % str(stmt.__class__))

def function_defn_to_ir1(function_defn: ir2.FunctionDefn, writer: FunWriter):
    return_type = type_to_ir1(function_defn.return_type)

    stmt_writer = StmtWriter(writer, return_type)
    stmts_to_ir1(function_defn.body, stmt_writer)

    writer.write(ir1.FunctionDefn(name=function_defn.name,
                                  args=[function_arg_decl_to_ir1(arg, stmt_writer)
                                        for arg in function_defn.args],
                                  body=stmt_writer.stmts,
                                  return_type=return_type))

def module_to_ir1(module: ir2.Module, identifier_generator: Iterator[str]):
    writer = FunWriter(identifier_generator)
    for toplevel_elem in module.body:
        if isinstance(toplevel_elem, ir2.FunctionDefn):
            function_defn_to_ir1(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir2.Assignment):
            assignment_to_ir1(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir2.Assert):
            assert_to_ir1(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir2.CustomType):
            writer.write(custom_type_to_ir1(toplevel_elem))
        elif isinstance(toplevel_elem, ir2.CheckIfErrorDefn):
            check_if_error_defn_to_ir1(toplevel_elem, writer)
        else:
            raise NotImplementedError('Unexpected toplevel element: %s' % str(toplevel_elem.__class__))

    return ir1.Module(body=writer.elems)
