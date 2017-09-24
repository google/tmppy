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

from typing import List, Iterator, Union
import _py2tmp.lowir as lowir

def expr_to_cpp(expr: lowir.Expr) -> str:
    if isinstance(expr, lowir.Literal):
        return literal_to_cpp(expr)
    elif isinstance(expr, lowir.TypeLiteral):
        return type_literal_to_cpp(expr)
    elif isinstance(expr, lowir.EqualityComparison):
        return equality_comparison_to_cpp(expr)
    elif isinstance(expr, lowir.TemplateInstantiation):
        return template_instantiation_to_cpp(expr)
    elif isinstance(expr, lowir.ClassMemberAccess):
        return class_member_access_to_cpp(expr)
    else:
        raise NotImplementedError('Unexpected expr: %s' % expr.__class__)

def static_assert_to_cpp(assert_stmt: lowir.StaticAssert,
                         enclosing_function_defn_args: List[lowir.TemplateArgDecl],
                         cxx_identifier_generator: Iterator[str]):
    if enclosing_function_defn_args:
        bound_variables = {arg_decl.name
                           for arg_decl in enclosing_function_defn_args}
        assert bound_variables

    cpp_meta_expr = expr_to_cpp(assert_stmt.expr)
    message = assert_stmt.message
    if not enclosing_function_defn_args or assert_stmt.expr.references_any_of(bound_variables):
        return 'static_assert({cpp_meta_expr}, "{message}");'.format(**locals())
    else:
        # The expression is constant, we need to add a reference to a variable bound in this function to prevent the
        # static_assert from being evaluated before the template is instantiated.

        # TODO: We could avoid adding a param dependency in more cases by checking for references to local variables
        # that depend (directly or indirectly) on a param.

        for arg_decl in enclosing_function_defn_args:
            if arg_decl.type.kind == lowir.ExprKind.BOOL:
                bound_var = arg_decl.name
                return 'static_assert(AlwaysTrueFromBool<{bound_var}>::value && {cpp_meta_expr}, "{message}");'.format(**locals())
            elif arg_decl.type.kind == lowir.ExprKind.TYPE:
                bound_var = arg_decl.name
                return 'static_assert(AlwaysTrueFromType<{bound_var}>::value && {cpp_meta_expr}, "{message}");'.format(**locals())

        # All of this function's params are functions, we can't use any of the predefined AlwaysTrue* templates.
        # We need to define a new AlwaysTrueFromType variant for this specific function type.
        always_true_id = next(cxx_identifier_generator)
        template_param_decl = _type_to_template_param_declaration(type=enclosing_function_defn_args[0].type)
        template_param = enclosing_function_defn_args[0].name
        return '''\
            template <{template_param_decl}>
            struct {always_true_id} {{
              static constexpr bool value = true;
            }};
            static_assert({always_true_id}<{template_param}>::value && {cpp_meta_expr}, "{message}");
            '''.format(**locals())

def constant_def_to_cpp(constant_def: lowir.ConstantDef, cxx_identifier_generator: Iterator[str]):
    if isinstance(constant_def.type, lowir.BoolType):
        type_cpp = 'bool'
    else:
        raise NotImplementedError('Unexpected expression type: %s' % constant_def.type)

    name = constant_def.name
    cpp_meta_expr = expr_to_cpp(constant_def.expr)
    return '''\
        static constexpr {type_cpp} {name} = {cpp_meta_expr};
        '''.format(**locals())

def typedef_to_cpp(typedef: lowir.Typedef, cxx_identifier_generator: Iterator[str]):
    name = typedef.name
    if typedef.type.kind == lowir.ExprKind.TYPE:
        cpp_meta_expr = expr_to_cpp(typedef.expr)
        return '''\
            using {name} = {cpp_meta_expr};
            '''.format(**locals())
    elif typedef.type.kind == lowir.ExprKind.TEMPLATE:
        assert isinstance(typedef.type, lowir.TemplateType)

        template_args = [lowir.TemplateArgDecl(type=arg_type, name=next(cxx_identifier_generator))
                         for arg_type in typedef.type.argtypes]
        template_args_decl = ', '.join(template_arg_decl_to_cpp(arg)
                                       for arg in template_args)

        template_instantiation_expr = lowir.TemplateInstantiation(template_expr=typedef.expr,
                                                                  args=[lowir.TypeLiteral(kind=arg.type.kind,
                                                                                          cpp_type=arg.name)
                                                                  for arg in template_args])

        cpp_meta_expr = template_instantiation_to_cpp(template_instantiation_expr)

        return '''\
            template <{template_args_decl}>
            using {name} = {cpp_meta_expr};
            '''.format(**locals())
    else:
        raise NotImplementedError('Unexpected expression type kind: %s' % typedef.type.kind)

