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

from _py2tmp.compiler.testing import main, assert_compilation_succeeds, assert_conversion_fails

@assert_compilation_succeeds()
def test_type_literal_success():
    from tmppy import Type
    assert Type('int') == Type('int')

@assert_compilation_succeeds()
def test_type_pointer_literal_success():
    from tmppy import Type
    assert Type.pointer(Type('int')) == Type.pointer(Type('int'))

@assert_compilation_succeeds()
def test_type_reference_literal_success():
    from tmppy import Type
    assert Type.reference(Type('int')) == Type.reference(Type('int'))

@assert_compilation_succeeds(always_allow_toplevel_static_asserts_after_optimization=True)
def test_type_reference_literal_collapsed():
    from tmppy import Type
    assert Type.reference(Type('int')) == Type.reference(Type.reference(Type('int')))

@assert_compilation_succeeds()
def test_type_rvalue_reference_literal_success():
    from tmppy import Type
    assert Type.rvalue_reference(Type('int')) == Type.rvalue_reference(Type('int'))

@assert_compilation_succeeds(always_allow_toplevel_static_asserts_after_optimization=True)
def test_type_rvalue_reference_literal_different_from_two_references_success():
    from tmppy import Type
    assert Type.rvalue_reference(Type('int')) != Type.reference(Type.reference(Type('int')))

@assert_compilation_succeeds(always_allow_toplevel_static_asserts_after_optimization=True)
def test_type_rvalue_reference_literal_collapsed():
    from tmppy import Type
    assert Type.rvalue_reference(Type('int')) == Type.rvalue_reference(Type.rvalue_reference(Type('int')))

@assert_compilation_succeeds(always_allow_toplevel_static_asserts_after_optimization=True)
def test_type_rvalue_reference_literal_collapsed_with_reference():
    from tmppy import Type
    assert Type.reference(Type('int')) == Type.rvalue_reference(Type.reference(Type('int')))

@assert_compilation_succeeds(always_allow_toplevel_static_asserts_after_optimization=True)
def test_type_rvalue_reference_literal_collapsed_with_reference_reverse_order():
    from tmppy import Type
    assert Type.reference(Type('int')) == Type.rvalue_reference(Type.reference(Type('int')))

@assert_compilation_succeeds()
def test_const_type_literal_success():
    from tmppy import Type
    assert Type.const(Type('int')) == Type.const(Type('int'))

@assert_compilation_succeeds()
def test_type_array_literal_success():
    from tmppy import Type
    assert Type.array(Type('int')) == Type.array(Type('int'))

@assert_compilation_succeeds()
def test_type_function_literal_with_no_args_success():
    from tmppy import Type, empty_list
    assert Type.function(Type('int'), empty_list(Type)) == Type.function(Type('int'), empty_list(Type))

@assert_compilation_succeeds()
def test_type_function_pointer_literal_with_no_args_success():
    from tmppy import Type, empty_list
    assert Type.pointer(Type.function(Type('int'), empty_list(Type))) == Type.pointer(Type.function(Type('int'), empty_list(Type)))

@assert_compilation_succeeds()
def test_type_function_literal_success():
    from tmppy import Type
    assert Type.function(Type('int'), [Type('float'), Type('double')]) == Type.function(Type('int'), [Type('float'), Type('double')])

@assert_compilation_succeeds()
def test_type_function_pointer_literal_success():
    from tmppy import Type
    assert Type.pointer(Type.function(Type('int'), [Type('float'), Type('double')])) == Type.pointer(Type.function(Type('int'), [Type('float'), Type('double')]))

@assert_conversion_fails
def test_type_literal_no_arguments_error():
    from tmppy import Type
    def f(x: bool):
        return Type()  # error: Type\(\) takes 1 argument. Got: 0

@assert_conversion_fails
def test_type_literal_too_many_arguments_error():
    from tmppy import Type
    def f(x: bool):
        return Type('', '')  # error: Type\(\) takes 1 argument. Got: 2

@assert_conversion_fails
def test_type_literal_argument_with_wrong_type_error():
    from tmppy import Type
    def f(x: bool):
        return Type(x)  # error: The argument passed to Type should be a string constant.

@assert_conversion_fails
def test_type_literal_kwargs_arg_not_supported():
    from tmppy import Type
    def f(x: bool):
        y = 1
        return Type(**y)  # error: Keyword arguments are not supported in Type\(\)

@assert_conversion_fails
def test_type_literal_keyword_arg_error():
    from tmppy import Type
    def f(x: bool):
        return Type('T', T=Type('int'))  # error: Keyword arguments are not supported in Type\(\)

@assert_compilation_succeeds()
def test_template_instantiation_literal_success():
    from tmppy import Type
    assert Type.pointer(Type('int')) == Type.template_instantiation('std::add_pointer', [Type('int')]).type

