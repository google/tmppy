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

from typing import List, Iterator, Tuple, Union
import _py2tmp.lowir as lowir

class Writer:
    def new_id(self) -> str: ... # pragma: no cover

    def write_toplevel_elem(self, s: str): ... # pragma: no cover

    def write_template_body_elem(self, s: str): ... # pragma: no cover

    def create_child_writer(self) -> 'TemplateElemWriter': ...  # pragma: no cover

class ToplevelWriter(Writer):
    def __init__(self, identifier_generator: Iterator[str]):
        self.identifier_generator = identifier_generator
        self.strings = []

    def new_id(self):
        return next(self.identifier_generator)

    def write_toplevel_elem(self, s: str):
        self.strings.append(s)

    def write_template_body_elem(self, s: str):
        self.write_toplevel_elem(s)

    def create_child_writer(self):
        return TemplateElemWriter(self)

class TemplateElemWriter(Writer):
    def __init__(self, toplevel_writer: ToplevelWriter):
        self.toplevel_writer = toplevel_writer
        self.strings = []

    def new_id(self):
        return self.toplevel_writer.new_id()

    def write_toplevel_elem(self, s: str):
        self.toplevel_writer.write_toplevel_elem(s)

    def write_template_body_elem(self, s: str):
        self.strings.append(s)

    def create_child_writer(self):
        return TemplateElemWriter(self.toplevel_writer)

def expr_to_cpp(expr: lowir.Expr,
                enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                writer: Writer) -> str:
    if isinstance(expr, lowir.Literal):
        return literal_to_cpp(expr)
    elif isinstance(expr, lowir.TypeLiteral):
        return type_literal_to_cpp(expr)
    elif isinstance(expr, lowir.ComparisonExpr):
        return comparison_expr_to_cpp(expr, enclosing_function_defn_args, writer)
    elif isinstance(expr, lowir.TemplateInstantiation):
        return template_instantiation_to_cpp(expr, enclosing_function_defn_args, writer)
    elif isinstance(expr, lowir.ClassMemberAccess):
        return class_member_access_to_cpp(expr, enclosing_function_defn_args, writer)
    elif isinstance(expr, lowir.NotExpr):
        return not_expr_to_cpp(expr, enclosing_function_defn_args, writer)
    elif isinstance(expr, lowir.UnaryMinusExpr):
        return unary_minus_expr_to_cpp(expr, enclosing_function_defn_args, writer)
    elif isinstance(expr, lowir.Int64BinaryOpExpr):
        return int64_binary_op_expr_to_cpp(expr, enclosing_function_defn_args, writer)
    else:
        raise NotImplementedError('Unexpected expr: %s' % str(expr.__class__))

def static_assert_to_cpp(assert_stmt: lowir.StaticAssert,
                         enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                         writer: Writer):
    if enclosing_function_defn_args:
        bound_variables = {arg_decl.name
                           for arg_decl in enclosing_function_defn_args}
        assert bound_variables

    cpp_meta_expr = expr_to_cpp(assert_stmt.expr, enclosing_function_defn_args, writer)
    message = assert_stmt.message
    if not enclosing_function_defn_args or assert_stmt.expr.references_any_of(bound_variables):
        writer.write_template_body_elem('static_assert({cpp_meta_expr}, "{message}");'.format(**locals()))
    else:
        # The expression is constant, we need to add a reference to a variable bound in this function to prevent the
        # static_assert from being evaluated before the template is instantiated.

        # TODO: We could avoid adding a param dependency in more cases by checking for references to local variables
        # that depend (directly or indirectly) on a param.

        for arg_decl in enclosing_function_defn_args:
            if arg_decl.type.kind == lowir.ExprKind.BOOL:
                bound_var = arg_decl.name
                writer.write_template_body_elem('static_assert(AlwaysTrueFromBool<{bound_var}>::value && {cpp_meta_expr}, "{message}");'.format(**locals()))
                return
            elif arg_decl.type.kind == lowir.ExprKind.INT64:
                bound_var = arg_decl.name
                writer.write_template_body_elem('static_assert(AlwaysTrueFromInt64<{bound_var}>::value && {cpp_meta_expr}, "{message}");'.format(**locals()))
                return
            elif arg_decl.type.kind == lowir.ExprKind.TYPE:
                bound_var = arg_decl.name
                writer.write_template_body_elem('static_assert(AlwaysTrueFromType<{bound_var}>::value && {cpp_meta_expr}, "{message}");'.format(**locals()))
                return

        # All of this function's params are functions, we can't use any of the predefined AlwaysTrue* templates.
        # We need to define a new AlwaysTrueFromType variant for this specific function type.
        always_true_id = writer.new_id()
        template_param_decl = _type_to_template_param_declaration(type=enclosing_function_defn_args[0].type)
        template_param = enclosing_function_defn_args[0].name
        writer.write_template_body_elem('''\
            template <{template_param_decl}>
            struct {always_true_id} {{
              static constexpr bool value = true;
            }};
            static_assert({always_true_id}<{template_param}>::value && {cpp_meta_expr}, "{message}");
            '''.format(**locals()))

