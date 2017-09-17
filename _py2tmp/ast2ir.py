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
import _py2tmp.ir as ir
import _py2tmp.types as types
import typed_ast.ast3 as ast
from typing import List, Tuple, Dict, Optional, Union

class Symbol:
    def __init__(self, name: str, type: types.ExprType):
        self.type = type
        self.name = name

class SymbolTable:
    def __init__(self, parent=None):
        self.symbols_by_name = dict() # type: Dict[str, Tuple[Symbol, ast.AST]]
        self.parent = parent

    def get_symbol_definition(self, name: str) -> Tuple[Optional[Symbol], Optional[ast.AST]]:
        result = self.symbols_by_name.get(name)
        if result:
            return result
        if self.parent:
            return self.parent.get_symbol_definition(name)
        return None, None

    def add_symbol(self, name: str, type: types.ExprType, definition_ast_node: ast.AST, compilation_context):
        '''
        Adds a symbol to the symbol table.

        This throws an error (created by calling `create_already_defined_error(previous_type)`) if a symbol with the
        same name and different type was already defined in this scope.
        '''
        previous_symbol, previous_definition_ast_node = self.symbols_by_name.get(name, (None, None))
        if previous_symbol:
            assert isinstance(previous_definition_ast_node, ast.AST)
            raise CompilationError(compilation_context,
                                   definition_ast_node,
                                   '%s was already defined in this scope.' % name,
                                   notes=[(previous_definition_ast_node, 'The previous declaration was here.')])
        self.symbols_by_name[name] = (Symbol(name, type), definition_ast_node)

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
            new_function_defns, fun_type = function_def_ast_to_ir(ast_node, compilation_context)
            function_defns += new_function_defns
            compilation_context.symbol_table.add_symbol(
                name=ast_node.name,
                type=fun_type,
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
                raise CompilationError(compilation_context, ast_node, 'Imports must import at least 1 symbol.') # pragma: no cover
            for imported_name in ast_node.names:
                if (not isinstance(imported_name, ast.alias)
                    or imported_name.asname):
                    raise CompilationError(compilation_context, ast_node, 'TMPPy only supports imports of the form "from some_module import some_symbol, some_other_symbol".')
                if not imported_name.name in supported_imports:
                    raise CompilationError(compilation_context, ast_node, 'The only supported imports from %s are: %s.' % (ast_node.module, ', '.join(sorted(supported_imports))))
        elif isinstance(ast_node, ast.Import):
            raise CompilationError(compilation_context, ast_node,
                                   'TMPPy only supports imports of the form "from some_module import some_symbol, some_other_symbol".')
        elif isinstance(ast_node, ast.Assert):
            toplevel_assertions.append(assert_ast_to_ir(ast_node, compilation_context))
        else:
            raise CompilationError(compilation_context, ast_node, 'This Python construct is not supported in TMPPy')
    return ir.Module(function_defns=function_defns, assertions=toplevel_assertions)

def match_expression_ast_to_ir(ast_node: ast.Call, compilation_context: CompilationContext):
    assert isinstance(ast_node.func, ast.Call)
    if ast_node.keywords or ast_node.func.keywords:
        raise CompilationError(compilation_context, ast_node, 'Keyword arguments are not allowed in match(...)({...})')
    if not ast_node.func.args:
        raise CompilationError(compilation_context, ast_node.func, 'Found match() with no arguments; it must have at least 1 argument.')
    matched_exprs = []
    for expr_ast in ast_node.func.args:
        expr = expression_ast_to_ir(expr_ast, compilation_context)
        if expr.type != types.TypeType():
            raise CompilationError(compilation_context, expr_ast,
                                   'All arguments passed to match must have type Type, but an argument with type %s was specified.' % str(expr.type))
        matched_exprs.append(expr)
    if len(ast_node.args) != 1 or not isinstance(ast_node.args[0], ast.Dict):
        raise CompilationError(compilation_context, ast_node, 'Malformed match(...)({...})')
    [dict_expr_ast] = ast_node.args

    # Note that we only forward "local" symbols (excluding e.g. the symbols of global functions).
    local_variables_args = [ir.FunctionArgDecl(type=symbol.type, name=symbol.name)
                            for _, (symbol, _) in compilation_context.symbol_table.symbols_by_name.items()]

    parent_function_name = compilation_context.current_function_name
    assert parent_function_name
    # TODO: the names of these helpers might conflict once we allow multiple match() expressions (e.g. in an if-else).
    helper_function_name = parent_function_name + '_MatchHelper'

    forwarded_args_patterns = [ir.TypePatternLiteral(cxx_pattern=function_arg.to_cpp())
                               for function_arg in local_variables_args]

    main_definition = None
    main_definition_key_expr_ast = None
    function_specializations = []
    last_lambda_body_type = None
    last_lambda_body_ast_node = None
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
            raise CompilationError(compilation_context, key_expr_ast, 'Keyword arguments in TypePattern are not supported yet.')
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
                                                                    type=types.TypeType(),
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

        function_specialization_args = local_variables_args + [ir.FunctionArgDecl(type=types.TypeType(), name=arg_name)
                                                               for arg_name in lambda_arguments]

        specialization_patterns = forwarded_args_patterns + [ir.TypePatternLiteral(cxx_pattern=pattern)
                                                             for pattern in type_patterns]
        function_specialization = ir.FunctionSpecialization(args=function_specialization_args,
                                                            patterns=specialization_patterns,
                                                            asserts_and_assignments=[],
                                                            expression=lambda_body)

        if function_specialization.is_main_definition():
            if main_definition:
                assert main_definition_key_expr_ast
                raise CompilationError(compilation_context, key_expr_ast,
                                       'Found multiple specializations that specialize nothing',
                                       notes=[(main_definition_key_expr_ast, 'A previous specialization that specializes nothing was here')])
            main_definition = function_specialization
            main_definition_key_expr_ast = key_expr_ast
        else:
            function_specializations.append(function_specialization)

    expression_args = [ir.VarReference(symbol.type, symbol.name)
                       for _, (symbol, _) in compilation_context.symbol_table.symbols_by_name.items()] + matched_exprs

    helper_function = ir.FunctionDefn(args=local_variables_args + [ir.FunctionArgDecl(type=types.TypeType()) for _ in matched_exprs],
                                      main_definition=main_definition,
                                      specializations=function_specializations,
                                      cxx_name=helper_function_name,
                                      original_name=compilation_context.current_function_name,
                                      return_type=last_lambda_body_type)

    helper_function_reference = ir.VarReference(type=helper_function.type,
                                                cxx_name=helper_function.cxx_name)
    expression = ir.FunctionCall(fun_expr=helper_function_reference,
                                 args=expression_args)

    return helper_function, expression

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
        args.append(ir.FunctionArgDecl(type=arg_type, name=arg.arg))
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
    if ast_node.returns:
        declared_return_type = type_declaration_ast_to_ir_expression_type(ast_node.returns, compilation_context)
    else:
        declared_return_type = None

    asserts_and_assignments = []
    for statement_node in ast_node.body[:-1]:
        if isinstance(statement_node, ast.Assert):
            asserts_and_assignments.append(assert_ast_to_ir(statement_node, function_body_compilation_context))
        elif isinstance(statement_node, ast.Assign) or isinstance(statement_node, ast.AnnAssign) or isinstance(statement_node, ast.AugAssign):
            assignment_ir = assignment_ast_to_ir(statement_node, function_body_compilation_context)
            compilation_context.symbol_table.add_symbol(name=assignment_ir.lhs.name,
                                                        type=assignment_ir.lhs.type,
                                                        definition_ast_node=statement_node,
                                                        compilation_context=compilation_context)
            asserts_and_assignments.append(assignment_ir)
        else:
            raise CompilationError(compilation_context, statement_node, 'All statements in a function (except the last) must be assertions or assignments.')
    if not isinstance(ast_node.body[-1], ast.Return):
        raise CompilationError(compilation_context, ast_node.body[-1], 'The last statement in a function must be a return statement.')
    expression = ast_node.body[-1].value
    if not expression:
        raise CompilationError(compilation_context, ast_node.body[-1], 'Return statements with no returned expression are not supported.')
    if isinstance(expression, ast.Call) and isinstance(expression.func, ast.Call) and isinstance(expression.func.func, ast.Name) and expression.func.func.id == 'match':
        helper_function, expression = match_expression_ast_to_ir(expression, function_body_compilation_context)
        helper_functions = [helper_function]
    else:
        expression = expression_ast_to_ir(expression, function_body_compilation_context)
        helper_functions = []
    fun_type = types.FunctionType(argtypes=[arg.type for arg in args],
                                  returns=expression.type)

    if declared_return_type and declared_return_type != expression.type:
        raise CompilationError(compilation_context, ast_node.returns,
                               '%s declared %s as return type, but the actual return type was %s.' % (
                                   ast_node.name, str(declared_return_type), str(expression.type)))

    main_definition = ir.FunctionSpecialization(args=args,
                                                patterns=None,
                                                asserts_and_assignments=asserts_and_assignments,
                                                expression=expression)

    function_defn = ir.FunctionDefn(main_definition=main_definition,
                                    name=ast_node.name,
                                    return_type=expression.type,
                                    args=args,
                                    specializations=[])
    return helper_functions + [function_defn], fun_type

def assert_ast_to_ir(ast_node: ast.Assert, compilation_context: CompilationContext):
    expr = expression_ast_to_ir(ast_node.test, compilation_context)
    assert expr.type.kind == types.ExprKind.BOOL

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

    return ir.StaticAssert(expr=expr, message=message)

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

    return ir.Assignment(lhs=ir.VarReference(type=expr.type, name=target.id),
                         rhs=expr)

def compare_ast_to_ir(ast_node: ast.Compare, compilation_context: CompilationContext):
    if len(ast_node.ops) == 1 and isinstance(ast_node.ops[0], ast.Eq):
        if len(ast_node.comparators) != 1:
            raise CompilationError(compilation_context, ast_node, 'Expected exactly 1 comparator in expression, but got %s' % len(ast_node.comparators))
        return eq_ast_to_ir(ast_node.left, ast_node.comparators[0], compilation_context)
    else:
        raise CompilationError(compilation_context, ast_node, 'Comparison not supported.')  # pragma: no cover

def expression_ast_to_ir(ast_node: ast.AST, compilation_context: CompilationContext):
    if isinstance(ast_node, ast.NameConstant):
        return name_constant_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Name) and ast_node.func.id == 'Type':
        return type_literal_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Name) and ast_node.func.id == 'empty_list':
        return empty_list_literal_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Call) and isinstance(ast_node.func.func, ast.Name) and ast_node.func.func.id == 'match':
        raise CompilationError(compilation_context, ast_node, 'match expressions are only allowed at the top-level of a return statement')
    elif isinstance(ast_node, ast.Call):
        return function_call_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Compare):
        return compare_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.Name) and isinstance(ast_node.ctx, ast.Load):
        return var_reference_ast_to_ir(ast_node, compilation_context)
    elif isinstance(ast_node, ast.List) and isinstance(ast_node.ctx, ast.Load):
        return list_expression_ast_to_ir(ast_node, compilation_context)
    else:
        raise CompilationError(compilation_context, ast_node, 'Unsupported expression type.')  # pragma: no cover

