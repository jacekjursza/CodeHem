import pytest
from core.finder import get_code_finder

@pytest.fixture
def typescript_finder():
    return get_code_finder('typescript')

def test_find_interface_simple(typescript_finder):
    code = '''
interface Person {
  name: string;
  age?: number;
}
'''
    (start_line, end_line) = typescript_finder.find_interface(code, 'Person')
    assert start_line == 2, f'Expected interface start at line 2, got {start_line}'
    assert end_line == 4, f'Expected interface end at line 4, got {end_line}'

def test_find_interface_with_extends(typescript_finder):
    code = '''
interface Employee extends Person {
  employeeId: number;
  department: string;
}
'''
    (start_line, end_line) = typescript_finder.find_interface(code, 'Employee')
    assert start_line == 2, f'Expected interface start at line 2, got {start_line}'
    assert end_line == 5, f'Expected interface end at line 5, got {end_line}'

def test_find_interface_missing(typescript_finder):
    code = '''
interface ExistingInterface {
  prop: string;
}
'''
    (start_line, end_line) = typescript_finder.find_interface(code, 'NonExistentInterface')
    assert start_line == 0 and end_line == 0, 'Expected no lines for a non-existent interface'

def test_find_type_alias_simple(typescript_finder):
    code = '''
type ID = string;
type User = {
  id: ID;
  name: string;
};
'''
    (start_line, end_line) = typescript_finder.find_type_alias(code, 'User')
    assert start_line == 3, f'Expected type alias start at line 3, got {start_line}'
    assert end_line == 6, f'Expected type alias end at line 6, got {end_line}'

def test_find_type_alias_union(typescript_finder):
    code = '''
type Status = 'pending' | 'active' | 'completed';
'''
    (start_line, end_line) = typescript_finder.find_type_alias(code, 'Status')
    assert start_line == 2, f'Expected type alias start at line 2, got {start_line}'
    assert end_line == 2, f'Expected type alias end at line 2, got {end_line}'

def test_find_type_alias_missing(typescript_finder):
    code = '''
type ExistingType = string;
'''
    (start_line, end_line) = typescript_finder.find_type_alias(code, 'NonExistentType')
    assert start_line == 0 and end_line == 0, 'Expected no lines for a non-existent type alias'