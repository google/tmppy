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

from typing import Tuple, Optional, Iterator, Union, Callable, Dict, List, Sequence, Set

from _py2tmp.ir0 import GlobalLiterals, NameReplacementTransformation
from _py2tmp.ir0 import Writer as PlainWriter, ToplevelWriter as PlainToplevelWriter, \
    TemplateBodyWriter as PlainTemplateBodyWriter
from _py2tmp.ir0 import ir0, GLOBAL_LITERALS_BY_NAME
from _py2tmp.ir1 import ir1
from _py2tmp.ir1.free_variables import get_unique_free_variables_in_stmts, get_unique_free_variables_in_expr


class Writer(PlainWriter):
    def __init__(self, identifier_generator: Iterator[str]):
        PlainWriter.__init__(self)
        self.identifier_generator = identifier_generator

    def new_id(self) -> str:
        return next(self.identifier_generator)

    def get_is_instance_template_name_for_error(self, error_name: str) -> str: ...  # pragma: no cover

class ToplevelWriter(Writer, PlainToplevelWriter):
    def __init__(self, identifier_generator: Iterator[str]):
        Writer.__init__(self, identifier_generator)
        PlainToplevelWriter.__init__(self)
        self.check_if_error_specializations: List[ir0.TemplateSpecialization] = []
        self.holder_template_name_for_error: Dict[str, str] = dict()
        self.is_instance_template_name_for_error: Dict[str, str] = dict()

    def write_check_if_error_specialization(self, specialization: ir0.TemplateSpecialization):
        self.check_if_error_specializations.append(specialization)

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

class TemplateBodyWriter(Writer, PlainTemplateBodyWriter):
    def __init__(self,
                 parent_writer: Writer,
                 parent_arbitrary_arg: ir0.TemplateArgDecl,
                 parent_return_type: Optional[ir0.ExprType]):
        Writer.__init__(self, parent_writer.identifier_generator)
        PlainTemplateBodyWriter.__init__(self, parent_writer.toplevel_writer)
        self.parent_arbitrary_arg = parent_arbitrary_arg
        self.parent_return_type = parent_return_type
        self.result_body_elements_written = False

    def write_result_body_elements(self,
                                   result_expr: Optional[ir0.Expr],
                                   error_expr: Optional[ir0.Expr]):
        assert self.parent_return_type
        if error_expr:
            assert isinstance(error_expr.expr_type, ir0.TypeType)

        if self.result_body_elements_written:
            # If there are multiple "return statements" in a single specialization only the first one counts.
            return
        self.result_body_elements_written = True

        if self.parent_return_type.kind == ir0.ExprKind.BOOL:
            self.write(ir0.ConstantDef(name='value',
                                       expr=result_expr or ir0.Literal(value=True)))
        elif self.parent_return_type.kind == ir0.ExprKind.INT64:
            self.write(ir0.ConstantDef(name='value',
                                       expr=result_expr or ir0.Literal(value=0)))
        else:
            self.write(ir0.Typedef(name='type',
                                   expr=result_expr or GlobalLiterals.VOID))

        self.write(ir0.Typedef(name='error',
                               expr=error_expr or GlobalLiterals.VOID))

    def create_sibling_writer(self,
                              parent_arbitrary_arg: ir0.TemplateArgDecl,
                              parent_return_type: ir0.ExprType):
        return TemplateBodyWriter(self.toplevel_writer,
                                  parent_arbitrary_arg=parent_arbitrary_arg,
                                  parent_return_type=parent_return_type)

    def get_is_instance_template_name_for_error(self, error_name: str):
        return self.toplevel_writer.get_is_instance_template_name_for_error(error_name)

def type_to_ir0(expr_type: ir1.ExprType):
    if isinstance(expr_type, ir1.BoolType):
        return ir0.BoolType()
    elif isinstance(expr_type, ir1.IntType):
        return ir0.Int64Type()
    elif isinstance(expr_type, ir1.TypeType):
        return ir0.TypeType()
    elif isinstance(expr_type, ir1.CustomType):
        return ir0.TypeType()
    elif isinstance(expr_type, ir1.ErrorOrVoidType):
        return ir0.TypeType()
    elif isinstance(expr_type, ir1.FunctionType):
        return function_type_to_ir0(expr_type)
    elif isinstance(expr_type, ir1.BottomType):
        return ir0.TypeType()
    elif isinstance(expr_type, ir1.ParameterPackType):
        return type_to_ir0(expr_type.element_type)
    elif isinstance(expr_type, ir1.ListType):
        return ir0.TypeType()
    else:
        raise NotImplementedError('Unexpected type: %s' % str(expr_type.__class__))

def function_type_to_ir0(fun_type: ir1.FunctionType):
    return ir0.TemplateType(args=tuple(ir0.TemplateArgType(expr_type=type_to_ir0(arg),
                                                           is_variadic=isinstance(arg, ir1.ParameterPackType))
                                       for arg in fun_type.argtypes))

def expr_to_ir0(expr: ir1.Expr, writer: Writer) -> Tuple[Optional[ir0.Expr], Optional[ir0.Expr]]:
    if isinstance(expr, (ir1.VarReference, ir1.VarReferencePattern)):
        return var_reference_to_ir0(expr), None
    elif isinstance(expr, ir1.MatchExpr):
        assert isinstance(writer, TemplateBodyWriter)
        return match_expr_to_ir0(expr, writer)
    elif isinstance(expr, ir1.BoolLiteral):
        return bool_literal_to_ir0(expr)
    elif isinstance(expr, ir1.IntLiteral):
        return int_literal_to_ir0(expr)
    elif isinstance(expr, (ir1.AtomicTypeLiteral, ir1.AtomicTypeLiteralPattern)):
        return atomic_type_literal_to_ir0(expr)
    elif isinstance(expr, (ir1.PointerTypeExpr, ir1.PointerTypePatternExpr)):
        return pointer_type_expr_to_ir0(expr, writer)
    elif isinstance(expr, (ir1.ReferenceTypeExpr, ir1.ReferenceTypePatternExpr)):
        return reference_type_expr_to_ir0(expr, writer)
    elif isinstance(expr, (ir1.RvalueReferenceTypeExpr, ir1.RvalueReferenceTypePatternExpr)):
        return rvalue_reference_type_expr_to_ir0(expr, writer)
    elif isinstance(expr, (ir1.ConstTypeExpr, ir1.ConstTypePatternExpr)):
        return const_type_expr_to_ir0(expr, writer)
    elif isinstance(expr, (ir1.ArrayTypeExpr, ir1.ArrayTypePatternExpr)):
        return array_type_expr_to_ir0(expr, writer)
    elif isinstance(expr, (ir1.FunctionTypeExpr, ir1.FunctionTypePatternExpr)):
        return function_type_expr_to_ir0(expr, writer)
    elif isinstance(expr, ir1.FunctionCall):
        return function_call_to_ir0(expr, writer)
    elif isinstance(expr, ir1.EqualityComparison):
        return equality_comparison_to_ir0(expr, writer)
    elif isinstance(expr, ir1.IsInListExpr):
        return is_in_list_expr_to_ir0(expr, writer)
    elif isinstance(expr, ir1.AttributeAccessExpr):
        return attribute_access_expr_to_ir0(expr)
    elif isinstance(expr, ir1.NotExpr):
        return not_expr_to_ir0(expr)
    elif isinstance(expr, ir1.UnaryMinusExpr):
        return unary_minus_expr_to_ir0(expr)
    elif isinstance(expr, ir1.IntComparisonExpr):
        return int_comparison_expr_to_ir0(expr)
    elif isinstance(expr, ir1.IntBinaryOpExpr):
        return int_binary_op_expr_to_ir0(expr)
    elif isinstance(expr, ir1.IsInstanceExpr):
        return is_instance_expr_to_ir0(expr, writer)
    elif isinstance(expr, ir1.SafeUncheckedCast):
        return safe_unchecked_cast_expr_to_ir0(expr), None
    elif isinstance(expr, ir1.ListComprehensionExpr):
        return list_comprehension_expr_to_ir0(expr, writer)
    elif isinstance(expr, ir1.TemplateMemberAccessExpr):
        return template_member_access_expr_to_ir0(expr, writer)
    elif isinstance(expr, ir1.TemplateInstantiationExpr):
        return template_instantiation_expr_to_ir0(expr, writer)
    elif isinstance(expr, ir1.AddToSetExpr):
        return add_to_set_expr_to_ir0(expr), None
    elif isinstance(expr, ir1.SetEqualityComparison):
        return set_equality_comparison_expr_to_ir0(expr), None
    elif isinstance(expr, ir1.ListToSetExpr):
        return list_to_set_expr_to_ir0(expr), None
    elif isinstance(expr, ir1.ParameterPackExpansion):
        return parameter_pack_expansion_expr_to_ir0(expr), None
    elif isinstance(expr, (ir1.ListExpr, ir1.ListPatternExpr)):
        return list_expr_to_ir1(expr, writer), None
    elif isinstance(expr, ir1.IntListSumExpr):
        return int_list_sum_expr_to_ir0(expr, writer), None
    elif isinstance(expr, ir1.BoolListAllExpr):
        return bool_list_all_expr_to_ir0(expr, writer), None
    elif isinstance(expr, ir1.BoolListAnyExpr):
        return bool_list_any_expr_to_ir0(expr, writer), None
    elif isinstance(expr, ir1.ListConcatExpr):
        return list_concat_expr_to_ir0(expr, writer), None
    elif isinstance(expr, ir1.TemplateInstantiationPatternExpr):
        return template_instantiation_pattern_expr_to_ir0(expr, writer), None
    elif isinstance(expr, ir1.SetToListExpr):
        return set_to_list_expr_to_ir0(expr), None
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def function_arg_decl_to_ir0(decl: ir1.FunctionArgDecl):
    return ir0.TemplateArgDecl(expr_type=type_to_ir0(decl.expr_type),
                               name=decl.name,
                               is_variadic=isinstance(decl.expr_type, ir1.ParameterPackType))

def var_reference_to_ir0(var: (ir1.VarReference, ir1.VarReferencePattern)):
    if var.is_global_function:
        ir0_type = type_to_ir0(var.expr_type)
        assert isinstance(ir0_type, ir0.TemplateType)
        return ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=var.name,
                                                           args=ir0_type.args,
                                                           is_metafunction_that_may_return_error=True,
                                                           may_be_alias=False)
    else:
        return ir0.AtomicTypeLiteral.for_local(cpp_type=var.name,
                                               expr_type=type_to_ir0(var.expr_type),
                                               is_variadic=isinstance(var.expr_type, ir1.ParameterPackType))

