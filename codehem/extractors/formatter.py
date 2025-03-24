"""
Code formatter for extracted code elements.
"""
from typing import Dict, List, Optional, Any
import re

class CodeFormatter:
    """Formatter for extracted code elements."""
    
    def __init__(self, language_code: str):
        self.language_code = language_code
        self.formatters = {
            'python': self._format_python,
            'javascript': self._format_javascript,
            'typescript': self._format_typescript
        }
        
    def format(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a code element to ensure proper indentation and style.
        
        Args:
            element: The code element to format
            
        Returns:
            Formatted code element
        """
        formatter = self.formatters.get(self.language_code, self._format_default)
        formatted = formatter(element)
        return formatted
        
    def _format_python(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Format Python code."""
        element_type = element.get('type')
        content = element.get('content', '')
        
        if element_type == 'method':
            # Ensure method has proper indentation (4 spaces per level)
            lines = content.splitlines()
            if lines:
                # Determine the base indentation level
                base_indent = self._get_indentation(lines[0])
                
                # Format each line with consistent indentation
                formatted_lines = []
                for line in lines:
                    line_indent = self._get_indentation(line)
                    relative_indent = max(0, line_indent - base_indent)
                    formatted_indent = ' ' * 4 * (relative_indent // 4)
                    formatted_line = formatted_indent + line.lstrip()
                    formatted_lines.append(formatted_line)
                
                element['content'] = '\n'.join(formatted_lines)
                
        elif element_type in ('function', 'class'):
            # Similar formatting for functions and classes
            # ... implementation similar to method formatting
            pass
            
        return element
        
    def _format_javascript(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Format JavaScript code."""
        # Similar to Python formatting but with different style conventions
        return element
        
    def _format_typescript(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Format TypeScript code."""
        # Similar to JavaScript formatting but with TypeScript specifics
        return element
        
    def _format_default(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Default formatter for unsupported languages."""
        return element
        
    def _get_indentation(self, line: str) -> int:
        """Get the indentation level of a line (number of leading spaces)."""
        return len(line) - len(line.lstrip())