def name_constant_ast_to_ir(ast_node: ast.NameConstant, compilation_context: CompilationContext):
    if ast_node.value in (True, False):
        type = types.BoolType()
    else:
        raise CompilationError(compilation_context, ast_node, 'NameConstant not supported: ' + str(ast_node.value))  # pragma: no cover

    return ir.Literal(
        value=ast_node.value,
        type=type)

def type_literal_ast_to_ir(ast_node: ast.Call, compilation_context: CompilationContext):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node, 'Keyword arguments are not supported.')
    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, 'Type() takes 1 argument. Got: %s' % len(ast_node.args))
    [arg] = ast_node.args
    if not isinstance(arg, ast.Str):
        raise CompilationError(compilation_context, arg, 'The first argument to Type should be a string constant.')
    return ir.TypeLiteral(cpp_type=arg.s)

def empty_list_literal_ast_to_ir(ast_node: ast.Call, compilation_context: CompilationContext):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node, 'Keyword arguments are not supported.')
    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, 'empty_list() takes 1 argument. Got: %s' % len(ast_node.args))
    [arg] = ast_node.args
    elem_type = type_declaration_ast_to_ir_expression_type(arg, compilation_context)
    return ir.ListExpr(type=types.ListType(elem_type),
                       elem_exprs=[])

