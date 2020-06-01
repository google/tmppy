#!/usr/bin/env python3
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

import difflib
import inspect
import itertools
import json
import os
import pickle
import re
import subprocess
import sys
import shlex
import tempfile
import textwrap
import traceback
import unittest
from collections import defaultdict
from functools import wraps, lru_cache
from typing import Callable, Iterable, Any, Tuple, Set, Dict, List, Sequence, Optional

# noinspection PyUnresolvedReferences
import py2tmp_test_config as config
import pytest
from absl.testing import parameterized, absltest
from coverage import Coverage
from coverage.config import CoverageConfig
from coverage.parser import PythonParser
from coverage.python import PythonFileReporter

from _py2tmp import ir2, ir1, ir0
from _py2tmp.compiler._compile import compile_source_code
from _py2tmp.compiler._link import compute_merged_header_for_linking
from _py2tmp.compiler.output_files import ObjectFileContent, merge_object_files
from _py2tmp.compiler.stages import CompilationError
from _py2tmp.coverage import report_covered, is_coverage_collection_enabled, SourceBranch
from _py2tmp.ir0_optimization import ConfigurationKnobs, DEFAULT_VERBOSE_SETTING
from py2tmp.testing.pytest_plugin import TmppyFixture

CHECK_TESTS_WERE_FULLY_OPTIMIZED = True

TEST_MODULE_NAME = 'test_module'


class TestFailedException(Exception):
    pass


def bisect_with_predicate(last_known_good: int, first_known_bad: int, is_good: Callable[[int], bool]):
    assert last_known_good < first_known_bad
    while last_known_good + 1 < first_known_bad:
        middle = (last_known_good + first_known_bad + 1) // 2
        assert last_known_good < middle < first_known_bad
        if is_good(middle):
            last_known_good = middle
        else:
            first_known_bad = middle
        assert last_known_good < first_known_bad
    assert last_known_good + 1 == first_known_bad
    return first_known_bad


# run takes a bool allow_toplevel_static_asserts_after_optimization and returns the cpp source.
def run_test_with_optional_optimization(run: Callable[[bool], str], allow_reaching_max_optimization_loops=False):
    try:
        ConfigurationKnobs.verbose = DEFAULT_VERBOSE_SETTING

        e1 = None
        e1_traceback = None
        try:
            ConfigurationKnobs.max_num_optimization_steps = 0
            cpp_source = run(True)
        except (TestFailedException, AttributeError, AssertionError) as e:
            e1 = e
            e1_traceback = traceback.format_exc()
            cpp_source = None

        e2 = None
        try:
            ConfigurationKnobs.max_num_optimization_steps = -1
            ConfigurationKnobs.optimization_step_counter = 0
            ConfigurationKnobs.reached_max_num_remaining_loops_counter = 0
            run(True)
        except (TestFailedException, AttributeError, AssertionError) as e:
            e2 = e

        if e1 and e2:
            raise e1

        if not e1 and not e2:
            if ConfigurationKnobs.reached_max_num_remaining_loops_counter != 0 and not allow_reaching_max_optimization_loops:
                ConfigurationKnobs.verbose = True
                optimized_cpp_source = run(True)
                raise TestFailedException(
                    'The test passed, but hit max_num_remaining_loops.\nOptimized C++ code:\n%s' % optimized_cpp_source)
            if CHECK_TESTS_WERE_FULLY_OPTIMIZED:
                run(False)
            return

        def predicate(max_num_optimization_steps: int):
            ConfigurationKnobs.max_num_optimization_steps = max_num_optimization_steps
            try:
                run(True)
                return True
            except (TestFailedException, AttributeError, AssertionError) as e:
                return False

        if e2:
            # Fails with ir0_optimization, succeeds without.
            # Bisect to find the issue.
            bisect_result = bisect_with_predicate(0, ConfigurationKnobs.optimization_step_counter, predicate)
            ConfigurationKnobs.verbose = True
            ConfigurationKnobs.max_num_optimization_steps = bisect_result
            try:
                run(True)
            except TestFailedException as e:
                [message] = e.args
                raise TestFailedException(
                    'Found test that fails after ir0_optimization.\n%s\nNon-optimized C++ code:\n%s' % (
                    textwrap.dedent(message),
                    cpp_source))
            except (AttributeError, AssertionError):
                raise TestFailedException(
                    'Found test that fails after ir0_optimization.\n%s\nNon-optimized C++ code:\n%s' % (
                    traceback.format_exc(),
                    cpp_source))

            raise Exception(
                'This should never happen, the test failed before with the same max_num_optimization_steps.')
        else:
            # Fails without ir0_optimization, succeeds with.
            # Bisect to find the issue.
            bisect_result = bisect_with_predicate(0, ConfigurationKnobs.optimization_step_counter,
                                                  lambda n: not predicate(n))
            ConfigurationKnobs.verbose = True
            ConfigurationKnobs.max_num_optimization_steps = bisect_result
            run(True)
            raise TestFailedException('Found test that succeeds only after ir0_optimization: ' + e1_traceback)
    except TestFailedException as e:
        [message] = e.args
        pytest.fail(message, pytrace=False)


def pretty_print_command(command: Sequence[str]):
    return ' '.join(shlex.quote(x) for x in command)


def multiple_parameters(*param_lists):
    param_lists = [[params if isinstance(params, tuple) else (params,)
                    for params in param_list]
                   for param_list in param_lists]
    result = param_lists[0]
    for param_list in param_lists[1:]:
        result = [(*args1, *args2)
                  for args1 in result
                  for args2 in param_list]
    return parameterized.parameters(*result)


def multiple_named_parameters(*param_lists):
    result = param_lists[0]
    for param_list in param_lists[1:]:
        result = [(name1 + ', ' + name2, *args1, *args2)
                  for name1, *args1 in result
                  for name2, *args2 in param_list]
    return parameterized.named_parameters(*result)


def add_line_numbers(source_code):
    lines = source_code.splitlines()
    last_line_num_length = len(str(len(lines)))
    return '\n'.join('%%%sd: %%s' % last_line_num_length % (n + 1, line) for n, line in enumerate(lines))


