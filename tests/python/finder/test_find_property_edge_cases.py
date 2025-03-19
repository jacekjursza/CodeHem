import pytest

from core.finder.factory import get_code_finder


@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_property_setter_before_getter(python_finder):
    """Test finding a property when the setter is defined before the getter."""
    code = '''
class MyClass:
    @my_value.setter
    def my_value(self, value):
        self._value = value
        
    @property
    def my_value(self):
        return self._value
'''
    (start_line, end_line) = python_finder.find_property(code, 'MyClass', 'my_value')
    assert start_line == 7, f'Expected property start at line 7, got {start_line}'
    assert end_line == 9, f'Expected property end at line 9, got {end_line}'

def test_find_property_among_other_decorators(python_finder):
        """Test finding a property that has multiple decorators."""
        code = '''
    class MyClass:
        @staticmethod
        def static_method():
            pass

        @classmethod
        def class_method(cls):
            pass

        @custom_decorator
        @property
        def my_value(self):
            return self._value
    '''
        (start_line, end_line) = python_finder.find_property(code, 'MyClass', 'my_value')
        assert start_line == 11, f'Expected property start at line 11, got {start_line}'
        assert end_line == 14, f'Expected property end at line 14, got {end_line}'
