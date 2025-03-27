"""
Base manipulator for standardizing manipulation across languages.
"""
import re
import logging
from typing import Tuple, Optional, List, Type, Dict, Any
from abc import ABC, abstractmethod

from codehem.models.enums import CodeElementType
from codehem.core.formatting.formatter import BaseFormatter

logger = logging.getLogger(__name__)

class ManipulatorBase(ABC):
    """Base class for all language-specific manipulators."""
    LANGUAGE_CODE: str = ''
    ELEMENT_TYPE: Optional[CodeElementType] = None
    COMMENT_MARKERS: List[str] = []
    DECORATOR_MARKERS: List[str] = []

    def __init__(self, language_code: str = None, element_type: CodeElementType = None, 
                 formatter: BaseFormatter = None, extraction_service = None):
        """Initialize the manipulator."""
        self.language_code = language_code or self.LANGUAGE_CODE
        self.element_type = element_type or self.ELEMENT_TYPE
        self._extraction_service = extraction_service
        self.formatter = formatter or BaseFormatter()

        if not self.language_code:
            raise ValueError("Manipulator requires a language_code.")

    @property
    def extraction_service(self):
        """Get extraction service, creating it on demand."""
        if self._extraction_service is None:
            # Deferred import to avoid circular dependencies
            from codehem.core.extraction import ExtractionService
            try:
                self._extraction_service = ExtractionService(self.language_code)
            except ValueError as e:
                 logger.error(f"Failed to create ExtractionService for {self.language_code}: {e}")
                 raise
        return self._extraction_service

    # --- Core Abstract Methods ---

    @abstractmethod
    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add an element to the code. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement add_element")

    # --- Common Workflow Methods ---

    def find_element(self, code: str, element_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find an element in the code using the Extraction Service."""
        if not self.element_type:
            logger.warning("find_element called without ELEMENT_TYPE set.")
            return (0, 0)
        try:
            return self.extraction_service.find_element(code, self.element_type.value, element_name, parent_name)
        except Exception as e:
            logger.error(f"Error finding element ({self.element_type.value}, {element_name}, {parent_name}): {e}")
            return (0, 0)

    def format_element(self, element_code: str, indent_level: int = 0) -> str:
        """Format a code element using the language-specific formatter."""
        if hasattr(self.formatter, 'format_element') and self.element_type:
             # Use formatter to get properly formatted code
             dedented_code = self.formatter.dedent(element_code)
             formatted_no_base_indent = self.formatter.format_element(self.element_type.value, dedented_code)
             base_indent = self.formatter.indent_string * indent_level
             return self.apply_indentation(formatted_no_base_indent, base_indent)

        # Fallback to generic indentation
        indent = ' ' * (self.formatter.indent_size if hasattr(self.formatter, 'indent_size') else 4) * indent_level
        return self.apply_indentation(element_code.strip(), indent)

    def replace_element(self, original_code: str, element_name: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Replace an element in the code, handling decorators/comments."""
        logger.debug(f"Replacing {self.element_type} '{element_name}' (parent: {parent_name})")
        start_line, end_line = self.find_element(original_code, element_name, parent_name)

        if start_line == 0 and end_line == 0:
            logger.info(f"{self.element_type} '{element_name}' not found. Attempting to add.")
            can_add = parent_name or self.element_type in [
                CodeElementType.FUNCTION, CodeElementType.CLASS, CodeElementType.IMPORT
            ]
            if can_add:
                 try:
                     return self.add_element(original_code, new_element, parent_name)
                 except Exception as e:
                     logger.error(f"Error adding missing element '{element_name}': {e}")
                     return original_code
            else:
                 logger.warning(f"Element '{element_name}' not found and cannot be added without parent context.")
                 return original_code

        lines = original_code.splitlines()
        adjusted_start = self._adjust_start_line(lines, start_line)
        logger.debug(f"Found element at lines {start_line}-{end_line}. Adjusted start: {adjusted_start}")

        indent_level = self.get_element_indent_level(original_code, adjusted_start, parent_name)
        formatted_element = self.format_element(new_element, indent_level)

        return self.replace_lines(original_code, adjusted_start, end_line, formatted_element)

    def remove_element(self, original_code: str, element_name: str, parent_name: Optional[str]=None) -> str:
        """Remove an element from the code, handling decorators/comments."""
        logger.debug(f"Removing {self.element_type} '{element_name}' (parent: {parent_name})")
        start_line, end_line = self.find_element(original_code, element_name, parent_name)

        if start_line == 0 and end_line == 0:
            logger.warning(f"Element '{element_name}' not found. Cannot remove.")
            return original_code

        lines = original_code.splitlines()
        adjusted_start = self._adjust_start_line(lines, start_line)
        logger.debug(f"Found element for removal at lines {start_line}-{end_line}. Adjusted: {adjusted_start}")

        return self.replace_lines(original_code, adjusted_start, end_line, '')

    # --- Helper Methods ---

    def get_element_indent_level(self, code: str, element_start_line: int, parent_name: Optional[str]=None) -> int:
        """Calculate indentation level for an element."""
        if element_start_line <= 0:
            return 0
        lines = code.splitlines()
        if element_start_line > len(lines):
             return 0
        line_index = element_start_line - 1
        indent_str = self.get_indentation(lines[line_index])
        indent_size = self.formatter.indent_size if hasattr(self.formatter, 'indent_size') else 4
        return len(indent_str) // indent_size if indent_size > 0 else 0

    def _adjust_start_line(self, lines: List[str], start_line: int) -> int:
        """Adjusts the start line to include preceding decorators or comments."""
        adjusted_start = start_line
        # Combine markers for checking
        allowed_prefixes = tuple(self.DECORATOR_MARKERS)
        comment_prefixes = tuple(self.COMMENT_MARKERS)

        # Check lines above the start line
        for i in range(start_line - 2, -1, -1):
            if i >= len(lines): 
                continue
            line = lines[i].strip()

            # Include decorators
            if line.startswith(allowed_prefixes):
                adjusted_start = i + 1
            # Stop at non-empty, non-decorator, non-comment lines
            elif line and not line.startswith(comment_prefixes):
                break
            # Skip empty lines
            elif not line:
                continue

        return adjusted_start

    # --- Static Utility Methods ---

    @staticmethod
    def get_indentation(line: str) -> str:
        """Extract indentation from a line."""
        match = re.match(r'^(\s*)', line)
        return match.group(1) if match else ''

    @staticmethod
    def apply_indentation(content: str, indent: str) -> str:
        """Apply consistent indentation to a block of content."""
        lines = content.splitlines()
        if not lines:
            return ""

        # Find minimum indentation to preserve relative indents
        min_indent_len = float('inf')
        for line in lines:
            if line.strip():
                line_indent_len = len(ManipulatorBase.get_indentation(line))
                min_indent_len = min(min_indent_len, line_indent_len)

        if min_indent_len == float('inf'): # All lines empty
             return "\n".join([indent + line.lstrip() if line.strip() else "" for line in lines])

        result = []
        for line in lines:
            if line.strip():
                current_indent_len = len(ManipulatorBase.get_indentation(line))
                relative_indent = ' ' * (current_indent_len - min_indent_len)
                result.append(f'{indent}{relative_indent}{line.lstrip()}')
            else:
                result.append('') # Preserve empty lines

        return '\n'.join(result)

    @staticmethod
    def replace_lines(original_code: str, start_line: int, end_line: int, new_content: str) -> str:
        """Replace lines between start_line and end_line with new_content."""
        if start_line <= 0 or end_line < start_line:
            logger.error(f"Invalid line range: start={start_line}, end={end_line}")
            return original_code

        lines = original_code.splitlines()

        # Adjust to 0-based index for list slicing
        start_index = start_line - 1
        end_index = end_line

        if start_index >= len(lines):
             logger.warning(f"Start line {start_line} beyond end of code ({len(lines)} lines).")
             return original_code

        # Ensure end_index does not exceed list bounds
        end_index = min(end_index, len(lines))

        result = []
        # Lines before the replacement
        result.extend(lines[:start_index])
        # The new content
        result.extend(new_content.splitlines())
        # Lines after the replacement
        result.extend(lines[end_index:])

        return '\n'.join(result)