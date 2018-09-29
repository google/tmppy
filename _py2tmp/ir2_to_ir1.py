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
from _py2tmp import ir1
from _py2tmp import ir2
from _py2tmp import ir1_to_ir0

from typing import List, Iterator, Optional, Union

class Writer:
    def write(self, elem: ir1.Union[ir1.FunctionDefn, ir1.Assignment, ir1.Assert, ir1.CustomType, ir1.CheckIfErrorDefn, ir1.UnpackingAssignment, ir1.CheckIfErrorStmt]): ...  # pragma: no cover

class FunWriter(Writer):
    def __init__(self):
        self.elems = []  # type: List[ir1.Union[ir1.FunctionDefn, ir1.Assignment, ir1.Assert, ir1.CustomType, ir1.CheckIfErrorDefn, ir1.UnpackingAssignment, ir1.CheckIfErrorStmt]]

    def write(self, elem: ir1.Union[ir1.FunctionDefn, ir1.Assignment, ir1.Assert, ir1.CustomType, ir1.CheckIfErrorDefn, ir1.UnpackingAssignment, ir1.CheckIfErrorStmt]):
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

def custom_type_to_ir1(expr_type: ir2.CustomType):
    return ir1.CustomType(name=expr_type.name,
                          arg_types=[ir1.CustomTypeArgDecl(name=arg.name, expr_type=type_to_ir1(arg.expr_type))
                                     for arg in expr_type.arg_types])

def type_to_ir1(expr_type: ir2.ExprType):
    if isinstance(expr_type, ir2.BoolType):
        return ir1.BoolType()
    elif isinstance(expr_type, ir2.IntType):
        return ir1.IntType()
    elif isinstance(expr_type, ir2.TypeType):
        return ir1.TypeType()
    elif isinstance(expr_type, ir2.BottomType):
        return ir1.BottomType()
    elif isinstance(expr_type, ir2.ErrorOrVoidType):
        return ir1.ErrorOrVoidType()
    elif isinstance(expr_type, ir2.ListType):
        return ir1.ListType(type_to_ir1(expr_type.elem_type))
    elif isinstance(expr_type, ir2.FunctionType):
        return ir1.FunctionType(argtypes=[type_to_ir1(arg)
                                          for arg in expr_type.argtypes],
                                returns=type_to_ir1(expr_type.returns))
    elif isinstance(expr_type, ir2.CustomType):
        return custom_type_to_ir1(expr_type)
    else:
        raise NotImplementedError('Unexpected type: %s' % str(expr_type.__class__))