class CommandFailedException(Exception):
    def __init__(self, command, stdout, stderr, error_code):
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.error_code = error_code

    def __str__(self):
        return textwrap.dedent('''\
        Ran command: {command}
        Exit code {error_code}
        
        Stdout:
        {stdout}

        Stderr:
        {stderr}
        ''').format(command=pretty_print_command(self.command), error_code=self.error_code, stdout=self.stdout,
                    stderr=self.stderr)


def run_command(executable: str, args: List[str] = ()):
    command = [executable, *args]
    # print('Executing command:', pretty_print_command(command))
    try:
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        (stdout, stderr) = p.communicate()
    except Exception as e:
        raise Exception("While executing: %s" % command)
    if p.returncode != 0:
        raise CommandFailedException(command, stdout, stderr, p.returncode)
    # print('Execution successful.')
    # print('stdout:')
    # print(stdout)
    # print('')
    # print('stderr:')
    # print(stderr)
    # print('')
    return stdout, stderr


def run_compiled_executable(executable: str):
    return run_command(executable)


class CompilationFailedException(Exception):
    def __init__(self, command, error_message) -> None:
        self.command = command
        self.error_message = error_message

    def __str__(self) -> str:
        return textwrap.dedent('''\
        Ran command: {command}
        Error message:
        {error_message}
        ''').format(command=pretty_print_command(self.command), error_message=self.error_message)

_EXTRACT_SOURCE_BRANCHES_REGEX = re.compile('<fruit-coverage-internal-marker file_name=\'([^\']*)\' source_line=\'([^\']*)\' dest_line=\'([^\']*)\' />')

def _extract_covered_source_branches(compiler_stderr: str):
    for file_name, source_line, dest_line in _EXTRACT_SOURCE_BRANCHES_REGEX.findall(compiler_stderr):
        report_covered(SourceBranch(file_name, source_line, dest_line))

class PosixCompiler:
    def __init__(self) -> None:
        self.executable = config.CXX
        self.name = config.CXX_COMPILER_NAME

    def compile_discarding_output(self, source: str, include_dirs: List[str], args: List[str] = ()):
        try:
            args = args + ['-c', source, '-o', os.path.devnull]
            return self._compile(include_dirs, args=args)
        except CommandFailedException as e:
            raise CompilationFailedException(e.command, e.stderr)

    def compile_and_link(self, source: str, include_dirs: List[str], output_file_name: str, args: List[str] = ()):
        return self._compile(
            include_dirs,
            args=(
                    [source]
                    + config.ADDITIONAL_LINKER_FLAGS.split()
                    + args
                    + ['-o', output_file_name]
            ))

    def _compile(self, include_dirs: List[str], args: List[str]):
        all_args = ['-W', '-Wall', '-g0', '-std=c++11']
        if not is_coverage_collection_enabled():
            all_args.append('-Werror')
        for include_dir in include_dirs:
            all_args.append('-I%s' % include_dir)
        all_args += config.ADDITIONAL_COMPILER_FLAGS.split()
        all_args += args
        stdout, stderr = run_command(self.executable, all_args)
        assert not stdout
        _extract_covered_source_branches(stderr)


class MsvcCompiler:
    def __init__(self) -> None:
        self.executable = config.CXX
        self.name = config.CXX_COMPILER_NAME

    def compile_discarding_output(self, source: str, include_dirs: List[str], args: List[str] = ()):
        try:
            args = args + ['/c', source]
            return self._compile(include_dirs, args=args)
        except CommandFailedException as e:
            # Note that we use stdout here, unlike above. MSVC reports compilation warnings and errors on stdout.
            raise CompilationFailedException(e.command, e.stdout)

    def compile_and_link(self, source: str, include_dirs: List[str], output_file_name: str, args: List[str] = ()):
        return self._compile(
            include_dirs,
            args=(
                    [source]
                    + config.ADDITIONAL_LINKER_FLAGS.split()
                    + args
                    + ['/Fe' + output_file_name]
            ))

    def _compile(self, include_dirs: List[str], args: List[str]):
        all_args = ['/nologo', '/FS', '/W4', '/D_SCL_SECURE_NO_WARNINGS']
        if not is_coverage_collection_enabled():
            all_args.append('/WX')
        for include_dir in include_dirs:
            all_args.append('-I%s' % include_dir)
        all_args += config.ADDITIONAL_COMPILER_FLAGS.split()
        all_args += args
        stdout, stderr = run_command(self.executable, all_args)
        assert not stdout
        _extract_covered_source_branches(stderr)


if config.CXX_COMPILER_NAME == 'MSVC':
    compiler = MsvcCompiler()
    py2tmp_error_message_extraction_regex = 'error C2338: (.*)'
else:
    compiler = PosixCompiler()
    py2tmp_error_message_extraction_regex = 'static.assert(.*)'

_assert_helper = unittest.TestCase()


def _create_temporary_file(file_content: str, file_name_suffix: str = ''):
    file_descriptor, file_name = tempfile.mkstemp(text=True, suffix=file_name_suffix)
    file = os.fdopen(file_descriptor, mode='w')
    file.write(file_content)
    file.close()
    return file_name


def _cap_to_lines(s: str, n: int):
    lines = s.splitlines()
    if len(lines) <= n:
        return s
    else:
        return '\n'.join(lines[0:n] + ['...'])


def try_remove_temporary_file(filename: str):
    # noinspection PyBroadException
    try:
        os.remove(filename)
    except:
        # When running tests on Windows using Appveyor, the remove command fails for temporary files sometimes.
        # This shouldn't cause the tests to fail, so we ignore the exception and go ahead.
        pass


def expect_cpp_code_compile_error_helper(
        check_error_fun: Callable[[CompilationFailedException, Iterable[str], Iterable[str], Iterable[str]], Any],
        tmppy_source: str,
        object_file_content: ObjectFileContent,
        cxx_source: str):
    main_module = object_file_content.modules_by_name[TEST_MODULE_NAME]

    source_file_name = _create_temporary_file(cxx_source, file_name_suffix='.cpp')

    try:
        compiler.compile_discarding_output(
            source=source_file_name,
            include_dirs=[config.MPYL_INCLUDE_DIR],
            args=[])
        raise TestFailedException(textwrap.dedent('''\
            The test should have failed to compile, but it compiled successfully.
            
            TMPPy source:
            {tmppy_source}

            TMPPy IR1:
            {tmppy_ir1}
            
            C++ source code:
            {cxx_source}
            ''').format(tmppy_source=add_line_numbers(tmppy_source),
                        tmppy_ir1=str(main_module.ir1_module),
                        cxx_source=add_line_numbers(cxx_source)))
    except CompilationFailedException as e1:
        e = e1

    error_message = e.error_message
    error_message_lines = error_message.splitlines()
    # Different compilers output a different number of spaces when pretty-printing types.
    # When using libc++, sometimes std::foo identifiers are reported as std::__1::foo.
    normalized_error_message = error_message.replace(' ', '').replace('std::__1::', 'std::')
    normalized_error_message_lines = normalized_error_message.splitlines()
    error_message_head = _cap_to_lines(error_message, 40)

    check_error_fun(e, error_message_lines, error_message_head, normalized_error_message_lines)

    try_remove_temporary_file(source_file_name)


