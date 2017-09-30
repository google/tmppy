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

import textwrap
import _py2tmp.highir as highir
import typed_ast.ast3 as ast
from typing import List, Tuple, Dict, Optional, Union
from _py2tmp.utils import ast_to_string

class Symbol:
    def __init__(self, name: str, type: highir.ExprType):
        self.type = type
        self.name = name

class SymbolLookupResult:
    def __init__(self, symbol: Symbol, ast_node: ast.AST, is_only_partially_defined: bool, symbol_table: 'SymbolTable'):
        self.symbol = symbol
        self.ast_node = ast_node
        self.is_only_partially_defined = is_only_partially_defined
        self.symbol_table = symbol_table

class SymbolTable:
    def __init__(self, parent=None):
        self.symbols_by_name = dict()  # type: Dict[str, Tuple[Symbol, ast.AST, bool]]
        self.parent = parent

    def get_symbol_definition(self, name: str):
        result = self.symbols_by_name.get(name)
        if result:
            symbol, ast_node, is_only_partially_defined = result
            return SymbolLookupResult(symbol, ast_node, is_only_partially_defined, self)
        if self.parent:
            return self.parent.get_symbol_definition(name)
        return None

    def add_symbol(self,
                   name: str,
                   type: highir.ExprType,
                   definition_ast_node: ast.AST,
                   compilation_context: 'CompilationContext',
                   is_only_partially_defined: bool = False):
        """
        Adds a symbol to the symbol table.

        This throws an error (created by calling `create_already_defined_error(previous_type)`) if a symbol with the
        same name and different type was already defined in this scope.
        """
        previous_symbol, previous_definition_ast_node, previous_symbol_is_only_partially_defined = self.symbols_by_name.get(name, (None, None, None))
        if previous_symbol:
            assert isinstance(previous_definition_ast_node, ast.AST)
            if previous_symbol_is_only_partially_defined:
                raise CompilationError(compilation_context,
                                       definition_ast_node,
                                       '%s could be already initialized at this point.' % name,
                                       notes=[(previous_definition_ast_node, 'It might have been initialized here (depending on which branch is taken).')])
            else:
                raise CompilationError(compilation_context,
                                       definition_ast_node,
                                       '%s was already defined in this scope.' % name,
                                       notes=[(previous_definition_ast_node, 'The previous declaration was here.')])
        self.symbols_by_name[name] = (Symbol(name, type), definition_ast_node, is_only_partially_defined)

class CompilationContext:
    def __init__(self, symbol_table: SymbolTable, filename: str, source_lines: List[str], function_name: Optional[str] = None):
        self.symbol_table = symbol_table
        self.filename = filename
        self.source_lines = source_lines
        self.current_function_name = function_name

    def create_child_context(self, function_name=None):
        return CompilationContext(SymbolTable(parent=self.symbol_table),
                                  self.filename,
                                  self.source_lines,
                                  function_name=function_name or self.current_function_name)

class CompilationError(Exception):
    def __init__(self, compilation_context: CompilationContext, ast_node: ast.AST, error_message: str, notes: List[Tuple[ast.AST, str]] = []):
        error_message = CompilationError._diagnostic_to_string(compilation_context=compilation_context,
                                                               ast_node=ast_node,
                                                               message='error: ' + error_message)
        notes = [CompilationError._diagnostic_to_string(compilation_context=compilation_context,
                                                        ast_node=note_ast_node,
                                                        message='note: ' + note_message)
                 for note_ast_node, note_message in notes]
        super().__init__(''.join([error_message] + notes))

    @staticmethod
    def _diagnostic_to_string(compilation_context: CompilationContext, ast_node: ast.AST, message: str):
        first_line_number = ast_node.lineno
        first_column_number = ast_node.col_offset
        error_marker = ' ' * first_column_number + '^'
        return textwrap.dedent('''\
            {filename}:{first_line_number}:{first_column_number}: {message}
            {line}
            {error_marker}
            ''').format(filename=compilation_context.filename,
                        first_line_number=first_line_number,
                        first_column_number=first_column_number,
                        message=message,
                        line=compilation_context.source_lines[first_line_number - 1],
                        error_marker=error_marker)