def _create_metafunction_call(template_expr: ir0.Expr,
                              args: Tuple[ir0.Expr, ...],
                              member_type: ir0.ExprType,
                              writer: Writer):
    assert isinstance(template_expr.expr_type, ir0.TemplateType)
    if isinstance(member_type, (ir0.BoolType, ir0.Int64Type)):
        member_name = 'value'
    else:
        member_name = 'type'
    template_instantiation_expr = ir0.TemplateInstantiation(template_expr=template_expr,
                                                            args=args,
                                                            instantiation_might_trigger_static_asserts=True)
    if isinstance(writer, ToplevelWriter) and (not isinstance(template_expr, ir0.AtomicTypeLiteral)
                                               or template_expr.is_metafunction_that_may_return_error):
        # TODO: consider removing this, it seems redundant now.

        # using T = CheckIfError<F<x, y>::error>::type;
        check_if_error_template_instantiation_expr = ir0.TemplateInstantiation(template_expr=GlobalLiterals.CHECK_IF_ERROR,
                                                                               args=(ir0.ClassMemberAccess(inner_expr=template_instantiation_expr,
                                                                                                           member_name='error',
                                                                                                           expr_type=ir0.TypeType()),),
                                                                               instantiation_might_trigger_static_asserts=True)
        writer.write(ir0.Typedef(name=writer.new_id(),
                                 expr=ir0.ClassMemberAccess(inner_expr=check_if_error_template_instantiation_expr,
                                                            member_name='type',
                                                            expr_type=ir0.TypeType())))
    result_expr = ir0.ClassMemberAccess(inner_expr=template_instantiation_expr,
                                        member_name=member_name,
                                        expr_type=member_type)
    if template_expr.is_metafunction_that_may_return_error:
        error_expr = ir0.ClassMemberAccess(inner_expr=template_instantiation_expr,
                                           member_name='error',
                                           expr_type=ir0.TypeType())
    else:
        error_expr = None

    return result_expr, error_expr

def is_trivial_specialization(args: Sequence[ir0.TemplateArgDecl],
                              patterns: [Sequence[ir0.Expr]]):
    patterns_set = set()
    for pattern in patterns:
        if isinstance(pattern, ir0.AtomicTypeLiteral):
            patterns_set.add(pattern.cpp_type)
        elif isinstance(pattern, ir0.VariadicTypeExpansion) and isinstance(pattern.inner_expr, ir0.AtomicTypeLiteral):
            patterns_set.add(pattern.inner_expr.cpp_type)
        else:
            # This is not a trivial pattern, so it can't be part of a trivial specialization.
            return False

    args_set = {arg.name for arg in args}
    return args_set == patterns_set

def _create_metafunction_specialization(args: Tuple[ir0.TemplateArgDecl, ...],
                                        patterns: Optional[Tuple[ir0.Expr, ...]],
                                        body: Tuple[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef], ...]):

    # patterns==None means that this is not actually a specialization (it's the main definition).
    # Instead, patterns==[] means that this is a full specialization.
    if patterns is not None and is_trivial_specialization(args, patterns):
        # This specializes nothing, so it's the main definition. Keeping the explicit patterns would cause
        # C++ compilation errors, so we remove them.
        patterns = None

    return ir0.TemplateSpecialization(args=args, patterns=patterns, body=body, is_metafunction=True)

def match_expr_to_ir0(match_expr: ir1.MatchExpr,
                      writer: TemplateBodyWriter):
    forwarded_args: List[ir1.VarReference] = []
    forwarded_args_names = set()
    for match_case in match_expr.match_cases:
        local_vars = set(match_case.matched_var_names).union(match_case.matched_variadic_var_names)
        for var in get_unique_free_variables_in_expr(match_case.expr):
            if var.name not in local_vars and var.name not in forwarded_args_names:
                forwarded_args_names.add(var.name)
                forwarded_args.append(var)

    if forwarded_args or all(match_case.matched_var_names
                             for match_case in match_expr.match_cases):
        forwarded_args_decls = tuple(ir0.TemplateArgDecl(expr_type=type_to_ir0(var_ref.expr_type),
                                                         name=var_ref.name,
                                                         is_variadic=isinstance(var_ref, ir1.ParameterPackType))
                                     for var_ref in forwarded_args)
        forwarded_args_exprs = tuple(ir0.AtomicTypeLiteral.for_local(cpp_type=var_ref.name,
                                                                     expr_type=type_to_ir0(var_ref.expr_type),
                                                                     is_variadic=isinstance(var_ref, ir1.ParameterPackType))
                                     for var_ref in forwarded_args)
        forwarded_args_patterns = forwarded_args_exprs
    else:
        # We must add a dummy parameter so that the specialization isn't a full specialization.
        dummy_param_name = writer.new_id()
        forwarded_args_decls = (ir0.TemplateArgDecl(expr_type=ir0.TypeType(),
                                                    name=dummy_param_name,
                                                    is_variadic=False),)
        forwarded_args_exprs = (GlobalLiterals.VOID,)
        forwarded_args_patterns = (ir0.AtomicTypeLiteral.for_local(cpp_type=dummy_param_name,
                                                                   expr_type=ir0.TypeType(),
                                                                   is_variadic=False),)

    matched_vars = tuple(var_reference_to_ir0(var)
                         for var in match_expr.matched_vars)

    main_definition = None
    specializations = []
    for match_case in match_expr.match_cases:
        # We use the pre-existing identifiers for typedefs that wrap the variadic type as List<Ts...>.
        variadic_var_name_by_list_var_name = {list_var_name: writer.new_id()
                                              for list_var_name in match_case.matched_variadic_var_names}

        specialization_arg_decls = (
                *forwarded_args_decls,
                *(ir0.TemplateArgDecl(expr_type=ir0.TypeType(), name=arg_name, is_variadic=False)
                   for arg_name in match_case.matched_var_names),
                # So we rename the template params here.
                *(ir0.TemplateArgDecl(expr_type=ir0.TypeType(), name=variadic_var_name_by_list_var_name[arg_name], is_variadic=True)
                   for arg_name in match_case.matched_variadic_var_names))

        # And we rename the pattern expressions here to match.
        pattern_writer = writer.create_sibling_writer(parent_arbitrary_arg=writer.parent_arbitrary_arg,
                                                      parent_return_type=writer.parent_return_type)
        pattern_result_exprs_before_rename = []
        for pattern in match_case.type_patterns:
            result_expr, error_expr = expr_to_ir0(pattern, pattern_writer)
            assert error_expr is None, str(pattern)
            pattern_result_exprs_before_rename.append(result_expr)

        rename_pattern_transformation = NameReplacementTransformation(replacements=variadic_var_name_by_list_var_name)
        renamed_pattern_elems = rename_pattern_transformation.transform_template_body_elems(tuple(pattern_writer.elems))

        for elem in renamed_pattern_elems:
            writer.write(elem)
        pattern_result_exprs_after_rename = [rename_pattern_transformation.transform_expr(expr)
                                             for expr in pattern_result_exprs_before_rename]

        specialization_patterns = (*forwarded_args_patterns, *pattern_result_exprs_after_rename)

        match_case_writer = TemplateBodyWriter(writer,
                                               parent_arbitrary_arg=writer.parent_arbitrary_arg,
                                               parent_return_type=type_to_ir0(match_case.expr.expr_type))
        if match_case.match_case_start_branch:
            match_case_writer.write(ir0.NoOpStmt(match_case.match_case_start_branch))
        if match_case.match_case_end_branch:
            match_case_writer.write(ir0.NoOpStmt(match_case.match_case_end_branch))
        for list_var_name, variadic_var_name in variadic_var_name_by_list_var_name.items():
            match_case_writer.write(ir0.Typedef(name=list_var_name,
                                                expr=ir0.TemplateInstantiation(template_expr=GlobalLiterals.LIST,
                                                                                    instantiation_might_trigger_static_asserts=False,
                                                                                    args=(ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type=variadic_var_name,
                                                                                                                                                    expr_type=ir0.TypeType(),
                                                                                                                                                    is_variadic=True)),))))

        expr_ir0, error_expr = expr_to_ir0(match_case.expr, match_case_writer)
        match_case_writer.write_result_body_elements(result_expr=expr_ir0,
                                                     error_expr=error_expr)

        if match_case.is_main_definition():
            assert not main_definition
            main_definition = _create_metafunction_specialization(args=specialization_arg_decls,
                                                                  patterns=None,
                                                                  body=tuple(match_case_writer.elems))
        else:
            specialization = _create_metafunction_specialization(args=specialization_arg_decls,
                                                                 patterns=specialization_patterns,
                                                                 body=tuple(match_case_writer.elems))
            if specialization.patterns:
                specializations.append(specialization)
            else:
                # Trivial specialization.
                assert not main_definition
                main_definition = specialization

    if main_definition:
        args_decls = main_definition.args
    else:
        args_decls = (*forwarded_args_decls, *(ir0.TemplateArgDecl(expr_type=ir0.TypeType(),
                                                                   name=writer.new_id(),
                                                                   is_variadic=False)
                                               for _ in match_expr.matched_vars))

    args_exprs = (*forwarded_args_exprs, *matched_vars)

    helper_function = ir0.TemplateDefn(args=args_decls,
                                       main_definition=main_definition,
                                       specializations=tuple(specializations),
                                       name=writer.new_id(),
                                       description='(meta)function wrapping a match expression',
                                       result_element_names=frozenset(('value', 'type', 'error')))
    writer.write_toplevel_elem(helper_function)

    helper_function_reference = ir0.AtomicTypeLiteral.from_nonlocal_template_defn(helper_function,
                                                                                  is_metafunction_that_may_return_error=True)

    return _create_metafunction_call(template_expr=helper_function_reference,
                                     args=args_exprs,
                                     member_type=type_to_ir0(match_expr.expr_type),
                                     writer=writer)

def bool_literal_to_ir0(literal: ir1.BoolLiteral):
    return ir0.Literal(value=literal.value), None

def int_literal_to_ir0(literal: ir1.IntLiteral):
    return ir0.Literal(value=literal.value), None

def atomic_type_literal_to_ir0(literal: ir1.AtomicTypeLiteral):
    expr_type = type_to_ir0(literal.expr_type)
    kind = expr_type.kind

    may_be_alias = True
    for field_value in GlobalLiterals.__dict__.values():
        if isinstance(field_value, ir0.AtomicTypeLiteral) and field_value.cpp_type == literal.cpp_type:
            may_be_alias = False

    expr = ir0.AtomicTypeLiteral.for_nonlocal(cpp_type=literal.cpp_type,
                                              expr_type=expr_type,
                                              is_metafunction_that_may_return_error=(kind == ir0.ExprKind.TEMPLATE),
                                              may_be_alias=may_be_alias)
    return expr, None