def expect_cpp_code_generic_compile_error(expected_error_regex: str,
                                          tmppy_source: str,
                                          object_file_contents: ObjectFileContent,
                                          cxx_source: str):
    """
    Tests that the given source produces the expected error during compilation.

    :param expected_error_regex: A regex used to match the _py2tmp error type,
           e.g. 'NoBindingFoundForAbstractClassError<ScalerImpl>'.
    :param cxx_source: The second part of the source code. This will be dedented.
    """

    main_module = object_file_contents.modules_by_name[TEST_MODULE_NAME]

    expected_error_regex = expected_error_regex.replace(' ', '')

    def check_error(e, error_message_lines, error_message_head, normalized_error_message_lines):
        for line in normalized_error_message_lines:
            if re.search(expected_error_regex, line):
                return
        raise TestFailedException(textwrap.dedent('''\
                Expected error {expected_error} but the compiler output did not contain that.
                Compiler command line: {compiler_command}
                Error message was:
                {error_message}

                TMPPy source:
                {tmppy_source}
                    
                TMPPy IR1:
                {tmppy_ir1}
                
                C++ source:
                {cxx_source}
                ''').format(expected_error=expected_error_regex,
                            compiler_command=e.command,
                            tmppy_source=add_line_numbers(tmppy_source),
                            tmppy_ir1=str(main_module.ir1_module),
                            cxx_source=add_line_numbers(cxx_source),
                            error_message=error_message_head))

    expect_cpp_code_compile_error_helper(check_error, tmppy_source, object_file_contents, cxx_source)


