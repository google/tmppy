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
def test_if_else_success():
    from tmppy import Type
    def f(x: bool):
        if x:
            return Type('int')
        else:
            return Type('float')
    assert f(True) == Type('int')

@assert_compilation_succeeds()
def test_if_else_defining_local_var_success():
    from tmppy import Type
    def f(x: bool):
        if x:
            y = x
            return Type('int')
        else:
            return Type('float')
    assert f(True) == Type('int')

@assert_compilation_succeeds()
def test_if_else_only_if_returns_success():
    from tmppy import Type
    def f(x: bool):
        if x:
            return Type('int')
        else:
            y = Type('float')
        return y
    assert f(True) == Type('int')

@assert_compilation_succeeds()
def test_if_else_only_else_returns_success():
    from tmppy import Type
    def f(x: bool):
        if x:
            y = Type('int')
        else:
            return Type('float')
        return y
    assert f(True) == Type('int')

@assert_compilation_succeeds()
def test_if_returns_success():
    from tmppy import Type
    def f(x: bool):
        if x:
            return Type('int')
        return Type('float')
    assert f(True) == Type('int')

@assert_compilation_succeeds()
def test_if_else_neither_returns_success():
    from tmppy import Type
    def f(x: bool):
        if x:
            y = Type('int')
        else:
            y = Type('float')
        return y
    assert f(True) == Type('int')

@assert_compilation_succeeds()
def test_if_else_assert_in_if_branch_never_taken_ok():
    def f(x: bool):
        if False:
            b = False
            assert b
        return True
    assert f(True) == True

@assert_compilation_succeeds()
def test_if_else_assert_in_else_branch_never_taken_ok():
    def f(x: bool):
        if True:
            b = True
            assert b
        else:
            b = False
            assert b
        return True
    assert f(True) == True

@assert_compilation_succeeds()
def test_if_else_assert_in_continuation_never_executed_ok():
    from tmppy import Type
    def f(x: bool):
        if True:
            return Type('int')
        b = False
        assert b
        return Type('void')
    assert f(True) == Type('int')

@assert_compilation_succeeds()
def test_if_else_with_comparisons_success():
    from tmppy import Type
    def f(x: Type):
        if x == Type('int'):
            b = x == Type('int')
        else:
            return x == Type('float')
        return b == True
    assert f(Type('int')) == True

@assert_compilation_succeeds()
def test_if_else_variable_forwarded_to_if_branch_success():
    def f(x: bool):
        if x:
            return x
        else:
            return False
    assert f(True) == True

@assert_compilation_succeeds()
def test_if_else_variable_forwarded_to_else_branch_success():
    def f(x: bool):
        if x:
            return False
        else:
            return x
    assert f(False) == False

@assert_compilation_succeeds()
def test_if_else_variable_forwarded_to_continuation_success():
    def f(x: bool):
        if False:
            return False
        return x
    assert f(True) == True

@assert_compilation_succeeds()
def test_if_else_variable_forwarded_to_both_branches_success():
    def f(x: bool):
        if x:
            return x
        else:
            return x
    assert f(True) == True

@assert_conversion_fails
def test_if_else_condition_not_bool_error():
    from tmppy import Type
    def f(x: Type):
        if x:  # error: The condition in an if statement must have type bool, but was: Type
            return Type('int')
        else:
            return Type('float')

@assert_conversion_fails
def test_if_else_defining_same_var_with_different_types():
    from tmppy import Type
    def f(x: Type):
        if True:
            y = Type('int')  # note: A previous definition with type Type was here.
        else:
            y = True  # error: The variable y is defined with type bool here, but it was previously defined with type Type in another branch.
        return True

@assert_conversion_fails
def test_if_else_returning_different_types_error():
    from tmppy import Type
    def f(x: Type):
        if True:
            return Type('int')  # note: A previous return statement returning a Type was here.
        else:
            return True  # error: Found return statement with different return type: bool instead of Type.

