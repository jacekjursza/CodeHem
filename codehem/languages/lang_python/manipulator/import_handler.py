"""
Python import manipulator implementation.
"""
import re
import logging
from typing import Optional, Tuple, List
from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.core.manipulators.template_import_manipulator import TemplateImportManipulator

logger = logging.getLogger(__name__)

@manipulator
class PythonImportManipulator(TemplateImportManipulator):
    """Manipulator for Python imports."""
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.IMPORT
    COMMENT_MARKERS = ['#']
    
    def _perform_insertion(self, code: str, formatted_element: str, insertion_point: int, 
                          parent_name: Optional[str]=None) -> str:
        """Add an import to Python code with proper spacing."""
        lines = code.splitlines() if code else []
        
        if insertion_point == 0:
            # Handle docstrings at the start of the file
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
                    result_lines = lines[:docstring_end + 1]
                    result_lines.append('')
                    result_lines.extend(formatted_element.splitlines())
                    result_lines.append('')
                    result_lines.extend(lines[docstring_end + 1:])
                    return '\n'.join(result_lines)
                    
            # Add at the beginning if no docstring or complete docstring not found
            return formatted_element + '\n\n' + (code or '')
            
        # Handle insertion after existing imports or at specific point
        result_lines = lines[:insertion_point]
        result_lines.extend(formatted_element.splitlines())
        result_lines.extend(lines[insertion_point:])
        
        return '\n'.join(result_lines)