def expect_cpp_code_compile_error(
        expected_py2tmp_error_regex: str,
        expected_py2tmp_error_desc_regex: str,
        tmppy_source: str,
        object_file_content: ObjectFileContent,
        cxx_source: str):
    """
    Tests that the given source produces the expected error during compilation.

    :param expected_py2tmp_error_regex: A regex used to match the _py2tmp error type,
           e.g. 'NoBindingFoundForAbstractClassError<ScalerImpl>'.
    :param expected_py2tmp_error_desc_regex: A regex used to match the _py2tmp error description,
           e.g. 'No explicit binding was found for C, and C is an abstract class'.
    :param cxx_source: The C++ source code. This will be dedented.
    """
    if '\n' in expected_py2tmp_error_regex:
        raise Exception('expected_py2tmp_error_regex should not contain newlines')
    if '\n' in expected_py2tmp_error_desc_regex:
        raise Exception('expected_py2tmp_error_desc_regex should not contain newlines')

    main_module = object_file_content.modules_by_name[TEST_MODULE_NAME]

    expected_py2tmp_error_regex = expected_py2tmp_error_regex.replace(' ', '')

    def check_error(e, error_message_lines, error_message_head, normalized_error_message_lines):
        for line_number, line in enumerate(normalized_error_message_lines):
            match = re.search('tmppy::impl::(.*Error<.*>)', line)
            if match:
                actual_py2tmp_error_line_number = line_number
                actual_py2tmp_error = match.groups()[0]
                if config.CXX_COMPILER_NAME == 'MSVC':
                    # MSVC errors are of the form:
                    #
                    # C:\Path\To\header\foo.h(59): note: see reference to class template instantiation 'tmppy::impl::MyError<X, Y>' being compiled
                    #         with
                    #         [
                    #              X=int,
                    #              Y=double
                    #         ]
                    #
                    # So we need to parse the following few lines and use them to replace the placeholder types in the tmppy error type.
                    try:
                        replacement_lines = []
                        if normalized_error_message_lines[line_number + 1].strip() == 'with':
                            for line1 in itertools.islice(normalized_error_message_lines, line_number + 3, None):
                                line1 = line1.strip()
                                if line1 == ']':
                                    break
                                if line1.endswith(','):
                                    line1 = line1[:-1]
                                replacement_lines.append(line1)
                        for replacement_line in replacement_lines:
                            match = re.search('([A-Za-z0-9_-]*)=(.*)', replacement_line)
                            if not match:
                                raise Exception('Failed to parse replacement line: %s' % replacement_line) from e
                            (type_variable, type_expression) = match.groups()
                            actual_py2tmp_error = re.sub(r'\b' + type_variable + r'\b', type_expression,
                                                         actual_py2tmp_error)
                    except Exception:
                        raise Exception('Failed to parse MSVC template type arguments')
                break
        else:
            raise TestFailedException(textwrap.dedent('''\
                    Expected error {expected_error} but the compiler output did not contain user-facing _py2tmp errors.
                    Compiler command line: {compiler_command}
                    Error message was:
                    {error_message}

                    TMPPy source:
                    {tmppy_source}
                    
                    TMPPy IR1:
                    {tmppy_ir1}
                    
                    C++ source code:
                    {cxx_source}
                    ''').format(expected_error=expected_py2tmp_error_regex,
                                compiler_command=e.command,
                                tmppy_source=add_line_numbers(tmppy_source),
                                tmppy_ir1=str(main_module.ir1_module),
                                cxx_source=add_line_numbers(cxx_source),
                                error_message=error_message_head))

        for line_number, line in enumerate(error_message_lines):
            match = re.search(py2tmp_error_message_extraction_regex, line)
            if match:
                actual_static_assert_error_line_number = line_number
                actual_static_assert_error = match.groups()[0]
                break
        else:
            raise TestFailedException(textwrap.dedent('''\
                    Expected error {expected_error} but the compiler output did not contain static_assert errors.
                    Compiler command line: {compiler_command}
                    Error message was:
                    {error_message}
                    
                    TMPPy source:
                    {tmppy_source}
                    
                    TMPPy IR1:
                    {tmppy_ir1}
                    
                    C++ source code:
                    {cxx_source}
                    ''').format(expected_error=expected_py2tmp_error_regex,
                                compiler_command=e.command,
                                tmppy_source=add_line_numbers(tmppy_source),
                                tmppy_ir1=str(main_module.ir1_module),
                                cxx_source=add_line_numbers(cxx_source),
                                error_message=error_message_head))

        try:
            regex_search_result = re.search(expected_py2tmp_error_regex, actual_py2tmp_error)
        except Exception as e:
            raise Exception('re.search() failed for regex \'%s\'' % expected_py2tmp_error_regex) from e
        if not regex_search_result:
            raise TestFailedException(textwrap.dedent('''\
                    The compilation failed as expected, but with a different error type.
                    Expected _py2tmp error type:    {expected_py2tmp_error_regex}
                    Error type was:               {actual_py2tmp_error}
                    Expected static assert error: {expected_py2tmp_error_desc_regex}
                    Static assert was:            {actual_static_assert_error}
                    
                    Error message was:
                    {error_message}
                    
                    TMPPy source:
                    {tmppy_source}
                    
                    TMPPy IR1:
                    {tmppy_ir1}
                    
                    C++ source code:
                    {cxx_source}
                    '''.format(expected_py2tmp_error_regex=expected_py2tmp_error_regex,
                               actual_py2tmp_error=actual_py2tmp_error,
                               expected_py2tmp_error_desc_regex=expected_py2tmp_error_desc_regex,
                               actual_static_assert_error=actual_static_assert_error,
                               tmppy_source=add_line_numbers(tmppy_source),
                               tmppy_ir1=str(main_module.ir1_module),
                               cxx_source=add_line_numbers(cxx_source),
                               error_message=error_message_head)))
        try:
            regex_search_result = re.search(expected_py2tmp_error_desc_regex, actual_static_assert_error)
        except Exception as e:
            raise Exception('re.search() failed for regex \'%s\'' % expected_py2tmp_error_desc_regex) from e
        if not regex_search_result:
            raise TestFailedException(textwrap.dedent('''\
                    The compilation failed as expected, but with a different error message.
                    Expected _py2tmp error type:    {expected_py2tmp_error_regex}
                    Error type was:               {actual_py2tmp_error}
                    Expected static assert error: {expected_py2tmp_error_desc_regex}
                    Static assert was:            {actual_static_assert_error}
                    
                    Error message:
                    {error_message}
                    
                    TMPPy source:
                    {tmppy_source}
                    
                    TMPPy IR1:
                    {tmppy_ir1}
                    
                    C++ source code:
                    {cxx_source}
                    '''.format(expected_py2tmp_error_regex=expected_py2tmp_error_regex,
                               actual_py2tmp_error=actual_py2tmp_error,
                               expected_py2tmp_error_desc_regex=expected_py2tmp_error_desc_regex,
                               actual_static_assert_error=actual_static_assert_error,
                               tmppy_source=add_line_numbers(tmppy_source),
                               tmppy_ir1=str(main_module.ir1_module),
                               cxx_source=add_line_numbers(cxx_source),
                               error_message=error_message_head)))

        # 6 is just a constant that works for both g++ (<=6.0.0 at least) and clang++ (<=4.0.0 at least).
        # It might need to be changed.
        if actual_py2tmp_error_line_number > 6 or actual_static_assert_error_line_number > 6:
            raise TestFailedException(textwrap.dedent('''\
                    The compilation failed with the expected message, but the error message contained too many lines before the relevant ones.
                    The error type was reported on line {actual_py2tmp_error_line_number} of the message (should be <=6).
                    The static assert was reported on line {actual_static_assert_error_line_number} of the message (should be <=6).
                    Error message:
                    {error_message}

                    TMPPy source:
                    {tmppy_source}
                    
                    TMPPy IR1:
                    {tmppy_ir1}
                    
                    C++ source code:
                    {cxx_source}
                    '''.format(actual_py2tmp_error_line_number=actual_py2tmp_error_line_number,
                               actual_static_assert_error_line_number=actual_static_assert_error_line_number,
                               tmppy_source=add_line_numbers(tmppy_source),
                               tmppy_ir1=str(main_module.ir1_module),
                               cxx_source=add_line_numbers(cxx_source),
                               error_message=error_message_head)))

        for line in error_message_lines[:max(actual_py2tmp_error_line_number, actual_static_assert_error_line_number)]:
            if re.search('tmppy::impl', line):
                raise TestFailedException(
                    'The compilation failed with the expected message, but the error message contained some metaprogramming types in the output (besides Error). Error message:\n%s' + error_message_head)

    expect_cpp_code_compile_error_helper(check_error, tmppy_source, object_file_content, cxx_source)


def expect_cpp_code_success(tmppy_source: str,
                            object_file_content: ObjectFileContent,
                            cxx_source: str,
                            main_module_name=TEST_MODULE_NAME):
    """
    Tests that the given source compiles and runs successfully.

    :param cxx_source: The C++ source code. This will be dedented.
    """

    main_module = object_file_content.modules_by_name[main_module_name]

    if 'main(' not in cxx_source:
        cxx_source += textwrap.dedent('''
            int main() {
            }
            ''')

    source_file_name = _create_temporary_file(cxx_source, file_name_suffix='.cpp')
    executable_suffix = {'posix': '', 'nt': '.exe'}[os.name]
    output_file_name = _create_temporary_file('', executable_suffix)

    e = None

    try:
        compiler.compile_and_link(
            source=source_file_name,
            include_dirs=[config.MPYL_INCLUDE_DIR],
            output_file_name=output_file_name,
            args=[])
    except CommandFailedException as e1:
        e = e1

    if e:
        raise TestFailedException(textwrap.dedent('''\
                The generated C++ source did not compile.
                Compiler command line: {compiler_command}
                Error message was:
                {error_message}
                
                TMPPy source:
                {tmppy_source}
                
                TMPPy IR1:
                {tmppy_ir1}
                
                C++ source:
                {cxx_source}
                ''').format(compiler_command=e.command,
                            tmppy_source=add_line_numbers(tmppy_source),
                            tmppy_ir1=str(main_module.ir1_module),
                            cxx_source=add_line_numbers(cxx_source),
                            error_message=_cap_to_lines(e.stderr, 40)))

    try:
        run_compiled_executable(output_file_name)
    except CommandFailedException as e1:
        e = e1

    if e:
        raise TestFailedException(textwrap.dedent('''\
                The generated C++ executable did not run successfully.
                stderr was:
                {error_message}

                TMPPy source:
                {tmppy_source}
                
                C++ source:
                {cxx_source}
                ''').format(tmppy_source=add_line_numbers(tmppy_source),
                            cxx_source=add_line_numbers(cxx_source),
                            error_message=_cap_to_lines(e.stderr, 40)))

    # Note that we don't delete the temporary files if the test failed. This is intentional, keeping them around helps debugging the failure.
    try_remove_temporary_file(source_file_name)
    try_remove_temporary_file(output_file_name)


