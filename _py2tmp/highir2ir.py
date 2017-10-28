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

from collections import defaultdict
import _py2tmp.ir as ir
import _py2tmp.highir as highir
import _py2tmp.utils as utils
from typing import List, Iterator, Optional, Dict
from contextlib import contextmanager

class FunWriter:
    def __init__(self, identifier_generator: Iterator[str]):
        self.identifier_generator = identifier_generator
        self.is_error_fun_ref = self.new_var(ir.FunctionType(argtypes=[ir.ErrorOrVoidType()],
                                                             returns=ir.BoolType()),
                                             is_global_function=True)
        self.function_defns = [self._create_is_error_fun_defn()]
        self.obfuscated_identifiers_by_identifier = defaultdict(lambda: self.new_id())  # type: Dict[str, str]

    def new_id(self):
        return next(self.identifier_generator)

    def obfuscate_identifier(self, identifier: str):
        return self.obfuscated_identifiers_by_identifier[identifier]

    def new_var(self, type: ir.ExprType, is_global_function: bool = False):
        return ir.VarReference(type=type,
                               name=self.new_id(),
                               is_global_function=is_global_function,
                               is_function_that_may_throw=isinstance(type, ir.FunctionType))

    def write_function(self, fun_defn: ir.FunctionDefn):
        self.function_defns.append(fun_defn)

    def _create_is_error_fun_defn(self):
        # def is_error(x: ErrorOrVoid):
        #   v = Type('void')
        #   b = (x == v)
        #   b2 = not b
        #   return b2

        stmt_writer = StmtWriter(self, current_fun_return_type=ir.BoolType())
        x_var = self.new_var(type=ir.ErrorOrVoidType())
        v_var = stmt_writer.new_var_for_expr(ir.TypeLiteral(cpp_type='void', args=dict()))
        b_var = stmt_writer.new_var_for_expr(ir.EqualityComparison(lhs=x_var, rhs=v_var))
        b2_var = stmt_writer.new_var_for_expr(ir.NotExpr(b_var))
        stmt_writer.write_stmt(ir.ReturnStmt(result=b2_var, error=None))

        return ir.FunctionDefn(name=self.is_error_fun_ref.name,
                               args=[ir.FunctionArgDecl(type=x_var.type, name=x_var.name)],
                               body=stmt_writer.stmts,
                               return_type=ir.BoolType())

class TryExceptContext:
    def __init__(self,
                 caught_exception_type: ir.CustomType,
                 caught_exception_name: str,
                 except_fun_call_expr: ir.FunctionCall):
        self.caught_exception_type = caught_exception_type
        self.caught_exception_name = caught_exception_name
        self.except_fun_call_expr = except_fun_call_expr

