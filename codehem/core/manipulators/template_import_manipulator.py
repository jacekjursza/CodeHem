"""
Template implementation for import manipulator.
"""
import logging
from typing import Optional, Tuple

from codehem.core.manipulators.template_manipulator import TemplateManipulator
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

class TemplateImportManipulator(TemplateManipulator):
    """Template implementation for import manipulation."""
    ELEMENT_TYPE = CodeElementType.IMPORT
    
    def find_element(self, code: str, import_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find an import with special handling for 'all' imports."""
        if import_name == 'all':
            # Find all imports as a block
            imports = self.extraction_service.extract_imports(code)
            if not imports:
                return (0, 0)
                
            if len(imports) == 1 and imports[0].get('name') == 'imports':
                range_data = imports[0].get('range', {})
                start_line = range_data.get('start', {}).get('line', 0)
                end_line = range_data.get('end', {}).get('line', 0)
                return (start_line, end_line)
                
            # Find min/max lines of all imports
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
            
        # Regular import search
        return self.extraction_service.find_element(code, self.ELEMENT_TYPE.value, import_name)
    
    def _find_insertion_point(self, code: str, parent_name: Optional[str]=None) -> int:
        """Imports go at the top of the file, after docstrings if present."""
        lines = code.splitlines()
        
        # Check for docstring
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
                return docstring_end + 1
                
        # Check existing imports
        start_line, end_line = self.find_element(code, 'all')
        if end_line > 0:
            return end_line
            
        # Default: top of file
        return 0
        
    def _perform_insertion(self, code: str, formatted_element: str, insertion_point: int, 
                          parent_name: Optional[str]=None) -> str:
        """Insert imports at the appropriate position."""
        lines = code.splitlines()
        
        if insertion_point == 0:
            # Add at the beginning
            return formatted_element + '\n\n' + code
            
        result_lines = lines[:insertion_point]
        result_lines.extend(formatted_element.splitlines())
        result_lines.extend(lines[insertion_point:])
        
        return '\n'.join(result_lines)