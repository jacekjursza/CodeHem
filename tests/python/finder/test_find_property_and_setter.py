import pytest
from finder.factory import get_code_finder

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_property_and_setter_together(python_finder):
    """Test finding both property getter and setter when they're adjacent."""
    code = '''
class MyClass:
    @property
    def my_value(self):
        return self._value
        
    @my_value.setter
    def my_value(self, value):
        self._value = value
'''
    (start_line, end_line) = python_finder.find_property_and_setter(code, 'MyClass', 'my_value')
    assert start_line == 3, f'Expected combined start at line 3, got {start_line}'
    assert end_line == 9, f'Expected combined end at line 9, got {end_line}'

def test_find_property_and_setter_separated(python_finder):
    """Test finding both property getter and setter when they're not adjacent."""
    code = '''
class MyClass:
    @property
    def my_value(self):
        return self._value
        
    def other_method(self):
        pass
        
    @my_value.setter
    def my_value(self, value):
        self._value = value
'''
    (start_line, end_line) = python_finder.find_property_and_setter(code, 'MyClass', 'my_value')
    assert start_line == 3, f'Expected combined start at line 3, got {start_line}'
    assert end_line == 12, f'Expected combined end at line 12, got {end_line}'

def test_find_property_and_setter_only_getter(python_finder):
    """Test finding property and setter when only the getter exists."""
    code = '''
class MyClass:
    @property
    def my_value(self):
        return self._value
'''
    (start_line, end_line) = python_finder.find_property_and_setter(code, 'MyClass', 'my_value')
    assert start_line == 3, f'Expected getter start at line 3, got {start_line}'
    assert end_line == 5, f'Expected getter end at line 5, got {end_line}'

def test_find_property_and_setter_only_setter(python_finder):
    """Test finding property and setter when only the setter exists."""
    code = '''
class MyClass:
    @my_value.setter
    def my_value(self, value):
        self._value = value
'''
    (start_line, end_line) = python_finder.find_property_and_setter(code, 'MyClass', 'my_value')
    assert start_line == 3, f'Expected setter start at line 3, got {start_line}'
    assert end_line == 5, f'Expected setter end at line 5, got {end_line}'

def test_find_property_and_setter_missing(python_finder):
    """Test finding property and setter when neither exists."""
    code = '''
class MyClass:
    def other_method(self):
        pass
'''
    (start_line, end_line) = python_finder.find_property_and_setter(code, 'MyClass', 'my_value')
    assert start_line == 0 and end_line == 0, 'Expected no lines when property does not exist'