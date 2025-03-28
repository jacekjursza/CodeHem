"""
Base manipulator for Python-specific manipulators.
"""
import logging
from typing import Optional, Tuple

from codehem.core.manipulator_base import ManipulatorBase
from codehem.core.formatting.formatter import BaseFormatter
from codehem.core.registry import registry
from codehem.models.enums import CodeElementType
from codehem.languages.lang_python.formatting.python_formatter import PythonFormatter
logger = logging.getLogger(__name__)

class PythonManipulatorBase(ManipulatorBase):
    """Base class for Python-specific manipulators."""
    LANGUAGE_CODE = 'python'
    COMMENT_MARKERS = ['#']
    DECORATOR_MARKERS = ['@']

    def __init__(self, element_type: CodeElementType = None, formatter: BaseFormatter = None, 
                 extraction_service = None):
        """Initialize Python manipulator with appropriate formatter."""
        if formatter is None:
            try:
                lang_service = registry.get_language_service('python')
                if lang_service and hasattr(lang_service, 'formatter'):
                     formatter = lang_service.formatter
                else:

                     formatter = PythonFormatter()
            except Exception as e:
                logger.warning(f"Could not get PythonFormatter: {e}")

        super().__init__(
            language_code="python",
            element_type=element_type,
            formatter=formatter,
            extraction_service=extraction_service,
        )

    def format_element(self, element_code: str, indent_level: int = 0) -> str:
        """Format a Python element, ensuring proper indentation."""
        if hasattr(self.formatter, "format_element") and self.element_type:
            # First properly dedent the code to remove any existing indentation
            dedented_code = self.formatter.dedent(element_code)
            # Then format it with the formatter
            formatted_no_base_indent = self.formatter.format_element(
                self.element_type.value, dedented_code
            )
            # Finally, apply the correct indentation level
            base_indent = self.formatter.indent_string * indent_level
            return self.apply_indentation(formatted_no_base_indent, base_indent)
        indent = (
            " "
            * (
                self.formatter.indent_size
                if hasattr(self.formatter, "indent_size")
                else 4
            )
            * indent_level
        )
        # Ensure we dedent before applying new indentation
        dedented_code = self.formatter.dedent(element_code.strip())
        return self.apply_indentation(dedented_code, indent)

    def get_element_indent_level(self, code: str, element_start_line: int, parent_name: Optional[str]=None) -> int:
        """Calculate indentation level for Python elements, considering parent classes."""
        # For elements with parent classes
        if parent_name:
            try:
                # Find parent class indentation
                class_start, _ = self.extraction_service.find_element(code, CodeElementType.CLASS.value, parent_name)
                if class_start > 0:
                    lines = code.splitlines()
                    if class_start - 1 < len(lines):
                        class_indent_str = self.get_indentation(lines[class_start - 1])
                        indent_size = getattr(self.formatter, 'indent_size', 4)
                        class_indent_level = len(class_indent_str) // indent_size
                        # Element inside class is one level deeper
                        return class_indent_level + 1
            except Exception as e:
                logger.error(f"Error determining parent class indent: {e}")

        # Fallback to base implementation
        return super().get_element_indent_level(code, element_start_line, parent_name)