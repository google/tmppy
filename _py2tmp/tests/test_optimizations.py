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

from py2tmp.testing import *

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename> struct CheckIfError;
template <typename TmppyInternal_1> struct TmppyInternal_0;
template <int64_t TmppyInternal_5> struct inc;
template <typename> struct CheckIfError { using type = void; };
// The is_error (meta)function
template <typename TmppyInternal_1> struct TmppyInternal_0 {
  using error = void;
  static constexpr bool value =
      !(std::is_same<
          typename Select1stTypeType<TmppyInternal_1, TmppyInternal_1>::value,
          void>::value);
};
template <int64_t TmppyInternal_5> struct inc {
  static constexpr int64_t value = (TmppyInternal_5) + (1LL);
  using error = void;
};
''')
def test_optimization_one_function():
    def inc(n: int):
        return n + 1

# TODO: change the expected output once optimization is implemented.
@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename> struct CheckIfError;
template <typename TmppyInternal_1> struct TmppyInternal_0;
template <int64_t TmppyInternal_5> struct f;
template <typename> struct CheckIfError { using type = void; };
// The is_error (meta)function
template <typename TmppyInternal_1> struct TmppyInternal_0 {
  using error = void;
  static constexpr bool value =
      !(std::is_same<
          typename Select1stTypeType<TmppyInternal_1, TmppyInternal_1>::value,
          void>::value);
};
template <int64_t TmppyInternal_5> struct f {
  static constexpr int64_t TmppyInternal_10 =
      (2LL) * ((TmppyInternal_5) + (1LL));
  static constexpr bool value =
      ((TmppyInternal_10) == (TmppyInternal_10)) ==
      (std::is_same<typename Select1stTypeInt64<int *, TmppyInternal_5>::value,
                    int *>::value);
  using error = void;
};
''')
def test_common_subexpression_elimination():
    from tmppy import Type
    def f(n: int):
        x1 = 2*(n + 1)
        x2 = 2*(n + 1)
        t1 = Type('int*')
        t2 = Type('int*')
        return (x1 == x2) == (t1 == t2)

# TODO: change the expected output once optimization is implemented.
@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename> struct CheckIfError;
template <typename TmppyInternal_1> struct TmppyInternal_0;
template <int64_t TmppyInternal_5, int64_t TmppyInternal_6> struct plus;
template <int64_t TmppyInternal_5> struct inc;
template <typename> struct CheckIfError { using type = void; };
// The is_error (meta)function
template <typename TmppyInternal_1> struct TmppyInternal_0 {
  using error = void;
  static constexpr bool value =
      !(std::is_same<
          typename Select1stTypeType<TmppyInternal_1, TmppyInternal_1>::value,
          void>::value);
};
template <int64_t TmppyInternal_5, int64_t TmppyInternal_6> struct plus {
  static constexpr int64_t value = (TmppyInternal_5) + (TmppyInternal_6);
  using error = void;
};
template <int64_t TmppyInternal_5> struct inc {
  using error = void;
  static constexpr int64_t value = (TmppyInternal_5) + (1LL);
};
''')
def test_optimization_two_functions_with_call():
    def plus(n: int, m: int):
        return n + m
    def inc(n: int):
        return plus(n, 1)

# TODO: change the expected output once optimization is implemented.
@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename> struct CheckIfError;
template <typename TmppyInternal_1> struct TmppyInternal_0;
template <bool TmppyInternal_5, bool> struct TmppyInternal_10;
template <bool TmppyInternal_5> struct f;
template <bool TmppyInternal_5> struct g;
template <typename> struct CheckIfError { using type = void; };
// The is_error (meta)function
template <typename TmppyInternal_1> struct TmppyInternal_0 {
  using error = void;
  static constexpr bool value =
      !(std::is_same<
          typename Select1stTypeType<TmppyInternal_1, TmppyInternal_1>::value,
          void>::value);
};
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5> struct TmppyInternal_10<TmppyInternal_5, true> {
  static constexpr int64_t value = 3LL;
  using error = void;
};
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5>
struct TmppyInternal_10<TmppyInternal_5, false> {
  static constexpr int64_t value =
      g<Select1stBoolBool<true, TmppyInternal_5>::value>::value;
  using error = void;
};
template <bool TmppyInternal_5> struct f {
  static constexpr int64_t value = TmppyInternal_10<
      Select1stBoolBool<TmppyInternal_5, TmppyInternal_5>::value,
      TmppyInternal_5>::value;
  using error = typename TmppyInternal_10<
      Select1stBoolBool<TmppyInternal_5, TmppyInternal_5>::value,
      TmppyInternal_5>::error;
};
template <bool TmppyInternal_5> struct g {
  static constexpr int64_t value =
      f<Select1stBoolBool<TmppyInternal_5, TmppyInternal_5>::value>::value;
  using error = void;
};
''')
def test_optimization_of_mutually_recursive_functions():
    def f(b: bool) -> int:
        if b:
            return 3
        else:
            return g(True)
    def g(b: bool) -> int:
        return f(b)
