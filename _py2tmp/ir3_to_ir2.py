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
from _py2tmp import ir2
from _py2tmp import ir3
from _py2tmp import utils
from typing import List, Iterator, Optional, Dict
from contextlib import contextmanager

class Writer:
    def obfuscate_identifier(self, identifier: str) -> str: ...  # pragma: no cover

class FunWriter(Writer):
    def __init__(self, identifier_generator: Iterator[str]):
        self.identifier_generator = identifier_generator
        self.is_error_fun_ref = self.new_var(ir2.FunctionType(argtypes=[ir2.ErrorOrVoidType()],
                                                              returns=ir2.BoolType()),
                                             is_global_function=True)
        self.function_defns = [self._create_is_error_fun_defn()]
        self.obfuscated_identifiers_by_identifier = defaultdict(lambda: self.new_id())  # type: Dict[str, str]

    def new_id(self):
        return next(self.identifier_generator)

    def obfuscate_identifier(self, identifier: str):
        return self.obfuscated_identifiers_by_identifier[identifier]

    def new_var(self, type: ir2.ExprType, is_global_function: bool = False):
        return ir2.VarReference(type=type,
                                name=self.new_id(),
                                is_global_function=is_global_function,
                                is_function_that_may_throw=isinstance(type, ir2.FunctionType))

    def write_function(self, fun_defn: ir2.FunctionDefn):
        self.function_defns.append(fun_defn)

    def _create_is_error_fun_defn(self):
        # def is_error(x: ErrorOrVoid):
        #   v = Type('void')
        #   b = (x == v)
        #   b2 = not b
        #   return b2

        x_var = self.new_var(type=ir2.ErrorOrVoidType())
        arg_decls = [ir2.FunctionArgDecl(type=x_var.type, name=x_var.name)]

        stmt_writer = StmtWriter(self,
                                 current_fun_return_type=ir2.BoolType(),
                                 current_fun_args=arg_decls,
                                 current_fun_name=self.is_error_fun_ref.name,
                                 try_except_contexts=[])
        v_var = stmt_writer.new_var_for_expr(ir2.AtomicTypeLiteral('void'))
        b_var = stmt_writer.new_var_for_expr(ir2.EqualityComparison(lhs=x_var, rhs=v_var))
        b2_var = stmt_writer.new_var_for_expr(ir2.NotExpr(b_var))
        stmt_writer.write_stmt(ir2.ReturnStmt(result=b2_var, error=None))

        return ir2.FunctionDefn(name=self.is_error_fun_ref.name,
                                description='The is_error (meta)function',
                                args=arg_decls,
                                body=stmt_writer.stmts,
                                return_type=ir2.BoolType())

class TryExceptContext:
    def __init__(self,
                 caught_exception_type: ir2.CustomType,
                 caught_exception_name: str,
                 except_fun_call_expr: ir2.FunctionCall):
        self.caught_exception_type = caught_exception_type
        self.caught_exception_name = caught_exception_name
        self.except_fun_call_expr = except_fun_call_expr

