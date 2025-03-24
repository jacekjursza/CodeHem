"""
Factory for creating code finders that use extractor under the hood.
"""


import re
from typing import Tuple, Optional, List
from codehem.extractor import Extractor

class FinderFacade:
    """
    A façade that provides the finder API expected by handlers but uses the extractor under the hood.
    """
    
    def __init__(self, language_code: str):
        self.language_code = language_code
        self.extractor = Extractor(language_code)
    
    def find_function(self, code: str, function_name: str) -> Tuple[int, int]:
        """Find a function and return its line range."""
        functions = self.extractor.extract_functions(code)
        for func in functions:
            if func.get('name') == function_name:
                return self._get_line_range(func)
        return (0, 0)
    
    def find_class(self, code: str, class_name: str) -> Tuple[int, int]:
        """Find a class and return its line range."""
        classes = self.extractor.extract_classes(code)
        for cls in classes:
            if cls.get('name') == class_name:
                return self._get_line_range(cls)
        return (0, 0)
    
    def find_method(self, code: str, class_name: str, method_name: str) -> Tuple[int, int]:
        """Find a method in a class and return its line range."""
        methods = self.extractor.extract_methods(code, class_name)
        for method in methods:
            if method.get('name') == method_name and method.get('class_name') == class_name:
                return self._get_line_range(method)
        return (0, 0)
    
    def find_property(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        """Find a property in a class and return its line range."""
        # The extractor might not have a direct method for extracting properties,
        # so we extract methods and filter them
        methods = self.extractor.extract_methods(code, class_name)
        for method in methods:
            if method.get('name') == property_name and (
                method.get('type') in ('property', 'property_getter', 'property_setter')):
                return self._get_line_range(method)
        return (0, 0)
    
    def find_property_setter(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        """Find a property setter in a class."""
        methods = self.extractor.extract_methods(code, class_name)
        for method in methods:
            if method.get('name') == property_name and method.get('type') == 'property_setter':
                return self._get_line_range(method)
        return (0, 0)
    
    def find_property_and_setter(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        """Find both a property and its setter."""
        getter_range = self.find_property(code, class_name, property_name)
        setter_range = self.find_property_setter(code, class_name, property_name)
        
        if getter_range == (0, 0) and setter_range == (0, 0):
            return (0, 0)
        
        if getter_range == (0, 0):
            return setter_range
        
        if setter_range == (0, 0):
            return getter_range
        
        start_line = min(getter_range[0], setter_range[0])
        end_line = max(getter_range[1], setter_range[1])
        return (start_line, end_line)
    
    def find_imports_section(self, code: str) -> Tuple[int, int]:
        """Find the imports section in a file."""
        imports = self.extractor.extract_imports(code)
        if imports:
            # For imports, we need to check if there's a combined import section
            if len(imports) == 1 and imports[0].get('name') == 'imports':
                # Already a combined section
                return self._get_line_range(imports[0])
            
            # Multiple imports, find the range from first to last
            ranges = [self._get_line_range(imp) for imp in imports]
            start_line = min(r[0] for r in ranges if r[0] > 0)
            end_line = max(r[1] for r in ranges if r[1] > 0)
            if start_line > 0 and end_line > 0:
                return (start_line, end_line)
        return (0, 0)
    
    def find_properties_section(self, code: str, class_name: str) -> Tuple[int, int]:
        """Find the properties section in a class."""
        # Look for "__init__" method and find properties assigned there
        (class_start, class_end) = self.find_class(code, class_name)
        if class_start == 0:
            return (0, 0)
            
        methods = self.extractor.extract_methods(code, class_name)
        for method in methods:
            if method.get('name') == '__init__':
                return self._get_line_range(method)
        
        # No init method found, just return the start of the class
        return (class_start, class_start)
    
    def find_class_for_method(self, method_name: str, code: str) -> Optional[str]:
        """Find the class containing a method."""
        classes = self.extractor.extract_classes(code)
        for cls in classes:
            class_name = cls.get('name')
            methods = self.extractor.extract_methods(code, class_name)
            for method in methods:
                if method.get('name') == method_name:
                    return class_name
        return None
    
    def has_class_method_indicator(self, method_node, code_bytes) -> bool:
        """Check if a method has class method indicators."""
        # This is a placeholder implementation since we don't have the direct equivalent
        return False
    
    def is_correct_syntax(self, plain_text: str) -> bool:
        """Check if text has correct syntax for this language."""
        # This is a simplified implementation that just checks if there's any valid code
        if not plain_text.strip():
            return False
        try:
            # Try to extract something, if it succeeds, syntax is likely correct
            result = self.extractor.extract_any(plain_text, 'function')
            return bool(result)
        except Exception:
            return False
            
    def content_looks_like_class_definition(self, content: str) -> bool:
        """Check if content looks like a class definition."""

        return bool(re.search(r'class\s+\w+', content))
    
    def _get_line_range(self, element: dict) -> Tuple[int, int]:
        """Extract start and end line from an element."""
        range_data = element.get('range', {})
        start = range_data.get('start', {})
        end = range_data.get('end', {})
        start_line = start.get('line', 0) + 1  # Convert to 1-indexed
        end_line = end.get('line', 0) + 1      # Convert to 1-indexed
        return (start_line, end_line)

def get_code_finder(language_code: str) -> FinderFacade:
    """Get a code finder for the specified language."""
    return FinderFacade(language_code)