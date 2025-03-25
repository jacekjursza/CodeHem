import re
from typing import Optional, Tuple
from codehem.models.enums import CodeElementType
from codehem.core.registry import element_type_descriptor, manipulator
from codehem.languages.lang_python.manipulator.base import PythonBaseManipulator
from codehem.core.extraction import ExtractionService

@manipulator
class PythonPropertyManipulator(PythonBaseManipulator):
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.PROPERTY

    def format_element(self, element_code: str, indent_level: int=0) -> str:
        """Format a Python property definition"""
        indent = ' ' * (4 * indent_level)
        lines = element_code.strip().splitlines()
        if not lines:
            return ''
        result = []
        is_property_decorator = False
        for line in lines:
            if line.strip().startswith('@property'):
                is_property_decorator = True
                break
        if is_property_decorator:
            decorator_lines = []
            method_line_idx = -1
            for (i, line) in enumerate(lines):
                if line.strip().startswith('@'):
                    decorator_lines.append(i)
                elif line.strip().startswith('def '):
                    method_line_idx = i
                    break
            for i in decorator_lines:
                result.append(f'{indent}{lines[i].strip()}')
            if method_line_idx >= 0:
                result.append(f'{indent}{lines[method_line_idx].strip()}')
                method_indent = indent + '    '
                for i in range(method_line_idx + 1, len(lines)):
                    line = lines[i].strip()
                    if not line:
                        result.append('')
                        continue
                    result.append(f'{method_indent}{line}')
        else:
            for line in lines:
                result.append(f'{indent}{line.strip()}')
        return '\n'.join(result)

    def find_element(self, code: str, property_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find a property in Python code"""
        if not parent_name:
            return (0, 0)
        
        extraction_service = ExtractionService(self.LANGUAGE_CODE)
        
        # Try to find a property getter
        property_getter = extraction_service.find_element(code, CodeElementType.PROPERTY_GETTER.value, property_name, parent_name)
        if property_getter[0] > 0:
            return property_getter
        
        # Try to find a property setter
        property_setter = extraction_service.find_element(code, CodeElementType.PROPERTY_SETTER.value, property_name, parent_name)
        if property_setter[0] > 0:
            return property_setter
        
        # Try to find a static property
        static_property = extraction_service.find_element(code, CodeElementType.STATIC_PROPERTY.value, property_name, parent_name)
        if static_property[0] > 0:
            return static_property
        
        # Try to find a regular property in the __init__ method
        (class_start, class_end) = extraction_service.find_element(code, CodeElementType.CLASS.value, parent_name)
        if class_start == 0:
            return (0, 0)
        
        lines = code.splitlines()
        for i in range(class_start, class_end):
            if i >= len(lines):
                break
            if re.search('self\\.' + re.escape(property_name) + '\\s*=', lines[i]):
                return (i + 1, i + 1)
        
        return (0, 0)

    def replace_element(self, original_code: str, property_name: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Replace a property in Python code"""
        (start_line, end_line) = self.find_element(original_code, property_name, parent_name)
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
        property_indent_level = len(class_indent) // 4 + 1
        formatted_property = self.format_element(new_element, property_indent_level)
        return self.replace_lines(original_code, adjusted_start, end_line, formatted_property)

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add a property to a Python class"""
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
        property_indent_level = len(class_indent) // 4 + 1
        formatted_property = self.format_element(new_element, property_indent_level)
        is_property_decorator = '@property' in new_element
        if is_property_decorator:
            insertion_point = class_end
            if insertion_point > len(lines):
                insertion_point = len(lines)
            result_lines = lines[:insertion_point]
            if result_lines and result_lines[-1].strip():
                result_lines.append('')
            result_lines.append(formatted_property)
            result_lines.extend(lines[insertion_point:])
        else:
            found_init = False
            method_line = class_end
            for i in range(class_start, class_end):
                if i >= len(lines):
                    break
                line = lines[i].strip()
                if line.startswith('def __init__'):
                    found_init = True
                elif found_init and line.startswith('self.'):
                    continue
                elif line.startswith('def '):
                    method_line = i
                    break
            result_lines = lines[:method_line]
            if result_lines and result_lines[-1].strip() and (result_lines[-1].strip() != ':'):
                result_lines.append('')
            result_lines.append(formatted_property)
            if method_line < class_end:
                result_lines.append('')
            result_lines.extend(lines[method_line:])
        return '\n'.join(result_lines)

    def remove_element(self, original_code: str, property_name: str, parent_name: Optional[str]=None) -> str:
        """Remove a property from a Python class"""
        (start_line, end_line) = self.find_element(original_code, property_name, parent_name)
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