def expr_to_ir1(expr: Union[ir2.Expr, ir2.PatternExpr]) -> ir1.Expr:
    if isinstance(expr, (ir2.VarReference, ir2.VarReferencePattern)):
        return var_reference_to_ir1(expr)
    elif isinstance(expr, ir2.MatchExpr):
        return match_expr_to_ir1(expr)
    elif isinstance(expr, ir2.BoolLiteral):
        return bool_literal_to_ir1(expr)
    elif isinstance(expr, ir2.IntLiteral):
        return int_literal_to_ir1(expr)
    elif isinstance(expr, (ir2.AtomicTypeLiteral, ir2.AtomicTypeLiteralPattern)):
        return atomic_type_literal_to_ir1(expr)
    elif isinstance(expr, (ir2.PointerTypeExpr, ir2.PointerTypePatternExpr)):
        return pointer_type_expr_to_ir1(expr)
    elif isinstance(expr, (ir2.ReferenceTypeExpr, ir2.ReferenceTypePatternExpr)):
        return reference_type_expr_to_ir1(expr)
    elif isinstance(expr, (ir2.RvalueReferenceTypeExpr, ir2.RvalueReferenceTypePatternExpr)):
        return rvalue_reference_type_expr_to_ir1(expr)
    elif isinstance(expr, (ir2.ConstTypeExpr, ir2.ConstTypePatternExpr)):
        return const_type_expr_to_ir1(expr)
    elif isinstance(expr, (ir2.ArrayTypeExpr, ir2.ArrayTypePatternExpr)):
        return array_type_expr_to_ir1(expr)
    elif isinstance(expr, (ir2.FunctionTypeExpr, ir2.FunctionTypePatternExpr)):
        return function_type_expr_to_ir1(expr)
    elif isinstance(expr, ir2.TemplateInstantiationExpr):
        return template_instantiation_expr_to_ir1(expr)
    elif isinstance(expr, ir2.TemplateMemberAccessExpr):
        return template_member_access_expr_to_ir1(expr)
    elif isinstance(expr, (ir2.ListExpr, ir2.ListPatternExpr)):
        return list_expr_to_ir1(expr)
    elif isinstance(expr, ir2.FunctionCall):
        return function_call_to_ir1(expr)
    elif isinstance(expr, ir2.EqualityComparison):
        return equality_comparison_to_ir1(expr)
    elif isinstance(expr, ir2.AttributeAccessExpr):
        return attribute_access_expr_to_ir1(expr)
    elif isinstance(expr, ir2.NotExpr):
        return not_expr_to_ir1(expr)
    elif isinstance(expr, ir2.IntComparisonExpr):
        return int_comparison_expr_to_ir1(expr)
    elif isinstance(expr, ir2.UnaryMinusExpr):
        return unary_minus_expr_to_ir1(expr)
    elif isinstance(expr, ir2.IntListSumExpr):
        return int_list_sum_expr_to_ir1(expr)
    elif isinstance(expr, ir2.BoolListAllExpr):
        return bool_list_all_expr_to_ir1(expr)
    elif isinstance(expr, ir2.BoolListAnyExpr):
        return bool_list_any_expr_to_ir1(expr)
    elif isinstance(expr, ir2.IntBinaryOpExpr):
        return int_binary_op_expr_to_ir1(expr)
    elif isinstance(expr, ir2.ListConcatExpr):
        return list_concat_expr_to_ir1(expr)
    elif isinstance(expr, ir2.ListComprehensionExpr):
        return list_comprehension_expr_to_ir1(expr)
    elif isinstance(expr, ir2.IsInstanceExpr):
        return is_instance_expr_to_ir1(expr)
    elif isinstance(expr, ir2.SafeUncheckedCast):
        return safe_unchecked_cast_expr_to_ir1(expr)
    elif isinstance(expr, ir2.AddToSetExpr):
        return add_to_set_expr_to_ir1(expr)
    elif isinstance(expr, ir2.SetEqualityComparison):
        return set_equality_comparison_expr_to_ir1(expr)
    elif isinstance(expr, ir2.ListToSetExpr):
        return list_to_set_expr_to_ir1(expr)
    elif isinstance(expr, ir2.SetToListExpr):
        return set_to_list_expr_to_ir1(expr)
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def type_pattern_expr_to_ir1(expr: ir2.PatternExpr) -> ir1.Expr:
    if isinstance(expr, ir2.VarReferencePattern):
        return var_reference_pattern_to_ir1(expr)
    elif isinstance(expr, ir2.AtomicTypeLiteralPattern):
        return atomic_type_literal_pattern_to_ir1(expr)
    elif isinstance(expr, ir2.PointerTypePatternExpr):
        return pointer_type_pattern_expr_to_ir1(expr)
    elif isinstance(expr, ir2.ReferenceTypePatternExpr):
        return reference_type_pattern_expr_to_ir1(expr)
    elif isinstance(expr, ir2.RvalueReferenceTypePatternExpr):
        return rvalue_reference_type_pattern_expr_to_ir1(expr)
    elif isinstance(expr, ir2.ConstTypePatternExpr):
        return const_type_pattern_expr_to_ir1(expr)
    elif isinstance(expr, ir2.ArrayTypePatternExpr):
        return array_type_pattern_expr_to_ir1(expr)
    elif isinstance(expr, ir2.FunctionTypePatternExpr):
        return function_type_pattern_expr_to_ir1(expr)
    elif isinstance(expr, ir2.TemplateInstantiationPatternExpr):
        return template_instantiation_pattern_expr_to_ir1(expr)
    elif isinstance(expr, ir2.ListPatternExpr):
        return list_expr_to_ir1(expr)
    # TODO: Re-enable this once it's possible to use bools/ints in template instantiations.
    # elif isinstance(expr, ir2.BoolLiteral):
    #     return bool_literal_to_ir1(expr)
    # elif isinstance(expr, ir2.IntLiteral):
    #     return int_literal_to_ir1(expr)
    else:
        raise NotImplementedError('Unexpected pattern expression: %s' % str(expr.__class__))

def function_arg_decl_to_ir1(decl: ir2.FunctionArgDecl):
    return ir1.FunctionArgDecl(expr_type=type_to_ir1(decl.expr_type),
                               name=decl.name)

