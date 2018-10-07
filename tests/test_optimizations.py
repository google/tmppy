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
template <int64_t TmppyInternal_5> struct inc {
  using error = void;
  static constexpr int64_t value = (TmppyInternal_5) + (1LL);
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_one_function():
    def inc(n: int):
        return n + 1

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_toplevel_code():
    assert 1 + 1 == 2

@assert_code_optimizes_to(r'''
template <int64_t TmppyInternal_5> struct f {
  using error = void;
  static constexpr bool value = true;
};
template <typename T> struct CheckIfError { using type = void; };
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
template <typename T> struct CheckIfError { using type = void; };
''')
def test_common_subexpression_elimination_toplevel():
    from tmppy import Type
    assert (2*(3+1) == 2*(3+1)) == (Type.pointer(Type('int')) == Type.pointer(Type('int')))

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_common_subexpression_elimination_at_toplevel():
    from tmppy import Type
    assert (2*(3 + 1) == 2*(3 + 1)) == (Type.pointer(Type('int')) == Type.pointer(Type('int')))

@assert_code_optimizes_to(r'''
template <int64_t TmppyInternal_5> struct inc {
  using error = void;
  static constexpr int64_t value = (TmppyInternal_5) + (1LL);
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_two_functions_with_call():
    def _plus(n: int, m: int):
        return n + m
    def inc(n: int):
        return _plus(n, 1)

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_function_call_at_toplevel():
    def _plus(n: int, m: int):
        return n + m
    assert _plus(3, 1) == 4

@assert_code_optimizes_to(r'''
template <bool TmppyInternal_5, bool TmppyInternal_15> struct TmppyInternal_20;
template <bool TmppyInternal_5> struct TmppyInternal_22;
template <bool TmppyInternal_5> struct TmppyInternal_24;
// Split that generates value of: f
template <bool TmppyInternal_5> struct TmppyInternal_22 {
  static constexpr int64_t value =
      TmppyInternal_20<TmppyInternal_5, TmppyInternal_5>::value;
};
// Split that generates value of: g
template <bool TmppyInternal_5> struct TmppyInternal_24 {
  static constexpr int64_t value = TmppyInternal_22<TmppyInternal_5>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5> struct TmppyInternal_20<TmppyInternal_5, true> {
  static constexpr int64_t value = 3LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5>
struct TmppyInternal_20<TmppyInternal_5, false> {
  static constexpr int64_t value = TmppyInternal_24<true>::value;
};
template <bool TmppyInternal_5> struct f {
  using error = void;
  static constexpr int64_t value =
      TmppyInternal_20<TmppyInternal_5, TmppyInternal_5>::value;
};
template <bool TmppyInternal_5> struct g {
  using error = void;
  static constexpr int64_t value =
      TmppyInternal_20<TmppyInternal_5, TmppyInternal_5>::value;
};
template <typename T> struct CheckIfError { using type = void; };
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
template <bool TmppyInternal_5, bool TmppyInternal_15> struct TmppyInternal_20;
template <bool TmppyInternal_5> struct TmppyInternal_22;
template <bool TmppyInternal_5> struct TmppyInternal_24;
// Split that generates value of: f
template <bool TmppyInternal_5> struct TmppyInternal_22 {
  static constexpr int64_t value =
      TmppyInternal_20<TmppyInternal_5, TmppyInternal_5>::value;
};
// Split that generates value of: g
template <bool TmppyInternal_5> struct TmppyInternal_24 {
  static constexpr int64_t value = TmppyInternal_22<TmppyInternal_5>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5>
struct TmppyInternal_20<TmppyInternal_5, false> {
  static constexpr int64_t value = 3LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5> struct TmppyInternal_20<TmppyInternal_5, true> {
  static constexpr int64_t value = TmppyInternal_24<false>::value;
};
template <bool TmppyInternal_5> struct f {
  using error = void;
  static constexpr int64_t value =
      TmppyInternal_20<TmppyInternal_5, TmppyInternal_5>::value;
};
template <bool TmppyInternal_5> struct g {
  using error = void;
  static constexpr int64_t value =
      TmppyInternal_20<TmppyInternal_5, TmppyInternal_5>::value;
};
template <typename T> struct CheckIfError { using type = void; };
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
template <typename TmppyInternal_5, bool TmppyInternal_17>
struct TmppyInternal_22;
template <typename TmppyInternal_5> struct TmppyInternal_24;
template <typename TmppyInternal_5> struct TmppyInternal_26;
// Split that generates value of: f
template <typename TmppyInternal_5> struct TmppyInternal_24 {
  static constexpr int64_t value =
      TmppyInternal_22<TmppyInternal_5,
                       std::is_same<TmppyInternal_5, int>::value>::value;
};
// Split that generates value of: g
template <typename TmppyInternal_5> struct TmppyInternal_26 {
  static constexpr int64_t value = TmppyInternal_24<TmppyInternal_5>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename TmppyInternal_5>
struct TmppyInternal_22<TmppyInternal_5, true> {
  static constexpr int64_t value = 3LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename TmppyInternal_5>
struct TmppyInternal_22<TmppyInternal_5, false> {
  static constexpr int64_t value = TmppyInternal_26<int>::value;
};
template <typename TmppyInternal_5> struct f {
  using error = void;
  static constexpr int64_t value =
      TmppyInternal_22<TmppyInternal_5,
                       std::is_same<TmppyInternal_5, int>::value>::value;
};
template <typename TmppyInternal_5> struct g {
  using error = void;
  static constexpr int64_t value =
      TmppyInternal_22<TmppyInternal_5,
                       std::is_same<TmppyInternal_5, int>::value>::value;
};
template <typename T> struct CheckIfError { using type = void; };
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
template <typename T> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_char():
    from tmppy import Type
    assert Type('void') != Type('char')

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_short():
    from tmppy import Type
    assert Type('void') != Type('short')

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_int():
    from tmppy import Type
    assert Type('void') != Type('int')

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_int32_t():
    from tmppy import Type
    assert Type('void') != Type('int32_t')

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_int64_t():
    from tmppy import Type
    assert Type('void') != Type('int64_t')

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_uint32_t():
    from tmppy import Type
    assert Type('void') != Type('uint32_t')

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_uint64_t():
    from tmppy import Type
    assert Type('void') != Type('uint64_t')

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_unsigned():
    from tmppy import Type
    assert Type('void') != Type('unsigned')

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_long():
    from tmppy import Type
    assert Type('void') != Type('long')

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
''')
def test_is_same_optimization_void_float():
    from tmppy import Type
    assert Type('void') != Type('float')

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
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
template <typename T> struct CheckIfError { using type = void; };
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
template <typename T> struct CheckIfError { using type = void; };
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
template <typename T> struct CheckIfError { using type = void; };
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
template <typename T> struct CheckIfError { using type = void; };
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
template <typename T> struct CheckIfError { using type = void; };
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
template <typename T> struct CheckIfError { using type = void; };
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
template <typename T> struct CheckIfError { using type = void; };
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
template <bool TmppyInternal_5, bool TmppyInternal_24> struct TmppyInternal_35;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5> struct TmppyInternal_35<TmppyInternal_5, true> {
  static constexpr int64_t value = 5LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5>
struct TmppyInternal_35<TmppyInternal_5, false> {
  static constexpr int64_t value = -1LL;
};
template <bool TmppyInternal_5> struct f {
  using error = void;
  static constexpr int64_t value =
      TmppyInternal_35<TmppyInternal_5, TmppyInternal_5>::value;
};
template <typename TmppyInternal_8> struct TmppyInternal_49;
// Split that generates type of: g
template <bool... TmppyInternal_25>
struct TmppyInternal_49<BoolList<(TmppyInternal_25)...>> {
  using type = Int64List<(
      TmppyInternal_35<TmppyInternal_25, TmppyInternal_25>::value)...>;
};
template <typename TmppyInternal_8> struct g {
  using error = void;
  using type = typename TmppyInternal_49<TmppyInternal_8>::type;
};
template <typename T> struct CheckIfError { using type = void; };
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
template <bool TmppyInternal_5, bool TmppyInternal_27> struct TmppyInternal_38;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5> struct TmppyInternal_38<TmppyInternal_5, true> {
  static constexpr int64_t value = 5LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool TmppyInternal_5>
struct TmppyInternal_38<TmppyInternal_5, false> {
  static constexpr int64_t value = -1LL;
};
template <bool TmppyInternal_5> struct f {
  using error = void;
  static constexpr int64_t value =
      TmppyInternal_38<TmppyInternal_5, TmppyInternal_5>::value;
};
template <typename TmppyInternal_8, int64_t TmppyInternal_9>
struct TmppyInternal_52;
// Split that generates type of: g
template <bool... TmppyInternal_28, int64_t TmppyInternal_9>
struct TmppyInternal_52<BoolList<(TmppyInternal_28)...>, TmppyInternal_9> {
  using type =
      Int64List<((TmppyInternal_38<TmppyInternal_28, TmppyInternal_28>::value) +
                 (TmppyInternal_9))...>;
};
template <typename TmppyInternal_8, int64_t TmppyInternal_9> struct g {
  using error = void;
  using type =
      typename TmppyInternal_52<TmppyInternal_8, TmppyInternal_9>::type;
};
template <typename T> struct CheckIfError { using type = void; };
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
template <typename TmppyInternal_5> struct TmppyInternal_66;
// Split that generates type of: f
template <typename... TmppyInternal_31>
struct TmppyInternal_66<List<TmppyInternal_31...>> {
  using type = List<TmppyInternal_31 *const...>;
};
template <typename TmppyInternal_5> struct f {
  using error = void;
  using type = typename TmppyInternal_66<TmppyInternal_5>::type;
};
template <typename T> struct CheckIfError { using type = void; };
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
template <typename L1, typename L2> struct BoolListConcat;
template <bool... bs1, bool... bs2>
struct BoolListConcat<BoolList<(bs1)...>, BoolList<(bs2)...>> {
  using type = BoolList<(bs1)..., (bs2)...>;
};
template <typename TmppyInternalBuiltin_7, bool TmppyInternalBuiltin_21,
          bool TmppyInternalBuiltin_123>
struct TmppyInternalBuiltin_246;
// Split that generates type of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_7, bool TmppyInternalBuiltin_21>
struct TmppyInternalBuiltin_246<TmppyInternalBuiltin_7, TmppyInternalBuiltin_21,
                                true> {
  using type = TmppyInternalBuiltin_7;
};
// Split that generates type of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_7, bool TmppyInternalBuiltin_21>
struct TmppyInternalBuiltin_246<TmppyInternalBuiltin_7, TmppyInternalBuiltin_21,
                                false> {
  using type = typename BoolListConcat<BoolList<TmppyInternalBuiltin_21>,
                                       TmppyInternalBuiltin_7>::type;
};
template <bool TmppyInternal_5, bool TmppyInternal_6> struct set_of {
  using error = void;
  using type = typename TmppyInternalBuiltin_246<
      BoolList<TmppyInternal_5>, TmppyInternal_6,
      (TmppyInternal_6) == (TmppyInternal_5)>::type;
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_set_with_two_bools():
    def set_of(x: bool, y: bool):
        return {x, y}
    assert set_of(True, False) == {True, False}

@assert_code_optimizes_to(r'''
template <typename L1, typename L2> struct Int64ListConcat;
template <int64_t... ns, int64_t... ms>
struct Int64ListConcat<Int64List<(ns)...>, Int64List<(ms)...>> {
  using type = Int64List<(ns)..., (ms)...>;
};
template <typename TmppyInternalBuiltin_7, int64_t TmppyInternalBuiltin_28,
          bool TmppyInternalBuiltin_126>
struct TmppyInternalBuiltin_250;
// Split that generates type of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_7, int64_t TmppyInternalBuiltin_28>
struct TmppyInternalBuiltin_250<TmppyInternalBuiltin_7, TmppyInternalBuiltin_28,
                                true> {
  using type = TmppyInternalBuiltin_7;
};
// Split that generates type of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_7, int64_t TmppyInternalBuiltin_28>
struct TmppyInternalBuiltin_250<TmppyInternalBuiltin_7, TmppyInternalBuiltin_28,
                                false> {
  using type = typename Int64ListConcat<Int64List<TmppyInternalBuiltin_28>,
                                        TmppyInternalBuiltin_7>::type;
};
template <int64_t TmppyInternal_5, int64_t TmppyInternal_6> struct set_of {
  using error = void;
  using type = typename TmppyInternalBuiltin_250<
      Int64List<TmppyInternal_5>, TmppyInternal_6,
      (TmppyInternal_6) == (TmppyInternal_5)>::type;
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_set_with_two_ints():
    def set_of(x: int, y: int):
        return {x, y}
    assert set_of(3, 4) == {3, 4}

@assert_code_optimizes_to(r'''
template <typename L1, typename L2> struct TypeListConcat;
template <typename... Ts, typename... Us>
struct TypeListConcat<List<Ts...>, List<Us...>> {
  using type = List<Ts..., Us...>;
};
template <typename TmppyInternalBuiltin_7, typename TmppyInternalBuiltin_5,
          bool TmppyInternalBuiltin_129>
struct TmppyInternalBuiltin_254;
// Split that generates type of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_7, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_254<TmppyInternalBuiltin_7, TmppyInternalBuiltin_5,
                                true> {
  using type = TmppyInternalBuiltin_7;
};
// Split that generates type of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_7, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_254<TmppyInternalBuiltin_7, TmppyInternalBuiltin_5,
                                false> {
  using type = typename TypeListConcat<List<TmppyInternalBuiltin_5>,
                                       TmppyInternalBuiltin_7>::type;
};
template <typename TmppyInternal_5, typename TmppyInternal_6> struct set_of {
  using error = void;
  using type = typename TmppyInternalBuiltin_254<
      List<TmppyInternal_5>, TmppyInternal_6,
      std::is_same<TmppyInternal_6, TmppyInternal_5>::value>::type;
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_set_with_two_types():
    from tmppy import Type
    def set_of(x: Type, y: Type):
        return {x, y}
    assert set_of(Type('int'), Type('float')) == {Type('int'), Type('float')}

@assert_code_optimizes_to(r'''
template <bool TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_20;
// Split that generates value of: is_in_set
template <bool TmppyInternal_5, bool... TmppyInternal_15>
struct TmppyInternal_20<TmppyInternal_5, BoolList<(TmppyInternal_15)...>> {
  static constexpr bool value =
      !(std::is_same<BoolList<((TmppyInternal_5) == (TmppyInternal_15))...>,
                     BoolList<(Select1stBoolBool<
                               false, TmppyInternal_15>::value)...>>::value);
};
template <bool TmppyInternal_5, typename TmppyInternal_6> struct is_in_set {
  using error = void;
  static constexpr bool value =
      TmppyInternal_20<TmppyInternal_5, TmppyInternal_6>::value;
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_is_in_bool_set():
    from typing import Set
    def is_in_set(x: bool, y: Set[bool]):
        return x in y
    assert is_in_set(True, {False}) == False

@assert_code_optimizes_to(r'''
template <int64_t TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_20;
// Split that generates value of: is_in_set
template <int64_t TmppyInternal_5, int64_t... TmppyInternal_15>
struct TmppyInternal_20<TmppyInternal_5, Int64List<(TmppyInternal_15)...>> {
  static constexpr bool value =
      !(std::is_same<BoolList<((TmppyInternal_5) == (TmppyInternal_15))...>,
                     BoolList<(Select1stBoolInt64<
                               false, TmppyInternal_15>::value)...>>::value);
};
template <int64_t TmppyInternal_5, typename TmppyInternal_6> struct is_in_set {
  using error = void;
  static constexpr bool value =
      TmppyInternal_20<TmppyInternal_5, TmppyInternal_6>::value;
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_is_in_int_set():
    from typing import Set
    def is_in_set(x: int, y: Set[int]):
        return x in y
    assert is_in_set(3, {5}) == False

@assert_code_optimizes_to(r'''
template <typename TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_20;
// Split that generates value of: is_in_set
template <typename TmppyInternal_5, typename... TmppyInternal_15>
struct TmppyInternal_20<TmppyInternal_5, List<TmppyInternal_15...>> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<(std::is_same<TmppyInternal_5, TmppyInternal_15>::value)...>,
          BoolList<(Select1stBoolType<false, TmppyInternal_15>::value)...>>::
            value);
};
template <typename TmppyInternal_5, typename TmppyInternal_6> struct is_in_set {
  using error = void;
  static constexpr bool value =
      TmppyInternal_20<TmppyInternal_5, TmppyInternal_6>::value;
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_is_in_type_set():
    from tmppy import Type
    from typing import Set
    def is_in_set(x: Type, y: Set[Type]):
        return x in y
    assert is_in_set(Type('int'), {Type('float')}) == False

@assert_code_optimizes_to(r'''
template <typename TmppyInternalBuiltin_7> struct TmppyInternalBuiltin_196;
// Split that generates value of: BoolListAll
template <bool... TmppyInternalBuiltin_90>
struct TmppyInternalBuiltin_196<BoolList<(TmppyInternalBuiltin_90)...>> {
  static constexpr bool value = std::is_same<
      BoolList<(TmppyInternalBuiltin_90)...>,
      BoolList<(Select1stBoolBool<true, TmppyInternalBuiltin_90>::value)...>>::
      value;
};
template <typename TmppyInternalBuiltin_5, bool TmppyInternalBuiltin_58>
struct TmppyInternalBuiltin_260;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function BoolSetEquals
template <bool... TmppyInternalBuiltin_131, bool TmppyInternalBuiltin_58>
struct TmppyInternalBuiltin_260<BoolList<(TmppyInternalBuiltin_131)...>,
                                TmppyInternalBuiltin_58> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((TmppyInternalBuiltin_58) ==
                    (TmppyInternalBuiltin_131))...>,
          BoolList<(Select1stBoolBool<
                    false, TmppyInternalBuiltin_131>::value)...>>::value);
};
template <typename L, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_268;
// Split that generates type of: TmppyInternalBuiltin_138
template <bool... elems, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_268<BoolList<(elems)...>, TmppyInternalBuiltin_5> {
  using type = BoolList<(
      TmppyInternalBuiltin_260<TmppyInternalBuiltin_5, elems>::value)...>;
};
template <typename TmppyInternalBuiltin_35, typename TmppyInternalBuiltin_5,
          bool TmppyInternalBuiltin_143>
struct TmppyInternalBuiltin_276;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_35, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_276<TmppyInternalBuiltin_35, TmppyInternalBuiltin_5,
                                true> {
  static constexpr bool value =
      TmppyInternalBuiltin_196<typename TmppyInternalBuiltin_268<
          TmppyInternalBuiltin_35, TmppyInternalBuiltin_5>::type>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_35, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_276<TmppyInternalBuiltin_35, TmppyInternalBuiltin_5,
                                false> {
  static constexpr bool value = false;
};
template <typename TmppyInternalBuiltin_35, bool TmppyInternalBuiltin_51>
struct TmppyInternalBuiltin_258;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function BoolSetEquals
template <bool... TmppyInternalBuiltin_130, bool TmppyInternalBuiltin_51>
struct TmppyInternalBuiltin_258<BoolList<(TmppyInternalBuiltin_130)...>,
                                TmppyInternalBuiltin_51> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((TmppyInternalBuiltin_51) ==
                    (TmppyInternalBuiltin_130))...>,
          BoolList<(Select1stBoolBool<
                    false, TmppyInternalBuiltin_130>::value)...>>::value);
};
template <typename TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_23;
// Split that generates value of: eq
template <bool... TmppyInternal_17, bool... TmppyInternal_18>
struct TmppyInternal_23<BoolList<(TmppyInternal_17)...>,
                        BoolList<(TmppyInternal_18)...>> {
  static constexpr bool value = TmppyInternalBuiltin_276<
      BoolList<(TmppyInternal_18)...>, BoolList<(TmppyInternal_17)...>,
      std::is_same<
          BoolList<(TmppyInternalBuiltin_258<BoolList<(TmppyInternal_18)...>,
                                             TmppyInternal_17>::value)...>,
          BoolList<(Select1stBoolBool<true, TmppyInternal_17>::value)...>>::
          value>::value;
};
template <typename TmppyInternal_5, typename TmppyInternal_6> struct eq {
  using error = void;
  static constexpr bool value =
      TmppyInternal_23<TmppyInternal_5, TmppyInternal_6>::value;
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_bool_set_equals():
    from typing import Set
    def eq(x: Set[bool], y: Set[bool]):
        return x == y
    assert eq({True}, {False}) == False

@assert_code_optimizes_to(r'''
template <typename TmppyInternalBuiltin_7> struct TmppyInternalBuiltin_196;
// Split that generates value of: BoolListAll
template <bool... TmppyInternalBuiltin_90>
struct TmppyInternalBuiltin_196<BoolList<(TmppyInternalBuiltin_90)...>> {
  static constexpr bool value = std::is_same<
      BoolList<(TmppyInternalBuiltin_90)...>,
      BoolList<(Select1stBoolBool<true, TmppyInternalBuiltin_90>::value)...>>::
      value;
};
template <typename TmppyInternalBuiltin_5, int64_t TmppyInternalBuiltin_58>
struct TmppyInternalBuiltin_286;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function Int64SetEquals
template <int64_t... TmppyInternalBuiltin_148, int64_t TmppyInternalBuiltin_58>
struct TmppyInternalBuiltin_286<Int64List<(TmppyInternalBuiltin_148)...>,
                                TmppyInternalBuiltin_58> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((TmppyInternalBuiltin_58) ==
                    (TmppyInternalBuiltin_148))...>,
          BoolList<(Select1stBoolInt64<
                    false, TmppyInternalBuiltin_148>::value)...>>::value);
};
template <typename L, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_294;
// Split that generates type of: TmppyInternalBuiltin_155
template <int64_t... elems, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_294<Int64List<(elems)...>, TmppyInternalBuiltin_5> {
  using type = BoolList<(
      TmppyInternalBuiltin_286<TmppyInternalBuiltin_5, elems>::value)...>;
};
template <typename TmppyInternalBuiltin_35, typename TmppyInternalBuiltin_5,
          bool TmppyInternalBuiltin_160>
struct TmppyInternalBuiltin_302;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_35, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_302<TmppyInternalBuiltin_35, TmppyInternalBuiltin_5,
                                true> {
  static constexpr bool value =
      TmppyInternalBuiltin_196<typename TmppyInternalBuiltin_294<
          TmppyInternalBuiltin_35, TmppyInternalBuiltin_5>::type>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_35, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_302<TmppyInternalBuiltin_35, TmppyInternalBuiltin_5,
                                false> {
  static constexpr bool value = false;
};
template <typename TmppyInternalBuiltin_35, int64_t TmppyInternalBuiltin_51>
struct TmppyInternalBuiltin_284;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function Int64SetEquals
template <int64_t... TmppyInternalBuiltin_147, int64_t TmppyInternalBuiltin_51>
struct TmppyInternalBuiltin_284<Int64List<(TmppyInternalBuiltin_147)...>,
                                TmppyInternalBuiltin_51> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((TmppyInternalBuiltin_51) ==
                    (TmppyInternalBuiltin_147))...>,
          BoolList<(Select1stBoolInt64<
                    false, TmppyInternalBuiltin_147>::value)...>>::value);
};
template <typename TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_23;
// Split that generates value of: eq
template <int64_t... TmppyInternal_17, int64_t... TmppyInternal_18>
struct TmppyInternal_23<Int64List<(TmppyInternal_17)...>,
                        Int64List<(TmppyInternal_18)...>> {
  static constexpr bool value = TmppyInternalBuiltin_302<
      Int64List<(TmppyInternal_18)...>, Int64List<(TmppyInternal_17)...>,
      std::is_same<
          BoolList<(TmppyInternalBuiltin_284<Int64List<(TmppyInternal_18)...>,
                                             TmppyInternal_17>::value)...>,
          BoolList<(Select1stBoolInt64<true, TmppyInternal_17>::value)...>>::
          value>::value;
};
template <typename TmppyInternal_5, typename TmppyInternal_6> struct eq {
  using error = void;
  static constexpr bool value =
      TmppyInternal_23<TmppyInternal_5, TmppyInternal_6>::value;
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_int_set_equals():
    from typing import Set
    def eq(x: Set[int], y: Set[int]):
        return x == y
    assert eq({3}, {5}) == False

@assert_code_optimizes_to(r'''
template <typename TmppyInternalBuiltin_7> struct TmppyInternalBuiltin_196;
// Split that generates value of: BoolListAll
template <bool... TmppyInternalBuiltin_90>
struct TmppyInternalBuiltin_196<BoolList<(TmppyInternalBuiltin_90)...>> {
  static constexpr bool value = std::is_same<
      BoolList<(TmppyInternalBuiltin_90)...>,
      BoolList<(Select1stBoolBool<true, TmppyInternalBuiltin_90>::value)...>>::
      value;
};
template <typename TmppyInternalBuiltin_5, typename TmppyInternalBuiltin_58>
struct TmppyInternalBuiltin_312;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function TypeSetEquals
template <typename... TmppyInternalBuiltin_165,
          typename TmppyInternalBuiltin_58>
struct TmppyInternalBuiltin_312<List<TmppyInternalBuiltin_165...>,
                                TmppyInternalBuiltin_58> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<(std::is_same<TmppyInternalBuiltin_58,
                                 TmppyInternalBuiltin_165>::value)...>,
          BoolList<(Select1stBoolType<
                    false, TmppyInternalBuiltin_165>::value)...>>::value);
};
template <typename L, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_320;
// Split that generates type of: TmppyInternalBuiltin_172
template <typename... elems, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_320<List<elems...>, TmppyInternalBuiltin_5> {
  using type = BoolList<(
      TmppyInternalBuiltin_312<TmppyInternalBuiltin_5, elems>::value)...>;
};
template <typename TmppyInternalBuiltin_35, typename TmppyInternalBuiltin_5,
          bool TmppyInternalBuiltin_177>
struct TmppyInternalBuiltin_328;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_35, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_328<TmppyInternalBuiltin_35, TmppyInternalBuiltin_5,
                                true> {
  static constexpr bool value =
      TmppyInternalBuiltin_196<typename TmppyInternalBuiltin_320<
          TmppyInternalBuiltin_35, TmppyInternalBuiltin_5>::type>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename TmppyInternalBuiltin_35, typename TmppyInternalBuiltin_5>
struct TmppyInternalBuiltin_328<TmppyInternalBuiltin_35, TmppyInternalBuiltin_5,
                                false> {
  static constexpr bool value = false;
};
template <typename TmppyInternalBuiltin_35, typename TmppyInternalBuiltin_51>
struct TmppyInternalBuiltin_310;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function TypeSetEquals
template <typename... TmppyInternalBuiltin_164,
          typename TmppyInternalBuiltin_51>
struct TmppyInternalBuiltin_310<List<TmppyInternalBuiltin_164...>,
                                TmppyInternalBuiltin_51> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<(std::is_same<TmppyInternalBuiltin_51,
                                 TmppyInternalBuiltin_164>::value)...>,
          BoolList<(Select1stBoolType<
                    false, TmppyInternalBuiltin_164>::value)...>>::value);
};
template <typename TmppyInternal_5, typename TmppyInternal_6>
struct TmppyInternal_23;
// Split that generates value of: eq
template <typename... TmppyInternal_17, typename... TmppyInternal_18>
struct TmppyInternal_23<List<TmppyInternal_17...>, List<TmppyInternal_18...>> {
  static constexpr bool value = TmppyInternalBuiltin_328<
      List<TmppyInternal_18...>, List<TmppyInternal_17...>,
      std::is_same<
          BoolList<(TmppyInternalBuiltin_310<List<TmppyInternal_18...>,
                                             TmppyInternal_17>::value)...>,
          BoolList<(Select1stBoolType<true, TmppyInternal_17>::value)...>>::
          value>::value;
};
template <typename TmppyInternal_5, typename TmppyInternal_6> struct eq {
  using error = void;
  static constexpr bool value =
      TmppyInternal_23<TmppyInternal_5, TmppyInternal_6>::value;
};
template <typename T> struct CheckIfError { using type = void; };
''')
def test_optimization_type_set_equals():
    from tmppy import Type
    from typing import Set
    def eq(x: Set[Type], y: Set[Type]):
        return x == y
    assert eq({Type('int')}, {Type('float')}) == False

if __name__== '__main__':
    main(__file__)