@assert_compilation_succeeds()
def test_if_else_if_branch_defining_additional_var_success():
    from tmppy import Type
    def f(x: bool):
        if x:
            y = Type('int')
            b = True
        else:
            y = Type('float')
        return y
    assert f(True) == Type('int')

@assert_compilation_succeeds()
def test_if_else_else_branch_defining_additional_var_success():
    from tmppy import Type
    def f(x: bool):
        if x:
            y = Type('int')
        else:
            y = Type('float')
            b = True
        return y
    assert f(True) == Type('int')

@assert_conversion_fails
def test_if_else_defining_different_vars_possibly_undefined_var_used_in_continuation_error():
    from tmppy import Type
    def f(x: bool):
        if x:
            y = Type('int')
        else:
            y = Type('float')
            b = True  # note: b might have been initialized here
        return b  # error: Reference to a variable that may or may not have been initialized \(depending on which branch was taken\)

@assert_conversion_fails
def test_if_else_defining_different_vars_definitely_undefined_var_from_if_branch_used_in_continuation_error():
    '''
    from tmppy import Type
    def f(x: bool):
        if x:
            y = Type('int')
            b = True
            return True
        else:
            y = Type('float')
        return b  # error: Reference to undefined variable/function
    '''

@assert_conversion_fails
def test_if_else_defining_different_vars_definitely_undefined_var_from_else_branch_used_in_continuation_error():
    '''
    from tmppy import Type
    def f(x: bool):
        if x:
            y = Type('int')
        else:
            y = Type('float')
            b = True
            return True
        return b  # error: Reference to undefined variable/function
    '''

@assert_conversion_fails
def test_if_else_if_branch_does_not_return_error():
    from tmppy import Type
    def f(x: bool):
        if x:
            y = Type('int') # error: Missing return statement.
        else:
            return True

@assert_conversion_fails
def test_if_else_else_branch_does_not_return_error():
    from tmppy import Type
    def f(x: bool):
        if x:
            return True
        else:
            y = Type('int') # error: Missing return statement.

@assert_conversion_fails
def test_if_else_missing_else_branch_no_return_after_error():
    def f(x: bool):
        if x:  # error: Missing return statement. You should add an else branch that returns, or a return after the if.
            return True

@assert_compilation_succeeds()
def test_if_else_sequential_success():
    from tmppy import Type
    def f(x: bool):
        if x:
            return False
        else:
            y = Type('int')
        if y == Type('float'):
            return False
        else:
            return True
    assert f(False) == True

@assert_conversion_fails
def test_if_else_sequential_reassigned_var_if_if_error():
    from tmppy import Type
    def f(x: bool, y: bool):
        if x:
            z = Type('int')  # note: It might have been initialized here \(depending on which branch is taken\).
        else:
            p1 = True
        if y:
            z = Type('int')  # error: z could be already initialized at this point.
        else:
            p2 = True
        return True

@assert_conversion_fails
def test_if_else_sequential_reassigned_var_if_without_else_if_error():
    from tmppy import Type
    def f(x: bool, y: bool):
        if x:
            z = Type('int')  # note: It might have been initialized here \(depending on which branch is taken\).
        if y:
            z = Type('int')  # error: z could be already initialized at this point.
        else:
            p1 = True
        return True

@assert_conversion_fails
def test_if_else_sequential_reassigned_var_if_else_error():
    from tmppy import Type
    def f(x: bool, y: bool):
        if x:
            z = Type('int')  # note: It might have been initialized here \(depending on which branch is taken\).
        else:
            p1 = True
        if y:
            p2 = True
        else:
            z = Type('int')  # error: z could be already initialized at this point.
        return True

@assert_conversion_fails
def test_if_else_sequential_reassigned_var_if_without_else_else_error():
    from tmppy import Type
    def f(x: bool, y: bool):
        if x:
            z = Type('int')  # note: It might have been initialized here \(depending on which branch is taken\).
        if y:
            p1 = True
        else:
            z = Type('int')  # error: z could be already initialized at this point.
        return True