def module_ast_to_ir(module_ast_node: ast.Module, compilation_context: CompilationContext):
    function_defns = []
    toplevel_assertions = []
    for ast_node in module_ast_node.body:
        if isinstance(ast_node, ast.FunctionDef):
            new_function_defn = function_def_ast_to_ir(ast_node, compilation_context)
            function_defns.append(new_function_defn)

            compilation_context.symbol_table.add_symbol(
                name=ast_node.name,
                type=highir.FunctionType(argtypes=[arg.type
                                                   for arg in new_function_defn.args],
                                         returns=new_function_defn.return_type),
                definition_ast_node=ast_node,
                compilation_context=compilation_context)
        elif isinstance(ast_node, ast.ImportFrom):
            supported_imports_by_module = {
                'tmppy': ('Type', 'empty_list', 'TypePattern', 'match'),
                'typing': ('List', 'Callable')
            }
            supported_imports = supported_imports_by_module.get(ast_node.module)
            if not supported_imports:
                raise CompilationError(compilation_context, ast_node,
                                       'The only modules that can be imported in TMPPy are: ' + ', '.join(sorted(supported_imports_by_module.keys())))
            if len(ast_node.names) == 0:
                raise CompilationError(compilation_context, ast_node, 'Imports must import at least 1 symbol.')  # pragma: no cover
            for imported_name in ast_node.names:
                if not isinstance(imported_name, ast.alias) or imported_name.asname:
                    raise CompilationError(compilation_context, ast_node, 'TMPPy only supports imports of the form "from some_module import some_symbol, some_other_symbol".')
                if imported_name.name not in supported_imports:
                    raise CompilationError(compilation_context, ast_node, 'The only supported imports from %s are: %s.' % (ast_node.module, ', '.join(sorted(supported_imports))))
        elif isinstance(ast_node, ast.Import):
            raise CompilationError(compilation_context, ast_node,
                                   'TMPPy only supports imports of the form "from some_module import some_symbol, some_other_symbol".')
        elif isinstance(ast_node, ast.Assert):
            toplevel_assertions.append(assert_ast_to_ir(ast_node, compilation_context))
        else:
            raise CompilationError(compilation_context, ast_node, 'This Python construct is not supported in TMPPy')
    return highir.Module(function_defns=function_defns,
                         assertions=toplevel_assertions)

def match_expression_ast_to_ir(ast_node: ast.Call, compilation_context: CompilationContext):
    assert isinstance(ast_node.func, ast.Call)
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value, 'Keyword arguments are not allowed in match(...)({...})')
    if ast_node.func.keywords:
        raise CompilationError(compilation_context, ast_node.func.keywords[0].value, 'Keyword arguments are not allowed in match(...)({...})')
    if not ast_node.func.args:
        raise CompilationError(compilation_context, ast_node.func, 'Found match() with no arguments; it must have at least 1 argument.')
    matched_exprs = []
    for expr_ast in ast_node.func.args:
        expr = expression_ast_to_ir(expr_ast, compilation_context)
        if expr.type != highir.TypeType():
            raise CompilationError(compilation_context, expr_ast,
                                   'All arguments passed to match must have type Type, but an argument with type %s was specified.' % str(expr.type))
        matched_exprs.append(expr)
    if len(ast_node.args) != 1 or not isinstance(ast_node.args[0], ast.Dict):
        raise CompilationError(compilation_context, ast_node, 'Malformed match(...)({...})')
    [dict_expr_ast] = ast_node.args

    if not dict_expr_ast.keys:
        raise CompilationError(compilation_context, dict_expr_ast,
                               'An empty mapping dict was passed to match(), but at least 1 mapping is required.')

    parent_function_name = compilation_context.current_function_name
    assert parent_function_name

    main_definition = None
    main_definition_key_expr_ast = None
    last_lambda_body_type = None
    last_lambda_body_ast_node = None
    match_cases = []
    for key_expr_ast, value_expr_ast in zip(dict_expr_ast.keys, dict_expr_ast.values):
        if not isinstance(key_expr_ast, ast.Call) or not isinstance(key_expr_ast.func, ast.Name) or key_expr_ast.func.id != 'TypePattern':
            raise CompilationError(compilation_context, key_expr_ast, 'All keys in the dict used in match(...)({...}) must be of the form TypePattern(...).')
        if not key_expr_ast.args:
            raise CompilationError(compilation_context, key_expr_ast, 'Found TypePattern with no arguments, but the first argument is required.')
        for arg in key_expr_ast.args:
            if not isinstance(arg, ast.Str):
                raise CompilationError(compilation_context, arg, 'The non-keyword arguments of TypePattern must be string literals.')
        type_patterns = [arg.s for arg in key_expr_ast.args]
        if key_expr_ast.keywords:
            raise CompilationError(compilation_context, key_expr_ast.keywords[0].value, 'Keyword arguments in TypePattern are not supported yet.')
        if not isinstance(value_expr_ast, ast.Lambda):
            raise CompilationError(compilation_context, value_expr_ast, 'All values in the dict used in match(...)({...}) must be lambdas.')
        assert not value_expr_ast.args.kwonlyargs
        assert not value_expr_ast.args.vararg
        assert not value_expr_ast.args.kwarg
        assert not value_expr_ast.args.defaults
        assert not value_expr_ast.args.kw_defaults
        lambda_body_compilation_context = compilation_context.create_child_context()
        lambda_arguments = []
        for arg in value_expr_ast.args.args:
            lambda_arguments.append(arg.arg)
            lambda_body_compilation_context.symbol_table.add_symbol(name=arg.arg,
                                                                    type=highir.TypeType(),
                                                                    definition_ast_node=arg,
                                                                    compilation_context=lambda_body_compilation_context)
        lambda_body = expression_ast_to_ir(value_expr_ast.body, lambda_body_compilation_context)
        if last_lambda_body_type and lambda_body.type != last_lambda_body_type:
            raise CompilationError(compilation_context, value_expr_ast.body,
                                   'All lambdas in a match(...)({...}) expression should return the same type, but '
                                   'this lambda returns a %s while a previous lambda in this match expression '
                                   'returns a %s' % (
                                       str(lambda_body.type), str(last_lambda_body_type)),
                                   notes=[(last_lambda_body_ast_node,
                                           'A previous lambda returning a %s was here.' % str(last_lambda_body_type))])
        last_lambda_body_type = lambda_body.type
        last_lambda_body_ast_node = value_expr_ast.body

        match_case = highir.MatchCase(type_patterns=type_patterns, matched_var_names=lambda_arguments, expr=lambda_body)
        match_cases.append(match_case)

        if match_case.is_main_definition():
            if main_definition:
                assert main_definition_key_expr_ast
                raise CompilationError(compilation_context, key_expr_ast,
                                       'Found multiple specializations that specialize nothing',
                                       notes=[(main_definition_key_expr_ast, 'A previous specialization that specializes nothing was here')])
            main_definition = match_case
            main_definition_key_expr_ast = key_expr_ast

    return highir.MatchExpr(matched_exprs=matched_exprs, match_cases=match_cases)

