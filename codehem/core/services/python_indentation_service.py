"""
Service for handling Python code indentation, especially for nested structures.
"""
import re
from typing import List, Dict, Tuple, Optional

class PythonIndentationService:
    """Service for calculating and applying proper indentation to Python code."""

    def __init__(self, indent_size: int=4):
        """Initialize the service with the indent size (default: 4 spaces)."""
        self.indent_size = indent_size
        self.indent_string = ' ' * indent_size

    def calculate_class_indentation(self, code_lines: List[str], class_name: str) -> str:
        """
        Calculate the proper indentation for a class, handling nested classes.

        Args:
            code_lines: Source code lines
            class_name: Class name (can include dots for nested classes)

        Returns:
            Indentation string for the class
        """
        if '.' in class_name:
            class_parts = class_name.split('.')
            current_indent = ''
            for line in code_lines:
                if line.strip().startswith(f'class {class_parts[0]}'):
                    current_indent = self._get_indentation(line) + self.indent_string
                    break
            for i in range(1, len(class_parts)):
                current_indent += self.indent_string
            return current_indent
        else:
            for line in code_lines:
                if line.strip().startswith(f'class {class_name}'):
                    return self._get_indentation(line) + self.indent_string
        return self.indent_string

    def format_method_content(self, method_content: str, base_indent: str) -> str:
        """
        Format method content with proper indentation by preserving the original
        indentation structure and shifting it to match the class context.
        """
        method_content = method_content.strip()
        if not method_content:
            return ''

        method_lines = method_content.splitlines()
        if not method_lines:
            return ''

        method_def_index = -1
        decorator_indices = []

        # Find decorators and method definition
        for (i, line) in enumerate(method_lines):
            line_stripped = line.strip()
            if line_stripped.startswith('@'):
                decorator_indices.append(i)
            elif line_stripped.startswith('def '):
                method_def_index = i
                break

        if method_def_index == -1:
            return self.apply_indentation(method_content, base_indent)

        # Preserve all decorators, especially @property
        result_lines = []
        for idx in decorator_indices:
            result_lines.append(f'{base_indent}{method_lines[idx].strip()}')

        result_lines.append(f'{base_indent}{method_lines[method_def_index].strip()}')

        if len(method_lines) <= method_def_index + 1:
            return '\n'.join(result_lines)

        min_indent = float('inf')
        body_lines = []

        for i in range(method_def_index + 1, len(method_lines)):
            line = method_lines[i]
            body_lines.append(line)
            if not line.strip():
                continue
            indent_len = len(line) - len(line.lstrip())
            if indent_len > 0 and indent_len < min_indent:
                min_indent = indent_len

        if min_indent == float('inf'):
            min_indent = self.indent_size

        for line in body_lines:
            if not line.strip():
                result_lines.append('')
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent >= min_indent:
                relative_indent = current_indent - min_indent
                new_indent = base_indent + self.indent_string + ' ' * relative_indent
                result_lines.append(f'{new_indent}{line.lstrip()}')
            else:
                result_lines.append(f'{base_indent}{self.indent_string}{line.lstrip()}')

        return '\n'.join(result_lines)

    def _get_indentation(self, line: str) -> str:
        """Extract the whitespace indentation from a line."""
        match = re.match(r'^(\s*)', line)
        return match.group(1) if match else ''

    def apply_indentation(self, content: str, base_indent: str) -> str:
        """Apply consistent indentation to a block of content."""
        lines = content.splitlines()
        result = []
        for line in lines:
            if line.strip():
                result.append(f"{base_indent}{line.strip()}")
            else:
                result.append('')
        return '\n'.join(result)