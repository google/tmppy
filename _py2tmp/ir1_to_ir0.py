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
from _py2tmp import utils
from typing import List, Tuple, Optional, Iterator, Union, Callable, Dict

class Writer:
    def new_id(self) -> str: ...  # pragma: no cover

    def write(self, elem: Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]): ...  # pragma: no cover

    def get_is_instance_template_name_for_error(self, error_name: str) -> str: ...  # pragma: no cover

class ToplevelWriter(Writer):
    def __init__(self, identifier_generator: Iterator[str]):
        self.identifier_generator = identifier_generator
        self.elems = []  # type: List[Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]]
        self.holder_template_name_for_error = dict()  # type: Dict[str, str]
        self.is_instance_template_name_for_error = dict()  # type: Dict[str, str]

    def new_id(self):
        return next(self.identifier_generator)

    def write(self, elem: Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]):
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
                 parent_arbitrary_arg: ir0.TemplateArgDecl,
                 parent_return_type: Optional[ir0.ExprType]):
        self.writer = writer
        self.elems = []  # type: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]]
        self.parent_arbitrary_arg = parent_arbitrary_arg
        self.parent_return_type = parent_return_type
        self.result_body_elements_written = False

    def new_id(self):
        return self.writer.new_id()

    def write(self, elem: Union[ir0.TemplateDefn, ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]):
        if isinstance(elem, ir0.TemplateDefn):
            self.writer.write(elem)
        else:
            self.elems.append(elem)

    def write_result_body_elements(self,
                                   result_expr: Optional[ir0.Expr],
                                   error_expr: Optional[ir0.Expr]):
        assert self.parent_return_type
        assert result_expr or error_expr
        if error_expr:
            assert isinstance(error_expr.type, ir0.TypeType)

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
                                   expr=result_expr or ir0.TypeLiteral.for_nonlocal_type('void')))

        if error_expr is None:
            error_expr = ir0.TypeLiteral.for_nonlocal_type('void')
        self.write(ir0.Typedef(name='error',
                               expr=error_expr))

    def create_sibling_writer(self,
                              parent_arbitrary_arg: ir0.TemplateArgDecl,
                              parent_return_type: ir0.ExprType):
        return TemplateBodyWriter(self.writer,
                                  parent_arbitrary_arg=parent_arbitrary_arg,
                                  parent_return_type=parent_return_type)

    def get_is_instance_template_name_for_error(self, error_name: str):
        return self.writer.get_is_instance_template_name_for_error(error_name)

def type_to_ir0(type: ir1.ExprType):
    if isinstance(type, ir1.BoolType):
        return ir0.BoolType()
    elif isinstance(type, ir1.IntType):
        return ir0.Int64Type()
    elif isinstance(type, ir1.TypeType):
        return ir0.TypeType()
    elif isinstance(type, ir1.CustomType):
        return ir0.TypeType()
    elif isinstance(type, ir1.ErrorOrVoidType):
        return ir0.TypeType()
    elif isinstance(type, ir1.FunctionType):
        return function_type_to_ir0(type)
    elif isinstance(type, ir1.BottomType):
        return ir0.TypeType()
    else:
        raise NotImplementedError('Unexpected type: %s' % str(type.__class__))

def function_type_to_ir0(fun_type: ir1.FunctionType):
    return ir0.TemplateType(argtypes=[type_to_ir0(arg)
                                      for arg in fun_type.argtypes])

def expr_to_ir0(expr: ir1.Expr, writer: Writer) -> Tuple[Optional[ir0.Expr], Optional[ir0.Expr]]:
    if isinstance(expr, ir1.VarReference):
        return var_reference_to_ir0(expr), None
    elif isinstance(expr, ir1.MatchExpr):
        assert isinstance(writer, TemplateBodyWriter)
        return match_expr_to_ir0(expr, writer)
    elif isinstance(expr, ir1.BoolLiteral):
        return bool_literal_to_ir0(expr)
    elif isinstance(expr, ir1.IntLiteral):
        return int_literal_to_ir0(expr)
    elif isinstance(expr, ir1.TypeLiteral):
        return type_literal_to_ir0(expr)
    elif isinstance(expr, ir1.FunctionCall):
        return function_call_to_ir0(expr, writer)
    elif isinstance(expr, ir1.EqualityComparison):
        return equality_comparison_to_ir0(expr, writer)
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
    elif isinstance(expr, ir1.ClassMemberAccess):
        return class_member_access_expr_to_ir0(expr, writer), None
    elif isinstance(expr, ir1.TemplateInstantiation):
        return template_instantiation_expr_to_ir0(expr, writer), None
    elif isinstance(expr, ir1.AddToSetExpr):
        return add_to_set_expr_to_ir0(expr), None
    elif isinstance(expr, ir1.SetEqualityComparison):
        return set_equality_comparison_expr_to_ir0(expr), None
    elif isinstance(expr, ir1.ListToSetExpr):
        return list_to_set_expr_to_ir0(expr), None
    else:
        raise NotImplementedError('Unexpected expression: %s' % str(expr.__class__))

def function_arg_decl_to_ir0(decl: ir1.FunctionArgDecl):
    return ir0.TemplateArgDecl(type=type_to_ir0(decl.type),
                               name=decl.name)

def var_reference_to_ir0(var: ir1.VarReference):
    if var.is_global_function:
        ir0_type = type_to_ir0(var.type)
        assert isinstance(ir0_type, ir0.TemplateType)
        return ir0.TypeLiteral.for_nonlocal_template(cpp_type=var.name,
                                                     arg_types=ir0_type.argtypes,
                                                     is_metafunction_that_may_return_error=True)
    else:
        return ir0.TypeLiteral.for_local(cpp_type=var.name,
                                         type=type_to_ir0(var.type))

