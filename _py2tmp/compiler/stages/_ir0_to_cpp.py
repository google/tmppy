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
import dataclasses
from dataclasses import dataclass
from typing import Iterator, Tuple, Union, Callable, Iterable, Optional

from _py2tmp.ir0 import ir0, compute_template_dependency_graph, Visitor, is_expr_variadic
from _py2tmp.utils import clang_format, compute_condensation_in_topological_order
from _py2tmp.cpp import Writer, ToplevelWriter, TemplateElemWriter, ExprWriter

@dataclass(frozen=True)
class Context:
    enclosing_function_defn_args: Tuple[ir0.TemplateArgDecl, ...]
    coverage_collection_enabled: bool
    writer: Writer

def expr_to_cpp(expr: ir0.Expr,
                context: Context) -> str:
    if isinstance(expr, ir0.Literal):
        return literal_to_cpp(expr)
    elif isinstance(expr, ir0.ComparisonExpr):
        return comparison_expr_to_cpp(expr, context)
    elif isinstance(expr, ir0.NotExpr):
        return not_expr_to_cpp(expr, context)
    elif isinstance(expr, ir0.UnaryMinusExpr):
        return unary_minus_expr_to_cpp(expr, context)
    elif isinstance(expr, ir0.Int64BinaryOpExpr):
        return int64_binary_op_expr_to_cpp(expr, context)
    elif isinstance(expr, ir0.BoolBinaryOpExpr):
        return bool_binary_op_expr_to_cpp(expr, context)
    else:
        writer = ExprWriter(context.writer)
        type_expr_to_cpp(expr, dataclasses.replace(context, writer=writer))
        return ''.join(writer.strings)

def expr_to_cpp_simple(expr: ir0.Expr):
    writer = ToplevelWriter(iter([]))
    context = Context(enclosing_function_defn_args=(), coverage_collection_enabled=False, writer=writer)
    expr_str = expr_to_cpp(expr, context)
    return ''.join(writer.strings) + expr_str

def static_assert_to_cpp(assert_stmt: ir0.StaticAssert,
                         context: Context):
    if context.enclosing_function_defn_args:
        bound_variables = {arg_decl.name
                           for arg_decl in context.enclosing_function_defn_args}
        assert bound_variables
    else:
        bound_variables = None

    cpp_meta_expr = expr_to_cpp(assert_stmt.expr, context)
    message = assert_stmt.message
    if not context.enclosing_function_defn_args or assert_stmt.expr.references_any_of(bound_variables):
        context.writer.write_template_body_elem('static_assert({cpp_meta_expr}, "{message}");'.format(**locals()))
    else:
        # The expression is constant, we need to add a reference to a variable bound in this function to prevent the
        # static_assert from being evaluated before the template is instantiated.

        # TODO: We could avoid adding a param dependency in more cases by checking for references to local variables
        # that depend (directly or indirectly) on a param.

        for arg_decl in context.enclosing_function_defn_args:
            if arg_decl.expr_type.kind == ir0.ExprKind.BOOL:
                bound_var = arg_decl.name
                context.writer.write_template_body_elem('static_assert(AlwaysTrueFromBool<{bound_var}>::value && {cpp_meta_expr}, "{message}");'.format(**locals()))
                return
            elif arg_decl.expr_type.kind == ir0.ExprKind.INT64:
                bound_var = arg_decl.name
                context.writer.write_template_body_elem('static_assert(AlwaysTrueFromInt64<{bound_var}>::value && {cpp_meta_expr}, "{message}");'.format(**locals()))
                return
            elif arg_decl.expr_type.kind == ir0.ExprKind.TYPE:
                bound_var = arg_decl.name
                context.writer.write_template_body_elem('static_assert(AlwaysTrueFromType<{bound_var}>::value && {cpp_meta_expr}, "{message}");'.format(**locals()))
                return

        # All of this function's params are functions, we can't use any of the predefined AlwaysTrue* templates.
        # We need to define a new AlwaysTrueFromType variant for this specific function type.
        always_true_id = context.writer.new_id()
        template_param_decl = _type_to_template_param_declaration(expr_type=context.enclosing_function_defn_args[0].expr_type,
                                                                  is_variadic=context.enclosing_function_defn_args[0].is_variadic)
        template_param = context.enclosing_function_defn_args[0].name
        context.writer.write_template_body_elem('''\
            // Custom AlwaysTrueFor* template
            template <{template_param_decl}>
            struct {always_true_id} {{
              static constexpr bool value = true;
            }};
            static_assert({always_true_id}<{template_param}>::value && {cpp_meta_expr}, "{message}");
            '''.format(**locals()))