def pointer_type_expr_to_ir0(expr: ir1.PointerTypeExpr, writer: Writer):
    type_expr, error_expr = expr_to_ir0(expr.type_expr, writer)
    return ir0.PointerTypeExpr(type_expr), error_expr

def reference_type_expr_to_ir0(expr: ir1.ReferenceTypeExpr, writer: Writer):
    type_expr, error_expr = expr_to_ir0(expr.type_expr, writer)
    return ir0.ReferenceTypeExpr(type_expr), error_expr

def rvalue_reference_type_expr_to_ir0(expr: ir1.RvalueReferenceTypeExpr, writer: Writer):
    type_expr, error_expr = expr_to_ir0(expr.type_expr, writer)
    return ir0.RvalueReferenceTypeExpr(type_expr), error_expr

def const_type_expr_to_ir0(expr: ir1.ConstTypeExpr, writer: Writer):
    type_expr, error_expr = expr_to_ir0(expr.type_expr, writer)
    return ir0.ConstTypeExpr(type_expr), error_expr

def array_type_expr_to_ir0(expr: ir1.ArrayTypeExpr, writer: Writer):
    type_expr, error_expr = expr_to_ir0(expr.type_expr, writer)
    return ir0.ArrayTypeExpr(type_expr), error_expr

def function_type_expr_to_ir0(expr: ir1.FunctionTypeExpr, writer: Writer):

    return_type_expr, error_expr = expr_to_ir0(expr.return_type_expr, writer)
    assert error_expr is None

    if isinstance(expr.arg_list_expr, ir1.ListPatternExpr):
        # Simple case, no need to generate a helper template.
        # This is not just an optimization, for type patterns we can't generate helper templates and we rely on this.
        assert not expr.arg_list_expr.list_extraction_expr

        arg_exprs = []
        for arg_expr in expr.arg_list_expr.elems:
            arg_expr, error_expr = expr_to_ir0(arg_expr, writer)
            assert error_expr is None
            arg_exprs.append(arg_expr)

        return ir0.FunctionTypeExpr(return_type_expr=return_type_expr,
                                    arg_exprs=tuple(arg_exprs)), None

    #   Type.function(..., ...)
    #
    # Becomes:
    #
    #   template <typename, typename>
    #   struct Helper;
    #
    #   template <typename X, typename... Args>
    #   struct Helper<X, List<Args...>> {
    #     using type = X(Args...);
    #   };
    #
    #   typename Helper<..., ...>::type

    x_var_name = writer.new_id()
    args_var_name = writer.new_id()

    function_type_expr = ir0.FunctionTypeExpr(return_type_expr=ir0.AtomicTypeLiteral.for_local(x_var_name, expr_type=ir0.TypeType(), is_variadic=False),
                                              arg_exprs=(ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(args_var_name,
                                                                                                                   ir0.TypeType(),
                                                                                                                   is_variadic=True)),))
    helper_specialization = ir0.TemplateSpecialization(args=(ir0.TemplateArgDecl(ir0.TypeType(), name=x_var_name, is_variadic=False),
                                                             ir0.TemplateArgDecl(ir0.TypeType(), name=args_var_name, is_variadic=True)),
                                                       patterns=(ir0.AtomicTypeLiteral.for_local(cpp_type=x_var_name,
                                                                                                 expr_type=ir0.TypeType(),
                                                                                                 is_variadic=False),
                                                                 ir0.TemplateInstantiation(template_expr=GlobalLiterals.LIST,
                                                                                           args=(ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type=args_var_name,
                                                                                                                                                           expr_type=ir0.TypeType(),
                                                                                                                                                           is_variadic=True)),),
                                                                                           instantiation_might_trigger_static_asserts=False)),
                                                       body=(ir0.Typedef(name='type',
                                                                         expr=function_type_expr),),
                                                       is_metafunction=True)
    helper_template_defn = ir0.TemplateDefn(name=writer.new_id(),
                                            description='(meta)function to expand the list of function args used to construct a C++ function type',
                                            specializations=(helper_specialization,),
                                            args=(ir0.TemplateArgDecl(expr_type=ir0.TypeType(), name=writer.new_id(), is_variadic=False),
                                                  ir0.TemplateArgDecl(expr_type=ir0.TypeType(), name=writer.new_id(), is_variadic=False),),
                                            main_definition=None,
                                            result_element_names=frozenset(('type',)))

    writer.write_toplevel_elem(helper_template_defn)

    arg_list_expr, error_expr = expr_to_ir0(expr.arg_list_expr, writer)
    assert error_expr is None

    return _create_metafunction_call(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=helper_template_defn.name,
                                                                                               is_metafunction_that_may_return_error=False,
                                                                                               args=(ir0.TemplateArgType(expr_type=ir0.TypeType(), is_variadic=False),
                                                                                                     ir0.TemplateArgType(expr_type=ir0.TypeType(), is_variadic=False)),
                                                                                               may_be_alias=False),
                                     args=(return_type_expr,
                                           arg_list_expr),
                                     member_type=ir0.TypeType(),
                                     writer=writer)


def function_call_to_ir0(call_expr: ir1.FunctionCall, writer: Writer):
    fun = var_reference_to_ir0(call_expr.fun)
    args = tuple(var_reference_to_ir0(arg)
                 for arg in call_expr.args)

    assert isinstance(call_expr.fun.expr_type, ir1.FunctionType)
    return _create_metafunction_call(template_expr=fun,
                                     args=args,
                                     member_type=type_to_ir0(call_expr.fun.expr_type.returns),
                                     writer=writer)

def equality_comparison_to_ir0(comparison_expr: ir1.EqualityComparison, writer: Writer):
    lhs = var_reference_to_ir0(comparison_expr.lhs)
    rhs = var_reference_to_ir0(comparison_expr.rhs)
    if isinstance(lhs.expr_type, ir0.TypeType):
        comparison_expr, comparison_error_expr = _create_metafunction_call(template_expr=GlobalLiterals.STD_IS_SAME,
                                                                           args=(lhs, rhs),
                                                                           member_type=ir0.BoolType(),
                                                                           writer=writer)
    else:
        comparison_expr = ir0.ComparisonExpr(lhs=lhs, rhs=rhs, op='==')
        comparison_error_expr = None
    return comparison_expr, comparison_error_expr

def is_in_list_expr_to_ir0(expr: ir1.IsInListExpr, writer: Writer):
    lhs = var_reference_to_ir0(expr.lhs)
    rhs = var_reference_to_ir0(expr.rhs)
    template_expr = {
        ir0.ExprKind.BOOL: GlobalLiterals.IS_IN_BOOL_LIST,
        ir0.ExprKind.INT64: GlobalLiterals.IS_IN_INT64_LIST,
        ir0.ExprKind.TYPE: GlobalLiterals.IS_IN_TYPE_LIST,
    }[lhs.expr_type.kind]
    return _create_metafunction_call(template_expr=template_expr,
                                     args=(lhs, rhs),
                                     member_type=ir0.BoolType(),
                                     writer=writer)

def attribute_access_expr_to_ir0(attribute_access_expr: ir1.AttributeAccessExpr):
    class_expr = var_reference_to_ir0(attribute_access_expr.var)
    assert isinstance(class_expr.expr_type, ir0.TypeType)
    expr = ir0.ClassMemberAccess(inner_expr=class_expr,
                                 member_name=attribute_access_expr.attribute_name,
                                 expr_type=type_to_ir0(attribute_access_expr.expr_type))
    return expr, None

def not_expr_to_ir0(not_expr: ir1.NotExpr):
    return ir0.NotExpr(inner_expr=var_reference_to_ir0(not_expr.var)), None

def unary_minus_expr_to_ir0(expr: ir1.UnaryMinusExpr):
    return ir0.UnaryMinusExpr(inner_expr=var_reference_to_ir0(expr.var)), None

def int_comparison_expr_to_ir0(expr: ir1.IntComparisonExpr):
    lhs = var_reference_to_ir0(expr.lhs)
    rhs = var_reference_to_ir0(expr.rhs)
    return ir0.ComparisonExpr(lhs=lhs, rhs=rhs, op=expr.op), None

def int_binary_op_expr_to_ir0(expr: ir1.IntBinaryOpExpr):
    lhs = var_reference_to_ir0(expr.lhs)
    rhs = var_reference_to_ir0(expr.rhs)
    cpp_op = {
        '+': '+',
        '-': '-',
        '*': '*',
        '//': '/',
        '%': '%',
    }[expr.op]
    return ir0.Int64BinaryOpExpr(lhs=lhs, rhs=rhs, op=cpp_op), None

def is_instance_expr_to_ir0(expr: ir1.IsInstanceExpr, writer: Writer):
    is_instance_of_type_template = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=writer.get_is_instance_template_name_for_error(expr.checked_type.name),
                                                                               is_metafunction_that_may_return_error=False,
                                                                               args=(ir0.TemplateArgType(expr_type=ir0.TypeType(), is_variadic=False),),
                                                                               may_be_alias=False)
    return _create_metafunction_call(template_expr=is_instance_of_type_template,
                                     args=(var_reference_to_ir0(expr.var),),
                                     member_type=ir0.BoolType(),
                                     writer=writer)

def safe_unchecked_cast_expr_to_ir0(expr: ir1.SafeUncheckedCast):
    assert type_to_ir0(expr.var.expr_type).kind == type_to_ir0(expr.expr_type).kind
    return var_reference_to_ir0(ir1.VarReference(expr_type=expr.expr_type,
                                                name=expr.var.name,
                                                is_global_function=expr.var.is_global_function,
                                                is_function_that_may_throw=expr.var.is_function_that_may_throw))

def list_template_name_for_type(expr_type: ir0.ExprType):
    if expr_type.kind == ir0.ExprKind.BOOL:
        return 'BoolList'
    elif expr_type.kind == ir0.ExprKind.INT64:
        return 'Int64List'
    elif expr_type.kind == ir0.ExprKind.TYPE:
        return 'List'
    else:
        raise NotImplementedError('expr_type.kind: %s' % expr_type.kind)