def var_reference_to_ir1(var: Union[ir2.VarReference, ir2.VarReferencePattern]):
    return ir1.VarReference(expr_type=type_to_ir1(var.expr_type),
                            name=var.name,
                            is_global_function=var.is_global_function,
                            is_function_that_may_throw=var.is_function_that_may_throw)

def match_expr_to_ir1(match_expr: ir2.MatchExpr):
    return ir1.MatchExpr(matched_vars=[var_reference_to_ir1(var)
                                       for var in match_expr.matched_vars],
                         match_cases=[ir1.MatchCase(type_patterns=[type_pattern_expr_to_ir1(pattern)
                                                                   for pattern in match_case.type_patterns],
                                                    matched_var_names=match_case.matched_var_names,
                                                    matched_variadic_var_names=match_case.matched_variadic_var_names,
                                                    expr=function_call_to_ir1(match_case.expr))
                                      for match_case in match_expr.match_cases])

def bool_literal_to_ir1(literal: ir2.BoolLiteral):
    return ir1.BoolLiteral(value=literal.value)

def int_literal_to_ir1(literal: ir2.IntLiteral):
    return ir1.IntLiteral(value=literal.value)

def atomic_type_literal_to_ir1(literal: Union[ir2.AtomicTypeLiteral, ir2.AtomicTypeLiteralPattern]):
    return ir1.AtomicTypeLiteral(cpp_type=literal.cpp_type, expr_type=type_to_ir1(literal.expr_type))

def pointer_type_expr_to_ir1(expr: Union[ir2.PointerTypeExpr, ir2.PointerTypePatternExpr]):
    return ir1.PointerTypeExpr(expr_to_ir1(expr.type_expr))

def reference_type_expr_to_ir1(expr: Union[ir2.ReferenceTypeExpr, ir2.ReferenceTypePatternExpr]):
    return ir1.ReferenceTypeExpr(expr_to_ir1(expr.type_expr))

def rvalue_reference_type_expr_to_ir1(expr: Union[ir2.RvalueReferenceTypeExpr, ir2.RvalueReferenceTypePatternExpr]):
    return ir1.RvalueReferenceTypeExpr(expr_to_ir1(expr.type_expr))

def const_type_expr_to_ir1(expr: Union[ir2.ConstTypeExpr, ir2.ConstTypePatternExpr]):
    return ir1.ConstTypeExpr(expr_to_ir1(expr.type_expr))

def array_type_expr_to_ir1(expr: Union[ir2.ArrayTypeExpr, ir2.ArrayTypePatternExpr]):
    return ir1.ArrayTypeExpr(expr_to_ir1(expr.type_expr))

def function_type_expr_to_ir1(expr: Union[ir2.FunctionTypeExpr, ir2.FunctionTypePatternExpr]):
    return ir1.FunctionTypeExpr(return_type_expr=var_reference_to_ir1(expr.return_type_expr),
                                arg_list_expr=var_reference_to_ir1(expr.arg_list_expr))

def template_instantiation_expr_to_ir1(expr: ir2.TemplateInstantiationExpr):
    return ir1.TemplateInstantiationWithList(template_name=expr.template_atomic_cpp_type,
                                             arg_list_expr=expr_to_ir1(expr.arg_list_expr),
                                             instantiation_might_trigger_static_asserts=True)

def template_member_access_expr_to_ir1(expr: ir2.TemplateMemberAccessExpr):
    return ir1.TemplateMemberAccess(var_reference_to_ir1(expr.class_type_expr),
                                    expr.member_name,
                                    var_reference_to_ir1(expr.arg_list_expr))

def list_expr_to_ir1(list_expr: Union[ir2.ListExpr, ir2.ListPatternExpr]):
    # [1, 2, x]
    #
    # Becomes:
    #
    # IntList<1, 2, x>

    list_template_name = ir1_to_ir0.list_template_name_for_type(ir1_to_ir0.type_to_ir0(type_to_ir1(list_expr.elem_type)))

    arg_exprs = [expr_to_ir1(elem_expr) for elem_expr in list_expr.elems]
    if isinstance(list_expr, ir2.ListPatternExpr) and list_expr.list_extraction_expr:
        arg_exprs.append(ir1.ParameterPackExpansion(ir1.VarReference(expr_type=ir1.ParameterPackType(type_to_ir1(list_expr.list_extraction_expr)),
                                                                     name=list_expr.list_extraction_expr.name,
                                                                     is_global_function=list_expr.list_extraction_expr.is_global_function,
                                                                     is_function_that_may_throw=list_expr.list_extraction_expr.is_function_that_may_throw)))

    return ir1.TemplateInstantiation(template_name=list_template_name,
                                     arg_exprs=arg_exprs,
                                     expr_type=type_to_ir1(list_expr.expr_type),
                                     instantiation_might_trigger_static_asserts=False)