def no_op_stmt_to_cpp(stmt: ir0.NoOpStmt, context: Context):
    if context.coverage_collection_enabled:
        branch = stmt.source_branch
        message = f'<fruit-coverage-internal-marker file_name=\'{branch.file_name}\' source_line=\'{branch.source_line}\' dest_line=\'{branch.dest_line}\' />'
        fun = context.writer.new_id()
        var = context.writer.new_id()
        context.writer.write_template_body_elem('[[deprecated("%s")]] constexpr int %s() { return 0; }' % (message, fun))
        context.writer.write_template_body_elem('constexpr static const int %s = %s();' % (var, fun))

def constant_def_to_cpp(constant_def: ir0.ConstantDef,
                        context: Context):
    if isinstance(constant_def.expr.expr_type, ir0.BoolType):
        type_cpp = 'bool'
    elif isinstance(constant_def.expr.expr_type, ir0.Int64Type):
        type_cpp = 'int64_t'
    else:
        raise NotImplementedError('Unexpected expression type: %s' % constant_def.expr.expr_type)

    name = constant_def.name
    cpp_meta_expr = expr_to_cpp(constant_def.expr, context)
    context.writer.write_template_body_elem('''\
        static constexpr {type_cpp} {name} = {cpp_meta_expr};
        '''.format(**locals()))

def typedef_to_cpp(typedef: ir0.Typedef,
                   context: Context):
    if typedef.expr.expr_type.kind == ir0.ExprKind.TEMPLATE:
        assert not typedef.template_args
        template_args = tuple(ir0.TemplateArgDecl(expr_type=arg.expr_type, name=context.writer.new_id(), is_variadic=arg.is_variadic)
                              for arg in typedef.expr.expr_type.args)
        typedef = ir0.Typedef(name=typedef.name,
                              expr=ir0.TemplateInstantiation(template_expr=typedef.expr,
                                                             args=tuple(ir0.AtomicTypeLiteral.for_local(expr_type=arg.expr_type,
                                                                                                        cpp_type=arg.name,
                                                                                                        is_variadic=arg.is_variadic)
                                                                        for arg in template_args),
                                                             # TODO: use static analysis to determine when it's
                                                             # safe to set this to False.
                                                             instantiation_might_trigger_static_asserts=True),
                              description=typedef.description,
                              template_args=template_args)

    assert typedef.expr.expr_type.kind == ir0.ExprKind.TYPE, typedef.expr.expr_type.kind

    name = typedef.name
    cpp_meta_expr = expr_to_cpp(typedef.expr, context)
    if typedef.description:
        description = '// ' + typedef.description + '\n'
    else:
        description = ''

    if not typedef.template_args:
        context.writer.write_template_body_elem('''\
            {description}using {name} = {cpp_meta_expr};
            '''.format(**locals()))
    else:
        template_args_decl = ', '.join(template_arg_decl_to_cpp(arg)
                                       for arg in typedef.template_args)
        context.writer.write_template_body_elem('''\
            {description}template <{template_args_decl}>
            using {name} = {cpp_meta_expr};
            '''.format(**locals()))

def _type_to_template_param_declaration(expr_type: ir0.ExprType, is_variadic: bool):
    if expr_type.kind == ir0.ExprKind.TEMPLATE:
        assert not is_variadic
        assert isinstance(expr_type, ir0.TemplateType)
        return ('template <'
                + ', '.join(_type_to_template_param_declaration(arg.expr_type, arg.is_variadic)
                            for arg in expr_type.args)
                + '> class')
    result = {
        ir0.ExprKind.BOOL: 'bool',
        ir0.ExprKind.INT64: 'int64_t',
        ir0.ExprKind.TYPE: 'typename',
    }[expr_type.kind]
    if is_variadic:
        result = result + '...'
    return result

def template_arg_decl_to_cpp(arg_decl: ir0.TemplateArgDecl):
    return _type_to_template_param_declaration(arg_decl.expr_type, is_variadic=arg_decl.is_variadic) + ' ' + arg_decl.name