def _create_metafunction_call(template_expr: ir0.Expr,
                              args: List[ir0.Expr],
                              member_type: ir0.ExprType,
                              writer: Writer):
    assert isinstance(template_expr.type, ir0.TemplateType)
    if isinstance(member_type, (ir0.BoolType, ir0.Int64Type)):
        member_name = 'value'
    else:
        member_name = 'type'
    template_instantiation_expr = ir0.TemplateInstantiation(template_expr=template_expr,
                                                            args=args,
                                                            instantiation_might_trigger_static_asserts=True)
    if isinstance(writer, ToplevelWriter) and (not isinstance(template_expr, ir0.TypeLiteral)
                                               or template_expr.is_metafunction_that_may_return_error):
        # using T = CheckIfError<F<x, y>::error>::type;
        check_if_error_template_instantiation_expr = ir0.TemplateInstantiation(template_expr=ir0.TypeLiteral.for_nonlocal_template(cpp_type='CheckIfError',
                                                                                                                                   arg_types=[ir0.TypeType()],
                                                                                                                                   is_metafunction_that_may_return_error=False),
                                                                               args=[ir0.ClassMemberAccess(class_type_expr=template_instantiation_expr,
                                                                                                           member_name='error',
                                                                                                           member_type=ir0.TypeType())],
                                                                               instantiation_might_trigger_static_asserts=True)
        writer.write(ir0.Typedef(name=writer.new_id(),
                                 expr=ir0.ClassMemberAccess(class_type_expr=check_if_error_template_instantiation_expr,
                                                            member_name='type',
                                                            member_type=ir0.TypeType())))
    result_expr = ir0.ClassMemberAccess(class_type_expr=template_instantiation_expr,
                                        member_name=member_name,
                                        member_type=member_type)
    error_expr = ir0.ClassMemberAccess(class_type_expr=template_instantiation_expr,
                                       member_name='error',
                                       member_type=ir0.TypeType())
    return result_expr, error_expr

def _create_metafunction_specialization(args: List[ir0.TemplateArgDecl],
                                        patterns: Optional[List[ir0.TemplateArgPatternLiteral]],
                                        body: List[Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef]]):

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

    return ir0.TemplateSpecialization(args=args, patterns=patterns, body=body)

