import re
from typing import Optional, Tuple, List
from codehem.models.enums import CodeElementType
from codehem.core.registry import element_type_descriptor, manipulator
from codehem.languages.lang_python.manipulator.base import PythonBaseManipulator
from codehem.core.extraction import ExtractionService

@manipulator
class PythonImportManipulator(PythonBaseManipulator):
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.IMPORT

    def format_element(self, element_code: str, indent_level: int=0) -> str:
        """Format Python import statements"""
        lines = element_code.strip().splitlines()
        return '\n'.join(lines)

    def find_element(self, code: str, import_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find an import in Python code"""
        extraction_service = ExtractionService(self.LANGUAGE_CODE)
        
        if import_name == 'all':
            # Extract all imports and find the range from the first to the last
            imports = extraction_service.extract_imports(code)
            if not imports:
                return (0, 0)
            
            # If there's a single combined import, return its range
            if len(imports) == 1 and imports[0].get('name') == 'imports':
                range_data = imports[0].get('range', {})
                start_line = range_data.get('start', {}).get('line', 0) + 1
                end_line = range_data.get('end', {}).get('line', 0) + 1
                return (start_line, end_line)
            
            # Otherwise, find the range from the first to the last import
            start_line = float('inf')
            end_line = 0
            for imp in imports:
                range_data = imp.get('range', {})
                imp_start = range_data.get('start', {}).get('line', 0) + 1
                imp_end = range_data.get('end', {}).get('line', 0) + 1
                start_line = min(start_line, imp_start)
                end_line = max(end_line, imp_end)
            
            if start_line == float('inf'):
                return (0, 0)
            
            return (start_line, end_line)
        
        return extraction_service.find_element(code, self.ELEMENT_TYPE.value, import_name)

    def replace_element(self, original_code: str, import_name: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Replace an import in Python code"""
        if import_name == 'all':
            (start_line, end_line) = self.find_element(original_code, 'all')
            if start_line == 0 and end_line == 0:
                return self.add_element(original_code, new_element)
            formatted_imports = self.format_element(new_element)
            return self.replace_lines(original_code, start_line, end_line, formatted_imports)
        (start_line, end_line) = self.find_element(original_code, import_name)
        if start_line == 0 and end_line == 0:
            return self.add_element(original_code, new_element)
        formatted_import = self.format_element(new_element)
        return self.replace_lines(original_code, start_line, end_line, formatted_import)

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add an import to Python code"""
        formatted_import = self.format_element(new_element)
        (start_line, end_line) = self.find_element(original_code, 'all')
        if start_line == 0 and end_line == 0:
            lines = original_code.splitlines()
            if lines and (lines[0].startswith('"""') or lines[0].startswith("'''")):
                docstring_end = 0
                in_docstring = True
                docstring_marker = lines[0].strip()[0:3]
                for (i, line) in enumerate(lines):
                    if i == 0:
                        continue
                    if docstring_marker in line:
                        docstring_end = i
                        in_docstring = False
                        break
                if not in_docstring:
                    result_lines = lines[:docstring_end + 1]
                    result_lines.append('')
                    result_lines.extend(formatted_import.splitlines())
                    result_lines.append('')
                    result_lines.extend(lines[docstring_end + 1:])
                    return '\n'.join(result_lines)
            if formatted_import.endswith('\n'):
                return formatted_import + original_code
            else:
                return formatted_import + '\n\n' + original_code
        else:
            lines = original_code.splitlines()
            result_lines = lines[:end_line]
            result_lines.extend(formatted_import.splitlines())
            result_lines.extend(lines[end_line:])
            return '\n'.join(result_lines)

    def remove_element(self, original_code: str, import_name: str, parent_name: Optional[str]=None) -> str:
        """Remove an import from Python code"""
        if import_name == 'all':
            (start_line, end_line) = self.find_element(original_code, 'all')
            if start_line == 0 and end_line == 0:
                return original_code
            return self.replace_lines(original_code, start_line, end_line, '')
        (start_line, end_line) = self.find_element(original_code, import_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, '')