class StmtWriter:
    def __init__(self,
                 fun_writer: FunWriter,
                 current_fun_return_type: Optional[ir.ExprType]):
        self.fun_writer = fun_writer
        self.current_fun_return_type = current_fun_return_type
        self.stmts = []  # type: List[ir.Stmt]
        self.try_except_contexts = []  # type: List[TryExceptContext]

    def write_function(self, fun_defn: ir.FunctionDefn):
        self.fun_writer.write_function(fun_defn)

    def write_stmt(self, stmt: ir.Stmt):
        self.stmts.append(stmt)

    def new_id(self):
        return self.fun_writer.new_id()

    def obfuscate_identifier(self, identifier: str):
        return self.fun_writer.obfuscate_identifier(identifier)

    def new_var(self, type: ir.ExprType):
        return self.fun_writer.new_var(type)

    def new_var_for_expr(self, expr: ir.Expr):
        var = self.fun_writer.new_var(expr.type)
        self.write_stmt(ir.Assignment(lhs=var, rhs=expr))
        return var

    def new_var_for_expr_with_error_checking(self, expr: ir.Expr):
        if self.current_fun_return_type:
            # x, err = <expr>
            # b = is_error(err)
            # if b:
            #   b1 = isinstance(err, MyError1)
            #   if b1:
            #     e1 = err  # type: MyError1
            #     res1, err1 = except_handler_fun1(...)
            #     return res1, err1
            #   ...
            #   bN = isinstance(err, MyErrorN)
            #   if bN:
            #     eN = err  # type: MyErrorN
            #     resN, errN = except_handler_funN(...)
            #     return resN, errN
            #   return None, err

            x_var = self.fun_writer.new_var(expr.type)
            error_var = self.fun_writer.new_var(ir.ErrorOrVoidType())
            self.write_stmt(ir.Assignment(lhs=x_var, lhs2=error_var, rhs=expr))
            b_var = self.new_var_for_expr(ir.FunctionCall(fun=self.fun_writer.is_error_fun_ref,
                                                          args=[error_var]))

            outer_if_branch_writer = StmtWriter(self.fun_writer, self.current_fun_return_type)
            for context in self.try_except_contexts:
                if_branch_writer = StmtWriter(self.fun_writer, self.current_fun_return_type)
                if_branch_writer.write_stmt(ir.Assignment(lhs=ir.VarReference(type=context.caught_exception_type,
                                                                              name=self.obfuscate_identifier(context.caught_exception_name),
                                                                              is_global_function=False,
                                                                              is_function_that_may_throw=False),
                                                          rhs=ir.SafeUncheckedCast(error_var,
                                                                                   type=context.caught_exception_type)))
                res_i = if_branch_writer.new_var(type=self.current_fun_return_type)
                err_i = if_branch_writer.new_var(type=ir.ErrorOrVoidType())
                if_branch_writer.write_stmt(ir.Assignment(lhs=res_i,
                                                          lhs2=err_i,
                                                          rhs=context.except_fun_call_expr))
                if_branch_writer.write_stmt(ir.ReturnStmt(result=res_i, error=err_i))

                b_i = outer_if_branch_writer.new_var_for_expr(ir.IsInstanceExpr(error_var, context.caught_exception_type))
                outer_if_branch_writer.write_stmt(ir.IfStmt(cond=b_i,
                                                            if_stmts=if_branch_writer.stmts,
                                                            else_stmts=[]))

            outer_if_branch_writer.write_stmt(ir.ReturnStmt(result=None, error=error_var))

            self.write_stmt(ir.IfStmt(cond=b_var,
                                      if_stmts=outer_if_branch_writer.stmts,
                                      else_stmts=[]))
            return x_var
        else:
            # This statement is at top-level.

            # x = <expr>

            x_var = self.fun_writer.new_var(expr.type)
            self.write_stmt(ir.Assignment(lhs=x_var,
                                          rhs=expr))
            return x_var

    @contextmanager
    def enter_try_except_context(self, context: TryExceptContext):
        self.try_except_contexts.append(context)
        yield
        context1 = self.try_except_contexts.pop()
        assert context1 is context

def type_to_ir(type: highir.ExprType):
    if isinstance(type, highir.BoolType):
        return ir.BoolType()
    elif isinstance(type, highir.IntType):
        return ir.IntType()
    elif isinstance(type, highir.TypeType):
        return ir.TypeType()
    elif isinstance(type, highir.BottomType):
        return ir.BottomType()
    elif isinstance(type, highir.ListType):
        return ir.ListType(elem_type=type_to_ir(type.elem_type))
    elif isinstance(type, highir.FunctionType):
        return ir.FunctionType(argtypes=[type_to_ir(arg)
                                         for arg in type.argtypes],
                               returns=type_to_ir(type.returns))
    elif isinstance(type, highir.CustomType):
        return ir.CustomType(name=type.name,
                             arg_types=[ir.CustomTypeArgDecl(name=arg.name, type=type_to_ir(arg.type))
                                        for arg in type.arg_types])
    else:
        raise NotImplementedError('Unexpected type: %s' % str(type.__class__))