def return_stmt_ast_to_ir(ast_node: ast.Return,
                          compilation_context: CompilationContext):
    expression = ast_node.value
    if not expression:
        raise CompilationError(compilation_context, ast_node,
                               'Return statements with no returned expression are not supported.')

    expression = expression_ast_to_ir(expression, compilation_context)

    return highir.ReturnStmt(expr=expression)

def if_stmt_ast_to_ir(ast_node: ast.If,
                      compilation_context: CompilationContext,
                      previous_return_stmt: Optional[Tuple[highir.ExprType, ast.Return]],
                      check_always_returns: bool):
    cond_expr = expression_ast_to_ir(ast_node.test, compilation_context)
    if cond_expr.type != highir.BoolType():
        raise CompilationError(compilation_context, ast_node,
                               'The condition in an if statement must have type bool, but was: %s' % str(cond_expr.type))

    if_branch_compilation_context = compilation_context.create_child_context()
    if_stmts, first_return_stmt = statements_ast_to_ir(ast_node.body, if_branch_compilation_context, previous_return_stmt, check_always_returns)
    if_branch_return_info = if_stmts[-1].get_return_type()

    if not previous_return_stmt and first_return_stmt:
        previous_return_stmt = first_return_stmt

    else_branch_compilation_context = compilation_context.create_child_context()

    if ast_node.orelse:
        else_stmts, first_return_stmt = statements_ast_to_ir(ast_node.orelse, else_branch_compilation_context, previous_return_stmt, check_always_returns)
        else_branch_return_info = else_stmts[-1].get_return_type()

        if not previous_return_stmt and first_return_stmt:
            previous_return_stmt = first_return_stmt
    else:
        else_branch_return_info = highir.ReturnTypeInfo(type=None, always_returns=False)

        else_stmts = []
        if check_always_returns:
            raise CompilationError(compilation_context, ast_node,
                                   'Missing return statement. You should add an else branch that returns, or a return after the if.')

    symbol_names = set()
    if not if_branch_return_info.always_returns:
        symbol_names = symbol_names.union(if_branch_compilation_context.symbol_table.symbols_by_name.keys())
    if not else_branch_return_info.always_returns:
        symbol_names = symbol_names.union(else_branch_compilation_context.symbol_table.symbols_by_name.keys())

    for symbol_name in symbol_names:
        if if_branch_return_info.always_returns or symbol_name not in if_branch_compilation_context.symbol_table.symbols_by_name:
            if_branch_symbol = None
            if_branch_definition_ast_node = None
            if_branch_is_only_partially_defined = None
        else:
            if_branch_symbol, if_branch_definition_ast_node, if_branch_is_only_partially_defined = if_branch_compilation_context.symbol_table.symbols_by_name[symbol_name]

        if else_branch_return_info.always_returns or symbol_name not in else_branch_compilation_context.symbol_table.symbols_by_name:
            else_branch_symbol = None
            else_branch_definition_ast_node = None
            else_branch_is_only_partially_defined = None
        else:
            else_branch_symbol, else_branch_definition_ast_node, else_branch_is_only_partially_defined = else_branch_compilation_context.symbol_table.symbols_by_name[symbol_name]

        if if_branch_symbol and else_branch_symbol:
            if if_branch_symbol.type != else_branch_symbol.type:
                raise CompilationError(compilation_context, else_branch_definition_ast_node,
                                       'The variable %s is defined with type %s here, but it was previously defined with type %s in another branch.' % (
                                           symbol_name, str(else_branch_symbol.type), str(if_branch_symbol.type)),
                                       notes=[(if_branch_definition_ast_node, 'A previous definition with type %s was here.' % str(if_branch_symbol.type))])
            symbol = if_branch_symbol
            definition_ast_node = if_branch_definition_ast_node
            is_only_partially_defined = if_branch_is_only_partially_defined or else_branch_is_only_partially_defined
        elif if_branch_symbol:
            symbol = if_branch_symbol
            definition_ast_node = if_branch_definition_ast_node
            if else_branch_return_info.always_returns:
                is_only_partially_defined = if_branch_is_only_partially_defined
            else:
                is_only_partially_defined = True
        elif else_branch_symbol:
            symbol = else_branch_symbol
            definition_ast_node = else_branch_definition_ast_node
            if if_branch_return_info.always_returns:
                is_only_partially_defined = else_branch_is_only_partially_defined
            else:
                is_only_partially_defined = True
        else:
            continue

        compilation_context.symbol_table.add_symbol(name=symbol.name,
                                                    type=symbol.type,
                                                    definition_ast_node=definition_ast_node,
                                                    compilation_context=compilation_context,
                                                    is_only_partially_defined=is_only_partially_defined)

    return highir.IfStmt(cond_expr=cond_expr, if_stmts=if_stmts, else_stmts=else_stmts), previous_return_stmt

