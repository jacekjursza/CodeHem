"""
Code formatting system for standardizing code output across languages.
"""
from typing import List, Optional
import re
import textwrap

class CodeFormatter:
    """
    Base class for language-specific code formatters.
    Provides common formatting utilities and language-specific hooks.
    """
    
    def __init__(self, indent_size: int = 4):
        """
        Initialize a code formatter.
        
        Args:
            indent_size: Number of spaces for each indentation level
        """
        self.indent_size = indent_size
        self.indent_string = ' ' * indent_size
    
    def format_code(self, code: str) -> str:
        """
        Format code according to language standards.
        This is a placeholder to be overridden by language-specific formatters.
        
        Args:
            code: Code to format
            
        Returns:
            Formatted code
        """
        return code
    
    def get_indentation(self, line: str) -> str:
        """
        Get the whitespace indentation from a line.
        
        Args:
            line: Source line to analyze
            
        Returns:
            Indentation string
        """
        match = re.match(r'^(\s*)', line)
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
    
    def apply_indentation(self, code: str, indent: str) -> str:
        """
        Apply indentation to all non-empty lines of code.
        
        Args:
            code: Code to indent
            indent: Indentation string to apply
            
        Returns:
            Indented code
        """
        lines = code.splitlines()
        result = []
        
        for line in lines:
            if line.strip():
                result.append(f"{indent}{line.lstrip()}")
            else:
                result.append(line)
                
        return '\n'.join(result)
    
    def normalize_indentation(self, code: str, base_indent: str = '') -> str:
        """
        Normalize indentation to be consistent throughout the code.
        
        Args:
            code: Code to normalize
            base_indent: Base indentation to apply
            
        Returns:
            Code with normalized indentation
        """
        lines = code.splitlines()
        
        # Find common indentation and indentation steps
        non_empty_lines = [line for line in lines if line.strip()]
        if not non_empty_lines:
            return code
            
        min_indent = min(len(self.get_indentation(line)) for line in non_empty_lines)
        
        # Remove common indentation and apply base indent
        result = []
        for line in lines:
            if not line.strip():
                result.append('')
                continue
                
            current_indent = len(self.get_indentation(line))
            if current_indent >= min_indent:
                indent_depth = current_indent - min_indent
                result.append(f"{base_indent}{' ' * indent_depth}{line[current_indent:]}")
            else:
                result.append(f"{base_indent}{line}")
                
        return '\n'.join(result)
    
    def merge_indentation(self, code: str, reference_code: str) -> str:
        """
        Apply indentation from reference code to new code.
        
        Args:
            code: Code to format
            reference_code: Reference code to get indentation from
            
        Returns:
            Code with merged indentation
        """
        ref_lines = reference_code.splitlines()
        if not ref_lines:
            return code
            
        ref_indent = self.get_indentation(ref_lines[0])
        return self.apply_indentation(self.dedent(code), ref_indent)