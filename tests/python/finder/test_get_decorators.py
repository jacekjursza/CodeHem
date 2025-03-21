import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_get_function_decorators(python_finder):
    example = TestHelper.load_example('function_decorators.py', category='decorator')
    decorators = python_finder.get_decorators(example.content, example.metadata['function_name'])
    assert len(decorators) == len(example.metadata['expected_decorators']), f'Expected {len(example.metadata["expected_decorators"])} decorators, got {len(decorators)}'
    for expected_decorator in example.metadata['expected_decorators']:
        assert expected_decorator in decorators, f'Expected {expected_decorator} in decorators'

def test_get_method_decorators(python_finder):
    example = TestHelper.load_example('method_decorators.py', category='decorator')
    class_name = example.metadata['class_name']
    method_decorators = example.metadata['method_decorators']
    
    for method_name, expected_decorators in method_decorators.items():
        decorators = python_finder.get_decorators(example.content, method_name, class_name)
        assert len(decorators) == len(expected_decorators), f'Expected {len(expected_decorators)} decorator for {method_name}, got {len(decorators)}'
        for expected_decorator in expected_decorators:
            assert expected_decorator in decorators, f'Expected {expected_decorator} in decorators for {method_name}'

def test_get_function_no_decorators(python_finder):
    example = TestHelper.load_example('function_no_decorators.py', category='decorator')
    decorators = python_finder.get_decorators(example.content, example.metadata['function_name'])
    assert len(decorators) == len(example.metadata['expected_decorators']), f'Expected {len(example.metadata["expected_decorators"])} decorators, got {len(decorators)}'

def test_get_method_no_decorators(python_finder):
    example = TestHelper.load_example('method_no_decorators.py', category='decorator')
    decorators = python_finder.get_decorators(example.content, example.metadata['method_name'], example.metadata['class_name'])
    assert len(decorators) == len(example.metadata['expected_decorators']), f'Expected {len(example.metadata["expected_decorators"])} decorators, got {len(decorators)}'

def test_get_method_multiple_decorators(python_finder):
    example = TestHelper.load_example('method_multiple_decorators.py', category='decorator')
    decorators = python_finder.get_decorators(example.content, example.metadata['method_name'], example.metadata['class_name'])
    assert len(decorators) == len(example.metadata['expected_decorators']), f'Expected {len(example.metadata["expected_decorators"])} decorators, got {len(decorators)}'
    for expected_decorator in example.metadata['expected_decorators']:
        assert expected_decorator in decorators, f'Expected {expected_decorator} in decorators'