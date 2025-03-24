import pytest
from codehem.core.codehem2 import CodeHem2
from codehem.core.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_add_imports(codehem2):
    """Test adding imports to a file with no imports."""
    original_code = '\ndef function():\n    pass\n'
    new_imports = '\nimport os\nimport sys\n'
    
    # Use upsert_element for imports
    result = codehem2.upsert_element(
        original_code, 
        CodeElementType.IMPORT.value, 
        '', 
        new_imports
    )
    
    assert 'import os' in result
    assert 'import sys' in result
    assert 'def function():' in result

def test_combine_imports(codehem2):
    """Test adding imports to a file with existing imports."""
    original_code = '\nimport os\n\ndef function():\n    pass\n'
    new_imports = '\nimport sys\nimport datetime\n'
    
    # Use upsert_element for imports
    result = codehem2.upsert_element(
        original_code, 
        CodeElementType.IMPORT.value, 
        '', 
        new_imports
    )
    
    # Check that both original and new imports are present
    assert 'import os' in result
    assert 'import sys' in result
    assert 'import datetime' in result
    assert 'def function():' in result