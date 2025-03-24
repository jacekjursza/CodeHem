import pytest
from codehem.core.codehem2 import CodeHem2
from tests.helpers.code_examples import TestHelper
from codehem.core.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_find_imports_section_simple(codehem2):
    """Test finding a simple imports section."""
    example = TestHelper.load_example('imports_simple.py', category='import')
    
    # Use extract to get all elements
    result = codehem2.extract(example.content)
    
    # Find imports
    imports_found = False
    for element in result.elements:
        if element.type == CodeElementType.IMPORT:
            imports_found = True
            break
    
    assert imports_found, "Import section not found"
    
    # Check if we can get imports via filter
    imports_element = codehem2.filter(result, 'imports')
    assert imports_element is not None, "Import section not found via filter"

def test_find_imports_section_none(codehem2):
    """Test finding an imports section in a file without imports."""
    example = TestHelper.load_example('imports_none.py', category='import')
    
    # Use extract to get all elements
    result = codehem2.extract(example.content)
    
    # Find imports
    imports_found = False
    for element in result.elements:
        if element.type == CodeElementType.IMPORT:
            imports_found = True
            break
    
    assert not imports_found, "Unexpected import section found"
    
    # Check that filter returns None
    imports_element = codehem2.filter(result, 'imports')
    assert imports_element is None, "Unexpected import section found via filter"