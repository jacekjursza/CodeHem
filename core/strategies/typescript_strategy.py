"""
TypeScript-specific implementation of the language strategy.
"""
import re
from typing import Tuple, List, Dict, Any, Optional
from tree_sitter import Node
from .language_strategy import LanguageStrategy

class TypeScriptStrategy(LanguageStrategy):
    """
    TypeScript-specific implementation of the language strategy.
    """

    @property
    def language_code(self) -> str:
        return 'typescript'

    @property
    def file_extensions(self) -> List[str]:
        return ['.ts', '.tsx', '.js', '.jsx']

    def is_class_definition(self, line: str) -> bool:
        """
        Check if a line of code is a TypeScript class definition.

        Args:
            line: Line of code to check

        Returns:
            True if the line is a class definition, False otherwise
        """
        return bool(re.match('^\\s*(export\\s+)?(abstract\\s+)?class\\s+[A-Za-z_][A-Za-z0-9_]*', line))

    def is_function_definition(self, line: str) -> bool:
        """
        Check if a line of code is a TypeScript function definition.

        Args:
            line: Line of code to check

        Returns:
            True if the line is a function definition, False otherwise
        """
        return bool(re.match('^\\s*(export\\s+)?(function\\s+|async\\s+function\\s+)[A-Za-z_][A-Za-z0-9_]*\\s*\\(', line))

    def is_method_definition(self, line: str) -> bool:
        """
        Check if a line of code is a TypeScript method definition.

        Args:
            line: Line of code to check

        Returns:
            True if the line is a method definition, False otherwise
        """
        return bool(re.match('^\\s*(public|private|protected|static|async)?\\s*[A-Za-z_][A-Za-z0-9_]*\\s*\\(', line))

    def extract_method_name(self, method_line: str) -> Optional[str]:
        """
        Extract the method name from a TypeScript method definition line.

        Args:
            method_line: Method definition line

        Returns:
            Method name or None if not found
        """
        match = re.match('^\\s*(public|private|protected|static|async)?\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\(', method_line)
        return match.group(2) if match else None

    def extract_class_name(self, class_line: str) -> Optional[str]:
        """
        Extract the class name from a TypeScript class definition line.

        Args:
            class_line: Class definition line

        Returns:
            Class name or None if not found
        """
        match = re.match('^\\s*(export\\s+)?(abstract\\s+)?class\\s+([A-Za-z_][A-Za-z0-9_]*)', class_line)
        return match.group(3) if match else None

    def extract_function_name(self, function_line: str) -> Optional[str]:
        """
        Extract the function name from a TypeScript function definition line.

        Args:
            function_line: Function definition line

        Returns:
            Function name or None if not found
        """
        match = re.match('^\\s*(export\\s+)?(function\\s+|async\\s+function\\s+)([A-Za-z_][A-Za-z0-9_]*)\\s*\\(', function_line)
        return match.group(3) if match else None

    def fix_special_characters(self, content: str, xpath: str) -> Tuple[str, str]:
        """
        Fix special characters in method names and xpaths for TypeScript.

        Args:
            content: Code content
            xpath: XPath string

        Returns:
            Tuple of (updated_content, updated_xpath)
        """
        updated_content = content
        updated_xpath = xpath
        if content:
            pattern = 'function\\s+\\*+([A-Za-z_][A-Za-z0-9_]*)\\*+\\s*\\('
            replacement = 'function \\1('
            if re.search(pattern, content):
                updated_content = re.sub(pattern, replacement, content)
            method_pattern = '(public|private|protected|static|async)?\\s*\\*+([A-Za-z_][A-Za-z0-9_]*)\\*+\\s*\\('
            method_replacement = '\\1 \\2('
            if re.search(method_pattern, content):
                updated_content = re.sub(method_pattern, method_replacement, updated_content)
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
        Adjust the indentation of TypeScript code to the specified level.

        Args:
            code: Code to adjust
            indent_level: Target indentation level

        Returns:
            Code with adjusted indentation
        """
        indent_str = ' ' * (2 * indent_level)
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
        Get the default indentation string for TypeScript.

        Returns:
            Default indentation string (2 spaces)
        """
        return '  '

    def is_method_of_class(self, method_node: Node, class_name: str, code_bytes: bytes) -> bool:
        """
        Check if a method belongs to a specific TypeScript class.

        Args:
        method_node: Method node
        class_name: Class name to check
        code_bytes: Source code as bytes

        Returns:
        True if the method belongs to the class, False otherwise
        """
        if method_node is None:
            return False
        current = method_node
        while current:
            if current.type == 'class_declaration':
                for child in current.children:
                    if child.type == 'identifier':
                        class_node_name = code_bytes[child.start_byte:child.end_byte].decode('utf8')
                        return class_node_name == class_name
            elif current.type == 'class_body':
                parent_class = current.parent
                if parent_class and parent_class.type == 'class_declaration':
                    for child in parent_class.children:
                        if child.type == 'identifier':
                            class_node_name = code_bytes[child.start_byte:child.end_byte].decode('utf8')
                            return class_node_name == class_name
            current = current.parent
        return False

    def determine_element_type(self, decorators: List[str], is_method: bool = False) -> str:
        """
        Determine the TypeScript element type based on decorators and context.

        Args:
            decorators: List of decorator strings
            is_method: Whether the element is a method

        Returns:
            Element type name from CodeElementType
        """
        if is_method:
            # Check for getter/setter
            for decorator in decorators:
                if '@get ' in decorator or decorator.startswith('@get '):
                    return "PROPERTY"
            return "METHOD"
        return "FUNCTION"

    def _extract_decorator_name(self, decorator: str) -> str:
        """
        Extract decorator name from TypeScript decorator string.

        Args:
            decorator: Decorator string

        Returns:
            Decorator name
        """
        decorator = decorator.strip()
        if decorator.startswith('@'):
            decorator = decorator[1:]
        return decorator.split('(')[0].strip()