def match_expr_to_ir0(match_expr: ir1.MatchExpr,
                      writer: TemplateBodyWriter):
    forwarded_args = []  # type: List[ir1.VarReference]
    forwarded_args_names = set()
    for match_case in match_expr.match_cases:
        local_vars = set(match_case.matched_var_names)
        for var in match_case.expr.get_free_variables():
            if var.name not in local_vars and var.name not in forwarded_args_names:
                forwarded_args_names.add(var.name)
                forwarded_args.append(var)

    if forwarded_args or all(match_case.matched_var_names
                             for match_case in match_expr.match_cases):
        forwarded_args_decls = [ir0.TemplateArgDecl(type=type_to_ir0(var_ref.type), name=var_ref.name)
                                for var_ref in forwarded_args]
        forwarded_args_exprs = [ir0.TypeLiteral.for_local(cpp_type=var_ref.name,
                                                          type=type_to_ir0(var_ref.type))
                                for var_ref in forwarded_args]
        forwarded_args_patterns = [ir0.TemplateArgPatternLiteral(cxx_pattern=var_ref.name)
                                   for var_ref in forwarded_args]
    else:
        # We must add a dummy parameter so that the specialization isn't a full specialization.
        dummy_param_name = writer.new_id()
        forwarded_args_decls = [ir0.TemplateArgDecl(type=ir0.TypeType(),
                                                    name=dummy_param_name)]
        forwarded_args_exprs = [ir0.TypeLiteral.for_nonlocal_type('void')]
        forwarded_args_patterns = [ir0.TemplateArgPatternLiteral(cxx_pattern=dummy_param_name)]

    matched_vars = [var_reference_to_ir0(var)
                    for var in match_expr.matched_vars]

    main_definition = None
    specializations = []
    for match_case in match_expr.match_cases:
        specialization_arg_decls = forwarded_args_decls + [ir0.TemplateArgDecl(type=ir0.TypeType(), name=arg_name)
                                                           for arg_name in match_case.matched_var_names]

        specialization_patterns = forwarded_args_patterns + [ir0.TemplateArgPatternLiteral(cxx_pattern=pattern)
                                                             for pattern in match_case.type_patterns]

        match_case_writer = TemplateBodyWriter(writer,
                                               parent_arbitrary_arg=writer.parent_arbitrary_arg,
                                               parent_return_type=type_to_ir0(match_case.expr.type))

        expr_ir0, error_expr = expr_to_ir0(match_case.expr, match_case_writer)
        match_case_writer.write_result_body_elements(result_expr=expr_ir0,
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

    args_decls = forwarded_args_decls + [ir0.TemplateArgDecl(type=ir0.TypeType(), name='')
                                         for _ in match_expr.matched_vars]

    args_exprs = forwarded_args_exprs + matched_vars

    helper_function = ir0.TemplateDefn(args=args_decls,
                                       main_definition=main_definition,
                                       specializations=specializations,
                                       name=writer.new_id(),
                                       description='(meta)function wrapping a match expression',
                                       result_element_names=['value', 'type', 'error'])
    writer.write(helper_function)

    helper_function_reference = ir0.TypeLiteral.from_nonlocal_template_defn(helper_function,
                                                                            is_metafunction_that_may_return_error=True)
    return _create_metafunction_call(template_expr=helper_function_reference,
                                     args=args_exprs,
                                     member_type=type_to_ir0(match_expr.type),
                                     writer=writer)

def bool_literal_to_ir0(literal: ir1.BoolLiteral):
    return ir0.Literal(value=literal.value), None

def int_literal_to_ir0(literal: ir1.IntLiteral):
    return ir0.Literal(value=literal.value), None

def type_literal_to_ir0(literal: ir1.TypeLiteral):
    type = type_to_ir0(literal.type)
    kind = type.kind
    replacements = dict()
    arg_literals = []
    for arg_name, arg_expr in sorted(literal.args.items(), key=lambda item: item[0]):
        arg_literal = var_reference_to_ir0(arg_expr)
        arg_literals.append(arg_literal)
        assert isinstance(arg_literal.type, ir0.TypeType)
        assert not arg_literal.is_metafunction_that_may_return_error
        replacements[arg_name] = arg_literal.cpp_type
    expr = ir0.TypeLiteral.for_nonlocal(cpp_type=utils.replace_identifiers(literal.cpp_type, replacements),
                                        type=type,
                                        is_metafunction_that_may_return_error=(kind == ir0.ExprKind.TEMPLATE),
                                        referenced_locals=arg_literals)
    return expr, None

def function_call_to_ir0(call_expr: ir1.FunctionCall, writer: Writer):
    fun = var_reference_to_ir0(call_expr.fun)
    args = [var_reference_to_ir0(arg)
            for arg in call_expr.args]

    assert isinstance(call_expr.fun.type, ir1.FunctionType)
    return _create_metafunction_call(template_expr=fun,
                                     args=args,
                                     member_type=type_to_ir0(call_expr.fun.type.returns),
                                     writer=writer)

def equality_comparison_to_ir0(comparison_expr: ir1.EqualityComparison, writer: Writer):
    lhs = var_reference_to_ir0(comparison_expr.lhs)
    rhs = var_reference_to_ir0(comparison_expr.rhs)
    if isinstance(lhs.type, ir0.TypeType):
        std_is_same = ir0.TypeLiteral.for_nonlocal_template(cpp_type='std::is_same',
                                                            is_metafunction_that_may_return_error=False,
                                                            arg_types=[ir0.TypeType(), ir0.TypeType()])
        comparison_expr, comparison_error_expr = _create_metafunction_call(template_expr=std_is_same,
                                                                           args=[lhs, rhs],
                                                                           member_type=ir0.BoolType(),
                                                                           writer=writer)
    else:
        comparison_expr = ir0.ComparisonExpr(lhs=lhs, rhs=rhs, op='==')
        comparison_error_expr = None
    return comparison_expr, comparison_error_expr

def attribute_access_expr_to_ir0(attribute_access_expr: ir1.AttributeAccessExpr):
    class_expr = var_reference_to_ir0(attribute_access_expr.var)
    assert isinstance(class_expr.type, ir0.TypeType)
    expr = ir0.ClassMemberAccess(class_type_expr=class_expr,
                                 member_name=attribute_access_expr.attribute_name,
                                 member_type=type_to_ir0(attribute_access_expr.type))
    return expr, None

def not_expr_to_ir0(not_expr: ir1.NotExpr):
    return ir0.NotExpr(expr=var_reference_to_ir0(not_expr.var)), None

def unary_minus_expr_to_ir0(expr: ir1.UnaryMinusExpr):
    return ir0.UnaryMinusExpr(expr=var_reference_to_ir0(expr.var)), None

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
    is_instance_of_type_template = ir0.TypeLiteral.for_nonlocal_template(cpp_type=writer.get_is_instance_template_name_for_error(expr.checked_type.name),
                                                                         is_metafunction_that_may_return_error=False,
                                                                         arg_types=[ir0.TypeType()])
    return _create_metafunction_call(template_expr=is_instance_of_type_template,
                                     args=[var_reference_to_ir0(expr.var)],
                                     member_type=ir0.BoolType(),
                                     writer=writer)

def safe_unchecked_cast_expr_to_ir0(expr: ir1.SafeUncheckedCast):
    assert type_to_ir0(expr.var.type).kind == type_to_ir0(expr.type).kind
    return var_reference_to_ir0(ir1.VarReference(type=expr.type,
                                                 name=expr.var.name,
                                                 is_global_function=expr.var.is_global_function,
                                                 is_function_that_may_throw=expr.var.is_function_that_may_throw))

def list_comprehension_expr_to_ir0(expr: ir1.ListComprehensionExpr, writer: Writer):
    captured_vars = [var
                     for var in ir1.get_unique_free_variables_in_stmts([ir1.ReturnStmt(result=expr.result_elem_expr,
                                                                                       error=None)])
                     if var.name != expr.loop_var.name]

    # TODO: introduce unchecked versions of these and use them when we know that the list comprehension can't result in
    # an error.
    transform_metafunction_name_for_kinds = {
        (ir0.ExprKind.BOOL, ir0.ExprKind.BOOL): 'TransformBoolListToBoolList',
        (ir0.ExprKind.BOOL, ir0.ExprKind.INT64): 'TransformBoolListToInt64List',
        (ir0.ExprKind.BOOL, ir0.ExprKind.TYPE): 'TransformBoolListToTypeList',
        (ir0.ExprKind.INT64, ir0.ExprKind.BOOL): 'TransformInt64ListToBoolList',
        (ir0.ExprKind.INT64, ir0.ExprKind.INT64): 'TransformInt64ListToInt64List',
        (ir0.ExprKind.INT64, ir0.ExprKind.TYPE): 'TransformInt64ListToTypeList',
        (ir0.ExprKind.TYPE, ir0.ExprKind.BOOL): 'TransformTypeListToBoolList',
        (ir0.ExprKind.TYPE, ir0.ExprKind.INT64): 'TransformTypeListToInt64List',
        (ir0.ExprKind.TYPE, ir0.ExprKind.TYPE): 'TransformTypeListToTypeList',
    }

    x_type = type_to_ir0(expr.loop_var.type)
    result_elem_type = type_to_ir0(expr.result_elem_expr.type)

    template_arg_decl = ir0.TemplateArgDecl(type=x_type,
                                            name=expr.loop_var.name)
    helper_template_body_writer = TemplateBodyWriter(writer,
                                                     parent_arbitrary_arg=template_arg_decl,
                                                     parent_return_type=result_elem_type)
    result_expr, error_expr = function_call_to_ir0(expr.result_elem_expr, helper_template_body_writer)
    helper_template_body_writer.write_result_body_elements(result_expr=result_expr, error_expr=error_expr)
    helper_template_defn = ir0.TemplateDefn(name=writer.new_id(),
                                            description='(meta)function wrapping the expression in a list comprehension',
                                            specializations=[],
                                            args=[template_arg_decl],
                                            main_definition=ir0.TemplateSpecialization(args=[template_arg_decl],
                                                                                       patterns=None,
                                                                                       body=helper_template_body_writer.elems),
                                            result_element_names=['type', 'value', 'error'])

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
        return _create_metafunction_call(template_expr=ir0.TypeLiteral.for_nonlocal_template(cpp_type=transform_metafunction_name_for_kinds[(x_type.kind, result_elem_type.kind)],
                                                                                             is_metafunction_that_may_return_error=expr.result_elem_expr.fun.is_function_that_may_throw,
                                                                                             arg_types=[ir0.TypeType(), ir0.TemplateType(argtypes=[arg.type for arg in helper_template_defn.args])]),
                                         args=[var_reference_to_ir0(expr.list_var),
                                               ir0.TypeLiteral.from_nonlocal_template_defn(helper_template_defn,
                                                                                           is_metafunction_that_may_return_error=expr.result_elem_expr.fun.is_function_that_may_throw)],
                                         member_type=type_to_ir0(expr.type),
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

        captured_vars_as_template_args = [ir0.TemplateArgDecl(type=type_to_ir0(var.type),
                                                              name=var.name)
                                          for var in captured_vars]
        helper_wrapper_template_defn = ir0.TemplateDefn(name=writer.new_id(),
                                                        description='(meta)function wrapping the metafunction that implements the expression in a list comprehension (to pass captured local vars)',
                                                        specializations=[],
                                                        args=captured_vars_as_template_args,
                                                        main_definition=ir0.TemplateSpecialization(args=captured_vars_as_template_args,
                                                                                                   patterns=None,
                                                                                                   body=[helper_template_defn]),
                                                        result_element_names=['value', 'type', 'error'])

        writer.write(helper_wrapper_template_defn)
        helper_template_expr = ir0.ClassMemberAccess(class_type_expr=ir0.TemplateInstantiation(template_expr=ir0.TypeLiteral.from_nonlocal_template_defn(helper_wrapper_template_defn,
                                                                                                                                                         is_metafunction_that_may_return_error=False),
                                                                                               args=[var_reference_to_ir0(var)
                                                                                                         for var in captured_vars],
                                                                                               instantiation_might_trigger_static_asserts=True),
                                                     member_name=helper_template_defn.name,
                                                     member_type=ir0.TemplateType(argtypes=[x_type]))
        return _create_metafunction_call(template_expr=ir0.TypeLiteral.for_nonlocal_template(cpp_type=transform_metafunction_name_for_kinds[(x_type.kind, result_elem_type.kind)],
                                                                                             arg_types=[type_to_ir0(expr.list_var.type),
                                                                                                        ir0.TemplateType(argtypes=[x_type])],
                                                                                             is_metafunction_that_may_return_error=expr.result_elem_expr.fun.is_function_that_may_throw),
                                         args=[var_reference_to_ir0(expr.list_var),
                                               helper_template_expr],
                                         member_type=type_to_ir0(expr.type),
                                         writer=writer)

def class_member_access_expr_to_ir0(expr: ir1.ClassMemberAccess, writer: Writer):
    result_var, error_var = expr_to_ir0(expr.class_type_expr, writer)
    assert not error_var
    return ir0.ClassMemberAccess(class_type_expr=result_var,
                                 member_name=expr.member_name,
                                 member_type=type_to_ir0(expr.member_type))

def template_instantiation_expr_to_ir0(expr: ir1.TemplateInstantiation, writer: Writer):
    return ir0.TemplateInstantiation(template_expr=ir0.TypeLiteral.for_nonlocal_template(cpp_type=expr.template_name,
                                                                                         arg_types=[type_to_ir0(arg.type)
                                                                                                    for arg in expr.args],
                                                                                         is_metafunction_that_may_return_error=False),
                                     args=[var_reference_to_ir0(arg)
                                           for arg in expr.args],
                                     instantiation_might_trigger_static_asserts=expr.instantiation_might_trigger_static_asserts)

def add_to_set_expr_to_ir0(expr: ir1.AddToSetExpr):
    # add_to_set(s, 3)
    #
    # Becomes:
    #
    # AddToInt64Set<s, 3>::type

    set_expr = var_reference_to_ir0(expr.set_expr)
    elem_expr = var_reference_to_ir0(expr.elem_expr)

    if isinstance(elem_expr.type, ir0.BoolType):
        template_name = 'AddToBoolSet'
    elif isinstance(elem_expr.type, ir0.Int64Type):
        template_name = 'AddToInt64Set'
    elif isinstance(elem_expr.type, ir0.TypeType):
        template_name = 'AddToTypeSet'
    else:
        raise NotImplementedError('Unexpected type kind: %s' % elem_expr.kind)

    add_to_set_instantiation = ir0.TemplateInstantiation(template_expr=ir0.TypeLiteral.for_nonlocal_template(cpp_type=template_name,
                                                                                                             is_metafunction_that_may_return_error=False,
                                                                                                             arg_types=[ir0.TypeType(), type_to_ir0(expr.elem_expr.type)]),
                                                         args=[set_expr, elem_expr],
                                                         instantiation_might_trigger_static_asserts=False)

    return ir0.ClassMemberAccess(class_type_expr=add_to_set_instantiation,
                                 member_name='type',
                                 member_type=ir0.TypeType())

def set_equality_comparison_expr_to_ir0(expr: ir1.SetEqualityComparison):
    # set_equals(x, y)
    #
    # Becomes:
    #
    # Int64SetEquals<x, y>::value

    lhs = var_reference_to_ir0(expr.lhs)
    rhs = var_reference_to_ir0(expr.rhs)
    assert lhs.type == rhs.type

    elem_type = type_to_ir0(expr.elem_type)
    if isinstance(elem_type, ir0.BoolType):
        template_name = 'BoolSetEquals'
    elif isinstance(elem_type, ir0.Int64Type):
        template_name = 'Int64SetEquals'
    elif isinstance(elem_type, ir0.TypeType):
        template_name = 'TypeSetEquals'
    else:
        raise NotImplementedError('Unexpected type: %s' % str(elem_type))

    set_equals_instantiation = ir0.TemplateInstantiation(template_expr=ir0.TypeLiteral.for_nonlocal_template(cpp_type=template_name,
                                                                                                             arg_types=[type_to_ir0(expr.lhs.type), type_to_ir0(expr.rhs.type)],
                                                                                                             is_metafunction_that_may_return_error=False),
                                                         args=[lhs, rhs],
                                                         instantiation_might_trigger_static_asserts=False)

    return ir0.ClassMemberAccess(class_type_expr=set_equals_instantiation,
                                 member_name='value',
                                 member_type=ir0.BoolType())

def list_to_set_expr_to_ir0(expr: ir1.ListToSetExpr):
    # list_to_set(x)
    #
    # Becomes:
    #
    # Int64ListToSet<x>::type

    var = var_reference_to_ir0(expr.var)

    elem_kind = type_to_ir0(expr.elem_type).kind
    if elem_kind == ir0.ExprKind.BOOL:
        template_name = 'BoolListToSet'
    elif elem_kind == ir0.ExprKind.INT64:
        template_name = 'Int64ListToSet'
    elif elem_kind == ir0.ExprKind.TYPE:
        template_name = 'TypeListToSet'
    else:
        raise NotImplementedError('Unexpected type kind: %s' % elem_kind)

    set_equals_instantiation = ir0.TemplateInstantiation(template_expr=ir0.TypeLiteral.for_nonlocal_template(cpp_type=template_name,
                                                                                                             arg_types=[type_to_ir0(expr.var.type)],
                                                                                                             is_metafunction_that_may_return_error=False),
                                                         args=[var],
                                                         instantiation_might_trigger_static_asserts=False)

    return ir0.ClassMemberAccess(class_type_expr=set_equals_instantiation,
                                 member_name='type',
                                 member_type=ir0.TypeType())

def assert_to_ir0(assert_stmt: ir1.Assert, writer: Writer):
    expr = var_reference_to_ir0(assert_stmt.var)
    writer.write(ir0.StaticAssert(expr=expr, message=assert_stmt.message))

def assignment_to_ir0(assignment: ir1.Assignment, writer: Writer):
    lhs = var_reference_to_ir0(assignment.lhs)
    rhs, rhs_error = expr_to_ir0(assignment.rhs, writer)

    type_ir0 = type_to_ir0(assignment.lhs.type)
    if type_ir0.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
        writer.write(ir0.ConstantDef(name=lhs.cpp_type, expr=rhs))
    else:
        writer.write(ir0.Typedef(name=lhs.cpp_type, expr=rhs))

    if assignment.lhs2:
        lhs2 = var_reference_to_ir0(assignment.lhs2)
        assert isinstance(rhs_error.type, ir0.TypeType)
        writer.write(ir0.Typedef(name=lhs2.cpp_type, expr=rhs_error))

def custom_type_defn_to_ir0(custom_type: ir1.CustomType, writer: ToplevelWriter):
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
        arg_type = type_to_ir0(arg.type)
        arg_types.append(arg_type)
        arg_decls.append(ir0.TemplateArgDecl(type=arg_type,
                                             name=forwarded_arg_name))

    holder_template_writer = TemplateBodyWriter(writer,
                                                parent_arbitrary_arg=_select_arbitrary_parent_arg(arg_decls),
                                                parent_return_type=None)
    holder_template_instantiation_args = []
    for arg, arg_decl in zip(custom_type.arg_types, arg_decls):
        lhs_var = ir1.VarReference(type=arg.type,
                                   name=arg.name,
                                   is_global_function=False,
                                   is_function_that_may_throw=isinstance(arg.type, ir1.FunctionType))
        rhs_var = ir1.VarReference(type=arg.type,
                                   name=arg_decl.name,
                                   is_global_function=False,
                                   is_function_that_may_throw=isinstance(arg.type, ir1.FunctionType))
        assignment_to_ir0(ir1.Assignment(lhs=lhs_var, rhs=rhs_var),
                          holder_template_writer)
        holder_template_instantiation_args.append(var_reference_to_ir0(rhs_var))

    holder_template = ir0.TemplateDefn(name=holder_template_id,
                                       description='Holder template for the custom type %s' % custom_type.name,
                                       args=arg_decls,
                                       specializations=[],
                                       main_definition=ir0.TemplateSpecialization(args=arg_decls,
                                                                                  patterns=None,
                                                                                  body=holder_template_writer.elems),
                                       result_element_names=[arg.name
                                                             for arg in custom_type.arg_types])
    writer.write(holder_template)

    constructor_fn_typedef = ir0.Typedef(name='type',
                                         expr=ir0.TemplateInstantiation(template_expr=ir0.TypeLiteral.from_nonlocal_template_defn(holder_template,
                                                                                                                                  is_metafunction_that_may_return_error=False),
                                                                        args=holder_template_instantiation_args,
                                                                        instantiation_might_trigger_static_asserts=False))
    constructor_fn_error_typedef = ir0.Typedef(name='error',
                                               expr=ir0.TypeLiteral.for_nonlocal_type('void'))
    constructor_fn = ir0.TemplateDefn(name=custom_type.name,
                                      description='Constructor (meta)function for the custom type %s' % custom_type.name,
                                      args=arg_decls,
                                      specializations=[],
                                      main_definition=ir0.TemplateSpecialization(args=arg_decls,
                                                                                 patterns=None,
                                                                                 body=[constructor_fn_typedef,
                                                                                           constructor_fn_error_typedef]),
                                      result_element_names=['type', 'error'])
    writer.write(constructor_fn)

    writer.set_holder_template_name_for_error(custom_type.name, holder_template_id)

    is_instance_template = ir0.TemplateDefn(name=writer.new_id(),
                                            description='isinstance() (meta)function for the custom type %s' % custom_type.name,
                                            args=[ir0.TemplateArgDecl(type=ir0.TypeType())],
                                            main_definition=ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(type=ir0.TypeType())],
                                                                                       patterns=None,
                                                                                       body=[ir0.ConstantDef(name='value',
                                                                                                             expr=ir0.Literal(value=False))]),
                                            specializations=[ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(type=type_to_ir0(arg.type), name=arg.name)
                                                                                              for arg in custom_type.arg_types],
                                                                                        patterns=[ir0.TemplateArgPatternLiteral('%s<%s>' % (
                                                                                                holder_template_id,
                                                                                                ', '.join(arg.name
                                                                                                          for arg in custom_type.arg_types)))],
                                                                                        body=[ir0.ConstantDef(name='value',
                                                                                                              expr=ir0.Literal(value=True))])],
                                            result_element_names=['value'])

    writer.write(is_instance_template)
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

