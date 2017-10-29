#!/usr/bin/env python3
#  Copyright 2016 Google Inc. All Rights Reserved.
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

import yaml

# "smoke tests" are run before other build matrix rows.
build_matrix_smoke_test_rows = []
build_matrix_rows = []

def determine_compiler_kind(compiler):
  if compiler.startswith('gcc'):
    return 'gcc'
  elif compiler.startswith('clang'):
    return 'clang'
  else:
    raise Exception('Unexpected compiler: %s' % compiler)

def determine_tests(smoke_tests, exclude_tests, include_only_tests):
  tests = ['ReleasePlain', 'DebugPlain']
  for smoke_test in smoke_tests:
    if smoke_test not in tests:
      tests += [smoke_test]
  excessive_excluded_tests = set(exclude_tests) - set(tests)
  if excessive_excluded_tests:
    raise Exception(
      'Some tests were excluded but were not going to run anyway: %s. '
      'Tests to run (ignoring the possible NoPch prefix): %s'
      % (excessive_excluded_tests, tests))
  if include_only_tests is not None:
    if exclude_tests != []:
      raise Exception('Using exclude_tests and include_only_tests together is not supported.')
    tests = include_only_tests
  else:
    tests = [test for test in tests if test not in exclude_tests]
  return tests

def generate_export_statements_for_env(env):
  return ' '.join(['export %s=\'%s\';' % (var_name, value) for (var_name, value) in sorted(env.items())])

def generate_env_string_for_env(env):
  return ' '.join(['%s=%s' % (var_name, value) for (var_name, value) in sorted(env.items())])

def add_ubuntu_tests(ubuntu_version, compiler, stl=None, smoke_tests=[], exclude_tests=[], include_only_tests=None):
  env = {
    'UBUNTU': ubuntu_version,
    'COMPILER': compiler
  }
  if stl is not None:
    env['STL'] = stl
  compiler_kind = determine_compiler_kind(compiler)
  export_statements = 'export OS=linux; ' + generate_export_statements_for_env(env=env)
  test_environment_template = {'os': 'linux', 'compiler': compiler_kind,
                               'install': '%s extras/scripts/travis_ci_install_linux.sh' % export_statements}
  tests = determine_tests(smoke_tests,
                          exclude_tests=exclude_tests,
                          include_only_tests=include_only_tests)
  for test in tests:
    test_environment = test_environment_template.copy()
    test_environment['script'] = '%s extras/scripts/postsubmit.sh %s' % (export_statements, test)
    # The TEST variable has no effect on the test run, but allows to see the test name in the Travis CI dashboard.
    test_environment['env'] = generate_env_string_for_env(env) + " TEST=%s" % test
    if test in smoke_tests:
      build_matrix_smoke_test_rows.append(test_environment)
    else:
      build_matrix_rows.append(test_environment)


def add_osx_tests(compiler, xcode_version=None, stl=None, smoke_tests=[], exclude_tests=[], include_only_tests=None):
  env = {'COMPILER': compiler}
  if stl is not None:
    env['STL'] = stl
  compiler_kind = determine_compiler_kind(compiler)
  export_statements = 'export OS=osx; ' + generate_export_statements_for_env(env=env)
  test_environment_template = {'os': 'osx', 'compiler': compiler_kind,
                               'install': '%s extras/scripts/travis_ci_install_osx.sh' % export_statements}
  if xcode_version is not None:
    test_environment_template['osx_image'] = 'xcode%s' % xcode_version

  tests = determine_tests(smoke_tests,
                          exclude_tests=exclude_tests,
                          include_only_tests=include_only_tests)
  for test in tests:
    test_environment = test_environment_template.copy()
    test_environment['script'] = '%s extras/scripts/postsubmit.sh %s' % (export_statements, test)
    # The TEST variable has no effect on the test run, but allows to see the test name in the Travis CI dashboard.
    test_environment['env'] = generate_env_string_for_env(env) + " TEST=%s" % test
    if test in smoke_tests:
      build_matrix_smoke_test_rows.append(test_environment)
    else:
      build_matrix_rows.append(test_environment)


add_ubuntu_tests(ubuntu_version='17.10', compiler='gcc-7', smoke_tests=['DebugPlain', 'ReleasePlain'])
add_ubuntu_tests(ubuntu_version='17.10', compiler='clang-4.0', stl='libstdc++', smoke_tests=['DebugPlain', 'ReleasePlain'])

add_ubuntu_tests(ubuntu_version='17.04', compiler='gcc-6', smoke_tests=['DebugPlain', 'ReleasePlain'])
add_ubuntu_tests(ubuntu_version='17.04', compiler='clang-4.0', stl='libstdc++', smoke_tests=['DebugPlain', 'ReleasePlain'])

add_ubuntu_tests(ubuntu_version='16.04', compiler='gcc-5')
add_ubuntu_tests(ubuntu_version='16.04', compiler='clang-3.5', stl='libstdc++')
add_ubuntu_tests(ubuntu_version='16.04', compiler='clang-3.9', stl='libstdc++')
add_ubuntu_tests(ubuntu_version='16.04', compiler='clang-3.5', stl='libc++')
add_ubuntu_tests(ubuntu_version='16.04', compiler='clang-3.9', stl='libc++')

add_osx_tests(compiler='gcc-5', xcode_version='8')
add_osx_tests(compiler='gcc-6', xcode_version='8', smoke_tests=['DebugPlain'])
add_osx_tests(compiler='clang-3.7', stl='libc++')
add_osx_tests(compiler='clang-4.0', xcode_version='8', stl='libc++', smoke_tests=['DebugPlain'])

add_osx_tests(compiler='clang-default', xcode_version='7.3', stl='libc++')
add_osx_tests(compiler='clang-default', xcode_version='8.2', stl='libc++', smoke_tests=['DebugPlain'])

yaml_file = {
  'sudo': 'required',
  'dist': 'trusty',
  'services' : ['docker'],
  'language': 'cpp',
  'branches': {
    'only': ['master'],
  },
  'matrix': {
    'fast_finish': True,
    'include': build_matrix_smoke_test_rows + build_matrix_rows,
  },
}

class CustomDumper(yaml.SafeDumper):
   def ignore_aliases(self, _data):
       return True

print('#')
print('# This file was auto-generated from extras/scripts/travis_yml_generator.py, DO NOT EDIT')
print('#')
print(yaml.dump(yaml_file, default_flow_style=False, Dumper=CustomDumper))
