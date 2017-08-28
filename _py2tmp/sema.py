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

from _py2tmp.ir import *

class Symbol:
    def __init__(self, name: str, type: ExprType):
        self.type = type
        self.name = name

class SymbolTable:
    def __init__(self, parent=None):
        self.symbols_by_name = dict()
        self.parent = parent

    def get_symbol(self, name: str):
        result = self.symbols_by_name.get(name)
        if not result and self.parent:
            result = self.parent.get_symbol(name)
        return result

    def add_symbol(self, name: str, type: ExprType):
        previous_symbol = self.get_symbol(name)
        if previous_symbol and previous_symbol.type != type:
            raise Exception('Type mismatch for symbol %s. It was defined both with type %s and with type %s' % (
                name, str(previous_symbol.type), str(type)))
        self.symbols_by_name[name] = Symbol(name, type)

def generate_ir_Module(ast_node: ast.Module, symbol_table: SymbolTable):
    function_defns = []
    for child_node in ast_node.body:
        if isinstance(child_node, ast.FunctionDef):
            function_defn = generate_ir_FunctionDef(child_node, symbol_table)
            function_defns.append(function_defn)
            symbol_table.add_symbol(child_node.name, function_defn.type)
        elif isinstance(child_node, ast.ImportFrom):
            if child_node.module == 'tmppy':
                if (len(child_node.names) != 1
                    or not isinstance(child_node.names[0], ast.alias)
                    or child_node.names[0].name != 'Type'
                    or child_node.names[0].asname):
                    raise Exception('The only supported import from mypl is "from tmppy import Type" but found: ' + pretty_dump(child_node))
            elif child_node.module == 'typing':
                if (len(child_node.names) != 1
                    or not isinstance(child_node.names[0], ast.alias)
                    or child_node.names[0].name not in ('List', 'Callable')
                    or child_node.names[0].asname):
                    raise Exception('The only supported import from typing are "from typing import List" and "from typing import Callable" but found: ' + pretty_dump(child_node))
        else:
            raise Exception('Unsupported AST node in MypyFile: ' + pretty_dump(child_node))
    return Module(function_defns=function_defns)

def generate_ir_FunctionDef(ast_node: ast.FunctionDef, symbol_table: SymbolTable):
    function_body_symbol_table = SymbolTable(parent=symbol_table)
    args = []
    for arg in ast_node.args.args:
        if arg.type_comment:
            raise Exception('Type comments (as opposed to annotations) for function arguments are not supported.')
        if not arg.annotation:
            raise Exception('All function arguments must have a type annotation')
        arg_type = type_declaration_to_type(arg.annotation)
        function_body_symbol_table.add_symbol(arg.arg, arg_type)
        args.append(FunctionArgDecl(type=arg_type, name=arg.arg))
    if not args:
        raise Exception('Functions with no arguments are not supported.')

    if ast_node.args.vararg:
        raise Exception('Function vararg arguments are not supported.')
    if ast_node.args.kwonlyargs:
        raise Exception('Keyword-only function arguments are not supported.')
    if ast_node.args.kw_defaults or ast_node.args.defaults:
        raise Exception('Default values for function arguments are not supported.')
    if ast_node.args.kwarg:
        raise Exception('Keyword function arguments are not supported.')
    if ast_node.decorator_list:
        raise Exception('Function decorators are not supported.')
    if ast_node.returns:
        raise Exception('Return type annotations for functions are not supported.')

    asserts = []
    for statement_node in ast_node.body[:-1]:
        if not isinstance(statement_node, ast.Assert):
            raise Exception('All statements in a function (except the last) must be assertions, but got: ' + pretty_dump(statement_node))
        asserts.append(generate_ir_Assert(statement_node, function_body_symbol_table))
    if not isinstance(ast_node.body[-1], ast.Return):
        raise Exception(
            'The last statement in a function must be a Return statement. Got: ' + pretty_dump(ast_node.body[-1]))
    expression = ast_node.body[-1].value
    if not expression:
        raise Exception('Return statements with no returned expression are not supported.')
    expression = generate_ir_expression(expression, function_body_symbol_table)
    type = FunctionType(argtypes=[arg.type for arg in args],
                        returns=expression.type)

    return FunctionDefn(
        asserts=asserts,
        expression=expression,
        name=ast_node.name,
        type=type,
        args=args)

def generate_ir_Assert(ast_node: ast.Assert, symbol_table: SymbolTable):
    expr = generate_ir_expression(ast_node.test, symbol_table)
    assert expr.type.kind == ExprKind.BOOL

    if ast_node.msg:
        assert isinstance(ast_node.msg, ast.Str)
        message = ast_node.msg.s
    else:
        message = 'Assertion error'

    return StaticAssert(expr=expr, message=message)

def generate_ir_Compare(ast_node: ast.Compare, symbol_table: SymbolTable):
    if len(ast_node.ops) == 1 and isinstance(ast_node.ops[0], ast.Eq):
        if len(ast_node.comparators) != 1:
            raise Exception('Expected exactly 1 comparator in expression, but got: ' + pretty_dump(ast_node))
        return generate_ir_Eq(ast_node.left, ast_node.comparators[0], symbol_table)
    else:
        raise Exception('Comparison not supported: ' + pretty_dump(ast_node))

def generate_ir_expression(ast_node: ast.AST, symbol_table: SymbolTable):
    if isinstance(ast_node, ast.NameConstant):
        return generate_ir_NameConstant(ast_node, symbol_table)
    elif isinstance(ast_node, ast.Call) and ast_node.func.id == 'Type':
        return generate_ir_type_literal(ast_node, symbol_table)
    elif isinstance(ast_node, ast.Call):
        return generate_ir_function_call(ast_node, symbol_table)
    elif isinstance(ast_node, ast.Compare):
        return generate_ir_Compare(ast_node, symbol_table)
    elif isinstance(ast_node, ast.Name) and isinstance(ast_node.ctx, ast.Load):
        return generate_ir_var_reference(ast_node, symbol_table)
    elif isinstance(ast_node, ast.List) and isinstance(ast_node.ctx, ast.Load):
        return generate_ir_list_expression(ast_node, symbol_table)
    else:
        raise Exception('Unsupported expression type: ' + pretty_dump(ast_node))