def _define_transform_list_to_list_template(source_type: ir0.ExprType,
                                            dest_type: ir0.ExprType,
                                            forwarded_args: Tuple[ir0.TemplateArgDecl, ...],
                                            functor_literal: ir0.AtomicTypeLiteral,
                                            writer: Writer):
    assert not functor_literal.is_local
    for arg in forwarded_args:
        assert not arg.is_variadic

    # template <typename L, typename ForwardedT, bool forwarded_bool>
    # struct TransformBoolListToInt64List;
    #
    # template <bool... bs, typename ForwardedT, bool forwarded_bool>
    # struct TransformBoolListToInt64List<BoolList<bs...>, ForwardedT, forwarded_bool> {
    #   using error = typename GetFirstError<typename F<bs, ForwardedT, forwarded_bool>::error...>::type;
    #   using type = Int64List<F<bs, ForwardedT, forwarded_bool>::value...>;
    # };

    source_type_list_name = list_template_name_for_type(source_type)
    dest_type_list_name = list_template_name_for_type(dest_type)
    transform_list_to_list_template_name = writer.new_id()

    list_arg_decl = ir0.TemplateArgDecl(name='L', expr_type=ir0.TypeType(), is_variadic=False)
    template_specialization_writer = TemplateBodyWriter(writer, parent_arbitrary_arg=list_arg_decl, parent_return_type=ir0.TypeType())

    forwarded_exprs = tuple(ir0.AtomicTypeLiteral.for_local(cpp_type=arg.name, expr_type=arg.expr_type, is_variadic=False)
                            for arg in forwarded_args)

    source_variadic_arg_decl = ir0.TemplateArgDecl(expr_type=source_type, name='elems', is_variadic=True)
    source_variadic_arg_decl_type = ir0.TemplateArgType(expr_type=source_type, is_variadic=True)
    source_variadic_arg_expr = ir0.AtomicTypeLiteral.for_local('elems', source_type, is_variadic=True)
    dest_variadic_arg_expr = ir0.AtomicTypeLiteral.for_local('results', dest_type, is_variadic=True)
    source_list_pattern_expr = ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=source_type_list_name,
                                                                                                                   args=(source_variadic_arg_decl_type,),
                                                                                                                   is_metafunction_that_may_return_error=False,
                                                                                                                   may_be_alias=False),
                                                         args=(ir0.VariadicTypeExpansion(source_variadic_arg_expr),),
                                                         instantiation_might_trigger_static_asserts=False)

    type_expr, error_expr = _create_metafunction_call(template_expr=functor_literal,
                                                      args=(source_variadic_arg_expr, *forwarded_exprs),
                                                      member_type=dest_type,
                                                      writer=template_specialization_writer)
    if error_expr:
        error_expr, _ = _create_metafunction_call(template_expr=GlobalLiterals.GET_FIRST_ERROR,
                                                  args=(ir0.VariadicTypeExpansion(error_expr),),
                                                  member_type=ir0.TypeType(),
                                                  writer=template_specialization_writer)

    dest_list_literal = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=dest_type_list_name,
                                                                    args=(dest_variadic_arg_expr,),
                                                                    is_metafunction_that_may_return_error=False,
                                                                    may_be_alias=False)
    type_expr = ir0.TemplateInstantiation(template_expr=dest_list_literal,
                                          args=(ir0.VariadicTypeExpansion(type_expr),),
                                          instantiation_might_trigger_static_asserts=False)

    template_specialization_writer.write_result_body_elements(result_expr=type_expr,
                                                              error_expr=error_expr)

    writer.write_toplevel_elem(ir0.TemplateDefn(main_definition=None,
                                                specializations=(ir0.TemplateSpecialization(args=(source_variadic_arg_decl, *forwarded_args),
                                                                                            patterns=(source_list_pattern_expr, *forwarded_exprs),
                                                                                            body=tuple(template_specialization_writer.elems),
                                                                                            is_metafunction=True),),
                                                name=transform_list_to_list_template_name,
                                                description='',
                                                result_element_names=frozenset(('type', 'error')),
                                                args=(list_arg_decl, *forwarded_args)))

    return transform_list_to_list_template_name


def list_comprehension_expr_to_ir0(expr: ir1.ListComprehensionExpr, writer: Writer):
    captured_vars = [var
                     for var in get_unique_free_variables_in_stmts([ir1.ReturnStmt(result=expr.result_elem_expr,
                                                                                   error=None,
                                                                                   source_branch=None)])
                     if var.name != expr.loop_var.name]
    forwarded_vars = [var_reference_to_ir0(var)
                      for var in captured_vars]
    forwarded_arg_decls = tuple(ir0.TemplateArgDecl(expr_type=var.expr_type, name=var.cpp_type, is_variadic=False)
                                for var in forwarded_vars)
    for var in forwarded_vars:
        assert not var.is_variadic

    x_type = type_to_ir0(expr.loop_var.expr_type)
    assert not isinstance(expr.loop_var.expr_type, ir1.ParameterPackType)
    result_elem_type = type_to_ir0(expr.result_elem_expr.expr_type)


    template_arg_decl = ir0.TemplateArgDecl(expr_type=x_type,
                                            name=expr.loop_var.name,
                                            is_variadic=False)
    helper_template_body_writer = TemplateBodyWriter(writer,
                                                     parent_arbitrary_arg=template_arg_decl,
                                                     parent_return_type=result_elem_type)
    if expr.loop_body_start_branch:
        helper_template_body_writer.write(ir0.NoOpStmt(expr.loop_body_start_branch))
    result_expr, error_expr = function_call_to_ir0(expr.result_elem_expr, helper_template_body_writer)
    helper_template_body_writer.write_result_body_elements(result_expr=result_expr, error_expr=error_expr)
    helper_template_defn = ir0.TemplateDefn(name=writer.new_id(),
                                            description='(meta)function wrapping the expression in a list comprehension',
                                            specializations=(),
                                            main_definition=ir0.TemplateSpecialization(args=(template_arg_decl, *forwarded_arg_decls),
                                                                                       patterns=None,
                                                                                       body=tuple(helper_template_body_writer.elems),
                                                                                       is_metafunction=True),
                                            result_element_names=frozenset(('type', 'value', 'error')))


    # TODO: introduce an unchecked version of this and use it when we know that the list comprehension can't result in
    # an error.
    transform_metafunction_name = _define_transform_list_to_list_template(source_type=x_type,
                                                                          dest_type=result_elem_type,
                                                                          forwarded_args=forwarded_arg_decls,
                                                                          functor_literal=ir0.AtomicTypeLiteral.from_nonlocal_template_defn(helper_template_defn,
                                                                                                                                            is_metafunction_that_may_return_error=expr.result_elem_expr.fun.is_function_that_may_throw),
                                                                          writer=writer)

    transform_list_template_literal = ir0.AtomicTypeLiteral.for_nonlocal_template(
        cpp_type=transform_metafunction_name,
        args=(ir0.TemplateArgType(expr_type=type_to_ir0(expr.list_var.expr_type), is_variadic=isinstance(expr.list_var.expr_type, ir1.ParameterPackType)),
              *forwarded_arg_decls),
        is_metafunction_that_may_return_error=expr.result_elem_expr.fun.is_function_that_may_throw,
        may_be_alias=False)

    # z = [f(y, x, z)
    #      for x in l]
    #
    # Becomes:
    #
    # template <typename X>
    # struct Helper {
    #   using type = typename f<X>::type;
    # };
    #
    # using Z = typename TransformTypeListWithHelper<L, Y, Z>::type;

    writer.write_toplevel_elem(helper_template_defn)

    if expr.loop_exit_branch:
        writer.write(ir0.NoOpStmt(expr.loop_exit_branch))

    return _create_metafunction_call(template_expr=transform_list_template_literal,
                                     args=(var_reference_to_ir0(expr.list_var), *forwarded_vars),
                                     member_type=type_to_ir0(expr.expr_type),
                                     writer=writer)

def template_member_access_expr_to_ir0(expr: ir1.TemplateMemberAccessExpr, writer: Writer):
    class_type_expr = var_reference_to_ir0(expr.class_type_expr)

    #   Type.template_member(..., 'member_name', ...)
    #
    # Becomes:
    #
    #   template <typename, typename>
    #   struct Helper;
    #
    #   template <typename X, typename... Args>
    #   struct Helper<X, List<Args...>> {
    #     using type = X::member_name<Args...>;
    #   };
    #
    #   typename Helper<..., ...>::type

    x_var_name = writer.new_id()
    args_var_name = writer.new_id()

    template_instantiation_expr = ir0.TemplateInstantiation(ir0.ClassMemberAccess(inner_expr=ir0.AtomicTypeLiteral.for_local(cpp_type=x_var_name,
                                                                                                                             expr_type=ir0.TypeType(),
                                                                                                                             is_variadic=False),
                                                                                  member_name=expr.member_name,
                                                                                  expr_type=ir0.TemplateType(args=(ir0.TemplateArgType(expr_type=ir0.TypeType(),
                                                                                                                                       is_variadic=True),))),
                                                            args=(ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type=args_var_name,
                                                                                                                            expr_type=ir0.TypeType(),
                                                                                                                            is_variadic=True)),),
                                                            instantiation_might_trigger_static_asserts=True)

    helper_specialization = ir0.TemplateSpecialization(args=(ir0.TemplateArgDecl(ir0.TypeType(), name=x_var_name, is_variadic=False),
                                                             ir0.TemplateArgDecl(ir0.TypeType(), name=args_var_name, is_variadic=True)),
                                                       patterns=(ir0.AtomicTypeLiteral.for_local(cpp_type=x_var_name,
                                                                                                 expr_type=ir0.TypeType(),
                                                                                                 is_variadic=False),
                                                                 ir0.TemplateInstantiation(template_expr=GlobalLiterals.LIST,
                                                                                           args=(ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type=args_var_name,
                                                                                                                                                           expr_type=ir0.TypeType(),
                                                                                                                                                           is_variadic=True)),),
                                                                                           instantiation_might_trigger_static_asserts=False)),
                                                       body=(ir0.Typedef(name='type',
                                                                         expr=template_instantiation_expr),),
                                                       is_metafunction=True)
    helper_template_defn = ir0.TemplateDefn(name=writer.new_id(),
                                            description='(meta)function to expand the list of function args used to construct a C++ function type',
                                            specializations=(helper_specialization,),
                                            args=(ir0.TemplateArgDecl(ir0.TypeType(), name=writer.new_id(), is_variadic=False),
                                                  ir0.TemplateArgDecl(ir0.TypeType(), name=writer.new_id(), is_variadic=False)),
                                            main_definition=None,
                                            result_element_names=frozenset(('type',)))

    writer.write_toplevel_elem(helper_template_defn)

    arg_list_expr = var_reference_to_ir0(expr.arg_list_expr)

    return _create_metafunction_call(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=helper_template_defn.name,
                                                                                               is_metafunction_that_may_return_error=False,
                                                                                               args=(ir0.TemplateArgType(ir0.TypeType(), is_variadic=False),
                                                                                                     ir0.TemplateArgType(ir0.TypeType(), is_variadic=False)),
                                                                                               may_be_alias=False),
                                     args=(class_type_expr,
                                           arg_list_expr),
                                     member_type=ir0.TypeType(),
                                     writer=writer)


