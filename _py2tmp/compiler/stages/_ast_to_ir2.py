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
import itertools
import re
import textwrap
from typing import List, Tuple, Dict, Optional, Union, Callable, Iterator, Set

import ast

from _py2tmp.compiler.output_files import ObjectFileContent
from _py2tmp.coverage import SourceBranch
from _py2tmp.ir2 import ir2, get_free_variables, get_return_type


class Symbol:
    def __init__(self,
                 name: str,
                 expr_type: ir2.ExprType,
                 is_function_that_may_throw: bool,
                 source_module: Optional[str]):
        if is_function_that_may_throw:
            assert isinstance(expr_type, ir2.FunctionType)
        self.expr_type = expr_type
        self.name = name
        self.is_function_that_may_throw = is_function_that_may_throw
        self.source_module = source_module

class SymbolLookupResult:
    def __init__(self, symbol: Symbol, ast_node: ast.AST, is_only_partially_defined: bool, symbol_table: 'SymbolTable'):
        self.symbol = symbol
        self.ast_node = ast_node
        self.is_only_partially_defined = is_only_partially_defined
        self.symbol_table = symbol_table

class SymbolTable:
    def __init__(self, parent: 'SymbolTable' =None):
        self.symbols_by_name: Dict[str, Tuple[Symbol, ast.AST, bool]] = dict()
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
                   expr_type: ir2.ExprType,
                   definition_ast_node: ast.AST,
                   is_only_partially_defined: bool,
                   is_function_that_may_throw: bool,
                   source_module: Optional[str]):
        if is_function_that_may_throw:
            assert isinstance(expr_type, ir2.FunctionType)
        self.symbols_by_name[name] = (Symbol(name, expr_type, is_function_that_may_throw, source_module),
                                      definition_ast_node,
                                      is_only_partially_defined)

class CompilationContext:
    def __init__(self,
                 symbol_table: SymbolTable,
                 custom_types_symbol_table: SymbolTable,
                 external_ir2_symbols_by_name_by_module: Dict[str, Dict[str, Union[ir2.FunctionDefn, ir2.CustomType]]],
                 filename: str,
                 source_lines: List[str],
                 identifier_generator: Iterator[str],
                 function_name: Optional[str] = None,
                 function_definition_line: Optional[int] = None,
                 first_enclosing_except_stmt_line: Optional[int] = None,
                 partially_typechecked_function_definitions_by_name: Dict[str, ast.FunctionDef] = None):
        assert (function_name is None) == (function_definition_line is None)
        self.symbol_table = symbol_table
        self.custom_types_symbol_table = custom_types_symbol_table
        self.external_ir2_symbols_by_name_by_module = external_ir2_symbols_by_name_by_module
        self.partially_typechecked_function_definitions_by_name = partially_typechecked_function_definitions_by_name or dict()
        self.filename = filename
        self.source_lines = source_lines
        self.current_function_name = function_name
        self.current_function_definition_line = function_definition_line
        self.first_enclosing_except_stmt_line = first_enclosing_except_stmt_line
        self.identifier_generator = identifier_generator

    def create_child_context(self,
                             function_name: Optional[str] = None,
                             function_definition_line: Optional[int] = None,
                             first_enclosing_except_stmt_line: Optional[int] = None):
        assert (function_name is None) == (function_definition_line is None)
        return CompilationContext(SymbolTable(parent=self.symbol_table),
                                  self.custom_types_symbol_table,
                                  self.external_ir2_symbols_by_name_by_module,
                                  self.filename,
                                  self.source_lines,
                                  self.identifier_generator,
                                  function_name=function_name or self.current_function_name,
                                  function_definition_line=function_definition_line or self.current_function_definition_line,
                                  first_enclosing_except_stmt_line=first_enclosing_except_stmt_line or self.first_enclosing_except_stmt_line,
                                  partially_typechecked_function_definitions_by_name=self.partially_typechecked_function_definitions_by_name)

    def add_symbol(self,
                   name: str,
                   expr_type: ir2.ExprType,
                   definition_ast_node: ast.AST,
                   is_only_partially_defined: bool,
                   is_function_that_may_throw: bool,
                   source_module: Optional[str] = None):
        """
        Adds a symbol to the symbol table.

        This throws an error (created by calling `create_already_defined_error(previous_type)`) if a symbol with the
        same name and different type was already defined in this scope.
        """
        if is_function_that_may_throw:
            assert isinstance(expr_type, ir2.FunctionType)

        self._check_not_already_defined(name, definition_ast_node)

        self.symbol_table.add_symbol(name=name,
                                     expr_type=expr_type,
                                     definition_ast_node=definition_ast_node,
                                     is_only_partially_defined=is_only_partially_defined,
                                     is_function_that_may_throw=is_function_that_may_throw,
                                     source_module=source_module)

    def add_custom_type_symbol(self,
                               custom_type: ir2.CustomType,
                               definition_ast_node: Union[ast.ClassDef, ast.ImportFrom, None],
                               source_module: Optional[str] = None):
        self.add_symbol(name=custom_type.name,
                        expr_type=ir2.FunctionType(argtypes=tuple(arg.expr_type
                                                                  for arg in custom_type.arg_types),
                                                   argnames=tuple(arg.name
                                                                  for arg in custom_type.arg_types),
                                                   returns=custom_type),
                        definition_ast_node=definition_ast_node,
                        is_only_partially_defined=False,
                        is_function_that_may_throw=False)
        self.custom_types_symbol_table.add_symbol(name=custom_type.name,
                                                  expr_type=custom_type,
                                                  definition_ast_node=definition_ast_node,
                                                  is_only_partially_defined=False,
                                                  is_function_that_may_throw=False,
                                                  source_module=source_module)

    def add_symbol_for_function_with_unknown_return_type(self,
                                                         name: str,
                                                         definition_ast_node: ast.FunctionDef):
        self._check_not_already_defined(name, definition_ast_node)

        self.partially_typechecked_function_definitions_by_name[name] = definition_ast_node

    def add_symbol_for_external_elem(self,
                                     elem: Union[ir2.FunctionDefn, ir2.CustomType],
                                     import_from_ast_node: ast.ImportFrom,
                                     source_module: str):
        if isinstance(elem, ir2.FunctionDefn):
            self.add_symbol(name=elem.name,
                            expr_type=ir2.FunctionType(argtypes=tuple(arg.expr_type for arg in elem.args),
                                                       argnames=tuple(arg.name for arg in elem.args),
                                                       returns=elem.return_type),
                            definition_ast_node=import_from_ast_node,
                            is_only_partially_defined=False,
                            is_function_that_may_throw=True,
                            source_module=source_module)
        elif isinstance(elem, ir2.CustomType):
            self.add_custom_type_symbol(custom_type=elem,
                                        definition_ast_node=import_from_ast_node,
                                        source_module=source_module)
        else:
            raise NotImplementedError('Unexpected elem type: %s' % elem.__class__.__name__)

    def get_symbol_definition(self, name: str):
        return self.symbol_table.get_symbol_definition(name)

    def get_partial_function_definition(self, name: str):
        return self.partially_typechecked_function_definitions_by_name.get(name)

    def get_type_symbol_definition(self, name: str):
        return self.custom_types_symbol_table.get_symbol_definition(name)

    def set_function_type(self, name: str, expr_type: ir2.FunctionType):
        if name in self.partially_typechecked_function_definitions_by_name:
            ast_node = self.partially_typechecked_function_definitions_by_name[name]
            del self.partially_typechecked_function_definitions_by_name[name]
            self.symbol_table.add_symbol(name=name,
                                         expr_type=expr_type,
                                         definition_ast_node=ast_node,
                                         is_only_partially_defined=False,
                                         is_function_that_may_throw=True,
                                         source_module=None)
        else:
            assert self.get_symbol_definition(name).symbol.expr_type == expr_type

    def _check_not_already_defined(self, name: str, definition_ast_node: ast.AST):
        symbol_lookup_result = self.symbol_table.get_symbol_definition(name)
        if not symbol_lookup_result:
            symbol_lookup_result = self.custom_types_symbol_table.get_symbol_definition(name)
        if symbol_lookup_result:
            is_only_partially_defined = symbol_lookup_result.is_only_partially_defined
            previous_definition_ast_node = symbol_lookup_result.ast_node
        elif name in self.partially_typechecked_function_definitions_by_name:
            is_only_partially_defined = False
            previous_definition_ast_node = self.partially_typechecked_function_definitions_by_name[name]
        else:
            is_only_partially_defined = None
            previous_definition_ast_node = None
        if previous_definition_ast_node:
            if is_only_partially_defined:
                raise CompilationError(self, definition_ast_node,
                                       '%s could be already initialized at this point.' % name,
                                       notes=[(previous_definition_ast_node, 'It might have been initialized here (depending on which branch is taken).')])
            else:
                raise CompilationError(self, definition_ast_node,
                                       '%s was already defined in this scope.' % name,
                                       notes=[(previous_definition_ast_node, 'The previous declaration was here.')])


class CompilationError(Exception):
    def __init__(self, compilation_context: CompilationContext, ast_node: ast.AST, error_message: str, notes: List[Tuple[ast.AST, str]] = ()):
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


def _first_stmt_line(stmt: ast.AST):
    if isinstance(stmt, ast.ClassDef) and stmt.decorator_list:
        return stmt.decorator_list[0].lineno
    else:
        return stmt.lineno

def module_ast_to_ir2(module_ast_node: ast.Module,
                      filename: str,
                      source_lines: List[str],
                      identifier_generator: Iterator[str],
                      context_object_files: ObjectFileContent):
    external_ir2_symbols_by_name_by_module = {module_name: {elem.name: elem
                                                            for elem in itertools.chain(module_info.ir2_module.function_defns, module_info.ir2_module.custom_types)
                                                            if elem.name in module_info.ir2_module.public_names}
                                              for module_name, module_info in context_object_files.modules_by_name.items()
                                              if module_info.ir2_module}
    compilation_context = CompilationContext(SymbolTable(),
                                             SymbolTable(),
                                             external_ir2_symbols_by_name_by_module,
                                             filename,
                                             source_lines,
                                             identifier_generator)

    if module_ast_node.body:
        first_line = _first_stmt_line(module_ast_node.body[0])
    else:
        first_line = 1

    function_defns = []
    toplevel_assertions = []
    custom_types = []
    pass_stmts = []

    # First pass: process everything except function bodies and toplevel assertions
    for index, ast_node in enumerate(module_ast_node.body):
        if index + 1 < len(module_ast_node.body):
            next_stmt_line = _first_stmt_line(module_ast_node.body[index + 1])
        else:
            next_stmt_line = -first_line
        if isinstance(ast_node, ast.FunctionDef):
            function_name, arg_types, arg_names, return_type = function_def_ast_to_symbol_info(ast_node, compilation_context)

            if return_type:
                compilation_context.add_symbol(
                    name=function_name,
                    expr_type=ir2.FunctionType(argtypes=arg_types,
                                               argnames=arg_names,
                                               returns=return_type),
                    definition_ast_node=ast_node,
                    is_only_partially_defined=False,
                    is_function_that_may_throw=True)
            else:
                compilation_context.add_symbol_for_function_with_unknown_return_type(
                    name=function_name,
                    definition_ast_node=ast_node)
        elif isinstance(ast_node, ast.ImportFrom):
            _import_from_ast_to_ir2(ast_node, compilation_context)
            pass_stmts.append(ir2.PassStmt(SourceBranch(compilation_context.filename,
                                                        ast_node.lineno,
                                                        next_stmt_line)))
        elif isinstance(ast_node, ast.Import):
            raise CompilationError(compilation_context, ast_node,
                                   'TMPPy only supports imports of the form "from some_module import some_symbol, some_other_symbol".')
        elif isinstance(ast_node, ast.ClassDef):
            custom_type, additional_pass_stmts = class_definition_ast_to_ir2(ast_node, compilation_context, next_stmt_line)
            for pass_stmt in additional_pass_stmts:
                pass_stmts.append(pass_stmt)
            compilation_context.add_custom_type_symbol(custom_type=custom_type,
                                                       definition_ast_node=ast_node)
            custom_types.append(custom_type)
        elif isinstance(ast_node, ast.Assert):
            # We'll process this in the 2nd pass (since we need to infer function return types first).
            pass
        elif isinstance(ast_node, ast.Pass):
            pass_stmts.append(ir2.PassStmt(SourceBranch(compilation_context.filename,
                                                        ast_node.lineno,
                                                        next_stmt_line)))
        else:
            # raise CompilationError(compilation_context, ast_node, 'This Python construct is not supported in TMPPy:\n%s' % ast_to_string(ast_node))
            raise CompilationError(compilation_context, ast_node, 'This Python construct is not supported in TMPPy')

    # 2nd pass: process function bodies and toplevel assertions
    for index, ast_node in enumerate(module_ast_node.body):
        if index + 1 < len(module_ast_node.body):
            next_stmt_line = _first_stmt_line(module_ast_node.body[index + 1])
        else:
            next_stmt_line = -first_line

        if isinstance(ast_node, ast.FunctionDef):
            new_function_defn = function_def_ast_to_ir2(ast_node, compilation_context, next_stmt_line)
            function_defns.append(new_function_defn)
            pass_stmts.append(ir2.PassStmt(SourceBranch(compilation_context.filename,
                                                        ast_node.lineno,
                                                        next_stmt_line)))

            compilation_context.set_function_type(
                name=ast_node.name,
                expr_type=ir2.FunctionType(returns=new_function_defn.return_type,
                                           argtypes=tuple(arg.expr_type
                                                          for arg in new_function_defn.args),
                                           argnames=tuple(arg.name
                                                          for arg in new_function_defn.args)))
        elif isinstance(ast_node, ast.Assert):
            toplevel_assertions.append(assert_ast_to_ir2(ast_node, compilation_context, next_stmt_line))

    pass_stmts.append(ir2.PassStmt(source_branch=SourceBranch(file_name=compilation_context.filename,
                                                              source_line=-first_line,
                                                              dest_line=first_line)))
    if not module_ast_node.body:
        # There is an implicit Pass statement in empty modules.
        pass_stmts.append(ir2.PassStmt(source_branch=SourceBranch(file_name=filename,
                                                                  source_line=1,
                                                                  dest_line=-1)))

    public_names = set()
    for function_defn in function_defns:
        if not function_defn.name.startswith('_'):
            public_names.add(function_defn.name)

    return ir2.Module(function_defns=tuple(function_defns),
                      assertions=tuple(toplevel_assertions),
                      custom_types=tuple(custom_types),
                      public_names=frozenset(public_names),
                      pass_stmts=tuple(pass_stmts))


def _import_from_ast_to_ir2(ast_node: ast.ImportFrom, compilation_context: CompilationContext):
    if len(ast_node.names) == 0:
        raise CompilationError(compilation_context, ast_node,
                               'Imports must import at least 1 symbol.')  # pragma: no cover
    for imported_name in ast_node.names:
        if not isinstance(imported_name, ast.alias) or imported_name.asname:
            raise CompilationError(compilation_context, ast_node,
                                   'TMPPy only supports imports of the form "from some_module import some_symbol, some_other_symbol".')

    builtin_imports_by_module = {
        'tmppy': ('Type', 'empty_list', 'empty_set', 'match'),
        'typing': ('List', 'Set', 'Callable'),
        'dataclasses': ('dataclass',),
    }

    importable_names = builtin_imports_by_module.get(ast_node.module)
    action = lambda symbol_name: None

    if not importable_names:
        # TODO: require all directly imported modules to be specified directly instead of allowing transitively-present
        # modules.
        symbols_by_name = compilation_context.external_ir2_symbols_by_name_by_module.get(ast_node.module)
        if symbols_by_name is not None:
            importable_names = symbols_by_name.keys()
            action = lambda imported_name: compilation_context.add_symbol_for_external_elem(elem=compilation_context.external_ir2_symbols_by_name_by_module[ast_node.module][imported_name.name],
                                                                                            import_from_ast_node=ast_node,
                                                                                            source_module=ast_node.module)

    if importable_names is None:
        raise CompilationError(compilation_context, ast_node,
                               'Module not found. The only modules that can be imported are the builtin modules ('
                               + ', '.join(sorted(builtin_imports_by_module.keys()))
                               + ') and the modules in the specified object files ('
                               + (', '.join(sorted(name for name in compilation_context.external_ir2_symbols_by_name_by_module.keys() if name != '_py2tmp.compiler._tmppy_builtins')) or 'none')
                               + ')')


    for imported_name in ast_node.names:
        if imported_name.name not in importable_names:
            raise CompilationError(compilation_context, ast_node, 'The only supported imports from %s are: %s.' % (
                ast_node.module, ', '.join(sorted(importable_names))))
        action(imported_name)


