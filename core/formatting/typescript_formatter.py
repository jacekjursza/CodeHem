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
    
    def __init__(self, indent_size: int=4):
        """
        Initialize a TypeScript formatter.

        Args:
        indent_size: Number of spaces for each indentation level (default: 4)
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
        code = code.strip()
        code = self._fix_spacing(code)

        # For more complex formatting, parse line by line
        lines = code.splitlines()
        if len(lines) <= 1:
            return code

        # Process indentation using brace tracking
        result = []
        brace_level = 0
        jsx_level = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                result.append('')
                continue

            # Handle comments with special indentation
            if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                result.append(self.indent_string * brace_level + stripped)
                continue

            # Count braces and JSX tags for indentation level
            open_count = stripped.count('{')
            close_count = stripped.count('}')

            # Handle JSX indentation
            open_jsx = stripped.count('<') - stripped.count('</') - stripped.count('/>')
            close_jsx = stripped.count('</') + stripped.count('/>')

            # Special handling for JSX/TSX
            jsx_indent = 0
            if '<' in stripped and '>' in stripped and not stripped.startswith('import'):
                if open_jsx > close_jsx:
                    jsx_indent = 1  # Increase indent for next line

            # Handle lines with just closing brace
            if stripped == '}' or stripped == '};':
                brace_level = max(0, brace_level - 1)
                result.append(self.indent_string * brace_level + stripped)
            else:
                # Normal line with current indentation (account for both braces and JSX)
                result.append(self.indent_string * (brace_level + jsx_level) + stripped)

                # Update brace level for next line
                brace_level += open_count
                if close_count > 0 and stripped != '}' and stripped != '};':
                    brace_level = max(0, brace_level - close_count)

                # Update JSX level
                jsx_level += jsx_indent
                jsx_level = max(0, jsx_level - (close_jsx if close_jsx > open_jsx else 0))

        return '\n'.join(result)
    
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
        # Method formatting is essentially the same as function formatting
        return self.format_function(method_code)
    
    def format_function(self, function_code: str) -> str:
        """
        Format a TypeScript function definition.

        Args:
        function_code: Function code to format

        Returns:
        Formatted function code
        """
        dedented = self.dedent(function_code.strip())
        lines = dedented.splitlines()
        if not lines:
            return ''

        result = []
        brace_level = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                result.append('')
                continue

            # Handle docstring/comment lines specially to maintain their indentation
            if stripped.startswith('/*') or stripped.startswith('*') or stripped.startswith('//'):
                # For first line of comment or standalone comment
                if brace_level == 0:
                    result.append(stripped)
                else:
                    result.append(self.indent_string * brace_level + stripped)
                continue

            # Count braces before deciding indentation
            open_count = stripped.count('{')
            close_count = stripped.count('}')

            # Lines with just a closing brace reduce level before indenting
            if stripped == '}' or stripped == '};':
                brace_level = max(0, brace_level - 1)
                result.append(self.indent_string * brace_level + stripped)
            else:
                # Apply current brace level for indentation
                result.append(self.indent_string * brace_level + stripped)

                # Update brace level for next line
                brace_level += open_count
                if close_count > 0 and stripped != '}' and stripped != '};':
                    brace_level = max(0, brace_level - close_count)

        return '\n'.join(result)
    
    def _fix_spacing(self, code: str) -> str:
        """
        Fix spacing issues in TypeScript code.

        Args:
        code: TypeScript code to fix

        Returns:
        Code with fixed spacing
        """
        code = re.sub(r'([^\s=!<>])=([^\s=])', r'\1 = \2', code)
        code = re.sub(r'([^\s!<>])==([^\s])', r'\1 == \2', code)  # Fixed: Added capture group
        code = re.sub(r'([^\s])([+\-*/%])', r'\1 \2', code)
        code = re.sub(r',([^\s])', r', \1', code)
        code = re.sub(r'([^\s]):([^\s])', r'\1: \2', code)
        code = re.sub(r';([^\s\n])', r';\n\1', code)
        code = re.sub(r'\n\s*\n\s*\n', r'\n\n', code)
        return code
