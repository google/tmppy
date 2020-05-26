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
from enum import Enum


def ir_to_string(ir_elem, line_indent=''):
    next_line_indent = line_indent + '  '

    if ir_elem is None:
        return 'None'
    elif isinstance(ir_elem, (str, bool, int, Enum)):
        return repr(ir_elem)
    elif isinstance(ir_elem, (list, tuple, set, frozenset)):
        return ('['
                + ','.join('\n' + next_line_indent + ir_to_string(child_node, next_line_indent)
                           for child_node in ir_elem)
                + ']')
    else:
        return (ir_elem.__class__.__name__
                + '('
                + ','.join('\n' + next_line_indent + field_name + ' = ' + ir_to_string(child_node, next_line_indent)
                           for field_name, child_node in ir_elem.__dict__.items())
                + ')')