def _get_function_body(f):
    # The body of some tests is a multiline string because they would otherwise cause the pytest test file to fail
    # parsing.
    if f.__doc__:
        return textwrap.dedent(f.__doc__)

    source_code, _ = inspect.getsourcelines(f)

    # Skip the annotation and the line where the function is defined.
    expected_line = 'def %s(tmppy: TmppyFixture):\n' % f.__name__
    expected_line2 = 'def %s():\n' % f.__name__
    while source_code[0] not in (expected_line, expected_line2):
        source_code = source_code[1:]
    source_code = source_code[1:]

    return textwrap.dedent(''.join(source_code))

def builtins_object_file_path() -> str:
    if is_coverage_collection_enabled():
        return './builtins_for_coverage.tmppyc'
    else:
        return './builtins.tmppyc'

@lru_cache()
def get_builtins_object_file_content():
    with open(builtins_object_file_path(), 'rb') as file:
        object_file = pickle.loads(file.read())
    assert isinstance(object_file, ObjectFileContent)
    return object_file


class _GetIR2InstrumentedBranches(ir2.Visitor):
    def __init__(self):
        self.branches: Dict[Tuple[int, int], List] = defaultdict(list)

    def _add_branch(self, branch: SourceBranch, ir_element: Any):
        self.branches[(branch.source_line, branch.dest_line)].append(ir_element)

    def visit_match_case(self, match_case: ir2.ir.MatchCase):
        super().visit_match_case(match_case)
        self._add_branch(match_case.match_case_start_branch, match_case)
        self._add_branch(match_case.match_case_end_branch, match_case)

    def visit_list_comprehension(self, expr: ir2.ir.ListComprehension):
        super().visit_list_comprehension(expr)
        self._add_branch(expr.loop_body_start_branch, expr)
        self._add_branch(expr.loop_exit_branch, expr)

    def visit_set_comprehension(self, expr: ir2.ir.SetComprehension):
        super().visit_set_comprehension(expr)
        self._add_branch(expr.loop_body_start_branch, expr)
        self._add_branch(expr.loop_exit_branch, expr)

    def visit_assert(self, stmt: ir2.ir.Assert):
        super().visit_assert(stmt)
        self._add_branch(stmt.source_branch, stmt)

    def visit_assignment(self, stmt: ir2.ir.Assignment):
        super().visit_assignment(stmt)
        self._add_branch(stmt.source_branch, stmt)

    def visit_unpacking_assignment(self, stmt: ir2.ir.UnpackingAssignment):
        super().visit_unpacking_assignment(stmt)
        self._add_branch(stmt.source_branch, stmt)

    def visit_return_stmt(self, stmt: ir2.ir.ReturnStmt):
        super().visit_return_stmt(stmt)
        self._add_branch(stmt.source_branch, stmt)

    def visit_raise_stmt(self, stmt: ir2.ir.RaiseStmt):
        super().visit_raise_stmt(stmt)
        self._add_branch(stmt.source_branch, stmt)

    def visit_try_except_stmt(self, stmt: ir2.ir.TryExcept):
        super().visit_try_except_stmt(stmt)
        self._add_branch(stmt.try_branch, stmt)
        self._add_branch(stmt.except_branch, stmt)

    def visit_custom_type_defn(self, custom_type: ir2.ir.CustomType):
        super().visit_custom_type_defn(custom_type)
        for branch in custom_type.constructor_source_branches:
            self._add_branch(branch, custom_type)

    def visit_pass_stmt(self, stmt: ir2.ir.PassStmt):
        super().visit_pass_stmt(stmt)
        self._add_branch(stmt.source_branch, stmt)

class _GetIR1InstrumentedBranches(ir1.Visitor):
    def __init__(self) -> None:
        self.branches: Dict[Tuple[int, int], List] = defaultdict(list)

    def _add_branch(self, branch: Optional[SourceBranch], ir_element: Any):
        if branch:
            self.branches[(branch.source_line, branch.dest_line)].append(ir_element)

    def visit_match_case(self, match_case: ir1.ir.MatchCase):
        super().visit_match_case(match_case)
        self._add_branch(match_case.match_case_start_branch, match_case)
        self._add_branch(match_case.match_case_end_branch, match_case)

    def visit_list_comprehension_expr(self, expr: ir1.ir.ListComprehensionExpr):
        super().visit_list_comprehension_expr(expr)
        self._add_branch(expr.loop_body_start_branch, expr)
        self._add_branch(expr.loop_exit_branch, expr)

    def visit_assert(self, stmt: ir1.ir.Assert):
        super().visit_assert(stmt)
        self._add_branch(stmt.source_branch, stmt)

    def visit_assignment(self, stmt: ir1.ir.Assignment):
        super().visit_assignment(stmt)
        self._add_branch(stmt.source_branch, stmt)

    def visit_unpacking_assignment(self, stmt: ir1.ir.UnpackingAssignment):
        super().visit_unpacking_assignment(stmt)
        self._add_branch(stmt.source_branch, stmt)

    def visit_return_stmt(self, stmt: ir1.ir.ReturnStmt):
        super().visit_return_stmt(stmt)
        self._add_branch(stmt.source_branch, stmt)

    def visit_custom_type_definition(self, custom_type: ir1.ir.CustomType):
        super().visit_custom_type_definition(custom_type)
        for branch in custom_type.constructor_source_branches:
            self._add_branch(branch, custom_type)

    def visit_pass_stmt(self, stmt: ir1.ir.PassStmt):
        super().visit_pass_stmt(stmt)
        self._add_branch(stmt.source_branch, stmt)

