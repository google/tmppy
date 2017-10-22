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


#endif // TMPPY_H