def _get_free_vars_in_elements(elements: List[ir0.TemplateBodyElement]):
    free_var_names = set()
    bound_var_names = set()
    free_vars = [] # type: List[ir0.TypeLiteral]
    for element in elements:
        if isinstance(element, ir0.StaticAssert) or isinstance(element, ir0.ConstantDef) or isinstance(element, ir0.Typedef):
            for var in element.expr.get_free_vars():
                if var.cpp_type not in bound_var_names and var.cpp_type not in free_var_names:
                    free_var_names.add(var.cpp_type)
                    free_vars.append(var)
        else:
            raise NotImplementedError('Unexpected element type: %s' % str(element.__class__))
        if isinstance(element, ir0.ConstantDef) or isinstance(element, ir0.Typedef):
            bound_var_names.add(element.name)
    return free_vars

def if_stmt_to_ir0(if_stmt: ir1.IfStmt,
                   then_stmts: List[ir1.Stmt],
                   write_continuation_fun_call: Optional[Callable[[TemplateBodyWriter], None]],
                   writer: TemplateBodyWriter):

    cond_expr = var_reference_to_ir0(if_stmt.cond)

    if then_stmts:
        then_writer = writer.create_sibling_writer(writer.parent_arbitrary_arg, writer.parent_return_type)
        stmts_to_ir0(then_stmts, write_continuation_fun_call, then_writer)

        forwarded_vars = _get_free_vars_in_elements(then_writer.elems)

        forwarded_vars_args = [ir0.TemplateArgDecl(type=var.type, name=var.cpp_type)
                               for var in forwarded_vars]
        forwarded_vars_patterns = [ir0.TemplateArgPatternLiteral(cxx_pattern=var.cpp_type)
                                   for var in forwarded_vars]
        forwarded_vars_exprs = [ir0.TypeLiteral.for_local(cpp_type=var.cpp_type,
                                                          type=var.type)
                                for var in forwarded_vars]
        forwarded_vars_types = [var.type
                                for var in forwarded_vars]
        if not forwarded_vars:
            # We need to add a dummy template parameter, otherwise the "then" template will have no parameters and the C++
            # compiler will eagerly evaluate its body, even if it would never be instantiated (triggering e.g. any
            # assertions in that code).
            forwarded_vars_args.append(then_writer.parent_arbitrary_arg)
            forwarded_vars_patterns.append(ir0.TemplateArgPatternLiteral(cxx_pattern=then_writer.parent_arbitrary_arg.name))
            forwarded_vars_exprs.append(ir0.TypeLiteral.for_local(cpp_type=then_writer.parent_arbitrary_arg.name,
                                                                  type=then_writer.parent_arbitrary_arg.type))
            forwarded_vars_types.append(then_writer.parent_arbitrary_arg.type)

        then_template_defn = ir0.TemplateDefn(name=writer.new_id(),
                                              description='(meta)function wrapping the code after an if-else statement',
                                              args=forwarded_vars_args,
                                              main_definition=ir0.TemplateSpecialization(args=forwarded_vars_args,
                                                                                         patterns=None,
                                                                                         body=then_writer.elems),
                                              specializations=[],
                                              result_element_names=['value', 'type', 'error'])
        writer.write(then_template_defn)

        then_function_call_expr, then_function_call_error_expr = _create_metafunction_call(ir0.TypeLiteral.from_nonlocal_template_defn(then_template_defn,
                                                                                                                                       is_metafunction_that_may_return_error=True),
                                                                                           args=forwarded_vars_exprs,
                                                                                           member_type=writer.parent_return_type,
                                                                                           writer=writer)
    else:
        then_function_call_expr = None
        then_function_call_error_expr = None

    if write_continuation_fun_call is None and (then_function_call_expr or then_function_call_error_expr):
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

    forwarded_vars_args = [ir0.TemplateArgDecl(type=var.type, name=var.cpp_type)
                           for var in forwarded_vars]
    forwarded_vars_patterns = [ir0.TemplateArgPatternLiteral(cxx_pattern=var.cpp_type)
                               for var in forwarded_vars]
    forwarded_vars_exprs = [ir0.TypeLiteral.for_local(cpp_type=var.cpp_type,
                                                      type=var.type)
                            for var in forwarded_vars]
    forwarded_vars_types = [var.type
                            for var in forwarded_vars]
    if not forwarded_vars:
        # We need to add a dummy template parameter, otherwise the true/false specializations will be full specializations
        # and the C++ compiler will eagerly evaluate them, even if they would never be instantiated (triggering e.g.
        # any assertions in that code).
        forwarded_vars_args.append(writer.parent_arbitrary_arg)
        forwarded_vars_patterns.append(ir0.TemplateArgPatternLiteral(cxx_pattern=writer.parent_arbitrary_arg.name))
        forwarded_vars_exprs.append(ir0.TypeLiteral.for_local(cpp_type=writer.parent_arbitrary_arg.name,
                                                              type=writer.parent_arbitrary_arg.type))
        forwarded_vars_types.append(writer.parent_arbitrary_arg.type)

    if_branch_specialization = _create_metafunction_specialization(args=forwarded_vars_args,
                                                                   patterns=forwarded_vars_patterns + [ir0.TemplateArgPatternLiteral('true')],
                                                                   body=if_branch_writer.elems)
    else_branch_specialization = _create_metafunction_specialization(args=forwarded_vars_args,
                                                                     patterns=forwarded_vars_patterns + [ir0.TemplateArgPatternLiteral('false')],
                                                                     body=else_branch_writer.elems)

    fun_defn = ir0.TemplateDefn(main_definition=None,
                                name=writer.new_id(),
                                description='(meta)function generated for an if-else statement',
                                args=forwarded_vars_args + [ir0.TemplateArgDecl(type=ir0.BoolType())],
                                specializations=[if_branch_specialization, else_branch_specialization],
                                result_element_names=['value', 'type', 'error'])
    writer.write(fun_defn)
    function_call_expr, function_call_error_expr = _create_metafunction_call(ir0.TypeLiteral.from_nonlocal_template_defn(fun_defn,
                                                                                                                         is_metafunction_that_may_return_error=True),
                                                                             args=forwarded_vars_exprs + [cond_expr],
                                                                             member_type=writer.parent_return_type,
                                                                             writer=writer)

    writer.write_result_body_elements(result_expr=function_call_expr,
                                      error_expr=function_call_error_expr)