class StmtWriter(Writer):
    def __init__(self,
                 fun_writer: FunWriter,
                 current_fun_name: str,
                 current_fun_args: List[ir2.FunctionArgDecl],
                 current_fun_return_type: Optional[ir2.ExprType],
                 try_except_contexts: List[TryExceptContext]):
        for context in try_except_contexts:
            assert context.except_fun_call_expr.type == current_fun_return_type
        self.fun_writer = fun_writer
        self.current_fun_name = current_fun_name
        self.current_fun_args = current_fun_args
        self.current_fun_return_type = current_fun_return_type
        self.stmts = []  # type: List[ir2.Stmt]
        self.try_except_contexts = try_except_contexts.copy()

    def write_function(self, fun_defn: ir2.FunctionDefn):
        self.fun_writer.write_function(fun_defn)

    def write_stmt(self, stmt: ir2.Stmt):
        self.stmts.append(stmt)

    def new_id(self):
        return self.fun_writer.new_id()

    def obfuscate_identifier(self, identifier: str):
        return self.fun_writer.obfuscate_identifier(identifier)

    def new_var(self, type: ir2.ExprType):
        return self.fun_writer.new_var(type)

    def new_var_for_expr(self, expr: ir2.Expr):
        var = self.fun_writer.new_var(expr.type)
        self.write_stmt(ir2.Assignment(lhs=var, rhs=expr))
        return var

    def new_var_for_expr_with_error_checking(self, expr: ir2.Expr):
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
            error_var = self.fun_writer.new_var(ir2.ErrorOrVoidType())
            self.write_stmt(ir2.Assignment(lhs=x_var, lhs2=error_var, rhs=expr))
            b_var = self.new_var_for_expr(ir2.FunctionCall(fun=self.fun_writer.is_error_fun_ref,
                                                           args=[error_var]))

            outer_if_branch_writer = StmtWriter(self.fun_writer,
                                                self.current_fun_name,
                                                self.current_fun_args,
                                                self.current_fun_return_type,
                                                try_except_contexts=self.try_except_contexts)
            for context in self.try_except_contexts:
                if_branch_writer = StmtWriter(self.fun_writer,
                                              self.current_fun_name,
                                              self.current_fun_args,
                                              self.current_fun_return_type,
                                              try_except_contexts=self.try_except_contexts)
                if_branch_writer.write_stmt(ir2.Assignment(lhs=ir2.VarReference(type=context.caught_exception_type,
                                                                                name=self.obfuscate_identifier(context.caught_exception_name),
                                                                                is_global_function=False,
                                                                                is_function_that_may_throw=False),
                                                           rhs=ir2.SafeUncheckedCast(error_var,
                                                                                     type=context.caught_exception_type)))
                res_i = if_branch_writer.new_var(type=self.current_fun_return_type)
                err_i = if_branch_writer.new_var(type=ir2.ErrorOrVoidType())
                if_branch_writer.write_stmt(ir2.Assignment(lhs=res_i,
                                                           lhs2=err_i,
                                                           rhs=context.except_fun_call_expr))
                if_branch_writer.write_stmt(ir2.ReturnStmt(result=res_i, error=err_i))

                b_i = outer_if_branch_writer.new_var_for_expr(ir2.IsInstanceExpr(error_var, context.caught_exception_type))
                outer_if_branch_writer.write_stmt(ir2.IfStmt(cond=b_i,
                                                             if_stmts=if_branch_writer.stmts,
                                                             else_stmts=[]))

            outer_if_branch_writer.write_stmt(ir2.ReturnStmt(result=None, error=error_var))

            self.write_stmt(ir2.IfStmt(cond=b_var,
                                       if_stmts=outer_if_branch_writer.stmts,
                                       else_stmts=[]))
            return x_var
        else:
            # This statement is at top-level.

            # x, err = <expr>

            x_var = self.fun_writer.new_var(expr.type)
            error_var = self.fun_writer.new_var(ir2.ErrorOrVoidType())
            self.write_stmt(ir2.Assignment(lhs=x_var, lhs2=error_var, rhs=expr))
            self.write_stmt(ir2.CheckIfError(error_var))
            return x_var

    @contextmanager
    def enter_try_except_context(self, context: TryExceptContext):
        self.try_except_contexts.append(context)
        yield
        context1 = self.try_except_contexts.pop()
        assert context1 is context

def type_to_ir2(type: ir3.ExprType):
    if isinstance(type, ir3.BoolType):
        return ir2.BoolType()
    elif isinstance(type, ir3.IntType):
        return ir2.IntType()
    elif isinstance(type, ir3.TypeType):
        return ir2.TypeType()
    elif isinstance(type, ir3.BottomType):
        return ir2.BottomType()
    elif isinstance(type, ir3.ListType):
        return ir2.ListType(elem_type=type_to_ir2(type.elem_type))
    elif isinstance(type, ir3.SetType):
        return ir2.ListType(elem_type=type_to_ir2(type.elem_type))
    elif isinstance(type, ir3.FunctionType):
        return ir2.FunctionType(argtypes=[type_to_ir2(arg)
                                          for arg in type.argtypes],
                                returns=type_to_ir2(type.returns))
    elif isinstance(type, ir3.CustomType):
        return ir2.CustomType(name=type.name,
                              arg_types=[ir2.CustomTypeArgDecl(name=arg.name, type=type_to_ir2(arg.type))
                                         for arg in type.arg_types])
    else:
        raise NotImplementedError('Unexpected type: %s' % str(type.__class__))