def _type_to_template_param_declaration(type: lowir.ExprType):
    if type.kind == lowir.ExprKind.BOOL:
        return 'bool'
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
                                   cxx_identifier_generator: Iterator[str]):
    def _template_body_element_to_cpp(x):
        if isinstance(x, lowir.StaticAssert):
            return static_assert_to_cpp(x,
                                        enclosing_function_defn_args=specialization.args,
                                        cxx_identifier_generator=cxx_identifier_generator)
        elif isinstance(x, lowir.ConstantDef):
            return constant_def_to_cpp(x, cxx_identifier_generator)
        elif isinstance(x, lowir.Typedef):
            return typedef_to_cpp(x, cxx_identifier_generator)
        else:
            raise NotImplementedError('Unsupported element: ' + x.__class__)


    asserts_and_assignments_str = ''.join(_template_body_element_to_cpp(x) + '\n'
                                          for x in specialization.body)
    template_args = ', '.join(template_arg_decl_to_cpp(arg)
                              for arg in specialization.args)
    if specialization.patterns is not None:
        patterns_str = ', '.join(type_pattern_literal_to_cpp(pattern)
                                 for pattern in specialization.patterns)
        return '''\
            template <{template_args}>
            struct {cxx_name}<{patterns_str}> {{
              {asserts_and_assignments_str}  
            }};
            '''.format(**locals())
    else:
        return '''\
            template <{template_args}>
            struct {cxx_name} {{
              {asserts_and_assignments_str}  
            }};
            '''.format(**locals())

def template_defn_to_cpp(template_defn: lowir.TemplateDefn, cxx_identifier_generator: Iterator[str]):
    template_name = template_defn.name
    if template_defn.main_definition:
        main_definition_str = template_specialization_to_cpp(template_defn.main_definition,
                                                             cxx_name=template_name,
                                                             cxx_identifier_generator=cxx_identifier_generator)
    else:
        template_args = ', '.join(template_arg_decl_to_cpp(arg)
                                  for arg in template_defn.args)
        main_definition_str = '''\
            template <{template_args}>
            struct {template_name};
            '''.format(**locals())
    specializations_str = ''.join(template_specialization_to_cpp(specialization,
                                                                 cxx_name=template_name,
                                                                 cxx_identifier_generator=cxx_identifier_generator)
                                  for specialization in template_defn.specializations)
    return main_definition_str + specializations_str

def literal_to_cpp(literal: lowir.Literal):
    return {
        True: 'true',
        False: 'false',
    }[literal.value]

def type_literal_to_cpp(literal: lowir.TypeLiteral):
    return literal.cpp_type

def type_pattern_literal_to_cpp(pattern: lowir.TypePatternLiteral):
    return pattern.cxx_pattern

def equality_comparison_to_cpp(comparison: lowir.EqualityComparison):
    lhs_cpp_meta_expr = expr_to_cpp(comparison.lhs)
    rhs_cpp_meta_expr = expr_to_cpp(comparison.rhs)
    return '({lhs_cpp_meta_expr}) == ({rhs_cpp_meta_expr})'.format(**locals())

def template_instantiation_to_cpp(instantiation_expr: lowir.TemplateInstantiation, omit_typename=False):
    template_params = ', '.join(expr_to_cpp(arg)
                                for arg in instantiation_expr.args)
    if isinstance(instantiation_expr.template_expr, lowir.ClassMemberAccess):
        cpp_fun = class_member_access_to_cpp(instantiation_expr.template_expr,
                                             omit_typename=omit_typename,
                                             parent_expr_is_template_instantiation=True)
    else:
        cpp_fun = expr_to_cpp(instantiation_expr.template_expr)
    return '{cpp_fun}<{template_params}>'.format(**locals())

def class_member_access_to_cpp(expr: lowir.ClassMemberAccess,
                               omit_typename: bool = False,
                               parent_expr_is_template_instantiation: bool = False):
    if isinstance(expr.class_type_expr, lowir.TemplateInstantiation):
        cpp_fun = template_instantiation_to_cpp(expr.class_type_expr, omit_typename=True)
    elif isinstance(expr.class_type_expr, lowir.ClassMemberAccess):
        cpp_fun = class_member_access_to_cpp(expr.class_type_expr, omit_typename=True)
    else:
        cpp_fun = expr_to_cpp(expr.class_type_expr)
    member_name = expr.member_name
    if expr.member_kind == lowir.ExprKind.BOOL:
        cpp_str_template = '{cpp_fun}::{member_name}'
    elif expr.member_kind in (lowir.ExprKind.TYPE, lowir.ExprKind.TEMPLATE):
        if omit_typename:
            maybe_typename = ''
        else:
            maybe_typename = 'typename '
        if parent_expr_is_template_instantiation:
            maybe_template = 'template '
        else:
            maybe_template = ''

        cpp_str_template = '{maybe_typename}{cpp_fun}::{maybe_template}{member_name}'
    else:
        raise NotImplementedError('Member kind: %s' % expr.member_kind)
    return cpp_str_template.format(**locals())

def header_to_cpp(header: lowir.Header, cxx_identifier_generator: Iterator[str]):
    includes = '''\
        #include <tmppy/tmppy.h>
        #include <type_traits>     
        '''
    return (includes
            + ''.join(template_defn_to_cpp(x, cxx_identifier_generator=cxx_identifier_generator)
                      for x in header.template_defns)
            + ''.join(static_assert_to_cpp(x,
                                           enclosing_function_defn_args=[],
                                           cxx_identifier_generator=cxx_identifier_generator)
                      for x in header.assertions))