@assert_conversion_fails
def test_if_else_sequential_reassigned_var_else_if_error():
    from tmppy import Type
    def f(x: bool, y: bool):
        if x:
            p1 = True
        else:
            z = Type('int')  # note: It might have been initialized here \(depending on which branch is taken\).
        if y:
            z = Type('int')  # error: z could be already initialized at this point.
        else:
            p2 = True
        return True

@assert_conversion_fails
def test_if_else_sequential_reassigned_var_else_if_without_else_error():
    from tmppy import Type
    def f(x: bool, y: bool):
        if x:
            p1 = True
        else:
            z = Type('int')  # note: It might have been initialized here \(depending on which branch is taken\).
        if y:
            z = Type('int')  # error: z could be already initialized at this point.
        return True

@assert_conversion_fails
def test_if_else_sequential_reassigned_var_else_else_error():
    from tmppy import Type
    def f(x: bool, y: bool):
        if x:
            p1 = True
        else:
            z = Type('int')  # note: It might have been initialized here \(depending on which branch is taken\).
        if y:
            p2 = True
        else:
            z = Type('int')  # error: z could be already initialized at this point.
        return True

@assert_compilation_succeeds()
def test_two_nested_ifs_with_else():
    def g(b1: bool, b2: bool):
        if b1:
            if b2:
                return 1
            else:
                return 2
        else:
            if b2:
                return 3
            else:
                return 4
    assert g(True, True) == 1
    assert g(True, False) == 2
    assert g(False, True) == 3
    assert g(False, False) == 4

@assert_compilation_succeeds()
def test_two_nested_ifs_without_else():
    def g(b1: bool, b2: bool):
        if b1:
            if b2:
                return 1
            return 2
        return 3
    assert g(True, True) == 1
    assert g(True, False) == 2
    assert g(False, True) == 3
    assert g(False, False) == 3

@assert_compilation_succeeds()
def test_two_nested_ifs_outer_without_else():
    def g(b1: bool, b2: bool):
        if b1:
            if b2:
                return 1
            else:
                return 2
        return 3
    assert g(True, True) == 1
    assert g(True, False) == 2
    assert g(False, True) == 3
    assert g(False, False) == 3

@assert_compilation_succeeds()
def test_two_nested_ifs_inner_without_else():
    def g(b1: bool, b2: bool):
        if b1:
            if b2:
                return 1
            return 2
        else:
            if b2:
                return 3
            return 4
    assert g(True, True) == 1
    assert g(True, False) == 2
    assert g(False, True) == 3
    assert g(False, False) == 4

@assert_compilation_succeeds()
def test_three_nested_ifs_without_else():
    def g(b1: bool, b2: bool, b3: bool):
        if b1:
            if b2:
                if b3:
                    return 1
                return 2
            return 3
        return 4
    assert g(True, True, True) == 1
    assert g(True, True, False) == 2
    assert g(True, False, True) == 3
    assert g(True, False, False) == 3
    assert g(False, True, True) == 4
    assert g(False, True, False) == 4
    assert g(False, False, True) == 4
    assert g(False, False, False) == 4

@assert_compilation_succeeds()
def test_three_nested_ifs_outer_without_else():
    def g(b1: bool, b2: bool, b3: bool):
        if b1:
            if b2:
                if b3:
                    return 1
                else:
                    return 2
            else:
                if b3:
                    return 3
                else:
                    return 4
        return 5
    assert g(True, True, True) == 1
    assert g(True, True, False) == 2
    assert g(True, False, True) == 3
    assert g(True, False, False) == 4
    assert g(False, True, True) == 5
    assert g(False, True, False) == 5
    assert g(False, False, True) == 5
    assert g(False, False, False) == 5

