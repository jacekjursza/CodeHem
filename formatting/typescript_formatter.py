"""
TypeScript-specific code formatter.
"""
import re
from typing import List, Tuple, Optional
from .formatter import CodeFormatter

class TypeScriptFormatter(CodeFormatter):
    """
    TypeScript-specific code formatter.
    Handles TypeScript's indentation rules and common patterns.
    """
    
    def __init__(self, indent_size: int = 2):
        """
        Initialize a TypeScript formatter.
        
        Args:
            indent_size: Number of spaces for each indentation level (default: 2)
        """
        super().__init__(indent_size)
    
    def format_code(self, code: str) -> str:
        """
        Format TypeScript code according to common standards.
        
        Args:
            code: TypeScript code to format
            
        Returns:
            Formatted TypeScript code
        """
        # Basic cleaning
        code = code.strip()
        
        # Ensure proper spacing
        code = self._fix_spacing(code)
        
        return code
    
    def format_class(self, class_code: str) -> str:
        """
        Format a TypeScript class definition.
        
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
        current_indent = ''
        in_method_body = False
        brace_stack = []
        
        # Process each line
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                result.append('')
                continue
                
            # Track braces
            if '{' in stripped:
                brace_stack.append('{')
                
            if '}' in stripped:
                if brace_stack:
                    brace_stack.pop()
                    
            # Determine indentation level
            indent_level = len(brace_stack)
            if stripped == '{':
                # Opening brace on its own line
                current_indent = self.indent_string * (indent_level - 1)
            elif stripped == '}':
                # Closing brace on its own line
                current_indent = self.indent_string * (indent_level)
            else:
                current_indent = self.indent_string * indent_level
                
            # Apply proper indentation
            result.append(f"{current_indent}{stripped}")
                
        return '\n'.join(result)
    
    def format_method(self, method_code: str) -> str:
        """
        Format a TypeScript method definition.
        
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
        
        # Find opening and closing braces
        brace_stack = []
        
        # Process each line
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if not stripped:
                result.append('')
                continue
                
            # Track braces
            if '{' in stripped:
                brace_stack.append((i, '{'))
                
            if '}' in stripped and brace_stack:
                brace_stack.pop()
                
            # Determine indentation level
            indent_level = len(brace_stack)
            current_indent = self.indent_string * indent_level
                
            # Apply proper indentation
            result.append(f"{current_indent}{stripped}")
                
        return '\n'.join(result)
    
    def format_function(self, function_code: str) -> str:
        """
        Format a TypeScript function definition.
        
        Args:
            function_code: Function code to format
            
        Returns:
            Formatted function code
        """
        # For functions, we can reuse the method formatting logic
        return self.format_method(function_code)
    
    def _fix_spacing(self, code: str) -> str:
        """
        Fix spacing issues in TypeScript code.
        
        Args:
            code: TypeScript code to fix
            
        Returns:
            Code with fixed spacing
        """
        # Fix spacing around operators
        code = re.sub(r'([^\s=!<>])=([^\s=])', r'\1 = \2', code)  # Assignment
        code = re.sub(r'([^\s!<>])==[^\s]', r'\1 == \2', code)  # Equality
        code = re.sub(r'([^\s])([+\-*/%])', r'\1 \2', code)  # Binary operators
        
        # Fix spacing after commas
        code = re.sub(r',([^\s])', r', \1', code)
        
        # Fix spacing around colons in object literals and types
        code = re.sub(r'([^\s]):([^\s])', r'\1: \2', code)
        
        # Fix spacing after semicolons
        code = re.sub(r';([^\s\n])', r';\n\1', code)
        
        # Fix blank lines
        code = re.sub(r'\n\s*\n\s*\n', '\n\n', code)
        
        return code