def eq_ast_to_ir(lhs_node: ast.AST, rhs_node: ast.AST, compilation_context: CompilationContext):
    lhs = expression_ast_to_ir(lhs_node, compilation_context)
    rhs = expression_ast_to_ir(rhs_node, compilation_context)
    if lhs.type != rhs.type:
        raise CompilationError(compilation_context, lhs_node, 'Type mismatch in ==: %s vs %s' % (
            str(lhs.type), str(rhs.type)))
    if lhs.type.kind not in (types.ExprKind.BOOL, types.ExprKind.TYPE):
        raise CompilationError(compilation_context, lhs_node, 'Type not supported in equality comparison: ' + str(lhs.type))
    return ir.EqualityComparison(lhs=lhs, rhs=rhs)

def function_call_ast_to_ir(ast_node: ast.Call, compilation_context: CompilationContext):
    fun_expr = expression_ast_to_ir(ast_node.func, compilation_context)
    if not isinstance(fun_expr.type, types.FunctionType):
        raise CompilationError(compilation_context, ast_node,
                               'Attempting to call an object that is not a function. It has type: %s' % str(fun_expr.type))

    if ast_node.keywords and ast_node.args:
        raise CompilationError(compilation_context, ast_node, 'Function calls with a mix of keyword and non-keyword arguments are not supported. Please choose either style.')

    if ast_node.keywords:
        if not isinstance(fun_expr, ir.VarReference):
            raise CompilationError(compilation_context, ast_node,
                                   'Keyword arguments can only be used when calling a specific function, not when calling other callable expressions. Please switch to non-keyword arguments.')
        fun_symbol, fun_definition_ast_node = compilation_context.symbol_table.get_symbol_definition(fun_expr.name)
        function_definition_note = (fun_definition_ast_node, 'The definition of %s was here' % ast_node.func.id)
        assert fun_symbol
        assert fun_definition_ast_node
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
                    _, var_ref_ast_node = compilation_context.symbol_table.get_symbol_definition(keyword_arg.value.id)
                    notes.append((var_ref_ast_node, 'The definition of %s was here' % keyword_arg.value.id))

                raise CompilationError(compilation_context, keyword_arg.value,
                                       'Type mismatch for argument %s: expected type %s but was: %s' % (
                                           keyword_arg.arg, str(arg_type), str(expr.type)),
                                       notes=notes)
    else:
        ast_node_args = ast_node.args or []
        args = [expression_ast_to_ir(arg_node, compilation_context) for arg_node in ast_node_args]
        if len(args) != len(fun_expr.type.argtypes):
            if isinstance(ast_node.func, ast.Name):
                _, function_definition_ast_node = compilation_context.symbol_table.get_symbol_definition(ast_node.func.id)
                assert function_definition_ast_node
                raise CompilationError(compilation_context, ast_node,
                                       'Argument number mismatch in function call to %s: got %s arguments, expected %s' % (
                                           ast_node.func.id, len(args), len(fun_expr.type.argtypes)),
                                       notes=[(function_definition_ast_node, 'The definition of %s was here' % ast_node.func.id)])
            else:
                raise CompilationError(compilation_context, ast_node,
                                       'Argument number mismatch in function call: got %s arguments, expected %s' % (
                                           len(args), len(fun_expr.type.argtypes)))

        for arg_index, (expr, expr_ast_node, arg_type) in enumerate(zip(args, ast_node_args, fun_expr.type.argtypes)):
            if expr.type != arg_type:
                notes = []
                if isinstance(ast_node.func, ast.Name):
                    _, function_definition_ast_node = compilation_context.symbol_table.get_symbol_definition(ast_node.func.id)
                    notes.append((function_definition_ast_node, 'The definition of %s was here' % ast_node.func.id))

                if isinstance(expr_ast_node, ast.Name):
                    _, var_ref_ast_node = compilation_context.symbol_table.get_symbol_definition(expr_ast_node.id)
                    notes.append((var_ref_ast_node, 'The definition of %s was here' % expr_ast_node.id))

                raise CompilationError(compilation_context, expr_ast_node,
                                       'Type mismatch for argument %s: expected type %s but was: %s' % (
                                           arg_index, str(arg_type), str(expr.type)),
                                       notes=notes)

    return ir.FunctionCall(fun_expr=fun_expr, args=args)