def constant_def_to_cpp(constant_def: lowir.ConstantDef,
                        enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                        writer: Writer):
    if isinstance(constant_def.type, lowir.BoolType):
        type_cpp = 'bool'
    elif isinstance(constant_def.type, lowir.Int64Type):
        type_cpp = 'int64_t'
    else:
        raise NotImplementedError('Unexpected expression type: %s' % constant_def.type)

    name = constant_def.name
    cpp_meta_expr = expr_to_cpp(constant_def.expr, enclosing_function_defn_args, writer)
    writer.write_template_body_elem('''\
        static constexpr {type_cpp} {name} = {cpp_meta_expr};
        '''.format(**locals()))

def typedef_to_cpp(typedef: lowir.Typedef,
                   enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                   writer: Writer):
    name = typedef.name
    if typedef.type.kind == lowir.ExprKind.TYPE:
        cpp_meta_expr = expr_to_cpp(typedef.expr, enclosing_function_defn_args, writer)
        writer.write_template_body_elem('''\
            using {name} = {cpp_meta_expr};
            '''.format(**locals()))
    elif typedef.type.kind == lowir.ExprKind.TEMPLATE:
        assert isinstance(typedef.type, lowir.TemplateType)

        template_args = [lowir.TemplateArgDecl(type=arg_type, name=writer.new_id())
                         for arg_type in typedef.type.argtypes]
        template_args_decl = ', '.join(template_arg_decl_to_cpp(arg)
                                       for arg in template_args)

        template_instantiation_expr = lowir.TemplateInstantiation(template_expr=typedef.expr,
                                                                  args=[lowir.TypeLiteral.for_local(type=arg.type,
                                                                                                    cpp_type=arg.name)
                                                                        for arg in template_args],
                                                                  arg_types=[arg.type
                                                                             for arg in template_args],
                                                                  # TODO: use static analysis to determine when it's
                                                                  # safe to set this to False.
                                                                  instantiation_might_trigger_static_asserts=True)

        cpp_meta_expr = template_instantiation_to_cpp(template_instantiation_expr, enclosing_function_defn_args, writer)

        writer.write_template_body_elem('''\
            template <{template_args_decl}>
            using {name} = {cpp_meta_expr};
            '''.format(**locals()))
    else:
        raise NotImplementedError('Unexpected expression type kind: %s' % typedef.type.kind)

def _type_to_template_param_declaration(type: lowir.ExprType):
    if type.kind == lowir.ExprKind.BOOL:
        return 'bool'
    elif type.kind == lowir.ExprKind.INT64:
        return 'int64_t'
    elif type.kind == lowir.ExprKind.TYPE:
        return 'typename'
    elif type.kind == lowir.ExprKind.TEMPLATE:
        assert isinstance(type, lowir.TemplateType)
        return ('template <'
                + ', '.join(_type_to_template_param_declaration(arg_type)
                            for arg_type in type.argtypes)
                + '> class')
    else:
        raise NotImplementedError('Unsupported argument kind: ' + str(type.kind))

def template_arg_decl_to_cpp(arg_decl: lowir.TemplateArgDecl):
    return _type_to_template_param_declaration(arg_decl.type) + ' ' + arg_decl.name

