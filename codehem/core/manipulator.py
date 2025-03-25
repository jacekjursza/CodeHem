import re
from typing import Tuple, Optional

from codehem.extractors.base import BaseExtractor


class BaseManipulator:
    """Base handler for Python manipulators with common formatting utilities"""
    LANGUAGE_CODE = ''
    ELEMENT_TYPE = ''

    def __init__(self, extractor: BaseExtractor):
        self.extractor = extractor

    @staticmethod
    def get_indentation(line: str) -> str:
        """Extract indentation from a line"""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    @staticmethod
    def apply_indentation(content: str, indent: str) -> str:
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

    def find_element(self, code: str, method_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find a method in Python code"""
        results = self.extractor.extract(code, context={'class_name': parent_name, 'name': method_name})
        if results and len(results) == 1:
            result = results[0]
            return result['range']['start']['line'], result['range']['end']['line']
        return 0, 0

    @staticmethod
    def replace_lines(original_code: str, start_line: int,
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