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
from _py2tmp.testing.utils import main

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_8> struct CheckIfError { using type = void; };
template <int64_t TmppyInternal_5> struct inc {
  static constexpr int64_t value = (TmppyInternal_5) + (1LL);
  using error = void;
};
''')
def test_optimization_one_function():
    def inc(n: int):
        return n + 1

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_10> struct CheckIfError { using type = void; };
static_assert(((1LL) + (1LL)) == (2LL),
              "TMPPy assertion failed: \n<unknown>:1: assert 1 + 1 == 2");
''')
def test_optimization_toplevel_code():
    assert 1 + 1 == 2

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_25> struct CheckIfError { using type = void; };
template <int64_t TmppyInternal_5> struct f {
  static constexpr int64_t TmppyInternal_10 =
      (2LL) * ((TmppyInternal_5) + (1LL));
  using TmppyInternal_18 = int *;
  static constexpr bool value =
      ((TmppyInternal_10) == (TmppyInternal_10)) ==
      (std::is_same<
          typename Select1stTypeInt64<TmppyInternal_18, TmppyInternal_5>::value,
          TmppyInternal_18>::value);
  using error = void;
};
''')
def test_common_subexpression_elimination():
    from tmppy import Type
    def f(n: int):
        x1 = 2*(n + 1)
        x2 = 2*(n + 1)
        t1 = Type.pointer(Type('int'))
        t2 = Type.pointer(Type('int'))
        return (x1 == x2) == (t1 == t2)

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_22> struct CheckIfError { using type = void; };
static constexpr int64_t TmppyInternal_9 = (2LL) * ((3LL) + (1LL));
static_assert(
    ((TmppyInternal_9) == (TmppyInternal_9)) == (true),
    "TMPPy assertion failed: \n<unknown>:2: assert (2*(3+1) == 2*(3+1)) == "
    "(Type.pointer(Type('int')) == Type.pointer(Type('int')))");
''')
def test_common_subexpression_elimination_toplevel():
    from tmppy import Type
    assert (2*(3+1) == 2*(3+1)) == (Type.pointer(Type('int')) == Type.pointer(Type('int')))

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_22> struct CheckIfError { using type = void; };
static constexpr int64_t TmppyInternal_9 = (2LL) * ((3LL) + (1LL));
static_assert(
    ((TmppyInternal_9) == (TmppyInternal_9)) == (true),
    "TMPPy assertion failed: \n<unknown>:2: assert (2*(3 + 1) == 2*(3 + 1)) == "
    "(Type.pointer(Type('int')) == Type.pointer(Type('int')))");
''')
def test_common_subexpression_elimination_at_toplevel():
    from tmppy import Type
    assert (2*(3 + 1) == 2*(3 + 1)) == (Type.pointer(Type('int')) == Type.pointer(Type('int')))

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_10> struct CheckIfError { using type = void; };
template <int64_t TmppyInternal_5> struct inc {
  using error = void;
  static constexpr int64_t value = (TmppyInternal_5) + (1LL);
};
''')
def test_optimization_two_functions_with_call():
    def _plus(n: int, m: int):
        return n + m
    def inc(n: int):
        return _plus(n, 1)

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_13> struct CheckIfError { using type = void; };
static_assert(((3LL) + (1LL)) == (4LL),
              "TMPPy assertion failed: \n<unknown>:3: assert _plus(3, 1) == 4");