def function_call_to_ir1(call_expr: ir2.FunctionCall):
    return ir1.FunctionCall(fun=var_reference_to_ir1(call_expr.fun),
                            args=[var_reference_to_ir1(arg_expr)
                                  for arg_expr in call_expr.args])

def equality_comparison_to_ir1(comparison_expr: ir2.EqualityComparison):
    return ir1.EqualityComparison(lhs=var_reference_to_ir1(comparison_expr.lhs),
                                  rhs=var_reference_to_ir1(comparison_expr.rhs))

def attribute_access_expr_to_ir1(attribute_access_expr: ir2.AttributeAccessExpr):
    return ir1.AttributeAccessExpr(var=var_reference_to_ir1(attribute_access_expr.var),
                                   attribute_name=attribute_access_expr.attribute_name,
                                   expr_type=type_to_ir1(attribute_access_expr.expr_type))

def not_expr_to_ir1(expr: ir2.NotExpr):
    return ir1.NotExpr(var=var_reference_to_ir1(expr.var))

def int_comparison_expr_to_ir1(expr: ir2.IntComparisonExpr):
    return ir1.IntComparisonExpr(lhs=var_reference_to_ir1(expr.lhs),
                                 rhs=var_reference_to_ir1(expr.rhs),
                                 op=expr.op)

def unary_minus_expr_to_ir1(expr: ir2.UnaryMinusExpr):
    return ir1.UnaryMinusExpr(var=var_reference_to_ir1(expr.var))

def int_list_sum_expr_to_ir1(expr: ir2.IntListSumExpr):
    # sum(l)
    #
    # Becomes:
    #
    # Int64ListSum<l>::value

    template_instantiation = ir1.TemplateInstantiation(template_name='Int64ListSum',
                                                       arg_exprs=[expr_to_ir1(expr.var)],
                                                       instantiation_might_trigger_static_asserts=False)

    return ir1.ClassMemberAccess(class_type_expr=template_instantiation,
                                 member_name='value',
                                 member_type=ir1.IntType())

def bool_list_all_expr_to_ir1(expr: ir2.BoolListAllExpr):
    # all(l)
    #
    # Becomes:
    #
    # BoolListAll<l>::value

    template_instantiation = ir1.TemplateInstantiation(template_name='BoolListAll',
                                                       arg_exprs=[expr_to_ir1(expr.var)],
                                                       instantiation_might_trigger_static_asserts=False)

    return ir1.ClassMemberAccess(class_type_expr=template_instantiation,
                                 member_name='value',
                                 member_type=ir1.BoolType())


def bool_list_any_expr_to_ir1(expr: ir2.BoolListAnyExpr):
    # any(l)
    #
    # Becomes:
    #
    # BoolListAny<l>::value

    template_instantiation = ir1.TemplateInstantiation(template_name='BoolListAny',
                                                       arg_exprs=[expr_to_ir1(expr.var)],
                                                       instantiation_might_trigger_static_asserts=False)

    return ir1.ClassMemberAccess(class_type_expr=template_instantiation,
                                 member_name='value',
                                 member_type=ir1.BoolType())

def int_binary_op_expr_to_ir1(expr: ir2.IntBinaryOpExpr):
    return ir1.IntBinaryOpExpr(lhs=var_reference_to_ir1(expr.lhs),
                               rhs=var_reference_to_ir1(expr.rhs),
                               op=expr.op)

