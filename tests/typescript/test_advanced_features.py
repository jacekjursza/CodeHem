import pytest
import logging
from codehem import CodeHem, CodeElementType
from ..helpers.code_examples import TestHelper

logger = logging.getLogger(__name__)

@pytest.fixture
def codehem_ts():
    """Provides a CodeHem instance configured for TypeScript."""
    return CodeHem('typescript')

def test_extract_ts_enum(codehem_ts):
    """Test extracting a TypeScript enum."""
    logger.debug("Running test: test_extract_ts_enum")
    example = TestHelper.load_example('enum_declaration', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    enum_name = example.metadata.get('enum_name')
    enum_element = codehem_ts.filter(result, enum_name)

    assert enum_element is not None, f"Enum {enum_name} should be extracted"
    assert enum_element.type == CodeElementType.ENUM, f"Expected ENUM type, got {enum_element.type}"
    assert enum_element.name == enum_name
    assert enum_element.range is not None
    logger.debug(f"Successfully tested enum: {enum_name}")

def test_extract_ts_type_alias(codehem_ts):
    """Test extracting a TypeScript type alias."""
    logger.debug("Running test: test_extract_ts_type_alias")
    example = TestHelper.load_example('union_types', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    type_name = example.metadata.get('type_name')
    type_element = codehem_ts.filter(result, type_name)

    assert type_element is not None, f"Type alias {type_name} should be extracted"
    assert type_element.type == CodeElementType.TYPE_ALIAS, f"Expected TYPE_ALIAS type, got {type_element.type}"
    assert type_element.name == type_name
    assert type_element.range is not None
    logger.debug(f"Successfully tested type alias: {type_name}")

def test_extract_ts_namespace(codehem_ts):
    """Test extracting a TypeScript namespace."""
    logger.debug("Running test: test_extract_ts_namespace")
    example = TestHelper.load_example('namespace_declaration', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    namespace_name = example.metadata.get('namespace_name')
    namespace_element = codehem_ts.filter(result, namespace_name)

    assert namespace_element is not None, f"Namespace {namespace_name} should be extracted"
    assert namespace_element.type == CodeElementType.NAMESPACE, f"Expected NAMESPACE type, got {namespace_element.type}"
    assert namespace_element.name == namespace_name
    assert namespace_element.range is not None
    logger.debug(f"Successfully tested namespace: {namespace_name}")

def test_extract_ts_arrow_function(codehem_ts):
    """Test extracting TypeScript arrow functions with async/await."""
    logger.debug("Running test: test_extract_ts_arrow_function")
    example = TestHelper.load_example('arrow_function', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    function_name = example.metadata.get('function_name')
    function_element = codehem_ts.filter(result, function_name)

    assert function_element is not None, f"Arrow function {function_name} should be extracted"
    assert function_element.type == CodeElementType.FUNCTION, f"Expected FUNCTION type, got {function_element.type}"
    assert function_element.name == function_name
    assert function_element.range is not None
    logger.debug(f"Successfully tested arrow function: {function_name}")

def test_extract_ts_generic_interface(codehem_ts):
    """Test extracting TypeScript generic interfaces."""
    logger.debug("Running test: test_extract_ts_generic_interface")
    example = TestHelper.load_example('generic_interface', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    interface_name = example.metadata.get('interface_name')
    interface_element = codehem_ts.filter(result, interface_name)

    assert interface_element is not None, f"Generic interface {interface_name} should be extracted"
    assert interface_element.type == CodeElementType.INTERFACE, f"Expected INTERFACE type, got {interface_element.type}"
    assert interface_element.name == interface_name
    assert interface_element.range is not None
    logger.debug(f"Successfully tested generic interface: {interface_name}")

def test_extract_ts_complex_class(codehem_ts):
    """Test extracting a complex TypeScript class with generics, decorators, and inheritance."""
    logger.debug("Running test: test_extract_ts_complex_class")
    example = TestHelper.load_example('complex_class', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    class_name = example.metadata.get('class_name')
    class_element = codehem_ts.filter(result, class_name)

    assert class_element is not None, f"Complex class {class_name} should be extracted"
    assert class_element.type == CodeElementType.CLASS, f"Expected CLASS type, got {class_element.type}"
    assert class_element.name == class_name
    assert class_element.range is not None

    # Also check that methods and properties are extracted
    method_name = example.metadata.get('method_name')
    method_xpath = f"{class_name}.{method_name}"
    method_element = result.filter(method_xpath)
    assert method_element is not None, f"Method {method_name} should be extracted from complex class"

    logger.debug(f"Successfully tested complex class: {class_name}")

def test_extract_ts_async_function(codehem_ts):
    """Test extracting TypeScript async functions."""
    logger.debug("Running test: test_extract_ts_async_function")
    example = TestHelper.load_example('async_await', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    function_name = example.metadata.get('function_name')
    function_element = codehem_ts.filter(result, function_name)

    assert function_element is not None, f"Async function {function_name} should be extracted"
    assert function_element.type == CodeElementType.FUNCTION, f"Expected FUNCTION type, got {function_element.type}"
    assert function_element.name == function_name
    assert function_element.range is not None
    logger.debug(f"Successfully tested async function: {function_name}")

def test_extract_ts_export_patterns(codehem_ts):
    """Test extracting TypeScript export patterns."""
    logger.debug("Running test: test_extract_ts_export_patterns")
    example = TestHelper.load_example('export_patterns', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    # Should extract at least the default export function
    function_name = example.metadata.get('function_name')
    function_element = codehem_ts.filter(result, function_name)

    assert function_element is not None, f"Exported function {function_name} should be extracted"
    assert function_element.type == CodeElementType.FUNCTION, f"Expected FUNCTION type, got {function_element.type}"
    assert function_element.name == function_name
    logger.debug(f"Successfully tested export patterns with function: {function_name}")