def expr_to_ir2(expr: ir3.Expr, writer: StmtWriter) -> ir2.VarReference:
    if isinstance(expr, ir3.VarReference):
        return var_reference_to_ir2(expr, writer)
    elif isinstance(expr, ir3.MatchExpr):
        return match_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.BoolLiteral):
        return bool_literal_to_ir2(expr, writer)
    elif isinstance(expr, ir3.IntLiteral):
        return int_literal_to_ir2(expr, writer)
    elif isinstance(expr, ir3.AtomicTypeLiteral):
        return atomic_type_literal_to_ir2(expr, writer)
    elif isinstance(expr, ir3.PointerTypeExpr):
        return pointer_type_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.ReferenceTypeExpr):
        return reference_type_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.RvalueReferenceTypeExpr):
        return rvalue_reference_type_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.ConstTypeExpr):
        return const_type_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.ArrayTypeExpr):
        return array_type_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.FunctionTypeExpr):
        return function_type_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.TemplateInstantiationExpr):
        return template_instantiation_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.TemplateMemberAccessExpr):
        return template_member_access_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.ListExpr):
        return list_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.SetExpr):
        return set_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.FunctionCall):
        return function_call_to_ir2(expr, writer)
    elif isinstance(expr, ir3.EqualityComparison):
        return equality_comparison_to_ir2(expr, writer)
    elif isinstance(expr, ir3.AttributeAccessExpr):
        return attribute_access_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.AndExpr):
        return and_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.OrExpr):
        return or_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.NotExpr):
        return not_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.IntUnaryMinusExpr):
        return int_unary_minus_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.IntListSumExpr):
        return int_list_sum_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.IntSetSumExpr):
        return int_set_sum_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.BoolListAllExpr):
        return bool_list_all_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.BoolSetAllExpr):
        return bool_set_all_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.BoolListAnyExpr):
        return bool_list_any_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.BoolSetAnyExpr):
        return bool_set_any_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.IntComparisonExpr):
        return int_comparison_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.IntBinaryOpExpr):
        return int_binary_op_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.ListConcatExpr):
        return list_concat_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.ListComprehension):
        return list_comprehension_expr_to_ir2(expr, writer)
    elif isinstance(expr, ir3.SetComprehension):
        return set_comprehension_expr_to_ir2(expr, writer)
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def type_pattern_expr_to_ir2(expr: ir3.Expr, writer: StmtWriter) -> ir2.PatternExpr:
    if isinstance(expr, ir3.VarReference):
        return var_reference_to_ir2_pattern(expr, writer)
    elif isinstance(expr, ir3.AtomicTypeLiteral):
        return atomic_type_literal_to_ir2_type_pattern(expr, writer)
    # TODO: Re-enable this once it's possible to use bools in template instantiations.
    # elif isinstance(expr, ir3.BoolLiteral):
    #     return bool_literal_to_ir2_type_pattern(expr, writer)
    elif isinstance(expr, ir3.PointerTypeExpr):
        return pointer_type_expr_to_ir2_type_pattern(expr, writer)
    elif isinstance(expr, ir3.ReferenceTypeExpr):
        return reference_type_expr_to_ir2_type_pattern(expr, writer)
    elif isinstance(expr, ir3.RvalueReferenceTypeExpr):
        return rvalue_reference_type_expr_to_ir2_type_pattern(expr, writer)
    elif isinstance(expr, ir3.ConstTypeExpr):
        return const_type_expr_to_ir2_type_pattern(expr, writer)
    elif isinstance(expr, ir3.ArrayTypeExpr):
        return array_type_expr_to_ir2_type_pattern(expr, writer)
    elif isinstance(expr, ir3.FunctionTypeExpr):
        return function_type_expr_to_ir2_type_pattern(expr, writer)
    elif isinstance(expr, ir3.TemplateInstantiationExpr):
        return template_instantiation_expr_to_ir2_type_pattern(expr, writer)
    elif isinstance(expr, ir3.ListExpr):
        return list_expr_to_ir2_type_pattern(expr, writer)
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def function_arg_decl_to_ir2(decl: ir3.FunctionArgDecl, writer: Writer):
    return ir2.FunctionArgDecl(type=type_to_ir2(decl.type),
                               name=writer.obfuscate_identifier(decl.name))

def var_reference_to_ir2(var: ir3.VarReference, writer: StmtWriter):
    return ir2.VarReference(type=type_to_ir2(var.type),
                            name=var.name if var.is_global_function else writer.obfuscate_identifier(var.name),
                            is_global_function=var.is_global_function,
                            is_function_that_may_throw=var.is_function_that_may_throw)

def _select_arbitrary_forwarded_arg(args: List[ir2.FunctionArgDecl]):
    for arg in args:
        if not isinstance(arg.type, ir2.FunctionType):
            selected_arg = arg
            break
    else:
        selected_arg = args[0]

    return ir2.VarReference(type=selected_arg.type,
                            name=selected_arg.name,
                            is_global_function=False,
                            is_function_that_may_throw=isinstance(selected_arg.type, ir2.FunctionType))

def match_expr_to_ir2(match_expr: ir3.MatchExpr, writer: StmtWriter):
    matched_vars = [expr_to_ir2(expr, writer)
                    for expr in match_expr.matched_exprs]

    match_cases = []
    for match_case in match_expr.match_cases:
        match_case_writer = StmtWriter(writer.fun_writer,
                                       writer.current_fun_name,
                                       writer.current_fun_args,
                                       type_to_ir2(match_expr.type),
                                       writer.try_except_contexts)
        match_case_var = expr_to_ir2(match_case.expr, match_case_writer)
        match_case_writer.write_stmt(ir2.ReturnStmt(result=match_case_var, error=None))

        forwarded_vars = ir2.get_unique_free_variables_in_stmts(match_case_writer.stmts)

        if not forwarded_vars:
            forwarded_vars = [_select_arbitrary_forwarded_arg(writer.current_fun_args)]

        match_fun_name = writer.new_id()
        arg_decls = [ir2.FunctionArgDecl(type=var.type, name=var.name) for var in forwarded_vars]
        writer.write_function(ir2.FunctionDefn(name=match_fun_name,
                                               description='(meta)function wrapping the code in a branch of a match expression from the function %s' % writer.current_fun_name,
                                               args=arg_decls,
                                               body=match_case_writer.stmts,
                                               return_type=match_case_var.type))
        match_fun_ref = ir2.VarReference(type=ir2.FunctionType(argtypes=[var.type
                                                                         for var in forwarded_vars],
                                                               returns=match_case_var.type),
                                         name=match_fun_name,
                                         is_global_function=True,
                                         is_function_that_may_throw=True)

        match_cases.append(ir2.MatchCase(type_patterns=[type_pattern_expr_to_ir2(type_pattern, writer)
                                                        for type_pattern in match_case.type_patterns],
                                         matched_var_names=[writer.obfuscate_identifier(var_name)
                                                           for var_name in match_case.matched_var_names],
                                         matched_variadic_var_names=[writer.obfuscate_identifier(var_name)
                                                                     for var_name in match_case.matched_variadic_var_names],
                                         expr=ir2.FunctionCall(fun=match_fun_ref,
                                                               args=forwarded_vars)))

    return writer.new_var_for_expr_with_error_checking(ir2.MatchExpr(matched_vars, match_cases))

