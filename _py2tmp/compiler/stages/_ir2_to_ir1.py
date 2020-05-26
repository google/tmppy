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
from contextlib import contextmanager
from typing import List, Iterator, Optional, Dict, Tuple

from _py2tmp.coverage import SourceBranch
from _py2tmp.ir1 import ir1
from _py2tmp.ir1.free_variables import get_unique_free_variables_in_stmts
from _py2tmp.ir2 import ir2, get_return_type


class Writer:
    def obfuscate_identifier(self, identifier: str) -> str: ...  # pragma: no cover

class FunWriter(Writer):
    def __init__(self, identifier_generator: Iterator[str]):
        self.identifier_generator = identifier_generator
        self.is_error_fun_ref = self.new_var(ir1.FunctionType(argtypes=(ir1.ErrorOrVoidType(),),
                                                              returns=ir1.BoolType()),
                                             is_global_function=True)
        self.function_defns = [self._create_is_error_fun_defn()]
        self.obfuscated_identifiers_by_identifier: Dict[str, str] = defaultdict(lambda: self.new_id())

    def new_id(self) -> str:
        return next(self.identifier_generator)

    def obfuscate_identifier(self, identifier: str):
        return self.obfuscated_identifiers_by_identifier[identifier]

    def new_var(self, expr_type: ir1.ExprType, is_global_function: bool = False):
        return ir1.VarReference(expr_type=expr_type,
                                name=self.new_id(),
                                is_global_function=is_global_function,
                                is_function_that_may_throw=isinstance(expr_type, ir1.FunctionType))

    def write_function(self, fun_defn: ir1.FunctionDefn):
        self.function_defns.append(fun_defn)

    def _create_is_error_fun_defn(self):
        # def is_error(x: ErrorOrVoid):
        #   v = Type('void')
        #   b = (x == v)
        #   b2 = not b
        #   return b2

        x_var = self.new_var(expr_type=ir1.ErrorOrVoidType())
        arg_decls = (ir1.FunctionArgDecl(expr_type=x_var.expr_type, name=x_var.name),)

        stmt_writer = StmtWriter(self,
                                 current_fun_return_type=ir1.BoolType(),
                                 current_fun_args=arg_decls,
                                 current_fun_name=self.is_error_fun_ref.name,
                                 try_except_contexts=[])
        v_var = stmt_writer.new_var_for_expr(ir1.AtomicTypeLiteral('void'))
        b_var = stmt_writer.new_var_for_expr(ir1.EqualityComparison(lhs=x_var, rhs=v_var))
        b2_var = stmt_writer.new_var_for_expr(ir1.NotExpr(b_var))
        stmt_writer.write_stmt(ir1.ReturnStmt(result=b2_var, error=None, source_branch=None))

        return ir1.FunctionDefn(name=self.is_error_fun_ref.name,
                                description='The is_error (meta)function',
                                args=arg_decls,
                                body=tuple(stmt_writer.stmts),
                                return_type=ir1.BoolType())

class TryExceptContext:
    def __init__(self,
                 caught_exception_type: ir1.CustomType,
                 caught_exception_name: str,
                 except_fun_call_expr: ir1.FunctionCall):
        self.caught_exception_type = caught_exception_type
        self.caught_exception_name = caught_exception_name
        self.except_fun_call_expr = except_fun_call_expr

class StmtWriter(Writer):
    def __init__(self,
                 fun_writer: FunWriter,
                 current_fun_name: str,
                 current_fun_args: Tuple[ir1.FunctionArgDecl, ...],
                 current_fun_return_type: Optional[ir1.ExprType],
                 try_except_contexts: List[TryExceptContext]):
        for context in try_except_contexts:
            assert context.except_fun_call_expr.expr_type == current_fun_return_type
        self.fun_writer = fun_writer
        self.current_fun_name = current_fun_name
        self.current_fun_args = current_fun_args
        self.current_fun_return_type = current_fun_return_type
        self.stmts: List[ir1.Stmt] = []
        self.try_except_contexts = try_except_contexts.copy()

    def write_function(self, fun_defn: ir1.FunctionDefn):
        self.fun_writer.write_function(fun_defn)

    def write_stmt(self, stmt: ir1.Stmt):
        self.stmts.append(stmt)

    def new_id(self) -> str:
        return self.fun_writer.new_id()

    def obfuscate_identifier(self, identifier: str):
        return self.fun_writer.obfuscate_identifier(identifier)

    def new_var(self, expr_type: ir1.ExprType):
        return self.fun_writer.new_var(expr_type)

    def new_var_for_expr(self, expr: ir1.Expr):
        var = self.fun_writer.new_var(expr.expr_type)
        self.write_stmt(ir1.Assignment(lhs=var, rhs=expr, source_branch=None))
        return var

    def new_var_for_expr_with_error_checking(self, expr: ir1.Expr):
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

            x_var = self.fun_writer.new_var(expr.expr_type)
            error_var = self.fun_writer.new_var(ir1.ErrorOrVoidType())
            self.write_stmt(ir1.Assignment(lhs=x_var, lhs2=error_var, rhs=expr, source_branch=None))
            b_var = self.new_var_for_expr(ir1.FunctionCall(fun=self.fun_writer.is_error_fun_ref,
                                                           args=(error_var,)))

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
                if_branch_writer.write_stmt(ir1.Assignment(lhs=ir1.VarReference(expr_type=context.caught_exception_type,
                                                                                name=self.obfuscate_identifier(context.caught_exception_name),
                                                                                is_global_function=False,
                                                                                is_function_that_may_throw=False),
                                                           rhs=ir1.SafeUncheckedCast(var=error_var,
                                                                                     expr_type=context.caught_exception_type),
                                                           source_branch=None))
                res_i = if_branch_writer.new_var(expr_type=self.current_fun_return_type)
                err_i = if_branch_writer.new_var(expr_type=ir1.ErrorOrVoidType())
                if_branch_writer.write_stmt(ir1.Assignment(lhs=res_i,
                                                           lhs2=err_i,
                                                           rhs=context.except_fun_call_expr,
                                                           source_branch=None))
                if_branch_writer.write_stmt(ir1.ReturnStmt(result=res_i, error=err_i, source_branch=None))

                b_i = outer_if_branch_writer.new_var_for_expr(
                    ir1.IsInstanceExpr(error_var, context.caught_exception_type))
                outer_if_branch_writer.write_stmt(ir1.IfStmt(cond=b_i,
                                                             if_stmts=tuple(if_branch_writer.stmts),
                                                             else_stmts=()))

            outer_if_branch_writer.write_stmt(ir1.ReturnStmt(result=None, error=error_var, source_branch=None))

            self.write_stmt(ir1.IfStmt(cond=b_var,
                                       if_stmts=tuple(outer_if_branch_writer.stmts),
                                       else_stmts=()))
            return x_var
        else:
            # This statement is at top-level.

            # x, err = <expr>

            x_var = self.fun_writer.new_var(expr.expr_type)
            error_var = self.fun_writer.new_var(ir1.ErrorOrVoidType())
            self.write_stmt(ir1.Assignment(lhs=x_var, lhs2=error_var, rhs=expr, source_branch=None))
            self.write_stmt(ir1.CheckIfError(error_var))
            return x_var

    @contextmanager
    def enter_try_except_context(self, context: TryExceptContext):
        self.try_except_contexts.append(context)
        yield
        context1 = self.try_except_contexts.pop()
        assert context1 is context

