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

import _py2tmp.ast2highir as ast2highir
import _py2tmp.highir2ir as highir2ir
import _py2tmp.ir2lowir as ir2lowir
import _py2tmp.lowir2cpp as lowir2cpp
import _py2tmp.utils as utils

import argparse

def convert_to_cpp(python_source, filename='<unknown>', verbose=False):
    source_ast = ast.parse(python_source, filename=filename)
    compilation_context = ast2highir.CompilationContext(ast2highir.SymbolTable(),
                                                        ast2highir.SymbolTable(),
                                                        filename,
                                                        python_source.splitlines())

    def identifier_generator_fun():
        for i in itertools.count():
            yield 'TmppyInternal_%s' % i
    identifier_generator = iter(identifier_generator_fun())

    module_high_ir = ast2highir.module_ast_to_ir(source_ast, compilation_context)
    if verbose:
        print('TMPPy high IR:')
        print(utils.ir_to_string(module_high_ir))
        print()

    module_ir = highir2ir.module_to_ir(module_high_ir, identifier_generator)
    if verbose:
        print('TMPPy IR:')
        print(utils.ir_to_string(module_ir))
        print()

    header = ir2lowir.module_to_low_ir(module_ir, identifier_generator)
    if verbose:
        print('TMPPy low IR:')
        print(utils.ir_to_string(header))
        print()

    result = lowir2cpp.header_to_cpp(header, identifier_generator)
    result = utils.clang_format(result)

    if verbose:
        print('Conversion result:')
        print(result)
    return result

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
