"""
Python-specific formatter implementation.
"""
import re
from typing import Callable, Optional

from codehem.core.formatting.indent_formatter import IndentFormatter
from codehem.models.enums import CodeElementType


class PythonFormatter(IndentFormatter):
    """
    Python-specific implementation of the code formatter.
    """

    def __init__(self, indent_size: int=4):
        """
        Initialize the Python formatter.
        
        Args:
            indent_size: Number of spaces per indentation level (default: 4)
        """
        super().__init__(indent_size)

    def _get_element_formatter(self, element_type: str) -> Optional[Callable]:
        """
        Get the formatter function for the specified element type.
        
        Args:
            element_type: Element type
            
        Returns:
            Formatter function or None if no specific formatter
        """
        formatters = {
            CodeElementType.CLASS.value: self.format_class, 
            CodeElementType.METHOD.value: self.format_method, 
            CodeElementType.FUNCTION.value: self.format_function, 
            CodeElementType.PROPERTY.value: self.format_property, 
            CodeElementType.PROPERTY_GETTER.value: self.format_property_getter, 
            CodeElementType.PROPERTY_SETTER.value: self.format_property_setter, 
            CodeElementType.STATIC_PROPERTY.value: self.format_static_property, 
            CodeElementType.IMPORT.value: self.format_import
        }
        return formatters.get(element_type)

    def format_code(self, code: str) -> str:
        """
        Format Python code according to PEP 8-like standards.
        
        Args:
            code: Python code to format
            
        Returns:
            Formatted Python code
        """
        code = code.strip()
        code = self._fix_spacing(code)
        return code

    def format_class(self, code: str) -> str:
        """
        Format a Python class definition.
        
        Args:
            code: Class code to format
            
        Returns:
            Formatted class code
        """
        dedented = self.dedent(code).strip()
        lines = dedented.splitlines()
        if not lines:
            return ''
        result = []
        class_line_idx = next((i for (i, line) in enumerate(lines) if line.strip().startswith('class ')), 0)
        for i in range(class_line_idx):
            result.append(lines[i])
        result.append(lines[class_line_idx])
        in_method = False
        in_docstring = False
        docstring_delimiter = None
        for i in range(class_line_idx + 1, len(lines)):
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                result.append('')
                continue
            if in_docstring:
                if stripped.endswith(docstring_delimiter):
                    in_docstring = False
                result.append(f'{self.indent_string}{line}')
                continue
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = True
                docstring_delimiter = stripped[:3]
                result.append(f'{self.indent_string}{line}')
                continue
            if stripped.startswith('def ') or stripped.startswith('@'):
                in_method = True if stripped.startswith('def ') else False
                result.append(f'{self.indent_string}{stripped}')
                continue
            if in_method:
                result.append(f'{self.indent_string * 2}{stripped}')
            else:
                result.append(f"{self.indent_string}{stripped}")
        return "\n".join(result)

    def format_method(self, code: str) -> str:
        """
        Format a Python method definition with proper indentation.

        Args:
            code: Method code to format

        Returns:
            Formatted method code
        """
        # First ensure the code is properly dedented
        dedented = self.dedent(code).strip()
        lines = dedented.splitlines()
        if not lines:
            return ""

        result = []
        method_line_idx = next(
            (i for i, line in enumerate(lines) if line.strip().startswith("def ")), 0
        )

        # Add decorators and method definition without extra indentation
        for i in range(method_line_idx + 1):
            result.append(lines[i])

        # Add method body with single level of indentation
        for i in range(method_line_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                result.append("")
                continue
            result.append(f'{self.indent_string}{line.strip()}')

        return '\n'.join(result)

    def format_function(self, code: str) -> str:
        """
        Format a Python function definition.
        Delegates to format_method as they're essentially the same in Python.
        
        Args:
            code: Function code to format
            
        Returns:
            Formatted function code
        """
        return self.format_method(code)

    def format_property(self, code: str) -> str:
        """
        Format a Python property.
        
        Args:
            code: Property code to format
            
        Returns:
            Formatted property code
        """
        if '@property' in code:
            return self.format_property_getter(code)
        lines = self.dedent(code).strip().splitlines()
        if not lines:
            return ''
        return '\n'.join(lines)

    def format_property_getter(self, code: str) -> str:
        """
        Format a Python property getter.
        
        Args:
            code: Property getter code to format
            
        Returns:
            Formatted property getter code
        """
        code = self.dedent(code).strip()
        if not code.startswith('@property'):
            code = '@property\n' + code
        return self.format_method(code)

    def format_property_setter(self, code: str) -> str:
        """
        Format a Python property setter.
        
        Args:
            code: Property setter code to format
            
        Returns:
            Formatted property setter code
        """
        lines = self.dedent(code).strip().splitlines()
        if not lines:
            return ''
        property_name = None
        for line in lines:
            if line.strip().startswith('def '):
                match = re.match('def\\s+(\\w+)', line.strip())
                if match:
                    property_name = match.group(1)
                break
        if property_name:
            setter_decorator = f'@{property_name}.setter'
            if lines[0].strip() != setter_decorator:
                lines.insert(0, setter_decorator)
        return self.format_method('\n'.join(lines))

    def format_static_property(self, code: str) -> str:
        """
        Format a Python static property (class variable).
        
        Args:
            code: Static property code to format
            
        Returns:
            Formatted static property code
        """
        return self.dedent(code).strip()

    def format_import(self, code: str) -> str:
        """
        Format Python import statements.
        
        Args:
            code: Import statements to format
            
        Returns:
            Formatted import statements
        """
        lines = self.dedent(code).strip().splitlines()
        return '\n'.join((line.strip() for line in lines if line.strip()))