class _GetIR0InstrumentedBranches(ir0.Visitor):
    def __init__(self) -> None:
        self.branches: Dict[Tuple[int, int], List] = defaultdict(list)

    def _add_branch(self, branch: Optional[SourceBranch], ir_element: Any):
        if branch:
            self.branches[(branch.source_line, branch.dest_line)].append(ir_element)

    def visit_no_op_stmt(self, stmt: ir0.ir.NoOpStmt):
        self._add_branch(stmt.source_branch, stmt)

class _FakeByteParser:
    def __init__(self, num_lines: int):
        self.num_lines = num_lines

    def _find_statements(self) -> Set[int]:
        return set(range(self.num_lines))

def _extract_all_branches(python_source: str):
    parser = PythonParser(text=python_source)
    # This is a hack to force-disable Python optimization, otherwise Python will optimize away statements like
    # "if False: ..." and that would cause unexpected diffs in the coverage branches. Even when passing optimize=0 to
    # compile().
    parser._byte_parser = _FakeByteParser(num_lines=len(python_source.splitlines())+1)
    parser.parse_source()
    return parser.arcs()

class BranchExplainer:
    def __init__(self, python_source: str):
        _, tmp_file = tempfile.mkstemp(suffix='.py', text=True)
        with open(tmp_file, 'w') as f:
            f.write(python_source)
        config = CoverageConfig()
        config.branch = True
        coverage = Coverage(branch=True)
        coverage.start()
        coverage.stop()

        self.tmp_file = tmp_file
        self.delegate = PythonFileReporter(morf=tmp_file, coverage=coverage)

    def explain(self, start: int, end: int):
        return self.delegate.missing_arc_description(start, end)

    def __enter__(self) -> 'BranchExplainer':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.remove(self.tmp_file)

def compile(python_source: str,
            context_object_file_content: ObjectFileContent = ObjectFileContent({}),
            module_name=TEST_MODULE_NAME):
    object_file_content = compile_source_code(module_name=module_name, source_code=python_source,
                                              context_object_file_content=merge_object_files(
                                                  [get_builtins_object_file_content(), context_object_file_content]),
                                              include_intermediate_irs_for_debugging=True,
                                              coverage_collection_enabled=is_coverage_collection_enabled())
    if module_name == TEST_MODULE_NAME:
        module_info = object_file_content.modules_by_name[TEST_MODULE_NAME]
        expected_branches = _extract_all_branches(python_source)

        for visitor, visit, ir_name in (
                (_GetIR2InstrumentedBranches(), lambda visitor: visitor.visit_module(module_info.ir2_module), 'IR2'),
                (_GetIR1InstrumentedBranches(), lambda visitor: visitor.visit_module(module_info.ir1_module), 'IR1'),
                (_GetIR0InstrumentedBranches(), lambda visitor: visitor.visit_header(module_info.ir0_header_before_optimization), 'IR0'),
        ):
            visit(visitor)
            actual_branches = visitor.branches

            if actual_branches.keys() != expected_branches:
                with BranchExplainer(python_source) as explainer:
                    raise TestFailedException(
                        'Detected a wrong set of instrumentable branches in %s.\n' % ir_name
                        + 'Source code:\n'
                        + add_line_numbers(python_source) + '\n'
                        + 'Generated branches that should not be generated:\n'
                        + ''.join('* %s: %s, in the IR nodes:\n%s\n' % (branch,
                                                                        explainer.explain(branch[0], branch[1]),
                                                                        ', '.join(str(element)
                                                                                  for element in elements))
                                  for branch, elements in sorted(actual_branches.items())
                                  if branch not in expected_branches)
                        + 'Not generated branches that should have been generated:\n'
                        + ''.join('* %s: %s\n' % (branch,
                                                  explainer.explain(branch[0], branch[1]))
                                  for branch in sorted(expected_branches)
                                  if branch not in actual_branches)
                        + 'Matching branches (generated correctly):\n'
                        + ''.join('* %s: %s (in nodes: %s)\n' % (branch,
                                                                 explainer.explain(branch[0], branch[1]),
                                                                 ', '.join(element.__class__.__name__
                                                                           for element in elements))
                                  for branch, elements in sorted(actual_branches.items())
                                  if branch in expected_branches))

    return object_file_content


def link(object_file_content: ObjectFileContent,
         main_module_name=TEST_MODULE_NAME):
    from _py2tmp.compiler._link import link
    return link(main_module_name=main_module_name,
                object_file_content=object_file_content,
                coverage_collection_enabled=is_coverage_collection_enabled())


def _convert_to_cpp_expecting_success(tmppy_source: str,
                                      allow_toplevel_static_asserts_after_optimization: bool,
                                      context_object_file_content: ObjectFileContent):
    object_file_content = None
    try:
        object_file_content = compile(tmppy_source, context_object_file_content)
        e = None
    except CompilationError as e1:
        e = e1
    if e:
        raise TestFailedException(textwrap.dedent('''\
                The conversion from TMPPy to C++ failed.
                stderr was:
                {error_message}
                
                TMPPy source:
                {tmppy_source}
                ''').format(tmppy_source=add_line_numbers(tmppy_source),
                            error_message=e.args[0]))

    assert object_file_content

    if not allow_toplevel_static_asserts_after_optimization:
        def identifier_generator_fun():
            for i in itertools.count():
                yield 'TmppyInternal2_' + str(i)

        identifier_generator = identifier_generator_fun()
        merged_header_for_linking = compute_merged_header_for_linking(main_module_name=TEST_MODULE_NAME,
                                                                      object_file_content=object_file_content,
                                                                      identifier_generator=identifier_generator,
                                                                      coverage_collection_enabled=is_coverage_collection_enabled())

        for elem in merged_header_for_linking.toplevel_content:
            if isinstance(elem, ir0.ir.StaticAssert):
                # Re-run the ir0_optimization in verbose mode so that we output more detail on the error.
                ConfigurationKnobs.reached_max_num_remaining_loops_counter = 0
                ConfigurationKnobs.verbose = True
                ConfigurationKnobs.max_num_optimization_steps = -1
                object_file_content = compile(tmppy_source, context_object_file_content)
                main_module = object_file_content.modules_by_name[TEST_MODULE_NAME]
                cpp_source = link(object_file_content)

                if ConfigurationKnobs.reached_max_num_remaining_loops_counter:
                    raise TestFailedException('Reached max_num_remaining_loops_counter.')

                raise TestFailedException(textwrap.dedent('''\
                        The conversion from TMPPy to C++ succeeded, but there were static_assert()s left after ir0_optimization.
                        
                        TMPPy source:
                        {tmppy_source}
                        
                        TMPPy IR1:
                        {tmppy_ir1}
                        
                        Generated C++ source:
                        {cpp_source}
                        ''').format(tmppy_source=add_line_numbers(tmppy_source),
                                    tmppy_ir1=str(main_module.ir1_module),
                                    cpp_source=cpp_source))

    cpp_source = link(object_file_content)
    return object_file_content, cpp_source