def bool_literal_to_ir2(literal: ir3.BoolLiteral, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.BoolLiteral(value=literal.value))

def int_literal_to_ir2(literal: ir3.IntLiteral, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.IntLiteral(value=literal.value))

def atomic_type_literal_to_ir2(literal: ir3.AtomicTypeLiteral, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.AtomicTypeLiteral(cpp_type=literal.cpp_type))

def pointer_type_expr_to_ir2(expr: ir3.PointerTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.PointerTypeExpr(expr_to_ir2(expr.type_expr, writer)))

def reference_type_expr_to_ir2(expr: ir3.ReferenceTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.ReferenceTypeExpr(expr_to_ir2(expr.type_expr, writer)))

def rvalue_reference_type_expr_to_ir2(expr: ir3.RvalueReferenceTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.RvalueReferenceTypeExpr(expr_to_ir2(expr.type_expr, writer)))

def const_type_expr_to_ir2(expr: ir3.ConstTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.ConstTypeExpr(expr_to_ir2(expr.type_expr, writer)))

def array_type_expr_to_ir2(expr: ir3.ArrayTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.ArrayTypeExpr(expr_to_ir2(expr.type_expr, writer)))

def function_type_expr_to_ir2(expr: ir3.FunctionTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.FunctionTypeExpr(return_type_expr=expr_to_ir2(expr.return_type_expr, writer),
                                                        arg_list_expr=expr_to_ir2(expr.arg_list_expr, writer)))

def template_instantiation_expr_to_ir2(expr: ir3.TemplateInstantiationExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.TemplateInstantiationExpr(template_atomic_cpp_type=expr.template_atomic_cpp_type,
                                                                 arg_list_expr=expr_to_ir2(expr.arg_list_expr, writer)))

def template_member_access_expr_to_ir2(expr: ir3.TemplateMemberAccessExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.TemplateMemberAccessExpr(class_type_expr=expr_to_ir2(expr.class_type_expr, writer),
                                                                member_name=expr.member_name,
                                                                arg_list_expr=expr_to_ir2(expr.arg_list_expr, writer)))

def list_expr_to_ir2(list_expr: ir3.ListExpr, writer: StmtWriter):
    assert list_expr.list_extraction_expr is None
    elem_vars = [expr_to_ir2(elem_expr, writer)
                 for elem_expr in list_expr.elem_exprs]
    return writer.new_var_for_expr(ir2.ListExpr(elem_type=type_to_ir2(list_expr.elem_type),
                                                elems=elem_vars))

def set_expr_to_ir2(set_expr: ir3.SetExpr, writer: StmtWriter):
    result = writer.new_var_for_expr(ir2.ListExpr(elem_type=type_to_ir2(set_expr.elem_type),
                                                  elems=[]))

    elem_vars = [expr_to_ir2(elem_expr, writer)
                 for elem_expr in set_expr.elem_exprs]
    for var in elem_vars:
        result = writer.new_var_for_expr(ir2.AddToSetExpr(set_expr=result,
                                                          elem_expr=var))
    return result

def function_call_to_ir2(call_expr: ir3.FunctionCall, writer: StmtWriter):
    fun_var = expr_to_ir2(call_expr.fun_expr, writer)
    arg_vars = [expr_to_ir2(arg_expr, writer)
                for arg_expr in call_expr.args]
    if fun_var.is_function_that_may_throw:
        return writer.new_var_for_expr_with_error_checking(ir2.FunctionCall(fun=fun_var,
                                                                            args=arg_vars))
    else:
        return writer.new_var_for_expr(ir2.FunctionCall(fun=fun_var,
                                                        args=arg_vars))

def equality_comparison_to_ir2(comparison_expr: ir3.EqualityComparison, writer: StmtWriter):
    if isinstance(comparison_expr.lhs.type, ir3.SetType):
        return writer.new_var_for_expr(ir2.SetEqualityComparison(lhs=expr_to_ir2(comparison_expr.lhs, writer),
                                                                 rhs=expr_to_ir2(comparison_expr.rhs, writer)))
    else:
        return writer.new_var_for_expr(ir2.EqualityComparison(lhs=expr_to_ir2(comparison_expr.lhs, writer),
                                                              rhs=expr_to_ir2(comparison_expr.rhs, writer)))

def attribute_access_expr_to_ir2(attribute_access_expr: ir3.AttributeAccessExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.AttributeAccessExpr(var=expr_to_ir2(attribute_access_expr.expr, writer),
                                                           attribute_name=attribute_access_expr.attribute_name,
                                                           type=type_to_ir2(attribute_access_expr.type)))

