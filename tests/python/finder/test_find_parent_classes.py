import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_parent_classes_single(python_finder):
    """Test finding a single parent class."""
    example = TestHelper.load_example('parent_classes_single.py', category='inheritance')
    parents = python_finder.find_parent_classes(example.content, example.metadata['child_class'])
    expected_parents = example.metadata['expected_parents']
    assert len(parents) == len(expected_parents), f'Expected {len(expected_parents)} parent class, got {len(parents)}'
    for parent in expected_parents:
        assert parent in parents, f'Expected {parent} in parent classes'

def test_find_parent_classes_multiple(python_finder):
    """Test finding multiple parent classes."""
    example = TestHelper.load_example('parent_classes_multiple.py', category='inheritance')
    parents = python_finder.find_parent_classes(example.content, example.metadata['child_class'])
    expected_parents = example.metadata['expected_parents']
    assert len(parents) == len(expected_parents), f'Expected {len(expected_parents)} parent classes, got {len(parents)}'
    for parent in expected_parents:
        assert parent in parents, f'Expected {parent} in parent classes'

def test_find_parent_classes_module_qualified(python_finder):
    """Test finding a parent class with module qualification."""
    example = TestHelper.load_example('parent_classes_module_qualified.py', category='inheritance')
    parents = python_finder.find_parent_classes(example.content, example.metadata['child_class'])
    expected_parents = example.metadata['expected_parents']
    assert len(parents) == len(expected_parents), f'Expected {len(expected_parents)} parent class, got {len(parents)}'
    for parent in expected_parents:
        assert parent in parents, f'Expected {parent} in parent classes'

def test_find_parent_classes_none(python_finder):
    """Test finding parent classes when there are none."""
    example = TestHelper.load_example('parent_classes_none.py', category='inheritance')
    parents = python_finder.find_parent_classes(example.content, example.metadata['child_class'])
    expected_parents = example.metadata['expected_parents']
    assert len(parents) == len(expected_parents), 'Expected no parent classes'

def test_find_parent_classes_class_not_found(python_finder):
    """Test behavior when the class is not found."""
    example = TestHelper.load_example('parent_classes_class_not_found.py', category='inheritance')
    parents = python_finder.find_parent_classes(example.content, example.metadata['child_class'])
    expected_parents = example.metadata['expected_parents']
    assert len(parents) == len(expected_parents), 'Expected no parent classes when class not found'