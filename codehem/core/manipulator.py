import re
from typing import Tuple, Optional


class BaseManipulator:
    """Base handler for Python manipulators with common formatting utilities"""

    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line"""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    def apply_indentation(self, content: str, indent: str) -> str:
        """Apply consistent indentation to a block of content"""
        lines = content.splitlines()
        result = []
        for line in lines:
            if line.strip():
                result.append(f'{indent}{line.lstrip()}')
            else:
                result.append('')
        return '\n'.join(result)

    def format_element(self, element_code: str, indent_level: int = 0) -> str:
        """Format a code element generically"""
        indent = ' ' * (4 * indent_level)
        return self.apply_indentation(element_code.strip(), indent)

    def find_element(self, code: str, element_name: str,
                     parent_name: Optional[str] = None) -> Tuple[int, int]:
        """Find line numbers for an element in code"""
        # This should be implemented by specific handlers
        return 0, 0

    def replace_lines(self, original_code: str, start_line: int,
                      end_line: int, new_content: str) -> str:
        """Replace lines between start_line and end_line with new_content"""
        if start_line <= 0 or end_line < start_line:
            return original_code

        lines = original_code.splitlines()
        if start_line > len(lines):
            return original_code

        result = []
        result.extend(lines[:start_line-1])
        result.extend(new_content.splitlines())
        result.extend(lines[end_line:])

        return '\n'.join(result)