import pytest

from core.finder.factory import get_code_finder


@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_get_function_decorators(python_finder):
    code = '''
@decorator1
@decorator2
def my_function():
    return "Hello"
'''
    decorators = python_finder.get_decorators(code, 'my_function')
    assert len(decorators) == 2, f'Expected 2 decorators, got {len(decorators)}'
    assert '@decorator1' in decorators, 'Expected @decorator1 in decorators'
    assert '@decorator2' in decorators, 'Expected @decorator2 in decorators'

def test_get_method_decorators(python_finder):
    code = '''
class MyClass:
    @classmethod
    def class_method(cls):
        return "Class Method"
        
    @staticmethod
    def static_method():
        return "Static Method"
        
    @property
    def my_property(self):
        return "Property"
'''
    classmethod_decorators = python_finder.get_decorators(code, 'class_method', 'MyClass')
    assert len(classmethod_decorators) == 1, f'Expected 1 decorator, got {len(classmethod_decorators)}'
    assert '@classmethod' in classmethod_decorators, 'Expected @classmethod in decorators'
    
    staticmethod_decorators = python_finder.get_decorators(code, 'static_method', 'MyClass')
    assert len(staticmethod_decorators) == 1, f'Expected 1 decorator, got {len(staticmethod_decorators)}'
    assert '@staticmethod' in staticmethod_decorators, 'Expected @staticmethod in decorators'
    
    property_decorators = python_finder.get_decorators(code, 'my_property', 'MyClass')
    assert len(property_decorators) == 1, f'Expected 1 decorator, got {len(property_decorators)}'
    assert '@property' in property_decorators, 'Expected @property in decorators'

def test_get_function_no_decorators(python_finder):
    code = '''
def my_function():
    return "Hello"
'''
    decorators = python_finder.get_decorators(code, 'my_function')
    assert len(decorators) == 0, f'Expected 0 decorators, got {len(decorators)}'

def test_get_method_no_decorators(python_finder):
    code = '''
class MyClass:
    def my_method(self):
        return "Hello"
'''
    decorators = python_finder.get_decorators(code, 'my_method', 'MyClass')
    assert len(decorators) == 0, f'Expected 0 decorators, got {len(decorators)}'

def test_get_method_multiple_decorators(python_finder):
    code = '''
class MyClass:
    @decorator1
    @decorator2
    @decorator3
    def my_method(self):
        return "Hello"
'''
    decorators = python_finder.get_decorators(code, 'my_method', 'MyClass')
    assert len(decorators) == 3, f'Expected 3 decorators, got {len(decorators)}'
    assert '@decorator1' in decorators, 'Expected @decorator1 in decorators'
    assert '@decorator2' in decorators, 'Expected @decorator2 in decorators'
    assert '@decorator3' in decorators, 'Expected @decorator3 in decorators'