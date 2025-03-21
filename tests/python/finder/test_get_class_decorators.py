import pytest
from core.finder.factory import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_get_class_decorators(python_finder):
    example = TestHelper.load_example('class_decorators.py', category='decorator')
    decorators = python_finder.get_class_decorators(example.content, example.metadata['class_name'])
    assert len(decorators) == len(example.metadata['expected_decorators']), f'Expected {len(example.metadata["expected_decorators"])} decorators, got {len(decorators)}'
    for expected_decorator in example.metadata['expected_decorators']:
        assert expected_decorator in decorators, f'Expected {expected_decorator} in decorators'

def test_get_class_no_decorators(python_finder):
    example = TestHelper.load_example('class_no_decorators.py', category='decorator')
    decorators = python_finder.get_class_decorators(example.content, example.metadata['class_name'])
    assert len(decorators) == len(example.metadata['expected_decorators']), f'Expected {len(example.metadata["expected_decorators"])} decorators, got {len(decorators)}'

def test_get_class_decorators_with_arguments(python_finder):
    example = TestHelper.load_example('class_decorators_with_arguments.py', category='decorator')
    decorators = python_finder.get_class_decorators(example.content, example.metadata['class_name'])
    assert len(decorators) == len(example.metadata['expected_decorators']), f'Expected {len(example.metadata["expected_decorators"])} decorators, got {len(decorators)}'
    for expected_decorator in example.metadata['expected_decorators']:
        assert expected_decorator in decorators, f'Expected {expected_decorator} in decorators'

def test_get_class_decorator_custom_format(python_finder):
    example = TestHelper.load_example('class_decorator_custom_format.py', category='decorator')
    decorators = python_finder.get_class_decorators(example.content, example.metadata['class_name'])
    assert len(decorators) == 1, f'Expected 1 decorator, got {len(decorators)}'
    assert decorators[0].startswith(example.metadata['expected_decorator_prefix']), f'Expected decorator to start with {example.metadata["expected_decorator_prefix"]}'
    assert 'param1="value1"' in decorators[0], 'Expected param1="value1" in decorator'
    assert 'param2=123' in decorators[0], 'Expected param2=123 in decorator'
    assert 'param3=["list", "of", "items"]' in decorators[0], 'Expected param3=["list", "of", "items"] in decorator'