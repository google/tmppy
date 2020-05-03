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

from _py2tmp.compiler.testing import main, assert_code_optimizes_to, assert_compilation_fails_with_generic_error

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
template <int64_t tmppy_internal_test_module_x5> struct inc {
  using error = void;
  static constexpr int64_t value = (tmppy_internal_test_module_x5) + (1LL);
};
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
template <typename T> struct CheckIfError { using type = void; };
template <int64_t tmppy_internal_test_module_x5> struct f {
  using error = void;
  static constexpr bool value = true;
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
template <typename T> struct CheckIfError { using type = void; };
template <int64_t tmppy_internal_test_module_x5> struct inc {
  using error = void;
  static constexpr int64_t value = (tmppy_internal_test_module_x5) + (1LL);
};
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
template <typename T> struct CheckIfError { using type = void; };
template <bool tmppy_internal_test_module_x5,
          bool tmppy_internal_test_module_x15>
struct tmppy_internal_test_module_x20;
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x22;
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x24;
// Split that generates value of: f
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x22 {
  static constexpr int64_t value =
      tmppy_internal_test_module_x20<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x5>::value;
};
// Split that generates value of: g
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x24 {
  static constexpr int64_t value =
      tmppy_internal_test_module_x22<tmppy_internal_test_module_x5>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x20<tmppy_internal_test_module_x5, true> {
  static constexpr int64_t value = 3LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x20<tmppy_internal_test_module_x5, false> {
  static constexpr int64_t value = tmppy_internal_test_module_x24<true>::value;
};
template <bool tmppy_internal_test_module_x5> struct g {
  using error = void;
  static constexpr int64_t value =
      tmppy_internal_test_module_x20<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x5>::value;
};
template <bool tmppy_internal_test_module_x5> struct f {
  using error = void;
  static constexpr int64_t value =
      tmppy_internal_test_module_x20<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x5>::value;
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
template <typename T> struct CheckIfError { using type = void; };
template <bool tmppy_internal_test_module_x5,
          bool tmppy_internal_test_module_x15>
struct tmppy_internal_test_module_x20;
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x22;
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x24;
// Split that generates value of: f
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x22 {
  static constexpr int64_t value =
      tmppy_internal_test_module_x20<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x5>::value;
};
// Split that generates value of: g
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x24 {
  static constexpr int64_t value =
      tmppy_internal_test_module_x22<tmppy_internal_test_module_x5>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x20<tmppy_internal_test_module_x5, false> {
  static constexpr int64_t value = 3LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x20<tmppy_internal_test_module_x5, true> {
  static constexpr int64_t value = tmppy_internal_test_module_x24<false>::value;
};
template <bool tmppy_internal_test_module_x5> struct g {
  using error = void;
  static constexpr int64_t value =
      tmppy_internal_test_module_x20<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x5>::value;
};
template <bool tmppy_internal_test_module_x5> struct f {
  using error = void;
  static constexpr int64_t value =
      tmppy_internal_test_module_x20<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x5>::value;
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
template <typename T> struct CheckIfError { using type = void; };
template <typename tmppy_internal_test_module_x5,
          bool tmppy_internal_test_module_x17>
struct tmppy_internal_test_module_x22;
template <typename tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x24;
template <typename tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x26;
// Split that generates value of: f
template <typename tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x24 {
  static constexpr int64_t value = tmppy_internal_test_module_x22<
      tmppy_internal_test_module_x5,
      std::is_same<tmppy_internal_test_module_x5, int>::value>::value;
};
// Split that generates value of: g
template <typename tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x26 {
  static constexpr int64_t value =
      tmppy_internal_test_module_x24<tmppy_internal_test_module_x5>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x22<tmppy_internal_test_module_x5, true> {
  static constexpr int64_t value = 3LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x22<tmppy_internal_test_module_x5, false> {
  static constexpr int64_t value = tmppy_internal_test_module_x26<int>::value;
};
template <typename tmppy_internal_test_module_x5> struct g {
  using error = void;
  static constexpr int64_t value = tmppy_internal_test_module_x22<
      tmppy_internal_test_module_x5,
      std::is_same<tmppy_internal_test_module_x5, int>::value>::value;
};
template <typename tmppy_internal_test_module_x5> struct f {
  using error = void;
  static constexpr int64_t value = tmppy_internal_test_module_x22<
      tmppy_internal_test_module_x5,
      std::is_same<tmppy_internal_test_module_x5, int>::value>::value;
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

@assert_compilation_fails_with_generic_error('template instantiation depth exceeds maximum'
                                             '|constexpr variable .value. must be initialized by a constant expression'
                                             '|no member named .value. in .g<1>.',
                                             allow_reaching_max_optimization_loops=True)
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
template <typename T> struct CheckIfError { using type = void; };
template <bool tmppy_internal_test_module_x5,
          bool tmppy_internal_test_module_x24>
struct tmppy_internal_test_module_x35;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x35<tmppy_internal_test_module_x5, true> {
  static constexpr int64_t value = 5LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x35<tmppy_internal_test_module_x5, false> {
  static constexpr int64_t value = -1LL;
};
template <typename tmppy_internal_test_module_x8>
struct tmppy_internal_test_module_x49;
// Split that generates type of: g
template <bool... tmppy_internal_test_module_x25>
struct tmppy_internal_test_module_x49<
    BoolList<tmppy_internal_test_module_x25...>> {
  using type = Int64List<(tmppy_internal_test_module_x35<
                          tmppy_internal_test_module_x25,
                          tmppy_internal_test_module_x25>::value)...>;
};
template <typename tmppy_internal_test_module_x8> struct g {
  using error = void;
  using type = typename tmppy_internal_test_module_x49<
      tmppy_internal_test_module_x8>::type;
};
template <bool tmppy_internal_test_module_x5> struct f {
  using error = void;
  static constexpr int64_t value =
      tmppy_internal_test_module_x35<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x5>::value;
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
template <typename T> struct CheckIfError { using type = void; };
template <bool tmppy_internal_test_module_x5,
          bool tmppy_internal_test_module_x27>
struct tmppy_internal_test_module_x38;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x38<tmppy_internal_test_module_x5, true> {
  static constexpr int64_t value = 5LL;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <bool tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x38<tmppy_internal_test_module_x5, false> {
  static constexpr int64_t value = -1LL;
};
template <typename tmppy_internal_test_module_x8>
struct tmppy_internal_test_module_x52;
// Split that generates type of: g
template <bool... tmppy_internal_test_module_x28>
struct tmppy_internal_test_module_x52<
    BoolList<tmppy_internal_test_module_x28...>> {
  template <int64_t tmppy_internal_test_module_x9>
  using type = Int64List<(
      (tmppy_internal_test_module_x38<tmppy_internal_test_module_x28,
                                      tmppy_internal_test_module_x28>::value) +
      (tmppy_internal_test_module_x9))...>;
};
template <typename tmppy_internal_test_module_x8,
          int64_t tmppy_internal_test_module_x9>
struct g {
  using error = void;
  using type =
      typename tmppy_internal_test_module_x52<tmppy_internal_test_module_x8>::
          template type<tmppy_internal_test_module_x9>;
};
template <bool tmppy_internal_test_module_x5> struct f {
  using error = void;
  static constexpr int64_t value =
      tmppy_internal_test_module_x38<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x5>::value;
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
template <typename T> struct CheckIfError { using type = void; };
template <typename tmppy_internal_test_module_x5>
struct tmppy_internal_test_module_x66;
// Split that generates type of: f
template <typename... tmppy_internal_test_module_x31>
struct tmppy_internal_test_module_x66<List<tmppy_internal_test_module_x31...>> {
  using type = List<tmppy_internal_test_module_x31 *const...>;
};
template <typename tmppy_internal_test_module_x5> struct f {
  using error = void;
  using type = typename tmppy_internal_test_module_x66<
      tmppy_internal_test_module_x5>::type;
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
template <typename T> struct CheckIfError { using type = void; };
template <typename L1, typename L2> struct BoolListConcat;
template <bool... bs1, bool... bs2>
struct BoolListConcat<BoolList<bs1...>, BoolList<bs2...>> {
  using type = BoolList<(bs1)..., (bs2)...>;
};
template <bool tmppy_internal_tmppy_builtins_x123>
struct tmppy_internal_tmppy_builtins_x246;
// Split that generates type of: (meta)function generated for an if-else
// statement
template <> struct tmppy_internal_tmppy_builtins_x246<true> {
  template <typename tmppy_internal_tmppy_builtins_x7,
            bool tmppy_internal_tmppy_builtins_x21>
  using type = tmppy_internal_tmppy_builtins_x7;
};
// Split that generates type of: (meta)function generated for an if-else
// statement
template <> struct tmppy_internal_tmppy_builtins_x246<false> {
  template <typename tmppy_internal_tmppy_builtins_x7,
            bool tmppy_internal_tmppy_builtins_x21>
  using type =
      typename BoolListConcat<BoolList<tmppy_internal_tmppy_builtins_x21>,
                              tmppy_internal_tmppy_builtins_x7>::type;
};
template <bool tmppy_internal_test_module_x5,
          bool tmppy_internal_test_module_x6>
struct set_of {
  using error = void;
  using type = typename tmppy_internal_tmppy_builtins_x246<
      (tmppy_internal_test_module_x6) == (tmppy_internal_test_module_x5)>::
      template type<BoolList<tmppy_internal_test_module_x5>,
                    tmppy_internal_test_module_x6>;
};
''')
def test_optimization_set_with_two_bools():
    def set_of(x: bool, y: bool):
        return {x, y}
    assert set_of(True, False) == {True, False}

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
template <typename L1, typename L2> struct Int64ListConcat;
template <int64_t... ns, int64_t... ms>
struct Int64ListConcat<Int64List<ns...>, Int64List<ms...>> {
  using type = Int64List<(ns)..., (ms)...>;
};
template <bool tmppy_internal_tmppy_builtins_x126>
struct tmppy_internal_tmppy_builtins_x250;
// Split that generates type of: (meta)function generated for an if-else
// statement
template <> struct tmppy_internal_tmppy_builtins_x250<true> {
  template <typename tmppy_internal_tmppy_builtins_x7,
            int64_t tmppy_internal_tmppy_builtins_x28>
  using type = tmppy_internal_tmppy_builtins_x7;
};
// Split that generates type of: (meta)function generated for an if-else
// statement
template <> struct tmppy_internal_tmppy_builtins_x250<false> {
  template <typename tmppy_internal_tmppy_builtins_x7,
            int64_t tmppy_internal_tmppy_builtins_x28>
  using type =
      typename Int64ListConcat<Int64List<tmppy_internal_tmppy_builtins_x28>,
                               tmppy_internal_tmppy_builtins_x7>::type;
};
template <int64_t tmppy_internal_test_module_x5,
          int64_t tmppy_internal_test_module_x6>
struct set_of {
  using error = void;
  using type = typename tmppy_internal_tmppy_builtins_x250<
      (tmppy_internal_test_module_x6) == (tmppy_internal_test_module_x5)>::
      template type<Int64List<tmppy_internal_test_module_x5>,
                    tmppy_internal_test_module_x6>;
};
''')
def test_optimization_set_with_two_ints():
    def set_of(x: int, y: int):
        return {x, y}
    assert set_of(3, 4) == {3, 4}

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
template <typename L1, typename L2> struct TypeListConcat;
template <typename... Ts, typename... Us>
struct TypeListConcat<List<Ts...>, List<Us...>> {
  using type = List<Ts..., Us...>;
};
template <bool tmppy_internal_tmppy_builtins_x129>
struct tmppy_internal_tmppy_builtins_x254;
// Split that generates type of: (meta)function generated for an if-else
// statement
template <> struct tmppy_internal_tmppy_builtins_x254<true> {
  template <typename tmppy_internal_tmppy_builtins_x7,
            typename tmppy_internal_tmppy_builtins_x5>
  using type = tmppy_internal_tmppy_builtins_x7;
};
// Split that generates type of: (meta)function generated for an if-else
// statement
template <> struct tmppy_internal_tmppy_builtins_x254<false> {
  template <typename tmppy_internal_tmppy_builtins_x7,
            typename tmppy_internal_tmppy_builtins_x5>
  using type = typename TypeListConcat<List<tmppy_internal_tmppy_builtins_x5>,
                                       tmppy_internal_tmppy_builtins_x7>::type;
};
template <typename tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct set_of {
  using error = void;
  using type = typename tmppy_internal_tmppy_builtins_x254<std::is_same<
      tmppy_internal_test_module_x6, tmppy_internal_test_module_x5>::value>::
      template type<List<tmppy_internal_test_module_x5>,
                    tmppy_internal_test_module_x6>;
};
''')
def test_optimization_set_with_two_types():
    from tmppy import Type
    def set_of(x: Type, y: Type):
        return {x, y}
    assert set_of(Type('int'), Type('float')) == {Type('int'), Type('float')}

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
template <bool tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct tmppy_internal_test_module_x20;
// Split that generates value of: is_in_set
template <bool tmppy_internal_test_module_x5,
          bool... tmppy_internal_test_module_x15>
struct tmppy_internal_test_module_x20<
    tmppy_internal_test_module_x5,
    BoolList<tmppy_internal_test_module_x15...>> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((tmppy_internal_test_module_x5) ==
                    (tmppy_internal_test_module_x15))...>,
          BoolList<(Select1stBoolBool<
                    false, tmppy_internal_test_module_x15>::value)...>>::value);
};
template <bool tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct is_in_set {
  using error = void;
  static constexpr bool value =
      tmppy_internal_test_module_x20<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x6>::value;
};
''')
def test_optimization_is_in_bool_set():
    from typing import Set
    def is_in_set(x: bool, y: Set[bool]):
        return x in y
    assert is_in_set(True, {False}) == False

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
template <int64_t tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct tmppy_internal_test_module_x20;
// Split that generates value of: is_in_set
template <int64_t tmppy_internal_test_module_x5,
          int64_t... tmppy_internal_test_module_x15>
struct tmppy_internal_test_module_x20<
    tmppy_internal_test_module_x5,
    Int64List<tmppy_internal_test_module_x15...>> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((tmppy_internal_test_module_x5) ==
                    (tmppy_internal_test_module_x15))...>,
          BoolList<(Select1stBoolInt64<
                    false, tmppy_internal_test_module_x15>::value)...>>::value);
};
template <int64_t tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct is_in_set {
  using error = void;
  static constexpr bool value =
      tmppy_internal_test_module_x20<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x6>::value;
};
''')
def test_optimization_is_in_int_set():
    from typing import Set
    def is_in_set(x: int, y: Set[int]):
        return x in y
    assert is_in_set(3, {5}) == False

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
template <typename tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct tmppy_internal_test_module_x20;
// Split that generates value of: is_in_set
template <typename tmppy_internal_test_module_x5,
          typename... tmppy_internal_test_module_x15>
struct tmppy_internal_test_module_x20<tmppy_internal_test_module_x5,
                                      List<tmppy_internal_test_module_x15...>> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<(std::is_same<tmppy_internal_test_module_x5,
                                 tmppy_internal_test_module_x15>::value)...>,
          BoolList<(Select1stBoolType<
                    false, tmppy_internal_test_module_x15>::value)...>>::value);
};
template <typename tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct is_in_set {
  using error = void;
  static constexpr bool value =
      tmppy_internal_test_module_x20<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x6>::value;
};
''')
def test_optimization_is_in_type_set():
    from tmppy import Type
    from typing import Set
    def is_in_set(x: Type, y: Set[Type]):
        return x in y
    assert is_in_set(Type('int'), {Type('float')}) == False

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
template <typename tmppy_internal_tmppy_builtins_x5,
          bool tmppy_internal_tmppy_builtins_x58>
struct tmppy_internal_tmppy_builtins_x260;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function BoolSetEquals
template <bool... tmppy_internal_tmppy_builtins_x131,
          bool tmppy_internal_tmppy_builtins_x58>
struct tmppy_internal_tmppy_builtins_x260<
    BoolList<tmppy_internal_tmppy_builtins_x131...>,
    tmppy_internal_tmppy_builtins_x58> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((tmppy_internal_tmppy_builtins_x58) ==
                    (tmppy_internal_tmppy_builtins_x131))...>,
          BoolList<(Select1stBoolBool<
                    false, tmppy_internal_tmppy_builtins_x131>::value)...>>::
            value);
};
template <typename L> struct tmppy_internal_tmppy_builtins_x268;
// Split that generates type of: tmppy_internal_tmppy_builtins_x138
template <bool... elems>
struct tmppy_internal_tmppy_builtins_x268<BoolList<elems...>> {
  template <typename tmppy_internal_tmppy_builtins_x5>
  using type = BoolList<(tmppy_internal_tmppy_builtins_x260<
                         tmppy_internal_tmppy_builtins_x5, elems>::value)...>;
};
template <typename tmppy_internal_tmppy_builtins_x7>
struct tmppy_internal_tmppy_builtins_x196;
// Split that generates value of: BoolListAll
template <bool... tmppy_internal_tmppy_builtins_x90>
struct tmppy_internal_tmppy_builtins_x196<
    BoolList<tmppy_internal_tmppy_builtins_x90...>> {
  static constexpr bool value = std::is_same<
      BoolList<(tmppy_internal_tmppy_builtins_x90)...>,
      BoolList<(Select1stBoolBool<
                true, tmppy_internal_tmppy_builtins_x90>::value)...>>::value;
};
template <typename tmppy_internal_tmppy_builtins_x35,
          typename tmppy_internal_tmppy_builtins_x5,
          bool tmppy_internal_tmppy_builtins_x143>
struct tmppy_internal_tmppy_builtins_x276;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename tmppy_internal_tmppy_builtins_x35,
          typename tmppy_internal_tmppy_builtins_x5>
struct tmppy_internal_tmppy_builtins_x276<
    tmppy_internal_tmppy_builtins_x35, tmppy_internal_tmppy_builtins_x5, true> {
  static constexpr bool value = tmppy_internal_tmppy_builtins_x196<
      typename tmppy_internal_tmppy_builtins_x268<
          tmppy_internal_tmppy_builtins_x35>::
          template type<tmppy_internal_tmppy_builtins_x5>>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename tmppy_internal_tmppy_builtins_x35,
          typename tmppy_internal_tmppy_builtins_x5>
struct tmppy_internal_tmppy_builtins_x276<tmppy_internal_tmppy_builtins_x35,
                                          tmppy_internal_tmppy_builtins_x5,
                                          false> {
  static constexpr bool value = false;
};
template <typename tmppy_internal_tmppy_builtins_x35,
          bool tmppy_internal_tmppy_builtins_x51>
struct tmppy_internal_tmppy_builtins_x258;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function BoolSetEquals
template <bool... tmppy_internal_tmppy_builtins_x130,
          bool tmppy_internal_tmppy_builtins_x51>
struct tmppy_internal_tmppy_builtins_x258<
    BoolList<tmppy_internal_tmppy_builtins_x130...>,
    tmppy_internal_tmppy_builtins_x51> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((tmppy_internal_tmppy_builtins_x51) ==
                    (tmppy_internal_tmppy_builtins_x130))...>,
          BoolList<(Select1stBoolBool<
                    false, tmppy_internal_tmppy_builtins_x130>::value)...>>::
            value);
};
template <typename tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct tmppy_internal_test_module_x23;
// Split that generates value of: eq
template <bool... tmppy_internal_test_module_x17,
          bool... tmppy_internal_test_module_x18>
struct tmppy_internal_test_module_x23<
    BoolList<tmppy_internal_test_module_x17...>,
    BoolList<tmppy_internal_test_module_x18...>> {
  static constexpr bool value = tmppy_internal_tmppy_builtins_x276<
      BoolList<(tmppy_internal_test_module_x18)...>,
      BoolList<(tmppy_internal_test_module_x17)...>,
      std::is_same<
          BoolList<(tmppy_internal_tmppy_builtins_x258<
                    BoolList<(tmppy_internal_test_module_x18)...>,
                    tmppy_internal_test_module_x17>::value)...>,
          BoolList<(Select1stBoolBool<true, tmppy_internal_test_module_x17>::
                        value)...>>::value>::value;
};
template <typename tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct eq {
  using error = void;
  static constexpr bool value =
      tmppy_internal_test_module_x23<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x6>::value;
};
''')
def test_optimization_bool_set_equals():
    from typing import Set
    def eq(x: Set[bool], y: Set[bool]):
        return x == y
    assert eq({True}, {False}) == False

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
template <typename tmppy_internal_tmppy_builtins_x5,
          int64_t tmppy_internal_tmppy_builtins_x58>
struct tmppy_internal_tmppy_builtins_x286;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function Int64SetEquals
template <int64_t... tmppy_internal_tmppy_builtins_x148,
          int64_t tmppy_internal_tmppy_builtins_x58>
struct tmppy_internal_tmppy_builtins_x286<
    Int64List<tmppy_internal_tmppy_builtins_x148...>,
    tmppy_internal_tmppy_builtins_x58> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((tmppy_internal_tmppy_builtins_x58) ==
                    (tmppy_internal_tmppy_builtins_x148))...>,
          BoolList<(Select1stBoolInt64<
                    false, tmppy_internal_tmppy_builtins_x148>::value)...>>::
            value);
};
template <typename L> struct tmppy_internal_tmppy_builtins_x294;
// Split that generates type of: tmppy_internal_tmppy_builtins_x155
template <int64_t... elems>
struct tmppy_internal_tmppy_builtins_x294<Int64List<elems...>> {
  template <typename tmppy_internal_tmppy_builtins_x5>
  using type = BoolList<(tmppy_internal_tmppy_builtins_x286<
                         tmppy_internal_tmppy_builtins_x5, elems>::value)...>;
};
template <typename tmppy_internal_tmppy_builtins_x7>
struct tmppy_internal_tmppy_builtins_x196;
// Split that generates value of: BoolListAll
template <bool... tmppy_internal_tmppy_builtins_x90>
struct tmppy_internal_tmppy_builtins_x196<
    BoolList<tmppy_internal_tmppy_builtins_x90...>> {
  static constexpr bool value = std::is_same<
      BoolList<(tmppy_internal_tmppy_builtins_x90)...>,
      BoolList<(Select1stBoolBool<
                true, tmppy_internal_tmppy_builtins_x90>::value)...>>::value;
};
template <typename tmppy_internal_tmppy_builtins_x35,
          typename tmppy_internal_tmppy_builtins_x5,
          bool tmppy_internal_tmppy_builtins_x160>
struct tmppy_internal_tmppy_builtins_x302;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename tmppy_internal_tmppy_builtins_x35,
          typename tmppy_internal_tmppy_builtins_x5>
struct tmppy_internal_tmppy_builtins_x302<
    tmppy_internal_tmppy_builtins_x35, tmppy_internal_tmppy_builtins_x5, true> {
  static constexpr bool value = tmppy_internal_tmppy_builtins_x196<
      typename tmppy_internal_tmppy_builtins_x294<
          tmppy_internal_tmppy_builtins_x35>::
          template type<tmppy_internal_tmppy_builtins_x5>>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename tmppy_internal_tmppy_builtins_x35,
          typename tmppy_internal_tmppy_builtins_x5>
struct tmppy_internal_tmppy_builtins_x302<tmppy_internal_tmppy_builtins_x35,
                                          tmppy_internal_tmppy_builtins_x5,
                                          false> {
  static constexpr bool value = false;
};
template <typename tmppy_internal_tmppy_builtins_x35,
          int64_t tmppy_internal_tmppy_builtins_x51>
struct tmppy_internal_tmppy_builtins_x284;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function Int64SetEquals
template <int64_t... tmppy_internal_tmppy_builtins_x147,
          int64_t tmppy_internal_tmppy_builtins_x51>
struct tmppy_internal_tmppy_builtins_x284<
    Int64List<tmppy_internal_tmppy_builtins_x147...>,
    tmppy_internal_tmppy_builtins_x51> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<((tmppy_internal_tmppy_builtins_x51) ==
                    (tmppy_internal_tmppy_builtins_x147))...>,
          BoolList<(Select1stBoolInt64<
                    false, tmppy_internal_tmppy_builtins_x147>::value)...>>::
            value);
};
template <typename tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct tmppy_internal_test_module_x23;
// Split that generates value of: eq
template <int64_t... tmppy_internal_test_module_x17,
          int64_t... tmppy_internal_test_module_x18>
struct tmppy_internal_test_module_x23<
    Int64List<tmppy_internal_test_module_x17...>,
    Int64List<tmppy_internal_test_module_x18...>> {
  static constexpr bool value = tmppy_internal_tmppy_builtins_x302<
      Int64List<(tmppy_internal_test_module_x18)...>,
      Int64List<(tmppy_internal_test_module_x17)...>,
      std::is_same<
          BoolList<(tmppy_internal_tmppy_builtins_x284<
                    Int64List<(tmppy_internal_test_module_x18)...>,
                    tmppy_internal_test_module_x17>::value)...>,
          BoolList<(Select1stBoolInt64<true, tmppy_internal_test_module_x17>::
                        value)...>>::value>::value;
};
template <typename tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct eq {
  using error = void;
  static constexpr bool value =
      tmppy_internal_test_module_x23<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x6>::value;
};
''')
def test_optimization_int_set_equals():
    from typing import Set
    def eq(x: Set[int], y: Set[int]):
        return x == y
    assert eq({3}, {5}) == False

@assert_code_optimizes_to(r'''
template <typename T> struct CheckIfError { using type = void; };
template <typename tmppy_internal_tmppy_builtins_x5,
          typename tmppy_internal_tmppy_builtins_x58>
struct tmppy_internal_tmppy_builtins_x312;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function TypeSetEquals
template <typename... tmppy_internal_tmppy_builtins_x165,
          typename tmppy_internal_tmppy_builtins_x58>
struct tmppy_internal_tmppy_builtins_x312<
    List<tmppy_internal_tmppy_builtins_x165...>,
    tmppy_internal_tmppy_builtins_x58> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<(
              std::is_same<tmppy_internal_tmppy_builtins_x58,
                           tmppy_internal_tmppy_builtins_x165>::value)...>,
          BoolList<(Select1stBoolType<
                    false, tmppy_internal_tmppy_builtins_x165>::value)...>>::
            value);
};
template <typename L> struct tmppy_internal_tmppy_builtins_x320;
// Split that generates type of: tmppy_internal_tmppy_builtins_x172
template <typename... elems>
struct tmppy_internal_tmppy_builtins_x320<List<elems...>> {
  template <typename tmppy_internal_tmppy_builtins_x5>
  using type = BoolList<(tmppy_internal_tmppy_builtins_x312<
                         tmppy_internal_tmppy_builtins_x5, elems>::value)...>;
};
template <typename tmppy_internal_tmppy_builtins_x7>
struct tmppy_internal_tmppy_builtins_x196;
// Split that generates value of: BoolListAll
template <bool... tmppy_internal_tmppy_builtins_x90>
struct tmppy_internal_tmppy_builtins_x196<
    BoolList<tmppy_internal_tmppy_builtins_x90...>> {
  static constexpr bool value = std::is_same<
      BoolList<(tmppy_internal_tmppy_builtins_x90)...>,
      BoolList<(Select1stBoolBool<
                true, tmppy_internal_tmppy_builtins_x90>::value)...>>::value;
};
template <typename tmppy_internal_tmppy_builtins_x35,
          typename tmppy_internal_tmppy_builtins_x5,
          bool tmppy_internal_tmppy_builtins_x177>
struct tmppy_internal_tmppy_builtins_x328;
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename tmppy_internal_tmppy_builtins_x35,
          typename tmppy_internal_tmppy_builtins_x5>
struct tmppy_internal_tmppy_builtins_x328<
    tmppy_internal_tmppy_builtins_x35, tmppy_internal_tmppy_builtins_x5, true> {
  static constexpr bool value = tmppy_internal_tmppy_builtins_x196<
      typename tmppy_internal_tmppy_builtins_x320<
          tmppy_internal_tmppy_builtins_x35>::
          template type<tmppy_internal_tmppy_builtins_x5>>::value;
};
// Split that generates value of: (meta)function generated for an if-else
// statement
template <typename tmppy_internal_tmppy_builtins_x35,
          typename tmppy_internal_tmppy_builtins_x5>
struct tmppy_internal_tmppy_builtins_x328<tmppy_internal_tmppy_builtins_x35,
                                          tmppy_internal_tmppy_builtins_x5,
                                          false> {
  static constexpr bool value = false;
};
template <typename tmppy_internal_tmppy_builtins_x35,
          typename tmppy_internal_tmppy_builtins_x51>
struct tmppy_internal_tmppy_builtins_x310;
// Split that generates value of: (meta)function wrapping the result expression
// in a list/set comprehension from the function TypeSetEquals
template <typename... tmppy_internal_tmppy_builtins_x164,
          typename tmppy_internal_tmppy_builtins_x51>
struct tmppy_internal_tmppy_builtins_x310<
    List<tmppy_internal_tmppy_builtins_x164...>,
    tmppy_internal_tmppy_builtins_x51> {
  static constexpr bool value =
      !(std::is_same<
          BoolList<(
              std::is_same<tmppy_internal_tmppy_builtins_x51,
                           tmppy_internal_tmppy_builtins_x164>::value)...>,
          BoolList<(Select1stBoolType<
                    false, tmppy_internal_tmppy_builtins_x164>::value)...>>::
            value);
};
template <typename tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct tmppy_internal_test_module_x23;
// Split that generates value of: eq
template <typename... tmppy_internal_test_module_x17,
          typename... tmppy_internal_test_module_x18>
struct tmppy_internal_test_module_x23<List<tmppy_internal_test_module_x17...>,
                                      List<tmppy_internal_test_module_x18...>> {
  static constexpr bool value = tmppy_internal_tmppy_builtins_x328<
      List<tmppy_internal_test_module_x18...>,
      List<tmppy_internal_test_module_x17...>,
      std::is_same<
          BoolList<(tmppy_internal_tmppy_builtins_x310<
                    List<tmppy_internal_test_module_x18...>,
                    tmppy_internal_test_module_x17>::value)...>,
          BoolList<(Select1stBoolType<true, tmppy_internal_test_module_x17>::
                        value)...>>::value>::value;
};
template <typename tmppy_internal_test_module_x5,
          typename tmppy_internal_test_module_x6>
struct eq {
  using error = void;
  static constexpr bool value =
      tmppy_internal_test_module_x23<tmppy_internal_test_module_x5,
                                     tmppy_internal_test_module_x6>::value;
};
''')
def test_optimization_type_set_equals():
    from tmppy import Type
    from typing import Set
    def eq(x: Set[Type], y: Set[Type]):
        return x == y
    assert eq({Type('int')}, {Type('float')}) == False

if __name__== '__main__':
    main()