def generate_ir_NameConstant(ast_node: ast.NameConstant, symbol_table: SymbolTable):
    if ast_node.value in (True, False):
        type = BoolType()
    else:
        raise Exception('NameConstant not supported: ' + str(ast_node.value))

    return Literal(
        value=ast_node.value,
        type=type)

def generate_ir_type_literal(ast_node: ast.Call, symbol_table: SymbolTable):
    if len(ast_node.args) != 1:
        raise Exception('Type() takes exactly 1 argument. Got: ' + pretty_dump(ast_node))
    [arg] = ast_node.args
    if not isinstance(arg, ast.Str):
        raise Exception('The first argument to Type should be a string constant, but was: ' + pretty_dump(arg))
    assert isinstance(arg, ast.Str)
    return TypeLiteral(cpp_type=arg.s)

def generate_ir_Eq(lhs_node: ast.AST, rhs_node: ast.AST, symbol_table: SymbolTable):
    lhs = generate_ir_expression(lhs_node, symbol_table)
    rhs = generate_ir_expression(rhs_node, symbol_table)
    if lhs.type != rhs.type:
        raise Exception('Type mismatch in ==: %s vs %s' % (
            str(lhs.type), str(rhs.type)))
    if lhs.type.kind not in (ExprKind.BOOL, ExprKind.TYPE):
        raise Exception('Type not supported in equality comparison: ' + str(lhs.type))
    return EqualityComparison(lhs=lhs, rhs=rhs)

def generate_ir_function_call(ast_node: ast.Call, symbol_table: SymbolTable):
    fun_expr = generate_ir_expression(ast_node.func, symbol_table)
    if not isinstance(fun_expr.type, FunctionType):
        raise Exception('Attempting to call: %s but it\'s not a function. It has type: %s' % (
            pretty_dump(ast_node.func),
            str(fun_expr.type)))

    args = [generate_ir_expression(arg_node, symbol_table) for arg_node in ast_node.args]
    if len(args) != len(fun_expr.type.argtypes):
        raise Exception('Argument number mismatch in function call to %s: got %s arguments, expected %s' % (
            pretty_dump(ast_node.func), len(args), len(fun_expr.type.argtypes)))

    for arg_index, (expr, arg_type) in enumerate(zip(args, fun_expr.type.argtypes)):
        if expr.type != arg_type:
            raise Exception('Type mismatch for argument %s in the call to %s: expected type %s but was: %s' % (
                arg_index, pretty_dump(ast_node.func), str(arg_type), str(expr.type)))

    return FunctionCall(fun_expr=fun_expr, args=args)

def generate_ir_var_reference(ast_node: ast.Name, symbol_table: SymbolTable):
    assert isinstance(ast_node.ctx, ast.Load)
    symbol = symbol_table.get_symbol(ast_node.id)
    if not symbol:
        raise Exception('Reference to undefined variable/function: ' + ast_node.id)
    return VarReference(type=symbol.type, name=symbol.name)

def generate_ir_list_expression(ast_node: ast.List, symbol_table: SymbolTable):
    elem_exprs = [generate_ir_expression(elem_expr_node, symbol_table) for elem_expr_node in ast_node.elts]
    if len(elem_exprs) == 0:
        raise Exception('Empty lists are not currently supported.')
    elem_type = elem_exprs[0].type
    type = ListType(elem_type)
    for elem_expr in elem_exprs:
        if elem_expr.type != elem_type:
            raise Exception('Found different types in list elements, this is not supported. Types were: %s and %s' % (
                str(elem_type), str(elem_expr.type)))
    if isinstance(elem_type, FunctionType):
        raise Exception('Creating lists of functions is not supported')

    return ListExpr(type=type, elem_exprs=elem_exprs)

def type_declaration_to_type(ast_node: ast.AST):
    if isinstance(ast_node, ast.Name) and isinstance(ast_node.ctx, ast.Load):
        if ast_node.id == 'bool':
            return BoolType()
        elif ast_node.id == 'Type':
            return TypeType()
        else:
            raise Exception('Unsupported type constant: ' + ast_node.id)

    if (isinstance(ast_node, ast.Subscript)
          and isinstance(ast_node.value, ast.Name)
          and isinstance(ast_node.value.ctx, ast.Load)
          and isinstance(ast_node.ctx, ast.Load)
          and isinstance(ast_node.slice, ast.Index)):
        if ast_node.value.id == 'List':
            return ListType(type_declaration_to_type(ast_node.slice.value))
        elif (ast_node.value.id == 'Callable'
              and isinstance(ast_node.slice.value, ast.Tuple)
              and len(ast_node.slice.value.elts) == 2
              and isinstance(ast_node.slice.value.elts[0], ast.List)
              and isinstance(ast_node.slice.value.elts[0].ctx, ast.Load)
              and all(isinstance(elem, ast.Name) and isinstance(elem.ctx, ast.Load)
                      for elem in ast_node.slice.value.elts[0].elts)):
            return FunctionType(
                argtypes=[type_declaration_to_type(arg_type_decl)
                          for arg_type_decl in ast_node.slice.value.elts[0].elts],
                returns=type_declaration_to_type(ast_node.slice.value.elts[1]))

    raise Exception('Unsupported type declaration: ' + pretty_dump(ast_node))