def match_expression_ast_to_ir2(ast_node: ast.Call,
                                compilation_context: CompilationContext,
                                in_match_pattern: bool,
                                check_var_reference: Callable[[ast.Name], None],
                                match_lambda_argument_names: Set[str],
                                current_stmt_line: int):
    assert isinstance(ast_node.func, ast.Call)
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value, 'Keyword arguments are not allowed in match()')
    if ast_node.func.keywords:
        raise CompilationError(compilation_context, ast_node.func.keywords[0].value, 'Keyword arguments are not allowed in match()')
    if not ast_node.func.args:
        raise CompilationError(compilation_context, ast_node.func, 'Found match() with no arguments; it must have at least 1 argument.')
    matched_exprs = []
    for expr_ast in ast_node.func.args:
        expr = expression_ast_to_ir2(expr_ast, compilation_context, in_match_pattern, check_var_reference, match_lambda_argument_names, current_stmt_line)
        if expr.expr_type != ir2.TypeType():
            raise CompilationError(compilation_context, expr_ast,
                                   'All arguments passed to match must have type Type, but an argument with type %s was specified.' % str(expr.expr_type))
        matched_exprs.append(expr)

    if len(ast_node.args) != 1 or not isinstance(ast_node.args[0], ast.Lambda):
        raise CompilationError(compilation_context, ast_node, 'Malformed match()')
    [lambda_expr_ast] = ast_node.args
    lambda_args = lambda_expr_ast.args
    if lambda_args.vararg:
        raise CompilationError(compilation_context, lambda_args.vararg,
                               'Malformed match(): vararg lambda arguments are not supported')
    assert not lambda_args.kwonlyargs
    assert not lambda_args.kw_defaults
    assert not lambda_args.defaults

    lambda_arg_ast_node_by_name = {arg.arg: arg
                                   for arg in lambda_args.args}
    lambda_arg_index_by_name = {arg.arg: i
                                for i, arg in enumerate(lambda_args.args)}
    lambda_arg_names = {arg.arg for arg in lambda_args.args}
    unused_lambda_arg_names = {arg.arg for arg in lambda_args.args}

    if not isinstance(lambda_expr_ast.body, ast.Dict):
        raise CompilationError(compilation_context, ast_node, 'Malformed match()')
    dict_expr_ast = lambda_expr_ast.body

    if not dict_expr_ast.keys:
        raise CompilationError(compilation_context, dict_expr_ast,
                               'An empty mapping dict was passed to match(), but at least 1 mapping is required.')

    parent_function_name = compilation_context.current_function_name
    assert parent_function_name

    main_definition = None
    main_definition_key_expr_ast = None
    last_result_expr_type = None
    last_result_expr_ast_node = None
    match_cases = []
    for key_expr_ast, value_expr_ast in zip(dict_expr_ast.keys, dict_expr_ast.values):
        match_case_compilation_context = compilation_context.create_child_context()

        if isinstance(key_expr_ast, ast.Tuple):
            pattern_ast_nodes = key_expr_ast.elts
        else:
            pattern_ast_nodes = [key_expr_ast]

        if len(pattern_ast_nodes) != len(matched_exprs):
            raise CompilationError(match_case_compilation_context, key_expr_ast,
                                   '%s type patterns were provided, while %s were expected' % (len(pattern_ast_nodes), len(matched_exprs)),
                                   [(ast_node.func, 'The corresponding match() was here')])

        pattern_exprs = []
        for pattern_ast_node in pattern_ast_nodes:
            pattern_expr = expression_ast_to_ir2(pattern_ast_node,
                                                 match_case_compilation_context,
                                                 in_match_pattern=True,
                                                 check_var_reference=check_var_reference,
                                                 match_lambda_argument_names=lambda_arg_names,
                                                 current_stmt_line=current_stmt_line)
            pattern_exprs.append(pattern_expr)
            if pattern_expr.expr_type != ir2.TypeType():
                raise CompilationError(match_case_compilation_context, pattern_ast_node,
                                       'Type patterns must have type Type but this pattern has type %s' % str(pattern_expr.expr_type),
                                       [(ast_node.func, 'The corresponding match() was here')])

        lambda_args_used_in_pattern = {var.name: var.expr_type
                                       for pattern_expr in pattern_exprs
                                       for var in get_free_variables(pattern_expr).values()
                                       if var.name in lambda_arg_names}
        for var in lambda_args_used_in_pattern.keys():
            unused_lambda_arg_names.discard(var)

        def check_var_reference_in_result_expr(ast_node: ast.Name):
            check_var_reference(ast_node)
            if ast_node.id in lambda_arg_names and not ast_node.id in lambda_args_used_in_pattern:
                raise CompilationError(match_case_compilation_context, ast_node,
                                       '%s was used in the result of this match branch but not in any of its patterns' % ast_node.id)

        result_expr = expression_ast_to_ir2(value_expr_ast,
                                            match_case_compilation_context,
                                            in_match_pattern=in_match_pattern,
                                            check_var_reference=check_var_reference_in_result_expr,
                                            match_lambda_argument_names=match_lambda_argument_names,
                                            current_stmt_line=current_stmt_line)

        if last_result_expr_type and result_expr.expr_type != last_result_expr_type:
            raise CompilationError(match_case_compilation_context, value_expr_ast,
                                   'All branches in a match() must return the same type, but this branch returns a %s '
                                   'while a previous branch in this match expression returns a %s' % (
                                       str(result_expr.expr_type), str(last_result_expr_type)),
                                   notes=[(last_result_expr_ast_node,
                                           'A previous branch returning a %s was here.' % str(last_result_expr_type))])
        last_result_expr_type = result_expr.expr_type
        last_result_expr_ast_node = value_expr_ast

        matched_var_names = set()
        matched_variadic_var_names = set()
        for arg, arg_type in lambda_args_used_in_pattern.items():
            if arg_type == ir2.TypeType():
                matched_var_names.add(arg)
            elif arg_type == ir2.ListType(ir2.TypeType()):
                matched_variadic_var_names.add(arg)
            else:
                raise NotImplementedError('Unexpected arg type: %s' % str(arg_type))

        match_case = ir2.MatchCase(matched_var_names=frozenset(matched_var_names),
                                   matched_variadic_var_names=frozenset(matched_variadic_var_names),
                                   type_patterns=tuple(pattern_exprs),
                                   expr=result_expr,
                                   match_case_start_branch=SourceBranch(compilation_context.filename,
                                                                        current_stmt_line,
                                                                        -lambda_expr_ast.lineno),
                                   match_case_end_branch=SourceBranch(compilation_context.filename,
                                                                      -lambda_expr_ast.lineno,
                                                                      current_stmt_line))
        match_cases.append(match_case)

        if match_case.is_main_definition():
            if main_definition:
                assert main_definition_key_expr_ast
                raise CompilationError(match_case_compilation_context, key_expr_ast,
                                       'Found multiple specializations that specialize nothing',
                                       notes=[(main_definition_key_expr_ast, 'A previous specialization that specializes nothing was here')])
            main_definition = match_case
            main_definition_key_expr_ast = key_expr_ast

    if unused_lambda_arg_names:
        unused_arg_name = max(unused_lambda_arg_names, key=lambda arg_name: lambda_arg_index_by_name[arg_name])
        unused_arg_ast_node = lambda_arg_ast_node_by_name[unused_arg_name]
        raise CompilationError(compilation_context, unused_arg_ast_node,
                               'The lambda argument %s was not used in any pattern, it should be removed.' % unused_arg_name)

    return ir2.MatchExpr(matched_exprs=tuple(matched_exprs),
                         match_cases=tuple(match_cases))

def return_stmt_ast_to_ir2(ast_node: ast.Return,
                           compilation_context: CompilationContext):
    expression = ast_node.value
    if not expression:
        raise CompilationError(compilation_context, ast_node,
                               'Return statements with no returned expression are not supported.')

    expression = expression_ast_to_ir2(expression,
                                       compilation_context,
                                       in_match_pattern=False,
                                       check_var_reference=lambda ast_node: None,
                                       match_lambda_argument_names=set(),
                                       current_stmt_line=ast_node.lineno)

    return ir2.ReturnStmt(expr=expression,
                          source_branch=SourceBranch(compilation_context.filename,
                                                     ast_node.lineno,
                                                     -compilation_context.current_function_definition_line))

def if_stmt_ast_to_ir2(ast_node: ast.If,
                       compilation_context: CompilationContext,
                       previous_return_stmt: Optional[Tuple[ir2.ExprType, ast.Return]],
                       check_always_returns: bool,
                       next_stmt_line: int):
    cond_expr = expression_ast_to_ir2(ast_node.test,
                                      compilation_context,
                                      in_match_pattern=False,
                                      check_var_reference=lambda ast_node: None,
                                      match_lambda_argument_names=set(),
                                      current_stmt_line=ast_node.lineno)
    if cond_expr.expr_type != ir2.BoolType():
        raise CompilationError(compilation_context, ast_node,
                               'The condition in an if statement must have type bool, but was: %s' % str(cond_expr.expr_type))

    if_branch_compilation_context = compilation_context.create_child_context()
    if_stmts, first_return_stmt = statements_ast_to_ir2(ast_node.body, if_branch_compilation_context,
                                                        previous_return_stmt=previous_return_stmt,
                                                        check_block_always_returns=check_always_returns,
                                                        stmts_are_toplevel_in_function=False,
                                                        next_stmt_line=next_stmt_line)

    if not previous_return_stmt and first_return_stmt:
        previous_return_stmt = first_return_stmt

    else_branch_compilation_context = compilation_context.create_child_context()

    if ast_node.orelse:
        else_stmts, first_return_stmt = statements_ast_to_ir2(ast_node.orelse,
                                                              else_branch_compilation_context,
                                                              previous_return_stmt=previous_return_stmt,
                                                              check_block_always_returns=check_always_returns,
                                                              stmts_are_toplevel_in_function=False,
                                                              next_stmt_line=next_stmt_line)

        if not previous_return_stmt and first_return_stmt:
            previous_return_stmt = first_return_stmt
    else:
        else_stmts = []
        if check_always_returns:
            raise CompilationError(compilation_context, ast_node,
                                   'Missing return statement. You should add an else branch that returns, or a return after the if.')

    _join_definitions_in_branches(compilation_context,
                                  if_branch_compilation_context,
                                  if_stmts,
                                  else_branch_compilation_context,
                                  else_stmts)

    if_branch_first_nontrivial_stmt_line = compute_next_stmt_line_number_by_index([None, *ast_node.body], next_stmt_line)[0]
    else_branch_first_nontrivial_stmt_line = compute_next_stmt_line_number_by_index([None, *ast_node.orelse], next_stmt_line)[0]

    stmt_ir = ir2.IfStmt(cond_expr=cond_expr,
                         if_stmts=(ir2.PassStmt(SourceBranch(compilation_context.filename,
                                                ast_node.lineno,
                                                if_branch_first_nontrivial_stmt_line)),
                                   *if_stmts),
                         else_stmts=(ir2.PassStmt(SourceBranch(compilation_context.filename,
                                                  ast_node.lineno,
                                                  else_branch_first_nontrivial_stmt_line)),
                                     *else_stmts))

    return stmt_ir, previous_return_stmt

def _join_definitions_in_branches(parent_context: CompilationContext,
                                  branch1_context: CompilationContext,
                                  branch1_stmts: Tuple[ir2.Stmt, ...],
                                  branch2_context: CompilationContext,
                                  branch2_stmts: Tuple[ir2.Stmt, ...]):
    branch1_return_info = get_return_type(branch1_stmts)
    branch2_return_info = get_return_type(branch2_stmts)

    symbol_names = set()
    if not branch1_return_info.always_returns:
        symbol_names = symbol_names.union(branch1_context.symbol_table.symbols_by_name.keys())
    if not branch2_return_info.always_returns:
        symbol_names = symbol_names.union(branch2_context.symbol_table.symbols_by_name.keys())

    for symbol_name in symbol_names:
        if branch1_return_info.always_returns or symbol_name not in branch1_context.symbol_table.symbols_by_name:
            branch1_symbol = None
            branch1_definition_ast_node = None
            branch1_symbol_is_only_partially_defined = None
        else:
            branch1_symbol, branch1_definition_ast_node, branch1_symbol_is_only_partially_defined = branch1_context.symbol_table.symbols_by_name[symbol_name]

        if branch2_return_info.always_returns or symbol_name not in branch2_context.symbol_table.symbols_by_name:
            branch2_symbol = None
            branch2_definition_ast_node = None
            branch2_symbol_is_only_partially_defined = None
        else:
            branch2_symbol, branch2_definition_ast_node, branch2_symbol_is_only_partially_defined = branch2_context.symbol_table.symbols_by_name[symbol_name]

        if branch1_symbol and branch2_symbol:
            if branch1_symbol.expr_type != branch2_symbol.expr_type:
                raise CompilationError(parent_context, branch2_definition_ast_node,
                                       'The variable %s is defined with type %s here, but it was previously defined with type %s in another branch.' % (
                                           symbol_name, str(branch2_symbol.expr_type), str(branch1_symbol.expr_type)),
                                       notes=[(branch1_definition_ast_node, 'A previous definition with type %s was here.' % str(branch1_symbol.expr_type))])
            symbol = branch1_symbol
            definition_ast_node = branch1_definition_ast_node
            is_only_partially_defined = branch1_symbol_is_only_partially_defined or branch2_symbol_is_only_partially_defined
        elif branch1_symbol:
            symbol = branch1_symbol
            definition_ast_node = branch1_definition_ast_node
            if branch2_return_info.always_returns:
                is_only_partially_defined = branch1_symbol_is_only_partially_defined
            else:
                is_only_partially_defined = True
        else:
            assert branch2_symbol
            symbol = branch2_symbol
            definition_ast_node = branch2_definition_ast_node
            if branch1_return_info.always_returns:
                is_only_partially_defined = branch2_symbol_is_only_partially_defined
            else:
                is_only_partially_defined = True

        parent_context.add_symbol(name=symbol.name,
                                  expr_type=symbol.expr_type,
                                  definition_ast_node=definition_ast_node,
                                  is_only_partially_defined=is_only_partially_defined,
                                  is_function_that_may_throw=isinstance(symbol.expr_type, ir2.FunctionType))

def raise_stmt_ast_to_ir2(ast_node: ast.Raise, compilation_context: CompilationContext):
    if ast_node.cause:
        raise CompilationError(compilation_context, ast_node.cause,
                               '"raise ... from ..." is not supported. Use a plain "raise ..." instead.')
    exception_expr = expression_ast_to_ir2(ast_node.exc,
                                           compilation_context,
                                           in_match_pattern=False,
                                           check_var_reference=lambda ast_node: None,
                                           match_lambda_argument_names=set(),
                                           current_stmt_line=ast_node.lineno)
    if not (isinstance(exception_expr.expr_type, ir2.CustomType) and exception_expr.expr_type.is_exception_class):
        if isinstance(exception_expr.expr_type, ir2.CustomType):
            custom_type_defn = compilation_context.get_type_symbol_definition(exception_expr.expr_type.name).ast_node
            notes = [(custom_type_defn, 'The type %s was defined here.' % exception_expr.expr_type.name)]
        else:
            notes = []
        raise CompilationError(compilation_context, ast_node.exc,
                               'Can\'t raise an exception of type "%s", because it\'s not a subclass of Exception.' % str(exception_expr.expr_type),
                               notes=notes)
    return ir2.RaiseStmt(expr=exception_expr, source_branch=SourceBranch(compilation_context.filename,
                                                                         ast_node.lineno,
                                                                         compilation_context.first_enclosing_except_stmt_line
                                                                         if compilation_context.first_enclosing_except_stmt_line
                                                                         else -compilation_context.current_function_definition_line))