def template_specialization_to_cpp(specialization: ir0.TemplateSpecialization,
                                   cxx_name: str,
                                   context: Context):
    template_elem_writer = context.writer.create_child_writer()
    template_body_context = dataclasses.replace(context, enclosing_function_defn_args=specialization.args, writer=template_elem_writer)
    for elem in specialization.body:
        if isinstance(elem, ir0.StaticAssert):
            static_assert_to_cpp(elem, template_body_context)
        elif isinstance(elem, ir0.ConstantDef):
            constant_def_to_cpp(elem, template_body_context)
        elif isinstance(elem, ir0.Typedef):
            typedef_to_cpp(elem, template_body_context)
        elif isinstance(elem, ir0.TemplateDefn):
            template_defn_to_cpp(elem, template_body_context)
        elif isinstance(elem, ir0.NoOpStmt):
            no_op_stmt_to_cpp(elem, template_body_context)
        else:
            raise NotImplementedError('Unsupported element: ' + str(elem))

    asserts_and_assignments_str = ''.join(template_elem_writer.strings)
    template_args = ', '.join(template_arg_decl_to_cpp(arg)
                              for arg in specialization.args)
    if specialization.patterns is not None:
        expr_writer = ExprWriter(context.writer)
        with expr_writer.enter_pattern_context():
            patterns_str = ', '.join(expr_to_cpp(pattern, dataclasses.replace(template_body_context, writer=expr_writer))
                                     for pattern in specialization.patterns)
        assert not expr_writer.strings
        context.writer.write_template_body_elem('''\
            template <{template_args}>
            struct {cxx_name}<{patterns_str}> {{
              {asserts_and_assignments_str}
            }};
            '''.format(**locals()))
    else:
        context.writer.write_template_body_elem('''\
            template <{template_args}>
            struct {cxx_name} {{
              {asserts_and_assignments_str}
            }};
            '''.format(**locals()))

def template_defn_to_cpp_forward_decl(template_defn: ir0.TemplateDefn,
                                      context: Context):
    template_name = template_defn.name
    template_args = ', '.join(template_arg_decl_to_cpp(arg)
                              for arg in template_defn.args)
    context.writer.write_toplevel_elem('''\
        template <{template_args}>
        struct {template_name};
        '''.format(**locals()))

def template_defn_to_cpp(template_defn: ir0.TemplateDefn,
                         context: Context):
    template_name = template_defn.name
    if template_defn.main_definition:
        if template_defn.description:
            context.writer.write_toplevel_elem('// %s\n' % template_defn.description)
        template_specialization_to_cpp(template_defn.main_definition,
                                       cxx_name=template_name,
                                       context=context)

    for specialization in template_defn.specializations:
        if template_defn.description:
            context.writer.write_toplevel_elem('// %s\n' % template_defn.description)
        template_specialization_to_cpp(specialization,
                                       cxx_name=template_name,
                                       context=context)

def template_defn_to_cpp_simple(template_defn: ir0.TemplateDefn,
                                identifier_generator: Iterator[str]):
    writer = ToplevelWriter(identifier_generator)
    context = Context(enclosing_function_defn_args=(),
                      coverage_collection_enabled=False,
                      writer=writer)
    template_defn_to_cpp(template_defn, context)
    return clang_format(''.join(writer.strings))

def toplevel_elem_to_cpp_simple(elem: Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef],
                                identifier_generator: Iterator[str]):
    writer = ToplevelWriter(identifier_generator)
    context = Context(enclosing_function_defn_args=(),
                      coverage_collection_enabled=False,
                      writer=writer)
    toplevel_elem_to_cpp(elem, context)
    return clang_format(''.join(writer.strings))

def literal_to_cpp(literal: ir0.Literal):
    if isinstance(literal.value, bool):
        return {
            True: 'true',
            False: 'false',
        }[literal.value]
    elif isinstance(literal.value, int):
        return str(literal.value) + 'LL'
    else:
        raise NotImplementedError('Unexpected literal value: %s' % repr(literal.value))

def comparison_expr_to_cpp(comparison: ir0.ComparisonExpr,
                           context: Context):
    return '(%s) %s (%s)' % (
        expr_to_cpp(comparison.lhs, context),
        comparison.op,
        expr_to_cpp(comparison.rhs, context))

def int64_binary_op_expr_to_cpp(expr: ir0.Int64BinaryOpExpr,
                                context: Context):
    return '(%s) %s (%s)' % (
        expr_to_cpp(expr.lhs, context),
        expr.op,
        expr_to_cpp(expr.rhs, context))

def bool_binary_op_expr_to_cpp(expr: ir0.BoolBinaryOpExpr,
                               context: Context):
    return '(%s) %s (%s)' % (
        expr_to_cpp(expr.lhs, context),
        expr.op,
        expr_to_cpp(expr.rhs, context))

def _select_best_arg_decl_for_select1st(args: Tuple[ir0.TemplateArgDecl, ...]):
    for arg in args:
        if not isinstance(arg.expr_type, ir0.TemplateType):
            return arg
    return args[0]