def and_expr_to_ir2(expr: ir3.AndExpr, writer: StmtWriter):
    # y = f() and g()
    #
    # becomes:
    #
    # if f():
    #   x = g()
    # else:
    #   x = False
    # y = x

    lhs_var = expr_to_ir2(expr.lhs, writer)

    if_branch_writer = StmtWriter(writer.fun_writer,
                                  writer.current_fun_name,
                                  writer.current_fun_args,
                                  writer.current_fun_return_type,
                                  writer.try_except_contexts)
    rhs_var = expr_to_ir2(expr.rhs, if_branch_writer)

    writer.write_stmt(ir2.IfStmt(cond=lhs_var,
                                 if_stmts=if_branch_writer.stmts,
                                 else_stmts=[ir2.Assignment(lhs=rhs_var,
                                                            rhs=ir2.BoolLiteral(value=False))]))

    return rhs_var

def or_expr_to_ir2(expr: ir3.OrExpr, writer: StmtWriter):
    # y = f() or g()
    #
    # becomes:
    #
    # if f():
    #   x = True
    # else:
    #   x = g()
    # y = x

    lhs_var = expr_to_ir2(expr.lhs, writer)

    else_branch_writer = StmtWriter(writer.fun_writer,
                                    writer.current_fun_name,
                                    writer.current_fun_args,
                                    writer.current_fun_return_type,
                                    writer.try_except_contexts)
    rhs_var = expr_to_ir2(expr.rhs, else_branch_writer)

    writer.write_stmt(ir2.IfStmt(cond=lhs_var,
                                 if_stmts=[ir2.Assignment(lhs=rhs_var,
                                                          rhs=ir2.BoolLiteral(value=True))],
                                 else_stmts=else_branch_writer.stmts))

    return rhs_var

def not_expr_to_ir2(expr: ir3.NotExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.NotExpr(expr_to_ir2(expr.expr, writer)))

def int_unary_minus_expr_to_ir2(expr: ir3.IntUnaryMinusExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.UnaryMinusExpr(expr_to_ir2(expr.expr, writer)))

def int_list_sum_expr_to_ir2(expr: ir3.IntListSumExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.IntListSumExpr(expr_to_ir2(expr.list_expr, writer)))

def int_set_sum_expr_to_ir2(expr: ir3.IntSetSumExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.IntListSumExpr(expr_to_ir2(expr.set_expr, writer)))

def bool_list_all_expr_to_ir2(expr: ir3.BoolListAllExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.BoolListAllExpr(expr_to_ir2(expr.list_expr, writer)))

def bool_set_all_expr_to_ir2(expr: ir3.BoolSetAllExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.BoolListAllExpr(expr_to_ir2(expr.set_expr, writer)))

def bool_list_any_expr_to_ir2(expr: ir3.BoolListAnyExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.BoolListAnyExpr(expr_to_ir2(expr.list_expr, writer)))

def bool_set_any_expr_to_ir2(expr: ir3.BoolSetAnyExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.BoolListAnyExpr(expr_to_ir2(expr.set_expr, writer)))

def int_comparison_expr_to_ir2(expr: ir3.IntComparisonExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.IntComparisonExpr(lhs=expr_to_ir2(expr.lhs, writer),
                                                         rhs=expr_to_ir2(expr.rhs, writer),
                                                         op=expr.op))

def int_binary_op_expr_to_ir2(expr: ir3.IntBinaryOpExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.IntBinaryOpExpr(lhs=expr_to_ir2(expr.lhs, writer),
                                                       rhs=expr_to_ir2(expr.rhs, writer),
                                                       op=expr.op))

def list_concat_expr_to_ir2(expr: ir3.ListConcatExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir2.ListConcatExpr(lhs=expr_to_ir2(expr.lhs, writer),
                                                      rhs=expr_to_ir2(expr.rhs, writer)))

def deconstructed_list_comprehension_expr_to_ir2(list_var: ir3.VarReference,
                                                 loop_var: ir2.VarReference,
                                                 result_elem_expr: ir2.Expr,
                                                 writer: StmtWriter):
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

    result_elem_type = type_to_ir2(result_elem_expr.type)
    helper_fun_writer = StmtWriter(writer.fun_writer,
                                   current_fun_name=writer.current_fun_name,
                                   current_fun_args=writer.current_fun_args,
                                   current_fun_return_type=result_elem_type,
                                   # We can't forward the try_except_contexts here because the return type is different,
                                   # but it's ok because a list comprehension can't contain "raise" statements (while
                                   # of course it can throw indirectly).
                                   try_except_contexts=[])
    helper_fun_writer.write_stmt(ir2.ReturnStmt(result=expr_to_ir2(result_elem_expr, helper_fun_writer),
                                                error=None))
    forwarded_vars = ir2.get_unique_free_variables_in_stmts(helper_fun_writer.stmts)
    if not forwarded_vars:
        if writer.current_fun_args:
            forwarded_vars = [_select_arbitrary_forwarded_arg(writer.current_fun_args)]
        else:
            forwarded_vars = [writer.new_var_for_expr(expr=ir2.AtomicTypeLiteral('void'))]

    helper_fun_name = writer.new_id()
    writer.write_function(ir2.FunctionDefn(name=helper_fun_name,
                                           description='(meta)function wrapping the result expression in a list/set comprehension from the function %s' % writer.current_fun_name,
                                           args=[ir2.FunctionArgDecl(type=var.type, name=var.name)
                                                 for var in forwarded_vars],
                                           body=helper_fun_writer.stmts,
                                           return_type=result_elem_type))

    helper_fun_call = ir2.FunctionCall(fun=ir2.VarReference(name=helper_fun_name,
                                                            type=ir2.FunctionType(argtypes=[var.type
                                                                                            for var in forwarded_vars],
                                                                                  returns=result_elem_type),
                                                            is_global_function=True,
                                                            is_function_that_may_throw=True),
                                       args=forwarded_vars)
    return writer.new_var_for_expr_with_error_checking(ir2.ListComprehensionExpr(list_var=list_var,
                                                                                 loop_var=var_reference_to_ir2(loop_var, writer),
                                                                                 result_elem_expr=helper_fun_call))


