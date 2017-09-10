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

import typing

import _py2tmp.types as types
from typing import List, Optional

class Expr:
    def __init__(self, type: types.ExprType):
        self.type = type

    def to_cpp(self) -> str: ... # pragma: no cover

class StaticAssert:
    def __init__(self, expr: Expr, message: str):
        assert expr.type.kind == types.ExprKind.BOOL
        self.expr = expr
        self.message = message

    def to_cpp(self):
        return 'static_assert({cpp_meta_expr}, "{message}");'.format(
            cpp_meta_expr=self.expr.to_cpp(),
            message=self.message)

def _type_to_template_param_declaration(type):
    if type.kind == types.ExprKind.BOOL:
        return 'bool'
    elif type.kind == types.ExprKind.TYPE:
        return 'typename'
    elif type.kind == types.ExprKind.TEMPLATE:
        return ('template <'
                + ', '.join(_type_to_template_param_declaration(arg_type)
                            for arg_type in type.argtypes)
                + '> class')
    else:
        raise NotImplementedError('Unsupported argument kind: ' + str(type.kind))

class FunctionArgDecl:
    def __init__(self, type: types.ExprType, name: str):
        self.type = type
        self.name = name

def _identifier_to_cpp(type, name):
    if type.kind == types.ExprKind.BOOL:
        return name
    elif type.kind in (types.ExprKind.TYPE, types.ExprKind.TEMPLATE):
        return name.title().replace("_", "")
    else:
        raise NotImplementedError('Unsupported kind: ' + str(type.kind))

class FunctionDefn(Expr):
    def __init__(self, asserts: List[StaticAssert], expression: Expr, type: types.ExprType, name: str, args: List[FunctionArgDecl]):
        super().__init__(type)
        assert expression.type.kind in (types.ExprKind.BOOL, types.ExprKind.TYPE, types.ExprKind.TEMPLATE)
        if expression.type.kind == types.ExprKind.TEMPLATE:
            assert isinstance(expression.type, types.FunctionType)
            assert expression.type.returns.kind == types.ExprKind.TYPE
        self.asserts = asserts
        self.expression = expression
        self.name = name
        self.args = args

    def to_cpp(self):
        metafunction_name = _identifier_to_cpp(type=self.type, name=self.name)
        asserts_str = ''.join(x.to_cpp() + '\n' for x in self.asserts)
        template_args = ', '.join(_type_to_template_param_declaration(arg.type) + ' ' + _identifier_to_cpp(type=arg.type, name=arg.name)
                                  for arg in self.args)
        if self.expression.type.kind == types.ExprKind.BOOL:
            cpp_meta_expr = self.expression.to_cpp()
            return '''\
                template <{template_args}>
                struct {metafunction_name} {{
                  {asserts_str}  
                  static constexpr bool value = {cpp_meta_expr};
                }};
                '''.format(**locals())
        elif self.expression.type.kind == types.ExprKind.TYPE:
            cpp_meta_expr = self.expression.to_cpp()
            return '''\
                template <{template_args}>
                struct {metafunction_name} {{
                  {asserts_str}
                  using type = {cpp_meta_expr};
                }};
                '''.format(**locals())
        elif self.expression.type.kind == types.ExprKind.TEMPLATE:
            assert isinstance(self.expression.type, types.FunctionType)
            return_type = self.expression.type.returns
            assert return_type.kind == types.ExprKind.TYPE
            inner_template_args = [('Param_%s' % i, arg_type)
                                   for i, arg_type in enumerate(self.expression.type.argtypes)]
            inner_template_args_decl = ', '.join(_type_to_template_param_declaration(arg_type) + ' ' + template_arg_name
                                                 for template_arg_name, arg_type in inner_template_args)
            cpp_meta_expr = FunctionCall(self.expression,
                                         args=[VarReference(type=arg_type, cxx_name=template_arg_name)
                                               for template_arg_name, arg_type in inner_template_args]
                                         ).to_cpp()
            return '''\
                template <{template_args}>
                struct {metafunction_name} {{
                  {asserts_str}
                  template <{inner_template_args_decl}>
                  using type = {cpp_meta_expr};
                }};
                '''.format(**locals())
        else:
            raise NotImplementedError('Unexpected expression type kind: %s' % self.expression.type.kind)

