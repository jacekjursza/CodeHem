import re
from typing import Optional, Tuple
from codehem.models.enums import CodeElementType
from codehem.core.registry import element_type_descriptor, manipulator
from codehem.languages.lang_python.manipulator.base import PythonBaseManipulator
from codehem.core.extraction import ExtractionService

@manipulator
class PythonClassManipulator(PythonBaseManipulator):
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.CLASS

    def format_element(self, element_code: str, indent_level: int=0) -> str:
        """Format a Python class definition"""
        indent = ' ' * (4 * indent_level)
        lines = element_code.strip().splitlines()
        if not lines:
            return ''
        result = []
        class_line_idx = next((i for (i, line) in enumerate(lines) if line.strip().startswith('class ')), 0)
        for i in range(class_line_idx):
            result.append(f'{indent}{lines[i].strip()}')
        result.append(f'{indent}{lines[class_line_idx].strip()}')
        class_indent = indent + '    '
        for i in range(class_line_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                result.append('')
                continue
            result.append(f'{class_indent}{line}')
        return '\n'.join(result)

    def find_element(self, code: str, class_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find a class in Python code"""
        extraction_service = ExtractionService(self.LANGUAGE_CODE)
        return extraction_service.find_element(code, self.ELEMENT_TYPE.value, class_name)

    def replace_element(self, original_code: str, class_name: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Replace a class in Python code"""
        (start_line, end_line) = self.find_element(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return self.add_element(original_code, new_element)
        formatted_class = self.format_element(new_element)
        return self.replace_lines(original_code, start_line, end_line, formatted_class)

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add a class to Python code"""
        formatted_class = self.format_element(new_element)
        if original_code and (not original_code.endswith('\n\n')):
            if original_code.endswith('\n'):
                original_code += '\n'
            else:
                original_code += '\n\n'
        return original_code + formatted_class + '\n'

    def remove_element(self, original_code: str, class_name: str, parent_name: Optional[str]=None) -> str:
        """Remove a class from Python code"""
        (start_line, end_line) = self.find_element(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, '')