@assert_compilation_succeeds()
def test_three_nested_ifs_middle_without_else():
    def g(b1: bool, b2: bool, b3: bool):
        if b1:
            if b2:
                if b3:
                    return 1
                else:
                    return 2
            return 3
        else:
            if b2:
                if b3:
                    return 4
                else:
                    return 5
            return 6
    assert g(True, True, True) == 1
    assert g(True, True, False) == 2
    assert g(True, False, True) == 3
    assert g(True, False, False) == 3
    assert g(False, True, True) == 4
    assert g(False, True, False) == 5
    assert g(False, False, True) == 6
    assert g(False, False, False) == 6

@assert_compilation_succeeds()
def test_three_nested_ifs_inner_without_else():
    def g(b1: bool, b2: bool, b3: bool):
        if b1:
            if b2:
                if b3:
                    return 1
                return 2
            else:
                if b3:
                    return 3
                return 4
        else:
            if b2:
                if b3:
                    return 5
                return 6
            else:
                if b3:
                    return 7
                return 8
    assert g(True, True, True) == 1
    assert g(True, True, False) == 2
    assert g(True, False, True) == 3
    assert g(True, False, False) == 4
    assert g(False, True, True) == 5
    assert g(False, True, False) == 6
    assert g(False, False, True) == 7
    assert g(False, False, False) == 8

@assert_compilation_succeeds()
def test_three_nested_ifs_inner_and_middle_without_else():
    def g(b1: bool, b2: bool, b3: bool):
        if b1:
            if b2:
                if b3:
                    return 1
                return 2
            return 3
        else:
            if b2:
                if b3:
                    return 4
                return 5
            return 6
    assert g(True, True, True) == 1
    assert g(True, True, False) == 2
    assert g(True, False, True) == 3
    assert g(True, False, False) == 3
    assert g(False, True, True) == 4
    assert g(False, True, False) == 5
    assert g(False, False, True) == 6
    assert g(False, False, False) == 6

@assert_compilation_succeeds()
def test_three_nested_ifs_outer_and_middle_without_else():
    def g(b1: bool, b2: bool, b3: bool):
        if b1:
            if b2:
                if b3:
                    return 1
                else:
                    return 2
            return 3
        return 4
    assert g(True, True, True) == 1
    assert g(True, True, False) == 2
    assert g(True, False, True) == 3
    assert g(True, False, False) == 3
    assert g(False, True, True) == 4
    assert g(False, True, False) == 4
    assert g(False, False, True) == 4
    assert g(False, False, False) == 4

@assert_compilation_succeeds()
def test_three_nested_ifs_outer_and_inner_without_else():
    def g(b1: bool, b2: bool, b3: bool):
        if b1:
            if b2:
                if b3:
                    return 1
                return 2
            else:
                if b3:
                    return 3
                return 4
        return 5
    assert g(True, True, True) == 1
    assert g(True, True, False) == 2
    assert g(True, False, True) == 3
    assert g(True, False, False) == 4
    assert g(False, True, True) == 5
    assert g(False, True, False) == 5
    assert g(False, False, True) == 5
    assert g(False, False, False) == 5

@assert_compilation_succeeds()
def test_three_nested_if_else():
    def g(b1: bool, b2: bool, b3: bool):
        if b1:
            if b2:
                if b3:
                    return 1
                else:
                    return 2
            else:
                if b3:
                    return 3
                else:
                    return 4
        else:
            if b2:
                if b3:
                    return 5
                else:
                    return 6
            else:
                if b3:
                    return 7
                else:
                    return 8
    assert g(True, True, True) == 1
    assert g(True, True, False) == 2
    assert g(True, False, True) == 3
    assert g(True, False, False) == 4
    assert g(False, True, True) == 5
    assert g(False, True, False) == 6
    assert g(False, False, True) == 7
    assert g(False, False, False) == 8

if __name__== '__main__':
    main()
