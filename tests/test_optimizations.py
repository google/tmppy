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
template <bool TmppyInternal_5, bool TmppyInternal_16> struct TmppyInternal_18;
// Split that generates error of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5> struct TmppyInternal_18<TmppyInternal_5, true> {
  using error = void;
};
// Split that generates error of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5>
struct TmppyInternal_18<TmppyInternal_5, false> {
  using error = void;
};
template <bool TmppyInternal_5, bool TmppyInternal_16> struct TmppyInternal_19;
template <bool TmppyInternal_5> struct f;
template <bool TmppyInternal_5> struct g;
template <bool TmppyInternal_5> struct f {
  static constexpr int64_t value =
      TmppyInternal_19<TmppyInternal_5, TmppyInternal_5>::value;
  using error =
      typename TmppyInternal_18<TmppyInternal_5, TmppyInternal_5>::error;
};
template <bool TmppyInternal_5> struct g {
  static constexpr int64_t value = f<TmppyInternal_5>::value;
  using error = void;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5> struct TmppyInternal_19<TmppyInternal_5, true> {
  static constexpr int64_t value = 3LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5>
struct TmppyInternal_19<TmppyInternal_5, false> {
  static constexpr int64_t value = g<true>::value;
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
template <bool TmppyInternal_5, bool TmppyInternal_16> struct TmppyInternal_18;
// Split that generates error of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5> struct TmppyInternal_18<TmppyInternal_5, true> {
  using error = void;
};
// Split that generates error of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5>
struct TmppyInternal_18<TmppyInternal_5, false> {
  using error = void;
};
template <bool TmppyInternal_5, bool TmppyInternal_16> struct TmppyInternal_19;
template <bool TmppyInternal_5> struct f;
template <bool TmppyInternal_5> struct g;
template <bool TmppyInternal_5> struct f {
  static constexpr int64_t value =
      TmppyInternal_19<TmppyInternal_5, TmppyInternal_5>::value;
  using error =
      typename TmppyInternal_18<TmppyInternal_5, TmppyInternal_5>::error;
};
template <bool TmppyInternal_5> struct g {
  static constexpr int64_t value = f<TmppyInternal_5>::value;
  using error = void;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5>
struct TmppyInternal_19<TmppyInternal_5, false> {
  static constexpr int64_t value = 3LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5> struct TmppyInternal_19<TmppyInternal_5, true> {
  static constexpr int64_t value = g<false>::value;
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
template <typename TmppyInternal_5, bool TmppyInternal_18>
struct TmppyInternal_20;
// Split that generates error of: (meta)function generated for an if-else
// statement
template <typename TmppyInternal_5>
struct TmppyInternal_20<TmppyInternal_5, true> {
  using error = void;
};
// Split that generates error of: (meta)function generated for an if-else
// statement
template <typename TmppyInternal_5>
struct TmppyInternal_20<TmppyInternal_5, false> {
  using error = void;
};
template <typename TmppyInternal_5, bool TmppyInternal_18>
struct TmppyInternal_21;
template <typename TmppyInternal_5> struct f;
template <typename TmppyInternal_5> struct g;
template <typename TmppyInternal_5> struct f {
  static constexpr bool TmppyInternal_7 =
      std::is_same<TmppyInternal_5, int>::value;
  static constexpr int64_t value =
      TmppyInternal_21<TmppyInternal_5, TmppyInternal_7>::value;
  using error =
      typename TmppyInternal_20<TmppyInternal_5, TmppyInternal_7>::error;
};
template <typename TmppyInternal_5> struct g {
  static constexpr int64_t value = f<TmppyInternal_5>::value;
  using error = void;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename TmppyInternal_5>
struct TmppyInternal_21<TmppyInternal_5, true> {
  static constexpr int64_t value = 3LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename TmppyInternal_5>
struct TmppyInternal_21<TmppyInternal_5, false> {
  static constexpr int64_t value = g<int>::value;
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
template <typename TmppyInternal_23> struct CheckIfError { using type = void; };
template <bool TmppyInternal_5, bool TmppyInternal_25> struct TmppyInternal_34;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5> struct TmppyInternal_34<TmppyInternal_5, true> {
  static constexpr int64_t value = 5LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5>
struct TmppyInternal_34<TmppyInternal_5, false> {
  static constexpr int64_t value = -1LL;
};
template <bool TmppyInternal_5> struct f {
  static constexpr int64_t value =
      TmppyInternal_34<TmppyInternal_5, TmppyInternal_5>::value;
  using error = void;
};
template <typename TmppyInternal_8> struct TmppyInternal_40;
// Split that generates type of:
template <bool... TmppyInternal_26>
struct TmppyInternal_40<BoolList<(TmppyInternal_26)...>> {
  using type = Int64List<(
      TmppyInternal_34<TmppyInternal_26, TmppyInternal_26>::value)...>;
};
template <typename TmppyInternal_8> struct g {
  using error = void;
  using type = typename TmppyInternal_40<TmppyInternal_8>::type;
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
template <typename TmppyInternal_26> struct CheckIfError { using type = void; };
template <bool TmppyInternal_5, bool TmppyInternal_28> struct TmppyInternal_37;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5> struct TmppyInternal_37<TmppyInternal_5, true> {
  static constexpr int64_t value = 5LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5>
struct TmppyInternal_37<TmppyInternal_5, false> {
  static constexpr int64_t value = -1LL;
};
template <bool TmppyInternal_5> struct f {
  static constexpr int64_t value =
      TmppyInternal_37<TmppyInternal_5, TmppyInternal_5>::value;
  using error = void;
};
template <typename TmppyInternal_8, int64_t TmppyInternal_9>
struct TmppyInternal_43;
// Split that generates type of:
template <bool... TmppyInternal_29, int64_t TmppyInternal_9>
struct TmppyInternal_43<BoolList<(TmppyInternal_29)...>, TmppyInternal_9> {
  using type =
      Int64List<((TmppyInternal_37<TmppyInternal_29, TmppyInternal_29>::value) +
                 (TmppyInternal_9))...>;
};
template <typename TmppyInternal_8, int64_t TmppyInternal_9> struct g {
  using error = void;
  using type =
      typename TmppyInternal_43<TmppyInternal_8, TmppyInternal_9>::type;
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

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_31> struct CheckIfError { using type = void; };
template <typename TmppyInternal_5> struct TmppyInternal_53;
// Split that generates type of:
template <typename... TmppyInternal_32>
struct TmppyInternal_53<List<TmppyInternal_32...>> {
  using type = List<TmppyInternal_32 *const...>;
};
template <typename TmppyInternal_5> struct f {
  using error = void;
  using type = typename TmppyInternal_53<TmppyInternal_5>::type;
};
''')
def test_optimization_multiple_list_comprehensions():
    from typing import List
    from tmppy import Type
    def f(l0: List[Type]):
        l1 = [Type.pointer(x) for x in l0]
        l2 = [Type.const(x) for x in l1]
        return l2
    assert f([Type('int'), Type('float')]) == [Type.const(Type.pointer(Type('int'))),
                                               Type.const(Type.pointer(Type('float')))]

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename AllFalseListIfNotPresent, typename AllFalseList, typename S,
          bool b>
struct AddToBoolSetHelper {
  using type = S;
};
template <typename AllFalseList, bool... bs, bool b>
struct AddToBoolSetHelper<AllFalseList, AllFalseList, BoolList<(bs)...>, b> {
  using type = BoolList<(bs)..., b>;
};
template <typename TmppyInternal_19> struct CheckIfError { using type = void; };
template <bool TmppyInternal_5, bool TmppyInternal_6> struct set_of {
  using type = typename AddToBoolSetHelper<
      BoolList<(TmppyInternal_5) == (TmppyInternal_6)>, BoolList<false>,
      BoolList<TmppyInternal_5>, TmppyInternal_6>::type;
  using error = void;
};
''')
def test_optimization_set_with_two_bools():
    def set_of(x: bool, y: bool):
        return {x, y}
    assert set_of(True, False) == {True, False}

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename AllFalseListIfNotPresent, typename AllFalseList, typename S,
          int64_t n>
struct AddToInt64SetHelper {
  using type = S;
};
template <typename AllFalseList, int64_t... ns, int64_t n>
struct AddToInt64SetHelper<AllFalseList, AllFalseList, Int64List<(ns)...>, n> {
  using type = Int64List<(ns)..., n>;
};
template <typename TmppyInternal_19> struct CheckIfError { using type = void; };
template <int64_t TmppyInternal_5, int64_t TmppyInternal_6> struct set_of {
  using type = typename AddToInt64SetHelper<
      BoolList<(TmppyInternal_5) == (TmppyInternal_6)>, BoolList<false>,
      Int64List<TmppyInternal_5>, TmppyInternal_6>::type;
  using error = void;
};
''')
def test_optimization_set_with_two_ints():
    def set_of(x: int, y: int):
        return {x, y}
    assert set_of(3, 4) == {3, 4}

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename AllFalseListIfNotPresent, typename AllFalseList, typename S,
          typename T>
struct AddToTypeSetHelper {
  using type = S;
};
template <typename AllFalseList, typename... Ts, typename T>
struct AddToTypeSetHelper<AllFalseList, AllFalseList, List<Ts...>, T> {
  using type = List<Ts..., T>;
};
template <typename TmppyInternal_19> struct CheckIfError { using type = void; };
template <typename TmppyInternal_5, typename TmppyInternal_6> struct set_of {
  using type = typename AddToTypeSetHelper<
      BoolList<std::is_same<TmppyInternal_5, TmppyInternal_6>::value>,
      BoolList<false>, List<TmppyInternal_5>, TmppyInternal_6>::type;
  using error = void;
};
''')
def test_optimization_set_with_two_types():
    from tmppy import Type
    def set_of(x: Type, y: Type):
        return {x, y}
    assert set_of(Type('int'), Type('float')) == {Type('int'), Type('float')}

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_15> struct CheckIfError { using type = void; };
template <bool TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_19;
// Split that generates value of:
template <bool TmppyInternal_5, bool... TmppyInternal_16>
struct TmppyInternal_19<TmppyInternal_5, BoolList<(TmppyInternal_16)...>> {
  static constexpr bool value =
      !(std::is_same<BoolList<((TmppyInternal_16) == (TmppyInternal_5))...>,
                     BoolList<((TmppyInternal_16) && (false))...>>::value);
};
template <bool TmppyInternal_5, typename TmppyInternal_6> struct is_in_set {
  using error = void;
  static constexpr bool value =
      TmppyInternal_19<TmppyInternal_5, TmppyInternal_6>::value;
};
''')
def test_optimization_is_in_bool_set():
    from typing import Set
    def is_in_set(x: bool, y: Set[bool]):
        return x in y
    assert is_in_set(True, {False}) == False

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_15> struct CheckIfError { using type = void; };
template <int64_t TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_19;
// Split that generates value of:
template <int64_t TmppyInternal_5, int64_t... TmppyInternal_16>
struct TmppyInternal_19<TmppyInternal_5, Int64List<(TmppyInternal_16)...>> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((TmppyInternal_16) == (TmppyInternal_5))...>,
          BoolList<((TmppyInternal_16) != (TmppyInternal_16))...>>::value);
};
template <int64_t TmppyInternal_5, typename TmppyInternal_6> struct is_in_set {
  using error = void;
  static constexpr bool value =
      TmppyInternal_19<TmppyInternal_5, TmppyInternal_6>::value;
};
''')
def test_optimization_is_in_int_set():
    from typing import Set
    def is_in_set(x: int, y: Set[int]):
        return x in y
    assert is_in_set(3, {5}) == False

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename TmppyInternal_15> struct CheckIfError { using type = void; };
template <typename TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_19;
// Split that generates value of:
template <typename TmppyInternal_5, typename... TmppyInternal_16>
struct TmppyInternal_19<TmppyInternal_5, List<TmppyInternal_16...>> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<(std::is_same<TmppyInternal_16, TmppyInternal_5>::value)...>,
          BoolList<(Select1stBoolType<false, TmppyInternal_16>::value)...>>::
            value);
};
template <typename TmppyInternal_5, typename TmppyInternal_6> struct is_in_set {
  using error = void;
  static constexpr bool value =
      TmppyInternal_19<TmppyInternal_5, TmppyInternal_6>::value;
};
''')
def test_optimization_is_in_type_set():
    from tmppy import Type
    from typing import Set
    def is_in_set(x: Type, y: Set[Type]):
        return x in y
    assert is_in_set(Type('int'), {Type('float')}) == False

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <bool b, typename L> struct IsInBoolList;
template <bool b, bool... bs> struct IsInBoolList<b, BoolList<(bs)...>> {
  static constexpr bool value =
      !(std::is_same<BoolList<((bs) == (b))...>,
                     BoolList<((bs) && (false))...>>::value);
};
template <typename TmppyInternal_17> struct CheckIfError { using type = void; };
template <typename TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_22;
// Split that generates value of:
template <bool... TmppyInternal_18, bool... TmppyInternal_19>
struct TmppyInternal_22<BoolList<(TmppyInternal_18)...>,
                        BoolList<(TmppyInternal_19)...>> {
  static constexpr bool value = std::is_same<
      BoolList<(IsInBoolList<TmppyInternal_19,
                             BoolList<(TmppyInternal_18)...>>::value)...,
               (IsInBoolList<TmppyInternal_18,
                             BoolList<(TmppyInternal_19)...>>::value)...>,
      BoolList<((TmppyInternal_19) || (true))...,
               ((TmppyInternal_18) || (true))...>>::value;
};
template <typename TmppyInternal_5, typename TmppyInternal_6> struct eq {
  using error = void;
  static constexpr bool value =
      TmppyInternal_22<TmppyInternal_5, TmppyInternal_6>::value;
};
''')
def test_optimization_bool_set_equals():
    from typing import Set
    def eq(x: Set[bool], y: Set[bool]):
        return x == y
    assert eq({True}, {False}) == False

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <int64_t n, typename L> struct IsInInt64List;
template <int64_t n, int64_t... ns>
struct IsInInt64List<n, Int64List<(ns)...>> {
  static constexpr bool value =
      !(std::is_same<BoolList<((ns) == (n))...>,
                     BoolList<((ns) != (ns))...>>::value);
};
template <typename TmppyInternal_17> struct CheckIfError { using type = void; };
template <typename TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_22;
// Split that generates value of:
template <int64_t... TmppyInternal_18, int64_t... TmppyInternal_19>
struct TmppyInternal_22<Int64List<(TmppyInternal_18)...>,
                        Int64List<(TmppyInternal_19)...>> {
  static constexpr bool value = std::is_same<
      BoolList<(IsInInt64List<TmppyInternal_19,
                              Int64List<(TmppyInternal_18)...>>::value)...,
               (IsInInt64List<TmppyInternal_18,
                              Int64List<(TmppyInternal_19)...>>::value)...>,
      BoolList<((TmppyInternal_19) == (TmppyInternal_19))...,
               ((TmppyInternal_18) == (TmppyInternal_18))...>>::value;
};
template <typename TmppyInternal_5, typename TmppyInternal_6> struct eq {
  using error = void;
  static constexpr bool value =
      TmppyInternal_22<TmppyInternal_5, TmppyInternal_6>::value;
};
''')
def test_optimization_int_set_equals():
    from typing import Set
    def eq(x: Set[int], y: Set[int]):
        return x == y
    assert eq({3}, {5}) == False

@assert_code_optimizes_to(r'''
#include <tmppy/tmppy.h>
#include <type_traits>
template <typename T, typename L> struct IsInTypeList;
template <typename T, typename... Ts> struct IsInTypeList<T, List<Ts...>> {
  static constexpr bool value = !(
      std::is_same<BoolList<(std::is_same<Ts, T>::value)...>,
                   BoolList<(Select1stBoolType<false, Ts>::value)...>>::value);
};
template <typename TmppyInternal_17> struct CheckIfError { using type = void; };
template <typename TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_22;
// Split that generates value of:
template <typename... TmppyInternal_18, typename... TmppyInternal_19>
struct TmppyInternal_22<List<TmppyInternal_18...>, List<TmppyInternal_19...>> {
  static constexpr bool value = std::is_same<
      BoolList<
          (IsInTypeList<TmppyInternal_19, List<TmppyInternal_18...>>::value)...,
          (IsInTypeList<TmppyInternal_18,
                        List<TmppyInternal_19...>>::value)...>,
      BoolList<(Select1stBoolType<true, TmppyInternal_19>::value)...,
               (Select1stBoolType<true, TmppyInternal_18>::value)...>>::value;
};
template <typename TmppyInternal_5, typename TmppyInternal_6> struct eq {
  using error = void;
  static constexpr bool value =
      TmppyInternal_22<TmppyInternal_5, TmppyInternal_6>::value;
};
''')
def test_optimization_type_set_equals():
    from tmppy import Type
    from typing import Set
    def eq(x: Set[Type], y: Set[Type]):
        return x == y
    assert eq({Type('int')}, {Type('float')}) == False

if __name__== '__main__':
    main(__file__)