def unpacking_assignment_to_ir0(assignment: ir1.UnpackingAssignment,
                                other_stmts: List[ir1.Stmt],
                                write_continuation_fun_call: Optional[Callable[[TemplateBodyWriter], None]],
                                writer: TemplateBodyWriter):

    lhs_vars = [var_reference_to_ir0(var)
                for var in assignment.lhs_list]
    lhs_var_names = {var.cpp_type for var in lhs_vars}
    rhs_var = var_reference_to_ir0(assignment.rhs)

    elem_kind = lhs_vars[0].type.kind
    if elem_kind == ir0.ExprKind.BOOL:
        list_template_name = 'BoolList'
    elif elem_kind == ir0.ExprKind.INT64:
        list_template_name = 'Int64List'
    elif elem_kind == ir0.ExprKind.TYPE:
        list_template_name = 'List'
    else:
        raise NotImplementedError('elem_kind: %s' % elem_kind)

    then_writer = writer.create_sibling_writer(writer.parent_arbitrary_arg, writer.parent_return_type)
    assignment_to_ir0(ir1.Assignment(lhs=assignment.rhs,
                                     rhs=ir1.TemplateInstantiation(template_name=list_template_name,
                                                                   args=assignment.lhs_list,
                                                                   instantiation_might_trigger_static_asserts=False)),
                      then_writer)
    stmts_to_ir0(other_stmts, write_continuation_fun_call, then_writer)

    forwarded_vars = [var
                      for var in _get_free_vars_in_elements(then_writer.elems)
                      if var.cpp_type != rhs_var.cpp_type and var.cpp_type not in lhs_var_names]
    assert all(var.cpp_type != rhs_var.cpp_type
               for var in forwarded_vars)

    forwarded_vars_args = [ir0.TemplateArgDecl(type=var.type, name=var.cpp_type)
                           for var in forwarded_vars]
    forwarded_vars_patterns = [ir0.TemplateArgPatternLiteral(cxx_pattern=var.cpp_type)
                               for var in forwarded_vars]
    forwarded_vars_exprs = [ir0.TypeLiteral.for_local(cpp_type=var.cpp_type,
                                                      type=var.type)
                            for var in forwarded_vars]
    forwarded_vars_types = [var.type
                            for var in forwarded_vars]


    # template <typename L, ...>
    # struct Id1 {
    #   static_assert(AlwaysFalseFromType<L>::value, "<message>");
    # };
    rhs_var_arg_decl = ir0.TemplateArgDecl(type=ir0.TypeType(), name=rhs_var.cpp_type)
    always_false_instantiation = ir0.TemplateInstantiation(template_expr=ir0.TypeLiteral.for_nonlocal_template('AlwaysFalseFromType',
                                                                                                               arg_types=[ir0.TypeType()],
                                                                                                               is_metafunction_that_may_return_error=False),
                                                           args=[rhs_var],
                                                           instantiation_might_trigger_static_asserts=False)
    always_false_expr = ir0.ClassMemberAccess(class_type_expr=always_false_instantiation,
                                              member_name='value',
                                              member_type=ir0.BoolType())
    main_definition = ir0.TemplateSpecialization(args=[rhs_var_arg_decl] + forwarded_vars_args,
                                                 patterns=None,
                                                 body=[ir0.StaticAssert(expr=always_false_expr,
                                                                        message=assignment.error_message)])

    # template <int64_t n0, int64_t n1, int64_t n2, ...>
    # struct Id1<Int64List<n0, n1, n2>, ...> {
    #   using L = Int64List<n0, n1, n2>;
    #   ...
    # };
    lhs_vars_arg_decls = [ir0.TemplateArgDecl(type=var.type, name=var.cpp_type)
                          for var in lhs_vars]
    list_pattern = ir0.TemplateArgPatternLiteral('%s<%s>' % (list_template_name,
                                                             ', '.join(var.cpp_type for var in lhs_vars)))
    specialization = ir0.TemplateSpecialization(args=lhs_vars_arg_decls + forwarded_vars_args,
                                                patterns=[list_pattern] + forwarded_vars_patterns,
                                                body=then_writer.elems)

    template_defn = ir0.TemplateDefn(name=writer.new_id(),
                                     description='(meta)function wrapping an unpacking assignment',
                                     args=[rhs_var_arg_decl] + forwarded_vars_args,
                                     main_definition=main_definition,
                                     specializations=[specialization],
                                     result_element_names=['value', 'type', 'error'])
    writer.write(template_defn)

    function_call_expr, function_call_error_expr = _create_metafunction_call(ir0.TypeLiteral.from_nonlocal_template_defn(template_defn,
                                                                                                                         is_metafunction_that_may_return_error=True),
                                                                             args=[rhs_var] + forwarded_vars_exprs,
                                                                             member_type=writer.parent_return_type,
                                                                             writer=writer)

    writer.write_result_body_elements(result_expr=function_call_expr,
                                      error_expr=function_call_error_expr)

