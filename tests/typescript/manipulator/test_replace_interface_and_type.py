import pytest
from core.manipulator import get_code_manipulator

@pytest.fixture
def typescript_manipulator():
    return get_code_manipulator('typescript')

def test_replace_interface_simple(typescript_manipulator):
    original_code = '''
interface Person {
  name: string;
  age: number;
}
'''
    new_interface = '''
interface Person {
  name: string;
  age: number;
  email: string;
}
'''
    expected = '''
interface Person {
  name: string;
  age: number;
  email: string;
}
'''
    result = typescript_manipulator.replace_interface(original_code, 'Person', new_interface)
    assert result.strip() == expected.strip()

def test_replace_interface_missing(typescript_manipulator):
    original_code = '''
interface ExistingInterface {
  prop: string;
}
'''
    new_interface = '''
interface NonExistentInterface {
  prop: string;
}
'''
    result = typescript_manipulator.replace_interface(original_code, 'NonExistentInterface', new_interface)
    assert result.strip() == original_code.strip()

def test_replace_type_alias_simple(typescript_manipulator):
    original_code = '''
type User = {
  id: string;
  name: string;
};
'''
    new_type = '''
type User = {
  id: string;
  name: string;
  role: 'admin' | 'user';
};
'''
    expected = '''
type User = {
  id: string;
  name: string;
  role: 'admin' | 'user';
};
'''
    result = typescript_manipulator.replace_type_alias(original_code, 'User', new_type)
    assert result.strip() == expected.strip()

def test_replace_type_alias_missing(typescript_manipulator):
    original_code = '''
type ExistingType = string;
'''
    new_type = '''
type NonExistentType = number;
'''
    result = typescript_manipulator.replace_type_alias(original_code, 'NonExistentType', new_type)
    assert result.strip() == original_code.strip()