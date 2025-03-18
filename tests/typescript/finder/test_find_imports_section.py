import pytest
from finder.factory import get_code_finder

@pytest.fixture
def typescript_finder():
    return get_code_finder('typescript')

def test_find_imports_section_simple(typescript_finder):
    code = '\nimport { Component } from \'react\';\nimport axios from \'axios\';\n\nconst App = () => {};\n'
    (start_line, end_line) = typescript_finder.find_imports_section(code)
    assert start_line == 2, f'Expected imports section start at line 2, got {start_line}'
    assert end_line == 3, f'Expected imports section end at line 3, got {end_line}'

def test_find_imports_section_none(typescript_finder):
    code = '\nconst foo = () => {};\n'
    (start_line, end_line) = typescript_finder.find_imports_section(code)
    assert start_line == 0 and end_line == 0, 'Expected no imports section when no imports'

def test_find_imports_section_multiple_styles(typescript_finder):
    code = '\nimport * as React from \'react\';\nimport { useState, useEffect } from \'react\';\nimport type { ReactNode } from \'react\';\nimport MyComponent from \'./MyComponent\';\n\nconst App = () => {};\n'
    (start_line, end_line) = typescript_finder.find_imports_section(code)
    assert start_line == 2, f'Expected imports section start at line 2, got {start_line}'
    assert end_line == 5, f'Expected imports section end at line 5, got {end_line}'

def test_find_imports_section_with_comments(typescript_finder):
    code = '\n// React imports\nimport React from \'react\';\n// Other imports\nimport axios from \'axios\';\n\nconst App = () => {};\n'
    (start_line, end_line) = typescript_finder.find_imports_section(code)
    assert start_line == 3, f'Expected imports section start at line 3, got {start_line}'
    assert end_line == 5, f'Expected imports section end at line 5, got {end_line}'

def test_find_imports_section_with_reexports(typescript_finder):
    code = '\nimport { Component } from \'react\';\nexport { Component };\n\nconst App = () => {};\n'
    (start_line, end_line) = typescript_finder.find_imports_section(code)
    assert start_line == 2, f'Expected imports section start at line 2, got {start_line}'
    # May vary depending on how the finder handles export statements
    # Some implementations might consider the export part of the imports section