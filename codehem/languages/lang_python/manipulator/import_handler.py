"""
Python import manipulator implementation.
"""
import re
import logging
from typing import Optional, Tuple, List

from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.languages.lang_python.manipulator.base import PythonManipulatorBase

logger = logging.getLogger(__name__)

@manipulator
class PythonImportManipulator(PythonManipulatorBase):
    """Manipulator for Python imports."""
    ELEMENT_TYPE = CodeElementType.IMPORT

    def find_element(self, code: str, import_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find an import in Python code, with special handling for 'all' imports."""
        if import_name == 'all':
            imports = self.extraction_service.extract_imports(code)
            if not imports:
                return (0, 0)
                
            # Handle single combined import section
            if len(imports) == 1 and imports[0].get('name') == 'imports':
                range_data = imports[0].get('range', {})
                start_line = range_data.get('start', {}).get('line', 0)
                end_line = range_data.get('end', {}).get('line', 0)
                return (start_line, end_line)
                
            # Find min/max lines for scattered imports
            start_line = float('inf')
            end_line = 0
            for imp in imports:
                range_data = imp.get('range', {})
                imp_start = range_data.get('start', {}).get('line', 0)
                imp_end = range_data.get('end', {}).get('line', 0)
                start_line = min(start_line, imp_start)
                end_line = max(end_line, imp_end)
                
            if start_line == float('inf'):
                return (0, 0)
                
            return (start_line, end_line)
        
        # Regular import
        return self.extraction_service.find_element(code, self.ELEMENT_TYPE.value, import_name)

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add an import to Python code."""
        # Format imports consistently
        formatted_import = self.format_element(new_element, indent_level=0)
        
        # Try to find existing imports section
        start_line, end_line = self.find_element(original_code, 'all')
        
        if start_line == 0 and end_line == 0:
            # No imports yet - add at beginning with special handling for docstrings
            lines = original_code.splitlines() if original_code else []
            
            # Check for docstring at beginning
            if lines and (lines[0].startswith('"""') or lines[0].startswith("'''")):
                docstring_end = 0
                in_docstring = True
                docstring_marker = lines[0].strip()[0:3]
                
                for i, line in enumerate(lines):
                    if i == 0:
                        continue
                    if docstring_marker in line:
                        docstring_end = i
                        in_docstring = False
                        break
                        
                if not in_docstring:
                    # Insert after docstring
                    result_lines = lines[:docstring_end + 1]
                    result_lines.append('')
                    result_lines.extend(formatted_import.splitlines())
                    result_lines.append('')
                    result_lines.extend(lines[docstring_end + 1:])
                    return '\n'.join(result_lines)
            
            # No docstring or couldn't find end - insert at beginning
            return formatted_import + '\n\n' + (original_code or '')
        else:
            # Append to existing imports section
            lines = original_code.splitlines()
            result_lines = lines[:end_line]
            result_lines.extend(formatted_import.splitlines())
            result_lines.extend(lines[end_line:])
            return '\n'.join(result_lines)

    def replace_element(self, original_code: str, import_name: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Replace an import in Python code, with special handling for 'all' imports."""
        if import_name == 'all':
            # Replace entire imports section
            start_line, end_line = self.find_element(original_code, 'all')
            if start_line == 0 and end_line == 0:
                return self.add_element(original_code, new_element)
                
            formatted_imports = self.format_element(new_element, indent_level=0)
            return self.replace_lines(original_code, start_line, end_line, formatted_imports)
        
        # Regular import replacement
        return super().replace_element(original_code, import_name, new_element, parent_name)

    def remove_element(self, original_code: str, import_name: str, parent_name: Optional[str]=None) -> str:
        """Remove an import from Python code, with special handling for 'all' imports."""
        if import_name == 'all':
            # Remove entire imports section
            start_line, end_line = self.find_element(original_code, 'all')
            if start_line == 0 and end_line == 0:
                return original_code
                
            return self.replace_lines(original_code, start_line, end_line, '')
        
        # Regular import removal
        return super().remove_element(original_code, import_name, parent_name)