def try_stmt_ast_to_ir2(ast_node: ast.Try,
                        compilation_context: CompilationContext,
                        previous_return_stmt: Optional[Tuple[ir2.ExprType, ast.Return]],
                        check_always_returns: bool,
                        is_toplevel_in_function: bool,
                        next_stmt_line: int):

    if not is_toplevel_in_function:
        raise CompilationError(compilation_context, ast_node,
                               'try-except blocks are only supported at top-level in functions (not e.g. inside if-else statements).')

    if not ast_node.handlers:
        raise CompilationError(compilation_context, ast_node,
                               '"try" blocks must have an "except" clause.')
    # TODO: consider supporting this case too.
    if len(ast_node.handlers) > 1:
        raise CompilationError(compilation_context, ast_node.handlers[1],
                               '"try" blocks with multiple "except" clauses are not currently supported.')
    [handler] = ast_node.handlers

    body_compilation_context = compilation_context.create_child_context(first_enclosing_except_stmt_line=handler.lineno)
    body_stmts, body_first_return_stmt = statements_ast_to_ir2(ast_node.body,
                                                               body_compilation_context,
                                                               check_block_always_returns=check_always_returns,
                                                               previous_return_stmt=previous_return_stmt,
                                                               stmts_are_toplevel_in_function=False,
                                                               next_stmt_line=next_stmt_line)
    if not previous_return_stmt:
        previous_return_stmt = body_first_return_stmt

    if not (isinstance(handler, ast.ExceptHandler)
            and isinstance(handler.type, ast.Name)
            and isinstance(handler.type.ctx, ast.Load)
            and handler.name):
        raise CompilationError(compilation_context, handler,
                               '"except" clauses must be of the form: except SomeType as some_var')

    # TODO: consider adding support for this.
    if handler.type.id == 'Exception':
        raise CompilationError(compilation_context, handler.type,
                               'Catching all exceptions is not supported, you must catch a specific exception type.')

    caught_exception_type = type_declaration_ast_to_ir2_expression_type(handler.type, compilation_context)

    if ast_node.orelse:
        raise CompilationError(compilation_context, ast_node.orelse[0], '"else" clauses are not supported in try-except.')

    if ast_node.finalbody:
        raise CompilationError(compilation_context, ast_node.finalbody[0], '"finally" clauses are not supported.')

    except_body_compilation_context = compilation_context.create_child_context()
    except_body_compilation_context.add_symbol(name=handler.name,
                                               expr_type=caught_exception_type,
                                               definition_ast_node=handler,
                                               is_only_partially_defined=False,
                                               is_function_that_may_throw=False)
    except_body_stmts, except_body_first_return_stmt = statements_ast_to_ir2(handler.body,
                                                                             except_body_compilation_context,
                                                                             check_block_always_returns=check_always_returns,
                                                                             previous_return_stmt=previous_return_stmt,
                                                                             stmts_are_toplevel_in_function=False,
                                                                             next_stmt_line=next_stmt_line)
    if not previous_return_stmt:
        previous_return_stmt = except_body_first_return_stmt

    _join_definitions_in_branches(compilation_context,
                                  body_compilation_context,
                                  body_stmts,
                                  except_body_compilation_context,
                                  except_body_stmts)

    try_branch_first_nontrivial_stmt_line = compute_next_stmt_line_number_by_index([None, *ast_node.body], next_stmt_line)[0]
    except_branch_first_nontrivial_stmt_line = compute_next_stmt_line_number_by_index([None, *handler.body], next_stmt_line)[0]

    try_except_stmt = ir2.TryExcept(try_body=body_stmts,
                                    caught_exception_type=caught_exception_type,
                                    caught_exception_name=handler.name,
                                    except_body=except_body_stmts,
                                    try_branch=SourceBranch(compilation_context.filename,
                                                            ast_node.lineno,
                                                            try_branch_first_nontrivial_stmt_line),
                                    except_branch=SourceBranch(compilation_context.filename,
                                                               handler.lineno,
                                                               except_branch_first_nontrivial_stmt_line))

    return try_except_stmt, previous_return_stmt

def statements_ast_to_ir2(ast_nodes: List[ast.AST],
                          compilation_context: CompilationContext,
                          previous_return_stmt: Optional[Tuple[ir2.ExprType, ast.Return]],
                          check_block_always_returns: bool,
                          stmts_are_toplevel_in_function: bool,
                          next_stmt_line: int):
    assert ast_nodes

    next_stmt_line_number_by_index = compute_next_stmt_line_number_by_index(ast_nodes, next_stmt_line)

    statements = []
    first_return_stmt = None
    for index, statement_node in enumerate(ast_nodes):
        next_stmt_line = next_stmt_line_number_by_index[index]
        if get_return_type(statements).always_returns:
            raise CompilationError(compilation_context, statement_node, 'Unreachable statement.')

        check_stmt_always_returns = check_block_always_returns and statement_node is ast_nodes[-1]

        if isinstance(statement_node, ast.Assert):
            statements.append(assert_ast_to_ir2(statement_node, compilation_context, next_stmt_line))
        elif isinstance(statement_node, ast.Assign) or isinstance(statement_node, ast.AnnAssign) or isinstance(statement_node, ast.AugAssign):
            statements.append(assignment_ast_to_ir2(statement_node, compilation_context, next_stmt_line))
        elif isinstance(statement_node, ast.Return):
            return_stmt = return_stmt_ast_to_ir2(statement_node, compilation_context)
            if previous_return_stmt:
                previous_return_stmt_type, previous_return_stmt_ast_node = previous_return_stmt
                if return_stmt.expr.expr_type != previous_return_stmt_type:
                    raise CompilationError(compilation_context, statement_node,
                                           'Found return statement with different return type: %s instead of %s.' % (
                                               str(return_stmt.expr.expr_type), str(previous_return_stmt_type)),
                                           notes=[(previous_return_stmt_ast_node, 'A previous return statement returning a %s was here.' % (
                                               str(previous_return_stmt_type),))])
            if not first_return_stmt:
                first_return_stmt = (return_stmt.expr.expr_type, statement_node)
            if not previous_return_stmt:
                previous_return_stmt = first_return_stmt
            statements.append(return_stmt)
        elif isinstance(statement_node, ast.If):
            if_stmt, first_return_stmt_in_if = if_stmt_ast_to_ir2(statement_node,
                                                                  compilation_context,
                                                                  previous_return_stmt,
                                                                  check_stmt_always_returns,
                                                                  next_stmt_line)
            if not first_return_stmt:
                first_return_stmt = first_return_stmt_in_if
            if not previous_return_stmt:
                previous_return_stmt = first_return_stmt
            statements.append(if_stmt)
        elif isinstance(statement_node, ast.Raise):
            statements.append(raise_stmt_ast_to_ir2(statement_node, compilation_context))
        elif isinstance(statement_node, ast.Try):
            try_except_stmt, first_return_stmt_in_try_except = try_stmt_ast_to_ir2(statement_node,
                                                                                   compilation_context,
                                                                                   previous_return_stmt=previous_return_stmt,
                                                                                   check_always_returns=check_stmt_always_returns,
                                                                                   is_toplevel_in_function=stmts_are_toplevel_in_function,
                                                                                   next_stmt_line=next_stmt_line)
            if not first_return_stmt:
                first_return_stmt = first_return_stmt_in_try_except
            if not previous_return_stmt:
                previous_return_stmt = first_return_stmt
            statements.append(try_except_stmt)
        elif isinstance(statement_node, ast.Pass):
            statements.append(ir2.PassStmt(SourceBranch(compilation_context.filename,
                                                        statement_node.lineno,
                                                        next_stmt_line)))
        elif isinstance(statement_node, ast.Expr):
            statements.append(expression_stmt_to_ir2(statement_node, compilation_context, next_stmt_line))
        else:
            raise CompilationError(compilation_context, statement_node, 'Unsupported statement.')

    if check_block_always_returns and not get_return_type(statements).always_returns:
        raise CompilationError(compilation_context, ast_nodes[-1],
                               'Missing return statement.')

    return tuple(statements), first_return_stmt


def compute_next_stmt_line_number_by_index(ast_nodes: List[Optional[ast.AST]], next_stmt_line: int) -> List[Optional[int]]:
    next_stmt_line_number_by_index: List[Optional[int]] = [None] * len(ast_nodes)
    next_stmt_line_number = next_stmt_line
    for index, statement_node in reversed(list(enumerate(ast_nodes))):
        next_stmt_line_number_by_index[index] = next_stmt_line_number
        if statement_node is not None:
            next_stmt_line_number = statement_node.lineno
    return next_stmt_line_number_by_index

def function_def_ast_to_symbol_info(ast_node: ast.FunctionDef, compilation_context: CompilationContext):
    function_body_compilation_context = compilation_context.create_child_context(function_name=ast_node.name,
                                                                                 function_definition_line=ast_node.lineno)
    arg_types = []
    arg_names = []
    for arg in ast_node.args.args:
        if not arg.annotation:
            if arg.type_comment:
                raise CompilationError(compilation_context, arg, 'All function arguments must have a type annotation. Note that type comments are not supported.')
            else:
                raise CompilationError(compilation_context, arg, 'All function arguments must have a type annotation.')
        arg_type = type_declaration_ast_to_ir2_expression_type(arg.annotation, compilation_context)
        function_body_compilation_context.add_symbol(name=arg.arg,
                                                     expr_type=arg_type,
                                                     definition_ast_node=arg,
                                                     is_only_partially_defined=False,
                                                     is_function_that_may_throw=isinstance(arg_type, ir2.FunctionType))
        arg_types.append(arg_type)
        arg_names.append(arg.arg)
    if not arg_types:
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
        return_type = type_declaration_ast_to_ir2_expression_type(ast_node.returns, compilation_context)
    else:
        return_type = None

    return ast_node.name, tuple(arg_types), tuple(arg_names), return_type

def function_def_ast_to_ir2(ast_node: ast.FunctionDef, compilation_context: CompilationContext, next_stmt_line: int):
    function_body_compilation_context = compilation_context.create_child_context(function_name=ast_node.name,
                                                                                 function_definition_line=ast_node.lineno)
    args = []
    for arg in ast_node.args.args:
        arg_type = type_declaration_ast_to_ir2_expression_type(arg.annotation, compilation_context)
        function_body_compilation_context.add_symbol(name=arg.arg,
                                                     expr_type=arg_type,
                                                     definition_ast_node=arg,
                                                     is_only_partially_defined=False,
                                                     is_function_that_may_throw=isinstance(arg_type, ir2.FunctionType))
        args.append(ir2.FunctionArgDecl(expr_type=arg_type, name=arg.arg))

    statements, first_return_stmt = statements_ast_to_ir2(ast_node.body, function_body_compilation_context,
                                                          previous_return_stmt=None,
                                                          check_block_always_returns=True,
                                                          stmts_are_toplevel_in_function=True,
                                                          next_stmt_line=-ast_node.lineno)

    return_type = None
    first_return_stmt_ast_node = None
    if first_return_stmt:
        return_type, first_return_stmt_ast_node = first_return_stmt

    if ast_node.returns:
        declared_return_type = type_declaration_ast_to_ir2_expression_type(ast_node.returns, compilation_context)

        # first_return_stmt can be None if the function raises an exception instead of returning in all branches.
        if first_return_stmt:
            if declared_return_type != return_type:
                raise CompilationError(compilation_context, ast_node.returns,
                                       '%s declared %s as return type, but the actual return type was %s.' % (
                                           ast_node.name, str(declared_return_type), str(return_type)),
                                       notes=[(first_return_stmt_ast_node, 'A %s was returned here' % str(return_type))])

        return_type = declared_return_type

    if not first_return_stmt and not ast_node.returns:
        return_type = ir2.BottomType()

    first_nontrivial_stmt_line = compute_next_stmt_line_number_by_index([None, *ast_node.body], next_stmt_line)[0]

    return ir2.FunctionDefn(name=ast_node.name,
                            args=tuple(args),
                            body=(ir2.PassStmt(SourceBranch(compilation_context.filename,
                                                            -ast_node.lineno,
                                                            first_nontrivial_stmt_line)),
                                  *statements),
                            return_type=return_type)

def assert_ast_to_ir2(ast_node: ast.Assert, compilation_context: CompilationContext, next_stmt_line: int):
    expr = expression_ast_to_ir2(ast_node.test,
                                 compilation_context,
                                 in_match_pattern=False,
                                 check_var_reference=lambda ast_node: None,
                                 match_lambda_argument_names=set(),
                                 current_stmt_line=ast_node.lineno)

    if not isinstance(expr.expr_type, ir2.BoolType):
        raise CompilationError(compilation_context, ast_node.test,
                               'The value passed to assert must have type bool, but got a value with type %s.' % expr.expr_type)

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

    return ir2.Assert(expr=expr,
                      message=message,
                      source_branch=SourceBranch(compilation_context.filename,
                                                 ast_node.lineno,
                                                 next_stmt_line))

def assignment_ast_to_ir2(ast_node: Union[ast.Assign, ast.AnnAssign, ast.AugAssign],
                          compilation_context: CompilationContext,
                          next_stmt_line: int):
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
        # This is an "unpacking" assignment
        for lhs_elem_ast_node in target.elts:
            if not isinstance(lhs_elem_ast_node, ast.Name):
                raise CompilationError(compilation_context, lhs_elem_ast_node,
                                       'This kind of unpacking assignment is not supported. Only unpacking assignments of the form x,y=... or [x,y]=... are supported.')

        expr = expression_ast_to_ir2(ast_node.value,
                                     compilation_context,
                                     in_match_pattern=False,
                                     check_var_reference=lambda ast_node: None,
                                     match_lambda_argument_names=set(),
                                     current_stmt_line=ast_node.lineno)
        if not isinstance(expr.expr_type, ir2.ListType):
            raise CompilationError(compilation_context, ast_node,
                                   'Unpacking requires a list on the RHS, but the value on the RHS has type %s' % str(expr.expr_type))
        elem_type = expr.expr_type.elem_type

        var_refs = []
        for lhs_elem_ast_node in target.elts:
            lhs_var_name = lhs_elem_ast_node.id
            if lhs_var_name == '_':
                lhs_var_name = next(compilation_context.identifier_generator)
            compilation_context.add_symbol(name=lhs_var_name,
                                           expr_type=elem_type,
                                           definition_ast_node=lhs_elem_ast_node,
                                           is_only_partially_defined=False,
                                           is_function_that_may_throw=isinstance(elem_type, ir2.FunctionType))

            var_ref = ir2.VarReference(expr_type=elem_type,
                                       name=lhs_var_name,
                                       is_global_function=False,
                                       is_function_that_may_throw=isinstance(elem_type, ir2.FunctionType))
            var_refs.append(var_ref)

        first_line_number = ast_node.lineno
        message = 'unexpected number of elements in the TMPPy list unpacking at:\n{filename}:{first_line_number}: {line}'.format(
            filename=compilation_context.filename,
            first_line_number=first_line_number,
            line=compilation_context.source_lines[first_line_number - 1])
        message = message.replace('\\', '\\\\').replace('"', '\"').replace('\n', '\\n')

        return ir2.UnpackingAssignment(lhs_list=tuple(var_refs),
                                       rhs=expr,
                                       error_message=message,
                                       source_branch=SourceBranch(compilation_context.filename,
                                                                  ast_node.lineno,
                                                                  next_stmt_line))

    elif isinstance(target, ast.Name):
        # This is a "normal" assignment
        expr = expression_ast_to_ir2(ast_node.value,
                                     compilation_context,
                                     in_match_pattern=False,
                                     check_var_reference=lambda ast_node: None,
                                     match_lambda_argument_names=set(),
                                     current_stmt_line=ast_node.lineno)

        lhs_var_name = target.id
        if lhs_var_name == '_':
            lhs_var_name = next(compilation_context.identifier_generator)
        compilation_context.add_symbol(name=lhs_var_name,
                                       expr_type=expr.expr_type,
                                       definition_ast_node=target,
                                       is_only_partially_defined=False,
                                       is_function_that_may_throw=isinstance(expr.expr_type, ir2.FunctionType))

        return ir2.Assignment(lhs=ir2.VarReference(expr_type=expr.expr_type,
                                                   name=lhs_var_name,
                                                   is_global_function=False,
                                                   is_function_that_may_throw=isinstance(expr.expr_type, ir2.FunctionType)),
                              rhs=expr,
                              source_branch=SourceBranch(compilation_context.filename,
                                                         ast_node.lineno,
                                                         next_stmt_line))
    else:
        raise CompilationError(compilation_context, ast_node, 'Assignment not supported.')

