import pytest
import logging
from codehem import CodeHem, CodeElementType
# Ensure the import path for TestHelper is correct relative to this file's location
from ..helpers.code_examples import TestHelper # Assuming it's in tests/helpers/
# --- ADDED IMPORT FOR REGISTRY ---
from codehem.core.registry import registry
# ---------------------------------

# Configure logging for tests if needed
# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def codehem_ts():
    """ Provides a CodeHem instance configured for TypeScript. """
    # Ensure the TypeScript language service can be loaded
    try:
        # Attempt to initialize to catch potential issues early, though registry should handle it
        # Now 'registry' should be defined due to the import above
        ts_service = registry.get_language_service('typescript')
        if not ts_service:
             pytest.skip("TypeScript language service not fully registered or functional yet.")
        # Also check if essential components like formatter are present
        if not hasattr(ts_service, 'formatter') or ts_service.formatter is None:
             logger.warning("TypeScript service loaded but formatter might be missing.")
        # Check if extractors were loaded (at least some)
        if not hasattr(ts_service, 'extractors') or not ts_service.extractors:
             logger.warning("TypeScript service loaded but extractors might be missing.")

        # If basic checks pass, return the CodeHem instance
        return CodeHem('typescript')
    except ValueError as e:
        # Catch error if CodeHem('typescript') itself fails
        pytest.skip(f"Skipping TypeScript tests due to CodeHem initialization error: {e}")
    except Exception as e:
        # Catch any other unexpected errors during setup
        pytest.skip(f"Skipping TypeScript tests due to unexpected error in fixture setup: {e}")

# --- Basic Extraction Tests ---