@assert_compilation_succeeds(always_allow_toplevel_static_asserts_after_optimization=True, extra_cpp_prelude='''\
struct Holder {
  template <typename T, typename U>
  struct Inner {
    using type = U*;
  };
};
''')
def test_template_member_literal_success():
    from tmppy import Type
    assert Type.pointer(Type('float')) == Type.template_member(Type('Holder'), 'Inner', [Type('int'), Type('float')]).type

@assert_conversion_fails
def test_template_member_keyword_arg():
    from tmppy import Type
    def f(x: bool):
      return Type.template_member(
          type=Type('int'))  # error: Keyword arguments are not supported in Type.template_member\(\)

@assert_conversion_fails
def test_template_member_literal_no_args_error():
    from tmppy import Type
    def f(x: bool):
      return Type.template_member()  # error: Type.template_member\(\) takes 3 arguments. Got: 0

@assert_conversion_fails
def test_template_member_literal_one_arg_error():
    from tmppy import Type
    def f(x: bool):
      return Type.template_member(Type('int'))  # error: Type.template_member\(\) takes 3 arguments. Got: 1

@assert_conversion_fails
def test_template_member_literal_two_args_error():
    from tmppy import Type
    def f(x: bool):
      return Type.template_member(Type('int'), 'foo')  # error: Type.template_member\(\) takes 3 arguments. Got: 2

@assert_conversion_fails
def test_template_member_literal_four_args_error():
    from tmppy import Type
    def f(x: bool):
      return Type.template_member(Type('int'), 'foo', 'bar', 'baz')  # error: Type.template_member\(\) takes 3 arguments. Got: 4

@assert_conversion_fails
def test_template_member_literal_first_arg_incorrect_type():
    from tmppy import Type
    def f(x: bool):
      return Type.template_member(
          4,  # error: The first argument passed to Type.template_member should have type Type, but was: int
          'foo', [])

@assert_conversion_fails
def test_template_member_literal_second_arg_incorrect_kind():
    from tmppy import Type
    def f(x: bool):
      return Type.template_member(Type('int'),
                                  15,  # error: The second argument passed to Type.template_member should be a string
                                  [])

@assert_conversion_fails
def test_template_member_literal_second_arg_not_an_identifier():
    from tmppy import Type
    def f(x: bool):
      return Type.template_member(Type('int'),
                                  '1abc',  # error: The second argument passed to Type.template_member should be a valid C\+\+ identifier
                                  [])

@assert_conversion_fails
def test_template_member_literal_third_arg_incorrect_type():
    from tmppy import Type
    def f(x: bool):
      return Type.template_member(Type('int'), 'foo',
                                  15)  # error: The third argument passed to Type.template_member should have type List\[Type\], but was: int

@assert_compilation_succeeds(extra_cpp_prelude='''\
#include <string>
''')
def test_type_literal_qualified_ok():
  from tmppy import Type
  def f(x: bool):
    return Type('std::string')

@assert_conversion_fails
def test_type_literal_not_atomic_error():
  from tmppy import Type
  def f(x: bool):
    return Type('std::vector<bool>')  # error: Invalid atomic type. Atomic types should be C\+\+ identifiers \(possibly namespace-qualified\).

@assert_conversion_fails
def test_template_instantiation_literal_not_atomic_error():
  from tmppy import Type
  def f(x: bool):
    return Type.template_instantiation('std::dummy<int>::add_pointer', [Type('int')])  # error: Invalid atomic type. Atomic types should be C\+\+ identifiers \(possibly namespace-qualified\).

@assert_conversion_fails
def test_template_instantiation_literal_keyword_arg_error():
  from tmppy import Type
  def f(x: bool):
    return Type.template_instantiation(
        template_atomic_type='std::dummy<int>::add_pointer',  # error: Keyword arguments are not supported in Type.template_instantiation\(\)
        args=[Type('int')])

@assert_conversion_fails
def test_template_instantiation_literal_no_args_error():
  from tmppy import Type
  def f(x: bool):
    return Type.template_instantiation() # error: Type.template_instantiation\(\) takes 2 arguments. Got: 0

@assert_conversion_fails
def test_template_instantiation_literal_one_arg_error():
  from tmppy import Type
  def f(x: bool):
    return Type.template_instantiation('int') # error: Type.template_instantiation\(\) takes 2 arguments. Got: 1

@assert_conversion_fails
def test_template_instantiation_literal_three_arg_error():
  from tmppy import Type
  def f(x: bool):
    return Type.template_instantiation('F<X, Y>', Type('int'), Type('float')) # error: Type.template_instantiation\(\) takes 2 arguments. Got: 3

@assert_conversion_fails
def test_template_instantiation_literal_incorrect_first_arg_type():
  from tmppy import Type
  def f(x: bool):
    return Type.template_instantiation(
        1,  # error: The first argument passed to Type.template_instantiation should be a string
        [Type('int')])

@assert_conversion_fails
def test_template_instantiation_literal_incorrect_second_arg_type():
  from tmppy import Type
  def f(x: bool):
    return Type.template_instantiation(
        'std::vector',
        Type('int'))  # error: The second argument passed to Type.template_instantiation should have type List\[Type\], but was: Type

