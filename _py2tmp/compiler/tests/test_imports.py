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

from _py2tmp.compiler.output_files import merge_object_files
from _py2tmp.compiler.stages import CompilationError
from _py2tmp.compiler.testing import compile, link, expect_cpp_code_success, check_compilation_error, \
    assert_conversion_fails
from py2tmp.testing import main, assert_compilation_succeeds


@assert_conversion_fails
def test_import_unsupported_module():
    from os import path  # error: Module not found. The only modules that can be imported are the builtin modules \(dataclasses, tmppy, typing\) and the modules in the specified object files \(none\)

@assert_conversion_fails
def test_import_unsupported_symbol():
    from typing import MutableSequence  # error: The only supported imports from typing are: Callable, List, Set.

@assert_conversion_fails
def test_import_module_as_alias_error():
    import typing as x  # error: TMPPy only supports imports of the form "from some_module import some_symbol, some_other_symbol".

@assert_conversion_fails
def test_import_symbol_as_alias_error():
    from typing import Type as x  # error: TMPPy only supports imports of the form "from some_module import some_symbol, some_other_symbol".

@assert_compilation_succeeds()
def test_import_multiple_ok():
    from typing import List, Callable

def test_import_from_tmppy_module_ok():
    module_foo_name = 'foo'
    module_foo_source = '''\
def f(b: bool):
    if b:
        return 7
    else:
        return 43
'''
    compiled_module_foo = compile(module_foo_source,
                                  module_name=module_foo_name)

    module_bar_name = 'bar'
    module_bar_source = '''\
from foo import f
assert f(False) == 43
'''

    compiled_module_bar = compile(module_bar_source,
                                  module_name=module_bar_name,
                                  context_object_file_content=compiled_module_foo)

    cpp_source = link(compiled_module_bar, main_module_name=module_bar_name)

    expect_cpp_code_success(tmppy_source=module_foo_source + module_bar_source,
                            object_file_content=compiled_module_bar,
                            cxx_source=cpp_source,
                            main_module_name=module_bar_name)

def test_import_from_tmppy_module_name_not_found_error():
    module_foo_name = 'foo'
    module_foo_source = '''\
def f(b: bool):
    if b:
        return 7
    else:
        return 43
'''
    compiled_module_foo = compile(module_foo_source,
                                  module_name=module_foo_name)

    module_bar_name = 'bar'
    module_bar_source = '''\
from foo import f
assert f(False) == 43
'''

    compiled_module_bar = compile(module_bar_source,
                                  module_name=module_bar_name,
                                  context_object_file_content=compiled_module_foo)

    cpp_source = link(compiled_module_bar, main_module_name=module_bar_name)

    expect_cpp_code_success(tmppy_source=module_foo_source + module_bar_source,
                            object_file_content=compiled_module_bar,
                            cxx_source=cpp_source,
                            main_module_name=module_bar_name)

def test_import_from_tmppy_module_chain_ok():
    module_foo_name = 'foo'
    module_foo_source = '''\
def f(b: bool):
    return 7
'''
    compiled_module_foo = compile(module_foo_source,
                                  module_name=module_foo_name)

    module_bar_name = 'bar'
    module_bar_source = '''\
from foo import f
def g(b: bool):
    return f(b)
'''

    compiled_module_bar = compile(module_bar_source,
                                  module_name=module_bar_name,
                                  context_object_file_content=compiled_module_foo)

    module_baz_name = 'baz'
    module_baz_source = '''\
from bar import g
assert g(True) == 7
'''

    compiled_module_baz = compile(module_baz_source,
                                  module_name=module_baz_name,
                                  context_object_file_content=compiled_module_bar)

    cpp_source = link(compiled_module_baz, main_module_name=module_baz_name)

    expect_cpp_code_success(tmppy_source=module_foo_source + module_bar_source + module_baz_source,
                            object_file_content=compiled_module_baz,
                            cxx_source=cpp_source,
                            main_module_name=module_baz_name)

def test_import_from_tmppy_module_name_in_transitive_dep_not_found_error():
    module_foo_name = 'foo'
    module_foo_source = '''\
def f(b: bool):
    return 7
def g(b: bool):
    return 43
'''
    compiled_module_foo = compile(module_foo_source,
                                  module_name=module_foo_name)

    module_bar_name = 'bar'
    module_bar_source = '''\
from foo import f
def h(b: bool):
    return f(b)
'''

    compiled_module_bar = compile(module_bar_source,
                                  module_name=module_bar_name,
                                  context_object_file_content=compiled_module_foo)

    module_baz_name = 'baz'
    module_baz_source = '''\
from bar import h
assert \
    g(  # error: Reference to undefined variable/function
        True) == 43
'''

    try:
        compile(module_baz_source,
                module_name=module_baz_name,
                context_object_file_content=compiled_module_bar)
        raise Exception('Expected exception not thrown')
    except CompilationError as e:
        check_compilation_error(e, module_baz_source)

def test_import_clash_of_two_imported_names():
    module_foo_name = 'foo'
    module_foo_source = '''\
def f(b: bool):
    return 7
'''
    compiled_module_foo = compile(module_foo_source,
                                  module_name=module_foo_name)

    module_bar_name = 'bar'
    module_bar_source = '''\
def f(b: bool):
    return 42
'''

    compiled_module_bar = compile(module_bar_source,
                                  module_name=module_bar_name)

    module_baz_name = 'baz'
    module_baz_source = '''\
from foo import f  # note: The previous declaration was here.
from bar import f  # error: f was already defined in this scope.
'''

    try:
        compile(module_baz_source,
                module_name=module_baz_name,
                context_object_file_content=merge_object_files([compiled_module_foo, compiled_module_bar]))
        raise Exception('Expected exception not thrown')
    except CompilationError as e:
        check_compilation_error(e, module_baz_source)

def test_import_two_modules_with_same_public_name_only_one_imported_ok():
    module_foo_name = 'foo'
    module_foo_source = '''\
class MyError(Exception):
    def __init__(self, b: bool):
        self.message = 'Something went wrong'
        self.b = b
def is_false(b: bool):
    return not b
def f(b: bool):
    if is_false(b):
        return 3
    else:
        raise MyError(b)
'''
    compiled_module_foo = compile(module_foo_source,
                                  module_name=module_foo_name)

    module_bar_name = 'bar'
    module_bar_source = '''\
class MyError(Exception):
    def __init__(self, b: bool):
        self.message = 'Something went wrong'
        self.b = b
def is_false(b: bool):
    return not b
def g(b: bool):
    if is_false(b):
        return 3
    else:
        raise MyError(b)
'''

    compiled_module_bar = compile(module_bar_source,
                                  module_name=module_bar_name)

    module_baz_name = 'baz'
    module_baz_source = '''\
from foo import f
from bar import g
def h(b: bool):
    return f(b) + g(b)
'''

    compiled_module_baz = compile(module_baz_source,
                                  module_name=module_baz_name,
                                  context_object_file_content=merge_object_files([compiled_module_foo, compiled_module_bar]))

    cpp_source = link(compiled_module_baz, main_module_name=module_baz_name)

    expect_cpp_code_success(tmppy_source=module_foo_source + module_bar_source + module_baz_source,
                            object_file_content=compiled_module_baz,
                            cxx_source=cpp_source,
                            main_module_name=module_baz_name)

if __name__== '__main__':
    main()