def _select_best_arg_expr_index_for_select1st(args: Tuple[ir0.Expr, ...]):
    assert args
    for i, arg in enumerate(args):
        if not isinstance(arg.expr_type, ir0.TemplateType):
            return i
    return 0

def template_instantiation_to_cpp(instantiation_expr: ir0.TemplateInstantiation,
                                  context: Context,
                                  omit_typename=False):
    args = instantiation_expr.args

    if instantiation_expr.instantiation_might_trigger_static_asserts and context.enclosing_function_defn_args and args:
        bound_variables = {arg_decl.name
                           for arg_decl in context.enclosing_function_defn_args}
        assert bound_variables

        # TODO: We could avoid adding a param dependency in more cases by checking for references to local variables
        # that depend (directly or indirectly) on a param.
        if not any(arg.references_any_of(bound_variables)
                   for arg in args):
            # All template arguments are (or might be) constants, we need to add a reference to a variable bound in this
            # function to prevent the instantiation from happening early, potentially triggering static asserts.

            arg_decl = _select_best_arg_decl_for_select1st(context.enclosing_function_defn_args)
            arg_index = _select_best_arg_expr_index_for_select1st(args)
            arg_to_replace = args[arg_index]

            is_variadic = is_expr_variadic(arg_to_replace)
            if arg_decl.expr_type.kind != ir0.ExprKind.TEMPLATE and arg_to_replace.expr_type.kind != ir0.ExprKind.TEMPLATE:
                # We use lambdas here just to make sure we collect code coverage of each "branch". They are not necessary.
                # Note that we use the *Type variants for variadic types too. That's ok, since e.g.
                # Select1stBoolType<b, Args> will be expanded as e.g. Select1stBoolType<b, Args>... so it's exactly what
                # we want in the variadic case too.
                select1st_variant = {
                    (ir0.ExprKind.BOOL, ir0.ExprKind.BOOL):  lambda: 'Select1stBoolBool',
                    (ir0.ExprKind.BOOL, ir0.ExprKind.INT64): lambda: 'Select1stBoolInt64',
                    (ir0.ExprKind.BOOL, ir0.ExprKind.TYPE):  lambda: 'Select1stBoolType',
                    (ir0.ExprKind.INT64, ir0.ExprKind.BOOL):  lambda: 'Select1stInt64Bool',
                    (ir0.ExprKind.INT64, ir0.ExprKind.INT64): lambda: 'Select1stInt64Int64',
                    (ir0.ExprKind.INT64, ir0.ExprKind.TYPE):  lambda: 'Select1stInt64Type',
                    (ir0.ExprKind.TYPE, ir0.ExprKind.BOOL):  lambda: 'Select1stTypeBool',
                    (ir0.ExprKind.TYPE, ir0.ExprKind.INT64): lambda: 'Select1stTypeInt64',
                    (ir0.ExprKind.TYPE, ir0.ExprKind.TYPE):  lambda: 'Select1stTypeType',
                }[(arg_to_replace.expr_type.kind, arg_decl.expr_type.kind)]()
            else:
                # We need to define a new Select1st variant for the desired function type.
                select1st_variant = context.writer.new_id()
                forwarded_param_id = context.writer.new_id()
                template_param_decl1 = _type_to_template_param_declaration(expr_type=arg_to_replace.expr_type, is_variadic=is_variadic)
                template_param_decl2 = _type_to_template_param_declaration(expr_type=arg_decl.expr_type, is_variadic=arg_decl.is_variadic)

                select1st_variant_body_writer = TemplateElemWriter(context.writer.toplevel_writer)
                select1st_variant_context = dataclasses.replace(context, writer=select1st_variant_body_writer)
                if arg_to_replace.expr_type.kind in (ir0.ExprKind.BOOL, ir0.ExprKind.INT64):
                    select1st_variant_body = ir0.ConstantDef(name='value',
                                                             expr=ir0.AtomicTypeLiteral.for_local(cpp_type=forwarded_param_id,
                                                                                                  expr_type=arg_to_replace.expr_type,
                                                                                                  is_variadic=is_variadic))
                    constant_def_to_cpp(select1st_variant_body, select1st_variant_context)
                else:
                    replaced_type = arg_to_replace.expr_type
                    assert replaced_type.kind in (ir0.ExprKind.TYPE, ir0.ExprKind.TEMPLATE)
                    select1st_variant_body = ir0.Typedef(name='value',
                                                         expr=ir0.AtomicTypeLiteral.for_local(cpp_type=forwarded_param_id,
                                                                                              expr_type=replaced_type,
                                                                                              is_variadic=is_variadic))
                    typedef_to_cpp(select1st_variant_body, select1st_variant_context)

                select1st_variant_body_str = ''.join(select1st_variant_body_writer.strings)

                context.writer.write_template_body_elem('''
                    // Custom Select1st* template
                    template <{template_param_decl1} {forwarded_param_id}, {template_param_decl2}>
                    struct {select1st_variant} {{
                      {select1st_variant_body_str}
                    }};
                    '''.format(**locals()))

            select1st_type = ir0.TemplateType(args=(
                ir0.TemplateArgType(expr_type=arg_to_replace.expr_type, is_variadic=is_variadic),
                ir0.TemplateArgType(expr_type=arg_decl.expr_type, is_variadic=arg_decl.is_variadic)))
            select1st_instantiation = ir0.TemplateInstantiation(template_expr=ir0.AtomicTypeLiteral.for_local(cpp_type=select1st_variant,
                                                                                                              expr_type=select1st_type,
                                                                                                              is_variadic=False),
                                                                args=(arg_to_replace,
                                                                      ir0.AtomicTypeLiteral.for_local(cpp_type=arg_decl.name,
                                                                                                      expr_type=arg_decl.expr_type,
                                                                                                      is_variadic=arg_decl.is_variadic)),
                                                                instantiation_might_trigger_static_asserts=False)
            new_arg = ir0.ClassMemberAccess(inner_expr=select1st_instantiation,
                                            member_name='value',
                                            expr_type=arg_to_replace.expr_type)

            args = args[:arg_index] + (new_arg,) + args[arg_index + 1:]

    template_params = ', '.join(expr_to_cpp(arg, context)
                                for arg in args)

    if isinstance(instantiation_expr.template_expr, ir0.ClassMemberAccess):
        cpp_fun = class_member_access_to_cpp(instantiation_expr.template_expr,
                                             context,
                                             omit_typename=omit_typename,
                                             parent_expr_is_template_instantiation=True)
    else:
        cpp_fun = expr_to_cpp(instantiation_expr.template_expr, context)

    return '{cpp_fun}<{template_params}>'.format(**locals())

