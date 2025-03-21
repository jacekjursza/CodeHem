"""
Python-specific implementation of the language strategy.
"""
import re
from typing import Tuple, List, Dict, Any, Optional
from tree_sitter import Node
from .language_strategy import LanguageStrategy
from ..models import CodeElementType


class PythonStrategy(LanguageStrategy):
    """
    Python-specific implementation of the language strategy.
    """

    @property
    def language_code(self) -> str:
        return 'python'

    @property
    def file_extensions(self) -> List[str]:
        return ['.py']

    def is_class_definition(self, line: str) -> bool:
        """
        Check if a line of code is a Python class definition.

        Args:
            line: Line of code to check

        Returns:
            True if the line is a class definition, False otherwise
        """
        return bool(re.match('^\\s*class\\s+[A-Za-z_][A-Za-z0-9_]*(\\s*\\(.*\\))?\\s*:', line))

    def is_function_definition(self, line: str) -> bool:
        """
        Check if a line of code is a Python function definition.

        Args:
            line: Line of code to check

        Returns:
            True if the line is a function definition, False otherwise
        """
        return bool(re.match('^\\s*def\\s+[A-Za-z_][A-Za-z0-9_]*\\s*\\(', line))

    def is_method_definition(self, line: str) -> bool:
        """
        Check if a line of code is a Python method definition.

        Args:
            line: Line of code to check

        Returns:
            True if the line is a method definition, False otherwise
        """
        return bool(re.match('^\\s*def\\s+[A-Za-z_][A-Za-z0-9_]*\\s*\\(\\s*(self|cls)\\b', line))

    def extract_method_name(self, method_line: str) -> Optional[str]:
        """
        Extract the method name from a Python method definition line.

        Args:
            method_line: Method definition line

        Returns:
            Method name or None if not found
        """
        match = re.match('^\\s*def\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(', method_line)
        return match.group(1) if match else None

    def extract_class_name(self, class_line: str) -> Optional[str]:
        """
        Extract the class name from a Python class definition line.

        Args:
            class_line: Class definition line

        Returns:
            Class name or None if not found
        """
        match = re.match('^\\s*class\\s+([A-Za-z_][A-Za-z0-9_]*)', class_line)
        return match.group(1) if match else None

    def extract_function_name(self, function_line: str) -> Optional[str]:
        """
        Extract the function name from a Python function definition line.

        Args:
            function_line: Function definition line

        Returns:
            Function name or None if not found
        """
        match = re.match('^\\s*def\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(', function_line)
        return match.group(1) if match else None

    def fix_special_characters(self, content: str, xpath: str) -> Tuple[str, str]:
        """
        Fix special characters in method names and xpaths for Python.

        Args:
            content: Code content
            xpath: XPath string

        Returns:
            Tuple of (updated_content, updated_xpath)
        """
        updated_content = content
        updated_xpath = xpath
        if content:
            pattern = 'def\\s+\\*+([A-Za-z_][A-Za-z0-9_]*)\\*+\\s*\\('
            replacement = 'def \\1('
            if re.search(pattern, content):
                updated_content = re.sub(pattern, replacement, content)
        if xpath:
            method_pattern = '\\*+([A-Za-z_][A-Za-z0-9_]*)\\*+'
            if '.' in xpath:
                (class_name, method_name) = xpath.split('.')
                if '*' in method_name:
                    clean_method_name = re.sub(method_pattern, '\\1', method_name)
                    updated_xpath = f'{class_name}.{clean_method_name}'
            elif '*' in xpath:
                clean_name = re.sub(method_pattern, '\\1', xpath)
                updated_xpath = clean_name
        return (updated_content, updated_xpath)

    def adjust_indentation(self, code: str, indent_level: int) -> str:
        """
        Adjust the indentation of Python code to the specified level.

        Args:
            code: Code to adjust
            indent_level: Target indentation level

        Returns:
            Code with adjusted indentation
        """
        indent_str = ' ' * (4 * indent_level)
        lines = code.splitlines()
        result = []
        for line in lines:
            if line.strip():
                result.append(f'{indent_str}{line.lstrip()}')
            else:
                result.append('')
        return '\n'.join(result)

    def get_default_indentation(self) -> str:
        """
        Get the default indentation string for Python.

        Returns:
            Default indentation string (4 spaces)
        """
        return '    '

    def is_method_of_class(self, method_node: Node, class_name: str, code_bytes: bytes) -> bool:
        """
        Check if a method belongs to a specific Python class.

        Args:
            method_node: Method node
            class_name: Class name to check
            code_bytes: Source code as bytes

        Returns:
            True if the method belongs to the class, False otherwise
        """
        params_node = None
        for child in method_node.children:
            if child.type == 'parameters':
                params_node = child
                break
        if not params_node or not params_node.children:
            return False
        first_param = None
        for child in params_node.children:
            if child.type == 'identifier':
                first_param = child
                break
        if not first_param:
            return False
        if code_bytes[first_param.start_byte:first_param.end_byte].decode('utf8') != 'self':
            return False
        current = method_node
        while current:
            if current.type == 'class_definition':
                for child in current.children:
                    if child.type == 'identifier':
                        class_node_name = code_bytes[child.start_byte:child.end_byte].decode('utf8')
                        return class_node_name == class_name
            current = current.parent
        return False

    def get_content_type(self, content: str) -> str:
        """
        Determine the type of Python content.
        
        Args:
            content: The code content to analyze
            
        Returns:
            Content type from CodeElementType
        """
        if not content or not content.strip():
            return CodeElementType.MODULE.value
            
        lines = content.strip().splitlines()
        if not lines:
            return CodeElementType.MODULE.value
            
        # Check the first non-empty line
        first_line = None
        for line in lines:
            if line.strip():
                first_line = line.strip()
                break
                
        if not first_line:
            return CodeElementType.MODULE.value
            
        if self.is_class_definition(first_line):
            return CodeElementType.CLASS.value
            
        if self.is_method_definition(first_line):
            return CodeElementType.METHOD.value
            
        if self.is_function_definition(first_line):
            return CodeElementType.FUNCTION.value
            
        # Check for import statements
        if re.match(r'^\s*(import|from)', first_line):
            return CodeElementType.IMPORT.value
            
        # Check for properties
        if re.match(r'^\s*@property', first_line) or re.search(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=', first_line):
            return CodeElementType.PROPERTY.value
            
        # Check for decorators
        if first_line.startswith('@'):
            return CodeElementType.META_ELEMENT.value
            
        # Default to MODULE
        return CodeElementType.MODULE.value

    def determine_element_type(self, decorators: List[str], is_method: bool=False) -> str:
        """
        Determine the Python element type based on decorators and context.
        Simplified version: methods are always methods, regardless of decorators.

        Args:
        decorators: List of decorator strings
        is_method: Whether the element is a method

        Returns:
        Element type name from CodeElementType
        """
        if is_method:
            return 'METHOD'
        return 'FUNCTION'

    def _extract_decorator_name(self, decorator: str) -> str:
        """
        Extract decorator name from Python decorator string.

        Args:
            decorator: Decorator string

        Returns:
            Decorator name
        """
        decorator = decorator.strip()
        if decorator.startswith('@'):
            decorator = decorator[1:]
        if '.' in decorator:
            parts = decorator.split('.')
            if len(parts) >= 2 and parts[1].startswith('setter') or parts[1].startswith('deleter'):
                return parts[0]
        return decorator.split('(')[0].strip()