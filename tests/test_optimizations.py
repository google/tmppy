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
import pytest

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
''')
def test_optimization_toplevel_code():
    assert 1 + 1 == 2

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_25> struct CheckIfError { using type = void; };
template <int64_t TmppyInternal_5> struct f {
  static constexpr bool value = true;
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
''')
def test_common_subexpression_elimination_toplevel():
    from tmppy import Type
    assert (2*(3+1) == 2*(3+1)) == (Type.pointer(Type('int')) == Type.pointer(Type('int')))

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_22> struct CheckIfError { using type = void; };
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

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_char():
    from tmppy import Type
    assert Type('void') != Type('char')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_short():
    from tmppy import Type
    assert Type('void') != Type('short')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_int():
    from tmppy import Type
    assert Type('void') != Type('int')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_int32_t():
    from tmppy import Type
    assert Type('void') != Type('int32_t')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_int64_t():
    from tmppy import Type
    assert Type('void') != Type('int64_t')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_uint32_t():
    from tmppy import Type
    assert Type('void') != Type('uint32_t')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_uint64_t():
    from tmppy import Type
    assert Type('void') != Type('uint64_t')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_unsigned():
    from tmppy import Type
    assert Type('void') != Type('unsigned')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_long():
    from tmppy import Type
    assert Type('void') != Type('long')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_float():
    from tmppy import Type
    assert Type('void') != Type('float')

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_9> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_double():
    from tmppy import Type
    assert Type('void') != Type('double')