def class_member_access_to_cpp(expr: ir0.ClassMemberAccess,
                               context: Context,
                               omit_typename: bool = False,
                               parent_expr_is_template_instantiation: bool = False):
    if isinstance(expr.inner_expr, ir0.TemplateInstantiation):
        cpp_fun = template_instantiation_to_cpp(expr.inner_expr, context, omit_typename=True)
    elif isinstance(expr.inner_expr, ir0.ClassMemberAccess):
        cpp_fun = class_member_access_to_cpp(expr.inner_expr, context, omit_typename=True)
    else:
        cpp_fun = expr_to_cpp(expr.inner_expr, context)
    member_name = expr.member_name
    if isinstance(expr.expr_type, (ir0.BoolType, ir0.Int64Type)):
        cpp_str_template = '{cpp_fun}::{member_name}'
    elif isinstance(expr.expr_type, (ir0.TypeType, ir0.TemplateType)):
        if omit_typename or (isinstance(expr.expr_type, ir0.TemplateType) and not parent_expr_is_template_instantiation):
            maybe_typename = ''
        else:
            maybe_typename = 'typename '
        if isinstance(expr.expr_type, ir0.TemplateType):
            maybe_template = 'template '
        else:
            maybe_template = ''

        cpp_str_template = '{maybe_typename}{cpp_fun}::{maybe_template}{member_name}'
    else:
        raise NotImplementedError('Member type: %s' % expr.expr_type.__class__.__name__)
    return cpp_str_template.format(**locals())

def variadic_type_expansion_to_cpp(expr: ir0.VariadicTypeExpansion,
                                   context: Context):
    cpp = expr_to_cpp(expr.inner_expr, context)
    if expr.expr_type.kind == ir0.ExprKind.TYPE or (isinstance(context.writer, ExprWriter) and context.writer.is_in_pattern):
        return cpp + '...'
    else:
        return '(' + cpp + ')...'

def not_expr_to_cpp(expr: ir0.NotExpr,
                    context: Context):
    inner_expr = expr_to_cpp(expr.inner_expr, context)
    return '!({inner_expr})'.format(**locals())

def toplevel_elem_to_cpp(elem: Union[ir0.StaticAssert, ir0.ConstantDef, ir0.Typedef],
                         context: Context):
    if isinstance(elem, ir0.StaticAssert):
        static_assert_to_cpp(elem, context)
    elif isinstance(elem, ir0.ConstantDef):
        constant_def_to_cpp(elem, context)
    elif isinstance(elem, ir0.Typedef):
        typedef_to_cpp(elem, context)
    elif isinstance(elem, ir0.NoOpStmt):
        no_op_stmt_to_cpp(elem, context)
    else:
        raise NotImplementedError('Unexpected toplevel element: %s' % str(elem.__class__))