def list_comprehension_expr_to_ir2(expr: ir3.ListComprehension, writer: StmtWriter):
    l_var = expr_to_ir2(expr.list_expr, writer)

    return deconstructed_list_comprehension_expr_to_ir2(list_var=l_var,
                                                        loop_var=expr.loop_var,
                                                        result_elem_expr=expr.result_elem_expr,
                                                        writer=writer)


def set_comprehension_expr_to_ir2(expr: ir3.SetComprehension, writer: StmtWriter):
    # {f(x, y) * 2
    #  for x in s}
    #
    # Becomes:
    #
    # l = set_to_list(s)
    # l2 = [f(x, y) * 2
    #       for x in l] # (in fact, this will be converted further)
    # list_to_set(l2)

    s_var = expr_to_ir2(expr.set_expr, writer)
    l_var = writer.new_var_for_expr(ir2.SetToListExpr(s_var))

    l2_var = deconstructed_list_comprehension_expr_to_ir2(list_var=l_var,
                                                          loop_var=expr.loop_var,
                                                          result_elem_expr=expr.result_elem_expr,
                                                          writer=writer)

    return writer.new_var_for_expr(ir2.ListToSetExpr(l2_var))

def var_reference_to_ir2_pattern(var: ir3.VarReference, writer: StmtWriter):
    return ir2.VarReferencePattern(type=type_to_ir2(var.type),
                                   name=var.name if var.is_global_function else writer.obfuscate_identifier(var.name),
                                   is_global_function=var.is_global_function,
                                   is_function_that_may_throw=var.is_function_that_may_throw)

def atomic_type_literal_to_ir2_type_pattern(expr: ir3.AtomicTypeLiteral, writer: StmtWriter):
    return ir2.AtomicTypeLiteralPattern(expr.cpp_type)

# TODO: Re-enable this once it's possible to use bools in template instantiations.
# def bool_literal_to_ir2_type_pattern(expr: ir3.BoolLiteral, writer: StmtWriter):
#     return ir2.BoolLiteral(expr.value)

def pointer_type_expr_to_ir2_type_pattern(expr: ir3.PointerTypeExpr, writer: StmtWriter):
    return ir2.PointerTypePatternExpr(type_pattern_expr_to_ir2(expr.type_expr, writer))

def reference_type_expr_to_ir2_type_pattern(expr: ir3.ReferenceTypeExpr, writer: StmtWriter):
    return ir2.ReferenceTypePatternExpr(type_pattern_expr_to_ir2(expr.type_expr, writer))

def rvalue_reference_type_expr_to_ir2_type_pattern(expr: ir3.RvalueReferenceTypeExpr, writer: StmtWriter):
    return ir2.RvalueReferenceTypePatternExpr(type_pattern_expr_to_ir2(expr.type_expr, writer))

def const_type_expr_to_ir2_type_pattern(expr: ir3.ConstTypeExpr, writer: StmtWriter):
    return ir2.ConstTypePatternExpr(type_pattern_expr_to_ir2(expr.type_expr, writer))

def array_type_expr_to_ir2_type_pattern(expr: ir3.ArrayTypeExpr, writer: StmtWriter):
    return ir2.ArrayTypePatternExpr(type_pattern_expr_to_ir2(expr.type_expr, writer))

def function_type_expr_to_ir2_type_pattern(expr: ir3.FunctionTypeExpr, writer: StmtWriter):
    return ir2.FunctionTypePatternExpr(return_type_expr=type_pattern_expr_to_ir2(expr.return_type_expr, writer),
                                       arg_list_expr=type_pattern_expr_to_ir2(expr.arg_list_expr, writer))

def template_instantiation_expr_to_ir2_type_pattern(expr: ir3.TemplateInstantiationExpr, writer: StmtWriter):
    # This is the only ListExpr that's allowed in a template instantiation in a pattern.
    assert isinstance(expr.arg_list_expr, ir3.ListExpr)
    arg_exprs = [type_pattern_expr_to_ir2(arg_expr, writer) for arg_expr in expr.arg_list_expr.elem_exprs]
    list_extraction_expr = expr.arg_list_expr.list_extraction_expr
    return ir2.TemplateInstantiationPatternExpr(template_atomic_cpp_type=expr.template_atomic_cpp_type,
                                                arg_exprs=arg_exprs,
                                                list_extraction_arg_expr=var_reference_to_ir2_pattern(list_extraction_expr, writer) if list_extraction_expr else None)

