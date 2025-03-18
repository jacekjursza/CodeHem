import pytest
from finder.factory import get_code_finder
from tree_sitter import Node

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_get_classes_from_code(python_finder):
    code = '''
class FirstClass:
    def method1(self):
        pass
        
class SecondClass:
    def method2(self):
        pass
'''
    classes = python_finder.get_classes_from_code(code)
    assert len(classes) == 2, f'Expected 2 classes, got {len(classes)}'
    class_names = [name for name, _ in classes]
    assert 'FirstClass' in class_names, 'FirstClass not found'
    assert 'SecondClass' in class_names, 'SecondClass not found'
    
    # Check that the nodes are valid
    for _, node in classes:
        assert isinstance(node, Node), 'Expected a tree-sitter Node'

def test_get_methods_from_class(python_finder):
    code = '''
class TestClass:
    def method1(self):
        pass
        
    def method2(self, arg):
        return arg
        
    @staticmethod
    def static_method():
        pass
'''
    methods = python_finder.get_methods_from_class(code, 'TestClass')
    assert len(methods) == 3, f'Expected 3 methods, got {len(methods)}'
    method_names = [name for name, _ in methods]
    assert 'method1' in method_names, 'method1 not found'
    assert 'method2' in method_names, 'method2 not found'
    assert 'static_method' in method_names, 'static_method not found'

def test_has_class_method_indicator(python_finder):
    code = '''
class TestClass:
    def instance_method(self):
        pass
        
    @classmethod
    def class_method(cls):
        pass
        
    @staticmethod
    def static_method():
        pass
'''
    methods = python_finder.get_methods_from_class(code, 'TestClass')
    code_bytes = code.encode('utf8')
    
    # Find instance method
    instance_method = next(node for name, node in methods if name == 'instance_method')
    assert python_finder.has_class_method_indicator(instance_method, code_bytes), 'instance_method should have self parameter'
    
    # Find static method
    static_method = next(node for name, node in methods if name == 'static_method')
    assert not python_finder.has_class_method_indicator(static_method, code_bytes), 'static_method should not have self parameter'