def expression_stmt_to_ir2(stmt: ast.Expr, compilation_context: CompilationContext, next_stmt_line: int):
    expr = expression_ast_to_ir2(stmt.value,
                                 compilation_context,
                                 in_match_pattern=False,
                                 check_var_reference=lambda ast_node: None,
                                 match_lambda_argument_names=set(),
                                 current_stmt_line=stmt.lineno)

    lhs_var_name = next(compilation_context.identifier_generator)
    compilation_context.add_symbol(name=lhs_var_name,
                                   expr_type=expr.expr_type,
                                   definition_ast_node=stmt,
                                   is_only_partially_defined=False,
                                   is_function_that_may_throw=isinstance(expr.expr_type, ir2.FunctionType))

    return ir2.Assignment(lhs=ir2.VarReference(expr_type=expr.expr_type,
                                               name=lhs_var_name,
                                               is_global_function=False,
                                               is_function_that_may_throw=isinstance(expr.expr_type, ir2.FunctionType)),
                          rhs=expr,
                          source_branch=SourceBranch(compilation_context.filename,
                                                     stmt.lineno,
                                                     next_stmt_line))

def int_comparison_ast_to_ir2(lhs_ast_node: ast.AST,
                              rhs_ast_node: ast.AST,
                              op: str,
                              compilation_context: CompilationContext,
                              in_match_pattern: bool,
                              check_var_reference: Callable[[ast.Name], None],
                              current_stmt_line: int):
    lhs = expression_ast_to_ir2(lhs_ast_node,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names=set(),
                                current_stmt_line=current_stmt_line)
    rhs = expression_ast_to_ir2(rhs_ast_node,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names=set(),
                                current_stmt_line=current_stmt_line)

    if lhs.expr_type != ir2.IntType():
        raise CompilationError(compilation_context, lhs_ast_node,
                               'The "%s" operator is only supported for ints, but this value has type %s.' % (op, str(lhs.expr_type)))
    if rhs.expr_type != ir2.IntType():
        raise CompilationError(compilation_context, rhs_ast_node,
                               'The "%s" operator is only supported for ints, but this value has type %s.' % (op, str(rhs.expr_type)))

    return ir2.IntComparisonExpr(lhs=lhs, rhs=rhs, op=op)

def compare_ast_to_ir2(ast_node: ast.Compare,
                       compilation_context: CompilationContext,
                       in_match_pattern: bool,
                       check_var_reference: Callable[[ast.Name], None],
                       match_lambda_argument_names: Set[str],
                       current_stmt_line: int):
    if len(ast_node.ops) != 1 or len(ast_node.comparators) != 1:
        raise CompilationError(compilation_context, ast_node, 'Comparison not supported.')  # pragma: no cover

    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'Comparisons are not allowed in match patterns')

    lhs = ast_node.left
    op = ast_node.ops[0]
    rhs = ast_node.comparators[0]

    if isinstance(op, ast.Eq):
        return eq_ast_to_ir2(lhs, rhs, compilation_context, in_match_pattern, check_var_reference, current_stmt_line)
    elif isinstance(op, ast.NotEq):
        return not_eq_ast_to_ir2(lhs, rhs, compilation_context, in_match_pattern, check_var_reference, current_stmt_line)
    elif isinstance(op, ast.In):
        return in_ast_to_ir2(lhs, rhs, compilation_context, in_match_pattern, check_var_reference, current_stmt_line)
    elif isinstance(op, ast.Lt):
        return int_comparison_ast_to_ir2(lhs, rhs, '<', compilation_context, in_match_pattern, check_var_reference, current_stmt_line)
    elif isinstance(op, ast.LtE):
        return int_comparison_ast_to_ir2(lhs, rhs, '<=', compilation_context, in_match_pattern, check_var_reference, current_stmt_line)
    elif isinstance(op, ast.Gt):
        return int_comparison_ast_to_ir2(lhs, rhs, '>', compilation_context, in_match_pattern, check_var_reference, current_stmt_line)
    elif isinstance(op, ast.GtE):
        return int_comparison_ast_to_ir2(lhs, rhs, '>=', compilation_context, in_match_pattern, check_var_reference, current_stmt_line)
    else:
        raise CompilationError(compilation_context, ast_node, 'Comparison not supported.')  # pragma: no cover

def attribute_expression_ast_to_ir2(ast_node: ast.Attribute,
                                    compilation_context: CompilationContext,
                                    in_match_pattern: bool,
                                    check_var_reference: Callable[[ast.Name], None],
                                    match_lambda_argument_names: Set[str],
                                    current_stmt_line: int):
    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'Attribute access is not allowed in match patterns')

    value_expr = expression_ast_to_ir2(ast_node.value,
                                       compilation_context,
                                       in_match_pattern,
                                       check_var_reference,
                                       match_lambda_argument_names,
                                       current_stmt_line)
    if isinstance(value_expr.expr_type, ir2.TypeType):
        return ir2.AttributeAccessExpr(expr=value_expr,
                                       attribute_name=ast_node.attr,
                                       expr_type=ir2.TypeType())
    elif isinstance(value_expr.expr_type, ir2.CustomType):
        for arg in value_expr.expr_type.arg_types:
            if arg.name == ast_node.attr:
                return ir2.AttributeAccessExpr(expr=value_expr,
                                               attribute_name=ast_node.attr,
                                               expr_type=arg.expr_type)
        else:
            lookup_result = compilation_context.get_type_symbol_definition(value_expr.expr_type.name)
            assert lookup_result
            raise CompilationError(compilation_context, ast_node.value,
                                   'Values of type "%s" don\'t have the attribute "%s". The available attributes for this type are: {"%s"}.' % (
                                       str(value_expr.expr_type), ast_node.attr, '", "'.join(sorted(arg.name
                                                                                               for arg in value_expr.expr_type.arg_types))),
                                   notes=[(lookup_result.ast_node, '%s was defined here.' % str(value_expr.expr_type))])
    else:
        raise CompilationError(compilation_context, ast_node.value,
                               'Attribute access is not supported for values of type %s.' % str(value_expr.expr_type))

def number_literal_expression_ast_to_ir2(ast_node: ast.Num,
                                         compilation_context: CompilationContext,
                                         in_match_pattern: bool,
                                         check_var_reference: Callable[[ast.Name], None],
                                         match_lambda_argument_names: Set[str],
                                         positive: bool):
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
    return ir2.IntLiteral(value=n)

def and_expression_ast_to_ir2(ast_node: ast.BoolOp,
                              compilation_context: CompilationContext,
                              in_match_pattern: bool,
                              check_var_reference: Callable[[ast.Name], None],
                              match_lambda_argument_names: Set[str],
                              current_stmt_line: int):
    assert isinstance(ast_node.op, ast.And)

    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'The "and" operator is not allowed in match patterns')

    if not compilation_context.current_function_name:
        raise CompilationError(compilation_context, ast_node,
                               'The "and" operator is only supported in functions, not at toplevel.')

    assert len(ast_node.values) >= 2

    exprs = []
    for expr_ast_node in ast_node.values:
        expr = expression_ast_to_ir2(expr_ast_node,
                                     compilation_context,
                                     in_match_pattern,
                                     check_var_reference,
                                     match_lambda_argument_names,
                                     current_stmt_line)
        if expr.expr_type != ir2.BoolType():
            raise CompilationError(compilation_context, expr_ast_node,
                                   'The "and" operator is only supported for booleans, but this value has type %s.' % str(expr.expr_type))
        exprs.append(expr)

    final_expr = exprs[-1]
    for expr in reversed(exprs[:-1]):
        final_expr = ir2.AndExpr(lhs=expr, rhs=final_expr)

    return final_expr

def or_expression_ast_to_ir2(ast_node: ast.BoolOp,
                             compilation_context: CompilationContext,
                             in_match_pattern: bool,
                             check_var_reference: Callable[[ast.Name], None],
                             match_lambda_argument_names: Set[str],
                             current_stmt_line: int):
    assert isinstance(ast_node.op, ast.Or)

    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'The "or" operator is not allowed in match patterns')

    if not compilation_context.current_function_name:
        raise CompilationError(compilation_context, ast_node,
                               'The "or" operator is only supported in functions, not at toplevel.')

    assert len(ast_node.values) >= 2

    exprs = []
    for expr_ast_node in ast_node.values:
        expr = expression_ast_to_ir2(expr_ast_node,
                                     compilation_context,
                                     in_match_pattern,
                                     check_var_reference,
                                     match_lambda_argument_names,
                                     current_stmt_line)
        if expr.expr_type != ir2.BoolType():
            raise CompilationError(compilation_context, expr_ast_node,
                                   'The "or" operator is only supported for booleans, but this value has type %s.' % str(expr.expr_type))
        exprs.append(expr)

    final_expr = exprs[-1]
    for expr in reversed(exprs[:-1]):
        final_expr = ir2.OrExpr(lhs=expr, rhs=final_expr)

    return final_expr

def not_expression_ast_to_ir2(ast_node: ast.UnaryOp,
                              compilation_context: CompilationContext,
                              in_match_pattern: bool,
                              check_var_reference: Callable[[ast.Name], None],
                              match_lambda_argument_names: Set[str],
                              current_stmt_line: int):
    assert isinstance(ast_node.op, ast.Not)

    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'The "not" operator is not allowed in match patterns')

    expr = expression_ast_to_ir2(ast_node.operand,
                                 compilation_context,
                                 in_match_pattern,
                                 check_var_reference,
                                 match_lambda_argument_names,
                                 current_stmt_line)

    if expr.expr_type != ir2.BoolType():
        raise CompilationError(compilation_context, ast_node.operand,
                               'The "not" operator is only supported for booleans, but this value has type %s.' % str(expr.expr_type))

    return ir2.NotExpr(expr=expr)

def unary_minus_expression_ast_to_ir2(ast_node: ast.UnaryOp,
                                      compilation_context: CompilationContext,
                                      in_match_pattern: bool,
                                      check_var_reference: Callable[[ast.Name], None],
                                      match_lambda_argument_names: Set[str],
                                      current_stmt_line: int):
    assert isinstance(ast_node.op, ast.USub)

    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'The "-" operator is not allowed in match patterns')

    expr = expression_ast_to_ir2(ast_node.operand,
                                 compilation_context,
                                 in_match_pattern,
                                 check_var_reference,
                                 match_lambda_argument_names,
                                 current_stmt_line)

    if expr.expr_type != ir2.IntType():
        raise CompilationError(compilation_context, ast_node.operand,
                               'The "-" operator is only supported for ints, but this value has type %s.' % str(expr.expr_type))

    return ir2.IntUnaryMinusExpr(expr=expr)

def int_binary_op_expression_ast_to_ir2(ast_node: ast.BinOp,
                                        op: str,
                                        compilation_context: CompilationContext,
                                        in_match_pattern: bool,
                                        check_var_reference: Callable[[ast.Name], None],
                                        match_lambda_argument_names: Set[str],
                                        current_stmt_line: int):
    lhs = expression_ast_to_ir2(ast_node.left,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names,
                                current_stmt_line)
    rhs = expression_ast_to_ir2(ast_node.right,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names,
                                current_stmt_line)

    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'The "%s" operator is not allowed in match patterns' % op)

    if lhs.expr_type != ir2.IntType():
        raise CompilationError(compilation_context, ast_node.left,
                               'The "%s" operator is only supported for ints, but this value has type %s.' % (op, str(lhs.expr_type)))

    if rhs.expr_type != ir2.IntType():
        raise CompilationError(compilation_context, ast_node.right,
                               'The "%s" operator is only supported for ints, but this value has type %s.' % (op, str(rhs.expr_type)))

    return ir2.IntBinaryOpExpr(lhs=lhs, rhs=rhs, op=op)

def list_comprehension_ast_to_ir2(ast_node: ast.ListComp,
                                  compilation_context: CompilationContext,
                                  in_match_pattern: bool,
                                  check_var_reference: Callable[[ast.Name], None],
                                  match_lambda_argument_names: Set[str],
                                  current_stmt_line: int):
    assert ast_node.generators
    if len(ast_node.generators) > 1:
        raise CompilationError(compilation_context, ast_node.generators[1].target,
                               'List comprehensions with multiple "for" clauses are not currently supported.')

    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'List comprehensions are not allowed in match patterns')

    [generator] = ast_node.generators
    if generator.ifs:
        raise CompilationError(compilation_context, generator.ifs[0],
                               '"if" clauses in list comprehensions are not currently supported.')
    if not isinstance(generator.target, ast.Name):
        raise CompilationError(compilation_context, generator.target,
                               'Only list comprehensions of the form [... for var_name in ...] are supported.')

    list_expr = expression_ast_to_ir2(generator.iter,
                                      compilation_context,
                                      in_match_pattern,
                                      check_var_reference,
                                      match_lambda_argument_names,
                                      current_stmt_line)
    if not isinstance(list_expr.expr_type, ir2.ListType):
        notes = []
        if isinstance(list_expr, ir2.VarReference):
            lookup_result = compilation_context.get_symbol_definition(list_expr.name)
            assert lookup_result
            notes.append((lookup_result.ast_node, '%s was defined here' % list_expr.name))
        raise CompilationError(compilation_context, ast_node.generators[0].target,
                               'The RHS of a list comprehension should be a list, but this value has type "%s".' % str(list_expr.expr_type),
                               notes=notes)

    child_context = compilation_context.create_child_context()
    child_context.add_symbol(name=generator.target.id,
                             expr_type=list_expr.expr_type.elem_type,
                             definition_ast_node=generator.target,
                             is_only_partially_defined=False,
                             is_function_that_may_throw=False)
    result_elem_expr = expression_ast_to_ir2(ast_node.elt,
                                             child_context,
                                             in_match_pattern,
                                             check_var_reference,
                                             match_lambda_argument_names,
                                             current_stmt_line)

    if isinstance(result_elem_expr.expr_type, ir2.FunctionType):
        raise CompilationError(compilation_context, ast_node,
                               'Creating lists of functions is not supported. The elements of this list have type: %s' % str(result_elem_expr.expr_type))

    return ir2.ListComprehension(list_expr=list_expr,
                                 loop_var=ir2.VarReference(name=generator.target.id,
                                                           expr_type=list_expr.expr_type.elem_type,
                                                           is_global_function=False,
                                                           is_function_that_may_throw=False),
                                 result_elem_expr=result_elem_expr,
                                 loop_body_start_branch=SourceBranch(compilation_context.filename,
                                                                     current_stmt_line,
                                                                     -ast_node.elt.lineno),
                                 loop_exit_branch=SourceBranch(compilation_context.filename,
                                                               -ast_node.elt.lineno,
                                                               current_stmt_line))

