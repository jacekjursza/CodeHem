import pytest
from codehem.core.finder import get_code_finder
from tree_sitter import Node

@pytest.fixture
def typescript_finder():
    return get_code_finder('typescript')

def test_get_classes_from_code(typescript_finder):
    code = '\nclass FirstClass {\n    method1() {\n        console.log("Method 1");\n    }\n}\n\nclass SecondClass {\n    method2() {\n        console.log("Method 2");\n    }\n}\n'
    classes = typescript_finder.get_classes_from_code(code)
    assert len(classes) == 2, f'Expected 2 classes, got {len(classes)}'
    class_names = [name for (name, _) in classes]
    assert 'FirstClass' in class_names, 'FirstClass not found'
    assert 'SecondClass' in class_names, 'SecondClass not found'
    for (_, node) in classes:
        assert isinstance(node, Node), 'Expected a tree-sitter Node'

def test_get_methods_from_class(typescript_finder):
    code = '\nclass TestClass {\n    method1() {\n        console.log("Method 1");\n    }\n    \n    method2(arg: string) {\n        console.log(arg);\n        return arg;\n    }\n    \n    static staticMethod() {\n        console.log("Static method");\n    }\n}\n'
    methods = typescript_finder.get_methods_from_class(code, 'TestClass')
    assert len(methods) == 3, f'Expected 3 methods, got {len(methods)}'
    method_names = [name for (name, _) in methods]
    assert 'method1' in method_names, 'method1 not found'
    assert 'method2' in method_names, 'method2 not found'
    assert 'staticMethod' in method_names, 'staticMethod not found'

def test_has_class_method_indicator(typescript_finder):
    code = '\nclass TestClass {\n    instanceMethod() {\n        console.log(this.property); // Uses \'this\'\n    }\n    \n    static staticMethod() {\n        console.log(TestClass.property); // No \'this\'\n    }\n}\n'

    # Test the string-based approach directly
    (root, code_bytes) = typescript_finder._get_tree(code)

    # Assert based on the fact that 'this.' appears in the code
    assert typescript_finder.has_class_method_indicator(root, code_bytes), 'Should detect "this." in the code'