def list_concat_expr_to_ir1(expr: ir2.ListConcatExpr):
    # l1 + l2
    #
    # Becomes (if l1 and l2 are lists of ints):
    #
    # Int64ListConcat<l1, l2>::type

    elem_kind = ir1_to_ir0.type_to_ir0(type_to_ir1(expr.expr_type.elem_type)).kind
    if elem_kind == ir0.ExprKind.BOOL:
        list_concat_template_name = 'BoolListConcat'
    elif elem_kind == ir0.ExprKind.INT64:
        list_concat_template_name = 'Int64ListConcat'
    elif elem_kind == ir0.ExprKind.TYPE:
        list_concat_template_name = 'TypeListConcat'
    else:
        raise NotImplementedError('elem_kind: %s' % elem_kind)

    template_instantiation = ir1.TemplateInstantiation(template_name=list_concat_template_name,
                                                       arg_exprs=[expr_to_ir1(expr.lhs), expr_to_ir1(expr.rhs)],
                                                       instantiation_might_trigger_static_asserts=False)

    return ir1.ClassMemberAccess(class_type_expr=template_instantiation,
                                 member_name='type',
                                 member_type=type_to_ir1(expr.expr_type))

def list_comprehension_expr_to_ir1(expr: ir2.ListComprehensionExpr):
    return ir1.ListComprehensionExpr(list_var=var_reference_to_ir1(expr.list_var),
                                     loop_var=var_reference_to_ir1(expr.loop_var),
                                     result_elem_expr=function_call_to_ir1(expr.result_elem_expr))

def is_instance_expr_to_ir1(expr: ir2.IsInstanceExpr):
    return ir1.IsInstanceExpr(var=var_reference_to_ir1(expr.var),
                              checked_type=custom_type_to_ir1(expr.checked_type))

def safe_unchecked_cast_expr_to_ir1(expr: ir2.SafeUncheckedCast):
    return ir1.SafeUncheckedCast(var=var_reference_to_ir1(expr.var),
                                 expr_type=custom_type_to_ir1(expr.expr_type))

def add_to_set_expr_to_ir1(expr: ir2.AddToSetExpr):
    return ir1.AddToSetExpr(set_expr=var_reference_to_ir1(expr.set_expr),
                            elem_expr=var_reference_to_ir1(expr.elem_expr))

def set_equality_comparison_expr_to_ir1(expr: ir2.SetEqualityComparison):
    assert isinstance(expr.lhs.expr_type, ir2.ListType)
    return ir1.SetEqualityComparison(lhs=var_reference_to_ir1(expr.lhs),
                                     rhs=var_reference_to_ir1(expr.rhs),
                                     elem_type=type_to_ir1(expr.lhs.expr_type.elem_type))

def list_to_set_expr_to_ir1(expr: ir2.ListToSetExpr):
    assert isinstance(expr.var.expr_type, ir2.ListType)
    return ir1.ListToSetExpr(var=var_reference_to_ir1(expr.var),
                             elem_type=type_to_ir1(expr.var.expr_type.elem_type))

def set_to_list_expr_to_ir1(expr: ir2.SetToListExpr):
    return var_reference_to_ir1(expr.var)

def var_reference_pattern_to_ir1(expr: ir2.VarReferencePattern):
    return ir1.VarReference(expr_type=type_to_ir1(expr.expr_type),
                            name=expr.name,
                            is_global_function=expr.is_global_function,
                            is_function_that_may_throw=expr.is_function_that_may_throw)

def atomic_type_literal_pattern_to_ir1(expr: ir2.AtomicTypeLiteralPattern):
    return ir1.AtomicTypeLiteral(cpp_type=expr.cpp_type, expr_type=type_to_ir1(expr.expr_type))

def pointer_type_pattern_expr_to_ir1(expr: ir2.PointerTypePatternExpr):
    return ir1.PointerTypeExpr(type_pattern_expr_to_ir1(expr.type_expr))

def reference_type_pattern_expr_to_ir1(expr: ir2.ReferenceTypePatternExpr):
    return ir1.ReferenceTypeExpr(type_pattern_expr_to_ir1(expr.type_expr))

def rvalue_reference_type_pattern_expr_to_ir1(expr: ir2.RvalueReferenceTypePatternExpr):
    return ir1.RvalueReferenceTypeExpr(type_pattern_expr_to_ir1(expr.type_expr))

def const_type_pattern_expr_to_ir1(expr: ir2.ConstTypePatternExpr):
    return ir1.ConstTypeExpr(type_pattern_expr_to_ir1(expr.type_expr))

def array_type_pattern_expr_to_ir1(expr: ir2.ArrayTypePatternExpr):
    return ir1.ArrayTypeExpr(type_pattern_expr_to_ir1(expr.type_expr))

def function_type_pattern_expr_to_ir1(expr: ir2.FunctionTypePatternExpr):
    return ir1.FunctionTypeExpr(return_type_expr=type_pattern_expr_to_ir1(expr.return_type_expr),
                                arg_list_expr=type_pattern_expr_to_ir1(expr.arg_list_expr))

