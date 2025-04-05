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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def replace_element(self, original_code: str, name: str, new_code: str, parent_name: Optional[str] = None) -> str:
        """
        Replace an existing element (function, method, class, import) by name.
        If not found, insert the new element.

        Args:
            original_code: Original source code
            name: Name of the element to replace
            new_code: New content for the element
            parent_name: Optional parent element name (e.g., class name for methods)

        Returns:
            Modified code with element replaced or added
        """
        import re

        code_lines = original_code.splitlines()
        start_idx = None
        end_idx = None

        # Special case: replace all imports block if name is 'all' or '__imports__'
        if name in ('all', '__imports__'):
            import_start = None
            import_end = None
            inside_imports = False
            for idx, line in enumerate(code_lines):
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    if import_start is None:
                        import_start = idx
                    import_end = idx + 1
                    inside_imports = True
                elif inside_imports:
                    # Stop at first non-import after imports block
                    break
            if import_start is not None:
                start_idx = import_start
                end_idx = import_end
            else:
                # No imports found, insert at top
                start_idx = 0
                end_idx = 0

        else:
            # Helper to find element range within given lines, including decorators
            def find_element_range_with_decorators(lines, element_name, indent_level=0):
                pattern = re.compile(rf'^(\s*)def\s+{re.escape(element_name)}\s*\(')
                start = None
                end = None
                inside = False
                current_indent = None
                decorator_start = None
                for idx, line in enumerate(lines):
                    match = pattern.match(line)
                    if match:
                        current_indent = len(match.group(1))
                        # Backtrack to include decorators
                        dec_idx = idx - 1
                        while dec_idx >= 0:
                            prev_line = lines[dec_idx]
                            if prev_line.strip().startswith("@"):
                                dec_idx -= 1
                            elif prev_line.strip() == "":
                                dec_idx -= 1
                            else:
                                break
                        decorator_start = dec_idx + 1
                        if indent_level == 0 or current_indent == indent_level:
                            start = decorator_start
                            inside = True
                            continue
                    if inside:
                        stripped = line.strip()
                        if stripped == "":
                            continue
                        line_indent = len(line) - len(line.lstrip())
                        if line_indent <= current_indent and not line.lstrip().startswith("@"):
                            end = idx
                            break
                if inside and end is None:
                    end = len(lines)
                return (start, end) if start is not None else (None, None)

            # If parent_name is provided, find its block first
            if parent_name:
                class_pattern = re.compile(rf'^(\s*)class\s+{re.escape(parent_name)}\s*[\(:]')
                class_start = None
                class_end = None
                indent_level = None
                inside_class = False
                for idx, line in enumerate(code_lines):
                    match = class_pattern.match(line)
                    if match:
                        indent_level = len(match.group(1))
                        class_start = idx
                        inside_class = True
                        continue
                    if inside_class:
                        stripped = line.strip()
                        if stripped == "":
                            continue
                        line_indent = len(line) - len(line.lstrip())
                        if line_indent <= indent_level and not line.lstrip().startswith("@"):
                            class_end = idx
                            break
                if inside_class and class_end is None:
                    class_end = len(code_lines)

                if class_start is not None:
                    rel_start, rel_end = find_element_range_with_decorators(
                        code_lines[class_start + 1:class_end], name, indent_level + 4
                    )
                    if rel_start is not None:
                        start_idx = class_start + 1 + rel_start
                        end_idx = class_start + 1 + rel_end
            else:
                # Search globally for function first
                start_idx, end_idx = find_element_range_with_decorators(code_lines, name)
                if start_idx is None:
                    # Then try class
                    class_pattern = re.compile(rf'^(\s*)class\s+{re.escape(name)}\s*[\(:]')
                    inside = False
                    indent_level = None
                    for idx, line in enumerate(code_lines):
                        match = class_pattern.match(line)
                        if match:
                            indent_level = len(match.group(1))
                            start_idx = idx
                            inside = True
                            continue
                        if inside:
                            stripped = line.strip()
                            if stripped == "":
                                continue
                            line_indent = len(line) - len(line.lstrip())
                            if line_indent <= indent_level and not line.lstrip().startswith("@"):
                                end_idx = idx
                                break
                    if inside and end_idx is None:
                        end_idx = len(code_lines)

        if start_idx is not None and end_idx is not None:
            before = code_lines[:start_idx]
            after = code_lines[end_idx:]
            new_code_lines = new_code.strip('\n').splitlines()
            # Adjust indentation to match existing element
            indent = ''
            if before and before[-1].startswith(' '):
                indent = re.match(r'^(\s*)', before[-1]).group(1)
            elif start_idx < len(code_lines):
                indent = re.match(r'^(\s*)', code_lines[start_idx]).group(1)
            new_code_lines = [indent + line if line.strip() else line for line in new_code_lines]
            result_lines = before + new_code_lines + after
            return '\n'.join(result_lines)
        else:
            # Element not found, fallback to add
            return self.add_element(original_code, new_code, parent_name)

    def __init__(self, insert_blank_line_before_element: bool = True, insert_blank_line_after_element: bool = False, handle_docstrings_special: bool = False):
        self.insert_blank_line_before_element = insert_blank_line_before_element
        self.insert_blank_line_after_element = insert_blank_line_after_element
        self.handle_docstrings_special = handle_docstrings_special

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        import re

        lines = original_code.splitlines()
        indent_level = 0
        insertion_idx = len(lines)

        if parent_name:
            # Find class block to insert inside
            class_pattern = re.compile(rf'^(\s*)class\s+{re.escape(parent_name)}\s*[\(:]')
            class_start = None
            class_end = None
            indent = ''
            inside_class = False
            for idx, line in enumerate(lines):
                match = class_pattern.match(line)
                if match:
                    indent = match.group(1)
                    class_start = idx
                    inside_class = True
                    continue
                if inside_class:
                    stripped = line.strip()
                    if stripped == "":
                        continue
                    line_indent = len(line) - len(line.lstrip())
                    if line_indent <= len(indent) and not line.lstrip().startswith("@"):
                        class_end = idx
                        break
            if inside_class and class_end is None:
                class_end = len(lines)
            if class_start is not None:
                indent_level = len(indent) + 4
                insertion_idx = class_end
        else:
            # No parent, insert after imports and module docstring
            insertion_idx = 0
            in_docstring = False
            for idx, line in enumerate(lines):
                stripped = line.strip()
                if idx == 0 and (stripped.startswith('"""') or stripped.startswith("'''")):
                    in_docstring = True
                    continue
                if in_docstring:
                    if stripped.endswith('"""') or stripped.endswith("'''"):
                        in_docstring = False
                    continue
                if stripped.startswith('import ') or stripped.startswith('from '):
                    insertion_idx = idx + 1
                    continue
                if stripped == "":
                    continue
                break  # stop at first non-import, non-docstring line

        # Prepare formatted element
        formatted_element = self.format_element(new_element, indent_level)

        # Insert with blank lines before and after if needed
        before = lines[:insertion_idx]
        after = lines[insertion_idx:]
        insert_lines = formatted_element.strip('\n').splitlines()

        # Add blank line before if not at start and previous line is not blank
        if before and before[-1].strip() != "":
            insert_lines = [""] + insert_lines
        # Add blank line after if not at end and next line is not blank
        if after and after[0].strip() != "":
            insert_lines = insert_lines + [""]

        new_lines = before + insert_lines + after
        return "\n".join(new_lines)

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

    def _perform_insertion(self, code: str, formatted_element: str, insertion_point: int, parent_name: Optional[str]=None) -> str:
        lines = code.splitlines()

        if insertion_point >= len(lines):
            result = self._insert_at_end(code, formatted_element)
        else:
            result = self._insert_in_middle(lines, formatted_element, insertion_point)

        return result

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