def set_comprehension_ast_to_ir2(ast_node: ast.SetComp,
                                 compilation_context: CompilationContext,
                                 in_match_pattern: bool,
                                 check_var_reference: Callable[[ast.Name], None],
                                 match_lambda_argument_names: Set[str],
                                 current_stmt_line: int):
    assert ast_node.generators
    if len(ast_node.generators) > 1:
        raise CompilationError(compilation_context, ast_node.generators[1].target,
                               'Set comprehensions with multiple "for" clauses are not currently supported.')

    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'Set comprehensions are not allowed in match patterns')

    [generator] = ast_node.generators
    if generator.ifs:
        raise CompilationError(compilation_context, generator.ifs[0],
                               '"if" clauses in set comprehensions are not currently supported.')
    if not isinstance(generator.target, ast.Name):
        raise CompilationError(compilation_context, generator.target,
                               'Only set comprehensions of the form {... for var_name in ...} are supported.')

    set_expr = expression_ast_to_ir2(generator.iter,
                                     compilation_context,
                                     in_match_pattern,
                                     check_var_reference,
                                     match_lambda_argument_names,
                                     current_stmt_line)
    if not isinstance(set_expr.expr_type, ir2.SetType):
        notes = []
        if isinstance(set_expr, ir2.VarReference):
            lookup_result = compilation_context.get_symbol_definition(set_expr.name)
            assert lookup_result
            notes.append((lookup_result.ast_node, '%s was defined here' % set_expr.name))
        raise CompilationError(compilation_context, ast_node.generators[0].target,
                               'The RHS of a set comprehension should be a set, but this value has type "%s".' % str(set_expr.expr_type),
                               notes=notes)

    child_context = compilation_context.create_child_context()
    child_context.add_symbol(name=generator.target.id,
                             expr_type=set_expr.expr_type.elem_type,
                             definition_ast_node=generator.target,
                             is_only_partially_defined=False,
                             is_function_that_may_throw=False)
    result_elem_expr = expression_ast_to_ir2(ast_node.elt,
                                             child_context,
                                             in_match_pattern,
                                             check_var_reference,
                                             match_lambda_argument_names,
                                             current_stmt_line)

    if isinstance(result_elem_expr.expr_type, ir2.FunctionType):
        raise CompilationError(compilation_context, ast_node,
                               'Creating sets of functions is not supported. The elements of this set have type: %s' % str(result_elem_expr.expr_type))

    return ir2.SetComprehension(set_expr=set_expr,
                                loop_var=ir2.VarReference(name=generator.target.id,
                                                          expr_type=set_expr.expr_type.elem_type,
                                                          is_global_function=False,
                                                          is_function_that_may_throw=False),
                                result_elem_expr=result_elem_expr,
                                loop_body_start_branch=SourceBranch(compilation_context.filename,
                                                                    current_stmt_line,
                                                                    -ast_node.elt.lineno),
                                loop_exit_branch=SourceBranch(compilation_context.filename,
                                                              -ast_node.elt.lineno,
                                                              current_stmt_line))


def add_expression_ast_to_ir2(ast_node: ast.BinOp,
                              compilation_context: CompilationContext,
                              in_match_pattern: bool,
                              check_var_reference: Callable[[ast.Name], None],
                              match_lambda_argument_names: Set[str],
                              current_stmt_line: int):
    lhs = expression_ast_to_ir2(ast_node.left,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names,
                                current_stmt_line)
    rhs = expression_ast_to_ir2(ast_node.right,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names,
                                current_stmt_line)

    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'The "+" operator is not allowed in match patterns')

    if not isinstance(lhs.expr_type, (ir2.IntType, ir2.ListType)):
        raise CompilationError(compilation_context, ast_node.left,
                               'The "+" operator is only supported for ints and lists, but this value has type %s.' % str(lhs.expr_type))

    if not isinstance(rhs.expr_type, (ir2.IntType, ir2.ListType)):
        raise CompilationError(compilation_context, ast_node.right,
                               'The "+" operator is only supported for ints and lists, but this value has type %s.' % str(rhs.expr_type))

    if lhs.expr_type != rhs.expr_type:
        raise CompilationError(compilation_context, ast_node.left,
                               'Type mismatch: the LHS of "+" has type %s but the RHS has type %s.' % (str(lhs.expr_type), str(rhs.expr_type)))

    if lhs.expr_type == ir2.IntType():
        return ir2.IntBinaryOpExpr(lhs=lhs, rhs=rhs, op='+')
    else:
        return ir2.ListConcatExpr(lhs=lhs, rhs=rhs)


def expression_ast_to_ir2(ast_node: ast.AST,
                          compilation_context: CompilationContext,
                          in_match_pattern: bool,
                          check_var_reference: Callable[[ast.Name], None],
                          match_lambda_argument_names: Set[str],
                          current_stmt_line: int) -> ir2.Expr:
    if isinstance(ast_node, ast.NameConstant):
        return name_constant_ast_to_ir2(ast_node,
                                        compilation_context,
                                        in_match_pattern,
                                        check_var_reference,
                                        match_lambda_argument_names)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Name) and ast_node.func.id == 'Type':
        return atomic_type_literal_ast_to_ir2(ast_node,
                                              compilation_context,
                                              in_match_pattern,
                                              check_var_reference,
                                              match_lambda_argument_names)
    elif (isinstance(ast_node, ast.Call)
          and isinstance(ast_node.func, ast.Attribute)
          and isinstance(ast_node.func.value, ast.Name) and ast_node.func.value.id == 'Type'):
        return type_factory_method_ast_to_ir2(ast_node,
                                              compilation_context,
                                              in_match_pattern,
                                              check_var_reference,
                                              match_lambda_argument_names,
                                              current_stmt_line)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Name) and ast_node.func.id == 'empty_list':
        return empty_list_literal_ast_to_ir2(ast_node,
                                             compilation_context,
                                             in_match_pattern,
                                             check_var_reference,
                                             match_lambda_argument_names)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Name) and ast_node.func.id == 'empty_set':
        return empty_set_literal_ast_to_ir2(ast_node,
                                            compilation_context,
                                            in_match_pattern,
                                            check_var_reference,
                                            match_lambda_argument_names)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Name) and ast_node.func.id == 'sum':
        return int_iterable_sum_expr_ast_to_ir2(ast_node,
                                                compilation_context,
                                                in_match_pattern,
                                                check_var_reference,
                                                match_lambda_argument_names,
                                                current_stmt_line)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Name) and ast_node.func.id == 'all':
        return bool_iterable_all_expr_ast_to_ir2(ast_node,
                                                 compilation_context,
                                                 in_match_pattern,
                                                 check_var_reference,
                                                 current_stmt_line)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Name) and ast_node.func.id == 'any':
        return bool_iterable_any_expr_ast_to_ir2(ast_node,
                                                 compilation_context,
                                                 in_match_pattern,
                                                 check_var_reference,
                                                 current_stmt_line)
    elif isinstance(ast_node, ast.Call) and isinstance(ast_node.func, ast.Call) and isinstance(ast_node.func.func, ast.Name) and ast_node.func.func.id == 'match':
        return match_expression_ast_to_ir2(ast_node,
                                           compilation_context,
                                           in_match_pattern,
                                           check_var_reference,
                                           match_lambda_argument_names,
                                           current_stmt_line)
    elif isinstance(ast_node, ast.Call):
        return function_call_ast_to_ir2(ast_node,
                                        compilation_context,
                                        in_match_pattern,
                                        check_var_reference,
                                        match_lambda_argument_names,
                                        current_stmt_line)
    elif isinstance(ast_node, ast.Compare):
        return compare_ast_to_ir2(ast_node,
                                  compilation_context,
                                  in_match_pattern,
                                  check_var_reference,
                                  match_lambda_argument_names,
                                  current_stmt_line)
    elif isinstance(ast_node, ast.Name) and isinstance(ast_node.ctx, ast.Load):
        return var_reference_ast_to_ir2(ast_node,
                                        compilation_context,
                                        in_match_pattern,
                                        check_var_reference,
                                        match_lambda_argument_names)
    elif isinstance(ast_node, ast.List) and isinstance(ast_node.ctx, ast.Load):
        return list_expression_ast_to_ir2(ast_node,
                                          compilation_context,
                                          in_match_pattern,
                                          check_var_reference,
                                          match_lambda_argument_names,
                                          current_stmt_line)
    elif isinstance(ast_node, ast.Set):
        return set_expression_ast_to_ir2(ast_node,
                                         compilation_context,
                                         in_match_pattern,
                                         check_var_reference,
                                         match_lambda_argument_names,
                                         current_stmt_line)
    elif isinstance(ast_node, ast.Attribute) and isinstance(ast_node.ctx, ast.Load):
        return attribute_expression_ast_to_ir2(ast_node,
                                               compilation_context,
                                               in_match_pattern,
                                               check_var_reference,
                                               match_lambda_argument_names,
                                               current_stmt_line)
    elif isinstance(ast_node, ast.Num):
        return number_literal_expression_ast_to_ir2(ast_node,
                                                    compilation_context,
                                                    in_match_pattern,
                                                    check_var_reference,
                                                    match_lambda_argument_names,
                                                    positive=True)
    elif isinstance(ast_node, ast.UnaryOp) and isinstance(ast_node.op, ast.USub) and isinstance(ast_node.operand, ast.Num):
        return number_literal_expression_ast_to_ir2(ast_node.operand,
                                                    compilation_context,
                                                    in_match_pattern,
                                                    check_var_reference,
                                                    match_lambda_argument_names,
                                                    positive=False)
    elif isinstance(ast_node, ast.BoolOp) and isinstance(ast_node.op, ast.And):
        return and_expression_ast_to_ir2(ast_node,
                                         compilation_context,
                                         in_match_pattern,
                                         check_var_reference,
                                         match_lambda_argument_names,
                                         current_stmt_line)
    elif isinstance(ast_node, ast.BoolOp) and isinstance(ast_node.op, ast.Or):
        return or_expression_ast_to_ir2(ast_node,
                                        compilation_context,
                                        in_match_pattern,
                                        check_var_reference,
                                        match_lambda_argument_names,
                                        current_stmt_line)
    elif isinstance(ast_node, ast.UnaryOp) and isinstance(ast_node.op, ast.Not):
        return not_expression_ast_to_ir2(ast_node,
                                         compilation_context,
                                         in_match_pattern,
                                         check_var_reference,
                                         match_lambda_argument_names,
                                         current_stmt_line)
    elif isinstance(ast_node, ast.UnaryOp) and isinstance(ast_node.op, ast.USub):
        return unary_minus_expression_ast_to_ir2(ast_node,
                                                 compilation_context,
                                                 in_match_pattern,
                                                 check_var_reference,
                                                 match_lambda_argument_names,
                                                 current_stmt_line)
    elif isinstance(ast_node, ast.BinOp) and isinstance(ast_node.op, ast.Add):
        return add_expression_ast_to_ir2(ast_node,
                                         compilation_context,
                                         in_match_pattern,
                                         check_var_reference,
                                         match_lambda_argument_names,
                                         current_stmt_line)
    elif isinstance(ast_node, ast.BinOp) and isinstance(ast_node.op, ast.Sub):
        return int_binary_op_expression_ast_to_ir2(ast_node,
                                                   '-',
                                                   compilation_context,
                                                   in_match_pattern,
                                                   check_var_reference,
                                                   match_lambda_argument_names,
                                                   current_stmt_line)
    elif isinstance(ast_node, ast.BinOp) and isinstance(ast_node.op, ast.Mult):
        return int_binary_op_expression_ast_to_ir2(ast_node,
                                                   '*',
                                                   compilation_context,
                                                   in_match_pattern,
                                                   check_var_reference,
                                                   match_lambda_argument_names,
                                                   current_stmt_line)
    elif isinstance(ast_node, ast.BinOp) and isinstance(ast_node.op, ast.FloorDiv):
        return int_binary_op_expression_ast_to_ir2(ast_node,
                                                   '//',
                                                   compilation_context,
                                                   in_match_pattern,
                                                   check_var_reference,
                                                   match_lambda_argument_names,
                                                   current_stmt_line)
    elif isinstance(ast_node, ast.BinOp) and isinstance(ast_node.op, ast.Mod):
        return int_binary_op_expression_ast_to_ir2(ast_node,
                                                   '%',
                                                   compilation_context,
                                                   in_match_pattern,
                                                   check_var_reference,
                                                   match_lambda_argument_names,
                                                   current_stmt_line)
    elif isinstance(ast_node, ast.ListComp):
        return list_comprehension_ast_to_ir2(ast_node,
                                             compilation_context,
                                             in_match_pattern,
                                             check_var_reference,
                                             match_lambda_argument_names,
                                             current_stmt_line)
    elif isinstance(ast_node, ast.SetComp):
        return set_comprehension_ast_to_ir2(ast_node,
                                            compilation_context,
                                            in_match_pattern,
                                            check_var_reference,
                                            match_lambda_argument_names,
                                            current_stmt_line)
    else:
        # raise CompilationError(compilation_context, ast_node, 'This kind of expression is not supported: %s' % ast_to_string(ast_node))
        raise CompilationError(compilation_context, ast_node, 'This kind of expression is not supported.')  # pragma: no cover

def name_constant_ast_to_ir2(ast_node: ast.NameConstant,
                             compilation_context: CompilationContext,
                             in_match_pattern: bool,
                             check_var_reference: Callable[[ast.Name], None],
                             match_lambda_argument_names: Set[str]):
    if isinstance(ast_node.value, bool):
        return ir2.BoolLiteral(value=ast_node.value)
    else:
        raise CompilationError(compilation_context, ast_node, 'NameConstant not supported: ' + str(ast_node.value))  # pragma: no cover

_check_atomic_type_regex = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)*')

def _check_atomic_type(ast_node: ast.Str, compilation_context: CompilationContext):
    if not _check_atomic_type_regex.fullmatch(ast_node.s):
        raise CompilationError(compilation_context, ast_node,
                               'Invalid atomic type. Atomic types should be C++ identifiers (possibly namespace-qualified).')

def atomic_type_literal_ast_to_ir2(ast_node: ast.Call,
                                   compilation_context: CompilationContext,
                                   in_match_pattern: bool,
                                   check_var_reference: Callable[[ast.Name], None],
                                   match_lambda_argument_names: Set[str]):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value,
                               'Keyword arguments are not supported in Type()')

    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, 'Type() takes 1 argument. Got: %s' % len(ast_node.args))
    [arg] = ast_node.args
    if not isinstance(arg, ast.Str):
        raise CompilationError(compilation_context, arg, 'The argument passed to Type should be a string constant.')
    _check_atomic_type(arg, compilation_context)
    return ir2.AtomicTypeLiteral(cpp_type=arg.s)

def _extract_single_type_expr_arg(ast_node: ast.Call,
                                  called_fun_name: str,
                                  compilation_context: CompilationContext,
                                  in_match_pattern: bool,
                                  check_var_reference: Callable[[ast.Name], None],
                                  match_lambda_argument_names: Set[str],
                                  current_stmt_line: int):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value,
                               'Keyword arguments are not supported in %s()' % called_fun_name)

    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, '%s() takes 1 argument. Got: %s' % (called_fun_name, len(ast_node.args)))
    [arg] = ast_node.args

    arg_ir = expression_ast_to_ir2(arg,
                                   compilation_context,
                                   in_match_pattern,
                                   check_var_reference,
                                   match_lambda_argument_names,
                                   current_stmt_line)
    if arg_ir.expr_type != ir2.TypeType():
        raise CompilationError(compilation_context, arg, 'The argument passed to %s() should have type Type, but was: %s' % (called_fun_name, str(arg_ir.expr_type)))
    return arg_ir

def type_pointer_expr_ast_to_ir2(ast_node: ast.Call,
                                 compilation_context: CompilationContext,
                                 in_match_pattern: bool,
                                 check_var_reference: Callable[[ast.Name], None],
                                 match_lambda_argument_names: Set[str],
                                 current_stmt_line: int):
    return ir2.PointerTypeExpr(_extract_single_type_expr_arg(ast_node,
                                                             'Type.pointer',
                                                             compilation_context,
                                                             in_match_pattern,
                                                             check_var_reference,
                                                             match_lambda_argument_names,
                                                             current_stmt_line))

def type_reference_expr_ast_to_ir2(ast_node: ast.Call,
                                   compilation_context: CompilationContext,
                                   in_match_pattern: bool,
                                   check_var_reference: Callable[[ast.Name], None],
                                   match_lambda_argument_names: Set[str],
                                   current_stmt_line: int):
    return ir2.ReferenceTypeExpr(_extract_single_type_expr_arg(ast_node,
                                                               'Type.reference',
                                                               compilation_context,
                                                               in_match_pattern,
                                                               check_var_reference,
                                                               match_lambda_argument_names,
                                                               current_stmt_line))

def type_rvalue_reference_expr_ast_to_ir2(ast_node: ast.Call,
                                          compilation_context: CompilationContext,
                                          in_match_pattern: bool,
                                          check_var_reference: Callable[[ast.Name], None],
                                          match_lambda_argument_names: Set[str],
                                          current_stmt_line: int):
    return ir2.RvalueReferenceTypeExpr(_extract_single_type_expr_arg(ast_node,
                                                                     'Type.rvalue_reference',
                                                                     compilation_context,
                                                                     in_match_pattern,
                                                                     check_var_reference,
                                                                     match_lambda_argument_names,
                                                                     current_stmt_line))