''')
def test_optimization_function_call_at_toplevel():
    def _plus(n: int, m: int):
        return n + m
    assert _plus(3, 1) == 4

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_14> struct CheckIfError { using type = void; };
template <bool TmppyInternal_5, bool> struct TmppyInternal_15;
template <bool TmppyInternal_5> struct f;
template <bool TmppyInternal_5> struct g;
template <bool TmppyInternal_5> struct f {
  static constexpr int64_t value =
      TmppyInternal_15<TmppyInternal_5, TmppyInternal_5>::value;
  using error =
      typename TmppyInternal_15<TmppyInternal_5, TmppyInternal_5>::error;
};
template <bool TmppyInternal_5> struct g {
  static constexpr int64_t value = f<TmppyInternal_5>::value;
  using error = void;
};
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5> struct TmppyInternal_15<TmppyInternal_5, true> {
  static constexpr int64_t value = 3LL;
  using error = void;
};
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5>
struct TmppyInternal_15<TmppyInternal_5, false> {
  static constexpr int64_t value = g<true>::value;
  using error = void;
};
static_assert((3LL) == (3LL),
              "TMPPy assertion failed: \n<unknown>:8: assert g(False) == 3");
''')
def test_optimization_of_mutually_recursive_functions():
    def f(b: bool) -> int:
        if b:
            return 3
        else:
            return g(True)
    def g(b: bool) -> int:
        return f(b)
    assert g(False) == 3

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_14> struct CheckIfError { using type = void; };
template <bool TmppyInternal_5, bool> struct TmppyInternal_15;
template <bool TmppyInternal_5> struct f;
template <bool TmppyInternal_5> struct g;
template <bool TmppyInternal_5> struct f {
  static constexpr int64_t value =
      TmppyInternal_15<TmppyInternal_5, TmppyInternal_5>::value;
  using error =
      typename TmppyInternal_15<TmppyInternal_5, TmppyInternal_5>::error;
};
template <bool TmppyInternal_5> struct g {
  static constexpr int64_t value = f<TmppyInternal_5>::value;
  using error = void;
};
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5>
struct TmppyInternal_15<TmppyInternal_5, false> {
  static constexpr int64_t value = 3LL;
  using error = void;
};
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5> struct TmppyInternal_15<TmppyInternal_5, true> {
  static constexpr int64_t value = g<false>::value;
  using error = void;
};
static_assert((3LL) == (3LL),
              "TMPPy assertion failed: \n<unknown>:8: assert g(True) == 3");
''')
def test_optimization_of_mutually_recursive_functions_branches_swapped():
    def f(b: bool) -> int:
        if b:
            return g(False)
        else:
            return 3
    def g(b: bool) -> int:
        return f(b)
    assert g(True) == 3

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_16> struct CheckIfError { using type = void; };
template <typename TmppyInternal_5, bool> struct TmppyInternal_17;
template <typename TmppyInternal_5> struct f;
template <typename TmppyInternal_5> struct g;
template <typename TmppyInternal_5> struct f {
  static constexpr bool TmppyInternal_7 =
      std::is_same<TmppyInternal_5, int>::value;
  static constexpr int64_t value =
      TmppyInternal_17<TmppyInternal_5, TmppyInternal_7>::value;
  using error =
      typename TmppyInternal_17<TmppyInternal_5, TmppyInternal_7>::error;
};
template <typename TmppyInternal_5> struct g {
  static constexpr int64_t value = f<TmppyInternal_5>::value;
  using error = void;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_5>
struct TmppyInternal_17<TmppyInternal_5, true> {
  static constexpr int64_t value = 3LL;
  using error = void;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_5>
struct TmppyInternal_17<TmppyInternal_5, false> {
  static constexpr int64_t value = g<int>::value;
  using error = void;
};
static_assert(
    (TmppyInternal_17<float, std::is_same<float, int>::value>::value) == (3LL),
    "TMPPy assertion failed: \n<unknown>:9: assert g(Type('float')) == 3");
''')
def test_optimization_of_mutually_recursive_functions_with_type_param():
    from tmppy import Type
    def f(t: Type) -> int:
        if t == Type('int'):
            return 3
        else:
            return g(Type('int'))
    def g(t: Type) -> int:
        return f(t)
    assert g(Type('float')) == 3

