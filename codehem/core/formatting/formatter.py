"""
Base formatter class for CodeHem.
"""
import re
import textwrap
from typing import Optional, Callable, Dict

class BaseFormatter:
    """Base class for code formatters."""

    def __init__(self, indent_size: int = 4):
        """
        Initialize the formatter.
        
        Args:
            indent_size: Number of spaces per indentation level
        """
        self.indent_size = indent_size
        self.indent_string = ' ' * indent_size

    def format_element(self, element_type: str, code: str) -> str:
        """
        Format a code element of the specified type.
        
        Args:
            element_type: Type of the element to format
            code: Code to format
            
        Returns:
            Formatted code
        """
        formatter = self._get_element_formatter(element_type)
        if formatter:
            return formatter(code)
        return self.format_code(code)

    def _get_element_formatter(self, element_type: str) -> Optional[Callable]:
        """
        Get the formatter function for the specified element type.
        Override this in language-specific formatters.
        
        Args:
            element_type: Element type
            
        Returns:
            Formatter function or None if no specific formatter
        """
        return None

    def format_code(self, code: str) -> str:
        """
        Format code according to language standards.
        Override this in language-specific formatters.
        
        Args:
            code: Code to format
            
        Returns:
            Formatted code
        """
        return code

    def _fix_spacing(self, code: str) -> str:
        """Basic spacing normalization used by indent-based formatters."""
        code = re.sub(r'([^\s=!<>])=([^\s=])', r'\1 = \2', code)
        code = re.sub(r'([^\s!<>])==([^\s])', r'\1 == \2', code)
        code = re.sub(r'([^\s])([+\-*/%])', r'\1 \2', code)
        code = re.sub(r',([^\s])', r', \1', code)
        code = re.sub(r'([^\s]):([^\s])', r'\1: \2', code)
        code = re.sub(r'\n\s*\n\s*\n', r'\n\n', code)
        return code

    def apply_indentation(self, code: str, base_indent: str) -> str:
        """
        Apply indentation to the code.
        
        Args:
            code: Code to indent
            base_indent: Base indentation to apply
            
        Returns:
            Indented code
        """
        lines = code.splitlines()
        result = []
        for line in lines:
            if line.strip():
                result.append(base_indent + line.lstrip())
            else:
                result.append('')
        return '\n'.join(result)

    def get_indentation(self, line: str) -> str:
        """
        Get the indentation from a line.
        
        Args:
            line: Line to analyze
            
        Returns:
            Indentation string
        """
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    def dedent(self, code: str) -> str:
        """
        Remove common leading whitespace from all lines.
        
        Args:
            code: Code to dedent
            
        Returns:
            Dedented code
        """
        return textwrap.dedent(code)

    def normalize_indentation(self, code: str, target_indent: str='') -> str:
        """
        Normalize indentation to be consistent throughout the code.
        
        Args:
            code: Code to normalize
            target_indent: Target indentation
            
        Returns:
            Code with normalized indentation
        """
        lines = code.splitlines()
        non_empty_lines = [line for line in lines if line.strip()]
        if not non_empty_lines:
            return code
        min_indent = float('inf')
        for line in non_empty_lines:
            indent_size = len(self.get_indentation(line))
            if indent_size < min_indent:
                min_indent = indent_size
        if min_indent == float('inf'):
            min_indent = 0
        result = []
        for line in lines:
            if not line.strip():
                result.append('')
                continue
            indent = self.get_indentation(line)
            if len(indent) >= min_indent:
                relative_indent = len(indent) - min_indent
                result.append(target_indent + ' ' * relative_indent + line[len(indent):])
            else:
                result.append(target_indent + line)
        return '\n'.join(result)