def var_reference_ast_to_ir(ast_node: ast.Name, compilation_context: CompilationContext):
    assert isinstance(ast_node.ctx, ast.Load)
    symbol, _ = compilation_context.symbol_table.get_symbol_definition(ast_node.id)
    if not symbol:
        # TODO: remove debugging detail
        if compilation_context.symbol_table.parent:
            raise CompilationError(compilation_context, ast_node, 'Reference to undefined variable/function: ' + ast_node.id)
    return ir.VarReference(type=symbol.type, name=symbol.name)

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
    if isinstance(elem_type, types.FunctionType):
        raise CompilationError(compilation_context, ast_node,
                               'Creating lists of functions is not supported. The elements of this list have type: %s' % str(elem_type))

    list_type = types.ListType(elem_type)
    return ir.ListExpr(type=list_type, elem_exprs=elem_exprs)

def type_declaration_ast_to_ir_expression_type(ast_node: ast.AST, compilation_context: CompilationContext):
    if isinstance(ast_node, ast.Name) and isinstance(ast_node.ctx, ast.Load):
        if ast_node.id == 'bool':
            return types.BoolType()
        elif ast_node.id == 'Type':
            return types.TypeType()
        else:
            raise CompilationError(compilation_context, ast_node, 'Unsupported type: ' + ast_node.id)

    if (isinstance(ast_node, ast.Subscript)
          and isinstance(ast_node.value, ast.Name)
          and isinstance(ast_node.value.ctx, ast.Load)
          and isinstance(ast_node.ctx, ast.Load)
          and isinstance(ast_node.slice, ast.Index)):
        if ast_node.value.id == 'List':
            return types.ListType(type_declaration_ast_to_ir_expression_type(ast_node.slice.value, compilation_context))
        elif (ast_node.value.id == 'Callable'
              and isinstance(ast_node.slice.value, ast.Tuple)
              and len(ast_node.slice.value.elts) == 2
              and isinstance(ast_node.slice.value.elts[0], ast.List)
              and isinstance(ast_node.slice.value.elts[0].ctx, ast.Load)
              and all(isinstance(elem, ast.Name) and isinstance(elem.ctx, ast.Load)
                      for elem in ast_node.slice.value.elts[0].elts)):
            return types.FunctionType(
                argtypes=[type_declaration_ast_to_ir_expression_type(arg_type_decl, compilation_context)
                          for arg_type_decl in ast_node.slice.value.elts[0].elts],
                returns=type_declaration_ast_to_ir_expression_type(ast_node.slice.value.elts[1], compilation_context))

    raise CompilationError(compilation_context, ast_node, 'Unsupported type declaration.')
