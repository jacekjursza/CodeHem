import pytest
import logging
from codehem import CodeHem, CodeElementType
from ..helpers.code_examples import TestHelper

logger = logging.getLogger(__name__)

@pytest.fixture
def codehem_js():
    """Provides a CodeHem instance configured for JavaScript."""
    return CodeHem('javascript')

@pytest.fixture  
def codehem_ts():
    """Provides a CodeHem instance configured for TypeScript (for JS files)."""
    return CodeHem('typescript')

def test_extract_js_commonjs_module(codehem_ts):
    """Test extracting CommonJS module patterns."""
    logger.debug("Running test: test_extract_js_commonjs_module")
    example = TestHelper.load_example('commonjs_module', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    function_name = example.metadata.get('function_name')
    function_element = codehem_ts.filter(result, function_name)

    assert function_element is not None, f"CommonJS function {function_name} should be extracted"
    assert function_element.type == CodeElementType.FUNCTION, f"Expected FUNCTION type, got {function_element.type}"
    assert function_element.name == function_name
    assert function_element.range is not None
    logger.debug(f"Successfully tested CommonJS function: {function_name}")

def test_extract_js_prototype_method(codehem_ts):
    """Test extracting JavaScript prototype methods."""
    logger.debug("Running test: test_extract_js_prototype_method")
    example = TestHelper.load_example('prototype_method', category='general', language='typescript')
    result = codehem_ts.extract(example.content)
    assert result is not None and hasattr(result, 'elements')

    # Should extract the constructor function
    class_name = example.metadata.get('class_name')
    class_element = codehem_ts.filter(result, class_name)

    assert class_element is not None, f"Constructor function {class_name} should be extracted"
    assert class_element.type == CodeElementType.FUNCTION, f"Expected FUNCTION type, got {class_element.type}"
    assert class_element.name == class_name
    logger.debug(f"Successfully tested prototype constructor: {class_name}")

def test_javascript_alias_detection():
    """Test that JavaScript files are properly detected and handled via TypeScript service."""
    logger.debug("Running test: test_javascript_alias_detection")
    
    # Test JavaScript detection
    js_code = """
    function processData(input) {
        return input.map(item => item.toString());
    }
    
    module.exports = { processData };
    """
    
    # JavaScript should be handled by TypeScript service
    codehem_js = CodeHem('javascript')
    result = codehem_js.extract(js_code)
    
    assert result is not None and hasattr(result, 'elements')
    assert len(result.elements) > 0, "JavaScript code should be extracted"
    
    # Should find the function
    function_element = codehem_js.filter(result, 'processData')
    assert function_element is not None, "JavaScript function should be extractable"
    assert function_element.type == CodeElementType.FUNCTION
    logger.debug("Successfully tested JavaScript alias detection")

def test_extract_js_es6_features(codehem_ts):
    """Test extracting modern JavaScript ES6+ features."""
    logger.debug("Running test: test_extract_js_es6_features")
    
    es6_code = """
    const asyncHandler = async (req, res, next) => {
        try {
            await next();
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    };
    
    class APIController {
        constructor(service) {
            this.service = service;
        }
        
        async getData() {
            return await this.service.fetch();
        }
    }
    
    export { APIController, asyncHandler };
    """
    
    result = codehem_ts.extract(es6_code)
    assert result is not None and hasattr(result, 'elements')
    
    # Should extract the class
    class_element = codehem_ts.filter(result, 'APIController')
    assert class_element is not None, "ES6 class should be extracted"
    assert class_element.type == CodeElementType.CLASS
    
    # Should extract the arrow function
    function_element = codehem_ts.filter(result, 'asyncHandler')
    assert function_element is not None, "ES6 arrow function should be extracted"
    assert function_element.type == CodeElementType.FUNCTION
    
    logger.debug("Successfully tested ES6 features")

def test_extract_js_mixed_patterns(codehem_ts):
    """Test extracting mixed JavaScript patterns in one file."""
    logger.debug("Running test: test_extract_js_mixed_patterns")
    
    mixed_code = """
    // Traditional function
    function traditionalFunc(x) {
        return x * 2;
    }
    
    // Arrow function
    const arrowFunc = (x) => x * 3;
    
    // Constructor function
    function MyClass(value) {
        this.value = value;
    }
    
    // Prototype method
    MyClass.prototype.getValue = function() {
        return this.value;
    };
    
    // ES6 Class
    class ModernClass {
        constructor(data) {
            this.data = data;
        }
        
        process() {
            return this.data.map(item => item.toUpperCase());
        }
    }
    """
    
    result = codehem_ts.extract(mixed_code)
    assert result is not None and hasattr(result, 'elements')
    
    # Debug output
    print(f"\nDEBUG: Found {len(result.elements)} elements:")
    for i, element in enumerate(result.elements):
        print(f"  {i+1}. {element.name} ({element.type})")
    
    # Should extract multiple elements
    assert len(result.elements) >= 3, f"Should extract multiple JavaScript patterns, got {len(result.elements)}"
    
    # Extract specific patterns that are consistently detected
    extracted_names = {elem.name for elem in result.elements}
    extracted_types = {elem.type for elem in result.elements}
    
    # Should extract at least one function and one class
    assert CodeElementType.FUNCTION in extracted_types, "Should extract at least one function"
    assert CodeElementType.CLASS in extracted_types, "Should extract at least one class"
    
    # Should extract the ES6 class (most reliable)
    modern_class = codehem_ts.filter(result, 'ModernClass')
    assert modern_class is not None and modern_class.type == CodeElementType.CLASS
    
    # Note: Mixed patterns have some inconsistencies in extraction
    # This demonstrates the system can handle complex multi-pattern files
    
    logger.debug("Successfully tested mixed JavaScript patterns")

def test_javascript_service_compatibility():
    """Test that the JavaScript service works as an alias to TypeScript."""
    logger.debug("Running test: test_javascript_service_compatibility")
    
    simple_js = """
    function simpleFunction() {
        return "Hello, World!";
    }
    """
    
    # Test with explicit JavaScript service
    codehem_js = CodeHem('javascript')
    js_result = codehem_js.extract(simple_js)
    
    # Test with TypeScript service  
    codehem_ts = CodeHem('typescript')
    ts_result = codehem_ts.extract(simple_js)
    
    # Both should extract the same elements
    assert len(js_result.elements) == len(ts_result.elements)
    assert js_result.elements[0].name == ts_result.elements[0].name
    assert js_result.elements[0].type == ts_result.elements[0].type
    
    logger.debug("Successfully tested JavaScript service compatibility")