def type_to_ir1(expr_type: ir2.ExprType):
    if isinstance(expr_type, ir2.BoolType):
        return ir1.BoolType()
    elif isinstance(expr_type, ir2.IntType):
        return ir1.IntType()
    elif isinstance(expr_type, ir2.TypeType):
        return ir1.TypeType()
    elif isinstance(expr_type, ir2.BottomType):
        return ir1.BottomType()
    elif isinstance(expr_type, ir2.ListType):
        return ir1.ListType(elem_type=type_to_ir1(expr_type.elem_type))
    elif isinstance(expr_type, ir2.SetType):
        return ir1.ListType(elem_type=type_to_ir1(expr_type.elem_type))
    elif isinstance(expr_type, ir2.FunctionType):
        return ir1.FunctionType(argtypes=tuple(type_to_ir1(arg)
                                               for arg in expr_type.argtypes),
                                returns=type_to_ir1(expr_type.returns))
    elif isinstance(expr_type, ir2.CustomType):
        return ir1.CustomType(name=expr_type.name,
                              arg_types=tuple(ir1.CustomTypeArgDecl(name=arg.name, expr_type=type_to_ir1(arg.expr_type))
                                              for arg in expr_type.arg_types),
                              constructor_source_branches=expr_type.constructor_source_branches)
    else:
        raise NotImplementedError('Unexpected type: %s' % str(expr_type.__class__))

