import unittest
from main import CodeHem
from core.ast_handler import ASTHandler
from core.models import CodeElementsResult, CodeElementType
from tree_sitter import Node

class TestParserRobustness(unittest.TestCase):
    """Test suite for the parser robustness of CodeHem."""
    
    def test_parse_incomplete_python(self):
        """Test parsing incomplete or syntactically incorrect Python code."""
        # Incomplete function
        incomplete_func = """
def incomplete_function(arg1, arg2
    print("This is incomplete")
"""
        # Missing colon
        missing_colon = """
def missing_colon()
    print("Missing colon")
"""
        # Unmatched brackets
        unmatched_brackets = """
def brackets():
    items = [1, 2, 3
    for item in items:
        print(item)
"""
        # Indentation errors
        bad_indent = """
def bad_indent():
    if True:
    print("Bad indentation")
        print("More bad indentation")
"""
        python_hem = CodeHem('python')
        
        # These should not raise exceptions
        try:
            python_hem.extract(incomplete_func)
            python_hem.extract(missing_colon)
            python_hem.extract(unmatched_brackets)
            python_hem.extract(bad_indent)
            self.assertTrue(True)  # If we get here without exceptions, the test passes
        except Exception as e:
            self.fail(f"Parser failed to handle invalid Python code: {str(e)}")
            
    def test_parse_incomplete_typescript(self):
        """Test parsing incomplete or syntactically incorrect TypeScript code."""
        # Incomplete function
        incomplete_func = """
function incompleteFunction(arg1, arg2
    console.log("This is incomplete");
"""
        # Missing braces
        missing_braces = """
function missingBraces()
    console.log("Missing braces");
"""
        # Unmatched brackets
        unmatched_brackets = """
function brackets() {
    const items = [1, 2, 3;
    for (const item of items) {
        console.log(item);
    }
}
"""
        # Improper casing
        bad_case = """
Function BadCase() {
    Console.log("Improper casing");
}
"""
        ts_hem = CodeHem('typescript')
        
        # These should not raise exceptions
        try:
            ts_hem.extract(incomplete_func)
            ts_hem.extract(missing_braces)
            ts_hem.extract(unmatched_brackets)
            ts_hem.extract(bad_case)
            self.assertTrue(True)  # If we get here without exceptions, the test passes
        except Exception as e:
            self.fail(f"Parser failed to handle invalid TypeScript code: {str(e)}")
            
    def test_ast_handler_robustness(self):
        """Test the AST handler directly with various inputs."""
        python_handler = ASTHandler('python')
        ts_handler = ASTHandler('typescript')
        
        # Incomplete code should not crash the parser
        incomplete = "def foo("
        try:
            (root, code_bytes) = python_handler.parse(incomplete)
            self.assertIsInstance(root, Node)
        except Exception as e:
            self.fail(f"Python AST handler failed to parse incomplete code: {str(e)}")
            
        # Malformed TypeScript should not crash the parser
        malformed = "function foo( { return;"
        try:
            (root, code_bytes) = ts_handler.parse(malformed)
            self.assertIsInstance(root, Node)
        except Exception as e:
            self.fail(f"TypeScript AST handler failed to parse malformed code: {str(e)}")
            
    def test_unicode_robustness(self):
        """Test handling of Unicode characters in source code."""
        # Python with Unicode
        python_unicode = """
def unicode_function():
    # Contains Unicode: 你好 (Hello in Chinese)
    message = "你好，世界！"  # Hello, world!
    print(message)
"""
        # TypeScript with Unicode
        ts_unicode = """
function unicodeFunction() {
    // Contains Unicode: こんにちは (Hello in Japanese)
    const message = "こんにちは、世界！";  // Hello, world!
    console.log(message);
}
"""
        python_hem = CodeHem('python')
        ts_hem = CodeHem('typescript')
        
        # Extract elements from code with Unicode
        python_result = python_hem.extract(python_unicode)
        ts_result = ts_hem.extract(ts_unicode)
        
        # Verify elements were extracted
        self.assertIsInstance(python_result, CodeElementsResult)
        self.assertIsInstance(ts_result, CodeElementsResult)
        
        # Find the functions
        python_func = None
        ts_func = None
        
        for element in python_result.elements:
            if element.type == CodeElementType.FUNCTION and element.name == 'unicode_function':
                python_func = element
                
        for element in ts_result.elements:
            if element.type == CodeElementType.FUNCTION and element.name == 'unicodeFunction':
                ts_func = element
                
        self.assertIsNotNone(python_func, "Failed to extract Python function with Unicode")
        self.assertIsNotNone(ts_func, "Failed to extract TypeScript function with Unicode")
            
    def test_mixed_indentation_python(self):
        """Test handling of mixed indentation in Python."""
        mixed_indent = """
def spaces_function():
    print("Indented with spaces")
    if True:
        print("More spaces")

def tabs_function():
	print("Indented with tabs")
	if True:
		print("More tabs")

def mixed_function():
    print("Started with spaces")
	print("Switched to tabs")
    if True:
		print("Tabs inside")
        print("Back to spaces")
"""
        python_hem = CodeHem('python')
        
        # This should parse without exceptions
        try:
            result = python_hem.extract(mixed_indent)
            self.assertIsInstance(result, CodeElementsResult)
            
            # Count functions found
            functions = [e for e in result.elements if e.type == CodeElementType.FUNCTION]
            function_names = [f.name for f in functions]
            
            # We should find at least some of the functions, even with mixed indentation
            self.assertIn('spaces_function', function_names)
            self.assertIn('tabs_function', function_names)
        except Exception as e:
            self.fail(f"Failed to handle mixed indentation: {str(e)}")

if __name__ == '__main__':
    unittest.main()