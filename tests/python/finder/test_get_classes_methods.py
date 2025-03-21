import pytest
from tree_sitter import Node
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_get_classes_from_code(python_finder):
    example = TestHelper.load_example('classes_from_code.py', category='class_methods')
    classes = python_finder.get_classes_from_code(example.content)
    assert len(classes) == len(example.metadata['expected_classes']), f'Expected {len(example.metadata["expected_classes"])} classes, got {len(classes)}'
    class_names = [name for (name, _) in classes]
    for expected_class in example.metadata['expected_classes']:
        assert expected_class in class_names, f'{expected_class} not found'
    for (_, node) in classes:
        assert isinstance(node, Node), 'Expected a tree-sitter Node'

def test_get_methods_from_class(python_finder):
    example = TestHelper.load_example('methods_from_class.py', category='class_methods')
    methods = python_finder.get_methods_from_class(example.content, example.metadata['class_name'])
    assert len(methods) == len(example.metadata['expected_methods']), f'Expected {len(example.metadata["expected_methods"])} methods, got {len(methods)}'
    method_names = [name for (name, _) in methods]
    for expected_method in example.metadata['expected_methods']:
        assert expected_method in method_names, f'{expected_method} not found'

def test_has_class_method_indicator(python_finder):
    example = TestHelper.load_example('class_method_indicator.py', category='class_methods')
    methods = python_finder.get_methods_from_class(example.content, example.metadata['class_name'])
    code_bytes = example.content.encode('utf8')
    
    # Find the instance method node
    instance_method = next((node for (name, node) in methods if name == example.metadata['instance_method']), None)
    assert instance_method is not None, f'Instance method {example.metadata["instance_method"]} not found'
    assert python_finder.has_class_method_indicator(instance_method, code_bytes), 'instance_method should have self parameter'
    
    # Find the static method node
    static_method = next((node for (name, node) in methods if name == example.metadata['static_method']), None)
    assert static_method is not None, f'Static method {example.metadata["static_method"]} not found'
    assert not python_finder.has_class_method_indicator(static_method, code_bytes), 'static_method should not have self parameter'