def expr_to_ir(expr: highir.Expr, writer: StmtWriter) -> ir.VarReference:
    if isinstance(expr, highir.VarReference):
        return var_reference_to_ir(expr, writer)
    elif isinstance(expr, highir.MatchExpr):
        return match_expr_to_ir(expr, writer)
    elif isinstance(expr, highir.BoolLiteral):
        return bool_literal_to_ir(expr, writer)
    elif isinstance(expr, highir.IntLiteral):
        return int_literal_to_ir(expr, writer)
    elif isinstance(expr, highir.TypeLiteral):
        return type_literal_to_ir(expr, writer)
    elif isinstance(expr, highir.ListExpr):
        return list_expr_to_ir(expr, writer)
    elif isinstance(expr, highir.FunctionCall):
        return function_call_to_ir(expr, writer)
    elif isinstance(expr, highir.EqualityComparison):
        return equality_comparison_to_ir(expr, writer)
    elif isinstance(expr, highir.AttributeAccessExpr):
        return attribute_access_expr_to_ir(expr, writer)
    elif isinstance(expr, highir.AndExpr):
        return and_expr_to_ir(expr, writer)
    elif isinstance(expr, highir.OrExpr):
        return or_expr_to_ir(expr, writer)
    elif isinstance(expr, highir.NotExpr):
        return not_expr_to_ir(expr, writer)
    elif isinstance(expr, highir.IntUnaryMinusExpr):
        return int_unary_minus_expr_to_ir(expr, writer)
    elif isinstance(expr, highir.IntComparisonExpr):
        return int_comparison_expr_to_ir(expr, writer)
    elif isinstance(expr, highir.IntBinaryOpExpr):
        return int_binary_op_expr_to_ir(expr, writer)
    elif isinstance(expr, highir.ListConcatExpr):
        return list_concat_expr_to_ir(expr, writer)
    elif isinstance(expr, highir.ListComprehension):
        return list_comprehension_expr_to_ir(expr, writer)
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def function_arg_decl_to_ir(decl: highir.FunctionArgDecl, writer: StmtWriter):
    return ir.FunctionArgDecl(type=type_to_ir(decl.type),
                              name=writer.obfuscate_identifier(decl.name))

def var_reference_to_ir(var: highir.VarReference, writer: StmtWriter):
    return ir.VarReference(type=type_to_ir(var.type),
                           name=var.name if var.is_global_function else writer.obfuscate_identifier(var.name),
                           is_global_function=var.is_global_function,
                           is_function_that_may_throw=var.is_function_that_may_throw)

def match_expr_to_ir(match_expr: highir.MatchExpr, writer: StmtWriter):
    matched_vars = [expr_to_ir(expr, writer)
                    for expr in match_expr.matched_exprs]

    match_cases = []
    for match_case in match_expr.match_cases:
        match_case_writer = StmtWriter(writer.fun_writer, type_to_ir(match_expr.type))
        match_case_var = expr_to_ir(match_case.expr, match_case_writer)
        match_case_writer.write_stmt(ir.ReturnStmt(result=match_case_var, error=None))

        forwarded_vars = ir.get_unique_free_variables_in_stmts(match_case_writer.stmts)

        match_fun_name = writer.new_id()
        writer.write_function(ir.FunctionDefn(name=match_fun_name,
                                              args=[ir.FunctionArgDecl(type=var.type, name=var.name)
                                                    for var in forwarded_vars],
                                              body=match_case_writer.stmts,
                                              return_type=match_case_var.type))
        match_fun_ref = ir.VarReference(type=ir.FunctionType(argtypes=[var.type
                                                                       for var in forwarded_vars],
                                                             returns=match_case_var.type),
                                        name=match_fun_name,
                                        is_global_function=True,
                                        is_function_that_may_throw=True)
        replacements = {var_name: writer.obfuscate_identifier(var_name)
                        for var_name in match_case.matched_var_names}

        match_cases.append(ir.MatchCase(type_patterns=[utils.replace_identifiers(type_pattern, replacements)
                                                       for type_pattern in  match_case.type_patterns],
                                        matched_var_names=[writer.obfuscate_identifier(var_name)
                                                           for var_name in match_case.matched_var_names],
                                        expr=ir.FunctionCall(fun=match_fun_ref,
                                                             args=forwarded_vars)))

    return writer.new_var_for_expr_with_error_checking(ir.MatchExpr(matched_vars, match_cases))