@assert_compilation_fails_with_generic_error('template instantiation depth exceeds maximum', allow_reaching_max_optimization_loops=True)
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

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename... Ts> struct GetFirstError { using type = void; };
template <typename... Ts> struct GetFirstError<void, Ts...> {
  using type = typename GetFirstError<Ts...>::type;
};
template <typename T, typename... Ts> struct GetFirstError<T, Ts...> {
  using type = T;
};
template <typename TmppyInternal_23> struct CheckIfError { using type = void; };
template <bool TmppyInternal_5, bool> struct TmppyInternal_24;
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5> struct TmppyInternal_24<TmppyInternal_5, true> {
  static constexpr int64_t value = 5LL;
  using error = void;
};
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5>
struct TmppyInternal_24<TmppyInternal_5, false> {
  static constexpr int64_t value = -1LL;
  using error = void;
};
template <bool TmppyInternal_5> struct f {
  static constexpr int64_t value =
      TmppyInternal_24<TmppyInternal_5, TmppyInternal_5>::value;
  using error =
      typename TmppyInternal_24<TmppyInternal_5, TmppyInternal_5>::error;
};
// (meta)function wrapping the expression in a list comprehension
template <bool TmppyInternal_9> struct TmppyInternal_25 {
  static constexpr int64_t value =
      TmppyInternal_24<TmppyInternal_9, TmppyInternal_9>::value;
  using error = void;
};
template <typename L> struct TmppyInternal_26;
template <bool... elems> struct TmppyInternal_26<BoolList<(elems)...>> {
  using type = Int64List<(TmppyInternal_25<elems>::value)...>;
  using error =
      typename GetFirstError<typename TmppyInternal_25<elems>::error...>::type;
};
template <typename TmppyInternal_13, typename TmppyInternal_12, bool>
struct TmppyInternal_28;
// (meta)function generated for an if-else statement
template <typename TmppyInternal_13, typename TmppyInternal_12>
struct TmppyInternal_28<TmppyInternal_13, TmppyInternal_12, true> {
  using type = void;
  using error = TmppyInternal_13;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_13, typename TmppyInternal_12>
struct TmppyInternal_28<TmppyInternal_13, TmppyInternal_12, false> {
  using error = void;
  using type = TmppyInternal_12;
};
template <typename TmppyInternal_8> struct g {
  using TmppyInternal_12 = typename TmppyInternal_26<TmppyInternal_8>::type;
  using TmppyInternal_13 = typename TmppyInternal_26<TmppyInternal_8>::error;
  static constexpr bool TmppyInternal_73 =
      !(std::is_same<typename TmppyInternal_26<TmppyInternal_8>::error,
                     void>::value);
  using type = typename TmppyInternal_28<TmppyInternal_13, TmppyInternal_12,
                                         TmppyInternal_73>::type;
  using error = typename TmppyInternal_28<TmppyInternal_13, TmppyInternal_12,
                                          TmppyInternal_73>::error;
};
''')
def test_optimization_list_comprehension_bool_to_int():
    from typing import List
    def f(b: bool):
        if b:
            return 5
        else:
            return -1
    def g(l: List[bool]):
        return [f(x) for x in l]
    assert g([True, False]) == [5, -1]

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename... Ts> struct GetFirstError { using type = void; };
template <typename... Ts> struct GetFirstError<void, Ts...> {
  using type = typename GetFirstError<Ts...>::type;
};
template <typename T, typename... Ts> struct GetFirstError<T, Ts...> {
  using type = T;
};
template <typename TmppyInternal_26> struct CheckIfError { using type = void; };
template <bool TmppyInternal_5, bool> struct TmppyInternal_27;
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5> struct TmppyInternal_27<TmppyInternal_5, true> {
  static constexpr int64_t value = 5LL;
  using error = void;
};
// (meta)function generated for an if-else statement
template <bool TmppyInternal_5>
struct TmppyInternal_27<TmppyInternal_5, false> {
  static constexpr int64_t value = -1LL;
  using error = void;
};
template <bool TmppyInternal_5> struct f {
  static constexpr int64_t value =
      TmppyInternal_27<TmppyInternal_5, TmppyInternal_5>::value;
  using error =
      typename TmppyInternal_27<TmppyInternal_5, TmppyInternal_5>::error;
};
// (meta)function wrapping the expression in a list comprehension
template <bool TmppyInternal_10, int64_t TmppyInternal_9>
struct TmppyInternal_28 {
  static constexpr int64_t value =
      (TmppyInternal_27<TmppyInternal_10, TmppyInternal_10>::value) +
      (TmppyInternal_9);
  using error = void;
};
template <typename L, int64_t TmppyInternal_9> struct TmppyInternal_29;
template <bool... elems, int64_t TmppyInternal_9>
struct TmppyInternal_29<BoolList<(elems)...>, TmppyInternal_9> {
  using type = Int64List<(TmppyInternal_28<elems, TmppyInternal_9>::value)...>;
  using error = typename GetFirstError<
      typename TmppyInternal_28<elems, TmppyInternal_9>::error...>::type;
};
template <typename TmppyInternal_15, typename TmppyInternal_14, bool>
struct TmppyInternal_31;
// (meta)function generated for an if-else statement
template <typename TmppyInternal_15, typename TmppyInternal_14>
struct TmppyInternal_31<TmppyInternal_15, TmppyInternal_14, true> {
  using type = void;
  using error = TmppyInternal_15;
};
// (meta)function generated for an if-else statement
template <typename TmppyInternal_15, typename TmppyInternal_14>
struct TmppyInternal_31<TmppyInternal_15, TmppyInternal_14, false> {
  using error = void;
  using type = TmppyInternal_14;
};
template <typename TmppyInternal_8, int64_t TmppyInternal_9> struct g {
  using TmppyInternal_14 =
      typename TmppyInternal_29<TmppyInternal_8, TmppyInternal_9>::type;
  using TmppyInternal_15 =
      typename TmppyInternal_29<TmppyInternal_8, TmppyInternal_9>::error;
  static constexpr bool TmppyInternal_85 =
      !(std::is_same<
          typename TmppyInternal_29<TmppyInternal_8, TmppyInternal_9>::error,
          void>::value);
  using type = typename TmppyInternal_31<TmppyInternal_15, TmppyInternal_14,
                                         TmppyInternal_85>::type;
  using error = typename TmppyInternal_31<TmppyInternal_15, TmppyInternal_14,
                                          TmppyInternal_85>::error;
};
''')
def test_optimization_list_comprehension_bool_to_int_with_captured_var():
    from typing import List
    def f(b: bool):
        if b:
            return 5
        else:
            return -1
    def g(l: List[bool], n: int):
        return [f(x) + n for x in l]
    assert g([True, False], 6) == [11, 5]

if __name__== '__main__':
    main(__file__)
