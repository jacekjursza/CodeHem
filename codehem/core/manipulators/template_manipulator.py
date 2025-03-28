"""
Template pattern for manipulators to standardize language-specific implementations.
"""
import logging
from typing import Optional
from codehem.core.manipulators.manipulator_base import ManipulatorBase

logger = logging.getLogger(__name__)

class TemplateManipulator(ManipulatorBase):
    """
    Template method pattern for manipulators.
    Provides standardized implementations with hooks for language-specific customization.
    """

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add an element to the code following the template pattern."""
        # 1. Preparation
        prepared_code = self._prepare_code_for_addition(original_code, parent_name)
        
        # 2. Format the element
        indent_level = self._determine_indent_level_for_addition(prepared_code, parent_name)
        formatted_element = self.format_element(new_element, indent_level)
        
        # 3. Find insertion point
        insertion_point = self._find_insertion_point(prepared_code, parent_name)
        
        # 4. Perform the insertion (language-specific)
        return self._perform_insertion(prepared_code, formatted_element, insertion_point, parent_name)
    
    def _prepare_code_for_addition(self, code: str, parent_name: Optional[str]=None) -> str:
        """Prepare code for element addition (hook method)."""
        return code
    
    def _determine_indent_level_for_addition(self, code: str, parent_name: Optional[str]=None) -> int:
        """Determine the indentation level for the new element (hook method)."""
        if parent_name:
            # If we're adding to a parent element, increase indentation
            try:
                parent_start, _ = self.find_element(code, parent_name)
                if parent_start > 0:
                    return self.get_element_indent_level(code, parent_start) + 1
            except Exception as e:
                logger.debug(f"Error finding parent indentation: {e}")
        
        # Default indentation for top-level elements
        return 0
    
    def _find_insertion_point(self, code: str, parent_name: Optional[str]=None) -> int:
        """Find the insertion point for the new element (hook method)."""
        if parent_name:
            try:
                _, parent_end = self.find_element(code, parent_name)
                if parent_end > 0:
                    return parent_end
            except Exception as e:
                logger.debug(f"Error finding insertion point: {e}")
        
        # Default: append to the end of the file
        return len(code.splitlines())
    
    def _perform_insertion(self, code: str, formatted_element: str, insertion_point: int, 
                          parent_name: Optional[str]=None) -> str:
        """Perform the actual insertion (hook method)."""
        lines = code.splitlines()
        
        # Default implementation: append the element
        if insertion_point >= len(lines):
            if code and not code.endswith('\n\n'):
                if code.endswith('\n'):
                    result = code + '\n' + formatted_element
                else:
                    result = code + '\n\n' + formatted_element
            else:
                result = code + formatted_element
        else:
            result_lines = lines[:insertion_point]
            if result_lines and result_lines[-1].strip():
                result_lines.append('')
            result_lines.extend(formatted_element.splitlines())
            result_lines.extend(lines[insertion_point:])
            result = '\n'.join(result_lines)
        
        return result