def bool_literal_to_ir(literal: highir.BoolLiteral, writer: StmtWriter):
    return writer.new_var_for_expr(ir.BoolLiteral(value=literal.value))

def int_literal_to_ir(literal: highir.IntLiteral, writer: StmtWriter):
    return writer.new_var_for_expr(ir.IntLiteral(value=literal.value))

def type_literal_to_ir(literal: highir.TypeLiteral, writer: StmtWriter):
    arg_vars_by_name = dict()
    for arg_name, arg_expr in sorted(literal.arg_exprs.items(), key=lambda item: item[0]):
        arg_vars_by_name[arg_name] = expr_to_ir(arg_expr, writer)
    return writer.new_var_for_expr(ir.TypeLiteral(cpp_type=literal.cpp_type, args=arg_vars_by_name))

def list_expr_to_ir(list_expr: highir.ListExpr, writer: StmtWriter):
    elem_vars = [expr_to_ir(elem_expr, writer)
                 for elem_expr in list_expr.elem_exprs]
    return writer.new_var_for_expr(ir.ListExpr(elem_type=type_to_ir(list_expr.elem_type),
                                               elems=elem_vars))

def function_call_to_ir(call_expr: highir.FunctionCall, writer: StmtWriter):
    fun_var = expr_to_ir(call_expr.fun_expr, writer)
    arg_vars = [expr_to_ir(arg_expr, writer)
                for arg_expr in call_expr.args]
    if fun_var.is_function_that_may_throw:
        return writer.new_var_for_expr_with_error_checking(ir.FunctionCall(fun=fun_var,
                                                                           args=arg_vars))
    else:
        return writer.new_var_for_expr(ir.FunctionCall(fun=fun_var,
                                                       args=arg_vars))

def equality_comparison_to_ir(comparison_expr: highir.EqualityComparison, writer: StmtWriter):
    return writer.new_var_for_expr(ir.EqualityComparison(lhs=expr_to_ir(comparison_expr.lhs, writer),
                                                         rhs=expr_to_ir(comparison_expr.rhs, writer)))

def attribute_access_expr_to_ir(attribute_access_expr: highir.AttributeAccessExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir.AttributeAccessExpr(var=expr_to_ir(attribute_access_expr.expr, writer),
                                                          attribute_name=attribute_access_expr.attribute_name,
                                                          type=type_to_ir(attribute_access_expr.type)))

def and_expr_to_ir(expr: highir.AndExpr, writer: StmtWriter):
    # y = f() and g()
    #
    # becomes:
    #
    # if f():
    #   x = g()
    # else:
    #   x = False
    # y = x

    lhs_var = expr_to_ir(expr.lhs, writer)

    if_branch_writer = StmtWriter(writer.fun_writer, writer.current_fun_return_type)
    rhs_var = expr_to_ir(expr.rhs, if_branch_writer)

    writer.write_stmt(ir.IfStmt(cond=lhs_var,
                                if_stmts=if_branch_writer.stmts,
                                else_stmts=[ir.Assignment(lhs=rhs_var,
                                                          rhs=ir.BoolLiteral(value=False))]))

    return rhs_var

def or_expr_to_ir(expr: highir.OrExpr, writer: StmtWriter):
    # y = f() or g()
    #
    # becomes:
    #
    # if f():
    #   x = True
    # else:
    #   x = g()
    # y = x

    lhs_var = expr_to_ir(expr.lhs, writer)

    else_branch_writer = StmtWriter(writer.fun_writer, writer.current_fun_return_type)
    rhs_var = expr_to_ir(expr.rhs, else_branch_writer)

    writer.write_stmt(ir.IfStmt(cond=lhs_var,
                                if_stmts=[ir.Assignment(lhs=rhs_var,
                                                        rhs=ir.BoolLiteral(value=True))],
                                else_stmts=else_branch_writer.stmts))

    return rhs_var