def template_instantiation_pattern_expr_to_ir1(expr: ir2.TemplateInstantiationPatternExpr):
    arg_exprs = [type_pattern_expr_to_ir1(elem_expr) for elem_expr in expr.arg_exprs]
    if expr.list_extraction_arg_expr:
        arg_exprs.append(ir1.ParameterPackExpansion(ir1.VarReference(expr_type=ir1.ParameterPackType(type_to_ir1(expr.list_extraction_arg_expr.expr_type)),
                                                                     name=expr.list_extraction_arg_expr.name,
                                                                     is_global_function=expr.list_extraction_arg_expr.is_global_function,
                                                                     is_function_that_may_throw=expr.list_extraction_arg_expr.is_function_that_may_throw)))
    return ir1.TemplateInstantiation(template_name=expr.template_atomic_cpp_type,
                                     arg_exprs=arg_exprs,
                                     instantiation_might_trigger_static_asserts=False)

def assert_to_ir1(assert_stmt: ir2.Assert, writer: Writer):
    writer.write(ir1.Assert(var=var_reference_to_ir1(assert_stmt.var),
                            message=assert_stmt.message))

def assignment_to_ir1(assignment: ir2.Assignment, writer: Writer):
    writer.write(ir1.Assignment(lhs=var_reference_to_ir1(assignment.lhs),
                                lhs2=var_reference_to_ir1(assignment.lhs2) if assignment.lhs2 else None,
                                rhs=expr_to_ir1(assignment.rhs)))

def unpacking_assignment_to_ir1(assignment: ir2.UnpackingAssignment, writer: Writer):
    writer.write(ir1.UnpackingAssignment(lhs_list=[var_reference_to_ir1(var)
                                                   for var in assignment.lhs_list],
                                         rhs=var_reference_to_ir1(assignment.rhs),
                                         error_message=assignment.error_message))

def return_stmt_to_ir1(return_stmt: ir2.ReturnStmt, writer: StmtWriter):
    writer.write(ir1.ReturnStmt(result=var_reference_to_ir1(return_stmt.result) if return_stmt.result else None,
                                error=var_reference_to_ir1(return_stmt.error) if return_stmt.error else None))

def if_stmt_to_ir1(if_stmt: ir2.IfStmt, writer: StmtWriter):
    if_branch_writer = StmtWriter(writer.fun_writer, writer.current_fun_return_type)
    stmts_to_ir1(if_stmt.if_stmts, if_branch_writer)

    else_branch_writer = StmtWriter(writer.fun_writer, writer.current_fun_return_type)
    stmts_to_ir1(if_stmt.else_stmts, else_branch_writer)

    writer.write(ir1.IfStmt(cond=var_reference_to_ir1(if_stmt.cond),
                            if_stmts=if_branch_writer.stmts,
                            else_stmts=else_branch_writer.stmts))

def check_if_error_defn_to_ir1(toplevel_elem: ir2.CheckIfErrorDefn, writer: Writer):
    writer.write(ir1.CheckIfErrorDefn(error_types_and_messages=[(custom_type_to_ir1(error_type), message)
                                                                for error_type, message in toplevel_elem.error_types_and_messages]))

def check_if_error_to_ir1(toplevel_elem: ir2.CheckIfError, writer: Writer):
    writer.write(ir1.CheckIfErrorStmt(var_reference_to_ir1(toplevel_elem.var)))

def stmts_to_ir1(stmts: List[ir2.Stmt], writer: StmtWriter):
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, ir2.IfStmt):
            if_stmt_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.Assignment):
            assignment_to_ir1(stmt, writer)
        elif isinstance(stmt, ir2.UnpackingAssignment):
            unpacking_assignment_to_ir1(stmt, writer)
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
                                  description=function_defn.description,
                                  args=[function_arg_decl_to_ir1(arg)
                                        for arg in function_defn.args],
                                  body=stmt_writer.stmts,
                                  return_type=return_type))

def module_to_ir1(module: ir2.Module):
    writer = FunWriter()
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
        elif isinstance(toplevel_elem, ir2.CheckIfError):
            check_if_error_to_ir1(toplevel_elem, writer)
        else:
            raise NotImplementedError('Unexpected toplevel element: %s' % str(toplevel_elem.__class__))

    return ir1.Module(body=writer.elems,
                      public_names=module.public_names)
