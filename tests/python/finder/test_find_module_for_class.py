import pytest

from core.finder.factory import get_code_finder


@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_module_direct_import(python_finder):
    """Test finding module with direct import: from module import Class."""
    code = '''
from my_module import MyClass

instance = MyClass()
'''
    module = python_finder.find_module_for_class(code, 'MyClass')
    assert module == 'my_module', f'Expected my_module, got {module}'

def test_find_module_aliased_import(python_finder):
    """Test finding module with aliased import: from module import Class as AliasClass."""
    code = '''
from my_module import OriginalClass as AliasClass

instance = AliasClass()
'''
    module = python_finder.find_module_for_class(code, 'AliasClass')
    assert module == 'my_module.OriginalClass', f'Expected my_module.OriginalClass, got {module}'

def test_find_module_module_import(python_finder):
    """Test finding module with module import: import module."""
    code = '''
import my_module

instance = my_module.MyClass()
'''
    module = python_finder.find_module_for_class(code, 'MyClass')
    assert module == 'my_module', f'Expected my_module, got {module}'

def test_find_module_subpackage_import(python_finder):
    """Test finding module with subpackage import: from package.submodule import Class."""
    code = '''
from package.submodule import MyClass

instance = MyClass()
'''
    module = python_finder.find_module_for_class(code, 'MyClass')
    assert module == 'package.submodule', f'Expected package.submodule, got {module}'

def test_find_module_class_not_imported(python_finder):
    """Test behavior when the class is not imported."""
    code = '''
from module import SomeClass

instance = SomeClass()
'''
    module = python_finder.find_module_for_class(code, 'NonImportedClass')
    assert module is None, f'Expected None, got {module}'