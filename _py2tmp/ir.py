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

from _py2tmp.types import *
from _py2tmp.utils import *
from typing import List, TypeVar, Generic

class Expr:
    def __init__(self, type: ExprType):
        self.type = type

    def to_cpp(self) -> str: ...

class StaticAssert:
    def __init__(self, expr: Expr, message: str):
        assert expr.type.kind == ExprKind.BOOL
        self.expr = expr
        self.message = message

    def to_cpp(self):
        return 'static_assert({cpp_meta_expr}, "{message}");'.format(
            cpp_meta_expr=self.expr.to_cpp(),
            message=self.message)

def _type_to_template_param_declaration(type):
    if type.kind == ExprKind.BOOL:
        return 'bool'
    elif type.kind == ExprKind.TYPE:
        return 'typename'
    elif type.kind == ExprKind.TEMPLATE:
        return ('template <'
                + ', '.join(_type_to_template_param_declaration(arg_type)
                            for arg_type in type.argtypes)
                + '> class')
    else:
        raise Exception('Unsupported argument kind: ' + str(type.kind))

class FunctionArgDecl:
    def __init__(self, type: ExprType, name: str):
        self.type = type
        self.name = name

def _identifier_to_cpp(type, name):
    if type.kind == ExprKind.BOOL:
        return name
    elif type.kind in (ExprKind.TYPE, ExprKind.TEMPLATE):
        return name.title().replace("_", "")
    else:
        raise Exception('Unsupported kind: ' + str(type.kind))

class FunctionDefn(Expr):
    def __init__(self, asserts: List[StaticAssert], expression: Expr, type: ExprType, name: str, args: List[FunctionArgDecl]):
        super().__init__(type)
        assert expression.type.kind in (ExprKind.BOOL, ExprKind.TYPE)
        self.asserts = asserts
        self.expression = expression
        self.name = name
        self.args = args

    def to_cpp(self):
        metafunction_name = _identifier_to_cpp(type=self.type, name=self.name)
        cpp_meta_expr = self.expression.to_cpp()
        asserts_str = ''.join('  ' + x.to_cpp() + '\n' for x in self.asserts)
        template_args = ', '.join(_type_to_template_param_declaration(arg.type) + ' ' + _identifier_to_cpp(type=arg.type, name=arg.name)
                                  for arg in self.args)
        cpp_str_template = {
            ExprKind.BOOL: '''\
template <{template_args}>
struct {metafunction_name} {{
{asserts_str}  static constexpr bool value = {cpp_meta_expr};
}};
''',
            ExprKind.TYPE: '''\
template <{template_args}>
struct {metafunction_name} {{
{asserts_str}  using type = {cpp_meta_expr};
}};
'''
        }[self.expression.type.kind]
        return cpp_str_template.format(**locals())


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
        super().__init__(type=TypeType())
        self.cpp_type = cpp_type

    def to_cpp(self):
        return self.cpp_type

class EqualityComparison(Expr):
    def __init__(self, lhs: Expr, rhs: Expr):
        super().__init__(type=BoolType())
        assert lhs.type == rhs.type
        assert lhs.type.kind in (ExprKind.BOOL, ExprKind.TYPE)
        self.lhs = lhs
        self.rhs = rhs

    def to_cpp(self):
        lhs_cpp_meta_expr = self.lhs.to_cpp()
        rhs_cpp_meta_expr = self.rhs.to_cpp()
        cpp_str_template = {
            ExprKind.BOOL: '({lhs_cpp_meta_expr}) == ({rhs_cpp_meta_expr})',
            ExprKind.TYPE: 'std::is_same<{lhs_cpp_meta_expr}, {rhs_cpp_meta_expr}>::value'
        }[self.lhs.type.kind]
        return cpp_str_template.format(**locals())

class FunctionCall(Expr):
    def __init__(self, fun_expr: Expr, args: List[Expr]):
        assert fun_expr.type.kind == ExprKind.TEMPLATE
        super().__init__(type=fun_expr.type.returns)
        assert len(fun_expr.type.argtypes) == len(args)
        assert self.type.kind in (ExprKind.BOOL, ExprKind.TYPE)
        self.fun_expr = fun_expr
        self.args = args

    def to_cpp(self):
        cpp_fun = self.fun_expr.to_cpp()
        template_params = ', '.join(arg.to_cpp() for arg in self.args)
        cpp_str_template = {
            ExprKind.BOOL: '{cpp_fun}<{template_params}>::value',
            ExprKind.TYPE: 'typename {cpp_fun}<{template_params}>::type',
        }[self.type.kind]
        return cpp_str_template.format(**locals())

class VarReference(Expr):
    def __init__(self, type: ExprType, name: str):
        super().__init__(type=type)
        self.name = name

    def to_cpp(self):
        return _identifier_to_cpp(type=self.type, name=self.name)

class ListExpr(Expr):
    def __init__(self, type: ListType, elem_exprs: List[Expr]):
        super().__init__(type=type)
        assert type.elem_type.kind in (ExprKind.BOOL, ExprKind.TYPE)
        self.elem_exprs = elem_exprs

    def to_cpp(self):
        template_params = ', '.join(elem_expr.to_cpp()
                                    for elem_expr in self.elem_exprs)
        cpp_str_template = {
            ExprKind.BOOL: 'BoolList<{template_params}>',
            ExprKind.TYPE: 'List<{template_params}>'
        }[self.type.elem_type.kind]
        return cpp_str_template.format(**locals())

class Module:
    def __init__(self, function_defns: List[FunctionDefn]):
        self.function_defns = function_defns

    def to_cpp(self):
        includes = '''\
#include <tmppy/tmppy.h>
#include <type_traits>     
'''
        return includes + ''.join(function_defn.to_cpp()
                                  for function_defn in self.function_defns)