@assert_compilation_fails_with_generic_error('template instantiation depth exceeds maximum')
def test_optimization_of_mutually_recursive_functions_infinite_loop():
    def f(n: int) -> int:
        return g(n)
    def g(n: int) -> int:
        return f(n)
    assert g(1) != 0

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_22> struct CheckIfError { using type = void; };
template <typename TmppyInternal_23, typename> struct TmppyInternal_25;
// (meta)function wrapping a match expression
template <typename TmppyInternal_23, typename... TmppyInternal_24>
struct TmppyInternal_25<TmppyInternal_23, std::tuple<TmppyInternal_24...>> {
  using type = List<TmppyInternal_24...>;
  using error = void;
};
template <typename TmppyInternal_9, typename TmppyInternal_8, bool>
struct TmppyInternal_27;
// (meta)function generated for an if-else statement
template <typename TmppyInternal_9, typename TmppyInternal_8>
struct TmppyInternal_27<TmppyInternal_9, TmppyInternal_8, true> {
  using type = void;
  using error = TmppyInternal_9;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_9, typename TmppyInternal_8>
struct TmppyInternal_27<TmppyInternal_9, TmppyInternal_8, false> {
  using error = void;
  using type = TmppyInternal_8;
};
template <typename> struct TmppyInternal_29;
// (meta)function to expand the list of args for a template instantiation
template <typename... TmppyInternal_28>
struct TmppyInternal_29<List<TmppyInternal_28...>> {
  using type = std::tuple<TmppyInternal_28...>;
};
using TmppyInternal_89 = typename TmppyInternal_25<
    void, typename TmppyInternal_29<List<int, float, double>>::type>::error;
using TmppyInternal_129 = List<int, float, double>;
static_assert(
    std::is_same<
        typename TmppyInternal_27<
            TmppyInternal_89,
            typename TmppyInternal_25<
                void, typename TmppyInternal_29<TmppyInternal_129>::type>::type,
            !(std::is_same<TmppyInternal_89, void>::value)>::type,
        TmppyInternal_129>::value,
    "TMPPy assertion failed: \n<unknown>:7: assert "
    "_unpack_tuple(Type.template_instantiation('std::tuple', [Type('int'), "
    "Type('float'), Type('double')])) \\");
''')
def test_match_expr_extract_list_optimization():
    from tmppy import Type, match
    def _unpack_tuple(t: Type):
        return match(t)(lambda Ts: {
            Type.template_instantiation('std::tuple', [*Ts]):
                Ts
        })
    assert _unpack_tuple(Type.template_instantiation('std::tuple', [Type('int'), Type('float'), Type('double')])) \
        == [Type('int'), Type('float'), Type('double')]

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_17> struct CheckIfError { using type = void; };
template <typename TmppyInternal_5, typename> struct TmppyInternal_18;
// (meta)function wrapping a match expression
template <typename TmppyInternal_5, typename TmppyInternal_8>
struct TmppyInternal_18<TmppyInternal_5, TmppyInternal_8 *> {
  using type = float;
  using error = void;
};
template <typename TmppyInternal_10, typename TmppyInternal_9, bool>
struct TmppyInternal_20;
// (meta)function generated for an if-else statement
template <typename TmppyInternal_10, typename TmppyInternal_9>
struct TmppyInternal_20<TmppyInternal_10, TmppyInternal_9, true> {
  using type = void;
  using error = TmppyInternal_10;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_10, typename TmppyInternal_9>
struct TmppyInternal_20<TmppyInternal_10, TmppyInternal_9, false> {
  using error = void;
  using type = TmppyInternal_9;
};
using TmppyInternal_92 = int *;
static_assert(
    std::is_same<
        typename TmppyInternal_20<
            void,
            typename TmppyInternal_18<TmppyInternal_92, TmppyInternal_92>::type,
            !(true)>::type,
        float>::value,
    "TMPPy assertion failed: \n<unknown>:7: assert "
    "_f(Type.pointer(Type('int'))) == Type('float')");
''')
def test_match_optimization_only_one_definition():
    from tmppy import Type, match
    def _f(t: Type):
        return match(t)(lambda T: {
            Type.pointer(T):
                Type('float')
        })
    assert _f(Type.pointer(Type('int'))) == Type('float')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_19> struct CheckIfError { using type = void; };
