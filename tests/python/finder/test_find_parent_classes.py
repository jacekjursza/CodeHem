import pytest
from finder.factory import get_code_finder

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_parent_classes_single(python_finder):
    """Test finding a single parent class."""
    code = '''
class Parent:
    def parent_method(self):
        pass

class Child(Parent):
    def child_method(self):
        pass
'''
    parents = python_finder.find_parent_classes(code, 'Child')
    assert len(parents) == 1, f'Expected 1 parent class, got {len(parents)}'
    assert 'Parent' in parents, 'Expected Parent in parent classes'

def test_find_parent_classes_multiple(python_finder):
    """Test finding multiple parent classes."""
    code = '''
class Parent1:
    pass

class Parent2:
    pass

class Child(Parent1, Parent2):
    pass
'''
    parents = python_finder.find_parent_classes(code, 'Child')
    assert len(parents) == 2, f'Expected 2 parent classes, got {len(parents)}'
    assert 'Parent1' in parents, 'Expected Parent1 in parent classes'
    assert 'Parent2' in parents, 'Expected Parent2 in parent classes'

def test_find_parent_classes_module_qualified(python_finder):
    """Test finding a parent class with module qualification."""
    code = '''
import module

class Child(module.Parent):
    pass
'''
    parents = python_finder.find_parent_classes(code, 'Child')
    assert len(parents) == 1, f'Expected 1 parent class, got {len(parents)}'
    assert 'module.Parent' in parents, 'Expected module.Parent in parent classes'

def test_find_parent_classes_none(python_finder):
    """Test finding parent classes when there are none."""
    code = '''
class StandaloneClass:
    pass
'''
    parents = python_finder.find_parent_classes(code, 'StandaloneClass')
    assert len(parents) == 0, 'Expected no parent classes'

def test_find_parent_classes_class_not_found(python_finder):
    """Test behavior when the class is not found."""
    code = '''
class ExistingClass:
    pass
'''
    parents = python_finder.find_parent_classes(code, 'NonExistentClass')
    assert len(parents) == 0, 'Expected no parent classes when class not found'