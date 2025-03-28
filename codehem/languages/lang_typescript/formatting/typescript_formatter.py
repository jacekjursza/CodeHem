"""
TypeScript-specific formatter implementation.
"""
import re
from typing import Callable, Dict, Optional
from codehem.core.formatting.formatter import BaseFormatter
from codehem.models.enums import CodeElementType

class TypeScriptFormatter(BaseFormatter):
    """
    TypeScript-specific implementation of the code formatter.
    """

    def __init__(self, indent_size: int=2):
        """Initialize the TypeScript formatter with 2-space indentation by default."""
        super().__init__(indent_size)

    def _get_element_formatter(self, element_type: str) -> Optional[Callable]:
        """Get the formatter function for the specified element type."""
        formatters = {
            CodeElementType.CLASS.value: self.format_class,
            CodeElementType.METHOD.value: self.format_method,
            CodeElementType.FUNCTION.value: self.format_function,
            CodeElementType.INTERFACE.value: self.format_interface,
            CodeElementType.TYPE_ALIAS.value: self.format_type_alias,
            CodeElementType.IMPORT.value: self.format_import,
            CodeElementType.PROPERTY.value: self.format_property
        }
        return formatters.get(element_type)

    def format_class(self, code: str) -> str:
        """Format a TypeScript class definition."""
        return self.dedent(code).strip()

    def format_method(self, code: str) -> str:
        """Format a TypeScript method definition."""
        return self.dedent(code).strip()

    def format_function(self, code: str) -> str:
        """Format a TypeScript function definition."""
        return self.dedent(code).strip()
        
    def format_interface(self, code: str) -> str:
        """Format a TypeScript interface definition."""
        return self.dedent(code).strip()
        
    def format_type_alias(self, code: str) -> str:
        """Format a TypeScript type alias definition."""
        return self.dedent(code).strip()
        
    def format_import(self, code: str) -> str:
        """Format TypeScript import statements."""
        return self.dedent(code).strip()
        
    def format_property(self, code: str) -> str:
        """Format a TypeScript property."""
        return self.dedent(code).strip()
        
    def format_code(self, code: str) -> str:
        """
        Format TypeScript code according to standard conventions.
        
        Args:
            code: TypeScript code to format
            
        Returns:
            Formatted TypeScript code
        """
        code = code.strip()
        code = self._fix_spacing(code)
        return code

    def _fix_spacing(self, code: str) -> str:
        """
        Fix spacing issues in TypeScript code.
        
        Args:
            code: TypeScript code to fix
            
        Returns:
            Code with fixed spacing
        """
        # Fix spacing around operators
        code = re.sub(r'([^\s=!<>])=([^\s=])', r'\1 = \2', code)
        code = re.sub(r'([^\s!<>])==[^\s]', r'\1 == \2', code)
        code = re.sub(r'([^\s])([+\-*/%])', r'\1 \2', code)
        
        # Fix spacing after commas
        code = re.sub(r',([^\s])', r', \1', code)
        
        # Fix spacing around colons in type annotations
        code = re.sub(r'([^\s]):([^\s])', r'\1: \2', code)
        
        # Remove excess blank lines
        code = re.sub(r'\n\s*\n\s*\n', r'\n\n', code)
        
        return code