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

# TODO: change the expected output once optimization is implemented.
@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename> struct CheckIfError;
template <typename TmppyInternal_1> struct TmppyInternal_0;
template <int64_t TmppyInternal_5> struct inc;
template <typename> struct CheckIfError { using type = void; };
// The is_error (meta)function
template <typename TmppyInternal_1> struct TmppyInternal_0 {
  using TmppyInternal_2 = void;
  static constexpr bool TmppyInternal_3 = std::is_same<
      typename Select1stTypeType<TmppyInternal_1, TmppyInternal_1>::value,
      TmppyInternal_2>::value;
  static constexpr bool TmppyInternal_4 = !(TmppyInternal_3);
  static constexpr bool value = TmppyInternal_4;
  using error = TmppyInternal_2;
};
template <int64_t TmppyInternal_5> struct inc {
  static constexpr int64_t TmppyInternal_6 = 1LL;
  static constexpr int64_t TmppyInternal_7 =
      (TmppyInternal_5) + (TmppyInternal_6);
  static constexpr int64_t value = TmppyInternal_7;
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
  using TmppyInternal_2 = void;
  static constexpr bool TmppyInternal_3 = std::is_same<
      typename Select1stTypeType<TmppyInternal_1, TmppyInternal_1>::value,
      TmppyInternal_2>::value;
  static constexpr bool TmppyInternal_4 = !(TmppyInternal_3);
  static constexpr bool value = TmppyInternal_4;
  using error = TmppyInternal_2;
};
template <int64_t TmppyInternal_5> struct f {
  static constexpr int64_t TmppyInternal_7 = 2LL;
  static constexpr int64_t TmppyInternal_8 = 1LL;
  static constexpr int64_t TmppyInternal_9 =
      (TmppyInternal_5) + (TmppyInternal_8);
  static constexpr int64_t TmppyInternal_10 =
      (TmppyInternal_7) * (TmppyInternal_9);
  static constexpr int64_t TmppyInternal_6 = TmppyInternal_10;
  using TmppyInternal_17 = int *;
  using TmppyInternal_16 = TmppyInternal_17;
  static constexpr bool TmppyInternal_20 =
      (TmppyInternal_6) == (TmppyInternal_6);
  static constexpr bool TmppyInternal_21 = std::is_same<
      typename Select1stTypeInt64<TmppyInternal_16, TmppyInternal_5>::value,
      TmppyInternal_16>::value;
  static constexpr bool TmppyInternal_22 =
      (TmppyInternal_20) == (TmppyInternal_21);
  static constexpr bool value = TmppyInternal_22;
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
template <int64_t TmppyInternal_9> struct TmppyInternal_12;
template <typename TmppyInternal_10, int64_t TmppyInternal_9, bool>
struct TmppyInternal_13;
template <int64_t TmppyInternal_5> struct inc;
template <typename> struct CheckIfError { using type = void; };
// The is_error (meta)function
template <typename TmppyInternal_1> struct TmppyInternal_0 {
  using TmppyInternal_2 = void;
  static constexpr bool TmppyInternal_3 = std::is_same<
      typename Select1stTypeType<TmppyInternal_1, TmppyInternal_1>::value,
      TmppyInternal_2>::value;
  static constexpr bool TmppyInternal_4 = !(TmppyInternal_3);
  static constexpr bool value = TmppyInternal_4;
  using error = TmppyInternal_2;
};
template <int64_t TmppyInternal_5, int64_t TmppyInternal_6> struct plus {
  static constexpr int64_t TmppyInternal_7 =
      (TmppyInternal_5) + (TmppyInternal_6);
  static constexpr int64_t value = TmppyInternal_7;
  using error = void;
};
// (meta)function wrapping the code after an if-else statement
template <int64_t TmppyInternal_9> struct TmppyInternal_12 {
  static constexpr int64_t value = TmppyInternal_9;
  using error = void;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_10, int64_t TmppyInternal_9>
struct TmppyInternal_13<TmppyInternal_10, TmppyInternal_9, true> {
  static constexpr int64_t value = 0LL;
  using error = TmppyInternal_10;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_10, int64_t TmppyInternal_9>
struct TmppyInternal_13<TmppyInternal_10, TmppyInternal_9, false> {
  static constexpr int64_t value = TmppyInternal_12<
      Select1stInt64Type<TmppyInternal_9, TmppyInternal_10>::value>::value;
  using error = typename TmppyInternal_12<
      Select1stInt64Type<TmppyInternal_9, TmppyInternal_10>::value>::error;
};
template <int64_t TmppyInternal_5> struct inc {
  static constexpr int64_t TmppyInternal_8 = 1LL;
  static constexpr int64_t TmppyInternal_9 =
      plus<Select1stInt64Int64<TmppyInternal_5, TmppyInternal_5>::value,
           TmppyInternal_8>::value;
  using TmppyInternal_10 = typename plus<
      Select1stInt64Int64<TmppyInternal_5, TmppyInternal_5>::value,
      TmppyInternal_8>::error;
  static constexpr bool TmppyInternal_11 =
      TmppyInternal_0<typename Select1stTypeInt64<
          TmppyInternal_10, TmppyInternal_5>::value>::value;
  static constexpr int64_t value = TmppyInternal_13<
      typename Select1stTypeInt64<TmppyInternal_10, TmppyInternal_5>::value,
      TmppyInternal_9, TmppyInternal_11>::value;
  using error = typename TmppyInternal_13<
      typename Select1stTypeInt64<TmppyInternal_10, TmppyInternal_5>::value,
      TmppyInternal_9, TmppyInternal_11>::error;
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
template <int64_t TmppyInternal_8> struct TmppyInternal_14;
template <typename TmppyInternal_9, int64_t TmppyInternal_8, bool>
struct TmppyInternal_15;
template <bool TmppyInternal_5, bool> struct TmppyInternal_16;
template <bool TmppyInternal_5> struct f;
template <int64_t TmppyInternal_11> struct TmppyInternal_17;
template <typename TmppyInternal_12, int64_t TmppyInternal_11, bool>
struct TmppyInternal_18;
template <bool TmppyInternal_5> struct g;
template <typename> struct CheckIfError { using type = void; };
// The is_error (meta)function
template <typename TmppyInternal_1> struct TmppyInternal_0 {
  using TmppyInternal_2 = void;
  static constexpr bool TmppyInternal_3 = std::is_same<
      typename Select1stTypeType<TmppyInternal_1, TmppyInternal_1>::value,
      TmppyInternal_2>::value;
  static constexpr bool TmppyInternal_4 = !(TmppyInternal_3);
  static constexpr bool value = TmppyInternal_4;
  using error = TmppyInternal_2;
};
// (meta)function wrapping the code after an if-else statement
template <int64_t TmppyInternal_8> struct TmppyInternal_14 {
  static constexpr int64_t value = TmppyInternal_8;
  using error = void;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_9, int64_t TmppyInternal_8>
struct TmppyInternal_15<TmppyInternal_9, TmppyInternal_8, true> {
  static constexpr int64_t value = 0LL;
  using error = TmppyInternal_9;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_9, int64_t TmppyInternal_8>
struct TmppyInternal_15<TmppyInternal_9, TmppyInternal_8, false> {
  static constexpr int64_t value = TmppyInternal_14<
      Select1stInt64Type<TmppyInternal_8, TmppyInternal_9>::value>::value;
  using error = typename TmppyInternal_14<
      Select1stInt64Type<TmppyInternal_8, TmppyInternal_9>::value>::error;
};
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5> struct TmppyInternal_16<TmppyInternal_5, true> {
  static constexpr int64_t TmppyInternal_6 = 3LL;
  static constexpr int64_t value = TmppyInternal_6;
  using error = void;
};
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5>
struct TmppyInternal_16<TmppyInternal_5, false> {
  static constexpr bool TmppyInternal_7 = true;
  static constexpr int64_t TmppyInternal_8 =
      g<Select1stBoolBool<TmppyInternal_7, TmppyInternal_5>::value>::value;
  using TmppyInternal_9 = typename g<
      Select1stBoolBool<TmppyInternal_7, TmppyInternal_5>::value>::error;
  static constexpr bool TmppyInternal_10 =
      TmppyInternal_0<typename Select1stTypeBool<
          TmppyInternal_9, TmppyInternal_5>::value>::value;
  static constexpr int64_t value = TmppyInternal_15<
      typename Select1stTypeBool<TmppyInternal_9, TmppyInternal_5>::value,
      TmppyInternal_8, TmppyInternal_10>::value;
  using error = typename TmppyInternal_15<
      typename Select1stTypeBool<TmppyInternal_9, TmppyInternal_5>::value,
      TmppyInternal_8, TmppyInternal_10>::error;
};
template <bool TmppyInternal_5> struct f {
  static constexpr int64_t value = TmppyInternal_16<
      Select1stBoolBool<TmppyInternal_5, TmppyInternal_5>::value,
      TmppyInternal_5>::value;
  using error = typename TmppyInternal_16<
      Select1stBoolBool<TmppyInternal_5, TmppyInternal_5>::value,
      TmppyInternal_5>::error;
};
// (meta)function wrapping the code after an if-else statement
template <int64_t TmppyInternal_11> struct TmppyInternal_17 {
  static constexpr int64_t value = TmppyInternal_11;
  using error = void;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_12, int64_t TmppyInternal_11>
struct TmppyInternal_18<TmppyInternal_12, TmppyInternal_11, true> {
  static constexpr int64_t value = 0LL;
  using error = TmppyInternal_12;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_12, int64_t TmppyInternal_11>
struct TmppyInternal_18<TmppyInternal_12, TmppyInternal_11, false> {
  static constexpr int64_t value = TmppyInternal_17<
      Select1stInt64Type<TmppyInternal_11, TmppyInternal_12>::value>::value;
  using error = typename TmppyInternal_17<
      Select1stInt64Type<TmppyInternal_11, TmppyInternal_12>::value>::error;
};
template <bool TmppyInternal_5> struct g {
  static constexpr int64_t TmppyInternal_11 =
      f<Select1stBoolBool<TmppyInternal_5, TmppyInternal_5>::value>::value;
  using TmppyInternal_12 = typename f<
      Select1stBoolBool<TmppyInternal_5, TmppyInternal_5>::value>::error;
  static constexpr bool TmppyInternal_13 =
      TmppyInternal_0<typename Select1stTypeBool<
          TmppyInternal_12, TmppyInternal_5>::value>::value;
  static constexpr int64_t value = TmppyInternal_18<
      typename Select1stTypeBool<TmppyInternal_12, TmppyInternal_5>::value,
      TmppyInternal_11, TmppyInternal_13>::value;
  using error = typename TmppyInternal_18<
      typename Select1stTypeBool<TmppyInternal_12, TmppyInternal_5>::value,
      TmppyInternal_11, TmppyInternal_13>::error;
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