def not_expr_to_ir(expr: highir.NotExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir.NotExpr(expr_to_ir(expr.expr, writer)))

def int_unary_minus_expr_to_ir(expr: highir.IntUnaryMinusExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir.UnaryMinusExpr(expr_to_ir(expr.expr, writer)))

def int_comparison_expr_to_ir(expr: highir.IntComparisonExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir.IntComparisonExpr(lhs=expr_to_ir(expr.lhs, writer),
                                                        rhs=expr_to_ir(expr.rhs, writer),
                                                        op=expr.op))

def int_binary_op_expr_to_ir(expr: highir.IntBinaryOpExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir.IntBinaryOpExpr(lhs=expr_to_ir(expr.lhs, writer),
                                                      rhs=expr_to_ir(expr.rhs, writer),
                                                      op=expr.op))

def list_concat_expr_to_ir(expr: highir.ListConcatExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir.ListConcatExpr(lhs=expr_to_ir(expr.lhs, writer),
                                                     rhs=expr_to_ir(expr.rhs, writer)))

def list_comprehension_expr_to_ir(expr: highir.ListComprehension, writer: StmtWriter):
    # [f(x, y) * 2
    #  for x in l]
    #
    # Becomes:
    #
    # def g(x, y):
    #   return f(x, y) * 2  # (in fact, this will be converted further)
    #
    # [g(x, y)
    #  for x in l]

    l_var = expr_to_ir(expr.list_expr, writer)

    result_elem_type = type_to_ir(expr.result_elem_expr.type)
    helper_fun_writer = StmtWriter(writer.fun_writer,
                                   current_fun_return_type=result_elem_type)
    helper_fun_writer.write_stmt(ir.ReturnStmt(result=expr_to_ir(expr.result_elem_expr, helper_fun_writer),
                                               error=None))
    forwarded_vars = ir.get_unique_free_variables_in_stmts(helper_fun_writer.stmts)
    helper_fun_name = writer.new_id()
    writer.write_function(ir.FunctionDefn(name=helper_fun_name,
                                          args=[ir.FunctionArgDecl(type=var.type, name=var.name)
                                                for var in forwarded_vars],
                                          body=helper_fun_writer.stmts,
                                          return_type=result_elem_type))

    helper_fun_call = ir.FunctionCall(fun=ir.VarReference(name=helper_fun_name,
                                                          type=ir.FunctionType(argtypes=[var.type
                                                                                         for var in forwarded_vars],
                                                                               returns=result_elem_type),
                                                          is_global_function=True,
                                                          is_function_that_may_throw=True),
                                      args=forwarded_vars)
    return writer.new_var_for_expr_with_error_checking(ir.ListComprehensionExpr(list_var=l_var,
                                                                                loop_var=var_reference_to_ir(expr.loop_var, writer),
                                                                                result_elem_expr=helper_fun_call))

def assert_to_ir(assert_stmt: highir.Assert, writer: StmtWriter):
    writer.write_stmt(ir.Assert(var=expr_to_ir(assert_stmt.expr, writer),
                                message=assert_stmt.message))