def expr_to_ir1(expr: ir2.Expr, writer: StmtWriter) -> ir1.VarReference:
    if isinstance(expr, ir2.VarReference):
        return var_reference_to_ir1(expr, writer)
    elif isinstance(expr, ir2.MatchExpr):
        return match_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.BoolLiteral):
        return bool_literal_to_ir1(expr, writer)
    elif isinstance(expr, ir2.IntLiteral):
        return int_literal_to_ir1(expr, writer)
    elif isinstance(expr, ir2.AtomicTypeLiteral):
        return atomic_type_literal_to_ir1(expr, writer)
    elif isinstance(expr, ir2.PointerTypeExpr):
        return pointer_type_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.ReferenceTypeExpr):
        return reference_type_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.RvalueReferenceTypeExpr):
        return rvalue_reference_type_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.ConstTypeExpr):
        return const_type_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.ArrayTypeExpr):
        return array_type_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.FunctionTypeExpr):
        return function_type_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.TemplateInstantiationExpr):
        return template_instantiation_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.TemplateMemberAccessExpr):
        return template_member_access_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.ListExpr):
        return list_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.SetExpr):
        return set_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.FunctionCall):
        return function_call_to_ir1(expr, writer)
    elif isinstance(expr, ir2.EqualityComparison):
        return equality_comparison_to_ir1(expr, writer)
    elif isinstance(expr, ir2.InExpr):
        return in_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.AttributeAccessExpr):
        return attribute_access_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.AndExpr):
        return and_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.OrExpr):
        return or_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.NotExpr):
        return not_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.IntUnaryMinusExpr):
        return int_unary_minus_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.IntListSumExpr):
        return int_list_sum_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.IntSetSumExpr):
        return int_set_sum_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.BoolListAllExpr):
        return bool_list_all_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.BoolSetAllExpr):
        return bool_set_all_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.BoolListAnyExpr):
        return bool_list_any_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.BoolSetAnyExpr):
        return bool_set_any_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.IntComparisonExpr):
        return int_comparison_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.IntBinaryOpExpr):
        return int_binary_op_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.ListConcatExpr):
        return list_concat_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.ListComprehension):
        return list_comprehension_expr_to_ir1(expr, writer)
    elif isinstance(expr, ir2.SetComprehension):
        return set_comprehension_expr_to_ir1(expr, writer)
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def type_pattern_expr_to_ir1(expr: ir2.Expr, writer: StmtWriter) -> ir1.PatternExpr:
    if isinstance(expr, ir2.VarReference):
        return var_reference_to_ir1_pattern(expr, writer)
    elif isinstance(expr, ir2.AtomicTypeLiteral):
        return atomic_type_literal_to_ir1_type_pattern(expr, writer)
    # TODO: Re-enable this once it's possible to use bools in template instantiations.
    # elif isinstance(expr, ir2.BoolLiteral):
    #     return bool_literal_to_ir1_type_pattern(expr, writer)
    elif isinstance(expr, ir2.PointerTypeExpr):
        return pointer_type_expr_to_ir1_type_pattern(expr, writer)
    elif isinstance(expr, ir2.ReferenceTypeExpr):
        return reference_type_expr_to_ir1_type_pattern(expr, writer)
    elif isinstance(expr, ir2.RvalueReferenceTypeExpr):
        return rvalue_reference_type_expr_to_ir1_type_pattern(expr, writer)
    elif isinstance(expr, ir2.ConstTypeExpr):
        return const_type_expr_to_ir1_type_pattern(expr, writer)
    elif isinstance(expr, ir2.ArrayTypeExpr):
        return array_type_expr_to_ir1_type_pattern(expr, writer)
    elif isinstance(expr, ir2.FunctionTypeExpr):
        return function_type_expr_to_ir1_type_pattern(expr, writer)
    elif isinstance(expr, ir2.TemplateInstantiationExpr):
        return template_instantiation_expr_to_ir1_type_pattern(expr, writer)
    elif isinstance(expr, ir2.ListExpr):
        return list_expr_to_ir1_type_pattern(expr, writer)
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def function_arg_decl_to_ir1(decl: ir2.FunctionArgDecl, writer: Writer):
    return ir1.FunctionArgDecl(expr_type=type_to_ir1(decl.expr_type),
                               name=writer.obfuscate_identifier(decl.name))

def var_reference_to_ir1(var: ir2.VarReference, writer: StmtWriter):
    return ir1.VarReference(expr_type=type_to_ir1(var.expr_type),
                            name=var.name if var.is_global_function else writer.obfuscate_identifier(var.name),
                            is_global_function=var.is_global_function,
                            is_function_that_may_throw=var.is_function_that_may_throw)

def _select_arbitrary_forwarded_arg(args: Tuple[ir1.FunctionArgDecl, ...]):
    for arg in args:
        if not isinstance(arg.expr_type, ir1.FunctionType):
            selected_arg = arg
            break
    else:
        selected_arg = args[0]

    return ir1.VarReference(expr_type=selected_arg.expr_type,
                            name=selected_arg.name,
                            is_global_function=False,
                            is_function_that_may_throw=isinstance(selected_arg.expr_type, ir1.FunctionType))

def match_expr_to_ir1(match_expr: ir2.MatchExpr, writer: StmtWriter):
    matched_vars = tuple(expr_to_ir1(expr, writer)
                         for expr in match_expr.matched_exprs)

    match_cases = []
    for match_case in match_expr.match_cases:
        match_case_writer = StmtWriter(writer.fun_writer,
                                       writer.current_fun_name,
                                       writer.current_fun_args,
                                       type_to_ir1(match_expr.expr_type),
                                       writer.try_except_contexts)
        match_case_var = expr_to_ir1(match_case.expr, match_case_writer)
        match_case_writer.write_stmt(ir1.ReturnStmt(result=match_case_var, error=None, source_branch=None))

        forwarded_vars = get_unique_free_variables_in_stmts(match_case_writer.stmts)

        if not forwarded_vars:
            forwarded_vars = (_select_arbitrary_forwarded_arg(writer.current_fun_args),)

        match_fun_name = writer.new_id()
        arg_decls = tuple(ir1.FunctionArgDecl(expr_type=var.expr_type, name=var.name)
                          for var in forwarded_vars)
        writer.write_function(ir1.FunctionDefn(name=match_fun_name,
                                               description='(meta)function wrapping the code in a branch of a match expression from the function %s' % writer.current_fun_name,
                                               args=arg_decls,
                                               body=tuple(match_case_writer.stmts),
                                               return_type=match_case_var.expr_type))
        match_fun_ref = ir1.VarReference(expr_type=ir1.FunctionType(argtypes=tuple(var.expr_type
                                                                                   for var in forwarded_vars),
                                                                    returns=match_case_var.expr_type),
                                         name=match_fun_name,
                                         is_global_function=True,
                                         is_function_that_may_throw=True)

        match_cases.append(ir1.MatchCase(type_patterns=tuple(type_pattern_expr_to_ir1(type_pattern, writer)
                                                             for type_pattern in match_case.type_patterns),
                                         matched_var_names=tuple(writer.obfuscate_identifier(var_name)
                                                                 for var_name in match_case.matched_var_names),
                                         matched_variadic_var_names=tuple(writer.obfuscate_identifier(var_name)
                                                                          for var_name in match_case.matched_variadic_var_names),
                                         expr=ir1.FunctionCall(fun=match_fun_ref,
                                                               args=forwarded_vars),
                                         match_case_start_branch=match_case.match_case_start_branch,
                                         match_case_end_branch=match_case.match_case_end_branch))

    return writer.new_var_for_expr_with_error_checking(ir1.MatchExpr(matched_vars, tuple(match_cases)))

