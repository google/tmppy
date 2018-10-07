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

from _py2tmp import (
    utils)
from _py2tmp.compile import compile
from _py2tmp.link import link

def convert_to_cpp(module_name: str, filename='<unknown>', verbose=False):

    object_file_content = compile(module_name=module_name,
                                  file_name=filename,
                                  context_object_files=[],
                                  unique_identifier_prefix='TmppyInternal_',
                                  include_intermediate_irs_for_debugging=verbose)
    main_module = object_file_content.modules_by_name[module_name]

    if verbose:
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

    result = link(module_name,
                  object_file_content,
                  unique_identifier_prefix='TmppyInternal2_')

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
        suffix = '.py'
        if not source_file_name.endswith(suffix):
            raise Exception('An input file name does not end with .py: ' + source_file_name)
        output_file_name = source_file_name[:-len(suffix)] + '.h'
        with open(output_file_name, 'w') as output_file:
            output_file.write(convert_to_cpp(source_file_name, verbose=(args.verbose == 'true')))

if __name__ == '__main__':
    main()
