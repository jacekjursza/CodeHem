import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_module_direct_import(python_finder):
    """Test finding module with direct import: from module import Class."""
    example = TestHelper.load_example('direct_import.py', category='module')
    module = python_finder.find_module_for_class(example.content, example.metadata['class_name'])
    assert module == example.metadata['expected_module'], f'Expected {example.metadata["expected_module"]}, got {module}'

def test_find_module_aliased_import(python_finder):
    """Test finding module with aliased import: from module import Class as AliasClass."""
    example = TestHelper.load_example('aliased_import.py', category='module')
    module = python_finder.find_module_for_class(example.content, example.metadata['class_name'])
    assert module == example.metadata['expected_module'], f'Expected {example.metadata["expected_module"]}, got {module}'

def test_find_module_module_import(python_finder):
    """Test finding module with module import: import module."""
    example = TestHelper.load_example('module_import.py', category='module')
    module = python_finder.find_module_for_class(example.content, example.metadata['class_name'])
    assert module == example.metadata['expected_module'], f'Expected {example.metadata["expected_module"]}, got {module}'

def test_find_module_subpackage_import(python_finder):
    """Test finding module with subpackage import: from package.submodule import Class."""
    example = TestHelper.load_example('subpackage_import.py', category='module')
    module = python_finder.find_module_for_class(example.content, example.metadata['class_name'])
    assert module == example.metadata['expected_module'], f'Expected {example.metadata["expected_module"]}, got {module}'

def test_find_module_class_not_imported(python_finder):
    """Test behavior when the class is not imported."""
    example = TestHelper.load_example('class_not_imported.py', category='module')
    module = python_finder.find_module_for_class(example.content, example.metadata['class_name'])
    assert module is None, f'Expected None, got {module}'