def statements_ast_to_ir(ast_nodes: List[ast.AST],
                         compilation_context: CompilationContext,
                         previous_return_stmt: Optional[Tuple[highir.ExprType, ast.Return]],
                         check_always_returns: bool):
    assert ast_nodes

    statements = []
    first_return_stmt = None
    for statement_node in ast_nodes:
        if statements and statements[-1].get_return_type().always_returns:
            raise CompilationError(compilation_context, statement_node, 'Unreachable statement.')

        if isinstance(statement_node, ast.Assert):
            statements.append(assert_ast_to_ir(statement_node, compilation_context))
        elif isinstance(statement_node, ast.Assign) or isinstance(statement_node, ast.AnnAssign) or isinstance(statement_node, ast.AugAssign):
            assignment_ir = assignment_ast_to_ir(statement_node, compilation_context)
            compilation_context.symbol_table.add_symbol(name=assignment_ir.lhs.name,
                                                        type=assignment_ir.lhs.type,
                                                        definition_ast_node=statement_node,
                                                        compilation_context=compilation_context)
            statements.append(assignment_ir)
        elif isinstance(statement_node, ast.Return):
            return_stmt = return_stmt_ast_to_ir(statement_node, compilation_context)
            if previous_return_stmt:
                previous_return_stmt_type, previous_return_stmt_ast_node = previous_return_stmt
                if return_stmt.expr.type != previous_return_stmt_type:
                    raise CompilationError(compilation_context, statement_node,
                                           'Found return statement with different return type: %s instead of %s.' % (
                                               str(return_stmt.expr.type), str(previous_return_stmt_type)),
                                           notes=[(previous_return_stmt_ast_node, 'A previous return statement returning a %s was here.' % (
                                               str(previous_return_stmt_type),))])
            if not first_return_stmt:
                first_return_stmt = (return_stmt.expr.type, statement_node)
            statements.append(return_stmt)
        elif isinstance(statement_node, ast.If):
            if_stmt, first_return_stmt_in_if = if_stmt_ast_to_ir(statement_node, compilation_context, previous_return_stmt, check_always_returns and statement_node is ast_nodes[-1])
            if not first_return_stmt:
                first_return_stmt = first_return_stmt_in_if
            statements.append(if_stmt)
        else:
            raise CompilationError(compilation_context, statement_node, 'Unsupported statement.')

    if check_always_returns and not first_return_stmt:
        raise CompilationError(compilation_context, ast_nodes[-1],
                               'Missing return statement.')

    return statements, first_return_stmt

def function_def_ast_to_ir(ast_node: ast.FunctionDef, compilation_context: CompilationContext):
    function_body_compilation_context = compilation_context.create_child_context(function_name=ast_node.name)
    args = []
    for arg in ast_node.args.args:
        if not arg.annotation:
            if arg.type_comment:
                raise CompilationError(compilation_context, arg, 'All function arguments must have a type annotation. Note that type comments are not supported.')
            else:
                raise CompilationError(compilation_context, arg, 'All function arguments must have a type annotation.')
        arg_type = type_declaration_ast_to_ir_expression_type(arg.annotation, compilation_context)
        function_body_compilation_context.symbol_table.add_symbol(
            name=arg.arg,
            type=arg_type,
            definition_ast_node=arg,
            compilation_context=compilation_context)
        args.append(highir.FunctionArgDecl(type=arg_type, name=arg.arg))
    if not args:
        raise CompilationError(compilation_context, ast_node, 'Functions with no arguments are not supported.')

    if ast_node.args.vararg:
        raise CompilationError(compilation_context, ast_node, 'Function vararg arguments are not supported.')
    if ast_node.args.kwonlyargs:
        raise CompilationError(compilation_context, ast_node, 'Keyword-only function arguments are not supported.')
    if ast_node.args.kw_defaults or ast_node.args.defaults:
        raise CompilationError(compilation_context, ast_node, 'Default values for function arguments are not supported.')
    if ast_node.args.kwarg:
        raise CompilationError(compilation_context, ast_node, 'Keyword function arguments are not supported.')
    if ast_node.decorator_list:
        raise CompilationError(compilation_context, ast_node, 'Function decorators are not supported.')

    statements, first_return_stmt = statements_ast_to_ir(ast_node.body, function_body_compilation_context,
                                                         previous_return_stmt=None,
                                                         check_always_returns=True)

    return_type, first_return_stmt_ast_node = first_return_stmt

    if ast_node.returns:
        declared_return_type = type_declaration_ast_to_ir_expression_type(ast_node.returns, compilation_context)
        if declared_return_type != return_type:
            raise CompilationError(compilation_context, ast_node.returns,
                                   '%s declared %s as return type, but the actual return type was %s.' % (
                                       ast_node.name, str(declared_return_type), str(return_type)),
                                   notes=[(first_return_stmt_ast_node, 'A %s was returned here' % str(return_type))])

    return highir.FunctionDefn(name=ast_node.name,
                               args=args,
                               body=statements,
                               return_type=return_type)