def const_type_expr_ast_to_ir2(ast_node: ast.Call,
                               compilation_context: CompilationContext,
                               in_match_pattern: bool,
                               check_var_reference: Callable[[ast.Name], None],
                               match_lambda_argument_names: Set[str],
                               current_stmt_line: int):
    return ir2.ConstTypeExpr(_extract_single_type_expr_arg(ast_node,
                                                           'Type.const',
                                                           compilation_context,
                                                           in_match_pattern,
                                                           check_var_reference,
                                                           match_lambda_argument_names,
                                                           current_stmt_line))

def type_array_expr_ast_to_ir2(ast_node: ast.Call,
                               compilation_context: CompilationContext,
                               in_match_pattern: bool,
                               check_var_reference: Callable[[ast.Name], None],
                               match_lambda_argument_names: Set[str],
                               current_stmt_line: int):
    return ir2.ArrayTypeExpr(_extract_single_type_expr_arg(ast_node,
                                                           'Type.array',
                                                           compilation_context,
                                                           in_match_pattern,
                                                           check_var_reference,
                                                           match_lambda_argument_names,
                                                           current_stmt_line))

def function_type_expr_ast_to_ir2(ast_node: ast.Call,
                                  compilation_context: CompilationContext,
                                  in_match_pattern: bool,
                                  check_var_reference: Callable[[ast.Name], None],
                                  match_lambda_argument_names: Set[str],
                                  current_stmt_line: int):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value,
                               'Keyword arguments are not supported in Type.function()')

    if len(ast_node.args) != 2:
        raise CompilationError(compilation_context, ast_node, 'Type.function() takes 2 arguments. Got: %s' % len(ast_node.args))
    [return_type_ast_node, arg_list_ast_node] = ast_node.args

    return_type_ir = expression_ast_to_ir2(return_type_ast_node,
                                           compilation_context,
                                           in_match_pattern,
                                           check_var_reference,
                                           match_lambda_argument_names,
                                           current_stmt_line)
    if return_type_ir.expr_type != ir2.TypeType():
        raise CompilationError(compilation_context, return_type_ast_node,
                               'The first argument passed to Type.function should have type Type, but was: %s' % str(return_type_ir.expr_type))

    arg_list_ir = expression_ast_to_ir2(arg_list_ast_node,
                                        compilation_context,
                                        in_match_pattern,
                                        check_var_reference,
                                        match_lambda_argument_names,
                                        current_stmt_line)
    if arg_list_ir.expr_type != ir2.ListType(ir2.TypeType()):
        raise CompilationError(compilation_context, arg_list_ast_node,
                               'The second argument passed to Type.function should have type List[Type], but was: %s' % str(arg_list_ir.expr_type))

    return ir2.FunctionTypeExpr(return_type_expr=return_type_ir,
                                arg_list_expr=arg_list_ir)

def template_instantiation_ast_to_ir2(ast_node: ast.Call,
                                      compilation_context: CompilationContext,
                                      in_match_pattern: bool,
                                      check_var_reference: Callable[[ast.Name], None],
                                      match_lambda_argument_names: Set[str],
                                      current_stmt_line: int):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value,
                               'Keyword arguments are not supported in Type.template_instantiation()')

    if len(ast_node.args) != 2:
        raise CompilationError(compilation_context, ast_node, 'Type.template_instantiation() takes 2 arguments. Got: %s' % len(ast_node.args))
    [template_atomic_cpp_type_ast_node, arg_list_ast_node] = ast_node.args

    if not isinstance(template_atomic_cpp_type_ast_node, ast.Str):
        raise CompilationError(compilation_context, template_atomic_cpp_type_ast_node,
                               'The first argument passed to Type.template_instantiation should be a string')
    _check_atomic_type(template_atomic_cpp_type_ast_node, compilation_context)

    arg_list_ir = expression_ast_to_ir2(arg_list_ast_node,
                                        compilation_context,
                                        in_match_pattern,
                                        check_var_reference,
                                        match_lambda_argument_names,
                                        current_stmt_line)
    if arg_list_ir.expr_type != ir2.ListType(ir2.TypeType()):
        raise CompilationError(compilation_context, arg_list_ast_node,
                               'The second argument passed to Type.template_instantiation should have type List[Type], but was: %s' % str(arg_list_ir.expr_type))

    return ir2.TemplateInstantiationExpr(template_atomic_cpp_type=template_atomic_cpp_type_ast_node.s,
                                         arg_list_expr=arg_list_ir)

_cxx_identifier_regex = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')

def template_member_access_ast_to_ir2(ast_node: ast.Call,
                                      compilation_context: CompilationContext,
                                      in_match_pattern: bool,
                                      check_var_reference: Callable[[ast.Name], None],
                                      match_lambda_argument_names: Set[str],
                                      current_stmt_line: int):
    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'Type.template_member() is not allowed in match patterns')

    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value,
                               'Keyword arguments are not supported in Type.template_member()')

    if len(ast_node.args) != 3:
        raise CompilationError(compilation_context, ast_node, 'Type.template_member() takes 3 arguments. Got: %s' % len(ast_node.args))
    [class_type_ast_node, member_name_ast_node, arg_list_ast_node] = ast_node.args

    class_type_expr_ir = expression_ast_to_ir2(class_type_ast_node,
                                               compilation_context,
                                               in_match_pattern,
                                               check_var_reference,
                                               match_lambda_argument_names,
                                               current_stmt_line)
    if class_type_expr_ir.expr_type != ir2.TypeType():
        raise CompilationError(compilation_context, class_type_ast_node,
                               'The first argument passed to Type.template_member should have type Type, but was: %s' % str(class_type_expr_ir.expr_type))

    if not isinstance(member_name_ast_node, ast.Str):
        raise CompilationError(compilation_context, member_name_ast_node,
                               'The second argument passed to Type.template_member should be a string')
    if not _cxx_identifier_regex.fullmatch(member_name_ast_node.s):
        raise CompilationError(compilation_context, member_name_ast_node,
                               'The second argument passed to Type.template_member should be a valid C++ identifier')

    arg_list_ir = expression_ast_to_ir2(arg_list_ast_node,
                                        compilation_context,
                                        in_match_pattern,
                                        check_var_reference,
                                        match_lambda_argument_names,
                                        current_stmt_line)
    if arg_list_ir.expr_type != ir2.ListType(ir2.TypeType()):
        raise CompilationError(compilation_context, arg_list_ast_node,
                               'The third argument passed to Type.template_member should have type List[Type], but was: %s' % str(arg_list_ir.expr_type))

    return ir2.TemplateMemberAccessExpr(class_type_expr=class_type_expr_ir,
                                        member_name=member_name_ast_node.s,
                                        arg_list_expr=arg_list_ir)

def type_factory_method_ast_to_ir2(ast_node: ast.Call,
                                   compilation_context: CompilationContext,
                                   in_match_pattern: bool,
                                   check_var_reference: Callable[[ast.Name], None],
                                   match_lambda_argument_names: Set[str],
                                   current_stmt_line: int):
    assert isinstance(ast_node, ast.Call)
    assert isinstance(ast_node.func, ast.Attribute)
    assert isinstance(ast_node.func.value, ast.Name)
    assert ast_node.func.value.id == 'Type'

    if ast_node.func.attr == 'pointer':
        return type_pointer_expr_ast_to_ir2(ast_node, compilation_context, in_match_pattern, check_var_reference, match_lambda_argument_names, current_stmt_line)
    elif ast_node.func.attr == 'reference':
        return type_reference_expr_ast_to_ir2(ast_node, compilation_context, in_match_pattern, check_var_reference, match_lambda_argument_names, current_stmt_line)
    elif ast_node.func.attr == 'rvalue_reference':
        return type_rvalue_reference_expr_ast_to_ir2(ast_node, compilation_context, in_match_pattern, check_var_reference, match_lambda_argument_names, current_stmt_line)
    elif ast_node.func.attr == 'const':
        return const_type_expr_ast_to_ir2(ast_node, compilation_context, in_match_pattern, check_var_reference, match_lambda_argument_names, current_stmt_line)
    elif ast_node.func.attr == 'array':
        return type_array_expr_ast_to_ir2(ast_node, compilation_context, in_match_pattern, check_var_reference, match_lambda_argument_names, current_stmt_line)
    elif ast_node.func.attr == 'function':
        return function_type_expr_ast_to_ir2(ast_node, compilation_context, in_match_pattern, check_var_reference, match_lambda_argument_names, current_stmt_line)
    elif ast_node.func.attr == 'template_instantiation':
        return template_instantiation_ast_to_ir2(ast_node, compilation_context, in_match_pattern, check_var_reference, match_lambda_argument_names, current_stmt_line)
    elif ast_node.func.attr == 'template_member':
        return template_member_access_ast_to_ir2(ast_node, compilation_context, in_match_pattern, check_var_reference, match_lambda_argument_names, current_stmt_line)
    else:
        raise CompilationError(compilation_context, ast_node,
                               'Undefined Type factory method')

def empty_list_literal_ast_to_ir2(ast_node: ast.Call,
                                  compilation_context: CompilationContext,
                                  in_match_pattern: bool,
                                  check_var_reference: Callable[[ast.Name], None],
                                  match_lambda_argument_names: Set[str]):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value, 'Keyword arguments are not supported.')
    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, 'empty_list() takes 1 argument. Got: %s' % len(ast_node.args))
    [arg] = ast_node.args
    elem_type = type_declaration_ast_to_ir2_expression_type(arg, compilation_context)
    return ir2.ListExpr(elem_type=elem_type, elem_exprs=(), list_extraction_expr=None)

def empty_set_literal_ast_to_ir2(ast_node: ast.Call,
                                 compilation_context: CompilationContext,
                                 in_match_pattern: bool,
                                 check_var_reference: Callable[[ast.Name], None],
                                 match_lambda_argument_names: Set[str]):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value, 'Keyword arguments are not supported.')
    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, 'empty_set() takes 1 argument. Got: %s' % len(ast_node.args))
    [arg] = ast_node.args
    elem_type = type_declaration_ast_to_ir2_expression_type(arg, compilation_context)
    return ir2.SetExpr(elem_type=elem_type, elem_exprs=())

def int_iterable_sum_expr_ast_to_ir2(ast_node: ast.Call,
                                     compilation_context: CompilationContext,
                                     in_match_pattern: bool,
                                     check_var_reference: Callable[[ast.Name], None],
                                     match_lambda_argument_names: Set[str],
                                     current_stmt_line: int):
    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'sum() is not allowed in match patterns')

    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value, 'Keyword arguments are not supported.')
    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, 'sum() takes 1 argument. Got: %s' % len(ast_node.args))
    [arg] = ast_node.args
    arg_expr = expression_ast_to_ir2(arg,
                                     compilation_context,
                                     in_match_pattern,
                                     check_var_reference,
                                     match_lambda_argument_names,
                                     current_stmt_line)
    if not (isinstance(arg_expr.expr_type, (ir2.ListType, ir2.SetType)) and isinstance(arg_expr.expr_type.elem_type, ir2.IntType)):
        notes = []
        if isinstance(arg_expr, ir2.VarReference):
            lookup_result = compilation_context.get_symbol_definition(arg_expr.name)
            assert lookup_result
            assert not lookup_result.is_only_partially_defined
            notes.append((lookup_result.ast_node, '%s was defined here' % arg_expr.name))
        raise CompilationError(compilation_context, arg,
                               'The argument of sum() must have type List[int] or Set[int]. Got type: %s' % str(arg_expr.expr_type),
                               notes=notes)
    if isinstance(arg_expr.expr_type, ir2.ListType):
        return ir2.IntListSumExpr(list_expr=arg_expr)
    else:
        return ir2.IntSetSumExpr(set_expr=arg_expr)

def bool_iterable_all_expr_ast_to_ir2(ast_node: ast.Call,
                                      compilation_context: CompilationContext,
                                      in_match_pattern: bool,
                                      check_var_reference: Callable[[ast.Name], None],
                                      current_stmt_line: int):
    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'all() is not allowed in match patterns')

    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value, 'Keyword arguments are not supported.')
    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, 'all() takes 1 argument. Got: %s' % len(ast_node.args))
    [arg] = ast_node.args
    arg_expr = expression_ast_to_ir2(arg,
                                     compilation_context,
                                     in_match_pattern,
                                     check_var_reference,
                                     match_lambda_argument_names=set(),
                                     current_stmt_line=current_stmt_line)
    if not (isinstance(arg_expr.expr_type, (ir2.ListType, ir2.SetType)) and isinstance(arg_expr.expr_type.elem_type, ir2.BoolType)):
        notes = []
        if isinstance(arg_expr, ir2.VarReference):
            lookup_result = compilation_context.get_symbol_definition(arg_expr.name)
            assert lookup_result
            assert not lookup_result.is_only_partially_defined
            notes.append((lookup_result.ast_node, '%s was defined here' % arg_expr.name))
        raise CompilationError(compilation_context, arg,
                               'The argument of all() must have type List[bool] or Set[bool]. Got type: %s' % str(arg_expr.expr_type),
                               notes=notes)
    if isinstance(arg_expr.expr_type, ir2.ListType):
        return ir2.BoolListAllExpr(list_expr=arg_expr)
    else:
        return ir2.BoolSetAllExpr(set_expr=arg_expr)

def bool_iterable_any_expr_ast_to_ir2(ast_node: ast.Call,
                                      compilation_context: CompilationContext,
                                      in_match_pattern: bool,
                                      check_var_reference: Callable[[ast.Name], None],
                                      current_stmt_line: int):
    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'any() is not allowed in match patterns')

    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value, 'Keyword arguments are not supported.')
    if len(ast_node.args) != 1:
        raise CompilationError(compilation_context, ast_node, 'any() takes 1 argument. Got: %s' % len(ast_node.args))
    [arg] = ast_node.args
    arg_expr = expression_ast_to_ir2(arg,
                                     compilation_context,
                                     in_match_pattern,
                                     check_var_reference,
                                     match_lambda_argument_names=set(),
                                     current_stmt_line=current_stmt_line)
    if not (isinstance(arg_expr.expr_type, (ir2.ListType, ir2.SetType)) and isinstance(arg_expr.expr_type.elem_type, ir2.BoolType)):
        notes = []
        if isinstance(arg_expr, ir2.VarReference):
            lookup_result = compilation_context.get_symbol_definition(arg_expr.name)
            assert lookup_result
            assert not lookup_result.is_only_partially_defined
            notes.append((lookup_result.ast_node, '%s was defined here' % arg_expr.name))
        raise CompilationError(compilation_context, arg,
                               'The argument of any() must have type List[bool] or Set[bool]. Got type: %s' % str(arg_expr.expr_type),
                               notes=notes)
    if isinstance(arg_expr.expr_type, ir2.ListType):
        return ir2.BoolListAnyExpr(list_expr=arg_expr)
    else:
        return ir2.BoolSetAnyExpr(set_expr=arg_expr)

def _is_structural_equality_check_supported_for_type(expr_type: ir2.ExprType):
    if isinstance(expr_type, ir2.BoolType):
        return True
    elif isinstance(expr_type, ir2.IntType):
        return True
    elif isinstance(expr_type, ir2.TypeType):
        return True
    elif isinstance(expr_type, ir2.FunctionType):
        return False
    elif isinstance(expr_type, ir2.ListType):
        return _is_structural_equality_check_supported_for_type(expr_type.elem_type)
    elif isinstance(expr_type, ir2.SetType):
        return False
    elif isinstance(expr_type, ir2.CustomType):
        return all(_is_structural_equality_check_supported_for_type(arg_type.expr_type)
                   for arg_type in expr_type.arg_types)
    else:
        raise NotImplementedError('Unexpected type: %s' % expr_type.__class__.__name__)

def _is_equality_check_supported_for_type(expr_type: ir2.ExprType):
    if isinstance(expr_type, ir2.SetType):
        return _is_structural_equality_check_supported_for_type(expr_type.elem_type)
    else:
        return _is_structural_equality_check_supported_for_type(expr_type)

