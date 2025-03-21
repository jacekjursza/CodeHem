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
        lines = code.splitlines()
        if len(lines) <= 1:
            return code
        result = []
        brace_level = 0
        jsx_level = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                result.append('')
                continue
            if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                result.append(self.indent_string * brace_level + stripped)
                continue
            open_count = stripped.count('{')
            close_count = stripped.count('}')
            open_jsx = stripped.count('<') - stripped.count('</') - stripped.count('/>')
            close_jsx = stripped.count('</') + stripped.count('/>')
            jsx_indent = 0
            if '<' in stripped and '>' in stripped and (not stripped.startswith('import')):
                if open_jsx > close_jsx:
                    jsx_indent = 1
            if stripped == '}' or stripped == '};':
                brace_level = max(0, brace_level - 1)
                result.append(self.indent_string * brace_level + stripped)
            else:
                result.append(self.indent_string * (brace_level + jsx_level) + stripped)
                brace_level += open_count
                if close_count > 0 and stripped != '}' and (stripped != '};'):
                    brace_level = max(0, brace_level - close_count)
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
        dedented = self.dedent(class_code).strip()
        lines = dedented.splitlines()
        if not lines:
            return ''
        result = []
        current_indent = ''
        in_method_body = False
        brace_stack = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                result.append('')
                continue
            if '{' in stripped:
                brace_stack.append('{')
            if '}' in stripped:
                if brace_stack:
                    brace_stack.pop()
            indent_level = len(brace_stack)
            if stripped == '{':
                current_indent = self.indent_string * (indent_level - 1)
            elif stripped == '}':
                current_indent = self.indent_string * indent_level
            else:
                current_indent = self.indent_string * indent_level
            result.append(f'{current_indent}{stripped}')
        return '\n'.join(result)

    def format_method(self, method_code: str) -> str:
        """
        Format a TypeScript method definition.

        Args:
        method_code: Method code to format

        Returns:
        Formatted method code
        """
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
        jsx_stack = []  # Stack to track JSX tag nesting
        has_jsx = any(('<' in line and '>' in line and (not line.strip().startswith('import')) for line in lines))
        in_jsdoc = False
        in_jsx_content = False  # Flag to track if we're in content between JSX tags

        for line in lines:
            stripped = line.strip()
            if not stripped:
                result.append('')
                continue

            # Handle JSDoc comments
            if stripped.startswith('/**'):
                in_jsdoc = True
                result.append(stripped)
                continue
            elif in_jsdoc and stripped.startswith('*/'):
                in_jsdoc = False
                # Ensure there's a space before */
                if stripped == '*/':
                    result.append(' */')
                else:
                    result.append(stripped)
                continue
            elif in_jsdoc and stripped.startswith('*'):
                orig_indent = len(line) - len(line.lstrip())
                orig_text = line.lstrip()
                if stripped == '*':
                    result.append(' ' * orig_indent + '*')
                elif orig_text.startswith('* '):
                    result.append(' ' * orig_indent + orig_text)
                else:
                    result.append(' ' * orig_indent + '* ' + orig_text[1:].lstrip())
                continue

            # Handle comments
            if stripped.startswith('//') or stripped.startswith('/*'):
                indent = brace_level * self.indent_size
                result.append(' ' * indent + stripped)
                continue

            # Process JSX
            if has_jsx and ('<' in stripped and '>' in stripped or in_jsx_content):
                # If we're inside JSX content (between tags)
                if in_jsx_content and not ('<' in stripped and '>' in stripped):
                    # Pure content (like "-" or "+")
                    jsx_level = len(jsx_stack)
                    indent = (brace_level + jsx_level) * self.indent_size
                    result.append(' ' * indent + stripped)
                    continue

                # Handle JSX tags
                if '</' in stripped:  # Closing tag
                    if jsx_stack:
                        jsx_stack.pop()
                    jsx_level = len(jsx_stack)
                    indent = (brace_level + jsx_level) * self.indent_size
                    result.append(' ' * indent + stripped)
                    in_jsx_content = False
                elif '/>' in stripped:  # Self-closing tag
                    jsx_level = len(jsx_stack)
                    indent = (brace_level + jsx_level) * self.indent_size
                    result.append(' ' * indent + stripped)
                elif '<' in stripped:  # Opening tag
                    if stripped.startswith('return ('):
                        indent = brace_level * self.indent_size
                        result.append(' ' * indent + stripped)
                        brace_level += 1
                    else:
                        jsx_level = len(jsx_stack)
                        indent = (brace_level + jsx_level) * self.indent_size
                        result.append(' ' * indent + stripped)

                        # If it's an opening tag and not self-closing, add to stack
                        if '<' in stripped and not '/>' in stripped and not 'return (' in stripped:
                            jsx_stack.append(stripped)
                            in_jsx_content = True  # Next line might be content between tags
                else:
                    jsx_level = len(jsx_stack)
                    indent = (brace_level + jsx_level) * self.indent_size
                    result.append(' ' * indent + stripped)
                continue

            # Handle braces
            open_count = stripped.count('{')
            close_count = stripped.count('}')

            if stripped == '}' or stripped == '};':
                brace_level = max(0, brace_level - 1)
                indent = brace_level * self.indent_size
                result.append(' ' * indent + stripped)
            else:
                indent = brace_level * self.indent_size
                result.append(' ' * indent + stripped)
                brace_level += open_count
                if close_count > 0 and stripped != '}' and stripped != '};':
                    brace_level = max(0, brace_level - close_count)

        return '\n'.join(result)

    def format_interface(self, interface_code: str) -> str:
        """
        Format a TypeScript interface definition with 2-space indentation.
        
        Args:
            interface_code: Interface code to format
            
        Returns:
            Formatted interface code
        """
        # Save original indentation settings
        original_indent_size = self.indent_size
        original_indent_string = self.indent_string
        
        # Use 2-space indentation for interfaces
        self.indent_size = 2
        self.indent_string = '  '
        
        # Format the interface
        dedented = self.dedent(interface_code.strip())
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
                
            open_count = stripped.count('{')
            close_count = stripped.count('}')
            
            if stripped == '}' or stripped == '};':
                brace_level = max(0, brace_level - 1)
                result.append(self.indent_string * brace_level + stripped)
            else:
                result.append(self.indent_string * brace_level + stripped)
                brace_level += open_count
                if close_count > 0 and stripped != '}' and (stripped != '};'):
                    brace_level = max(0, brace_level - close_count)
        
        formatted = '\n'.join(result)
        
        # Restore original indentation settings
        self.indent_size = original_indent_size
        self.indent_string = original_indent_string
        
        return formatted

    def _fix_spacing(self, code: str) -> str:
        """
        Fix spacing issues in TypeScript code.

        Args:
        code: TypeScript code to fix

        Returns:
        Code with fixed spacing
        """
        code = re.sub('([^\\s=!<>])=([^\\s=])', '\\1 = \\2', code)
        code = re.sub('([^\\s!<>])==([^\\s])', '\\1 == \\2', code)
        code = re.sub('([^\\s])([+\\-*/%])', '\\1 \\2', code)
        code = re.sub(',([^\\s])', ', \\1', code)
        code = re.sub('([^\\s]):([^\\s])', '\\1: \\2', code)
        code = re.sub(';([^\\s\\n])', ';\\n\\1', code)
        code = re.sub('\\n\\s*\\n\\s*\\n', '\\n\\n', code)
        return code