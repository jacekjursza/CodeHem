import pytest
from codehem.core.finder import get_code_finder

@pytest.fixture
def typescript_finder():
    return get_code_finder('typescript')

def test_find_function_simple(typescript_finder):
    code = '\nfunction myFunction() {\n    console.log("Hello");\n}\n'
    (start_line, end_line) = typescript_finder.find_function(code, 'myFunction')
    assert start_line == 2, f'Expected start line 2, got {start_line}'
    assert end_line == 4, f'Expected end line 4, got {end_line}'

def test_find_function_missing(typescript_finder):
    code = '\nfunction anotherFunction() {\n    console.log("Still hello");\n}\n'
    (start_line, end_line) = typescript_finder.find_function(code, 'myFunction')
    assert start_line == 0 and end_line == 0, 'Expected no lines when function does not exist'

def test_find_function_with_params(typescript_finder):
    code = '\nfunction myFunction(param1: string, param2: number): void {\n    console.log(param1, param2);\n}\n'
    (start_line, end_line) = typescript_finder.find_function(code, 'myFunction')
    assert start_line == 2, f'Expected start line 2, got {start_line}'
    assert end_line == 4, f'Expected end line 4, got {end_line}'

def test_find_async_function(typescript_finder):
    code = '\nasync function myAsyncFunction() {\n    return await Promise.resolve("Hello");\n}\n'
    (start_line, end_line) = typescript_finder.find_function(code, 'myAsyncFunction')
    assert start_line == 2, f'Expected start line 2, got {start_line}'
    assert end_line == 4, f'Expected end line 4, got {end_line}'

def test_find_exported_function(typescript_finder):
    code = '\nexport function exportedFunction() {\n    console.log("Exported");\n}\n'
    (start_line, end_line) = typescript_finder.find_function(code, 'exportedFunction')
    assert start_line == 2, f'Expected start line 2, got {start_line}'
    assert end_line == 4, f'Expected end line 4, got {end_line}'

def test_find_function_with_generic_types(typescript_finder):
    code = '\nfunction genericFunction<T>(item: T): T {\n    return item;\n}\n'
    (start_line, end_line) = typescript_finder.find_function(code, 'genericFunction')
    assert start_line == 2, f'Expected start line 2, got {start_line}'
    assert end_line == 4, f'Expected end line 4, got {end_line}'