def template_specialization_to_cpp(specialization: lowir.TemplateSpecialization,
                                   cxx_name: str,
                                   enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                                   writer: Writer):
    template_elem_writer = writer.create_child_writer()
    for elem in specialization.body:
        if isinstance(elem, lowir.StaticAssert):
            static_assert_to_cpp(elem,
                                 enclosing_function_defn_args=specialization.args,
                                 writer=template_elem_writer)
        elif isinstance(elem, lowir.ConstantDef):
            constant_def_to_cpp(elem,
                                enclosing_function_defn_args=specialization.args,
                                writer=template_elem_writer)
        elif isinstance(elem, lowir.Typedef):
            typedef_to_cpp(elem,
                           enclosing_function_defn_args=specialization.args,
                           writer=template_elem_writer)
        elif isinstance(elem, lowir.TemplateDefn):
            template_defn_to_cpp(elem,
                                 enclosing_function_defn_args=specialization.args,
                                 writer=template_elem_writer)
        else:
            raise NotImplementedError('Unsupported element: ' + str(elem))

    asserts_and_assignments_str = ''.join(template_elem_writer.strings)
    template_args = ', '.join(template_arg_decl_to_cpp(arg)
                              for arg in specialization.args)
    if specialization.patterns is not None:
        patterns_str = ', '.join(type_pattern_literal_to_cpp(pattern)
                                 for pattern in specialization.patterns)
        writer.write_template_body_elem('''\
            template <{template_args}>
            struct {cxx_name}<{patterns_str}> {{
              {asserts_and_assignments_str}
            }};
            '''.format(**locals()))
    else:
        writer.write_template_body_elem('''\
            template <{template_args}>
            struct {cxx_name} {{
              {asserts_and_assignments_str}
            }};
            '''.format(**locals()))

def template_defn_to_cpp_forward_decl(template_defn: lowir.TemplateDefn,
                                      enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                                      writer: Writer):
    template_name = template_defn.name
    template_args = ', '.join(template_arg_decl_to_cpp(arg)
                              for arg in template_defn.args)
    writer.write_toplevel_elem('''\
        template <{template_args}>
        struct {template_name};
        '''.format(**locals()))

def template_defn_to_cpp(template_defn: lowir.TemplateDefn,
                         enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                         writer: Writer):
    template_name = template_defn.name
    if template_defn.main_definition:
        template_specialization_to_cpp(template_defn.main_definition,
                                       cxx_name=template_name,
                                       enclosing_function_defn_args=enclosing_function_defn_args,
                                       writer=writer)

    for specialization in template_defn.specializations:
        template_specialization_to_cpp(specialization,
                                       cxx_name=template_name,
                                       enclosing_function_defn_args=enclosing_function_defn_args,
                                       writer=writer)

def literal_to_cpp(literal: lowir.Literal):
    if isinstance(literal.value, bool):
        return {
            True: 'true',
            False: 'false',
        }[literal.value]
    elif isinstance(literal.value, int):
        return str(literal.value) + 'LL'
    else:
        raise NotImplementedError('Unexpected literal value: %s' % repr(literal.value))

def type_literal_to_cpp(literal: lowir.TypeLiteral):
    return literal.cpp_type

def type_pattern_literal_to_cpp(pattern: lowir.TemplateArgPatternLiteral):
    return pattern.cxx_pattern

def comparison_expr_to_cpp(comparison: lowir.ComparisonExpr,
                           enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                           writer: Writer):
    return '(%s) %s (%s)' % (
        expr_to_cpp(comparison.lhs, enclosing_function_defn_args, writer),
        comparison.op,
        expr_to_cpp(comparison.rhs, enclosing_function_defn_args, writer))

def int64_binary_op_expr_to_cpp(expr: lowir.Int64BinaryOpExpr,
                                enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                                writer: Writer):
    return '(%s) %s (%s)' % (
        expr_to_cpp(expr.lhs, enclosing_function_defn_args, writer),
        expr.op,
        expr_to_cpp(expr.rhs, enclosing_function_defn_args, writer))

def _select_best_arg_decl_for_select1st(args: List[lowir.TemplateArgDecl]):
    for arg in args:
        if arg.type.kind != lowir.ExprKind.TEMPLATE:
            return arg
    return args[0]

def _select_best_arg_expr_index_for_select1st(args: List[lowir.Expr]):
    assert args
    for i, arg in enumerate(args):
        if arg.kind != lowir.ExprKind.TEMPLATE:
            return i
    return 0