def stmts_to_ir0(stmts: List[ir1.Stmt],
                 write_continuation_fun_call: Optional[Callable[[TemplateBodyWriter], None]],
                 writer: Writer):
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, ir1.Assert):
            assert_to_ir0(stmt, writer)
        elif isinstance(stmt, ir1.Assignment):
            assignment_to_ir0(stmt, writer)
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

def _select_arbitrary_parent_arg(args: List[ir0.TemplateArgDecl]) -> ir0.TemplateArgDecl:
    assert args
    # Prefer a non-template arg (if any), as that will lead to simpler/smaller generated code.
    for arg in args:
        if arg.type.kind != ir0.ExprKind.TEMPLATE:
            return arg
    return args[0]

def function_defn_to_ir0(function_defn: ir1.FunctionDefn, writer: ToplevelWriter):
    try:
        args = [function_arg_decl_to_ir0(arg)
                for arg in function_defn.args]
        if args:
            parent_arbitrary_arg = _select_arbitrary_parent_arg(args)
        else:
            parent_arbitrary_arg = ir0.TemplateArgDecl(type=ir0.TypeType(),
                                                       name=writer.new_id())
            args = [parent_arbitrary_arg]

        return_type = type_to_ir0(function_defn.return_type)
        body_writer = TemplateBodyWriter(writer,
                                         parent_arbitrary_arg=parent_arbitrary_arg,
                                         parent_return_type=return_type)
        stmts_to_ir0(function_defn.body,
                     write_continuation_fun_call=None,
                     writer=body_writer)

        main_definition = _create_metafunction_specialization(args=args,
                                                              patterns=None,
                                                              body=body_writer.elems)

        if return_type.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
          result_element_names = ['value', 'error']
        else:
          result_element_names = ['type', 'error']

        writer.write(ir0.TemplateDefn(main_definition=main_definition,
                                      name=function_defn.name,
                                      description=function_defn.description,
                                      args=args,
                                      specializations=[],
                                      result_element_names=result_element_names))
    except (AssertionError, TypeError) as e:  # pragma: no cover
        print('While converting a function defn to low IR:\n' + str(ir1.Module(body=[function_defn],
                                                                               public_names=set())))
        raise e