def _create_template_instantiation(template_name: str,
                                   arg_exprs: Sequence[ir1.Expr],
                                   instantiation_might_trigger_static_asserts: bool,
                                   writer: Writer):
    ir0_arg_exprs = []
    for arg in arg_exprs:
        ir0_expr, error_expr = expr_to_ir0(arg, writer)
        assert error_expr is None
        ir0_arg_exprs.append(ir0_expr)

    template_expr = GLOBAL_LITERALS_BY_NAME.get(template_name, None)
    if template_expr is None:
        template_expr = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=template_name,
                                                                    args=tuple(ir0.TemplateArgType(expr_type=type_to_ir0(arg.expr_type), is_variadic=isinstance(arg.expr_type, ir1.ParameterPackType))
                                                                               for arg in arg_exprs),
                                                                    is_metafunction_that_may_return_error=False,
                                                                    may_be_alias=True)

    return ir0.TemplateInstantiation(template_expr=template_expr,
                                     args=tuple(ir0_arg_exprs),
                                     instantiation_might_trigger_static_asserts=instantiation_might_trigger_static_asserts)

def template_instantiation_expr_to_ir0(expr: ir1.TemplateInstantiationExpr, writer: Writer):
    #   Type.template_instantiation('Foo', ...)
    #
    # Becomes:
    #
    #   template <typename typename>
    #   struct Helper;
    #
    #   template <typename... Args>
    #   struct Helper<List<Args...>> {
    #     using type = Foo<Args...>;
    #   };
    #
    #   typename Helper<...>::type

    args_var_name = writer.new_id()

    template_expr = GLOBAL_LITERALS_BY_NAME.get(expr.template_atomic_cpp_type, None)
    if template_expr is None:
        template_expr = ir0.AtomicTypeLiteral.for_nonlocal_template(expr.template_atomic_cpp_type,
                                                                    args=(ir0.TemplateArgType(expr_type=ir0.TypeType(), is_variadic=True),),
                                                                    is_metafunction_that_may_return_error=False,
                                                                    may_be_alias=True)

    # Foo<Args...>
    template_instantiation_expr = ir0.TemplateInstantiation(template_expr=template_expr,
                                                            args=(ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(args_var_name,
                                                                                                                            ir0.TypeType(),
                                                                                                                            is_variadic=True)),),
                                                            instantiation_might_trigger_static_asserts=True)
    helper_specialization = ir0.TemplateSpecialization(args=(ir0.TemplateArgDecl(ir0.TypeType(), name=args_var_name, is_variadic=True),),
                                                       patterns=(ir0.TemplateInstantiation(template_expr=GlobalLiterals.LIST,
                                                                                           args=(ir0.VariadicTypeExpansion(ir0.AtomicTypeLiteral.for_local(cpp_type=args_var_name,
                                                                                                                                                           expr_type=ir0.TypeType(),
                                                                                                                                                           is_variadic=True)),),
                                                                                           instantiation_might_trigger_static_asserts=False),),
                                                       body=(ir0.Typedef(name='type',
                                                                         expr=template_instantiation_expr),),
                                                       is_metafunction=True)
    helper_template_defn = ir0.TemplateDefn(name=writer.new_id(),
                                            description='(meta)function to expand the list of args for a template instantiation',
                                            specializations=(helper_specialization,),
                                            args=(ir0.TemplateArgDecl(ir0.TypeType(), name=writer.new_id(), is_variadic=False),),
                                            main_definition=None,
                                            result_element_names=frozenset(('type',)))

    writer.write_toplevel_elem(helper_template_defn)

    return _create_metafunction_call(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=helper_template_defn.name,
                                                                                               is_metafunction_that_may_return_error=False,
                                                                                               args=(ir0.TemplateArgType(ir0.TypeType(), is_variadic=False),),
                                                                                               may_be_alias=False),
                                     args=(var_reference_to_ir0(expr.arg_list_expr),),
                                     member_type=ir0.TypeType(),
                                     writer=writer)

def add_to_set_expr_to_ir0(expr: ir1.AddToSetExpr):
    # add_to_set(s, 3)
    #
    # Becomes:
    #
    # AddToInt64Set<s, 3>::type

    set_expr = var_reference_to_ir0(expr.set_expr)
    elem_expr = var_reference_to_ir0(expr.elem_expr)

    if isinstance(elem_expr.expr_type, ir0.BoolType):
        template_name = 'AddToBoolSet'
    elif isinstance(elem_expr.expr_type, ir0.Int64Type):
        template_name = 'AddToInt64Set'
    elif isinstance(elem_expr.expr_type, ir0.TypeType):
        template_name = 'AddToTypeSet'
    else:
        raise NotImplementedError('Unexpected type kind: %s' % elem_expr.kind)

    add_to_set_template_expr = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=template_name,
                                                                           is_metafunction_that_may_return_error=False,
                                                                           args=(ir0.TemplateArgType(ir0.TypeType(),
                                                                                                     is_variadic=False),
                                                                                 ir0.TemplateArgType(type_to_ir0(expr.elem_expr.expr_type),
                                                                                                     is_variadic=isinstance(expr.elem_expr.expr_type, ir1.ParameterPackType)),),
                                                                           may_be_alias=False)
    add_to_set_instantiation = ir0.TemplateInstantiation(template_expr=add_to_set_template_expr,
                                                         args=(set_expr, elem_expr),
                                                         instantiation_might_trigger_static_asserts=False)

    return ir0.ClassMemberAccess(inner_expr=add_to_set_instantiation,
                                 member_name='type',
                                 expr_type=ir0.TypeType())

def set_equality_comparison_expr_to_ir0(expr: ir1.SetEqualityComparison):
    # set_equals(x, y)
    #
    # Becomes:
    #
    # Int64SetEquals<x, y>::value

    lhs = var_reference_to_ir0(expr.lhs)
    rhs = var_reference_to_ir0(expr.rhs)
    assert lhs.expr_type == rhs.expr_type

    elem_type = type_to_ir0(expr.lhs.expr_type.elem_type)
    if isinstance(elem_type, ir0.BoolType):
        template_name = 'BoolSetEquals'
    elif isinstance(elem_type, ir0.Int64Type):
        template_name = 'Int64SetEquals'
    elif isinstance(elem_type, ir0.TypeType):
        template_name = 'TypeSetEquals'
    else:
        raise NotImplementedError('Unexpected type: %s' % str(elem_type))

    set_equals_template_expr = ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=template_name,
                                                                           args=(ir0.TemplateArgType(type_to_ir0(expr.lhs.expr_type),
                                                                                                     is_variadic=isinstance(expr.lhs.expr_type, ir1.ParameterPackType)),
                                                                                 ir0.TemplateArgType(type_to_ir0(expr.rhs.expr_type),
                                                                                                     is_variadic=isinstance(expr.rhs.expr_type, ir1.ParameterPackType))),
                                                                           is_metafunction_that_may_return_error=False,
                                                                           may_be_alias=False)
    set_equals_instantiation = ir0.TemplateInstantiation(template_expr=set_equals_template_expr,
                                                         args=(lhs, rhs),
                                                         instantiation_might_trigger_static_asserts=False)

    return ir0.ClassMemberAccess(inner_expr=set_equals_instantiation,
                                 member_name='value',
                                 expr_type=ir0.BoolType())

def list_to_set_expr_to_ir0(expr: ir1.ListToSetExpr):
    # list_to_set(x)
    #
    # Becomes:
    #
    # Int64ListToSet<x>::type

    var = var_reference_to_ir0(expr.var)

    elem_kind = type_to_ir0(expr.expr_type.elem_type).kind
    list_to_set_template_literal = {
        ir0.ExprKind.BOOL: GlobalLiterals.BOOL_LIST_TO_SET,
        ir0.ExprKind.INT64: GlobalLiterals.INT64_LIST_TO_SET,
        ir0.ExprKind.TYPE: GlobalLiterals.TYPE_LIST_TO_SET,
    }[elem_kind]
    set_equals_instantiation = ir0.TemplateInstantiation(template_expr=list_to_set_template_literal,
                                                         args=(var,),
                                                         instantiation_might_trigger_static_asserts=False)

    return ir0.ClassMemberAccess(inner_expr=set_equals_instantiation,
                                 member_name='type',
                                 expr_type=ir0.TypeType())

def parameter_pack_expansion_expr_to_ir0(expr: ir1.ParameterPackExpansion):
    return ir0.VariadicTypeExpansion(var_reference_to_ir0(expr.expr))

def assert_to_ir0(assert_stmt: ir1.Assert, writer: Writer):
    expr = var_reference_to_ir0(assert_stmt.var)
    writer.write(ir0.StaticAssert(expr=expr, message=assert_stmt.message))
    if assert_stmt.source_branch:
        writer.write(ir0.NoOpStmt(assert_stmt.source_branch))

def pass_stmt_to_ir0(stmt: ir1.PassStmt, writer: Writer):
    if stmt.source_branch:
        writer.write(ir0.NoOpStmt(stmt.source_branch))

def assignment_to_ir0(assignment: ir1.Assignment, writer: Writer):
    lhs = var_reference_to_ir0(assignment.lhs)
    rhs, rhs_error = expr_to_ir0(assignment.rhs, writer)

    type_ir0 = type_to_ir0(assignment.lhs.expr_type)
    if type_ir0.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
        writer.write(ir0.ConstantDef(name=lhs.cpp_type, expr=rhs))
    else:
        writer.write(ir0.Typedef(name=lhs.cpp_type, expr=rhs))

    if assignment.lhs2:
        lhs2 = var_reference_to_ir0(assignment.lhs2)
        assert isinstance(rhs_error.expr_type, ir0.TypeType)
        writer.write(ir0.Typedef(name=lhs2.cpp_type, expr=rhs_error))

    if assignment.source_branch:
        writer.write(ir0.NoOpStmt(assignment.source_branch))