def bool_literal_to_ir1(literal: ir2.BoolLiteral, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.BoolLiteral(value=literal.value))

def int_literal_to_ir1(literal: ir2.IntLiteral, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.IntLiteral(value=literal.value))

def atomic_type_literal_to_ir1(literal: ir2.AtomicTypeLiteral, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.AtomicTypeLiteral(cpp_type=literal.cpp_type))

def pointer_type_expr_to_ir1(expr: ir2.PointerTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.PointerTypeExpr(expr_to_ir1(expr.type_expr, writer)))

def reference_type_expr_to_ir1(expr: ir2.ReferenceTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.ReferenceTypeExpr(expr_to_ir1(expr.type_expr, writer)))

def rvalue_reference_type_expr_to_ir1(expr: ir2.RvalueReferenceTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.RvalueReferenceTypeExpr(expr_to_ir1(expr.type_expr, writer)))

def const_type_expr_to_ir1(expr: ir2.ConstTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.ConstTypeExpr(expr_to_ir1(expr.type_expr, writer)))

def array_type_expr_to_ir1(expr: ir2.ArrayTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.ArrayTypeExpr(expr_to_ir1(expr.type_expr, writer)))

def function_type_expr_to_ir1(expr: ir2.FunctionTypeExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.FunctionTypeExpr(return_type_expr=expr_to_ir1(expr.return_type_expr, writer),
                                                        arg_list_expr=expr_to_ir1(expr.arg_list_expr, writer)))

def template_instantiation_expr_to_ir1(expr: ir2.TemplateInstantiationExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.TemplateInstantiationExpr(template_atomic_cpp_type=expr.template_atomic_cpp_type,
                                                                 arg_list_expr=expr_to_ir1(expr.arg_list_expr, writer)))

def template_member_access_expr_to_ir1(expr: ir2.TemplateMemberAccessExpr, writer: StmtWriter):
    return writer.new_var_for_expr(
        ir1.TemplateMemberAccessExpr(class_type_expr=expr_to_ir1(expr.class_type_expr, writer),
                                     member_name=expr.member_name,
                                     arg_list_expr=expr_to_ir1(expr.arg_list_expr, writer)))

def list_expr_to_ir1(list_expr: ir2.ListExpr, writer: StmtWriter):
    assert list_expr.list_extraction_expr is None
    elem_vars = tuple(expr_to_ir1(elem_expr, writer)
                      for elem_expr in list_expr.elem_exprs)
    return writer.new_var_for_expr(ir1.ListExpr(elem_type=type_to_ir1(list_expr.elem_type),
                                                elems=elem_vars))

def set_expr_to_ir1(set_expr: ir2.SetExpr, writer: StmtWriter):
    result = writer.new_var_for_expr(ir1.ListExpr(elem_type=type_to_ir1(set_expr.elem_type),
                                                  elems=()))

    elem_vars = tuple(expr_to_ir1(elem_expr, writer)
                      for elem_expr in set_expr.elem_exprs)
    for var in elem_vars:
        result = writer.new_var_for_expr(ir1.AddToSetExpr(set_expr=result,
                                                          elem_expr=var))
    return result

def function_call_to_ir1(call_expr: ir2.FunctionCall, writer: StmtWriter):
    fun_var = expr_to_ir1(call_expr.fun_expr, writer)
    arg_vars = tuple(expr_to_ir1(arg_expr, writer)
                     for arg_expr in call_expr.args)
    if fun_var.is_function_that_may_throw:
        return writer.new_var_for_expr_with_error_checking(ir1.FunctionCall(fun=fun_var,
                                                                            args=arg_vars))
    else:
        return writer.new_var_for_expr(ir1.FunctionCall(fun=fun_var,
                                                        args=arg_vars))

def equality_comparison_to_ir1(comparison_expr: ir2.EqualityComparison, writer: StmtWriter):
    if isinstance(comparison_expr.lhs.expr_type, ir2.SetType):
        return writer.new_var_for_expr(ir1.SetEqualityComparison(lhs=expr_to_ir1(comparison_expr.lhs, writer),
                                                                 rhs=expr_to_ir1(comparison_expr.rhs, writer)))
    else:
        return writer.new_var_for_expr(ir1.EqualityComparison(lhs=expr_to_ir1(comparison_expr.lhs, writer),
                                                              rhs=expr_to_ir1(comparison_expr.rhs, writer)))

def in_expr_to_ir1(expr: ir2.InExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.IsInListExpr(lhs=expr_to_ir1(expr.lhs, writer),
                                                    rhs=expr_to_ir1(expr.rhs, writer)))

def attribute_access_expr_to_ir1(attribute_access_expr: ir2.AttributeAccessExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.AttributeAccessExpr(var=expr_to_ir1(attribute_access_expr.expr, writer),
                                                           attribute_name=attribute_access_expr.attribute_name,
                                                           expr_type=type_to_ir1(attribute_access_expr.expr_type)))

