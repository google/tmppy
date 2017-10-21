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

template <long...>
struct Int64List;

template <bool...>
struct BoolList;

template <bool>
struct AlwaysTrueFromBool {
  static constexpr bool value = true;
};

template <long>
struct AlwaysTrueFromInt64 {
  static constexpr long value = true;
};

template <typename>
struct AlwaysTrueFromType {
  static constexpr bool value = true;
};

template <bool b, bool>
struct Select1stBoolBool {
  static constexpr bool value = b;
};

template <bool b, long>
struct Select1stBoolInt64 {
  static constexpr bool value = b;
};

template <bool b, typename>
struct Select1stBoolType {
  static constexpr bool value = b;
};

template <long n, bool>
struct Select1stInt64Bool {
  static constexpr long value = n;
};

template <long n, long>
struct Select1stInt64Int64 {
  static constexpr long value = n;
};

template <long n, typename>
struct Select1stInt64Type {
  static constexpr long value = n;
};

template <typename T, bool>
struct Select1stTypeBool {
  // We intentionally use `value` instead of `type`, for simplicity of the implementation.
  using value = T;
};

template <typename T, long>
struct Select1stTypeInt64 {
  // We intentionally use `value` instead of `type`, for simplicity of the implementation.
  using value = T;
};

template <typename T, typename>
struct Select1stTypeType {
  // We intentionally use `value` instead of `type`, for simplicity of the implementation.
  using value = T;
};

#endif // TMPPY_H
