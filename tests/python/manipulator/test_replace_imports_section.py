
# test_replace_imports_section.py
import pytest

from codehem.core.manipulator.factory import get_code_manipulator


@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_replace_imports_section_simple(python_manipulator):
    original_code = """
import os
import sys

def function():
    pass
"""
    new_imports = """
import os
import datetime
import re
"""
    expected = """
import os
import datetime
import re

def function():
    pass
"""
    result = python_manipulator.replace_imports_section(original_code, new_imports)
    assert result.strip() == expected.strip()

def test_replace_imports_section_no_imports(python_manipulator):
    original_code = """
def function():
    pass
"""
    new_imports = """
import os
import sys
"""
    expected = """
import os
import sys

def function():
    pass
"""
    result = python_manipulator.replace_imports_section(original_code, new_imports)
    assert result.strip() == expected.strip()

def test_replace_imports_section_with_docstring(python_manipulator):
    original_code = """
\"\"\"Module docstring.\"\"\"

import os
import sys

def function():
    pass
"""
    new_imports = """
import datetime
import re
"""
    expected = """
\"\"\"Module docstring.\"\"\"

import datetime
import re

def function():
    pass
"""
    result = python_manipulator.replace_imports_section(original_code, new_imports)
    assert result.strip() == expected.strip()