def custom_type_defn_to_ir0(custom_type: ir1.CustomType, public_names: Set[str], writer: ToplevelWriter):
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
        arg_type = type_to_ir0(arg.expr_type)
        arg_types.append(arg_type)
        arg_decls.append(ir0.TemplateArgDecl(expr_type=arg_type,
                                             name=forwarded_arg_name,
                                             is_variadic=isinstance(arg.expr_type, ir1.ParameterPackType)))

    holder_template_writer = TemplateBodyWriter(writer,
                                                parent_arbitrary_arg=_select_arbitrary_parent_arg(arg_decls),
                                                parent_return_type=None)
    holder_template_instantiation_args = []
    for arg, arg_decl in zip(custom_type.arg_types, arg_decls):
        lhs_var = ir1.VarReference(expr_type=arg.expr_type,
                                  name=arg.name,
                                  is_global_function=False,
                                  is_function_that_may_throw=isinstance(arg.expr_type, ir1.FunctionType))
        rhs_var = ir1.VarReference(expr_type=arg.expr_type,
                                  name=arg_decl.name,
                                  is_global_function=False,
                                  is_function_that_may_throw=isinstance(arg.expr_type, ir1.FunctionType))
        assignment_to_ir0(ir1.Assignment(lhs=lhs_var,
                                         rhs=rhs_var,
                                         source_branch=None),
                          holder_template_writer)
        holder_template_instantiation_args.append(var_reference_to_ir0(rhs_var))

    holder_template = ir0.TemplateDefn(name=holder_template_id,
                                       description='Holder template for the custom type %s' % custom_type.name,
                                       specializations=(),
                                       main_definition=ir0.TemplateSpecialization(args=tuple(arg_decls),
                                                                                  patterns=None,
                                                                                  body=tuple(holder_template_writer.elems),
                                                                                  is_metafunction=False),
                                       result_element_names=frozenset((arg.name
                                                                       for arg in custom_type.arg_types)))
    writer.write_toplevel_elem(holder_template)

    # This is referenced by CheckIfError (at least).
    public_names.add(holder_template_id)

    constructor_fn_typedef = ir0.Typedef(name='type',
                                         expr=ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.from_nonlocal_template_defn(holder_template,
                                                                                                                                        is_metafunction_that_may_return_error=False),
                                                                        args=tuple(holder_template_instantiation_args),
                                                                        instantiation_might_trigger_static_asserts=False))
    constructor_fn_error_typedef = ir0.Typedef(name='error',
                                               expr=ir0.AtomicTypeLiteral.for_nonlocal_type('void', may_be_alias=False))
    constructor_fn = ir0.TemplateDefn(name=custom_type.name,
                                      description='Constructor (meta)function for the custom type %s' % custom_type.name,
                                      specializations=(),
                                      main_definition=ir0.TemplateSpecialization(args=tuple(arg_decls),
                                                                                 patterns=None,
                                                                                 body=(*(ir0.NoOpStmt(branch)
                                                                                         for branch in custom_type.constructor_source_branches),
                                                                                       constructor_fn_typedef,
                                                                                       constructor_fn_error_typedef),
                                                                                 is_metafunction=True),
                                      result_element_names=frozenset(('type', 'error')))
    writer.write_toplevel_elem(constructor_fn)

    writer.set_holder_template_name_for_error(custom_type.name, holder_template_id)

    is_instance_template = ir0.TemplateDefn(name=writer.new_id(),
                                            description='isinstance() (meta)function for the custom type %s' % custom_type.name,
                                            main_definition=ir0.TemplateSpecialization(args=(ir0.TemplateArgDecl(expr_type=ir0.TypeType(), name=writer.new_id(), is_variadic=False),),
                                                                                       patterns=None,
                                                                                       body=(ir0.ConstantDef(name='value',
                                                                                                             expr=ir0.Literal(value=False)),),
                                                                                       is_metafunction=True),
                                            specializations=(ir0.TemplateSpecialization(args=tuple(ir0.TemplateArgDecl(expr_type=type_to_ir0(arg.expr_type),
                                                                                                                       name=arg.name,
                                                                                                                       is_variadic=isinstance(arg.expr_type, ir1.ParameterPackType))
                                                                                                   for arg in custom_type.arg_types),
                                                                                        patterns=(ir0.TemplateInstantiation(ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=holder_template_id,
                                                                                                                                                                        is_metafunction_that_may_return_error=False,
                                                                                                                                                                        args=tuple(ir0.TemplateArgType(arg_type, is_variadic=False)
                                                                                                                                                                                   for arg_type in arg_types),
                                                                                                                                                                        may_be_alias=False),
                                                                                                                            args=tuple(ir0.AtomicTypeLiteral.for_local(cpp_type=arg.name,
                                                                                                                                                                       expr_type=type_to_ir0(arg.expr_type),
                                                                                                                                                                       is_variadic=isinstance(arg.expr_type, ir1.ParameterPackType))
                                                                                                                                       for arg in custom_type.arg_types),
                                                                                                                            instantiation_might_trigger_static_asserts=False),),
                                                                                        body=(ir0.ConstantDef(name='value',
                                                                                                              expr=ir0.Literal(value=True)),),
                                                                                        is_metafunction=True),),
                                            result_element_names=frozenset(('value',)))

    writer.write_toplevel_elem(is_instance_template)
    writer.set_is_instance_template_name_for_error(custom_type.name, is_instance_template.name)

def return_stmt_to_ir0(return_stmt: ir1.ReturnStmt, writer: TemplateBodyWriter):
    if return_stmt.result:
        result_var = var_reference_to_ir0(return_stmt.result)
    else:
        result_var = None
    if return_stmt.error:
        error_var = var_reference_to_ir0(return_stmt.error)
    else:
        error_var = None

    writer.write_result_body_elements(result_expr=result_var,
                                      error_expr=error_var)

    if return_stmt.source_branch:
        writer.write(ir0.NoOpStmt(return_stmt.source_branch))

def _get_free_vars_in_elements(elements: Sequence[ir0.TemplateBodyElement]):
    free_var_names = set()
    bound_var_names = set()
    free_vars: List[ir0.AtomicTypeLiteral] = []
    for element in elements:
        if isinstance(element, ir0.StaticAssert) or isinstance(element, ir0.ConstantDef) or isinstance(element, ir0.Typedef):
            for var in element.expr.free_vars:
                if var.cpp_type not in bound_var_names and var.cpp_type not in free_var_names:
                    free_var_names.add(var.cpp_type)
                    free_vars.append(var)
        elif isinstance(element, ir0.NoOpStmt):
            pass
        else:
            raise NotImplementedError('Unexpected element type: %s' % str(element.__class__))
        if isinstance(element, ir0.ConstantDef) or isinstance(element, ir0.Typedef):
            bound_var_names.add(element.name)
    return free_vars

def if_stmt_to_ir0(if_stmt: ir1.IfStmt,
                   then_stmts: Sequence[ir1.Stmt],
                   write_continuation_fun_call: Optional[Callable[[TemplateBodyWriter], None]],
                   writer: TemplateBodyWriter):

    cond_expr = var_reference_to_ir0(if_stmt.cond)

    if then_stmts:
        then_writer = writer.create_sibling_writer(writer.parent_arbitrary_arg, writer.parent_return_type)
        stmts_to_ir0(then_stmts, write_continuation_fun_call, then_writer)

        forwarded_vars = _get_free_vars_in_elements(then_writer.elems)

        forwarded_vars_args = [ir0.TemplateArgDecl(expr_type=var.expr_type,
                                                   name=var.cpp_type,
                                                   is_variadic=var.is_variadic)
                               for var in forwarded_vars]
        forwarded_vars_patterns = forwarded_vars
        forwarded_vars_exprs = [ir0.AtomicTypeLiteral.for_local(cpp_type=var.cpp_type,
                                                                expr_type=var.expr_type,
                                                                is_variadic=var.is_variadic)
                                for var in forwarded_vars]
        forwarded_vars_types = [var.expr_type
                                for var in forwarded_vars]
        if not forwarded_vars:
            # We need to add a dummy template parameter, otherwise the "then" template will have no parameters and the C++
            # _compiler will eagerly evaluate its body, even if it would never be instantiated (triggering e.g. any
            # assertions in that code).
            forwarded_vars_args.append(then_writer.parent_arbitrary_arg)
            arbitrary_arg_ref = ir0.AtomicTypeLiteral.for_local(cpp_type=then_writer.parent_arbitrary_arg.name,
                                                                expr_type=then_writer.parent_arbitrary_arg.expr_type,
                                                                is_variadic=then_writer.parent_arbitrary_arg.is_variadic)
            forwarded_vars_patterns.append(arbitrary_arg_ref)
            forwarded_vars_exprs.append(arbitrary_arg_ref)
            forwarded_vars_types.append(then_writer.parent_arbitrary_arg.expr_type)

        then_template_defn = ir0.TemplateDefn(name=writer.new_id(),
                                              description='(meta)function wrapping the code after an if-else statement',
                                              main_definition=ir0.TemplateSpecialization(args=tuple(forwarded_vars_args),
                                                                                         patterns=None,
                                                                                         body=tuple(then_writer.elems),
                                                                                         is_metafunction=True),
                                              specializations=(),
                                              result_element_names=frozenset(('value', 'type', 'error')))
        writer.write_toplevel_elem(then_template_defn)

        then_function_call_expr, then_function_call_error_expr = _create_metafunction_call(ir0.AtomicTypeLiteral.from_nonlocal_template_defn(then_template_defn,
                                                                                                                                             is_metafunction_that_may_return_error=True),
                                                                                           args=tuple(forwarded_vars_exprs),
                                                                                           member_type=writer.parent_return_type,
                                                                                           writer=writer)
    else:
        then_function_call_expr = None
        then_function_call_error_expr = None

    if then_function_call_expr or then_function_call_error_expr:
        write_continuation_fun_call = lambda writer: writer.write_result_body_elements(result_expr=then_function_call_expr,
                                                                                       error_expr=then_function_call_error_expr)

    if_branch_writer = writer.create_sibling_writer(writer.parent_arbitrary_arg, writer.parent_return_type)
    stmts_to_ir0(if_stmt.if_stmts, write_continuation_fun_call, if_branch_writer)

    else_branch_writer = writer.create_sibling_writer(writer.parent_arbitrary_arg, writer.parent_return_type)
    if if_stmt.else_stmts:
        stmts_to_ir0(if_stmt.else_stmts, write_continuation_fun_call, else_branch_writer)
    else:
        write_continuation_fun_call(else_branch_writer)

    forwarded_vars = _get_free_vars_in_elements(if_branch_writer.elems + else_branch_writer.elems)

    forwarded_vars_args = [ir0.TemplateArgDecl(expr_type=var.expr_type, name=var.cpp_type, is_variadic=var.is_variadic)
                           for var in forwarded_vars]
    forwarded_vars_exprs = [ir0.AtomicTypeLiteral.for_local(cpp_type=var.cpp_type,
                                                            expr_type=var.expr_type,
                                                            is_variadic=var.is_variadic)
                            for var in forwarded_vars]
    forwarded_vars_types = [var.expr_type
                            for var in forwarded_vars]
    if not forwarded_vars:
        # We need to add a dummy template parameter, otherwise the true/false specializations will be full specializations
        # and the C++ _compiler will eagerly evaluate them, even if they would never be instantiated (triggering e.g.
        # any assertions in that code).
        forwarded_vars_args.append(writer.parent_arbitrary_arg)
        forwarded_vars_exprs.append(ir0.AtomicTypeLiteral.for_local(cpp_type=writer.parent_arbitrary_arg.name,
                                                                    expr_type=writer.parent_arbitrary_arg.expr_type,
                                                                    is_variadic=writer.parent_arbitrary_arg.is_variadic))
        forwarded_vars_types.append(writer.parent_arbitrary_arg.expr_type)

    if_branch_specialization = _create_metafunction_specialization(args=tuple(forwarded_vars_args),
                                                                   patterns=(*forwarded_vars_exprs, ir0.Literal(True)),
                                                                   body=tuple(if_branch_writer.elems))
    else_branch_specialization = _create_metafunction_specialization(args=tuple(forwarded_vars_args),
                                                                     patterns=(*forwarded_vars_exprs, ir0.Literal(False)),
                                                                     body=tuple(else_branch_writer.elems))

    fun_defn = ir0.TemplateDefn(main_definition=None,
                                name=writer.new_id(),
                                description='(meta)function generated for an if-else statement',
                                args=(*forwarded_vars_args, ir0.TemplateArgDecl(expr_type=ir0.BoolType(),
                                                                                name=writer.new_id(),
                                                                                is_variadic=False)),
                                specializations=(if_branch_specialization, else_branch_specialization),
                                result_element_names=frozenset(('value', 'type', 'error')))
    writer.write_toplevel_elem(fun_defn)
    function_call_expr, function_call_error_expr = _create_metafunction_call(ir0.AtomicTypeLiteral.from_nonlocal_template_defn(fun_defn,
                                                                                                                               is_metafunction_that_may_return_error=True),
                                                                             args=(*forwarded_vars_exprs, cond_expr),
                                                                             member_type=writer.parent_return_type,
                                                                             writer=writer)

    writer.write_result_body_elements(result_expr=function_call_expr,
                                      error_expr=function_call_error_expr)