def unary_minus_expr_to_cpp(expr: ir0.UnaryMinusExpr,
                            context: Context):
    inner_expr = expr_to_cpp(expr.inner_expr, context)
    return '-({inner_expr})'.format(**locals())

class ComputeTemplateDefnsThatMustComeBeforeVisitor(Visitor):
    def __init__(self):
        self.results = set()
        self.constant_var_names = set()
        self.is_current_expr_constant = True
        self.encountered_template_refs_must_come_before_transformation = False

    def visit_template_body_elem(self, elem: ir0.TemplateBodyElement):
        self.is_current_expr_constant = True
        super().visit_template_body_elem(elem)

    def visit_typedef(self, typedef: ir0.Typedef):
        super().visit_typedef(typedef)
        if self.is_current_expr_constant:
            self.constant_var_names.add(typedef.name)

    def visit_constant_def(self, constant_def: ir0.ConstantDef):
        super().visit_constant_def(constant_def)
        if self.is_current_expr_constant:
            self.constant_var_names.add(constant_def.name)

    def visit_exprs(self, exprs: Tuple[ir0.Expr, ...]):
        initial_is_current_expr_constant = self.is_current_expr_constant
        final_is_current_expr_constant = self.is_current_expr_constant
        for expr in exprs:
            self.is_current_expr_constant = initial_is_current_expr_constant
            self.visit_expr(expr)
            final_is_current_expr_constant &= self.is_current_expr_constant

        self.is_current_expr_constant = final_is_current_expr_constant

    def visit_type_literal(self, type_literal: ir0.AtomicTypeLiteral):
        if type_literal.is_local:
            if type_literal.cpp_type not in self.constant_var_names:
                self.is_current_expr_constant = False
        else:
            if isinstance(type_literal.expr_type, ir0.TemplateType) and self.encountered_template_refs_must_come_before_transformation:
                self.results.add(type_literal.cpp_type)

    def visit_template_instantiation(self, template_instantiation: ir0.TemplateInstantiation):
        initial_is_current_expr_constant = self.is_current_expr_constant
        initial_encountered_template_refs_must_come_before_transformation = self.encountered_template_refs_must_come_before_transformation

        self.visit_exprs(template_instantiation.args)
        final_is_current_expr_constant = self.is_current_expr_constant
        if final_is_current_expr_constant:
            self.encountered_template_refs_must_come_before_transformation = True

        self.is_current_expr_constant = initial_is_current_expr_constant
        self.visit_expr(template_instantiation.template_expr)
        final_is_current_expr_constant &= self.is_current_expr_constant

        self.is_current_expr_constant = final_is_current_expr_constant
        self.encountered_template_refs_must_come_before_transformation = initial_encountered_template_refs_must_come_before_transformation

    def visit_class_member_access(self, class_member_access: ir0.ClassMemberAccess):
        initial_encountered_template_refs_must_come_before_transformation = self.encountered_template_refs_must_come_before_transformation
        self.encountered_template_refs_must_come_before_transformation = False
        self.visit_expr(class_member_access.inner_expr)
        self.encountered_template_refs_must_come_before_transformation = initial_encountered_template_refs_must_come_before_transformation

def compute_template_defns_that_must_come_before_specialization(specialization: ir0.TemplateSpecialization):
    visitor = ComputeTemplateDefnsThatMustComeBeforeVisitor()
    visitor.visit_template_body_elems(specialization.body)
    return visitor.results

def compute_template_defns_that_must_come_before(template_defn: ir0.TemplateDefn):
    specializations = list(template_defn.specializations)
    if template_defn.main_definition:
        specializations.append(template_defn.main_definition)
    return {template_name
            for specialization in specializations
            for template_name in compute_template_defns_that_must_come_before_specialization(specialization)}