// (meta)function wrapping a match expression
template <typename TmppyInternal_6> struct TmppyInternal_20 {
  using type = TmppyInternal_6 &;
  using error = void;
};
// (meta)function wrapping a match expression
template <typename TmppyInternal_6> struct TmppyInternal_20<TmppyInternal_6 *> {
  using type = TmppyInternal_6 &&;
  using error = void;
};
template <typename TmppyInternal_12, typename TmppyInternal_11, bool>
struct TmppyInternal_22;
// (meta)function generated for an if-else statement
template <typename TmppyInternal_12, typename TmppyInternal_11>
struct TmppyInternal_22<TmppyInternal_12, TmppyInternal_11, true> {
  using type = void;
  using error = TmppyInternal_12;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_12, typename TmppyInternal_11>
struct TmppyInternal_22<TmppyInternal_12, TmppyInternal_11, false> {
  using error = void;
  using type = TmppyInternal_11;
};
using TmppyInternal_85 = typename TmppyInternal_20<int>::error;
static_assert(
    std::is_same<typename TmppyInternal_22<
                     TmppyInternal_85, typename TmppyInternal_20<int>::type,
                     !(std::is_same<TmppyInternal_85, void>::value)>::type,
                 int &>::value,
    "TMPPy assertion failed: \n<unknown>:9: assert _f(Type('int')) == "
    "Type.reference(Type('int'))");
''')
def test_match_optimization_with_specialization_chooses_main_definition():
    from tmppy import Type, match
    def _f(t: Type):
        return match(t)(lambda T: {
            T:
                Type.reference(T),
            Type.pointer(T):
                Type.rvalue_reference(T),
        })
    assert _f(Type('int')) == Type.reference(Type('int'))

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_20> struct CheckIfError { using type = void; };
template <typename TmppyInternal_12, typename TmppyInternal_11, bool>
struct TmppyInternal_23;
// (meta)function generated for an if-else statement
template <typename TmppyInternal_12, typename TmppyInternal_11>
struct TmppyInternal_23<TmppyInternal_12, TmppyInternal_11, true> {
  using type = void;
  using error = TmppyInternal_12;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_12, typename TmppyInternal_11>
struct TmppyInternal_23<TmppyInternal_12, TmppyInternal_11, false> {
  using error = void;
  using type = TmppyInternal_11;
};
using TmppyInternal_108 = int &&;
static_assert(
    std::is_same<
        typename TmppyInternal_23<void, TmppyInternal_108, !(true)>::type,
        TmppyInternal_108>::value,
    "TMPPy assertion failed: \n<unknown>:9: assert "
    "_f(Type.pointer(Type('int'))) == Type.rvalue_reference(Type('int'))");
''')
def test_match_optimization_with_specialization_chooses_specialization():
    from tmppy import Type, match
    def _f(t: Type):
        return match(t)(lambda T: {
            T:
                Type.reference(T),
            Type.pointer(T):
                Type.rvalue_reference(T),
        })
    assert _f(Type.pointer(Type('int'))) == Type.rvalue_reference(Type('int'))

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_21> struct CheckIfError { using type = void; };
// (meta)function wrapping a match expression
template <typename TmppyInternal_6> struct TmppyInternal_22 {
  using type = TmppyInternal_6 &;
  using error = void;
};
// (meta)function wrapping a match expression
template <typename TmppyInternal_6> struct TmppyInternal_22<TmppyInternal_6 *> {
  using type = TmppyInternal_6 &&;
  using error = void;
};
// (meta)function wrapping a match expression
template <typename TmppyInternal_6>
struct TmppyInternal_22<TmppyInternal_6 **> {
  using type = TmppyInternal_6[];
  using error = void;
};
template <typename TmppyInternal_14, typename TmppyInternal_13, bool>
struct TmppyInternal_24;
// (meta)function generated for an if-else statement
template <typename TmppyInternal_14, typename TmppyInternal_13>
struct TmppyInternal_24<TmppyInternal_14, TmppyInternal_13, true> {
  using type = void;
  using error = TmppyInternal_14;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_14, typename TmppyInternal_13>
struct TmppyInternal_24<TmppyInternal_14, TmppyInternal_13, false> {
  using error = void;
  using type = TmppyInternal_13;
};
using TmppyInternal_95 = typename TmppyInternal_22<int>::error;
static_assert(
    std::is_same<typename TmppyInternal_24<
                     TmppyInternal_95, typename TmppyInternal_22<int>::type,
                     !(std::is_same<TmppyInternal_95, void>::value)>::type,
                 int &>::value,
    "TMPPy assertion failed: \n<unknown>:11: assert _f(Type('int')) == "
    "Type.reference(Type('int'))");
''')
def test_match_optimization_with_multiple_specializations_chooses_main_definition():
    from tmppy import Type, match
    def _f(t: Type):
        return match(t)(lambda T: {
            T:
                Type.reference(T),
            Type.pointer(T):
                Type.rvalue_reference(T),
            Type.pointer(Type.pointer(T)):
                Type.array(T),
        })
    assert _f(Type('int')) == Type.reference(Type('int'))

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_22> struct CheckIfError { using type = void; };
// (meta)function wrapping a match expression
template <typename TmppyInternal_6> struct TmppyInternal_23 {
  using type = TmppyInternal_6 &;
  using error = void;
};
// (meta)function wrapping a match expression
template <typename TmppyInternal_6> struct TmppyInternal_23<TmppyInternal_6 *> {
  using type = TmppyInternal_6 &&;
  using error = void;
};
// (meta)function wrapping a match expression
template <typename TmppyInternal_6>
struct TmppyInternal_23<TmppyInternal_6 **> {
  using type = TmppyInternal_6[];
  using error = void;
};
template <typename TmppyInternal_14, typename TmppyInternal_13, bool>
struct TmppyInternal_25;
// (meta)function generated for an if-else statement
template <typename TmppyInternal_14, typename TmppyInternal_13>
struct TmppyInternal_25<TmppyInternal_14, TmppyInternal_13, true> {
  using type = void;
  using error = TmppyInternal_14;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_14, typename TmppyInternal_13>
struct TmppyInternal_25<TmppyInternal_14, TmppyInternal_13, false> {
  using error = void;
  using type = TmppyInternal_13;
};
using TmppyInternal_96 = typename TmppyInternal_23<int *>::error;
static_assert(
    std::is_same<typename TmppyInternal_25<
                     TmppyInternal_96, typename TmppyInternal_23<int *>::type,
                     !(std::is_same<TmppyInternal_96, void>::value)>::type,
                 int &&>::value,
    "TMPPy assertion failed: \n<unknown>:11: assert "
    "_f(Type.pointer(Type('int'))) == Type.rvalue_reference(Type('int'))");
''')
def test_match_optimization_with_multiple_specializations_chooses_less_specific_specialization():
    from tmppy import Type, match
    def _f(t: Type):
        return match(t)(lambda T: {
            T:
                Type.reference(T),
            Type.pointer(T):
                Type.rvalue_reference(T),
            Type.pointer(Type.pointer(T)):
                Type.array(T),
        })
    assert _f(Type.pointer(Type('int'))) == Type.rvalue_reference(Type('int'))

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_23> struct CheckIfError { using type = void; };
// (meta)function wrapping a match expression
template <typename TmppyInternal_6> struct TmppyInternal_24 {
  using type = TmppyInternal_6 &;
  using error = void;
};
// (meta)function wrapping a match expression
template <typename TmppyInternal_6> struct TmppyInternal_24<TmppyInternal_6 *> {
  using type = TmppyInternal_6 &&;
  using error = void;
};
// (meta)function wrapping a match expression
template <typename TmppyInternal_6>
struct TmppyInternal_24<TmppyInternal_6 **> {
  using type = TmppyInternal_6[];
  using error = void;
};
template <typename TmppyInternal_14, typename TmppyInternal_13, bool>
struct TmppyInternal_26;
// (meta)function generated for an if-else statement
template <typename TmppyInternal_14, typename TmppyInternal_13>
struct TmppyInternal_26<TmppyInternal_14, TmppyInternal_13, true> {
  using type = void;
  using error = TmppyInternal_14;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_14, typename TmppyInternal_13>
struct TmppyInternal_26<TmppyInternal_14, TmppyInternal_13, false> {
  using error = void;
  using type = TmppyInternal_13;
};
using TmppyInternal_97 = typename TmppyInternal_24<int **>::error;
static_assert(
    std::is_same<typename TmppyInternal_26<
                     TmppyInternal_97, typename TmppyInternal_24<int **>::type,
                     !(std::is_same<TmppyInternal_97, void>::value)>::type,
                 int[]>::value,
    "TMPPy assertion failed: \n<unknown>:11: assert "
    "_f(Type.pointer(Type.pointer(Type('int')))) == Type.array(Type('int'))");
''')
def test_match_optimization_with_multiple_specializations_chooses_more_specific_specialization():
    from tmppy import Type, match
    def _f(t: Type):
        return match(t)(lambda T: {
            T:
                Type.reference(T),
            Type.pointer(T):
                Type.rvalue_reference(T),
            Type.pointer(Type.pointer(T)):
                Type.array(T),
        })
    assert _f(Type.pointer(Type.pointer(Type('int')))) == Type.array(Type('int'))

if __name__== '__main__':
    main(__file__)
