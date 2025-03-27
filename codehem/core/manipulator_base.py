"""
Base manipulator for standardizing manipulation across languages.
"""
import re
from typing import Tuple, Optional, Dict, Any
from codehem.models.enums import CodeElementType

class ManipulatorBase:
    """Base class for all language-specific manipulators."""
    
    LANGUAGE_CODE = ''
    ELEMENT_TYPE = None
    
    def __init__(self, language_code=None, element_type=None):
        """Initialize the manipulator."""
        self.language_code = language_code or self.LANGUAGE_CODE
        self.element_type = element_type or self.ELEMENT_TYPE
        
        # Don't create extraction service here - will be created on demand
        self._extraction_service = None
    
    @property
    def extraction_service(self):
        """Get extraction service, creating it on demand to avoid circular dependencies."""
        if self._extraction_service is None:
            # Import here to avoid circular imports
            from codehem.core.extraction import ExtractionService
            self._extraction_service = ExtractionService(self.language_code)
        return self._extraction_service
    
    def format_element(self, element_code: str, indent_level: int=0) -> str:
        """Format a code element with proper indentation."""
        indent = ' ' * (self.get_indent_size() * indent_level)
        return self.apply_indentation(element_code.strip(), indent)
    
    def find_element(self, code: str, element_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find an element in the code."""
        if not self.element_type:
            return (0, 0)
            
        return self.extraction_service.find_element(
            code, self.element_type.value, element_name, parent_name
        )
    
    def replace_element(self, original_code: str, element_name: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Replace an element in the code."""
        start_line, end_line = self.find_element(original_code, element_name, parent_name)
        
        # If not found, add instead
        if start_line == 0 and end_line == 0:
            return self.add_element(original_code, new_element, parent_name)
            
        # Format the new content
        formatted_element = self.format_element(
            new_element, self.get_element_indent_level(original_code, start_line, parent_name)
        )
        
        # Replace the element
        return self.replace_lines(original_code, start_line, end_line, formatted_element)
    
    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add an element to the code."""
        # Default implementation - will be overridden by language-specific implementations
        return original_code
    
    def remove_element(self, original_code: str, element_name: str, parent_name: Optional[str]=None) -> str:
        """Remove an element from the code."""
        start_line, end_line = self.find_element(original_code, element_name, parent_name)
        if start_line == 0 and end_line == 0:
            return original_code
            
        return self.replace_lines(original_code, start_line, end_line, '')
    
    def replace_lines(self, original_code: str, start_line: int, end_line: int, new_content: str) -> str:
        """Replace lines between start_line and end_line with new_content."""
        if start_line <= 0 or end_line < start_line:
            return original_code
            
        lines = original_code.splitlines()
        if start_line > len(lines):
            return original_code
            
        result = []
        result.extend(lines[:start_line - 1])
        result.extend(new_content.splitlines())
        result.extend(lines[end_line:])
        
        return '\n'.join(result)
    
    def get_element_indent_level(self, code: str, element_line: int, parent_name: Optional[str]=None) -> int:
        """Get the indentation level for an element."""
        indent_level = 0
        
        if parent_name:
            # For elements inside a class, add one level of indentation
            indent_level += 1
            
        return indent_level
    
    def get_indent_size(self) -> int:
        """Get the indentation size for this language."""
        # Python uses 4 spaces, TypeScript/JavaScript usually uses 2
        if self.language_code == 'python':
            return 4
        return 2
    
    @staticmethod
    def get_indentation(line: str) -> str:
        """Extract indentation from a line."""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''
    
    @staticmethod
    def apply_indentation(content: str, indent: str) -> str:
        """Apply consistent indentation to a block of content."""
        lines = content.splitlines()
        result = []
        
        for line in lines:
            if line.strip():
                result.append(f'{indent}{line.lstrip()}')
            else:
                result.append('')
                
        return '\n'.join(result)