def unpacking_assignment_to_ir0(assignment: ir1.UnpackingAssignment,
                                other_stmts: Sequence[ir1.Stmt],
                                write_continuation_fun_call: Optional[Callable[[TemplateBodyWriter], None]],
                                writer: TemplateBodyWriter):

    lhs_vars = tuple(var_reference_to_ir0(var)
                     for var in assignment.lhs_list)
    lhs_var_names = {var.cpp_type for var in lhs_vars}
    rhs_var = var_reference_to_ir0(assignment.rhs)

    elem_kind = lhs_vars[0].expr_type.kind
    if elem_kind == ir0.ExprKind.BOOL:
        list_literal = GlobalLiterals.BOOL_LIST
    elif elem_kind == ir0.ExprKind.INT64:
        list_literal = GlobalLiterals.INT_LIST
    elif elem_kind == ir0.ExprKind.TYPE:
        list_literal = GlobalLiterals.LIST
    else:
        raise NotImplementedError('elem_kind: %s' % elem_kind)

    then_writer = writer.create_sibling_writer(writer.parent_arbitrary_arg, writer.parent_return_type)

    lhs = var_reference_to_ir0(assignment.rhs)
    rhs = _create_template_instantiation(template_name=list_literal.cpp_type,
                                         arg_exprs=assignment.lhs_list,
                                         instantiation_might_trigger_static_asserts=False,
                                         writer=then_writer)

    type_ir0 = type_to_ir0(assignment.rhs.expr_type)
    if type_ir0.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
        then_writer.write(ir0.ConstantDef(name=lhs.cpp_type, expr=rhs))
    else:
        then_writer.write(ir0.Typedef(name=lhs.cpp_type, expr=rhs))

    stmts_to_ir0(other_stmts, write_continuation_fun_call, then_writer)

    forwarded_vars = [var
                      for var in _get_free_vars_in_elements(then_writer.elems)
                      if var.cpp_type != rhs_var.cpp_type and var.cpp_type not in lhs_var_names]
    assert all(var.cpp_type != rhs_var.cpp_type
               for var in forwarded_vars)

    forwarded_vars_args = [ir0.TemplateArgDecl(expr_type=var.expr_type, name=var.cpp_type, is_variadic=var.is_variadic)
                           for var in forwarded_vars]
    forwarded_vars_exprs = [ir0.AtomicTypeLiteral.for_local(cpp_type=var.cpp_type,
                                                            expr_type=var.expr_type,
                                                            is_variadic=var.is_variadic)
                            for var in forwarded_vars]


    # template <typename L, ...>
    # struct Id1 {
    #   static_assert(AlwaysFalseFromType<L>::value, "<message>");
    #   using type = void; // Or a definition of `value`
    # };
    rhs_var_arg_decl = ir0.TemplateArgDecl(expr_type=ir0.TypeType(), name=rhs_var.cpp_type, is_variadic=rhs_var.is_variadic)
    always_false_instantiation = ir0.TemplateInstantiation(template_expr=GlobalLiterals.ALWAYS_FALSE_FROM_TYPE,
                                                           args=(rhs_var,),
                                                           instantiation_might_trigger_static_asserts=False)
    always_false_expr = ir0.ClassMemberAccess(inner_expr=always_false_instantiation,
                                              member_name='value',
                                              expr_type=ir0.BoolType())
    main_definition_args = (rhs_var_arg_decl, *forwarded_vars_args)
    main_definition_body_writer = writer.create_sibling_writer(writer.parent_arbitrary_arg, writer.parent_return_type)
    main_definition_body_writer.write(ir0.StaticAssert(expr=always_false_expr,
                                                       message=assignment.error_message))
    main_definition_body_writer.write_result_body_elements(result_expr=None, error_expr=None)
    main_definition = ir0.TemplateSpecialization(args=main_definition_args,
                                                 patterns=None,
                                                 body=tuple(main_definition_body_writer.elems),
                                                 is_metafunction=True)

    # template <int64_t n0, int64_t n1, int64_t n2, ...>
    # struct Id1<Int64List<n0, n1, n2>, ...> {
    #   using L = Int64List<n0, n1, n2>;
    #   ...
    # };
    lhs_vars_arg_decls = tuple(ir0.TemplateArgDecl(expr_type=var.expr_type, name=var.cpp_type, is_variadic=var.is_variadic)
                               for var in lhs_vars)
    list_pattern = ir0.TemplateInstantiation(list_literal,
                                             args=lhs_vars,
                                             instantiation_might_trigger_static_asserts=False)
    specialization = ir0.TemplateSpecialization(args=(*lhs_vars_arg_decls, *forwarded_vars_args),
                                                patterns=(list_pattern, *forwarded_vars_exprs),
                                                body=tuple(then_writer.elems),
                                                is_metafunction=True)

    template_defn = ir0.TemplateDefn(name=writer.new_id(),
                                     description='(meta)function wrapping an unpacking assignment',
                                     main_definition=main_definition,
                                     specializations=(specialization,),
                                     result_element_names=frozenset(('value', 'type', 'error')))
    writer.write_toplevel_elem(template_defn)

    if assignment.source_branch:
        writer.write(ir0.NoOpStmt(assignment.source_branch))

    function_call_expr, function_call_error_expr = _create_metafunction_call(ir0.AtomicTypeLiteral.from_nonlocal_template_defn(template_defn,
                                                                                                                               is_metafunction_that_may_return_error=True),
                                                                             args=(rhs_var, *forwarded_vars_exprs),
                                                                             member_type=writer.parent_return_type,
                                                                             writer=writer)

    writer.write_result_body_elements(result_expr=function_call_expr,
                                      error_expr=function_call_error_expr)

def stmts_to_ir0(stmts: Sequence[ir1.Stmt],
                 write_continuation_fun_call: Optional[Callable[[TemplateBodyWriter], None]],
                 writer: Writer):
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, ir1.Assert):
            assert_to_ir0(stmt, writer)
        elif isinstance(stmt, ir1.Assignment):
            assignment_to_ir0(stmt, writer)
        elif isinstance(stmt, ir1.PassStmt):
            pass_stmt_to_ir0(stmt, writer)
        elif isinstance(stmt, ir1.ReturnStmt):
            assert isinstance(writer, TemplateBodyWriter)
            return_stmt_to_ir0(stmt, writer)
        elif isinstance(stmt, ir1.IfStmt):
            assert isinstance(writer, TemplateBodyWriter)
            if_stmt_to_ir0(stmt, stmts[index + 1:], write_continuation_fun_call, writer)
            break
        elif isinstance(stmt, ir1.UnpackingAssignment):
            unpacking_assignment_to_ir0(stmt, stmts[index + 1:], write_continuation_fun_call, writer)
            break
        else:
            raise NotImplementedError('Unexpected statement type: ' + stmt.__class__.__name__)

    if write_continuation_fun_call:
        assert isinstance(writer, TemplateBodyWriter)
        write_continuation_fun_call(writer)

def _select_arbitrary_parent_arg(args: Sequence[ir0.TemplateArgDecl]) -> ir0.TemplateArgDecl:
    assert args
    # Prefer a non-template arg (if any), as that will lead to simpler/smaller generated code.
    for arg in args:
        if arg.expr_type.kind != ir0.ExprKind.TEMPLATE:
            return arg
    return args[0]

def function_defn_to_ir0(function_defn: ir1.FunctionDefn, writer: ToplevelWriter):
    try:
        args = []
        specialization_args = []
        patterns = []
        has_nontrivial_patterns = False
        extra_stmts = []
        for arg in function_defn.args:
            ir0_arg = function_arg_decl_to_ir0(arg)
            args.append(ir0_arg)
            if isinstance(arg.expr_type, ir1.ListType):
                elem_type = type_to_ir0(arg.expr_type.elem_type)
                elems_literal = ir0.AtomicTypeLiteral.for_local(cpp_type=writer.new_id(),
                                                                expr_type=elem_type,
                                                                is_variadic=True)
                specialization_args.append(ir0.TemplateArgDecl(name=elems_literal.cpp_type,
                                                               expr_type=elems_literal.expr_type,
                                                               is_variadic=True))
                template_instantiation = ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=list_template_name_for_type(elem_type),
                                                                                                                             args=(ir0.TemplateArgType(expr_type=elem_type,
                                                                                                                                                       is_variadic=True),),
                                                                                                                             is_metafunction_that_may_return_error=False,
                                                                                                                             may_be_alias=False),
                                                                   args=(ir0.VariadicTypeExpansion(elems_literal),),
                                                                   instantiation_might_trigger_static_asserts=False)
                patterns.append(template_instantiation)
                extra_stmts.append(ir0.Typedef(name=arg.name,
                                               expr=template_instantiation))
                has_nontrivial_patterns = True
            else:
                patterns.append(ir0.AtomicTypeLiteral.for_local(cpp_type=ir0_arg.name,
                                                                expr_type=ir0_arg.expr_type,
                                                                is_variadic=ir0_arg.is_variadic))
                specialization_args.append(ir0_arg)

        if args:
            parent_arbitrary_arg = _select_arbitrary_parent_arg(args)
        else:
            parent_arbitrary_arg = ir0.TemplateArgDecl(expr_type=ir0.TypeType(),
                                                       name=writer.new_id(),
                                                       is_variadic=False)
            args = [parent_arbitrary_arg]
            assert not has_nontrivial_patterns

        return_type = type_to_ir0(function_defn.return_type)
        body_writer = TemplateBodyWriter(writer,
                                         parent_arbitrary_arg=parent_arbitrary_arg,
                                         parent_return_type=return_type)
        for stmt in extra_stmts:
            body_writer.write(stmt)
        stmts_to_ir0(function_defn.body,
                     write_continuation_fun_call=None,
                     writer=body_writer)

        if return_type.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
            result_element_names = frozenset(('value', 'error'))
        else:
            result_element_names = frozenset(('type', 'error'))

        if has_nontrivial_patterns:
            # We don't really need a specialization, but defining this template only for the list types helps the
            # optimizer inline other templates into this one (since it can assume that the param is a list).
            specialization = _create_metafunction_specialization(args=tuple(specialization_args),
                                                                 patterns=tuple(patterns),
                                                                 body=tuple(body_writer.elems))

            writer.write_toplevel_elem(ir0.TemplateDefn(main_definition=None,
                                                        args=tuple(args),
                                                        name=function_defn.name,
                                                        description=function_defn.description,
                                                        specializations=(specialization,),
                                                        result_element_names=result_element_names))
        else:
            main_definition = _create_metafunction_specialization(args=tuple(args),
                                                                  patterns=None,
                                                                  body=tuple(body_writer.elems))

            writer.write_toplevel_elem(ir0.TemplateDefn(main_definition=main_definition,
                                                        name=function_defn.name,
                                                        description=function_defn.description,
                                                        specializations=(),
                                                        result_element_names=result_element_names))
    except (AssertionError, AttributeError, TypeError) as e:  # pragma: no cover
        print('While converting a function defn to low IR:\n' + str(ir1.Module(body=(function_defn,),
                                                                               public_names=frozenset())))
        raise e

