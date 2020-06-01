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

import argparse
import pickle
from typing import List

from _py2tmp.utils import ir_to_string
from _py2tmp.compiler import compile, link


def _module_name_from_filename(file_name: str):
    assert file_name.endswith('.py')
    return file_name.replace('/', '.')[:-len('.py')]

def _compile(module_name: str, object_files: List[str], filename: str, verbose: bool, coverage_collection_enabled: bool):
    object_file_content = compile(module_name=module_name,
                                  file_name=filename,
                                  context_object_files=object_files,
                                  include_intermediate_irs_for_debugging=verbose,
                                  coverage_collection_enabled=coverage_collection_enabled)

    if verbose:
        main_module = object_file_content.modules_by_name[module_name]
        print('TMPPy IR2:')
        print(ir_to_string(main_module.ir2_module))
        print()
        print('TMPPy IR1:')
        print(ir_to_string(main_module.ir1_module))
        print()
        print('TMPPy IR0:')
        print(ir_to_string(main_module.ir0_header))
        print()

    return object_file_content

def _compile_and_link(module_name: str, object_files: List[str], filename: str, verbose: bool, coverage_collection_enabled: bool):
    object_file_content = _compile(module_name, object_files, filename, verbose)

    result = link(module_name,
                  object_file_content,
                  coverage_collection_enabled=coverage_collection_enabled)

    if verbose:
        print('Conversion result:')
        print(result)
    return result

def main(verbose: bool,
         builtins_path: str,
         output_file: str,
         source: str,
         object_files: List[str],
         coverage_collection_enabled: bool):
    object_files = object_files + [builtins_path]
    for object_file in object_files:
        if not object_file.endswith('.tmppyc'):
            raise Exception('The specified object file %s does not have a .tmppyc extension.')

    suffix = '.py'
    if not source.endswith(suffix):
        raise Exception('The input file name does not end with .py: ' + source)

    module_name = _module_name_from_filename(source)

    verbose = (verbose == 'true')
    if output_file.endswith('.h'):
        result = _compile_and_link(module_name, object_files, source, verbose, coverage_collection_enabled)
        with open(output_file, 'w') as output_file:
            output_file.write(result)
    elif output_file.endswith('.tmppyc'):
        result = pickle.dumps(_compile(module_name, object_files, source, verbose, coverage_collection_enabled))
        with open(output_file, 'wb') as output_file:
            output_file.write(result)
    else:
        raise Exception('The output file name does not end with .h or .tmppyc: ' + output_file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts python source code into C++ metafunctions.')
    parser.add_argument('--verbose', help='If "true", prints verbose messages during the conversion')
    parser.add_argument('--enable_coverage', help='If "true", disables optimizations and enables coverage data collection')
    parser.add_argument('--builtins-path', required=True, help='The path to the builtins.tmppyc file.')
    parser.add_argument('-o', required=True, metavar='output_file', help='Output file (.tmppyc or .h).')
    parser.add_argument('source', help='The python source file to convert')
    parser.add_argument('object_files', nargs='*', help='.tmppyc object files for the modules (directly) imported in this source file')

    args = parser.parse_args()

    if not args.source:
        raise Exception('You must specify a source file')

    main(verbose=(args.verbose == 'true'),
         builtins_path=args.builtins_path,
         output_file=args.o,
         source=args.source,
         object_files=args.object_files,
         coverage_collection_enabled=(args.enable_coverage == 'true'))