class Literal(Expr):
    def __init__(self, value, type):
        super().__init__(type)
        assert value in (True, False)
        self.value = value

    def to_cpp(self):
        return {
            True: 'true',
            False: 'false',
        }[self.value]

class TypeLiteral(Expr):
    def __init__(self, cpp_type: str):
        super().__init__(type=types.TypeType())
        self.cpp_type = cpp_type

    def to_cpp(self):
        return self.cpp_type

class EqualityComparison(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        super().__init__(type=types.BoolType())
        assert lhs.type == rhs.type
        assert lhs.type.kind in (types.ExprKind.BOOL, types.ExprKind.TYPE)
        self.lhs = lhs
        self.rhs = rhs

    def to_cpp(self):
        lhs_cpp_meta_expr = self.lhs.to_cpp()
        rhs_cpp_meta_expr = self.rhs.to_cpp()
        cpp_str_template = {
            types.ExprKind.BOOL: '({lhs_cpp_meta_expr}) == ({rhs_cpp_meta_expr})',
            types.ExprKind.TYPE: 'std::is_same<{lhs_cpp_meta_expr}, {rhs_cpp_meta_expr}>::value'
        }[self.lhs.type.kind]
        return cpp_str_template.format(**locals())

class FunctionCall(Expr):
    def __init__(self, fun_expr: Expr, args: List[Expr]):
        assert fun_expr.type.kind == types.ExprKind.TEMPLATE
        super().__init__(type=fun_expr.type.returns)
        assert len(fun_expr.type.argtypes) == len(args)
        assert self.type.kind in (types.ExprKind.BOOL, types.ExprKind.TYPE, types.ExprKind.TEMPLATE)
        self.fun_expr = fun_expr
        self.args = args

    def to_cpp(self, is_nested_call=False):
        template_params = ', '.join(arg.to_cpp() for arg in self.args)
        if self.type.kind == types.ExprKind.BOOL:
            assert not is_nested_call
            cpp_fun = self.fun_expr.to_cpp()
            cpp_str_template = '{cpp_fun}<{template_params}>::value'
        elif self.type.kind in (types.ExprKind.TYPE, types.ExprKind.TEMPLATE):
            if isinstance(self.fun_expr, FunctionCall):
                cpp_fun = self.fun_expr.to_cpp(is_nested_call=True)
                assert not is_nested_call
                cpp_str_template = 'typename {cpp_fun}<{template_params}>'
            else:
                cpp_fun = self.fun_expr.to_cpp()
                if is_nested_call:
                    cpp_str_template = '{cpp_fun}<{template_params}>::template type'
                else:
                    cpp_str_template = 'typename {cpp_fun}<{template_params}>::type'
        else:
            raise NotImplementedError('Type kind: %s' % self.type.kind)
        return cpp_str_template.format(**locals())

class VarReference(Expr):
    def __init__(self, type: types.ExprType, name: Optional[str] = None, cxx_name: Optional[str] = None):
        super().__init__(type=type)
        assert name or cxx_name
        assert not (name and cxx_name)
        self.name = name
        self.cxx_name = cxx_name

    def to_cpp(self):
        if self.name:
            return _identifier_to_cpp(type=self.type, name=self.name)
        else:
            assert self.cxx_name
            return self.cxx_name

class ListExpr(Expr):
    def __init__(self, type: types.ListType, elem_exprs: List[Expr]):
        super().__init__(type=type)
        assert type.elem_type.kind in (types.ExprKind.BOOL, types.ExprKind.TYPE)
        self.elem_exprs = elem_exprs

    def to_cpp(self):
        template_params = ', '.join(elem_expr.to_cpp()
                                    for elem_expr in self.elem_exprs)
        cpp_str_template = {
            types.ExprKind.BOOL: 'BoolList<{template_params}>',
            types.ExprKind.TYPE: 'List<{template_params}>'
        }[self.type.elem_type.kind]
        return cpp_str_template.format(**locals())

class Module:
    def __init__(self, function_defns: List[FunctionDefn], assertions: List[StaticAssert]):
        self.function_defns = function_defns
        self.assertions = assertions

    def to_cpp(self):
        includes = '''\
            #include <tmppy/tmppy.h>
            #include <type_traits>     
            '''
        return includes + ''.join(x.to_cpp()
                                  for x in self.function_defns + self.assertions)