def check_if_error_defn_to_ir0(check_if_error_defn: ir1.CheckIfErrorDefn, writer: ToplevelWriter):
    # template <int x, bool b, typename T>
    # struct CheckIfError<MyErrorHolder<x, b, T>> {
    #   static_assert(Select1stBoolBool<false, x>::value,
    #                 "<MyError's message>");
    #   using type = void;
    # };
    specializations = [ir0.TemplateSpecialization(args=tuple(ir0.TemplateArgDecl(expr_type=type_to_ir0(arg_decl.expr_type),
                                                                                 name=arg_decl.name,
                                                                                 is_variadic=isinstance(arg_decl.expr_type, ir1.ParameterPackType))
                                                             for arg_decl in custom_error_type.arg_types),
                                                  patterns=(ir0.TemplateInstantiation(ir0.AtomicTypeLiteral.for_nonlocal_template(cpp_type=writer.get_holder_template_name_for_error(custom_error_type.name),
                                                                                                                                  args=tuple(ir0.TemplateArgType(type_to_ir0(arg_type.expr_type),
                                                                                                                                                                 is_variadic=isinstance(arg_type.expr_type, ir1.ParameterPackType))
                                                                                                                                             for arg_type in custom_error_type.arg_types),
                                                                                                                                  is_metafunction_that_may_return_error=False,
                                                                                                                                  may_be_alias=False),
                                                                                      args=tuple(ir0.AtomicTypeLiteral.for_local(arg.name,
                                                                                                                                 expr_type=type_to_ir0(arg.expr_type),
                                                                                                                                 is_variadic=isinstance(arg.expr_type, ir1.ParameterPackType))
                                                                                                 for arg in custom_error_type.arg_types),
                                                                                      instantiation_might_trigger_static_asserts=False),),
                                                  body=(ir0.StaticAssert(expr=ir0.Literal(value=False),
                                                                         message=error_message),
                                                        ir0.Typedef(name='type',
                                                                    expr=ir0.AtomicTypeLiteral.for_nonlocal_type('void', may_be_alias=False))),
                                                  is_metafunction=True)
                       for custom_error_type, error_message in check_if_error_defn.error_types_and_messages]
    for specialization in specializations:
        writer.write_check_if_error_specialization(specialization)

def check_if_error_to_ir0(check_if_error: ir1.CheckIfError, writer: ToplevelWriter):
    # using x99 = CheckIfError<X>::type;
    writer.write(ir0.Typedef(name=writer.new_id(),
                             expr=ir0.ClassMemberAccess(inner_expr=ir0.TemplateInstantiation(template_expr=GlobalLiterals.CHECK_IF_ERROR,
                                                                                             args=(var_reference_to_ir0(check_if_error.var),),
                                                                                             instantiation_might_trigger_static_asserts=True),
                                                        member_name='type',
                                                        expr_type=ir0.TypeType())))

def list_expr_to_ir1(list_expr: Union[ir1.ListExpr, ir1.ListPatternExpr], writer: Writer):
    # [1, 2, x]
    #
    # Becomes:
    #
    # IntList<1, 2, x>

    list_template_name = list_template_name_for_type(type_to_ir0(list_expr.elem_type))

    arg_exprs = list(list_expr.elems)
    if isinstance(list_expr, ir1.ListPatternExpr) and list_expr.list_extraction_expr:
        arg_exprs.append(ir1.ParameterPackExpansion(ir1.VarReference(expr_type=ir1.ParameterPackType(list_expr.list_extraction_expr.expr_type),
                                                                     name=list_expr.list_extraction_expr.name,
                                                                     is_global_function=list_expr.list_extraction_expr.is_global_function,
                                                                     is_function_that_may_throw=list_expr.list_extraction_expr.is_function_that_may_throw),
                                                    ))

    return _create_template_instantiation(template_name=list_template_name,
                                          arg_exprs=arg_exprs,
                                          instantiation_might_trigger_static_asserts=False,
                                          writer=writer)

def int_list_sum_expr_to_ir0(expr: ir1.IntListSumExpr, writer: Writer):
    # sum(l)
    #
    # Becomes:
    #
    # Int64ListSum<l>::value

    template_instantiation = _create_template_instantiation(template_name='Int64ListSum',
                                                            arg_exprs=[expr.var],
                                                            instantiation_might_trigger_static_asserts=False,
                                                            writer=writer)

    return ir0.ClassMemberAccess(inner_expr=template_instantiation,
                                 member_name='value',
                                 expr_type=ir0.Int64Type())

def bool_list_all_expr_to_ir0(expr: ir1.BoolListAllExpr, writer: Writer):
    # all(l)
    #
    # Becomes:
    #
    # BoolListAll<l>::value

    template_instantiation = _create_template_instantiation(template_name='BoolListAll',
                                                            arg_exprs=[expr.var],
                                                            instantiation_might_trigger_static_asserts=False,
                                                            writer=writer)

    return ir0.ClassMemberAccess(inner_expr=template_instantiation,
                                 member_name='value',
                                 expr_type=ir0.BoolType())


def bool_list_any_expr_to_ir0(expr: ir1.BoolListAnyExpr, writer: Writer):
    # any(l)
    #
    # Becomes:
    #
    # BoolListAny<l>::value

    template_instantiation = _create_template_instantiation(template_name='BoolListAny',
                                                            arg_exprs=[expr.var],
                                                            instantiation_might_trigger_static_asserts=False,
                                                            writer=writer)

    return ir0.ClassMemberAccess(inner_expr=template_instantiation,
                                 member_name='value',
                                 expr_type=ir0.BoolType())

def list_concat_expr_to_ir0(expr: ir1.ListConcatExpr, writer: Writer):
    # l1 + l2
    #
    # Becomes (if l1 and l2 are lists of ints):
    #
    # Int64ListConcat<l1, l2>::type

    elem_kind = type_to_ir0(expr.expr_type.elem_type).kind
    if elem_kind == ir0.ExprKind.BOOL:
        list_concat_template_name = 'BoolListConcat'
    elif elem_kind == ir0.ExprKind.INT64:
        list_concat_template_name = 'Int64ListConcat'
    elif elem_kind == ir0.ExprKind.TYPE:
        list_concat_template_name = 'TypeListConcat'
    else:
        raise NotImplementedError('elem_kind: %s' % elem_kind)

    template_instantiation = _create_template_instantiation(template_name=list_concat_template_name,
                                                            arg_exprs=[expr.lhs, expr.rhs],
                                                            instantiation_might_trigger_static_asserts=False,
                                                            writer=writer)

    return ir0.ClassMemberAccess(inner_expr=template_instantiation,
                                 member_name='type',
                                 expr_type=type_to_ir0(expr.expr_type))

def template_instantiation_pattern_expr_to_ir0(expr: ir1.TemplateInstantiationPatternExpr, writer: Writer):
    arg_exprs = list(expr.arg_exprs)
    if expr.list_extraction_arg_expr:
        arg_exprs.append(ir1.ParameterPackExpansion(ir1.VarReference(expr_type=ir1.ParameterPackType(expr.list_extraction_arg_expr.expr_type),
                                                                     name=expr.list_extraction_arg_expr.name,
                                                                     is_global_function=expr.list_extraction_arg_expr.is_global_function,
                                                                     is_function_that_may_throw=expr.list_extraction_arg_expr.is_function_that_may_throw)))
    return _create_template_instantiation(template_name=expr.template_atomic_cpp_type,
                                          arg_exprs=arg_exprs,
                                          instantiation_might_trigger_static_asserts=False,
                                          writer=writer)

def set_to_list_expr_to_ir0(expr: ir1.SetToListExpr):
    return var_reference_to_ir0(expr.var)

def module_to_ir0(module: ir1.Module, identifier_generator: Iterator[str]):
    writer = ToplevelWriter(identifier_generator)
    public_names = set(module.public_names)
    for toplevel_elem in module.body:
        if isinstance(toplevel_elem, ir1.FunctionDefn):
            function_defn_to_ir0(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir1.Assert):
            assert_to_ir0(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir1.Assignment):
            assignment_to_ir0(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir1.CustomType):
            custom_type_defn_to_ir0(toplevel_elem, public_names, writer)
        elif isinstance(toplevel_elem, ir1.CheckIfErrorDefn):
            check_if_error_defn_to_ir0(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir1.CheckIfError):
            check_if_error_to_ir0(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir1.PassStmt):
            pass_stmt_to_ir0(toplevel_elem, writer)
        else:
            raise NotImplementedError('Unexpected toplevel element: %s' % str(toplevel_elem.__class__))
    return ir0.Header(template_defns=tuple(writer.template_defns),
                      check_if_error_specializations=tuple(writer.check_if_error_specializations),
                      toplevel_content=tuple(writer.toplevel_elems),
                      public_names=frozenset(public_names),
                      split_template_name_by_old_name_and_result_element_name=())
