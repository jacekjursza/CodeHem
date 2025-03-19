"""
Python-specific code formatter.
"""
import re
from typing import List, Tuple, Optional
from .formatter import CodeFormatter

class PythonFormatter(CodeFormatter):
    """
    Python-specific code formatter.
    Handles Python's indentation rules and common patterns.
    """
    
    def format_code(self, code: str) -> str:
        """
        Format Python code according to PEP 8-like standards.
        
        Args:
            code: Python code to format
            
        Returns:
            Formatted Python code
        """
        # Basic cleaning
        code = code.strip()
        
        # Ensure proper spacing
        code = self._fix_spacing(code)
        
        return code
    
    def format_class(self, class_code: str) -> str:
        """
        Format a Python class definition.
        
        Args:
            class_code: Class code to format
            
        Returns:
            Formatted class code
        """
        # Dedent the whole class definition first
        dedented = self.dedent(class_code).strip()
        
        lines = dedented.splitlines()
        if not lines:
            return ''
            
        result = []
        
        # Handle class and decorators
        class_line_idx = next((i for i, line in enumerate(lines) if line.strip().startswith('class ')), 0)
        
        # Add decorators
        for i in range(class_line_idx):
            result.append(lines[i])
            
        # Add class definition
        result.append(lines[class_line_idx])
        
        # Process class body with consistent indentation
        in_method = False
        in_docstring = False
        docstring_delimiter = None
        
        for i in range(class_line_idx + 1, len(lines)):
            line = lines[i]
            stripped = line.strip()
            
            if not stripped:
                result.append('')
                continue
                
            # Handle docstrings
            if in_docstring:
                if stripped.endswith(docstring_delimiter):
                    in_docstring = False
                result.append(f"{self.indent_string}{line}")
                continue
                
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = True
                docstring_delimiter = stripped[:3]
                result.append(f"{self.indent_string}{line}")
                continue
                
            # Handle method definitions
            if stripped.startswith('def ') or stripped.startswith('@'):
                in_method = True if stripped.startswith('def ') else False
                result.append(f"{self.indent_string}{stripped}")
                continue
                
            # Method body
            if in_method:
                result.append(f"{self.indent_string * 2}{stripped}")
            else:
                # Class attributes or other content
                result.append(f"{self.indent_string}{stripped}")
                
        return '\n'.join(result)
    
    def format_method(self, method_code: str) -> str:
        """
        Format a Python method definition.
        
        Args:
            method_code: Method code to format
            
        Returns:
            Formatted method code
        """
        # Dedent the whole method definition first
        dedented = self.dedent(method_code).strip()
        
        lines = dedented.splitlines()
        if not lines:
            return ''
            
        result = []
        
        # Find the method signature
        method_line_idx = next((i for i, line in enumerate(lines) if line.strip().startswith('def ')), 0)
        
        # Add decorators
        for i in range(method_line_idx):
            result.append(lines[i])
            
        # Add method signature
        result.append(lines[method_line_idx])
        
        # Process method body with consistent indentation
        for i in range(method_line_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                result.append('')
                continue
                
            result.append(f"{self.indent_string}{line}")
                
        return '\n'.join(result)
    
    def format_function(self, function_code: str) -> str:
        """
        Format a Python function definition.
        
        Args:
            function_code: Function code to format
            
        Returns:
            Formatted function code
        """
        # For functions, we can reuse the method formatting logic
        return self.format_method(function_code)
    
    def _fix_spacing(self, code: str) -> str:
        """
        Fix spacing issues in Python code.
        
        Args:
            code: Python code to fix
            
        Returns:
            Code with fixed spacing
        """
        # Fix spacing around operators
        code = re.sub(r'([^\s=!<>])=([^\s=])', r'\1 = \2', code)  # Assignment
        code = re.sub(r'([^\s!<>])==[^\s]', r'\1 == \2', code)  # Equality
        code = re.sub(r'([^\s])([+\-*/%])', r'\1 \2', code)  # Binary operators
        
        # Fix spacing after commas
        code = re.sub(r',([^\s])', r', \1', code)
        
        # Fix spacing around colons in dict literals and slices
        code = re.sub(r'([^\s]):([^\s])', r'\1: \2', code)
        
        # Fix blank lines
        code = re.sub(r'\n\s*\n\s*\n', '\n\n', code)
        
        return code