def assert_ast_to_ir(ast_node: ast.Assert, compilation_context: CompilationContext):
    expr = expression_ast_to_ir(ast_node.test, compilation_context)
    assert isinstance(expr.type, highir.BoolType)

    if ast_node.msg:
        assert isinstance(ast_node.msg, ast.Str)
        message = ast_node.msg.s
    else:
        message = ''

    first_line_number = ast_node.lineno
    message = 'TMPPy assertion failed: {message}\n{filename}:{first_line_number}: {line}'.format(
        filename=compilation_context.filename,
        first_line_number=first_line_number,
        message=message,
        line=compilation_context.source_lines[first_line_number - 1])
    message = message.replace('\\', '\\\\').replace('"', '\"').replace('\n', '\\n')

    return highir.Assert(expr=expr, message=message)

def assignment_ast_to_ir(ast_node: Union[ast.Assign, ast.AnnAssign, ast.AugAssign],
                         compilation_context: CompilationContext):
    if isinstance(ast_node, ast.AugAssign):
        raise CompilationError(compilation_context, ast_node, 'Augmented assignments are not supported.')
    if isinstance(ast_node, ast.AnnAssign):
        raise CompilationError(compilation_context, ast_node, 'Assignments with type annotations are not supported.')
    assert isinstance(ast_node, ast.Assign)
    if ast_node.type_comment:
        raise CompilationError(compilation_context, ast_node, 'Type comments in assignments are not supported.')
    if len(ast_node.targets) > 1:
        raise CompilationError(compilation_context, ast_node, 'Multi-assignment is not supported.')
    [target] = ast_node.targets
    if isinstance(target, ast.List) or isinstance(target, ast.Tuple):
        raise CompilationError(compilation_context, ast_node, 'Unpacking in assignments is not currently supported.')
    if not isinstance(target, ast.Name):
        raise CompilationError(compilation_context, ast_node, 'Assignment not supported.')

    expr = expression_ast_to_ir(ast_node.value, compilation_context)

    return highir.Assignment(lhs=highir.VarReference(type=expr.type, name=target.id, is_global_function=False),
                             rhs=expr)

def compare_ast_to_ir(ast_node: ast.Compare, compilation_context: CompilationContext):
    if len(ast_node.ops) == 1 and isinstance(ast_node.ops[0], ast.Eq):
        if len(ast_node.comparators) != 1:
            raise CompilationError(compilation_context, ast_node, 'Expected exactly 1 comparator in expression, but got %s' % len(ast_node.comparators))
        return eq_ast_to_ir(ast_node.left, ast_node.comparators[0], compilation_context)
    else:
        raise CompilationError(compilation_context, ast_node, 'Comparison not supported.')  # pragma: no cover

def attribute_expression_ast_to_ir(ast_node: ast.Attribute, compilation_context: CompilationContext):
    value_expr = expression_ast_to_ir(ast_node.value, compilation_context)
    if not isinstance(value_expr.type, highir.TypeType):
        raise CompilationError(compilation_context, ast_node.value,
                               'Attribute access is not supported for values of type %s.' % str(value_expr.type))
    return highir.AttributeAccessExpr(expr=value_expr, attribute_name=ast_node.attr)

def number_literal_expression_ast_to_ir(ast_node: ast.Num, compilation_context: CompilationContext, positive: bool):
    n = ast_node.n
    if isinstance(n, float):
        raise CompilationError(compilation_context, ast_node, 'Floating-point values are not supported.')
    if isinstance(n, complex):
        raise CompilationError(compilation_context, ast_node, 'Complex values are not supported.')
    assert isinstance(n, int)
    if not positive:
        n = -n
    if n <= -2**63:
        raise CompilationError(compilation_context, ast_node,
                               'int value out of bounds: values lower than -2^63+1 are not supported.')
    if n >= 2**63:
        raise CompilationError(compilation_context, ast_node,
                               'int value out of bounds: values greater than 2^63-1 are not supported.')
    return highir.IntLiteral(value=n)

