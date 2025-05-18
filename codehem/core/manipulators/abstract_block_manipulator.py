from typing import Optional
from .manipulator_base import ManipulatorBase

class AbstractBlockManipulator(ManipulatorBase):
    """Manipulator with generic block insertion logic."""

    BLOCK_START_TOKEN = '{'

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str] = None) -> str:
        lines = original_code.splitlines()
        insertion_line = len(lines)
        indent_level = 0
        if parent_name:
            start, end = self.find_element(original_code, parent_name)
            if end > 0:
                insertion_line = end
                indent_level = self.get_element_indent_level(original_code, start, parent_name) + 1
        formatted = self.format_element(new_element, indent_level)
        return self.replace_lines(original_code, insertion_line, insertion_line, formatted)