@assert_conversion_fails
def test_type_pointer_literal_with_keyword_argument():
    from tmppy import Type
    def f(x: bool):
        return Type.pointer(x=1)  # error: Keyword arguments are not supported in Type.pointer\(\)

@assert_conversion_fails
def test_type_pointer_literal_with_multiple_args():
    from tmppy import Type
    def f(x: bool):
        return Type.pointer('x', 'y')  # error: Type.pointer\(\) takes 1 argument. Got: 2

@assert_conversion_fails
def test_type_pointer_literal_with_arg_of_incorrect_type():
    from tmppy import Type
    def f(x: bool):
        return Type.pointer(5)  # error: The argument passed to Type.pointer\(\) should have type Type, but was: int

@assert_conversion_fails
def test_type_reference_literal_with_keyword_argument():
    from tmppy import Type
    def f(x: bool):
        return Type.reference(x=1)  # error: Keyword arguments are not supported in Type.reference\(\)

@assert_conversion_fails
def test_type_reference_literal_with_multiple_args():
    from tmppy import Type
    def f(x: bool):
        return Type.reference('x', 'y')  # error: Type.reference\(\) takes 1 argument. Got: 2

@assert_conversion_fails
def test_type_reference_literal_with_arg_of_incorrect_type():
    from tmppy import Type
    def f(x: bool):
        return Type.reference(5)  # error: The argument passed to Type.reference\(\) should have type Type, but was: int

@assert_conversion_fails
def test_type_rvalue_reference_literal_with_keyword_argument():
    from tmppy import Type
    def f(x: bool):
        return Type.rvalue_reference(x=1)  # error: Keyword arguments are not supported in Type.rvalue_reference\(\)

@assert_conversion_fails
def test_type_rvalue_reference_literal_with_multiple_args():
    from tmppy import Type
    def f(x: bool):
        return Type.rvalue_reference('x', 'y')  # error: Type.rvalue_reference\(\) takes 1 argument. Got: 2

@assert_conversion_fails
def test_type_rvalue_reference_literal_with_arg_of_incorrect_type():
    from tmppy import Type
    def f(x: bool):
        return Type.rvalue_reference(5)  # error: The argument passed to Type.rvalue_reference\(\) should have type Type, but was: int

@assert_conversion_fails
def test_type_const_literal_with_keyword_argument():
    from tmppy import Type
    def f(x: bool):
        return Type.const(x=1)  # error: Keyword arguments are not supported in Type.const\(\)

@assert_conversion_fails
def test_type_const_literal_with_multiple_args():
    from tmppy import Type
    def f(x: bool):
        return Type.const('x', 'y')  # error: Type.const\(\) takes 1 argument. Got: 2

@assert_conversion_fails
def test_type_const_literal_with_arg_of_incorrect_type():
    from tmppy import Type
    def f(x: bool):
        return Type.const(5)  # error: The argument passed to Type.const\(\) should have type Type, but was: int

@assert_conversion_fails
def test_type_array_literal_with_keyword_argument():
    from tmppy import Type
    def f(x: bool):
        return Type.array(x=1)  # error: Keyword arguments are not supported in Type.array\(\)

@assert_conversion_fails
def test_type_array_literal_with_multiple_args():
    from tmppy import Type
    def f(x: bool):
        return Type.array('x', 'y')  # error: Type.array\(\) takes 1 argument. Got: 2

@assert_conversion_fails
def test_type_array_literal_with_arg_of_incorrect_type():
    from tmppy import Type
    def f(x: bool):
        return Type.array(5)  # error: The argument passed to Type.array\(\) should have type Type, but was: int

@assert_conversion_fails
def test_type_function_literal_with_too_few_args():
    from tmppy import Type
    def f(x: bool):
        return Type.function('int')  # error: Type.function\(\) takes 2 arguments. Got: 1

@assert_conversion_fails
def test_type_function_literal_with_too_many_args():
    from tmppy import Type
    def f(x: bool):
        return Type.function('int', 'float', 'char')  # error: Type.function\(\) takes 2 arguments. Got: 3

@assert_conversion_fails
def test_type_function_literal_with_keyword_argument():
    from tmppy import Type
    def f(x: bool):
        return Type.function(x=1)  # error: Keyword arguments are not supported in Type.function\(\)

@assert_conversion_fails
def test_type_function_literal_incorrect_first_arg_type():
    from tmppy import Type
    def f(x: bool):
        return Type.function(1, [])  # error: The first argument passed to Type.function should have type Type, but was: int

@assert_conversion_fails
def test_type_function_literal_incorrect_second_arg_type():
    from tmppy import Type
    def f(x: bool):
        return Type.function(Type('double'), Type('int'))  # error: The second argument passed to Type.function should have type List\[Type\], but was: Type

@assert_conversion_fails
def test_type_undefined_static_method():
    from tmppy import Type
    def f(x: bool):
        return Type.i_do_not_exist()  # error: Undefined Type factory method

if __name__== '__main__':
    main()
