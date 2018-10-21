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
import subprocess


def clang_format(cxx_source: str, code_style='LLVM') -> str:
    command = ['clang-format',
               '-assume-filename=file.cpp',
               '-style=' + str({
                   'BasedOnStyle': code_style,
                   'MaxEmptyLinesToKeep': 0,
                   'KeepEmptyLinesAtTheStartOfBlocks': 'false',
                   'Standard': 'Cpp11'
               })]
    try:
        p = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True)
        stdout, stderr = p.communicate(cxx_source)
    except Exception:  # pragma: no cover
        raise Exception("Error while executing %s" % command)
    if p.returncode != 0:  # pragma: no cover
        raise Exception('clang-format exited with error code %s. Command was: %s. Error:\n%s' % (p.returncode, command, stderr))
    assert isinstance(stdout, str)

    if stdout != '' and stdout[-1] != '\n':
        return stdout + '\n'
    else:
        return stdout