def assert_compilation_succeeds(extra_cpp_prelude: str='', always_allow_toplevel_static_asserts_after_optimization: bool=False):
    def eval(f):
        @wraps(f)
        def wrapper(tmppy: TmppyFixture = TmppyFixture(ObjectFileContent({}))):
            def run_test(allow_toplevel_static_asserts_after_optimization: bool):
                tmppy_source = _get_function_body(f)
                object_file_content, cpp_source = _convert_to_cpp_expecting_success(tmppy_source,
                                                                                    allow_toplevel_static_asserts_after_optimization or always_allow_toplevel_static_asserts_after_optimization,
                                                                                    tmppy.tmppyc_files)
                expect_cpp_code_success(tmppy_source, object_file_content, extra_cpp_prelude + cpp_source)
                return cpp_source

            run_test_with_optional_optimization(run_test)

        return wrapper

    return eval


def assert_code_optimizes_to(expected_cpp_source: str, extra_cpp_prelude=''):
    def eval(f):
        @wraps(f)
        def wrapper(tmppy: TmppyFixture = TmppyFixture(ObjectFileContent({}))):
            tmppy_source = _get_function_body(f)

            def run_test(allow_toplevel_static_asserts_after_optimization: bool):
                object_file_content, cpp_source = _convert_to_cpp_expecting_success(tmppy_source,
                                                                                    allow_toplevel_static_asserts_after_optimization=True,
                                                                                    context_object_file_content=tmppy.tmppyc_files)
                expect_cpp_code_success(tmppy_source, object_file_content, extra_cpp_prelude + cpp_source)
                return cpp_source

            run_test_with_optional_optimization(run_test)

            try:
                ConfigurationKnobs.verbose = DEFAULT_VERBOSE_SETTING
                ConfigurationKnobs.max_num_optimization_steps = -1
                ConfigurationKnobs.reached_max_num_remaining_loops_counter = 0
                object_file_content, cpp_source = _convert_to_cpp_expecting_success(tmppy_source,
                                                                                    allow_toplevel_static_asserts_after_optimization=True,
                                                                                    context_object_file_content=tmppy.tmppyc_files)
                main_module = object_file_content.modules_by_name[TEST_MODULE_NAME]

                cpp_source_lines = cpp_source.splitlines(True)
                assert cpp_source_lines[0:3] == [
                    '#include <tmppy/tmppy.h>\n',
                    '#include <tuple>\n',
                    '#include <type_traits>\n',
                ], cpp_source_lines[0:3]
                cpp_source = ''.join(cpp_source_lines[3:])

                assert expected_cpp_source[0] == '\n'
                if cpp_source != expected_cpp_source[1:]:
                    raise TestFailedException(textwrap.dedent('''\
                            The generated code didn't match the expected code.
                            
                            TMPPy source:
                            {tmppy_source}
                            
                            TMPPy IR1:
                            {tmppy_ir1}
                            
                            Generated C++ source:
                            {cpp_source}
                            
                            Expected C++ source:
                            {expected_cpp_source}
                            
                            Diff:
                            {cpp_source_diff}
                            ''').format(tmppy_source=add_line_numbers(tmppy_source),
                                        tmppy_ir1=str(main_module.ir1_module),
                                        cpp_source=str(cpp_source),
                                        expected_cpp_source=str(expected_cpp_source[1:]),
                                        cpp_source_diff=''.join(
                                            difflib.unified_diff(expected_cpp_source[1:].splitlines(True),
                                                                 cpp_source.splitlines(True),
                                                                 fromfile='expected.h',
                                                                 tofile='actual.h'))))

                if ConfigurationKnobs.reached_max_num_remaining_loops_counter != 0:
                    raise TestFailedException(
                        'The generated code was the expected one, but hit max_num_remaining_loops')

            except TestFailedException as e:
                [message] = e.args
                pytest.fail(message, pytrace=False)

        return wrapper

    return eval


# TODO: Check that the error is s reported on the desired line (moving the regex to a comment in the test).
def assert_compilation_fails_with_generic_error(expected_error_regex: str, allow_reaching_max_optimization_loops=False):
    def eval(f):
        @wraps(f)
        def wrapper(tmppy: TmppyFixture = TmppyFixture(ObjectFileContent({}))):
            def run_test(allow_toplevel_static_asserts_after_optimization: bool):
                tmppy_source = _get_function_body(f)
                object_file_content, cpp_source = _convert_to_cpp_expecting_success(tmppy_source,
                                                                                    allow_toplevel_static_asserts_after_optimization=True,
                                                                                    context_object_file_content=tmppy.tmppyc_files)
                expect_cpp_code_generic_compile_error(
                    expected_error_regex,
                    tmppy_source,
                    object_file_content,
                    cpp_source)
                return cpp_source

            run_test_with_optional_optimization(run_test, allow_reaching_max_optimization_loops)

        return wrapper

    return eval


# TODO: Check that the error is s reported on the desired line (moving the regex to a comment in the test).
def assert_compilation_fails_with_static_assert_error(expected_error_regex: str):
    def eval(f):
        @wraps(f)
        def wrapper(tmppy: TmppyFixture = TmppyFixture(ObjectFileContent({}))):
            def run_test(allow_toplevel_static_asserts_after_optimization: bool):
                tmppy_source = _get_function_body(f)
                object_file_content, cpp_source = _convert_to_cpp_expecting_success(tmppy_source,
                                                                                    allow_toplevel_static_asserts_after_optimization=True,
                                                                                    context_object_file_content=tmppy.tmppyc_files)
                expect_cpp_code_generic_compile_error(
                    r'(error: static assertion failed: |error: static_assert failed .|static_assert failed due to requirement.*)' + expected_error_regex,
                    tmppy_source,
                    object_file_content,
                    cpp_source)
                return cpp_source

            run_test_with_optional_optimization(run_test)

        return wrapper

    return eval


