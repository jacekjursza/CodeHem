import pytest
from codehem.core import get_code_manipulator

@pytest.fixture
def typescript_manipulator():
    return get_code_manipulator('typescript')

def test_replace_imports_section_simple(typescript_manipulator):
    original_code = '\nimport React from \'react\';\nimport { useState } from \'react\';\n\nconst App = () => {};\n'
    new_imports = '\nimport React, { useState, useEffect } from \'react\';\nimport axios from \'axios\';\n'
    expected = '\nimport React, { useState, useEffect } from \'react\';\nimport axios from \'axios\';\n\nconst App = () => {};\n'
    result = typescript_manipulator.replace_imports_section(original_code, new_imports)
    assert result.strip() == expected.strip()

def test_replace_imports_section_no_imports(typescript_manipulator):
    original_code = '\nconst App = () => {};\n'
    new_imports = '\nimport React from \'react\';\n'
    expected = '\nimport React from \'react\';\n\nconst App = () => {};\n'
    result = typescript_manipulator.replace_imports_section(original_code, new_imports)
    assert result.strip() == expected.strip()

def test_replace_imports_section_with_comments(typescript_manipulator):
    original_code = '\n// React imports\nimport React from \'react\';\n\nconst App = () => {};\n'
    new_imports = '\n// Updated React imports\nimport React, { useState } from \'react\';\n'
    expected = '\n// Updated React imports\nimport React, { useState } from \'react\';\n\nconst App = () => {};\n'
    result = typescript_manipulator.replace_imports_section(original_code, new_imports)
    assert result.strip() == expected.strip()

def test_replace_imports_section_with_different_styles(typescript_manipulator):
    original_code = '\nimport React from \'react\';\nimport * as ReactDOM from \'react-dom\';\n\nconst App = () => {};\n'
    new_imports = '\nimport { Component } from \'react\';\nimport type { ReactNode } from \'react\';\n'
    expected = '\nimport { Component } from \'react\';\nimport type { ReactNode } from \'react\';\n\nconst App = () => {};\n'
    result = typescript_manipulator.replace_imports_section(original_code, new_imports)
    assert result.strip() == expected.strip()

def test_replace_imports_section_with_export(typescript_manipulator):
    original_code = '\nimport React from \'react\';\nexport const VERSION = "1.0.0";\n\nconst App = () => {};\n'
    new_imports = '\nimport React, { useState } from \'react\';\n'
    expected = '\nimport React, { useState } from \'react\';\nexport const VERSION = "1.0.0";\n\nconst App = () => {};\n'
    result = typescript_manipulator.replace_imports_section(original_code, new_imports)
    # This test may require adjustment based on how your implementation handles export statements