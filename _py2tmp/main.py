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
import typed_ast.ast3 as ast

from _py2tmp import (
    ast_to_ir3,
    ir3_to_ir2,
    ir2_to_ir1,
    ir1_to_ir0,
    ir0_to_cpp,
    utils,
    ir0_builtins)

from _py2tmp import ir0_optimization, ir3_optimization
import argparse

def convert_to_cpp(python_source, filename='<unknown>', verbose=False):
    source_ast = ast.parse(python_source, filename=filename)

    def identifier_generator_fun():
        for i in itertools.count():
            yield 'TmppyInternal_%s' % i
    identifier_generator = iter(identifier_generator_fun())

    module_ir3 = ast_to_ir3.module_ast_to_ir3(source_ast, filename, python_source.splitlines(), identifier_generator)
    if verbose:
        print('TMPPy IR3:')
        print(utils.ir_to_string(module_ir3))
        print()

    module_ir3 = ir3_optimization.optimize_module(module_ir3)
    if verbose:
        print('TMPPy IR3 after optimization:')
        print(utils.ir_to_string(module_ir3))
        print()

    module_ir2 = ir3_to_ir2.module_to_ir2(module_ir3, identifier_generator)
    if verbose:
        print('TMPPy IR2:')
        print(utils.ir_to_string(module_ir2))
        print()

    module_ir1 = ir2_to_ir1.module_to_ir1(module_ir2)
    if verbose:
        print('TMPPy IR1:')
        print(utils.ir_to_string(module_ir1))
        print()

    header_ir0 = ir1_to_ir0.module_to_ir0(module_ir1, identifier_generator)
    if verbose:
        print('TMPPy IR0:')
        print(utils.ir_to_string(header_ir0))
        print()

    header_ir0 = ir0_optimization.optimize_header(header_ir0, identifier_generator)
    if verbose:
        print('TMPPy IR0 after optimization:')
        print(utils.ir_to_string(header_ir0))
        print()

    result = ir0_to_cpp.header_to_cpp(header_ir0, identifier_generator)

    if verbose:
        print('Conversion result:')
        print(result)
    return ir0_builtins.get_builtins_cpp_code() + result

def main():
    parser = argparse.ArgumentParser(description='Converts python source code into C++ metafunctions.')
    parser.add_argument('sources', nargs='+', help='The python source files to convert')
    parser.add_argument('--output-dir', help='Output dir for the generated files')
    parser.add_argument('--verbose', help='If "true", prints verbose messages during the conversion')

    args = parser.parse_args()

    for source_file_name in args.sources:
        with open(source_file_name) as source_file:
            source = source_file.read()
        suffix = '.py'
        if not source_file_name.endswith(suffix):
            raise Exception('An input file name does not end with .py: ' + source_file_name)
        output_file_name = source_file_name[:-len(suffix)] + '.h'
        with open(output_file_name, 'w') as output_file:
            output_file.write(convert_to_cpp(source, source_file_name, verbose=(args.verbose == 'true')))

if __name__ == '__main__':
    main()