def try_except_stmt_to_ir(try_except_stmt: highir.TryExcept,
                          then_stmts: List[highir.Stmt],
                          writer: StmtWriter):
    # try:
    #   x = f()
    #   y = g()
    # except MyError as e:
    #   y = e.x
    #   if b:
    #     return 5
    # z = y + 3
    # return z
    #
    # Becomes:
    #
    # def then_fun(y):
    #   z = y + 3
    #   return z
    #
    # def except_fun(e, b):
    #   y = e.x
    #   if b:
    #     return 5
    #   x0, err0 = then_fun(y)
    #   b0 = is_error(err0)
    #   if b0:
    #     return None, err0
    #   return x0, None
    #
    # x, f_err = f()
    # f_b = is_error(f_err)
    # if f_b:
    #   b0 = is_instance_of_MyError(f_err)
    #   if b0:
    #     e = f_err  # type: MyError
    #     res, err = except_fun(...)
    #     return res, err
    #   return None, f_err
    # y, g_err = g()
    # g_b = is_error(g_err)
    # if g_b:
    #   b0 = is_instance_of_MyError(g_err)
    #   if b0:
    #     e = g_err  # type: MyError
    #     res, err = except_fun(...)
    #     return res, err
    #   return None, g_err
    # res, err = then_fun()
    # return res, err

    if then_stmts:
        then_stmts_writer = StmtWriter(writer.fun_writer, writer.current_fun_return_type)
        stmts_to_ir(then_stmts, then_stmts_writer)

        then_fun_forwarded_vars = ir.get_unique_free_variables_in_stmts(then_stmts_writer.stmts)
        then_fun_defn = ir.FunctionDefn(name=writer.new_id(),
                                        args=[ir.FunctionArgDecl(type=var.type, name=var.name)
                                              for var in then_fun_forwarded_vars],
                                        body=then_stmts_writer.stmts,
                                        return_type=writer.current_fun_return_type)
        writer.write_function(then_fun_defn)

        then_fun_ref = ir.VarReference(type=ir.FunctionType(argtypes=[arg.type
                                                                      for arg in then_fun_defn.args],
                                                            returns=then_fun_defn.return_type),
                                       name=then_fun_defn.name,
                                       is_global_function=True,
                                       is_function_that_may_throw=True)
        then_fun_call_expr = ir.FunctionCall(fun=then_fun_ref, args=then_fun_forwarded_vars)
    else:
        then_fun_call_expr = None

    except_stmts_writer = StmtWriter(writer.fun_writer, writer.current_fun_return_type)
    stmts_to_ir(try_except_stmt.except_body, except_stmts_writer)
    if then_fun_call_expr and not (try_except_stmt.except_body
                                   and try_except_stmt.except_body[-1].get_return_type().always_returns):
        except_stmts_writer.write_stmt(ir.ReturnStmt(result=except_stmts_writer.new_var_for_expr_with_error_checking(then_fun_call_expr),
                                                     error=None))

    except_fun_forwarded_vars = ir.get_unique_free_variables_in_stmts(except_stmts_writer.stmts)
    except_fun_defn = ir.FunctionDefn(name=writer.new_id(),
                                      args=[ir.FunctionArgDecl(type=var.type, name=var.name)
                                            for var in except_fun_forwarded_vars],
                                      body=except_stmts_writer.stmts,
                                      return_type=writer.current_fun_return_type)
    writer.write_function(except_fun_defn)

    except_fun_ref = ir.VarReference(type=ir.FunctionType(argtypes=[arg.type
                                                                    for arg in except_fun_defn.args],
                                                          returns=except_fun_defn.return_type),
                                     name=except_fun_defn.name,
                                     is_global_function=True,
                                     is_function_that_may_throw=True)
    except_fun_call_expr = ir.FunctionCall(fun=except_fun_ref, args=except_fun_forwarded_vars)

    with writer.enter_try_except_context(TryExceptContext(type_to_ir(try_except_stmt.caught_exception_type),
                                                          try_except_stmt.caught_exception_name,
                                                          except_fun_call_expr)):
        stmts_to_ir(try_except_stmt.try_body, writer)

    if then_fun_call_expr and not (try_except_stmt.try_body
                                   and try_except_stmt.try_body[-1].get_return_type().always_returns):
        writer.write_stmt(ir.ReturnStmt(result=writer.new_var_for_expr_with_error_checking(then_fun_call_expr),
                                        error=None))

def assignment_to_ir(assignment: highir.Assignment, writer: StmtWriter):
    writer.write_stmt(ir.Assignment(lhs=var_reference_to_ir(assignment.lhs, writer),
                                    rhs=expr_to_ir(assignment.rhs, writer)))

def return_stmt_to_ir(return_stmt: highir.ReturnStmt, writer: StmtWriter):
    writer.write_stmt(ir.ReturnStmt(result=expr_to_ir(return_stmt.expr, writer),
                                    error=None))