def and_expression_ast_to_ir(ast_node: ast.BoolOp, compilation_context: CompilationContext):
    assert isinstance(ast_node.op, ast.And)

    if not compilation_context.current_function_name:
        raise CompilationError(compilation_context, ast_node,
                               'The "and" operator is only supported in functions, not at toplevel.')

    assert len(ast_node.values) >= 2

    exprs = []
    for expr_ast_node in ast_node.values:
        expr = expression_ast_to_ir(expr_ast_node, compilation_context)
        if expr.type != highir.BoolType():
            raise CompilationError(compilation_context, ast_node.left,
                                   'The "and" operator is only supported for booleans, but this value has type %s.' % str(expr.type))
        exprs.append(expr)

    final_expr = exprs[-1]
    for expr in reversed(exprs[:-1]):
        final_expr = highir.AndExpr(lhs=expr, rhs=final_expr)

    return final_expr

def or_expression_ast_to_ir(ast_node: ast.BoolOp, compilation_context: CompilationContext):
    assert isinstance(ast_node.op, ast.Or)

    if not compilation_context.current_function_name:
        raise CompilationError(compilation_context, ast_node,
                               'The "or" operator is only supported in functions, not at toplevel.')

    assert len(ast_node.values) >= 2

    exprs = []
    for expr_ast_node in ast_node.values:
        expr = expression_ast_to_ir(expr_ast_node, compilation_context)
        if expr.type != highir.BoolType():
            raise CompilationError(compilation_context, ast_node.left,
                                   'The "or" operator is only supported for booleans, but this value has type %s.' % str(expr.type))
        exprs.append(expr)

    final_expr = exprs[-1]
    for expr in reversed(exprs[:-1]):
        final_expr = highir.OrExpr(lhs=expr, rhs=final_expr)

    return final_expr

def not_expression_ast_to_ir(ast_node: ast.UnaryOp, compilation_context: CompilationContext):
    assert isinstance(ast_node.op, ast.Not)

    expr = expression_ast_to_ir(ast_node.operand, compilation_context)

    if expr.type != highir.BoolType():
        raise CompilationError(compilation_context, ast_node.operand,
                               'The "or" operator is only supported for booleans, but this value has type %s.' % str(expr.type))

    return highir.NotExpr(expr=expr)

def expression_ast_to_ir(ast_node: ast.AST, compilation_context: CompilationContext):
    if isinstance(ast_node, ast.NameConstant):
        return name_constant_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Name) and ast_node.func.id == 'Type':
        return type_literal_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Name) and ast_node.func.id == 'empty_list':
        return empty_list_literal_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Call) and isinstance(ast_node.func.func, ast.Name) and ast_node.func.func.id == 'match':
        return match_expression_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Call):
        return function_call_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Compare):
        return compare_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Name) and isinstance(ast_node.ctx, ast.Load):
        return var_reference_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.List) and isinstance(ast_node.ctx, ast.Load):
        return list_expression_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Attribute) and isinstance(ast_node.ctx, ast.Load):
        return attribute_expression_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Num):
        return number_literal_expression_ast_to_ir(ast_node, compilation_context, positive=True)
    elif isinstance(ast_node, ast.UnaryOp) and isinstance(ast_node.op, ast.USub) and isinstance(ast_node.operand, ast.Num):
        return number_literal_expression_ast_to_ir(ast_node.operand, compilation_context, positive=False)
    elif isinstance(ast_node, ast.BoolOp) and isinstance(ast_node.op, ast.And):
        return and_expression_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.BoolOp) and isinstance(ast_node.op, ast.Or):
        return or_expression_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.UnaryOp) and isinstance(ast_node.op, ast.Not):
        return not_expression_ast_to_ir(ast_node, compilation_context)
    else:
        # raise CompilationError(compilation_context, ast_node, 'This kind of expression is not supported: %s' % ast_to_string(ast_node))
        raise CompilationError(compilation_context, ast_node, 'This kind of expression is not supported.')  # pragma: no cover

def name_constant_ast_to_ir(ast_node: ast.NameConstant, compilation_context: CompilationContext):
    if isinstance(ast_node.value, bool):
        return highir.BoolLiteral(value=ast_node.value)
    else:
        raise CompilationError(compilation_context, ast_node, 'NameConstant not supported: ' + str(ast_node.value))  # pragma: no cover

def type_literal_ast_to_ir(ast_node: ast.Call, compilation_context: CompilationContext):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value, 'Keyword arguments are not supported.')
    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, 'Type() takes 1 argument. Got: %s' % len(ast_node.args))
    [arg] = ast_node.args
    if not isinstance(arg, ast.Str):
        raise CompilationError(compilation_context, arg, 'The first argument to Type should be a string constant.')
    return highir.TypeLiteral(cpp_type=arg.s)

def empty_list_literal_ast_to_ir(ast_node: ast.Call, compilation_context: CompilationContext):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value, 'Keyword arguments are not supported.')
    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, 'empty_list() takes 1 argument. Got: %s' % len(ast_node.args))
    [arg] = ast_node.args
    elem_type = type_declaration_ast_to_ir_expression_type(arg, compilation_context)
    return highir.ListExpr(elem_type=elem_type, elem_exprs=[])

