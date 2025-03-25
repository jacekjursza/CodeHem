import re
from typing import Optional, Tuple
from codehem.models.enums import CodeElementType
from codehem.core.registry import element_type_descriptor, manipulator
from codehem.languages.lang_python.manipulator.base import PythonBaseManipulator
from codehem.core.extraction import ExtractionService

@manipulator
class PythonFunctionManipulator(PythonBaseManipulator):
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.FUNCTION

    def format_element(self, element_code: str, indent_level: int=0) -> str:
        """Format a Python function definition"""
        indent = ' ' * (4 * indent_level)
        lines = element_code.strip().splitlines()
        if not lines:
            return ''
        result = []
        func_line_idx = next((i for (i, line) in enumerate(lines) if line.strip().startswith('def ')), 0)
        for i in range(func_line_idx):
            result.append(f'{indent}{lines[i].strip()}')
        result.append(f'{indent}{lines[func_line_idx].strip()}')
        func_indent = indent + '    '
        for i in range(func_line_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                result.append('')
                continue
            result.append(f'{func_indent}{line}')
        return '\n'.join(result)

    def find_element(self, code: str, function_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find a function in Python code"""
        extraction_service = ExtractionService(self.LANGUAGE_CODE)
        return extraction_service.find_element(code, self.ELEMENT_TYPE.value, function_name)

    def replace_element(self, original_code: str, function_name: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Replace a function in Python code"""
        (start_line, end_line) = self.find_element(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return self.add_element(original_code, new_element)
        lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('#')):
                break
        formatted_function = self.format_element(new_element)
        return self.replace_lines(original_code, adjusted_start, end_line, formatted_function)

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add a function to Python code"""
        formatted_function = self.format_element(new_element)
        if original_code and (not original_code.endswith('\n\n')):
            if original_code.endswith('\n'):
                original_code += '\n'
            else:
                original_code += '\n\n'
        return original_code + formatted_function + '\n'

    def remove_element(self, original_code: str, function_name: str, parent_name: Optional[str]=None) -> str:
        """Remove a function from Python code"""
        (start_line, end_line) = self.find_element(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('#')):
                break
        return self.replace_lines(original_code, adjusted_start, end_line, '')