def and_expr_to_ir1(expr: ir2.AndExpr, writer: StmtWriter):
    # y = f() and g()
    #
    # becomes:
    #
    # if f():
    #   x = g()
    # else:
    #   x = False
    # y = x

    lhs_var = expr_to_ir1(expr.lhs, writer)

    if_branch_writer = StmtWriter(writer.fun_writer,
                                  writer.current_fun_name,
                                  writer.current_fun_args,
                                  writer.current_fun_return_type,
                                  writer.try_except_contexts)
    rhs_var = expr_to_ir1(expr.rhs, if_branch_writer)

    writer.write_stmt(ir1.IfStmt(cond=lhs_var,
                                 if_stmts=tuple(if_branch_writer.stmts),
                                 else_stmts=(ir1.Assignment(lhs=rhs_var,
                                                            rhs=ir1.BoolLiteral(value=False),
                                                            source_branch=None),)))

    return rhs_var

def or_expr_to_ir1(expr: ir2.OrExpr, writer: StmtWriter):
    # y = f() or g()
    #
    # becomes:
    #
    # if f():
    #   x = True
    # else:
    #   x = g()
    # y = x

    lhs_var = expr_to_ir1(expr.lhs, writer)

    else_branch_writer = StmtWriter(writer.fun_writer,
                                    writer.current_fun_name,
                                    writer.current_fun_args,
                                    writer.current_fun_return_type,
                                    writer.try_except_contexts)
    rhs_var = expr_to_ir1(expr.rhs, else_branch_writer)

    writer.write_stmt(ir1.IfStmt(cond=lhs_var,
                                 if_stmts=(ir1.Assignment(lhs=rhs_var,
                                                          rhs=ir1.BoolLiteral(value=True),
                                                          source_branch=None),),
                                 else_stmts=tuple(else_branch_writer.stmts)))

    return rhs_var

def not_expr_to_ir1(expr: ir2.NotExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.NotExpr(expr_to_ir1(expr.expr, writer)))

def int_unary_minus_expr_to_ir1(expr: ir2.IntUnaryMinusExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.UnaryMinusExpr(expr_to_ir1(expr.expr, writer)))

def int_list_sum_expr_to_ir1(expr: ir2.IntListSumExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.IntListSumExpr(expr_to_ir1(expr.list_expr, writer)))

def int_set_sum_expr_to_ir1(expr: ir2.IntSetSumExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.IntListSumExpr(expr_to_ir1(expr.set_expr, writer)))

def bool_list_all_expr_to_ir1(expr: ir2.BoolListAllExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.BoolListAllExpr(expr_to_ir1(expr.list_expr, writer)))

def bool_set_all_expr_to_ir1(expr: ir2.BoolSetAllExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.BoolListAllExpr(expr_to_ir1(expr.set_expr, writer)))

def bool_list_any_expr_to_ir1(expr: ir2.BoolListAnyExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.BoolListAnyExpr(expr_to_ir1(expr.list_expr, writer)))

def bool_set_any_expr_to_ir1(expr: ir2.BoolSetAnyExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.BoolListAnyExpr(expr_to_ir1(expr.set_expr, writer)))

def int_comparison_expr_to_ir1(expr: ir2.IntComparisonExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.IntComparisonExpr(lhs=expr_to_ir1(expr.lhs, writer),
                                                         rhs=expr_to_ir1(expr.rhs, writer),
                                                         op=expr.op))

def int_binary_op_expr_to_ir1(expr: ir2.IntBinaryOpExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.IntBinaryOpExpr(lhs=expr_to_ir1(expr.lhs, writer),
                                                       rhs=expr_to_ir1(expr.rhs, writer),
                                                       op=expr.op))

def list_concat_expr_to_ir1(expr: ir2.ListConcatExpr, writer: StmtWriter):
    return writer.new_var_for_expr(ir1.ListConcatExpr(lhs=expr_to_ir1(expr.lhs, writer),
                                                      rhs=expr_to_ir1(expr.rhs, writer)))

def deconstructed_list_comprehension_expr_to_ir1(list_var: ir2.VarReference,
                                                 loop_var: ir1.VarReference,
                                                 result_elem_expr: ir1.Expr,
                                                 writer: StmtWriter,
                                                 loop_body_start_branch: SourceBranch,
                                                 loop_exit_branch: SourceBranch):
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

    result_elem_type = type_to_ir1(result_elem_expr.expr_type)
    helper_fun_writer = StmtWriter(writer.fun_writer,
                                   current_fun_name=writer.current_fun_name,
                                   current_fun_args=writer.current_fun_args,
                                   current_fun_return_type=result_elem_type,
                                   # We can't forward the try_except_contexts here because the return type is different,
                                   # but it's ok because a list comprehension can't contain "raise" statements (while
                                   # of course it can throw indirectly).
                                   try_except_contexts=[])
    helper_fun_writer.write_stmt(ir1.ReturnStmt(result=expr_to_ir1(result_elem_expr, helper_fun_writer),
                                                error=None,
                                                source_branch=None))
    forwarded_vars = get_unique_free_variables_in_stmts(helper_fun_writer.stmts)
    if not forwarded_vars:
        if writer.current_fun_args:
            forwarded_vars = [_select_arbitrary_forwarded_arg(writer.current_fun_args)]
        else:
            forwarded_vars = [writer.new_var_for_expr(expr=ir1.AtomicTypeLiteral('void'))]

    helper_fun_name = writer.new_id()
    writer.write_function(ir1.FunctionDefn(name=helper_fun_name,
                                           description='(meta)function wrapping the result expression in a list/set comprehension from the function %s' % writer.current_fun_name,
                                           args=tuple(ir1.FunctionArgDecl(expr_type=var.expr_type, name=var.name)
                                                      for var in forwarded_vars),
                                           body=tuple(helper_fun_writer.stmts),
                                           return_type=result_elem_type))

    helper_fun_call = ir1.FunctionCall(fun=ir1.VarReference(name=helper_fun_name,
                                                            expr_type=ir1.FunctionType(argtypes=tuple(var.expr_type
                                                                                                      for var in forwarded_vars),
                                                                                       returns=result_elem_type),
                                                            is_global_function=True,
                                                            is_function_that_may_throw=True),
                                       args=forwarded_vars)
    return writer.new_var_for_expr_with_error_checking(ir1.ListComprehensionExpr(list_var=list_var,
                                                                                 loop_var=var_reference_to_ir1(loop_var, writer),
                                                                                 result_elem_expr=helper_fun_call,
                                                                                 loop_body_start_branch=loop_body_start_branch,
                                                                                 loop_exit_branch=loop_exit_branch))