def template_defns_to_cpp(template_defns: Iterable[ir0.TemplateDefn],
                          context: Context):
    template_defn_by_template_name = {elem.name: elem
                                      for elem in template_defns}

    template_dependency_graph = compute_template_dependency_graph(template_defns, template_defn_by_template_name)
    if template_dependency_graph.number_of_nodes():
        template_dependency_graph_condensed = compute_condensation_in_topological_order(template_dependency_graph)
    else:
        template_dependency_graph_condensed = []

    for connected_component_names in reversed(list(template_dependency_graph_condensed)):
        connected_component = sorted([template_defn_by_template_name[template_name]
                                      for template_name in connected_component_names],
                                     key=lambda template_defn: template_defn.name)

        if len(connected_component) > 1:
            # There's a dependency loop with >1 templates, we first need to emit all forward decls.
            for template_defn in connected_component:
                template_defn_to_cpp_forward_decl(template_defn, context)
        else:
            [template_defn] = connected_component
            if not template_defn.main_definition:
                # There's no loop here, but this template has only specializations and no main definition, so we need the
                # forward declaration anyway.
                template_defn_to_cpp_forward_decl(template_defn, context)

        template_defns_that_must_be_last = set()
        for template_defn in connected_component:
            template_order_dependencies = compute_template_defns_that_must_come_before(template_defn)
            if any(template_name in connected_component_names
                   for template_name in template_order_dependencies):
                # This doesn't only need to be before the ones it immediately references, it really needs to be last
                # since these templates instantiate each other in a cycle.
                template_defns_that_must_be_last.add(template_defn.name)

        assert len(template_defns_that_must_be_last) <= 1, 'Found multiple template defns that must appear before each other: ' + ', '.join(template_defns_that_must_be_last)

        for template_defn in connected_component:
            if template_defn.name not in template_defns_that_must_be_last:
                template_defn_to_cpp(template_defn, context)

        for template_defn in connected_component:
            if template_defn.name in template_defns_that_must_be_last:
                specializations = list(template_defn.specializations or tuple())
                if template_defn.main_definition:
                    specializations.append(template_defn.main_definition)

                last_specialization: Optional[ir0.TemplateSpecialization] = None
                for specialization in specializations:
                    if any(template_name in connected_component_names
                           for template_name in compute_template_defns_that_must_come_before_specialization(specialization)):
                        assert last_specialization is None, 'Found multiple specializations of ' + template_defn.name + ' that must appear before each other: ' + ', '.join(template_defns_that_must_be_last)
                        last_specialization = specialization
                    else:
                        if template_defn.description:
                            context.writer.write_toplevel_elem('// %s\n' % template_defn.description)
                        template_specialization_to_cpp(specialization,
                                                       cxx_name=template_defn.name,
                                                       context=context)

                if last_specialization:
                    if template_defn.description:
                        context.writer.write_toplevel_elem('// %s\n' % template_defn.description)
                    template_specialization_to_cpp(last_specialization,
                                                   cxx_name=template_defn.name,
                                                   context=context)

def header_to_cpp(header: ir0.Header, identifier_generator: Iterator[str], coverage_collection_enabled: bool):
    writer = ToplevelWriter(identifier_generator)
    writer.write_toplevel_elem('''\
        #include <tmppy/tmppy.h>
        #include <tuple>
        #include <type_traits>
        ''')
    context = Context(enclosing_function_defn_args=(),
                      coverage_collection_enabled=coverage_collection_enabled,
                      writer=writer)

    template_defns_to_cpp(header.template_defns, context)

    for elem in header.toplevel_content:
        toplevel_elem_to_cpp(elem, context)
    return clang_format(''.join(writer.strings))

def type_expr_to_cpp(expr: ir0.Expr,
                     context: Context):
    write_prefix, write_suffix = type_expr_to_cpp_prefix_suffix(expr, context, has_modifiers=False)
    write_prefix()
    write_suffix()

def type_expr_to_cpp_simple(expr: ir0.Expr):
    writer = ExprWriter(ToplevelWriter(identifier_generator=iter([])))
    context = Context(enclosing_function_defn_args=(), writer=writer, coverage_collection_enabled=False)
    type_expr_to_cpp(expr, context)
    return ''.join(writer.strings)

# We can't generate code like "int & &&", so we need to collapse reference types ourselves. The C++ _compiler has similar
# collapsing logic, but it's only applied to cases where a ref/rref is hidden inside a typedef and one isn't.
def _simplify_toplevel_references(expr: Union[ir0.RvalueReferenceTypeExpr, ir0.ReferenceTypeExpr]):
    has_reference = False
    while isinstance(expr, (ir0.RvalueReferenceTypeExpr, ir0.ReferenceTypeExpr)):
        has_reference |= isinstance(expr, ir0.ReferenceTypeExpr)
        expr = expr.type_expr
    if has_reference:
        return ir0.ReferenceTypeExpr(expr)
    else:
        return ir0.RvalueReferenceTypeExpr(expr)

