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
def test_attribute_access_success():
    from tmppy import Type
    assert Type.template_instantiation('std::remove_pointer', [Type.pointer(Type('int'))]).type == Type('int')

@assert_compilation_succeeds()
def test_attribute_access_on_function_result_expr_success():
    from tmppy import Type
    def f(x: Type):
        return x
    assert f(Type.template_instantiation('std::remove_pointer', [Type.pointer(Type('int'))])).type == Type('int')

@assert_compilation_succeeds()
def test_attribute_access_on_local_var_success():
    from tmppy import Type
    def f(x: bool):
        y = Type.template_instantiation('std::remove_pointer', [Type.pointer(Type('int'))])
        assert y.type == Type('int')
        return True
    assert f(True)

@assert_conversion_fails
def test_attribute_access_on_bool_error():
    from tmppy import Type
    assert True.type == Type('int')  # error: Attribute access is not supported for values of type bool.

@assert_conversion_fails
def test_attribute_access_on_int_error():
    from tmppy import Type
    def f(b: bool):
        x = 15
        assert x.type == Type('int')  # error: Attribute access is not supported for values of type int.

@assert_conversion_fails
def test_attribute_access_on_list_error():
    from tmppy import Type
    assert [Type('int')].type == Type('int')  # error: Attribute access is not supported for values of type List\[Type\].

@assert_conversion_fails
def test_attribute_access_on_set_error():
    from tmppy import Type
    assert {Type('int')}.type == Type('int')  # error: Attribute access is not supported for values of type Set\[Type\].

@assert_conversion_fails
def test_attribute_access_on_function_error():
    from tmppy import Type
    def f(x: Type):
        return x
    assert f.type == Type('int')  # error: Attribute access is not supported for values of type \(Type\) -> Type.

if __name__== '__main__':
    main()