def eq_ast_to_ir2(lhs_node: ast.AST,
                  rhs_node: ast.AST,
                  compilation_context: CompilationContext,
                  in_match_pattern: bool,
                  check_var_reference: Callable[[ast.Name], None],
                  current_stmt_line: int):
    assert not in_match_pattern

    lhs = expression_ast_to_ir2(lhs_node,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names=set(),
                                current_stmt_line=current_stmt_line)
    rhs = expression_ast_to_ir2(rhs_node,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names=set(),
                                current_stmt_line=current_stmt_line)
    if lhs.expr_type != rhs.expr_type:
        raise CompilationError(compilation_context, lhs_node, 'Type mismatch in ==: %s vs %s' % (
            str(lhs.expr_type), str(rhs.expr_type)))
    if not _is_equality_check_supported_for_type(lhs.expr_type):
        raise CompilationError(compilation_context, lhs_node, 'Type not supported in equality comparison: ' + str(lhs.expr_type))
    return ir2.EqualityComparison(lhs=lhs, rhs=rhs)

def not_eq_ast_to_ir2(lhs_node: ast.AST,
                      rhs_node: ast.AST,
                      compilation_context: CompilationContext,
                      in_match_pattern: bool,
                      check_var_reference: Callable[[ast.Name], None],
                      current_stmt_line: int):
    assert not in_match_pattern

    lhs = expression_ast_to_ir2(lhs_node,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names=set(),
                                current_stmt_line=current_stmt_line)
    rhs = expression_ast_to_ir2(rhs_node,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names=set(),
                                current_stmt_line=current_stmt_line)
    if lhs.expr_type != rhs.expr_type:
        raise CompilationError(compilation_context, lhs_node, 'Type mismatch in !=: %s vs %s' % (
            str(lhs.expr_type), str(rhs.expr_type)))
    if not _is_equality_check_supported_for_type(lhs.expr_type):
        raise CompilationError(compilation_context, lhs_node, 'Type not supported in equality comparison: ' + str(lhs.expr_type))
    return ir2.NotExpr(expr=ir2.EqualityComparison(lhs=lhs, rhs=rhs))

def in_ast_to_ir2(lhs_node: ast.AST,
                  rhs_node: ast.AST,
                  compilation_context: CompilationContext,
                  in_match_pattern: bool,
                  check_var_reference: Callable[[ast.Name], None],
                  current_stmt_line: int):
    assert not in_match_pattern

    lhs = expression_ast_to_ir2(lhs_node,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names=set(),
                                current_stmt_line=current_stmt_line)
    rhs = expression_ast_to_ir2(rhs_node,
                                compilation_context,
                                in_match_pattern,
                                check_var_reference,
                                match_lambda_argument_names=set(),
                                current_stmt_line=current_stmt_line)

    if isinstance(rhs.expr_type, ir2.ListType):
        rhs_elem_type = rhs.expr_type.elem_type
    elif isinstance(rhs.expr_type, ir2.SetType):
        rhs_elem_type = rhs.expr_type.elem_type
    else:
        raise CompilationError(compilation_context, rhs_node,
                               'The object on the RHS of "in" must be a list or a set, but found type: ' + str(rhs.expr_type))

    if lhs.expr_type != rhs_elem_type:
        raise CompilationError(compilation_context, lhs_node, 'Type mismatch in in: %s vs %s' % (
            str(lhs.expr_type), str(rhs.expr_type)))
    if not _is_equality_check_supported_for_type(lhs.expr_type):
        raise CompilationError(compilation_context, lhs_node, 'Type not supported in equality comparison (for the "in" operator): ' + str(lhs.expr_type))
    return ir2.InExpr(lhs=lhs, rhs=rhs)

def _construct_note_diagnostic_for_function_signature(function_lookup_result: SymbolLookupResult):
    return function_lookup_result.ast_node, 'The definition of %s was here' % function_lookup_result.symbol.name

def function_call_ast_to_ir2(ast_node: ast.Call,
                             compilation_context: CompilationContext,
                             in_match_pattern: bool,
                             check_var_reference: Callable[[ast.Name], None],
                             match_lambda_argument_names: Set[str],
                             current_stmt_line: int):
    # TODO: allow calls to custom types' constructors.
    if in_match_pattern:
        raise CompilationError(compilation_context, ast_node,
                               'Function calls are not allowed in match patterns')

    fun_expr = expression_ast_to_ir2(ast_node.func,
                                     compilation_context,
                                     in_match_pattern,
                                     check_var_reference,
                                     match_lambda_argument_names,
                                     current_stmt_line)
    if not isinstance(fun_expr.expr_type, ir2.FunctionType):
        raise CompilationError(compilation_context, ast_node,
                               'Attempting to call an object that is not a function. It has type: %s' % str(fun_expr.expr_type))

    if ast_node.keywords and ast_node.args:
        raise CompilationError(compilation_context, ast_node, 'Function calls with a mix of keyword and non-keyword arguments are not supported. Please choose either style.')

    if ast_node.keywords:
        if not isinstance(fun_expr, ir2.VarReference):
            raise CompilationError(compilation_context, ast_node.keywords[0].value,
                                   'Keyword arguments can only be used when calling a specific function or constructing a specific type, not when calling other callable objects. Please switch to non-keyword arguments.')
        lookup_result = compilation_context.get_symbol_definition(fun_expr.name)
        assert lookup_result
        assert not lookup_result.is_only_partially_defined
        if not lookup_result.symbol.expr_type.argnames:
            raise CompilationError(compilation_context, ast_node.keywords[0].value,
                                   'Keyword arguments can only be used when calling a specific function or constructing a specific type, not when calling other callable objects. Please switch to non-keyword arguments.')


        arg_expr_by_name = {keyword_arg.arg: expression_ast_to_ir2(keyword_arg.value,
                                                                   compilation_context,
                                                                   in_match_pattern,
                                                                   check_var_reference,
                                                                   match_lambda_argument_names,
                                                                   current_stmt_line)
                            for keyword_arg in ast_node.keywords}
        formal_arg_names = set(lookup_result.symbol.expr_type.argnames)
        specified_nonexisting_args = arg_expr_by_name.keys() - formal_arg_names
        missing_args = formal_arg_names - arg_expr_by_name.keys()
        if specified_nonexisting_args and missing_args:
            raise CompilationError(compilation_context, ast_node,
                                   'Incorrect arguments in call to %s. Missing arguments: {%s}. Specified arguments that don\'t exist: {%s}' % (
                                       fun_expr.name, ', '.join(sorted(missing_args)), ', '.join(sorted(specified_nonexisting_args))),
                                   notes=[_construct_note_diagnostic_for_function_signature(lookup_result)])
        elif specified_nonexisting_args:
            raise CompilationError(compilation_context, ast_node,
                                   'Incorrect arguments in call to %s. Specified arguments that don\'t exist: {%s}' % (
                                       fun_expr.name, ', '.join(sorted(specified_nonexisting_args))),
                                   notes=[_construct_note_diagnostic_for_function_signature(lookup_result)])
        elif missing_args:
            raise CompilationError(compilation_context, ast_node,
                                   'Incorrect arguments in call to %s. Missing arguments: {%s}' % (
                                       fun_expr.name, ', '.join(sorted(missing_args))),
                                   notes=[_construct_note_diagnostic_for_function_signature(lookup_result)])

        args = tuple(arg_expr_by_name[arg]
                     for arg in lookup_result.symbol.expr_type.argnames)

        for expr, keyword_arg, arg_type, arg_decl_ast_node in zip(args, ast_node.keywords, fun_expr.expr_type.argtypes, lookup_result.symbol.expr_type.argnames):
            if expr.expr_type != arg_type:
                notes = [_construct_note_diagnostic_for_function_signature(lookup_result)]
                if isinstance(keyword_arg.value, ast.Name):
                    lookup_result = compilation_context.get_symbol_definition(keyword_arg.value.id)
                    assert not lookup_result.is_only_partially_defined
                    notes.append((lookup_result.ast_node, 'The definition of %s was here' % keyword_arg.value.id))

                raise CompilationError(compilation_context, keyword_arg.value,
                                       'Type mismatch for argument %s: expected type %s but was: %s' % (
                                           keyword_arg.arg, str(arg_type), str(expr.expr_type)),
                                       notes=notes)
    else:
        ast_node_args = ast_node.args or []
        args = tuple(expression_ast_to_ir2(arg_node,
                                      compilation_context,
                                      in_match_pattern,
                                      check_var_reference,
                                      match_lambda_argument_names,
                                      current_stmt_line)
                     for arg_node in ast_node_args)
        if len(args) != len(fun_expr.expr_type.argtypes):
            if isinstance(ast_node.func, ast.Name):
                lookup_result = compilation_context.get_symbol_definition(ast_node.func.id)
                assert lookup_result
                assert not lookup_result.is_only_partially_defined
                raise CompilationError(compilation_context, ast_node,
                                       'Argument number mismatch in function call to %s: got %s arguments, expected %s' % (
                                           ast_node.func.id, len(args), len(fun_expr.expr_type.argtypes)),
                                       notes=[_construct_note_diagnostic_for_function_signature(lookup_result)])
            else:
                raise CompilationError(compilation_context, ast_node,
                                       'Argument number mismatch in function call: got %s arguments, expected %s' % (
                                           len(args), len(fun_expr.expr_type.argtypes)))

        for arg_index, (expr, expr_ast_node, arg_type) in enumerate(zip(args, ast_node_args, fun_expr.expr_type.argtypes)):
            if expr.expr_type != arg_type:
                notes = []

                if isinstance(ast_node.func, ast.Name):
                    lookup_result = compilation_context.get_symbol_definition(ast_node.func.id)
                    assert lookup_result
                    notes.append(_construct_note_diagnostic_for_function_signature(lookup_result))

                if isinstance(expr_ast_node, ast.Name):
                    lookup_result = compilation_context.get_symbol_definition(expr_ast_node.id)
                    assert lookup_result
                    notes.append((lookup_result.ast_node, 'The definition of %s was here' % expr_ast_node.id))

                raise CompilationError(compilation_context, expr_ast_node,
                                       'Type mismatch for argument %s: expected type %s but was: %s' % (
                                           arg_index, str(arg_type), str(expr.expr_type)),
                                       notes=notes)

    return ir2.FunctionCall(fun_expr=fun_expr,
                            args=args,
                            may_throw=(not isinstance(fun_expr, ir2.VarReference)
                                       or fun_expr.is_function_that_may_throw))

def var_reference_ast_to_ir2(ast_node: ast.Name,
                             compilation_context: CompilationContext,
                             in_match_pattern: bool,
                             check_var_reference: Callable[[ast.Name], None],
                             match_lambda_argument_names: Set[str]):
    assert isinstance(ast_node.ctx, ast.Load)
    check_var_reference(ast_node)

    lookup_result = compilation_context.get_symbol_definition(ast_node.id)

    # In match patterns, variables get defined at the first point of use, either here or in list_expression_ast_to_ir2().
    if in_match_pattern and ast_node.id in match_lambda_argument_names:
        if lookup_result:
            if lookup_result.symbol.expr_type != ir2.TypeType():
                raise CompilationError(compilation_context, ast_node,
                                       'Can\'t match %s as a Type because it was already used to match a List[Type]' % ast_node.id,
                                       notes=[(lookup_result.ast_node, 'A previous match as a List[Type] was here')])
        else:
            compilation_context.add_symbol(name=ast_node.id,
                                           expr_type=ir2.TypeType(),
                                           definition_ast_node=ast_node,
                                           is_only_partially_defined=False,
                                           is_function_that_may_throw=False)
            lookup_result = compilation_context.get_symbol_definition(ast_node.id)

    if lookup_result:
        if lookup_result.is_only_partially_defined:
            raise CompilationError(compilation_context, ast_node,
                                   'Reference to a variable that may or may not have been initialized (depending on which branch was taken)',
                                   notes=[(lookup_result.ast_node, '%s might have been initialized here' % ast_node.id)])
        return ir2.VarReference(expr_type=lookup_result.symbol.expr_type,
                                name=lookup_result.symbol.name,
                                is_global_function=lookup_result.symbol_table.parent is None,
                                is_function_that_may_throw=(isinstance(lookup_result.symbol.expr_type, ir2.FunctionType)
                                                            and lookup_result.symbol.is_function_that_may_throw),
                                source_module=lookup_result.symbol.source_module)
    else:
        definition_ast_node = compilation_context.get_partial_function_definition(ast_node.id)
        if definition_ast_node:
            if compilation_context.current_function_name == ast_node.id:
                raise CompilationError(compilation_context, ast_node, 'Recursive function references are only allowed if the return type is declared explicitly.',
                                       notes=[(definition_ast_node, '%s was defined here' % ast_node.id)])
            else:
                raise CompilationError(compilation_context, ast_node, 'Reference to a function whose return type hasn\'t been determined yet. Please add a return type declaration in %s or move its declaration before its use.' % ast_node.id,
                                       notes=[(definition_ast_node, '%s was defined here' % ast_node.id)])
        else:
            raise CompilationError(compilation_context, ast_node, 'Reference to undefined variable/function')

def list_expression_ast_to_ir2(ast_node: ast.List,
                               compilation_context: CompilationContext,
                               in_match_pattern: bool,
                               check_var_reference: Callable[[ast.Name], None],
                               match_lambda_argument_names: Set[str],
                               current_stmt_line: int):

    elem_exprs = []
    list_extraction_expr = None
    for index, elem_expr_node in enumerate(ast_node.elts):
        if isinstance(elem_expr_node, ast.Starred) and in_match_pattern:
            # [..., *Ts]
            if not isinstance(elem_expr_node.value, ast.Name):
                raise CompilationError(compilation_context, elem_expr_node,
                                       'List extraction is only allowed with an identifier, e.g. [*Ts]')

            if index != len(ast_node.elts) - 1:
                raise CompilationError(compilation_context, elem_expr_node,
                                       'List extraction is only allowed at the end of the list')

            list_extraction_var_name = elem_expr_node.value.id
            if list_extraction_var_name not in match_lambda_argument_names:
                raise CompilationError(compilation_context, elem_expr_node.value,
                                       'List extraction can only be used with type variables that are lambda arguments of this match()')

            existing_symbol = compilation_context.get_symbol_definition(elem_expr_node.value.id)
            if existing_symbol:
                if existing_symbol.symbol.expr_type != ir2.ListType(ir2.TypeType()):
                    raise CompilationError(compilation_context, elem_expr_node.value,
                                           'List extraction can\'t be used on %s because it was already used to match a Type' % elem_expr_node.value.id,
                                           notes=[(existing_symbol.ast_node, 'A previous match as a Type was here')])
            else:
                compilation_context.add_symbol(name=elem_expr_node.value.id,
                                               expr_type=ir2.ListType(ir2.TypeType()),
                                               definition_ast_node=elem_expr_node.value,
                                               is_only_partially_defined=False,
                                               is_function_that_may_throw=False)
            list_extraction_expr = ir2.VarReference(expr_type=ir2.ListType(ir2.TypeType()),
                                                    name=elem_expr_node.value.id,
                                                    is_global_function=False,
                                                    is_function_that_may_throw=False)
        else:
            elem_exprs.append(expression_ast_to_ir2(elem_expr_node,
                                                    compilation_context,
                                                    in_match_pattern,
                                                    check_var_reference,
                                                    match_lambda_argument_names,
                                                    current_stmt_line))

    if len(elem_exprs) > 0:
        elem_type = elem_exprs[0].expr_type
    elif list_extraction_expr:
        assert isinstance(list_extraction_expr.expr_type, ir2.ListType)
        elem_type = list_extraction_expr.expr_type.elem_type
    else:
        raise CompilationError(compilation_context, ast_node, 'Untyped empty lists are not supported. Please import empty_list from pytmp and then write e.g. empty_list(int) to create an empty list of ints.')

    for elem_expr, elem_expr_ast_node in zip(elem_exprs, ast_node.elts):
        if elem_expr.expr_type != elem_type:
            raise CompilationError(compilation_context, elem_expr_ast_node,
                                   'Found different types in list elements, this is not supported. The type of this element was %s instead of %s' % (
                                       str(elem_expr.expr_type), str(elem_type)),
                                   notes=[(ast_node.elts[0], 'A previous list element with type %s was here.' % str(elem_type))])
    if isinstance(elem_type, ir2.FunctionType):
        raise CompilationError(compilation_context, ast_node,
                               'Creating lists of functions is not supported. The elements of this list have type: %s' % str(elem_type))

    return ir2.ListExpr(elem_type=elem_type,
                        elem_exprs=tuple(elem_exprs),
                        list_extraction_expr=list_extraction_expr)

