"""
Template pattern for manipulators to standardize language-specific implementations.
"""
import logging
from typing import Optional

from codehem.models.enums import CodeElementType
from codehem.core.formatting.formatter import BaseFormatter
from codehem.core.manipulators.manipulator_base import ManipulatorBase

logger = logging.getLogger(__name__)

class TemplateManipulator(ManipulatorBase):
    """
    Template method pattern for manipulators.
    Provides standardized implementations with hooks for language-specific customization.
    """

    def __init__(
        self,
        language_code: str = None,
        element_type: CodeElementType = None,
        formatter: BaseFormatter = None,
        extraction_service=None,
        insert_blank_line_before_element: bool = True,
        insert_blank_line_after_element: bool = True,
        handle_docstrings_special: bool = False,
    ):
        """
        Initialize TemplateManipulator, passing necessary args to ManipulatorBase
        and setting blank line preferences. Defaulting to adding blank lines
        before and after elements.
        """
        # Call super init correctly, passing arguments it expects
        super().__init__(
            language_code=language_code,
            element_type=element_type,
            formatter=formatter,
            extraction_service=extraction_service,
        )
        # Set blank line preferences (defaulting after to True now)
        self.insert_blank_line_before_element = insert_blank_line_before_element
        self.insert_blank_line_after_element = insert_blank_line_after_element
        self.handle_docstrings_special = handle_docstrings_special
        logger.debug(
            f"TemplateManipulator initialized for {self.language_code}/{self.element_type} with blank line settings: before={self.insert_blank_line_before_element}, after={self.insert_blank_line_after_element}"
        )


    def replace_element(self, original_code: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Replace an existing element (function, method, class, import) by name using ExtractionService.
        If not found, insert the new element by calling add_element.
        [DEBUGGING: Added logging for find_element result]

        Args:
        original_code: Original source code
        name: Name of the element to replace (or 'all' for imports)
        new_code: New content for the element
        parent_name: Optional parent element name (e.g., class name for methods)

        Returns:
        Modified code with element replaced or added
        """
        logger.debug(f"[replace_element] Attempting to find element '{name}' (type: {self.element_type}, parent: {parent_name})")

        # Use the find_element method (which might be overridden, e.g., for imports)
        start_line, end_line = self.find_element(original_code, name, parent_name)

        # <<< DEBUG LOGGING START >>>
        # Log the result clearly to diagnose test failures
        logger.info(f"DIAGNOSTIC: find_element(name='{name}', parent='{parent_name}') returned: start_line={start_line}, end_line={end_line}")
        # <<< DEBUG LOGGING END >>>

        if start_line > 0 and end_line >= start_line:
            # Element found, proceed with replacement
            logger.info(f"[replace_element] Found existing element '{name}' at lines {start_line}-{end_line}. Replacing.")
            lines = original_code.splitlines()

            # Adjust start line to include decorators/comments
            adjusted_start = self._adjust_start_line(lines, start_line)
            logger.debug(f'[replace_element] Original start line: {start_line}, Adjusted start line (for comments/decorators): {adjusted_start}')

            # Determine indentation level based on the adjusted start line
            indent_level = self.get_element_indent_level(original_code, adjusted_start, parent_name)
            logger.debug(f'[replace_element] Determined indent level: {indent_level}')

            # Format the new code snippet with the determined indentation
            formatted_element = self.format_element(new_code, indent_level)
            logger.debug(f"[replace_element] Formatted element for replacement:\n{formatted_element}")

            # Replace the lines in the original code
            return self.replace_lines(original_code, adjusted_start, end_line, formatted_element)
        else:
            # Element not found, attempt to add it
            logger.info(f"[replace_element] Element '{name}' not found for replacement. Attempting to add via self.add_element.")
            try:
                # Ensure add_element handles different element types correctly
                # It should find the right insertion point based on type/parent
                return self.add_element(original_code, new_code, parent_name)
            except Exception as e:
                logger.error(f"[replace_element] Error adding element '{name}' after failing to find it for replacement: {e}", exc_info=True)
                # Return original code if adding fails
                return original_code


    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """
        Adds a new element to the code, finding an appropriate insertion point and indentation.

        Args:
        original_code: Original source code string.
        new_element: The code snippet for the new element.
        parent_name: Optional name of the parent element (e.g., class name).

        Returns:
        Modified code string with the new element added.
        """
        logger.info(f"Adding element (type: {self.element_type}, parent: {parent_name})")

        # Prepare the original code (e.g., ensure trailing newline)
        prepared_code = self._prepare_code_for_addition(original_code)
        lines = prepared_code.splitlines()

        # Determine the indentation level for the new element
        # Note: _determine_indent_level_for_addition might need specific overrides per element type
        indent_level = self._determine_indent_level_for_addition(prepared_code, parent_name)
        logger.debug(f"Determined indent level: {indent_level}")

        # Find the insertion point (line number, 1-based)
        # Note: _find_insertion_point needs specific overrides per element type
        # It should return the line *before* which the new element should be inserted.
        insertion_line_num = self._find_insertion_point(prepared_code, parent_name)
        logger.debug(f"Determined insertion line number: {insertion_line_num}")

        # Ensure insertion_line_num is a valid index (0-based) for list insertion
        # If _find_insertion_point returns len(lines), it means append at the end.
        # If it returns 0, it means insert at the beginning.
        insertion_idx = min(max(0, insertion_line_num), len(lines))

        # Format the new element code with the correct indentation
        formatted_element = self.format_element(new_element, indent_level)
        logger.debug(f"Formatted element:\n{formatted_element}")

        # Perform the insertion using the refined helper method
        return self._perform_insertion(prepared_code, formatted_element, insertion_idx, parent_name)

    def _prepare_code_for_addition(self, code: str, parent_name: Optional[str]=None) -> str:
        return code

    def _determine_indent_level_for_addition(self, code: str, parent_name: Optional[str]=None) -> int:
        if parent_name:
            try:
                parent_start, _ = self.find_element(code, parent_name)
                if parent_start > 0:
                    return self.get_element_indent_level(code, parent_start) + 1
            except Exception as e:
                logger.debug(f"Error finding parent indentation: {e}")
        return 0

    def _find_insertion_point(self, code: str, parent_name: Optional[str]=None) -> int:
        if parent_name:
            try:
                _, parent_end = self.find_element(code, parent_name)
                if parent_end > 0:
                    return parent_end
            except Exception as e:
                logger.debug(f"Error finding insertion point: {e}")
        return len(code.splitlines())

    def _perform_insertion(self, code: str, formatted_element: str, insertion_idx: int, parent_name: Optional[str]=None) -> str:
        """
        Inserts the formatted element into the code at the specified index,
        handling blank lines appropriately.

        Args:
        code: Original source code string (potentially prepared).
        formatted_element: The pre-formatted code snippet to insert.
        insertion_idx: The 0-based line index where insertion should occur.
        parent_name: Optional parent name (used for context, e.g., logging).

        Returns:
        Modified code string.
        """
        lines = code.splitlines()
        new_element_lines = formatted_element.splitlines()

        # Ensure insertion index is within bounds
        insertion_idx = min(max(0, insertion_idx), len(lines))

        # Build the resulting lines
        result_lines = lines[:insertion_idx]

        # Add blank line before if needed
        needs_blank_before = self.insert_blank_line_before_element and \
                             insertion_idx > 0 and \
                             result_lines and \
                             result_lines[-1].strip() != '' and \
                             not formatted_element.startswith('\n') # Avoid double blank if snippet starts with one

        # Check if the *previous actual code line* is a decorator/comment if inserting method/function
        is_func_or_method = self.element_type in [CodeElementType.FUNCTION, CodeElementType.METHOD, CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER]
        if needs_blank_before and is_func_or_method:
             prev_code_line_idx = insertion_idx -1
             while prev_code_line_idx >= 0 and not lines[prev_code_line_idx].strip():
                  prev_code_line_idx -= 1
             if prev_code_line_idx >=0 and lines[prev_code_line_idx].strip().startswith(tuple(self.DECORATOR_MARKERS + self.COMMENT_MARKERS)):
                  needs_blank_before = False # Don't add blank line right after decorator/comment block

        if needs_blank_before:
            logger.debug(f"Adding blank line before insertion at index {insertion_idx}")
            result_lines.append('')

        # Add the new element lines
        result_lines.extend(new_element_lines)

        # Add blank line after if needed
        needs_blank_after = self.insert_blank_line_after_element and \
                            insertion_idx < len(lines) and \
                            lines[insertion_idx].strip() != '' and \
                            not formatted_element.endswith('\n\n') # Avoid double blank

        # Also add blank line if inserting at the very end and configured to do so
        is_inserting_at_end = insertion_idx == len(lines)
        if is_inserting_at_end and self.insert_blank_line_after_element:
             needs_blank_after = True

        if needs_blank_after:
            # Check if the element itself ends with a blank line
            if not (new_element_lines and not new_element_lines[-1].strip()):
                 logger.debug(f"Adding blank line after insertion.")
                 result_lines.append('')
            else:
                 logger.debug(f"Skipping blank line after insertion, element already ends with one.")

        # Add the rest of the original lines
        result_lines.extend(lines[insertion_idx:])

        # Join lines and ensure trailing newline
        final_code = '\n'.join(result_lines)
        if not final_code.endswith('\n'):
            final_code += '\n'

        return final_code

    def _insert_at_end(self, code: str, formatted_element: str) -> str:
        if self.should_insert_blank_line_before_at_end(code):
            if code.endswith('\n'):
                return code + '\n' + formatted_element
            else:
                return code + '\n\n' + formatted_element
        else:
            return code + formatted_element

    def _insert_in_middle(self, lines: list, formatted_element: str, insertion_point: int) -> str:
        result_lines = lines[:insertion_point]
        if self.should_insert_blank_line_before_in_middle(result_lines):
            result_lines.append('')
        result_lines.extend(formatted_element.splitlines())
        result_lines.extend(lines[insertion_point:])
        return '\n'.join(result_lines)

    def should_insert_blank_line_before_at_end(self, code: str) -> bool:
        if not self.insert_blank_line_before_element:
            return False
        return code and not code.endswith('\n\n')

    def should_insert_blank_line_before_in_middle(self, result_lines: list) -> bool:
        if not self.insert_blank_line_before_element:
            return False
        return result_lines and result_lines[-1].strip() != ''