def template_instantiation_to_cpp(instantiation_expr: lowir.TemplateInstantiation,
                                  enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                                  writer: Writer,
                                  omit_typename=False):
    args = instantiation_expr.args

    if instantiation_expr.instantiation_might_trigger_static_asserts and enclosing_function_defn_args:
        bound_variables = {arg_decl.name
                           for arg_decl in enclosing_function_defn_args}
        assert bound_variables

        # TODO: We could avoid adding a param dependency in more cases by checking for references to local variables
        # that depend (directly or indirectly) on a param.
        if not any(arg.references_any_of(bound_variables)
                   for arg in args):
            # All template arguments are (or might be) constants, we need to add a reference to a variable bound in this
            # function to prevent the instantiation from happening early, potentially triggering static asserts.

            arg_decl = _select_best_arg_decl_for_select1st(enclosing_function_defn_args)
            arg_index = _select_best_arg_expr_index_for_select1st(args)
            arg_to_replace = args[arg_index]
            arg_to_replace_type = instantiation_expr.arg_types[arg_index]
            assert arg_to_replace.kind == arg_to_replace_type.kind

            if arg_decl.type.kind != lowir.ExprKind.TEMPLATE and arg_to_replace.kind != lowir.ExprKind.TEMPLATE:
                # We use lambdas here just to make sure we collect code coverage of each "branch". They are not necessary.
                select1st_variant = {
                    (lowir.ExprKind.BOOL,  lowir.ExprKind.BOOL):  lambda: 'Select1stBoolBool',
                    (lowir.ExprKind.BOOL,  lowir.ExprKind.INT64): lambda: 'Select1stBoolInt64',
                    (lowir.ExprKind.BOOL,  lowir.ExprKind.TYPE):  lambda: 'Select1stBoolType',
                    (lowir.ExprKind.INT64, lowir.ExprKind.BOOL):  lambda: 'Select1stInt64Bool',
                    (lowir.ExprKind.INT64, lowir.ExprKind.INT64): lambda: 'Select1stInt64Int64',
                    (lowir.ExprKind.INT64, lowir.ExprKind.TYPE):  lambda: 'Select1stInt64Type',
                    (lowir.ExprKind.TYPE,  lowir.ExprKind.BOOL):  lambda: 'Select1stTypeBool',
                    (lowir.ExprKind.TYPE,  lowir.ExprKind.INT64): lambda: 'Select1stTypeInt64',
                    (lowir.ExprKind.TYPE,  lowir.ExprKind.TYPE):  lambda: 'Select1stTypeType',
                }[(arg_to_replace.kind, arg_decl.type.kind)]()
            else:
                # We need to define a new Select1st variant for the desired function type.
                select1st_variant = writer.new_id()
                forwarded_param_id = writer.new_id()
                template_param_decl1 = _type_to_template_param_declaration(type=arg_to_replace_type)
                template_param_decl2 = _type_to_template_param_declaration(type=arg_decl.type)

                if isinstance(writer, ToplevelWriter):
                    select1st_variant_body_writer = TemplateElemWriter(writer)
                else:
                    assert isinstance(writer, TemplateElemWriter)
                    select1st_variant_body_writer = TemplateElemWriter(writer.toplevel_writer)
                if arg_to_replace.kind in (lowir.ExprKind.BOOL, lowir.ExprKind.INT64):
                    select1st_variant_body = lowir.ConstantDef(name='value',
                                                               expr=lowir.TypeLiteral.for_local(cpp_type=forwarded_param_id,
                                                                                                type=arg_to_replace_type),
                                                               type=arg_to_replace_type)
                    constant_def_to_cpp(select1st_variant_body, enclosing_function_defn_args, select1st_variant_body_writer)
                else:
                    assert arg_to_replace.kind in (lowir.ExprKind.TYPE, lowir.ExprKind.TEMPLATE)
                    select1st_variant_body = lowir.Typedef(name='value',
                                                           expr=lowir.TypeLiteral.for_local(cpp_type=forwarded_param_id,
                                                                                            type=arg_to_replace_type),
                                                           type=arg_to_replace_type)
                    typedef_to_cpp(select1st_variant_body, enclosing_function_defn_args, select1st_variant_body_writer)

                select1st_variant_body_str = ''.join(select1st_variant_body_writer.strings)

                writer.write_template_body_elem('''
                    template <{template_param_decl1} {forwarded_param_id}, {template_param_decl2}>
                    struct {select1st_variant} {{
                      {select1st_variant_body_str}
                    }};
                    '''.format(**locals()))

            select1st_type = lowir.TemplateType(argtypes=[arg_to_replace_type, arg_decl.type])
            select1st_instantiation = lowir.TemplateInstantiation(template_expr=lowir.TypeLiteral.for_local(cpp_type=select1st_variant,
                                                                                                            type=select1st_type),
                                                                  args=[arg_to_replace,
                                                                        lowir.TypeLiteral.for_local(cpp_type=arg_decl.name,
                                                                                                    type=arg_decl.type)],
                                                                  arg_types=[],
                                                                  instantiation_might_trigger_static_asserts=False)
            new_arg = lowir.ClassMemberAccess(class_type_expr=select1st_instantiation,
                                              member_name='value',
                                              member_kind=arg_to_replace.kind)

            args = args[:arg_index] + [new_arg] + args[arg_index + 1:]

    template_params = ', '.join(expr_to_cpp(arg, enclosing_function_defn_args, writer)
                                for arg in args)

    if isinstance(instantiation_expr.template_expr, lowir.ClassMemberAccess):
        cpp_fun = class_member_access_to_cpp(instantiation_expr.template_expr,
                                             enclosing_function_defn_args,
                                             writer,
                                             omit_typename=omit_typename,
                                             parent_expr_is_template_instantiation=True)
    else:
        cpp_fun = expr_to_cpp(instantiation_expr.template_expr, enclosing_function_defn_args, writer)

    return '{cpp_fun}<{template_params}>'.format(**locals())