def list_comprehension_expr_to_ir1(expr: ir2.ListComprehension, writer: StmtWriter):
    l_var = expr_to_ir1(expr.list_expr, writer)

    return deconstructed_list_comprehension_expr_to_ir1(list_var=l_var,
                                                        loop_var=expr.loop_var,
                                                        result_elem_expr=expr.result_elem_expr,
                                                        writer=writer,
                                                        loop_body_start_branch=expr.loop_body_start_branch,
                                                        loop_exit_branch=expr.loop_exit_branch)


def set_comprehension_expr_to_ir1(expr: ir2.SetComprehension, writer: StmtWriter):
    # {f(x, y) * 2
    #  for x in s}
    #
    # Becomes:
    #
    # l = set_to_list(s)
    # l2 = [f(x, y) * 2
    #       for x in l] # (in fact, this will be converted further)
    # list_to_set(l2)

    s_var = expr_to_ir1(expr.set_expr, writer)
    l_var = writer.new_var_for_expr(ir1.SetToListExpr(s_var))

    l2_var = deconstructed_list_comprehension_expr_to_ir1(list_var=l_var,
                                                          loop_var=expr.loop_var,
                                                          result_elem_expr=expr.result_elem_expr,
                                                          writer=writer,
                                                          loop_body_start_branch=expr.loop_body_start_branch,
                                                          loop_exit_branch=expr.loop_exit_branch)

    return writer.new_var_for_expr(ir1.ListToSetExpr(l2_var))

def var_reference_to_ir1_pattern(var: ir2.VarReference, writer: StmtWriter):
    return ir1.VarReferencePattern(expr_type=type_to_ir1(var.expr_type),
                                   name=var.name if var.is_global_function else writer.obfuscate_identifier(var.name),
                                   is_global_function=var.is_global_function,
                                   is_function_that_may_throw=var.is_function_that_may_throw)

def atomic_type_literal_to_ir1_type_pattern(expr: ir2.AtomicTypeLiteral, writer: StmtWriter):
    return ir1.AtomicTypeLiteralPattern(expr.cpp_type)

# TODO: Re-enable this once it's possible to use bools in template instantiations.
# def bool_literal_to_ir1_type_pattern(expr: ir2.BoolLiteral, writer: StmtWriter):
#     return ir1.BoolLiteral(expr.value)

def pointer_type_expr_to_ir1_type_pattern(expr: ir2.PointerTypeExpr, writer: StmtWriter):
    return ir1.PointerTypePatternExpr(type_pattern_expr_to_ir1(expr.type_expr, writer))

def reference_type_expr_to_ir1_type_pattern(expr: ir2.ReferenceTypeExpr, writer: StmtWriter):
    return ir1.ReferenceTypePatternExpr(type_pattern_expr_to_ir1(expr.type_expr, writer))

def rvalue_reference_type_expr_to_ir1_type_pattern(expr: ir2.RvalueReferenceTypeExpr, writer: StmtWriter):
    return ir1.RvalueReferenceTypePatternExpr(type_pattern_expr_to_ir1(expr.type_expr, writer))

def const_type_expr_to_ir1_type_pattern(expr: ir2.ConstTypeExpr, writer: StmtWriter):
    return ir1.ConstTypePatternExpr(type_pattern_expr_to_ir1(expr.type_expr, writer))

def array_type_expr_to_ir1_type_pattern(expr: ir2.ArrayTypeExpr, writer: StmtWriter):
    return ir1.ArrayTypePatternExpr(type_pattern_expr_to_ir1(expr.type_expr, writer))

def function_type_expr_to_ir1_type_pattern(expr: ir2.FunctionTypeExpr, writer: StmtWriter):
    return ir1.FunctionTypePatternExpr(return_type_expr=type_pattern_expr_to_ir1(expr.return_type_expr, writer),
                                       arg_list_expr=type_pattern_expr_to_ir1(expr.arg_list_expr, writer))

def template_instantiation_expr_to_ir1_type_pattern(expr: ir2.TemplateInstantiationExpr, writer: StmtWriter):
    # This is the only ListExpr that's allowed in a template instantiation in a pattern.
    assert isinstance(expr.arg_list_expr, ir2.ListExpr)
    arg_exprs = tuple(type_pattern_expr_to_ir1(arg_expr, writer)
                      for arg_expr in expr.arg_list_expr.elem_exprs)
    list_extraction_expr = expr.arg_list_expr.list_extraction_expr
    return ir1.TemplateInstantiationPatternExpr(template_atomic_cpp_type=expr.template_atomic_cpp_type,
                                                arg_exprs=arg_exprs,
                                                list_extraction_arg_expr=var_reference_to_ir1_pattern(list_extraction_expr, writer) if list_extraction_expr else None)

