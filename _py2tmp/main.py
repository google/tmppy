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

from _py2tmp import utils
from _py2tmp.compile import compile
from _py2tmp.link import link


def _module_name_from_filename(file_name: str):
    return file_name.replace('/', '.')

def _compile(module_name: str, filename: str, verbose):
    object_file_content = compile(module_name=module_name,
                                  file_name=filename,
                                  context_object_files=[],
                                  unique_identifier_prefix='TmppyInternal_',
                                  include_intermediate_irs_for_debugging=verbose)

    if verbose:
        main_module = object_file_content.modules_by_name[module_name]
        print('TMPPy IR3:')
        print(utils.ir_to_string(main_module.ir3_module))
        print()
        print('TMPPy IR2:')
        print(utils.ir_to_string(main_module.ir2_module))
        print()
        print('TMPPy IR1:')
        print(utils.ir_to_string(main_module.ir1_module))
        print()
        print('TMPPy IR0:')
        print(utils.ir_to_string(main_module.ir0_header))
        print()

    return object_file_content

def _compile_and_link(module_name, filename: str, verbose):
    object_file_content = _compile(module_name, filename, verbose)

    result = link(module_name,
                  object_file_content,
                  unique_identifier_prefix='TmppyInternal2_')

    if verbose:
        print('Conversion result:')
        print(result)
    return result

def main():
    parser = argparse.ArgumentParser(description='Converts python source code into C++ metafunctions.')
    parser.add_argument('--verbose', help='If "true", prints verbose messages during the conversion')
    parser.add_argument('-o', required=True, metavar='output_file', help='Output file (.tmppyc or .h).')
    parser.add_argument('source', help='The python source file to convert')
    parser.add_argument('object_files', nargs='*', help='.tmppyc object files for the modules (directly) imported in this source file')

    args = parser.parse_args()

    for object_file in args.object_files:
        if not object_file.endswith('.tmppyc'):
            raise Exception('The specified object file %s does not have a .tmppyc extension.')

    suffix = '.py'
    if not args.source.endswith(suffix):
        raise Exception('The input file name does not end with .py: ' + args.source)

    module_name = _module_name_from_filename(args.source)

    verbose = (args.verbose == 'true')
    if args.o.endswith('.h'):
        result = _compile_and_link(module_name, args.source, verbose)
        with open(args.o, 'w') as output_file:
            output_file.write(result)
    elif args.o.endswith('.tmppyc'):
        result = pickle.dumps(_compile(module_name, args.source, verbose))
        with open(args.o, 'wb') as output_file:
            output_file.write(result)
    else:
        raise Exception('The output file name does not end with .h or .tmppyc: ' + args.o)

if __name__ == '__main__':
    main()
