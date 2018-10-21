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

DEFAULT_VERBOSE_SETTING = False

class ConfigurationKnobs:
    # If this is >=0, the number of ir0_optimization steps is capped to this value.
    max_num_optimization_steps = -1
    optimization_step_counter = 0
    reached_max_num_remaining_loops_counter = 0
    verbose = DEFAULT_VERBOSE_SETTING