def raise_stmt_to_ir(raise_stmt: highir.RaiseStmt, writer: StmtWriter):
    exception_expr = expr_to_ir(raise_stmt.expr, writer)
    for context in writer.try_except_contexts:
        if context.caught_exception_type == exception_expr.type:
            # try:
            #   raise f(x)
            # except MyError as e:
            #   ...
            #
            # Becomes:
            #
            # def handler(e, ...) :
            #    ...
            #
            # e = f(x)
            # result, err = handler(e, ...)
            # return result, err
            exception_var = ir.VarReference(type=exception_expr.type,
                                            name=writer.obfuscate_identifier(context.caught_exception_name),
                                            is_global_function=False,
                                            is_function_that_may_throw=False)
            writer.write_stmt(ir.Assignment(lhs=exception_var, rhs=exception_expr))
            handler_result_var = writer.new_var(context.except_fun_call_expr.type)
            handler_error_var = writer.new_var(ir.ErrorOrVoidType())
            writer.write_stmt(ir.Assignment(lhs=handler_result_var,
                                            lhs2=handler_error_var,
                                            rhs=context.except_fun_call_expr))
            writer.write_stmt(ir.ReturnStmt(result=handler_result_var,
                                            error=handler_error_var))
            break
    else:
        writer.write_stmt(ir.ReturnStmt(result=None,
                                        error=exception_expr))

def if_stmt_to_ir(if_stmt: highir.IfStmt, writer: StmtWriter):
    cond_var = expr_to_ir(if_stmt.cond_expr, writer)

    if_branch_writer = StmtWriter(writer.fun_writer, writer.current_fun_return_type)
    stmts_to_ir(if_stmt.if_stmts, if_branch_writer)

    else_branch_writer = StmtWriter(writer.fun_writer, writer.current_fun_return_type)
    stmts_to_ir(if_stmt.else_stmts, else_branch_writer)

    writer.write_stmt(ir.IfStmt(cond=cond_var,
                                if_stmts=if_branch_writer.stmts,
                                else_stmts=else_branch_writer.stmts))

def stmts_to_ir(stmts: List[highir.Stmt], writer: StmtWriter):
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, highir.IfStmt):
            if_stmt_to_ir(stmt, writer)
        elif isinstance(stmt, highir.Assignment):
            assignment_to_ir(stmt, writer)
        elif isinstance(stmt, highir.ReturnStmt):
            return_stmt_to_ir(stmt, writer)
        elif isinstance(stmt, highir.RaiseStmt):
            raise_stmt_to_ir(stmt, writer)
        elif isinstance(stmt, highir.Assert):
            assert_to_ir(stmt, writer)
        elif isinstance(stmt, highir.TryExcept):
            try_except_stmt_to_ir(stmt, stmts[index + 1:], writer)
            return
        else:
            raise NotImplementedError('Unexpected statement: %s' % str(stmt.__class__))

def function_defn_to_ir(function_defn: highir.FunctionDefn, writer: FunWriter):
    return_type = type_to_ir(function_defn.return_type)

    stmt_writer = StmtWriter(writer, return_type)
    stmts_to_ir(function_defn.body, stmt_writer)

    writer.write_function(ir.FunctionDefn(name=function_defn.name,
                                          args=[function_arg_decl_to_ir(arg, stmt_writer)
                                                for arg in function_defn.args],
                                          body=stmt_writer.stmts,
                                          return_type=return_type))

def module_to_ir(module: highir.Module, identifier_generator: Iterator[str]):
    writer = FunWriter(identifier_generator)
    for function_defn in module.function_defns:
        function_defn_to_ir(function_defn, writer)

    stmt_writer = StmtWriter(writer, current_fun_return_type=None)
    for assertion in module.assertions:
        assert_to_ir(assertion, stmt_writer)

    custom_types_defns = [type_to_ir(type) for type in module.custom_types]
    check_if_error_defn = ir.CheckIfErrorDefn([(type_to_ir(type), type.exception_message)
                                               for type in module.custom_types if type.is_exception_class])
    return ir.Module(body=custom_types_defns + [check_if_error_defn] + writer.function_defns + stmt_writer.stmts)
