import re
from typing import Optional, Tuple, List

from codehem.models.enums import CodeElementType
from codehem.core.registry import element_type_descriptor, manipulator
from codehem.languages.lang_python.manipulator.base import PythonBaseManipulator
from codehem.core.finder.factory import get_code_finder

@manipulator
class PythonImportManipulator(PythonBaseManipulator):
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.IMPORT
    
    def __init__(self):
        self.finder = get_code_finder('python')
    
    def format_element(self, element_code: str, indent_level: int = 0) -> str:
        """Format Python import statements"""
        # Imports should not be indented in Python, ignore indent_level
        lines = element_code.strip().splitlines()
        
        # Sort imports according to PEP 8:
        # 1. Standard library imports
        # 2. Related third party imports
        # 3. Local application/library specific imports
        
        # For now, we'll just keep the original order and formatting
        return '\n'.join(lines)
    
    def find_element(self, code: str, import_name: str, 
                    parent_name: Optional[str] = None) -> Tuple[int, int]:
        """Find an import in Python code"""
        # If import_name is 'all', return the entire imports section
        if import_name == 'all':
            return self.finder.find_imports_section(code)
            
        # Look for the specific import
        lines = code.splitlines()
        for i, line in enumerate(lines):
            # Look for direct import: import X
            if re.match(r'import\s+' + re.escape(import_name) + r'\b', line.strip()):
                return i + 1, i + 1
                
            # Look for from-import: from X import Y
            if re.match(r'from\s+' + re.escape(import_name) + r'\s+import', line.strip()):
                # Check for multi-line imports with parentheses
                if '(' in line and ')' not in line:
                    j = i
                    while j < len(lines) and ')' not in lines[j]:
                        j += 1
                    if j < len(lines):
                        return i + 1, j + 1
                return i + 1, i + 1
        
        return 0, 0
    
    def replace_element(self, original_code: str, import_name: str, 
                       new_element: str, parent_name: Optional[str] = None) -> str:
        """Replace an import in Python code"""
        # If import_name is 'all', replace the entire imports section
        if import_name == 'all':
            start_line, end_line = self.finder.find_imports_section(original_code)
            if start_line == 0 and end_line == 0:
                # No imports section found, add imports at the beginning
                return self.add_element(original_code, new_element)
                
            # Replace the entire imports section
            formatted_imports = self.format_element(new_element)
            return self.replace_lines(original_code, start_line, end_line, formatted_imports)
        
        # Find the specific import
        start_line, end_line = self.find_element(original_code, import_name)
        if start_line == 0 and end_line == 0:
            # Import not found, add it
            return self.add_element(original_code, new_element)
            
        # Replace the specific import
        formatted_import = self.format_element(new_element)
        return self.replace_lines(original_code, start_line, end_line, formatted_import)
        
    def add_element(self, original_code: str, new_element: str,
                   parent_name: Optional[str] = None) -> str:
        """Add an import to Python code"""
        formatted_import = self.format_element(new_element)
        
        # Find existing imports section
        start_line, end_line = self.finder.find_imports_section(original_code)
        if start_line == 0 and end_line == 0:
            # No imports found, add at the beginning of the file
            # But respect docstrings if present
            lines = original_code.splitlines()
            if lines and (lines[0].startswith('"""') or lines[0].startswith("'''")):
                # Find the end of the docstring
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
                    # Add imports after the docstring
                    result_lines = lines[:docstring_end + 1]
                    result_lines.append('')  # Add blank line after docstring
                    result_lines.extend(formatted_import.splitlines())
                    result_lines.append('')  # Add blank line after imports
                    result_lines.extend(lines[docstring_end + 1:])
                    return '\n'.join(result_lines)
            
            # No docstring, add at the beginning
            if formatted_import.endswith('\n'):
                return formatted_import + original_code
            else:
                return formatted_import + '\n\n' + original_code
        else:
            # Add to existing imports section
            lines = original_code.splitlines()
            result_lines = lines[:end_line]
            result_lines.extend(formatted_import.splitlines())
            result_lines.extend(lines[end_line:])
            return '\n'.join(result_lines)
        
    def remove_element(self, original_code: str, import_name: str,
                      parent_name: Optional[str] = None) -> str:
        """Remove an import from Python code"""
        # If import_name is 'all', remove the entire imports section
        if import_name == 'all':
            start_line, end_line = self.finder.find_imports_section(original_code)
            if start_line == 0 and end_line == 0:
                return original_code
                
            return self.replace_lines(original_code, start_line, end_line, '')
        
        # Find the specific import
        start_line, end_line = self.find_element(original_code, import_name)
        if start_line == 0 and end_line == 0:
            return original_code
            
        return self.replace_lines(original_code, start_line, end_line, '')