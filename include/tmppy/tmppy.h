/*
 * Copyright 2017 Google Inc. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *     http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef TMPPY_H
#define TMPPY_H

#include <cstdint>
#include <type_traits>

template <typename...>
struct List;

template <int64_t...>
struct Int64List;

template <bool...>
struct BoolList;

template <bool>
struct AlwaysTrueFromBool {
  static constexpr bool value = true;
};

template <int64_t>
struct AlwaysTrueFromInt64 {
  static constexpr bool value = true;
};

template <typename>
struct AlwaysTrueFromType {
  static constexpr bool value = true;
};

template <typename>
struct AlwaysFalseFromType {
  static constexpr bool value = false;
};

template <bool b, bool>
struct Select1stBoolBool {
  static constexpr bool value = b;
};

template <bool b, int64_t>
struct Select1stBoolInt64 {
  static constexpr bool value = b;
};

template <bool b, typename>
struct Select1stBoolType {
  static constexpr bool value = b;
};

template <int64_t n, bool>
struct Select1stInt64Bool {
  static constexpr int64_t value = n;
};

template <int64_t n, int64_t>
struct Select1stInt64Int64 {
  static constexpr int64_t value = n;
};

template <int64_t n, typename>
struct Select1stInt64Type {
  static constexpr int64_t value = n;
};

template <typename T, bool>
struct Select1stTypeBool {
  // We intentionally use `value` instead of `type`, for simplicity of the implementation.
  using value = T;
};

template <typename T, int64_t>
struct Select1stTypeInt64 {
  // We intentionally use `value` instead of `type`, for simplicity of the implementation.
  using value = T;
};

template <typename T, typename>
struct Select1stTypeType {
  // We intentionally use `value` instead of `type`, for simplicity of the implementation.
  using value = T;
};

template <typename L1, typename L2>
struct TypeListConcat;

template <typename... Ts, typename... Us>
struct TypeListConcat<List<Ts...>, List<Us...>> {
  using type = List<Ts..., Us...>;
};

template <typename L1, typename L2>
struct Int64ListConcat;

template <int64_t... ns, int64_t... ms>
struct Int64ListConcat<Int64List<ns...>, Int64List<ms...>> {
  using type = Int64List<ns..., ms...>;
};

template <typename L1, typename L2>
struct BoolListConcat;

template <bool... bs1, bool... bs2>
struct BoolListConcat<BoolList<bs1...>, BoolList<bs2...>> {
  using type = BoolList<bs1..., bs2...>;
};

template <typename L>
struct Int64ListSum {
  static constexpr int64_t value = 0;
};

template <int64_t n, int64_t... ns>
struct Int64ListSum<Int64List<n, ns...>> {
  static constexpr int64_t value = n + Int64ListSum<Int64List<ns...>>::value;
};

template <typename L>
struct BoolListAll;

template <bool... bs>
struct BoolListAll<BoolList<bs...>> {
  static constexpr bool value = std::is_same<BoolList<bs...>, BoolList<(bs || true)...>>::value;
};

template <typename L>
struct BoolListAny;

template <bool... bs>
struct BoolListAny<BoolList<bs...>> {
  static constexpr bool value = !std::is_same<BoolList<bs...>, BoolList<(bs && false)...>>::value;
};

template <typename... Ts>
struct GetFirstError {
  using type = void;
};

template <typename... Ts>
struct GetFirstError<void, Ts...> {
  using type = typename GetFirstError<Ts...>::type;
};

template <typename T, typename... Ts>
struct GetFirstError<T, Ts...> {
  using type = T;
};

template <typename L, template <bool> class F>
struct TransformBoolListToBoolList;

template <bool... bs, template <bool> class F>
struct TransformBoolListToBoolList<BoolList<bs...>, F> {
  using error = typename GetFirstError<typename F<bs>::error...>::type;
  using type = BoolList<F<bs>::value...>;
};

template <typename L, template <bool> class F>
struct TransformBoolListToInt64List;

template <bool... bs, template <bool> class F>
struct TransformBoolListToInt64List<BoolList<bs...>, F> {
  using error = typename GetFirstError<typename F<bs>::error...>::type;
  using type = Int64List<F<bs>::value...>;
};

template <typename L, template <bool> class F>
struct TransformBoolListToTypeList;

template <bool... bs, template <bool> class F>
struct TransformBoolListToTypeList<BoolList<bs...>, F> {
  using error = typename GetFirstError<typename F<bs>::error...>::type;
  using type = List<typename F<bs>::type...>;
};

template <typename L, template <int64_t> class F>
struct TransformInt64ListToBoolList;

template <int64_t... ns, template <int64_t> class F>
struct TransformInt64ListToBoolList<Int64List<ns...>, F> {
  using error = typename GetFirstError<typename F<ns>::error...>::type;
  using type = BoolList<F<ns>::value...>;
};

template <typename L, template <int64_t> class F>
struct TransformInt64ListToInt64List;

template <int64_t... ns, template <int64_t> class F>
struct TransformInt64ListToInt64List<Int64List<ns...>, F> {
  using error = typename GetFirstError<typename F<ns>::error...>::type;
  using type = Int64List<F<ns>::value...>;
};

template <typename L, template <int64_t> class F>
struct TransformInt64ListToTypeList;

template <int64_t... ns, template <int64_t> class F>
struct TransformInt64ListToTypeList<Int64List<ns...>, F> {
  using error = typename GetFirstError<typename F<ns>::error...>::type;
  using type = List<typename F<ns>::type...>;
};

template <typename L, template <typename> class F>
struct TransformTypeListToBoolList;

template <typename... Ts, template <typename> class F>
struct TransformTypeListToBoolList<List<Ts...>, F> {
  using error = typename GetFirstError<typename F<Ts>::error...>::type;
  using type = BoolList<F<Ts>::value...>;
};

template <typename L, template <typename> class F>
struct TransformTypeListToInt64List;

template <typename... Ts, template <typename> class F>
struct TransformTypeListToInt64List<List<Ts...>, F> {
  using error = typename GetFirstError<typename F<Ts>::error...>::type;
  using type = Int64List<F<Ts>::value...>;
};

template <typename L, template <typename> class F>
struct TransformTypeListToTypeList;

template <typename... Ts, template <typename> class F>
struct TransformTypeListToTypeList<List<Ts...>, F> {
  using error = typename GetFirstError<typename F<Ts>::error...>::type;
  using type = List<typename F<Ts>::type...>;
};

template <typename AllFalseListIfNotPresent, typename AllFalseList, typename S, bool b>
struct AddToBoolSetHelper {
  using type = S;
};

template <typename AllFalseList, bool... bs, bool b>
struct AddToBoolSetHelper<AllFalseList, AllFalseList, BoolList<bs...>, b> {
  using type = BoolList<bs..., b>;
};

template <typename S, bool b>
struct AddToBoolSet;

template <bool... bs, bool b>
struct AddToBoolSet<BoolList<bs...>, b> {
  using type = typename AddToBoolSetHelper<BoolList<(bs == b)...>,
                                           BoolList<(bs && false)...>,
                                           BoolList<bs...>,
                                           b>::type;
};

template <typename AllFalseListIfNotPresent, typename AllFalseList, typename S, int64_t n>
struct AddToInt64SetHelper {
  using type = S;
};

template <typename AllFalseList, int64_t... ns, int64_t n>
struct AddToInt64SetHelper<AllFalseList, AllFalseList, Int64List<ns...>, n> {
  using type = Int64List<ns..., n>;
};

template <typename S, int64_t n>
struct AddToInt64Set;

template <int64_t... ns, int64_t n>
struct AddToInt64Set<Int64List<ns...>, n> {
  using type = typename AddToInt64SetHelper<BoolList<(ns == n)...>,
                                            BoolList<(ns && false)...>,
                                            Int64List<ns...>,
                                            n>::type;
};

template <typename AllFalseListIfNotPresent, typename AllFalseList, typename S, typename T>
struct AddToTypeSetHelper {
  using type = S;
};

template <typename AllFalseList, typename... Ts, typename T>
struct AddToTypeSetHelper<AllFalseList, AllFalseList, List<Ts...>, T> {
  using type = List<Ts..., T>;
};

template <typename S, typename T>
struct AddToTypeSet;

template <typename... Ts, typename T>
struct AddToTypeSet<List<Ts...>, T> {
  using type = typename AddToTypeSetHelper<BoolList<std::is_same<Ts, T>::value...>,
                                           BoolList<AlwaysFalseFromType<Ts>::value...>,
                                           List<Ts...>,
                                           T>::type;
};

template <typename S, bool b>
struct IsInBoolSet;

template <bool... bs, bool b>
struct IsInBoolSet<BoolList<bs...>, b> {
  static constexpr bool value = !std::is_same<BoolList<(bs == b)...>,
                                              BoolList<(bs && false)...>
                                              >::value;
};

template <typename S1, typename S2>
struct BoolSetEquals;

template <bool... bs1, bool... bs2>
struct BoolSetEquals<BoolList<bs1...>, BoolList<bs2...>> {
  static constexpr bool value =
      std::is_same<BoolList<IsInBoolSet<BoolList<bs1...>, bs2>::value...,
                            IsInBoolSet<BoolList<bs2...>, bs1>::value...>,
                   BoolList<(bs2 || true)...,
                            (bs1 || true)...>
                   >::value;
};

template <typename S, int64_t n>
struct IsInInt64Set;

template <int64_t... ns, int64_t n>
struct IsInInt64Set<Int64List<ns...>, n> {
  static constexpr bool value = !std::is_same<BoolList<(ns == n)...>,
                                              BoolList<(ns && false)...>
                                              >::value;
};

template <typename S1, typename S2>
struct Int64SetEquals;

template <int64_t... ns1, int64_t... ns2>
struct Int64SetEquals<Int64List<ns1...>, Int64List<ns2...>> {
  static constexpr bool value =
      std::is_same<BoolList<IsInInt64Set<Int64List<ns1...>, ns2>::value...,
                            IsInInt64Set<Int64List<ns2...>, ns1>::value...>,
                   BoolList<(ns2 || true)...,
                            (ns1 || true)...>
                   >::value;
};

template <typename S, typename T>
struct IsInTypeSet;

template <typename... Ts, typename T>
struct IsInTypeSet<List<Ts...>, T> {
  static constexpr bool value = !std::is_same<BoolList<std::is_same<Ts, T>::value...>,
                                              BoolList<AlwaysFalseFromType<Ts>::value...>
                                              >::value;
};

template <typename S1, typename S2>
struct TypeSetEquals;

template <typename... Ts, typename... Us>
struct TypeSetEquals<List<Ts...>, List<Us...>> {
  static constexpr bool value =
      std::is_same<BoolList<IsInTypeSet<List<Ts...>, Us>::value...,
                            IsInTypeSet<List<Us...>, Ts>::value...>,
                   BoolList<AlwaysTrueFromType<Us>::value...,
                            AlwaysTrueFromType<Ts>::value...>
                   >::value;
};

template <typename Acc, template <typename Acc1, bool b1> class F, bool... bs>
struct FoldBoolsToType {
  using type = Acc;
};

template <typename Acc, template <typename Acc1, bool b1> class F, bool b, bool... bs>
struct FoldBoolsToType<Acc, F, b, bs...> {
  using type = typename FoldBoolsToType<typename F<Acc, b>::type,
                                        F,
                                        bs...>::type;
};

template <typename L>
struct BoolListToSet;

template <bool... bs>
struct BoolListToSet<BoolList<bs...>> {
  using type = typename FoldBoolsToType<BoolList<>, AddToBoolSet, bs...>::type;
};

template <typename Acc, template <typename Acc1, int64_t n1> class F, int64_t... ns>
struct FoldInt64sToType {
  using type = Acc;
};

template <typename Acc, template <typename Acc1, int64_t n1> class F, int64_t n, int64_t... ns>
struct FoldInt64sToType<Acc, F, n, ns...> {
  using type = typename FoldInt64sToType<typename F<Acc, n>::type,
                                         F,
                                         ns...>::type;
};

template <typename L>
struct Int64ListToSet;

template <int64_t... ns>
struct Int64ListToSet<Int64List<ns...>> {
  using type = typename FoldInt64sToType<Int64List<>, AddToInt64Set, ns...>::type;
};

template <typename Acc, template <typename Acc1, typename T1> class F, typename... Ts>
struct FoldTypesToType {
  using type = Acc;
};

template <typename Acc, template <typename Acc1, typename T1> class F, typename T, typename... Ts>
struct FoldTypesToType<Acc, F, T, Ts...> {
  using type = typename FoldTypesToType<typename F<Acc, T>::type,
                                         F,
                                         Ts...>::type;
};

template <typename L>
struct TypeListToSet;

template <typename... Ts>
struct TypeListToSet<List<Ts...>> {
  using type = typename FoldTypesToType<List<>, AddToTypeSet, Ts...>::type;
};


#endif // TMPPY_H
