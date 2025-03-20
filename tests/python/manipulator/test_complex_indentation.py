import unittest
from core.manipulator.factory import get_code_manipulator

class TestPythonIndentationPreservation(unittest.TestCase):
    
    def setUp(self):
        self.manipulator = get_code_manipulator('python')
        
    def test_nested_function_indentation(self):
        original_code = '''
def outer_function(param1):
    """Outer function docstring."""
    def inner_function(inner_param):
        """Inner function docstring."""
        if inner_param > 0:
            if inner_param > 10:
                return "Large value"
            else:
                return "Normal value"
        else:
            return "Negative value"
    
    result = inner_function(param1)
    return result
'''
        
        new_function = '''
def outer_function(param1, param2=None):
    """Updated outer function docstring."""
    def inner_function(inner_param):
        """Inner function docstring."""
        if inner_param > 0:
            if inner_param > 10:
                return "Large value: " + str(inner_param)
            else:
                for i in range(inner_param):
                    if i % 2 == 0:
                        print(f"Even: {i}")
                    else:
                        print(f"Odd: {i}")
                return "Normal value"
        else:
            return "Negative value"
    
    result = inner_function(param1)
    if param2:
        result += str(param2)
    return result
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'outer_function', new_function)
        
        # Verify indentation is preserved
        self.assertIn('    def inner_function(inner_param):', modified_code)
        self.assertIn('        """Inner function docstring."""', modified_code)
        self.assertIn('            if inner_param > 10:', modified_code)
        self.assertIn('                return "Large value: " + str(inner_param)', modified_code)
        self.assertIn('                    if i % 2 == 0:', modified_code)
        self.assertIn('                        print(f"Even: {i}")', modified_code)
    
    def test_mixed_indentation_styles(self):
        # This test uses a mix of tabs and spaces in the original code
        original_code = '''
class MixedIndentClass:
    def method_with_tabs(self):
\t\t"""This method uses tabs for indentation."""
\t\tfor i in range(10):
\t\t\tif i > 5:
\t\t\t\treturn i
\t\treturn 0
    
    def method_with_spaces(self):
        """This method uses spaces for indentation."""
        for i in range(10):
            if i > 5:
                return i
        return 0
'''
        
        new_method = '''
def method_with_tabs(self):
    """Updated method now using spaces."""
    for i in range(10):
        if i > 5:
            print(f"Greater than 5: {i}")
            return i
    return 0
'''
        
        modified_code = self.manipulator.replace_method(original_code, 'MixedIndentClass', 'method_with_tabs', new_method)
        
        # Verify the method was updated properly with consistent indentation
        self.assertIn('    def method_with_tabs(self):', modified_code)
        self.assertIn('        """Updated method now using spaces."""', modified_code)
        self.assertIn('        for i in range(10):', modified_code)
        self.assertIn('            if i > 5:', modified_code)
        self.assertIn('                print(f"Greater than 5: {i}")', modified_code)
        
        # Verify the other method remains unchanged
        self.assertIn('    def method_with_spaces(self):', modified_code)
        self.assertIn('        """This method uses spaces for indentation."""', modified_code)
    
    def test_irregular_indentation_patterns(self):
        original_code = '''
def irregular_function():
  # 2 spaces
  if True:
      # 4 spaces
      for i in range(10):
        # back to 2 spaces
        print(i)
    # unexpected 4 spaces
    return True
'''
        
        new_function = '''
def irregular_function():
    # Now with consistent 4 spaces
    if True:
        for i in range(10):
            print(i)
            if i % 2 == 0:
                print("Even")
        return True
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'irregular_function', new_function)
        
        # Verify the function was fixed with consistent indentation
        self.assertIn('def irregular_function():', modified_code)
        self.assertIn('    # Now with consistent 4 spaces', modified_code)
        self.assertIn('    if True:', modified_code)
        self.assertIn('        for i in range(10):', modified_code)
        self.assertIn('            print(i)', modified_code)
        self.assertIn('            if i % 2 == 0:', modified_code)
        self.assertIn('                print("Even")', modified_code)
        self.assertIn('        return True', modified_code)
    
    def test_deep_nesting_with_complex_structures(self):
        original_code = '''
class OuterClass:
    class NestedClass:
        def nested_method(self, param):
            def local_function(x):
                if x > 0:
                    return [
                        i * 2
                        for i in range(x)
                        if i % 2 == 0
                    ]
                else:
                    return []
            
            result = local_function(param)
            return result
'''
        
        new_method = '''
def nested_method(self, param, extra_param=None):
    def local_function(x, modifier=1):
        if x > 0:
            return [
                i * modifier
                for i in range(x)
                if i % 2 == 0
            ]
        else:
            return []
    
    result = local_function(param, modifier=2 if extra_param else 1)
    
    # Add complex dictionary literal with specific indentation
    metadata = {
        "param": param,
        "extra_param": extra_param,
        "computed_values": {
            "first": local_function(param)[0] if param > 0 and len(local_function(param)) > 0 else None,
            "count": len(result)
        }
    }
    
    return (result, metadata)
'''
        
        modified_code = self.manipulator.replace_method(original_code, 'OuterClass.NestedClass', 'nested_method', new_method)
        
        # Verify complex indentation is preserved
        self.assertIn('        def nested_method(self, param, extra_param=None):', modified_code)
        self.assertIn('            def local_function(x, modifier=1):', modified_code)
        self.assertIn('                if x > 0:', modified_code)
        self.assertIn('                    return [', modified_code)
        self.assertIn('                        i * modifier', modified_code)
        self.assertIn('                        for i in range(x)', modified_code)
        self.assertIn('                        if i % 2 == 0', modified_code)
        self.assertIn('                    ]', modified_code)
        self.assertIn('                else:', modified_code)
        self.assertIn('                    return []', modified_code)
        
        # Verify dictionary literal indentation
        self.assertIn('            metadata = {', modified_code)
        self.assertIn('                "param": param,', modified_code)
        self.assertIn('                "computed_values": {', modified_code)
        self.assertIn('                    "first": local_function(param)[0]', modified_code)
        self.assertIn('                }', modified_code)
        self.assertIn('            }', modified_code)

if __name__ == '__main__':
    unittest.main()