def eq_ast_to_ir(lhs_node: ast.AST, rhs_node: ast.AST, compilation_context: CompilationContext):
    lhs = expression_ast_to_ir(lhs_node, compilation_context)
    rhs = expression_ast_to_ir(rhs_node, compilation_context)
    if lhs.type != rhs.type:
        raise CompilationError(compilation_context, lhs_node, 'Type mismatch in ==: %s vs %s' % (
            str(lhs.type), str(rhs.type)))
    if isinstance(lhs.type, highir.FunctionType):
        raise CompilationError(compilation_context, lhs_node, 'Type not supported in equality comparison: ' + str(lhs.type))
    return highir.EqualityComparison(lhs=lhs, rhs=rhs)

def function_call_ast_to_ir(ast_node: ast.Call, compilation_context: CompilationContext):
    fun_expr = expression_ast_to_ir(ast_node.func, compilation_context)
    if not isinstance(fun_expr.type, highir.FunctionType):
        raise CompilationError(compilation_context, ast_node,
                               'Attempting to call an object that is not a function. It has type: %s' % str(fun_expr.type))

    if ast_node.keywords and ast_node.args:
        raise CompilationError(compilation_context, ast_node, 'Function calls with a mix of keyword and non-keyword arguments are not supported. Please choose either style.')

    if ast_node.keywords:
        if not isinstance(fun_expr, highir.VarReference):
            raise CompilationError(compilation_context, ast_node,
                                   'Keyword arguments can only be used when calling a specific function, not when calling other callable expressions. Please switch to non-keyword arguments.')
        lookup_result = compilation_context.symbol_table.get_symbol_definition(fun_expr.name)
        assert lookup_result
        assert not lookup_result.is_only_partially_defined
        fun_definition_ast_node = lookup_result.ast_node

        function_definition_note = (fun_definition_ast_node, 'The definition of %s was here' % ast_node.func.id)
        if not isinstance(fun_definition_ast_node, ast.FunctionDef):
            raise CompilationError(compilation_context, ast_node,
                                   'Keyword arguments can only be used when calling a specific function, not when calling other callable expressions. Please switch to non-keyword arguments.',
                                   notes=[function_definition_note])

        arg_expr_by_name = {keyword_arg.arg: expression_ast_to_ir(keyword_arg.value, compilation_context)
                            for keyword_arg in ast_node.keywords}
        formal_arg_names = {arg.arg for arg in fun_definition_ast_node.args.args}
        specified_nonexisting_args = arg_expr_by_name.keys() - formal_arg_names
        missing_args = formal_arg_names - arg_expr_by_name.keys()
        if specified_nonexisting_args and missing_args:
            raise CompilationError(compilation_context, ast_node,
                                   'Incorrect arguments in call to %s. Missing arguments: {%s}. Specified arguments that don\'t exist: {%s}' % (
                                       fun_expr.name, ', '.join(sorted(missing_args)), ', '.join(sorted(specified_nonexisting_args))),
                                   notes=[function_definition_note])
        elif specified_nonexisting_args:
            raise CompilationError(compilation_context, ast_node,
                                   'Incorrect arguments in call to %s. Specified arguments that don\'t exist: {%s}' % (
                                       fun_expr.name, ', '.join(sorted(specified_nonexisting_args))),
                                   notes=[function_definition_note])
        elif missing_args:
            raise CompilationError(compilation_context, ast_node,
                                   'Incorrect arguments in call to %s. Missing arguments: {%s}' % (
                                       fun_expr.name, ', '.join(sorted(missing_args))),
                                   notes=[function_definition_note])

        args = [arg_expr_by_name[arg.arg] for arg in fun_definition_ast_node.args.args]

        for expr, keyword_arg, arg_type in zip(args, ast_node.keywords, fun_expr.type.argtypes):
            if expr.type != arg_type:
                notes = [function_definition_note]

                if isinstance(keyword_arg.value, ast.Name):
                    lookup_result = compilation_context.symbol_table.get_symbol_definition(keyword_arg.value.id)
                    assert not lookup_result.is_only_partially_defined
                    notes.append((lookup_result.ast_node, 'The definition of %s was here' % keyword_arg.value.id))

                raise CompilationError(compilation_context, keyword_arg.value,
                                       'Type mismatch for argument %s: expected type %s but was: %s' % (
                                           keyword_arg.arg, str(arg_type), str(expr.type)),
                                       notes=notes)
    else:
        ast_node_args = ast_node.args or []
        args = [expression_ast_to_ir(arg_node, compilation_context) for arg_node in ast_node_args]
        if len(args) != len(fun_expr.type.argtypes):
            if isinstance(ast_node.func, ast.Name):
                lookup_result = compilation_context.symbol_table.get_symbol_definition(ast_node.func.id)
                assert lookup_result
                assert not lookup_result.is_only_partially_defined
                raise CompilationError(compilation_context, ast_node,
                                       'Argument number mismatch in function call to %s: got %s arguments, expected %s' % (
                                           ast_node.func.id, len(args), len(fun_expr.type.argtypes)),
                                       notes=[(lookup_result.ast_node, 'The definition of %s was here' % ast_node.func.id)])
            else:
                raise CompilationError(compilation_context, ast_node,
                                       'Argument number mismatch in function call: got %s arguments, expected %s' % (
                                           len(args), len(fun_expr.type.argtypes)))

        for arg_index, (expr, expr_ast_node, arg_type) in enumerate(zip(args, ast_node_args, fun_expr.type.argtypes)):
            if expr.type != arg_type:
                notes = []
                if isinstance(ast_node.func, ast.Name):
                    lookup_result = compilation_context.symbol_table.get_symbol_definition(ast_node.func.id)
                    assert lookup_result
                    assert not lookup_result.is_only_partially_defined
                    notes.append((lookup_result.ast_node, 'The definition of %s was here' % ast_node.func.id))

                if isinstance(expr_ast_node, ast.Name):
                    lookup_result = compilation_context.symbol_table.get_symbol_definition(expr_ast_node.id)
                    assert lookup_result
                    assert not lookup_result.is_only_partially_defined
                    notes.append((lookup_result.ast_node, 'The definition of %s was here' % expr_ast_node.id))

                raise CompilationError(compilation_context, expr_ast_node,
                                       'Type mismatch for argument %s: expected type %s but was: %s' % (
                                           arg_index, str(arg_type), str(expr.type)),
                                       notes=notes)

    return highir.FunctionCall(fun_expr=fun_expr, args=args)