def _split_list(l, num_elems_in_chunk):
    args = [iter(l)] * num_elems_in_chunk
    return list(itertools.zip_longest(*args))


def _get_line_from_diagnostic(diagnostic):
    matches = re.match('<unknown>:([0-9]*):', diagnostic)
    return int(matches.group(1))


def check_compilation_error(e: CompilationError,
                            tmppy_source: str):
    actual_source_lines = []
    expected_error_regex = None
    expected_error_line = None
    expected_note_by_line = dict()
    for line_index, line in enumerate(tmppy_source.splitlines()):
        error_regex_marker = ' # error: '
        note_regex_marker = ' # note: '
        if error_regex_marker in line:
            if expected_error_regex:
                raise TestFailedException('Multiple expected errors in the same test are not supported')
            [line, expected_error_regex] = line.split(error_regex_marker)
            expected_error_line = line_index + 1
        elif note_regex_marker in line:
            [line, expected_note_regex] = line.split(note_regex_marker)
            expected_note_by_line[line_index + 1] = expected_note_regex
        actual_source_lines.append(line)

    if not expected_error_regex:
        raise TestFailedException(textwrap.dedent('''\
                assert_conversion_fails was used, but no expected error regex was found.
                
                TMPPy source:
                {tmppy_source}
                ''').format(tmppy_source=add_line_numbers(tmppy_source)))

    # py2tmp diagnostics take up 3 lines each, e.g.:
    # <unknown>:2:11: error: Empty lists are not currently supported.
    #   return []
    #          ^
    py2tmp_diagnostics = _split_list(e.args[0].splitlines(), num_elems_in_chunk=3)
    error_diagnostic = py2tmp_diagnostics[0]

    expected_error_regex = '<unknown>:[0-9]*:[0-9]*: error: ' + expected_error_regex
    if not re.match(expected_error_regex, error_diagnostic[0]):
        raise TestFailedException(textwrap.dedent('''\
                An exception was thrown, but it didn\'t match the expected error regex.
                Expected error regex: {expected_error_regex}
                Actual error:
                {actual_error}
                
                TMPPy source:
                {tmppy_source}
                ''').format(expected_error_regex=expected_error_regex,
                            actual_error='\n'.join(error_diagnostic),
                            tmppy_source=add_line_numbers(tmppy_source)))

    matches = re.match('<unknown>:([0-9]*):', error_diagnostic[0])
    actual_error_line = int(matches.group(1))
    if expected_error_line != actual_error_line:
        raise TestFailedException(textwrap.dedent('''\
                An exception matching the expected regex was thrown, but the error mentioned the wrong line: {actual_error_line} was reported instead of {expected_error_line}
                Expected error regex: {expected_error_regex}
                Actual error:
                {actual_error}
                
                TMPPy source:
                {tmppy_source}
                ''').format(actual_error_line=actual_error_line,
                            expected_error_line=expected_error_line,
                            expected_error_regex=expected_error_regex,
                            actual_error='\n'.join(error_diagnostic),
                            tmppy_source=add_line_numbers(tmppy_source)))

    actual_note_by_line = {_get_line_from_diagnostic(note[0]): note
                           for note in py2tmp_diagnostics[1:]}
    for expected_note_line, expected_note_regex in expected_note_by_line.items():
        actual_note = actual_note_by_line.get(expected_note_line)
        if not actual_note:
            raise Exception(
                'Expected the note %s on line %s but no note was emitted mentioning this line. Emitted notes: %s' % (
                    expected_note_regex, expected_note_line, json.dumps(actual_note_by_line, indent=4)))
        expected_note_regex = '<unknown>:[0-9]*:[0-9]*: note: ' + expected_note_regex
        if not re.match(expected_note_regex, actual_note[0]):
            raise TestFailedException(textwrap.dedent('''\
                    A note diagnostic was emitted, but it didn\'t match the expected note regex.
                    Expected note regex: {expected_note_regex}
                    Actual note:
                    {actual_note}
                    
                    TMPPy source:
                    {tmppy_source}
                    ''').format(expected_note_regex=expected_note_regex,
                                actual_note='\n'.join(actual_note),
                                tmppy_source=add_line_numbers(tmppy_source)))

    for actual_note_line, actual_note in actual_note_by_line.items():
        expected_note = expected_note_by_line.get(actual_note_line)
        if not expected_note:
            raise TestFailedException(textwrap.dedent('''\
                    Unexpected note:
                    {actual_note}
                    
                    TMPPy source:
                    {tmppy_source}
                    ''').format(actual_note='\n'.join(actual_note),
                                tmppy_source=add_line_numbers(tmppy_source)))


def assert_conversion_fails(f):
    @wraps(f)
    def wrapper(tmppy: TmppyFixture = TmppyFixture(ObjectFileContent({}))):
        def run_test(allow_toplevel_static_asserts_after_optimization: bool):
            tmppy_source = _get_function_body(f)
            e = None
            object_file_content = None
            try:
                object_file_content = compile(tmppy_source, tmppy.tmppyc_files)
            except CompilationError as e1:
                e = e1

            if not e:
                main_module = object_file_content.modules_by_name[TEST_MODULE_NAME]
                raise TestFailedException(textwrap.dedent('''\
                        Expected an exception, but the _py2tmp conversion completed successfully.
                        TMPPy source:
                        {tmppy_source}
    
                        TMPPy IR1:
                        {tmppy_ir1}
                        ''').format(tmppy_source=add_line_numbers(tmppy_source),
                                    tmppy_ir1=str(main_module.ir1_module)))

            check_compilation_error(e, tmppy_source)

            return '(no C++ source)'

        run_test_with_optional_optimization(run_test)

    return wrapper


# Note: this is not the main function of this file, it's meant to be used as main function from test_*.py files.
def main():
    absltest.main(*sys.argv)