def list_expr_to_ir1_type_pattern(expr: ir2.ListExpr, writer: StmtWriter):
    return ir1.ListPatternExpr(elem_type=type_to_ir1(expr.elem_type),
                               elems=tuple(type_pattern_expr_to_ir1(elem_expr, writer)
                                           for elem_expr in expr.elem_exprs),
                               list_extraction_expr = var_reference_to_ir1(expr.list_extraction_expr, writer)
                               if expr.list_extraction_expr else None)

def assert_to_ir1(assert_stmt: ir2.Assert, writer: StmtWriter):
    writer.write_stmt(ir1.Assert(var=expr_to_ir1(assert_stmt.expr, writer),
                                 message=assert_stmt.message,
                                 source_branch=assert_stmt.source_branch))

def pass_stmt_to_ir1(stmt: ir2.PassStmt, writer: StmtWriter):
    writer.write_stmt(ir1.PassStmt(source_branch=stmt.source_branch))

def try_except_stmt_to_ir1(try_except_stmt: ir2.TryExcept,
                           then_stmts: Tuple[ir2.Stmt, ...],
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
        stmts_to_ir1(then_stmts, then_stmts_writer)

        then_fun_forwarded_vars = get_unique_free_variables_in_stmts(then_stmts_writer.stmts)
        if not then_fun_forwarded_vars:
            then_fun_forwarded_vars = [_select_arbitrary_forwarded_arg(writer.current_fun_args)]

        then_fun_defn = ir1.FunctionDefn(name=writer.new_id(),
                                         description='(meta)function wrapping the code after a try-except statement from the function %s' % writer.current_fun_name,
                                         args=tuple(ir1.FunctionArgDecl(expr_type=var.expr_type, name=var.name)
                                                    for var in then_fun_forwarded_vars),
                                         body=tuple(then_stmts_writer.stmts),
                                         return_type=writer.current_fun_return_type)
        writer.write_function(then_fun_defn)

        then_fun_ref = ir1.VarReference(expr_type=ir1.FunctionType(argtypes=tuple(arg.expr_type
                                                                                  for arg in then_fun_defn.args),
                                                                   returns=then_fun_defn.return_type),
                                        name=then_fun_defn.name,
                                        is_global_function=True,
                                        is_function_that_may_throw=True)
        then_fun_call_expr = ir1.FunctionCall(fun=then_fun_ref, args=then_fun_forwarded_vars)
    else:
        then_fun_call_expr = None

    except_stmts_writer = StmtWriter(writer.fun_writer,
                                     writer.current_fun_name,
                                     writer.current_fun_args,
                                     writer.current_fun_return_type,
                                     writer.try_except_contexts)
    except_stmts_writer.write_stmt(ir1.PassStmt(source_branch=try_except_stmt.except_branch))
    stmts_to_ir1(try_except_stmt.except_body, except_stmts_writer)
    if then_fun_call_expr and not get_return_type(try_except_stmt.except_body).always_returns:
        except_stmts_writer.write_stmt(
            ir1.ReturnStmt(result=except_stmts_writer.new_var_for_expr_with_error_checking(then_fun_call_expr),
                           error=None,
                           source_branch=None))

    except_fun_forwarded_vars = get_unique_free_variables_in_stmts(except_stmts_writer.stmts)
    if not except_fun_forwarded_vars:
        except_fun_forwarded_vars = [_select_arbitrary_forwarded_arg(writer.current_fun_args)]

    except_fun_defn = ir1.FunctionDefn(name=writer.new_id(),
                                       description='(meta)function wrapping the code in an except block from the function %s' % writer.current_fun_name,
                                       args=tuple(ir1.FunctionArgDecl(expr_type=var.expr_type, name=var.name)
                                                  for var in except_fun_forwarded_vars),
                                       body=tuple(except_stmts_writer.stmts),
                                       return_type=writer.current_fun_return_type)
    writer.write_function(except_fun_defn)

    except_fun_ref = ir1.VarReference(expr_type=ir1.FunctionType(argtypes=tuple(arg.expr_type
                                                                                for arg in except_fun_defn.args),
                                                                 returns=except_fun_defn.return_type),
                                      name=except_fun_defn.name,
                                      is_global_function=True,
                                      is_function_that_may_throw=True)
    except_fun_call_expr = ir1.FunctionCall(fun=except_fun_ref, args=except_fun_forwarded_vars)

    with writer.enter_try_except_context(TryExceptContext(type_to_ir1(try_except_stmt.caught_exception_type),
                                                          try_except_stmt.caught_exception_name,
                                                          except_fun_call_expr)):
        writer.write_stmt(ir1.PassStmt(source_branch=try_except_stmt.try_branch))
        stmts_to_ir1(try_except_stmt.try_body, writer)

    if then_fun_call_expr and not get_return_type(try_except_stmt.try_body).always_returns:
        writer.write_stmt(ir1.ReturnStmt(result=writer.new_var_for_expr_with_error_checking(then_fun_call_expr),
                                         error=None,
                                         source_branch=None))

def assignment_to_ir1(assignment: ir2.Assignment, writer: StmtWriter):
    writer.write_stmt(ir1.Assignment(lhs=var_reference_to_ir1(assignment.lhs, writer),
                                     rhs=expr_to_ir1(assignment.rhs, writer),
                                     source_branch=assignment.source_branch))

def unpacking_assignment_to_ir1(assignment: ir2.UnpackingAssignment, writer: StmtWriter):
    writer.write_stmt(ir1.UnpackingAssignment(lhs_list=tuple(var_reference_to_ir1(var, writer)
                                                             for var in assignment.lhs_list),
                                              rhs=expr_to_ir1(assignment.rhs, writer),
                                              error_message=assignment.error_message,
                                              source_branch=assignment.source_branch))

def return_stmt_to_ir1(return_stmt: ir2.ReturnStmt, writer: StmtWriter):
    writer.write_stmt(ir1.ReturnStmt(result=expr_to_ir1(return_stmt.expr, writer),
                                     error=None,
                                     source_branch=return_stmt.source_branch))

def raise_stmt_to_ir1(raise_stmt: ir2.RaiseStmt, writer: StmtWriter):
    exception_expr = expr_to_ir1(raise_stmt.expr, writer)
    for context in writer.try_except_contexts:
        if context.caught_exception_type == exception_expr.expr_type:
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
            exception_var = ir1.VarReference(expr_type=exception_expr.expr_type,
                                             name=writer.obfuscate_identifier(context.caught_exception_name),
                                             is_global_function=False,
                                             is_function_that_may_throw=False)
            writer.write_stmt(ir1.Assignment(lhs=exception_var, rhs=exception_expr, source_branch=raise_stmt.source_branch))
            handler_result_var = writer.new_var(context.except_fun_call_expr.expr_type)
            handler_error_var = writer.new_var(ir1.ErrorOrVoidType())
            writer.write_stmt(ir1.Assignment(lhs=handler_result_var,
                                             lhs2=handler_error_var,
                                             rhs=context.except_fun_call_expr,
                                             source_branch=None))
            writer.write_stmt(ir1.ReturnStmt(result=handler_result_var,
                                             error=handler_error_var,
                                             source_branch=None))
            break
    else:
        writer.write_stmt(ir1.ReturnStmt(result=None,
                                         error=exception_expr,
                                         source_branch=raise_stmt.source_branch))

def if_stmt_to_ir1(if_stmt: ir2.IfStmt, writer: StmtWriter):
    cond_var = expr_to_ir1(if_stmt.cond_expr, writer)

    if_branch_writer = StmtWriter(writer.fun_writer,
                                  writer.current_fun_name,
                                  writer.current_fun_args,
                                  writer.current_fun_return_type,
                                  writer.try_except_contexts)
    stmts_to_ir1(if_stmt.if_stmts, if_branch_writer)

    else_branch_writer = StmtWriter(writer.fun_writer,
                                    writer.current_fun_name,
                                    writer.current_fun_args,
                                    writer.current_fun_return_type,
                                    writer.try_except_contexts)
    stmts_to_ir1(if_stmt.else_stmts, else_branch_writer)

    writer.write_stmt(ir1.IfStmt(cond=cond_var,
                                 if_stmts=tuple(if_branch_writer.stmts),
                                 else_stmts=tuple(else_branch_writer.stmts)))

def stmts_to_ir1(stmts: Tuple[ir2.Stmt, ...], writer: StmtWriter):
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, ir2.IfStmt):
            if_stmt_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.Assignment):
            assignment_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.UnpackingAssignment):
            unpacking_assignment_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.ReturnStmt):
            return_stmt_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.RaiseStmt):
            raise_stmt_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.Assert):
            assert_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.TryExcept):
            try_except_stmt_to_ir1(stmt, stmts[index + 1:], writer)
            return
        elif isinstance(stmt, ir2.PassStmt):
            pass_stmt_to_ir1(stmt, writer)
        else:
            raise NotImplementedError('Unexpected statement: %s' % str(stmt.__class__))

