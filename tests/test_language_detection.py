import unittest
from codehem.main import CodeHem
from codehem.core.finder import get_code_finder
from codehem.core.finder.lang.python_code_finder import PythonCodeFinder
from codehem.core.finder import TypeScriptCodeFinder

class TestLanguageDetection(unittest.TestCase):
    """Test suite for the language detection capabilities of CodeHem."""

    def test_simple_language_detection(self):
        """Test detection of clear Python and TypeScript code."""
        python_code = """
def hello_world():
    print("Hello, world!")
    
class MyClass:
    def __init__(self):
        self.value = 42
"""
        ts_code = """
function helloWorld() {
    console.log("Hello, world!");
}

class MyClass {
    private value: number = 42;
    
    constructor() {
        this.setupValue();
    }
    
    private setupValue(): void {
        this.value = 42;
    }
}
"""
        python_hem = CodeHem.from_raw_code(python_code)
        ts_hem = CodeHem.from_raw_code(ts_code)
        
        self.assertEqual(python_hem.language_code, 'python')
        self.assertEqual(ts_hem.language_code, 'typescript')
        
    def test_language_detection_with_minimal_code(self):
        """Test detection with minimal code snippets."""
        python_minimal = "def foo(): pass"
        ts_minimal = "function foo() {}"
        
        python_hem = CodeHem.from_raw_code(python_minimal)
        ts_hem = CodeHem.from_raw_code(ts_minimal)
        
        self.assertEqual(python_hem.language_code, 'python')
        self.assertEqual(ts_hem.language_code, 'typescript')
        
    def test_language_detection_with_ambiguous_code(self):
        """Test detection with potentially ambiguous code."""
        # This could be interpreted as either language
        ambiguous_code = """
// A function
function process(data) {
    // Implementation
}
"""
        # Try to detect - should pick one language consistently
        hem = CodeHem.from_raw_code(ambiguous_code)
        self.assertIn(hem.language_code, ['python', 'typescript'])
        
        # Ensure consistency - should return same language on repeated calls
        hem2 = CodeHem.from_raw_code(ambiguous_code)
        self.assertEqual(hem.language_code, hem2.language_code)
        
    def test_empty_code_detection(self):
        """Test detection with empty or whitespace-only code."""
        empty = ""
        whitespace = "   \n\t\n   "
        
        # Default to Python for empty content
        empty_hem = CodeHem.from_raw_code(empty)
        whitespace_hem = CodeHem.from_raw_code(whitespace)
        
        self.assertEqual(empty_hem.language_code, "python")
        self.assertEqual(whitespace_hem.language_code, "python")

        
    def test_detection_with_mixed_characteristics(self):
        """Test detection with code having characteristics of multiple languages."""
        # Has both Python features (def with :) and JS features (var, ;)
        mixed_code = """
def function_name():
    var x = 42;
    return x;
"""
        finder_py = PythonCodeFinder()
        finder_ts = TypeScriptCodeFinder()
        
        # Both finders might claim they can handle it
        can_handle_py = finder_py.can_handle(mixed_code)
        can_handle_ts = finder_ts.can_handle(mixed_code)
        
        # But CodeHem should make a consistent choice
        hem = CodeHem.from_raw_code(mixed_code)
        self.assertIn(hem.language_code, ['python', 'typescript'])
        
        # Print diagnostics about why it chose this language
        print(f"\nDetected language: {hem.language_code}")
        print(f"Python confidence: {finder_py.can_handle(mixed_code)}")
        print(f"TypeScript confidence: {finder_ts.can_handle(mixed_code)}")
        
    def test_detection_prioritization(self):
        """Test that strong indicators properly outweigh weak ones."""
        # Strong Python indicator (def with :) with weak TS indicators (;)
        python_priority = """
def main():
    print("Hello");
    return 42;
"""
        # Strong TS indicator (function with {}) with weak Python indicators (#)
        ts_priority = """
# This looks like Python
function main() {
    # But it's actually TypeScript with Python-like comments
    console.log("Hello");
}
"""
        python_hem = CodeHem.from_raw_code(python_priority)
        ts_hem = CodeHem.from_raw_code(ts_priority)
        
        self.assertEqual(python_hem.language_code, 'python')
        self.assertEqual(ts_hem.language_code, 'typescript')
        
    def test_file_extension_detection(self):
        """Test language detection from file extensions."""
        py_hem = CodeHem.from_file_extension('.py')
        js_hem = CodeHem.from_file_extension('.js') 
        ts_hem = CodeHem.from_file_extension('.ts')
        tsx_hem = CodeHem.from_file_extension('.tsx')

        print(f" {py_hem.language_code} /rr {js_hem.language_code} /rr {ts_hem.language_code} /rr {tsx_hem.language_code}")

        self.assertEqual(py_hem.language_code, 'python')
        self.assertEqual(js_hem.language_code, 'typescript')  # JS uses TS finder
        self.assertEqual(ts_hem.language_code, 'typescript')
        self.assertEqual(tsx_hem.language_code, 'typescript')  # Should handle TSX too
        
        # Test invalid extension
        with self.assertRaises(ValueError):
            CodeHem.from_file_extension('.invalid')

    def test_can_handle_methods(self):
        """Test the can_handle methods of finders directly."""
        python_finder = get_code_finder('python')
        ts_finder = get_code_finder('typescript')
        
        # Clear Python code
        self.assertTrue(python_finder.can_handle("def foo(): pass"))
        # Clear TypeScript code  
        self.assertTrue(ts_finder.can_handle("function foo() {}"))
        
        # Python finder should reject clear TypeScript
        self.assertFalse(python_finder.can_handle("const x: number = 42;"))
        # TypeScript finder should reject clear Python
        self.assertFalse(ts_finder.can_handle("def foo():\n    return 42"))

if __name__ == '__main__':
    unittest.main()