def type_expr_to_cpp_prefix_suffix(expr: ir0.Expr,
                                   context: Context,
                                   has_modifiers: bool) -> Tuple[Callable[[], None], Callable[[], None]]:
    if isinstance(expr, (ir0.RvalueReferenceTypeExpr, ir0.ReferenceTypeExpr)):
        expr = _simplify_toplevel_references(expr)

    if isinstance(expr, ir0.FunctionTypeExpr):
        return function_type_expr_to_cpp_prefix_suffix(expr, context, has_modifiers)
    elif isinstance(expr, ir0.PointerTypeExpr):
        return unary_modifier_type_expr_to_cpp_prefix_suffix('*', expr.type_expr, context)
    elif isinstance(expr, ir0.ReferenceTypeExpr):
        return unary_modifier_type_expr_to_cpp_prefix_suffix(' &',  expr.type_expr, context)
    elif isinstance(expr, ir0.RvalueReferenceTypeExpr):
        return unary_modifier_type_expr_to_cpp_prefix_suffix(' &&', expr.type_expr, context)
    elif isinstance(expr, ir0.ConstTypeExpr):
        return unary_modifier_type_expr_to_cpp_prefix_suffix(' const ', expr.type_expr, context)
    elif isinstance(expr, ir0.ArrayTypeExpr):
        return unary_modifier_type_expr_to_cpp_prefix_suffix('[]', expr.type_expr, context)

    if isinstance(expr, ir0.AtomicTypeLiteral):
        expr_cpp_code = atomic_type_literal_expr_to_cpp(expr)
    elif isinstance(expr, ir0.TemplateInstantiation):
        expr_cpp_code = template_instantiation_to_cpp(expr, context)
    elif isinstance(expr, ir0.ClassMemberAccess):
        expr_cpp_code = class_member_access_to_cpp(expr, context)
    elif isinstance(expr, ir0.VariadicTypeExpansion):
        expr_cpp_code = variadic_type_expansion_to_cpp(expr, context)
    else:
        raise NotImplementedError('Unexpected type expr: %s' % str(expr.__class__))

    def write_prefix():
        assert isinstance(context.writer, ExprWriter)
        context.writer.write_expr_fragment(expr_cpp_code)
    def write_suffix():
        pass
    return write_prefix, write_suffix

def function_type_expr_to_cpp_prefix_suffix(expr: ir0.FunctionTypeExpr,
                                            context: Context,
                                            has_modifiers: bool):
    # X1 -> Y                          |  Y(*) (X1)
    # X2 -> (X1 -> Y)                  |  Y(*(*) (X2)) (X1)
    # X3 -> (X2 -> (X1 -> Y))          |  Y(*(*(*) (X3)) (X2)) (X1)
    # X4 -> (X3 -> (X2 -> (X1 -> Y)))  |  Y(*(*(*(*) (X4)) (X3)) (X2)) (X1)
    #
    # Y -> X1                          |  X1(*) (Y)
    # (Y -> X1) -> X2                  |  X2(*) (X1(*) (Y))
    # ((Y -> X1) -> X2) -> X3          |  X3(*) (X2(*) (X1(*) (Y)))
    # (((Y -> X1) -> X2) -> X3) -> X4  |  X4(*) (X3(*) (X2(*) (X1(*) (Y))))

    return_type_write_prefix, return_type_write_suffix = type_expr_to_cpp_prefix_suffix(expr.return_type_expr, context, has_modifiers=False)

    def write_prefix():
        return_type_write_prefix()
        if has_modifiers:
            assert isinstance(context.writer, ExprWriter)
            context.writer.write_expr_fragment('(')

    def write_suffix():
        assert isinstance(context.writer, ExprWriter)
        if has_modifiers:
            context.writer.write_expr_fragment(')')
        context.writer.write_expr_fragment(' (')
        for i, arg in enumerate(expr.arg_exprs):
            if i != 0:
                context.writer.write_expr_fragment(', ')
            type_expr_to_cpp(arg, context)
        context.writer.write_expr_fragment(')')
        return_type_write_suffix()

    return write_prefix, write_suffix

def unary_modifier_type_expr_to_cpp_prefix_suffix(modifier_str: str,
                                                  sub_expr: ir0.Expr,
                                                  context: Context):
    write_subexpr_prefix, write_subexpr_suffix = type_expr_to_cpp_prefix_suffix(sub_expr, context, has_modifiers=True)
    def write_prefix():
        write_subexpr_prefix()
        assert isinstance(context.writer, ExprWriter)
        context.writer.write_expr_fragment(modifier_str)
    return write_prefix, write_subexpr_suffix

def atomic_type_literal_expr_to_cpp(expr: ir0.AtomicTypeLiteral):
    return expr.cpp_type