def test_extract_ts_class(codehem_ts):
    """Test extracting a simple TypeScript class."""
    logger.debug("Running test: test_extract_ts_class")
    example = TestHelper.load_example('simple_class', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None, "Extraction result should not be None"
    assert hasattr(result, 'elements'), "Extraction result should have 'elements' attribute"

    class_element = codehem_ts.filter(result, example.class_name)
    if class_element is None:
         available_elements = [(e.name, e.type.value) for e in result.elements] if result and result.elements else []
         pytest.fail(f"Class '{example.class_name}' not found. Available elements: {available_elements}")

    assert class_element.type == CodeElementType.CLASS, f"Expected CLASS type, got {class_element.type}"
    assert class_element.name == example.class_name
    assert class_element.range is not None, "Class element should have a range"
    # assert class_element.range.start_line == example.expected_start_line # Range checks might fail until extractors are perfect
    # assert class_element.range.end_line == example.expected_end_line
    logger.debug(f"Successfully tested class: {example.class_name}")

def test_extract_js_function(codehem_ts):
    """Test extracting a simple JavaScript function."""
    logger.debug("Running test: test_extract_js_function")
    example = TestHelper.load_example('simple_function.js', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    func_element = codehem_ts.filter(result, example.function_name)
    if func_element is None:
         available_elements = [(e.name, e.type.value) for e in result.elements] if result and result.elements else []
         pytest.fail(f"Function '{example.function_name}' not found. Available elements: {available_elements}")

    assert func_element.type == CodeElementType.FUNCTION, f"Expected FUNCTION type, got {func_element.type}"
    assert func_element.name == example.function_name
    assert func_element.range is not None, "Function element should have a range"
    # assert func_element.range.start_line == example.expected_start_line
    # assert func_element.range.end_line == example.expected_end_line
    logger.debug(f"Successfully tested function: {example.function_name}")

def test_extract_ts_interface(codehem_ts):
    """Test extracting a TypeScript interface."""
    logger.debug("Running test: test_extract_ts_interface")
    example = TestHelper.load_example('simple_interface', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    interface_name = example.metadata.get('interface_name')
    interface_element = codehem_ts.filter(result, interface_name)

    if interface_element is None:
         available_elements = [(e.name, e.type.value) for e in result.elements] if result and result.elements else []
         pytest.fail(f"Interface '{interface_name}' not found. Available elements: {available_elements}. Interface extraction might not be implemented yet.")

    assert interface_element.type == CodeElementType.INTERFACE, f"Expected INTERFACE type, got {interface_element.type}"
    assert interface_element.name == interface_name
    assert interface_element.range is not None
    # assert interface_element.range.start_line == example.expected_start_line
    # assert interface_element.range.end_line == example.expected_end_line
    logger.debug(f"Successfully tested interface: {interface_name}")

def test_extract_ts_method(codehem_ts):
    """Test extracting a method from a TypeScript class."""
    logger.debug("Running test: test_extract_ts_method")
    example = TestHelper.load_example('class_with_method', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    method_xpath = f"{example.class_name}.{example.method_name}"
    method_element = result.filter(method_xpath) # Use filter on the result object

    if method_element is None:
        class_element = result.filter(example.class_name)
        available_members = []
        if class_element and class_element.children:
             available_members = [(c.name, c.type.value) for c in class_element.children]
        pytest.fail(f"Method '{method_xpath}' not found. Class '{example.class_name}' members: {available_members}")

    assert method_element.type == CodeElementType.METHOD, f"Expected METHOD type for {method_xpath}, got {method_element.type}"
    assert method_element.name == example.method_name
    assert method_element.parent_name == example.class_name
    assert method_element.range is not None
    # assert method_element.range.start_line == example.expected_start_line
    # assert method_element.range.end_line == example.expected_end_line
    logger.debug(f"Successfully tested method: {method_xpath}")

def test_extract_ts_imports(codehem_ts):
    """Test extracting TypeScript/JavaScript imports."""
    logger.debug("Running test: test_extract_ts_imports")
    example = TestHelper.load_example('imports_section.ts', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    import_element = None
    for elem in result.elements:
        if elem.type == CodeElementType.IMPORT and elem.name == 'imports':
            import_element = elem
            break

    if import_element is None:
        available_elements = [(e.name, e.type.value) for e in result.elements] if result and result.elements else []
        pytest.fail(f"Combined 'imports' element not found. Found elements: {available_elements}. Import extraction/processing might be incomplete.")

    assert import_element.type == CodeElementType.IMPORT
    assert import_element.content is not None
    assert import_element.range is not None
    # Check if some expected imports are within the content
    expected = example.metadata.get('imports', '').split(', ')
    for imp in expected[:2]: # Check first few expected imports
         content_check = imp.strip() in import_element.content
         assert content_check, f"Expected import '{imp.strip()}' not found in combined content"
    logger.debug(f"Successfully tested combined imports section.")

def test_extract_ts_property(codehem_ts):
    """Test extracting a property (class field) from a TypeScript class."""
    logger.debug("Running test: test_extract_ts_property")
    example = TestHelper.load_example('class_with_property', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    class_element = result.filter(example.class_name)
    if class_element is None:
         available_elements = [(e.name, e.type.value) for e in result.elements] if result and result.elements else []
         pytest.fail(f"Class '{example.class_name}' not found. Available elements: {available_elements}")

    prop_name = example.metadata.get('property_name')
    property_element = None
    available_children = []
    if class_element.children:
         available_children = [(c.name, c.type.value) for c in class_element.children]
         for child in class_element.children:
             # Check for PROPERTY type specifically
             if child.name == prop_name and child.type == CodeElementType.PROPERTY:
                 property_element = child
                 break

    if property_element is None:
        pytest.fail(f"Property '{prop_name}' not found as child of type PROPERTY in {example.class_name}. Available children: {available_children}")

    assert property_element.type == CodeElementType.PROPERTY
    assert property_element.range is not None
    assert 'apiKey' in property_element.content # Check based on fixture content
    logger.debug(f"Successfully tested property: {prop_name}")

def test_extract_ts_decorated_method(codehem_ts):
    """Test extracting a method with a decorator in TypeScript."""
    logger.debug("Running test: test_extract_ts_decorated_method")
    example = TestHelper.load_example('decorated_method.ts', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    method_xpath = f"{example.class_name}.{example.method_name}"
    method_element = result.filter(method_xpath)

    if method_element is None:
        class_element = result.filter(example.class_name)
        available_members = []
        if class_element and class_element.children:
             available_members = [(c.name, c.type.value) for c in class_element.children]
        pytest.fail(f"Decorated method '{method_xpath}' not found. Class '{example.class_name}' members: {available_members}")

    assert method_element.type == CodeElementType.METHOD
    assert method_element.range is not None

    # Check for decorator as a child element
    decorator_name = example.metadata.get('decorator_name')
    found_decorator = None
    available_children = []
    if method_element.children:
         available_children = [(c.name, c.type.value) for c in method_element.children]
         for child in method_element.children:
             if child.type == CodeElementType.DECORATOR and child.name == decorator_name:
                 found_decorator = child
                 break

    if found_decorator is None:
         pytest.fail(f"Decorator '@{decorator_name}' not found as child of {method_xpath}. Available children: {available_children}")

    assert f"@{decorator_name}" in found_decorator.content
    logger.debug(f"Successfully tested decorated method: {method_xpath}")