def var_reference_ast_to_ir(ast_node: ast.Name, compilation_context: CompilationContext):
    assert isinstance(ast_node.ctx, ast.Load)
    lookup_result = compilation_context.symbol_table.get_symbol_definition(ast_node.id)
    if not lookup_result:
        raise CompilationError(compilation_context, ast_node, 'Reference to undefined variable/function')
    if lookup_result.is_only_partially_defined:
        raise CompilationError(compilation_context, ast_node,
                               'Reference to a variable that may or may not have been initialized (depending on which branch was taken)',
                               notes=[(lookup_result.ast_node, '%s might have been initialized here' % ast_node.id)])
    return highir.VarReference(type=lookup_result.symbol.type,
                               name=lookup_result.symbol.name,
                               is_global_function=lookup_result.symbol_table.parent is None)

def list_expression_ast_to_ir(ast_node: ast.List, compilation_context: CompilationContext):
    elem_exprs = [expression_ast_to_ir(elem_expr_node, compilation_context) for elem_expr_node in ast_node.elts]
    if len(elem_exprs) == 0:
        raise CompilationError(compilation_context, ast_node, 'Untyped empty lists are not supported. Please import empty_list from pytmp and then write e.g. empty_list(int) to create an empty list of ints.')
    elem_type = elem_exprs[0].type
    for elem_expr, elem_expr_ast_node in zip(elem_exprs, ast_node.elts):
        if elem_expr.type != elem_type:
            raise CompilationError(compilation_context, elem_expr_ast_node,
                                   'Found different types in list elements, this is not supported. The type of this element was %s instead of %s' % (
                                       str(elem_expr.type), str(elem_type)),
                                   notes=[(ast_node.elts[0], 'A previous list element with type %s was here.' % str(elem_type))])
    if isinstance(elem_type, highir.FunctionType):
        raise CompilationError(compilation_context, ast_node,
                               'Creating lists of functions is not supported. The elements of this list have type: %s' % str(elem_type))

    return highir.ListExpr(elem_type=elem_type, elem_exprs=elem_exprs)

def type_declaration_ast_to_ir_expression_type(ast_node: ast.AST, compilation_context: CompilationContext):
    if isinstance(ast_node, ast.Name) and isinstance(ast_node.ctx, ast.Load):
        if ast_node.id == 'bool':
            return highir.BoolType()
        elif ast_node.id == 'int':
            return highir.IntType()
        elif ast_node.id == 'Type':
            return highir.TypeType()
        else:
            raise CompilationError(compilation_context, ast_node, 'Unsupported type: ' + ast_node.id)

    if (isinstance(ast_node, ast.Subscript)
        and isinstance(ast_node.value, ast.Name)
        and isinstance(ast_node.value.ctx, ast.Load)
        and isinstance(ast_node.ctx, ast.Load)
        and isinstance(ast_node.slice, ast.Index)):
        if ast_node.value.id == 'List':
            return highir.ListType(type_declaration_ast_to_ir_expression_type(ast_node.slice.value, compilation_context))
        elif (ast_node.value.id == 'Callable'
              and isinstance(ast_node.slice.value, ast.Tuple)
              and len(ast_node.slice.value.elts) == 2
              and isinstance(ast_node.slice.value.elts[0], ast.List)
              and isinstance(ast_node.slice.value.elts[0].ctx, ast.Load)
              and all(isinstance(elem, ast.Name) and isinstance(elem.ctx, ast.Load)
                      for elem in ast_node.slice.value.elts[0].elts)):
            return highir.FunctionType(
                argtypes=[type_declaration_ast_to_ir_expression_type(arg_type_decl, compilation_context)
                          for arg_type_decl in ast_node.slice.value.elts[0].elts],
                returns=type_declaration_ast_to_ir_expression_type(ast_node.slice.value.elts[1], compilation_context))

    raise CompilationError(compilation_context, ast_node, 'Unsupported type declaration.')