def function_defn_to_ir1(function_defn: ir2.FunctionDefn, writer: FunWriter):
    return_type = type_to_ir1(function_defn.return_type)
    arg_decls = tuple(function_arg_decl_to_ir1(arg, writer) for arg in function_defn.args)

    stmt_writer = StmtWriter(writer, function_defn.name, arg_decls, return_type, try_except_contexts=[])
    stmts_to_ir1(function_defn.body, stmt_writer)

    writer.write_function(ir1.FunctionDefn(name=function_defn.name,
                                           description='',
                                           args=arg_decls,
                                           body=tuple(stmt_writer.stmts),
                                           return_type=return_type))

def module_to_ir1(module: ir2.Module, identifier_generator: Iterator[str]):
    writer = FunWriter(identifier_generator)
    for function_defn in module.function_defns:
        function_defn_to_ir1(function_defn, writer)

    stmt_writer = StmtWriter(writer, current_fun_name='', current_fun_args=(), current_fun_return_type=None, try_except_contexts=[])
    for assertion in module.assertions:
        assert_to_ir1(assertion, stmt_writer)

    custom_types_defns = [type_to_ir1(expr_type) for expr_type in module.custom_types]
    check_if_error_defn = ir1.CheckIfErrorDefn(tuple((type_to_ir1(expr_type), expr_type.exception_message)
                                                     for expr_type in module.custom_types if expr_type.is_exception_class))

    pass_stmts = tuple(ir1.PassStmt(stmt.source_branch)
                       for stmt in module.pass_stmts)

    return ir1.Module(body=(*custom_types_defns, check_if_error_defn, *writer.function_defns, *stmt_writer.stmts, *pass_stmts),
                      public_names=frozenset(module.public_names),)