def check_if_error_defn_to_ir0(check_if_error_defn: ir1.CheckIfErrorDefn, writer: ToplevelWriter):
    # template <typename>
    # struct CheckIfError {
    #   using type = void;
    # };
    main_definition = ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(type=ir0.TypeType(), name='')],
                                                 patterns=None,
                                                 body=[ir0.Typedef(name='type',
                                                                   expr=ir0.TypeLiteral.for_nonlocal_type('void'))])
    # template <int x, bool b, typename T>
    # struct CheckIfError<MyErrorHolder<x, b, T>> {
    #   static_assert(Select1stBoolBool<false, x>::value,
    #                 "<MyError's message>");
    # };
    specializations = [ir0.TemplateSpecialization(args=[ir0.TemplateArgDecl(type=type_to_ir0(arg_decl.type),
                                                                            name=arg_decl.name)
                                                        for arg_decl in custom_error_type.arg_types],
                                                  patterns=[ir0.TemplateArgPatternLiteral('%s<%s>' % (writer.get_holder_template_name_for_error(custom_error_type.name),
                                                                                                          ', '.join(arg.name
                                                                                                                    for arg in custom_error_type.arg_types)))],
                                                  body=[ir0.StaticAssert(expr=ir0.Literal(value=False),
                                                                         message=error_message)])
                       for custom_error_type, error_message in check_if_error_defn.error_types_and_messages]
    writer.write(ir0.TemplateDefn(name='CheckIfError',
                                  description='',
                                  main_definition=main_definition,
                                  specializations=specializations,
                                  args=main_definition.args,
                                  result_element_names=['type']))

def module_to_ir0(module: ir1.Module, identifier_generator: Iterator[str]):
    writer = ToplevelWriter(identifier_generator)
    public_names = module.public_names.copy()
    for toplevel_elem in module.body:
        if isinstance(toplevel_elem, ir1.FunctionDefn):
            function_defn_to_ir0(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir1.Assert):
            assert_to_ir0(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir1.Assignment):
            assignment_to_ir0(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir1.CustomType):
            custom_type_defn_to_ir0(toplevel_elem, writer)
        elif isinstance(toplevel_elem, ir1.CheckIfErrorDefn):
            check_if_error_defn_to_ir0(toplevel_elem, writer)
            public_names.add('CheckIfError')
        else:
            raise NotImplementedError('Unexpected toplevel element: %s' % str(toplevel_elem.__class__))

    return ir0.Header(content=writer.elems,
                      public_names=public_names)