def set_expression_ast_to_ir2(ast_node: ast.Set,
                              compilation_context: CompilationContext,
                              in_match_pattern: bool,
                              check_var_reference: Callable[[ast.Name], None],
                              match_lambda_argument_names: Set[str],
                              current_stmt_line: int):
    elem_exprs = tuple(expression_ast_to_ir2(elem_expr_node,
                                        compilation_context,
                                        in_match_pattern,
                                        check_var_reference,
                                        match_lambda_argument_names,
                                        current_stmt_line)
                       for elem_expr_node in ast_node.elts)
    assert elem_exprs
    elem_type = elem_exprs[0].expr_type
    for elem_expr, elem_expr_ast_node in zip(elem_exprs, ast_node.elts):
        if elem_expr.expr_type != elem_type:
            raise CompilationError(compilation_context, elem_expr_ast_node,
                                   'Found different types in set elements, this is not supported. The type of this element was %s instead of %s' % (
                                       str(elem_expr.expr_type), str(elem_type)),
                                   notes=[(ast_node.elts[0], 'A previous set element with type %s was here.' % str(elem_type))])
    if isinstance(elem_type, ir2.FunctionType):
        raise CompilationError(compilation_context, ast_node,
                               'Creating sets of functions is not supported. The elements of this set have type: %s' % str(elem_type))

    return ir2.SetExpr(elem_type=elem_type, elem_exprs=elem_exprs)

def type_declaration_ast_to_ir2_expression_type(ast_node: ast.AST, compilation_context: CompilationContext):
    if isinstance(ast_node, ast.Name) and isinstance(ast_node.ctx, ast.Load):
        if ast_node.id == 'bool':
            return ir2.BoolType()
        elif ast_node.id == 'int':
            return ir2.IntType()
        elif ast_node.id == 'Type':
            return ir2.TypeType()
        else:
            lookup_result = compilation_context.get_type_symbol_definition(ast_node.id)
            if lookup_result:
                return lookup_result.symbol.expr_type
            else:
                raise CompilationError(compilation_context, ast_node, 'Unsupported (or undefined) type: ' + ast_node.id)

    if (isinstance(ast_node, ast.Subscript)
        and isinstance(ast_node.value, ast.Name)
        and isinstance(ast_node.value.ctx, ast.Load)
        and isinstance(ast_node.ctx, ast.Load)
        and isinstance(ast_node.slice, ast.Index)):
        if ast_node.value.id == 'List':
            return ir2.ListType(type_declaration_ast_to_ir2_expression_type(ast_node.slice.value, compilation_context))
        if ast_node.value.id == 'Set':
            return ir2.SetType(type_declaration_ast_to_ir2_expression_type(ast_node.slice.value, compilation_context))
        elif (ast_node.value.id == 'Callable'
              and isinstance(ast_node.slice.value, ast.Tuple)
              and len(ast_node.slice.value.elts) == 2
              and isinstance(ast_node.slice.value.elts[0], ast.List)
              and isinstance(ast_node.slice.value.elts[0].ctx, ast.Load)
              and all(isinstance(elem, ast.Name) and isinstance(elem.ctx, ast.Load)
                      for elem in ast_node.slice.value.elts[0].elts)):
            return ir2.FunctionType(
                argtypes=tuple(type_declaration_ast_to_ir2_expression_type(arg_type_decl, compilation_context)
                               for arg_type_decl in ast_node.slice.value.elts[0].elts),
                argnames=None,
                returns=type_declaration_ast_to_ir2_expression_type(ast_node.slice.value.elts[1], compilation_context))

    raise CompilationError(compilation_context, ast_node, 'Unsupported type declaration.')

# Checks if the statement is of the form:
# self.some_field = <expr>
def _is_class_field_initialization(ast_node: ast.AST):
    return (isinstance(ast_node, ast.Assign)
            and not ast_node.type_comment
            and len(ast_node.targets) == 1
            and isinstance(ast_node.targets[0], ast.Attribute)
            and isinstance(ast_node.targets[0].ctx, ast.Store)
            and isinstance(ast_node.targets[0].value, ast.Name)
            and ast_node.targets[0].value.id == 'self'
            and isinstance(ast_node.targets[0].value.ctx, ast.Load))

def class_definition_ast_to_ir2(ast_node: ast.ClassDef, compilation_context: CompilationContext, next_stmt_line: int):
    if ast_node.bases:
        if len(ast_node.bases) > 1:
            raise CompilationError(compilation_context, ast_node.bases[1],
                                   'Multiple base classes are not supported.')
        [base] = ast_node.bases
        if not (isinstance(base, ast.Name) and isinstance(base.ctx, ast.Load) and base.id == 'Exception'):
            raise CompilationError(compilation_context, base,
                                   '"Exception" is the only supported base class.')
        inherits_from_exception = True
    else:
        inherits_from_exception = False

    if not ast_node.decorator_list:
        has_dataclass_decorator = False
    else:
        if len(ast_node.decorator_list) > 1:
            raise CompilationError(compilation_context, ast_node.decorator_list[1],
                                   'Classes with multiple decorators are not supported.')
        [decorator] = ast_node.decorator_list
        if not (isinstance(decorator, ast.Name) and isinstance(decorator.ctx, ast.Load) and decorator.id == 'dataclass'):
            raise CompilationError(compilation_context, decorator,
                                   '"@dataclass" is the only supported class decorator.')
        has_dataclass_decorator = True

    if not inherits_from_exception and not has_dataclass_decorator:
        raise CompilationError(compilation_context, ast_node,
                               'Custom classes must either inherit from Exception or be decorated with @dataclass.')

    if inherits_from_exception and has_dataclass_decorator:
        raise CompilationError(compilation_context, ast_node,
                               'Custom Exception classes should not have the @dataclass decorator.')

    if inherits_from_exception:
        return custom_exception_class_to_ir2(ast_node, compilation_context, next_stmt_line)
    else:
        return custom_dataclass_definition_to_ir2(ast_node, compilation_context, next_stmt_line)

def custom_exception_class_to_ir2(ast_node: ast.ClassDef,
                                  compilation_context: CompilationContext,
                                  next_stmt_line: int):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value,
                               'Keyword class arguments are not supported.')

    if len(ast_node.body) != 1 or not isinstance(ast_node.body[0], ast.FunctionDef) or ast_node.body[0].name != '__init__':
        raise CompilationError(compilation_context, ast_node,
                               'Custom classes must contain an __init__ method (and nothing else).')

    [init_defn_ast_node] = ast_node.body

    init_args_ast_node = init_defn_ast_node.args

    if init_args_ast_node.vararg:
        raise CompilationError(compilation_context, init_args_ast_node.vararg,
                               'Vararg arguments are not supported in __init__.')
    if init_args_ast_node.kwonlyargs:
        raise CompilationError(compilation_context, init_args_ast_node.kwonlyargs[0],
                               'Keyword-only arguments are not supported in __init__.')
    if init_args_ast_node.kw_defaults or init_args_ast_node.defaults:
        raise CompilationError(compilation_context, init_defn_ast_node,
                               'Default arguments are not supported in __init__.')
    if init_args_ast_node.kwarg:
        raise CompilationError(compilation_context, init_defn_ast_node,
                               'Keyword arguments are not supported in __init__.')

    init_args_ast_nodes = init_args_ast_node.args

    if not init_args_ast_nodes or init_args_ast_nodes[0].arg != 'self':
        raise CompilationError(compilation_context, init_defn_ast_node,
                               'Expected "self" as first argument of __init__.')

    if init_args_ast_nodes[0].annotation:
        raise CompilationError(compilation_context, init_args_ast_nodes[0].annotation,
                               'Type annotations on the "self" argument are not supported.')

    for arg in init_args_ast_nodes:
        if arg.type_comment:
            raise CompilationError(compilation_context, arg,
                                   'Type comments on arguments are not supported.')

    init_args_ast_nodes = init_args_ast_nodes[1:]

    if not init_args_ast_nodes:
        raise CompilationError(compilation_context, init_defn_ast_node,
                               'Custom types must have at least 1 constructor argument (and field).')

    arg_decl_nodes_by_name = dict()
    arg_types = []
    for arg in init_args_ast_nodes:
        if not init_args_ast_nodes[0].annotation:
            raise CompilationError(compilation_context, arg,
                                   'All arguments of __init__ (except "self") must have a type annotation.')
        if arg.arg in arg_decl_nodes_by_name:
            previous_arg_node = arg_decl_nodes_by_name[arg.arg]
            raise CompilationError(compilation_context, arg,
                                   'Found multiple arguments with name "%s".' % arg.arg,
                                   notes=[(previous_arg_node, 'A previous argument with name "%s" was declared here.' % arg.arg)])

        if arg.arg == 'type':
            raise CompilationError(compilation_context, arg,
                                   'Arguments of a custom type cannot be called "type", it\'s a reserved identifier')

        arg_decl_nodes_by_name[arg.arg] = arg
        arg_types.append(ir2.CustomTypeArgDecl(name=arg.arg,
                                               expr_type = type_declaration_ast_to_ir2_expression_type(arg.annotation, compilation_context)))

    init_body_ast_nodes = init_defn_ast_node.body

    first_stmt = init_body_ast_nodes[0]
    if not (_is_class_field_initialization(first_stmt)
            and isinstance(first_stmt.value, ast.Str)
            and first_stmt.targets[0].attr == 'message'):
        raise CompilationError(compilation_context, first_stmt,
                               'Unexpected statement. The first statement in the constructor of an exception class must be of the form: self.message = \'...\'.')
    exception_message = first_stmt.value.s
    init_body_ast_nodes = init_body_ast_nodes[1:]

    arg_assign_nodes_by_name = dict()
    for stmt_ast_node in init_body_ast_nodes:
        if not (_is_class_field_initialization(stmt_ast_node)
                and isinstance(stmt_ast_node.value, ast.Name)
                and isinstance(stmt_ast_node.value.ctx, ast.Load)):
            raise CompilationError(compilation_context, stmt_ast_node,
                                   'Unexpected statement. All statements in __init__ methods must be of the form "self.some_var = some_var".')

        if stmt_ast_node.value.id in arg_assign_nodes_by_name:
            previous_assign_node = arg_assign_nodes_by_name[stmt_ast_node.value.id]
            raise CompilationError(compilation_context, stmt_ast_node,
                                   'Found multiple assignments to the field "%s".' % stmt_ast_node.value.id,
                                   notes=[(previous_assign_node, 'A previous assignment to "self.%s" was here.' % stmt_ast_node.value.id)])

        if stmt_ast_node.targets[0].attr != stmt_ast_node.value.id:
            raise CompilationError(compilation_context, stmt_ast_node,
                                   '__init__ arguments must be assigned to a field of the same name, but "%s" was assigned to "%s".' % (stmt_ast_node.value.id, stmt_ast_node.targets[0].attr))

        if stmt_ast_node.value.id not in arg_decl_nodes_by_name:
            raise CompilationError(compilation_context, stmt_ast_node,
                                   'Unsupported assignment. All assigments in __init__ methods must assign a parameter to a field with the same name.')

        arg_assign_nodes_by_name[stmt_ast_node.value.id] = stmt_ast_node

    for arg_name, decl_ast_node in arg_decl_nodes_by_name.items():
        if arg_name not in arg_assign_nodes_by_name:
            raise CompilationError(compilation_context, decl_ast_node,
                                   'All __init__ arguments must be assigned to fields, but "%s" was never assigned.' % arg_name)

    definition_branches = (
        (-ast_node.lineno, ast_node.lineno),
        (ast_node.lineno, init_defn_ast_node.lineno),
        (ast_node.lineno, next_stmt_line),
        (init_defn_ast_node.lineno, -ast_node.lineno),
    )
    constructor_branches = [(-init_defn_ast_node.lineno, init_defn_ast_node.body[0].lineno)]
    for index, stmt_ast_node in enumerate(init_defn_ast_node.body):
        if index + 1 < len(init_defn_ast_node.body):
            constructor_branches.append((stmt_ast_node.lineno, init_defn_ast_node.body[index + 1].lineno))
        else:
            constructor_branches.append((stmt_ast_node.lineno, -init_defn_ast_node.lineno))


    custom_type_ir = ir2.CustomType(name=ast_node.name,
                                    arg_types=tuple(arg_types),
                                    is_exception_class=True,
                                    exception_message=exception_message,
                                    constructor_source_branches=tuple(
                                        SourceBranch(compilation_context.filename, start, end)
                                        for start, end in constructor_branches))

    pass_stmts = tuple(ir2.PassStmt(SourceBranch(compilation_context.filename, start, end))
                       for start, end in definition_branches)

    return custom_type_ir, pass_stmts

def custom_dataclass_definition_to_ir2(ast_node: ast.ClassDef,
                                       compilation_context: CompilationContext,
                                       next_stmt_line: int):
    if ast_node.keywords:
        raise CompilationError(compilation_context, ast_node.keywords[0].value,
                               'Keyword class arguments are not supported.')

    if not ast_node.body:
        raise CompilationError(compilation_context, ast_node,
                               'Dataclasses must have at least 1 field.')

    arg_decl_nodes_by_name: Dict[str, ast.AnnAssign] = dict()
    arg_types = []
    for field in ast_node.body:
        if not isinstance(field, ast.AnnAssign) or not isinstance(field.target, ast.Name):
            raise CompilationError(compilation_context, field,
                                   'Dataclasses can contain only typed field assignments (and no other statements).')
        if field.value:
            raise CompilationError(compilation_context, field,
                                   'Dataclass field defaults are not supported.')

        field_name = field.target.id
        field_type = field.annotation

        if field_name in arg_decl_nodes_by_name:
            previous_arg_node = arg_decl_nodes_by_name[field_name]
            raise CompilationError(compilation_context, field,
                                   'Found multiple dataclass fields with name "%s".' % field_name,
                                   notes=[(previous_arg_node, 'A previous field with name "%s" was declared here.' % field_name)])

        if field_name == 'type':
            raise CompilationError(compilation_context, field,
                                   'Dataclass fields cannot be called "type", it\'s a reserved identifier')

        arg_decl_nodes_by_name[field_name] = field
        arg_types.append(ir2.CustomTypeArgDecl(name=field_name,
                                               expr_type = type_declaration_ast_to_ir2_expression_type(field_type, compilation_context)))

    custom_type_ir = ir2.CustomType(name=ast_node.name,
                                    arg_types=tuple(arg_types),
                                    is_exception_class=False,
                                    exception_message=None,
                                    constructor_source_branches=())

    # 1: from dataclasses import dataclass
    # 2: @dataclass
    # 3: class MyType:
    # 4:     x: bool
    # 5:     y: int
    # 6: assert MyType(True, 15).x
    # Generated branches that should not be generated:
    # * (-3, 3): line -3 didn't jump to line 3, in the IR nodes:
    # PassStmt(
    #   source_branch = SourceBranch(
    #     file_name = '<unknown>',
    #     source_line = -3,
    #     dest_line = 3))
    # * (1, 3): line 1 didn't jump to line 3, in the IR nodes:
    # PassStmt(
    #   source_branch = SourceBranch(
    #     file_name = '<unknown>',
    #     source_line = 1,
    #     dest_line = 3))
    # Not generated branches that should have been generated:

    # * (4, 5): line 4 didn't jump to line 5
    # * (5, -2): line 5 didn't exit the body of class 'MyType'
    # Matching branches (generated correctly):
    # * (-1, 1): line -1 didn't jump to line 1 (in nodes: Module)
    # * (3, 6): line 3 didn't jump to line 6 (in nodes: PassStmt)
    # * (6, -1): line 6 didn't exit the module (in nodes: Assert)

    dataclass_decorator_line = ast_node.decorator_list[0].lineno
    class_line = ast_node.lineno
    fields = ast_node.body

    definition_branches = (
        (-dataclass_decorator_line, dataclass_decorator_line),
        (dataclass_decorator_line, class_line),
        (class_line, next_stmt_line),
        (dataclass_decorator_line, fields[0].lineno),
        *((field1.lineno, field2.lineno)
          for field1, field2 in zip(fields[:-1], fields[1:])),
        (fields[-1].lineno, -dataclass_decorator_line),
    )
    pass_stmts = tuple(ir2.PassStmt(SourceBranch(compilation_context.filename, start, end))
                       for start, end in definition_branches)

    return custom_type_ir, pass_stmts