def list_expr_to_ir2_type_pattern(expr: ir3.ListExpr, writer: StmtWriter):
    return ir2.ListPatternExpr(elem_type=type_to_ir2(expr.elem_type),
                               elems=[type_pattern_expr_to_ir2(elem_expr, writer)
                                      for elem_expr in expr.elem_exprs],
                               list_extraction_expr = var_reference_to_ir2(expr.list_extraction_expr, writer)
                                                      if expr.list_extraction_expr else None)

def assert_to_ir2(assert_stmt: ir3.Assert, writer: StmtWriter):
    writer.write_stmt(ir2.Assert(var=expr_to_ir2(assert_stmt.expr, writer),
                                 message=assert_stmt.message))

def try_except_stmt_to_ir2(try_except_stmt: ir3.TryExcept,
                          then_stmts: List[ir3.Stmt],
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
        then_stmts_writer = StmtWriter(writer.fun_writer,
                                       writer.current_fun_name,
                                       writer.current_fun_args,
                                       writer.current_fun_return_type,
                                       writer.try_except_contexts)
        stmts_to_ir2(then_stmts, then_stmts_writer)

        then_fun_forwarded_vars = ir2.get_unique_free_variables_in_stmts(then_stmts_writer.stmts)
        if not then_fun_forwarded_vars:
            then_fun_forwarded_vars = [_select_arbitrary_forwarded_arg(writer.current_fun_args)]

        then_fun_defn = ir2.FunctionDefn(name=writer.new_id(),
                                         description='(meta)function wrapping the code after a try-except statement from the function %s' % writer.current_fun_name,
                                         args=[ir2.FunctionArgDecl(type=var.type, name=var.name)
                                               for var in then_fun_forwarded_vars],
                                         body=then_stmts_writer.stmts,
                                         return_type=writer.current_fun_return_type)
        writer.write_function(then_fun_defn)

        then_fun_ref = ir2.VarReference(type=ir2.FunctionType(argtypes=[arg.type
                                                                        for arg in then_fun_defn.args],
                                                              returns=then_fun_defn.return_type),
                                        name=then_fun_defn.name,
                                        is_global_function=True,
                                        is_function_that_may_throw=True)
        then_fun_call_expr = ir2.FunctionCall(fun=then_fun_ref, args=then_fun_forwarded_vars)
    else:
        then_fun_call_expr = None

    except_stmts_writer = StmtWriter(writer.fun_writer,
                                     writer.current_fun_name,
                                     writer.current_fun_args,
                                     writer.current_fun_return_type,
                                     writer.try_except_contexts)
    stmts_to_ir2(try_except_stmt.except_body, except_stmts_writer)
    if then_fun_call_expr and not (try_except_stmt.except_body
                                   and try_except_stmt.except_body[-1].get_return_type().always_returns):
        except_stmts_writer.write_stmt(ir2.ReturnStmt(result=except_stmts_writer.new_var_for_expr_with_error_checking(then_fun_call_expr),
                                                      error=None))

    except_fun_forwarded_vars = ir2.get_unique_free_variables_in_stmts(except_stmts_writer.stmts)
    if not except_fun_forwarded_vars:
        except_fun_forwarded_vars = [_select_arbitrary_forwarded_arg(writer.current_fun_args)]

    except_fun_defn = ir2.FunctionDefn(name=writer.new_id(),
                                       description='(meta)function wrapping the code in an except block from the function %s' % writer.current_fun_name,
                                       args=[ir2.FunctionArgDecl(type=var.type, name=var.name)
                                             for var in except_fun_forwarded_vars],
                                       body=except_stmts_writer.stmts,
                                       return_type=writer.current_fun_return_type)
    writer.write_function(except_fun_defn)

    except_fun_ref = ir2.VarReference(type=ir2.FunctionType(argtypes=[arg.type
                                                                      for arg in except_fun_defn.args],
                                                            returns=except_fun_defn.return_type),
                                      name=except_fun_defn.name,
                                      is_global_function=True,
                                      is_function_that_may_throw=True)
    except_fun_call_expr = ir2.FunctionCall(fun=except_fun_ref, args=except_fun_forwarded_vars)

    with writer.enter_try_except_context(TryExceptContext(type_to_ir2(try_except_stmt.caught_exception_type),
                                                          try_except_stmt.caught_exception_name,
                                                          except_fun_call_expr)):
        stmts_to_ir2(try_except_stmt.try_body, writer)

    if then_fun_call_expr and not (try_except_stmt.try_body
                                   and try_except_stmt.try_body[-1].get_return_type().always_returns):
        writer.write_stmt(ir2.ReturnStmt(result=writer.new_var_for_expr_with_error_checking(then_fun_call_expr),
                                         error=None))

def assignment_to_ir2(assignment: ir3.Assignment, writer: StmtWriter):
    writer.write_stmt(ir2.Assignment(lhs=var_reference_to_ir2(assignment.lhs, writer),
                                     rhs=expr_to_ir2(assignment.rhs, writer)))

def unpacking_assignment_to_ir2(assignment: ir3.UnpackingAssignment, writer: StmtWriter):
    writer.write_stmt(ir2.UnpackingAssignment(lhs_list=[var_reference_to_ir2(var, writer)
                                                        for var in assignment.lhs_list],
                                              rhs=expr_to_ir2(assignment.rhs, writer),
                                              error_message=assignment.error_message))

def return_stmt_to_ir2(return_stmt: ir3.ReturnStmt, writer: StmtWriter):
    writer.write_stmt(ir2.ReturnStmt(result=expr_to_ir2(return_stmt.expr, writer),
                                     error=None))

def raise_stmt_to_ir2(raise_stmt: ir3.RaiseStmt, writer: StmtWriter):
    exception_expr = expr_to_ir2(raise_stmt.expr, writer)
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
            exception_var = ir2.VarReference(type=exception_expr.type,
                                             name=writer.obfuscate_identifier(context.caught_exception_name),
                                             is_global_function=False,
                                             is_function_that_may_throw=False)
            writer.write_stmt(ir2.Assignment(lhs=exception_var, rhs=exception_expr))
            handler_result_var = writer.new_var(context.except_fun_call_expr.type)
            handler_error_var = writer.new_var(ir2.ErrorOrVoidType())
            writer.write_stmt(ir2.Assignment(lhs=handler_result_var,
                                             lhs2=handler_error_var,
                                             rhs=context.except_fun_call_expr))
            writer.write_stmt(ir2.ReturnStmt(result=handler_result_var,
                                             error=handler_error_var))
            break
    else:
        writer.write_stmt(ir2.ReturnStmt(result=None,
                                         error=exception_expr))

def if_stmt_to_ir2(if_stmt: ir3.IfStmt, writer: StmtWriter):
    cond_var = expr_to_ir2(if_stmt.cond_expr, writer)

    if_branch_writer = StmtWriter(writer.fun_writer,
                                  writer.current_fun_name,
                                  writer.current_fun_args,
                                  writer.current_fun_return_type,
                                  writer.try_except_contexts)
    stmts_to_ir2(if_stmt.if_stmts, if_branch_writer)

    else_branch_writer = StmtWriter(writer.fun_writer,
                                    writer.current_fun_name,
                                    writer.current_fun_args,
                                    writer.current_fun_return_type,
                                    writer.try_except_contexts)
    stmts_to_ir2(if_stmt.else_stmts, else_branch_writer)

    writer.write_stmt(ir2.IfStmt(cond=cond_var,
                                 if_stmts=if_branch_writer.stmts,
                                 else_stmts=else_branch_writer.stmts))

def stmts_to_ir2(stmts: List[ir3.Stmt], writer: StmtWriter):
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, ir3.IfStmt):
            if_stmt_to_ir2(stmt, writer)
        elif isinstance(stmt, ir3.Assignment):
            assignment_to_ir2(stmt, writer)
        elif isinstance(stmt, ir3.UnpackingAssignment):
            unpacking_assignment_to_ir2(stmt, writer)
        elif isinstance(stmt, ir3.ReturnStmt):
            return_stmt_to_ir2(stmt, writer)
        elif isinstance(stmt, ir3.RaiseStmt):
            raise_stmt_to_ir2(stmt, writer)
        elif isinstance(stmt, ir3.Assert):
            assert_to_ir2(stmt, writer)
        elif isinstance(stmt, ir3.TryExcept):
            try_except_stmt_to_ir2(stmt, stmts[index + 1:], writer)
            return
        else:
            raise NotImplementedError('Unexpected statement: %s' % str(stmt.__class__))

