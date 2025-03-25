import re
from typing import Optional, Tuple
from codehem.models.enums import CodeElementType
from codehem.core.registry import element_type_descriptor, manipulator
from codehem.languages.lang_python.manipulator.base import PythonBaseManipulator
from codehem.core.extraction import ExtractionService

@manipulator
class PythonMethodManipulator(PythonBaseManipulator):
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.METHOD

    def format_element(self, element_code: str, indent_level: int=0) -> str:
        """Format a Python method definition"""
        indent = ' ' * (4 * indent_level)
        lines = element_code.strip().splitlines()
        if not lines:
            return ''
        result = []
        method_line_idx = next((i for (i, line) in enumerate(lines) if line.strip().startswith('def ')), 0)
        for i in range(method_line_idx):
            result.append(f'{indent}{lines[i].strip()}')
        result.append(f'{indent}{lines[method_line_idx].strip()}')
        method_indent = indent + '    '
        for i in range(method_line_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                result.append('')
                continue
            result.append(f'{method_indent}{line}')
        return '\n'.join(result)

    def find_element(self, code: str, method_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find a method in Python code"""
        # Create an extraction service for more advanced search capabilities
        extraction_service = ExtractionService(self.LANGUAGE_CODE)
        
        if not parent_name:
            # We need to find the parent class for the method
            # Extract all classes and check their methods
            classes = extraction_service.extract_classes(code)
            for cls in classes:
                cls_name = cls.get('name')
                methods = extraction_service.extract_methods(code, cls_name)
                for method in methods:
                    if method.get('name') == method_name:
                        parent_name = cls_name
                        break
                if parent_name:
                    break
            if not parent_name:
                return (0, 0)
        
        return extraction_service.find_element(code, self.ELEMENT_TYPE.value, method_name, parent_name)

    def replace_element(self, original_code: str, method_name: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Replace a method in Python code"""
        (start_line, end_line) = self.find_element(original_code, method_name, parent_name)
        if start_line == 0 and end_line == 0:
            if parent_name:
                return self.add_element(original_code, new_element, parent_name)
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
        class_line = 0
        if parent_name:
            extraction_service = ExtractionService(self.LANGUAGE_CODE)
            (class_start, _) = extraction_service.find_element(original_code, CodeElementType.CLASS.value, parent_name)
            if class_start > 0:
                class_line = class_start - 1
        class_indent = ''
        if class_line < len(lines):
            class_indent = self.get_indentation(lines[class_line])
        method_indent_level = len(class_indent) // 4 + 1
        formatted_method = self.format_element(new_element, method_indent_level)
        return self.replace_lines(original_code, adjusted_start, end_line, formatted_method)

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add a method to a Python class"""
        if not parent_name:
            return original_code
        extraction_service = ExtractionService(self.LANGUAGE_CODE)
        (class_start, class_end) = extraction_service.find_element(original_code, CodeElementType.CLASS.value, parent_name)
        if class_start == 0:
            return original_code
        lines = original_code.splitlines()
        class_indent = ''
        if class_start - 1 < len(lines):
            class_indent = self.get_indentation(lines[class_start - 1])
        method_indent_level = len(class_indent) // 4 + 1
        formatted_method = self.format_element(new_element, method_indent_level)
        insertion_point = class_end
        if insertion_point > len(lines):
            insertion_point = len(lines)
        result_lines = lines[:insertion_point]
        if result_lines and result_lines[-1].strip():
            result_lines.append('')
        result_lines.append(formatted_method)
        result_lines.extend(lines[insertion_point:])
        return '\n'.join(result_lines)

    def remove_element(self, original_code: str, method_name: str, parent_name: Optional[str]=None) -> str:
        """Remove a method from a Python class"""
        (start_line, end_line) = self.find_element(original_code, method_name, parent_name)
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