def class_member_access_to_cpp(expr: lowir.ClassMemberAccess,
                               enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                               writer: Writer,
                               omit_typename: bool = False,
                               parent_expr_is_template_instantiation: bool = False):
    if isinstance(expr.class_type_expr, lowir.TemplateInstantiation):
        cpp_fun = template_instantiation_to_cpp(expr.class_type_expr, enclosing_function_defn_args, writer, omit_typename=True)
    elif isinstance(expr.class_type_expr, lowir.ClassMemberAccess):
        cpp_fun = class_member_access_to_cpp(expr.class_type_expr, enclosing_function_defn_args, writer, omit_typename=True)
    else:
        cpp_fun = expr_to_cpp(expr.class_type_expr, enclosing_function_defn_args, writer)
    member_name = expr.member_name
    if expr.member_kind in (lowir.ExprKind.BOOL, lowir.ExprKind.INT64):
        cpp_str_template = '{cpp_fun}::{member_name}'
    elif expr.member_kind in (lowir.ExprKind.TYPE, lowir.ExprKind.TEMPLATE):
        if omit_typename or (expr.member_kind == lowir.ExprKind.TEMPLATE and not parent_expr_is_template_instantiation):
            maybe_typename = ''
        else:
            maybe_typename = 'typename '
        if expr.member_kind == lowir.ExprKind.TEMPLATE:
            maybe_template = 'template '
        else:
            maybe_template = ''

        cpp_str_template = '{maybe_typename}{cpp_fun}::{maybe_template}{member_name}'
    else:
        raise NotImplementedError('Member kind: %s' % expr.member_kind)
    return cpp_str_template.format(**locals())

def not_expr_to_cpp(expr: lowir.NotExpr,
                    enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                    writer: Writer):
    inner_expr = expr_to_cpp(expr.expr, enclosing_function_defn_args, writer)
    return '!({inner_expr})'.format(**locals())

def unary_minus_expr_to_cpp(expr: lowir.UnaryMinusExpr,
                            enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                            writer: Writer):
    inner_expr = expr_to_cpp(expr.expr, enclosing_function_defn_args, writer)
    return '-({inner_expr})'.format(**locals())

def header_to_cpp(header: lowir.Header, identifier_generator: Iterator[str]):
    writer = ToplevelWriter(identifier_generator)
    writer.write_toplevel_elem('''\
        #include <tmppy/tmppy.h>
        #include <type_traits>
        ''')
    for elem in header.content:
        # TODO: only do this when needed, many of these forward declarations are unnecessary.
        if isinstance(elem, lowir.TemplateDefn):
            template_defn_to_cpp_forward_decl(elem,
                                              enclosing_function_defn_args=[],
                                              writer=writer)
    for elem in header.content:
        if isinstance(elem, lowir.TemplateDefn):
            template_defn_to_cpp(elem,
                                 enclosing_function_defn_args=[],
                                 writer=writer)
        elif isinstance(elem, lowir.StaticAssert):
            static_assert_to_cpp(elem,
                                 enclosing_function_defn_args=[],
                                 writer=writer)
        elif isinstance(elem, lowir.ConstantDef):
            constant_def_to_cpp(elem,
                                enclosing_function_defn_args=[],
                                writer=writer)
        elif isinstance(elem, lowir.Typedef):
            typedef_to_cpp(elem,
                           enclosing_function_defn_args=[],
                           writer=writer)
        else:
            raise NotImplementedError('Unexpected toplevel element: %s' % str(elem.__class__))
    return ''.join(writer.strings)