def function_defn_to_ir2(function_defn: ir3.FunctionDefn, writer: FunWriter):
    return_type = type_to_ir2(function_defn.return_type)
    arg_decls = [function_arg_decl_to_ir2(arg, writer) for arg in function_defn.args]

    stmt_writer = StmtWriter(writer, function_defn.name, arg_decls, return_type, try_except_contexts=[])
    stmts_to_ir2(function_defn.body, stmt_writer)

    writer.write_function(ir2.FunctionDefn(name=function_defn.name,
                                           description='',
                                           args=arg_decls,
                                           body=stmt_writer.stmts,
                                           return_type=return_type))

def module_to_ir2(module: ir3.Module, identifier_generator: Iterator[str]):
    writer = FunWriter(identifier_generator)
    for function_defn in module.function_defns:
        function_defn_to_ir2(function_defn, writer)

    stmt_writer = StmtWriter(writer, current_fun_name='', current_fun_args=[], current_fun_return_type=None, try_except_contexts=[])
    for assertion in module.assertions:
        assert_to_ir2(assertion, stmt_writer)

    custom_types_defns = [type_to_ir2(type) for type in module.custom_types]
    check_if_error_defn = ir2.CheckIfErrorDefn([(type_to_ir2(type), type.exception_message)
                                                for type in module.custom_types if type.is_exception_class])
    return ir2.Module(body=custom_types_defns + [check_if_error_defn] + writer.function_defns + stmt_writer.stmts,
                      public_names=module.public_names)
