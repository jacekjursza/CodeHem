import pytest

from core.finder.factory import get_code_finder


@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_get_class_decorators(python_finder):
    code = '''
@class_decorator1
@class_decorator2
class MyClass:
    def method(self):
        pass
'''
    decorators = python_finder.get_class_decorators(code, 'MyClass')
    assert len(decorators) == 2, f'Expected 2 decorators, got {len(decorators)}'
    assert '@class_decorator1' in decorators, 'Expected @class_decorator1 in decorators'
    assert '@class_decorator2' in decorators, 'Expected @class_decorator2 in decorators'

def test_get_class_no_decorators(python_finder):
    code = '''
class MyClass:
    def method(self):
        pass
'''
    decorators = python_finder.get_class_decorators(code, 'MyClass')
    assert len(decorators) == 0, f'Expected 0 decorators, got {len(decorators)}'

def test_get_class_decorators_with_arguments(python_finder):
    code = '''
@register('category')
@dataclass(frozen=True)
class MyClass:
    id: int
    name: str
'''
    decorators = python_finder.get_class_decorators(code, 'MyClass')
    assert len(decorators) == 2, f'Expected 2 decorators, got {len(decorators)}'
    assert "@register('category')" in decorators, "Expected @register('category') in decorators"
    assert '@dataclass(frozen=True)' in decorators, 'Expected @dataclass(frozen=True) in decorators'

def test_get_class_decorator_custom_format(python_finder):
    code = '''
@some_decorator(
    param1="value1",
    param2=123,
    param3=["list", "of", "items"]
)
class ConfiguredClass:
    def method(self):
        pass
'''
    decorators = python_finder.get_class_decorators(code, 'ConfiguredClass')
    assert len(decorators) == 1, f'Expected 1 decorator, got {len(decorators)}'
    assert decorators[0].startswith('@some_decorator('), 'Expected decorator to start with @some_decorator('
    assert 'param1="value1"' in decorators[0], 'Expected param1="value1" in decorator'
    assert 'param2=123' in decorators[0], 'Expected param2=123 in decorator'
    assert 'param3=["list", "of", "items"]' in decorators[0], 'Expected param3=["list", "of", "items"] in decorator'