from finder.factory import get_code_finder
from manipulator.abstract import AbstractCodeManipulator


class BaseCodeManipulator(AbstractCodeManipulator):

    def __init__(self, language: str='python'):
        self.language = language
        self.finder = get_code_finder(language)

    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        (start_line, end_line) = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, new_function)

    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        """Replace a class definition with new content."""
        # Find the class position in the original code
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code

        # Format the new content properly before replacement
        # For class replacements, we need to preserve indentation and structure

        # Get lines from original content to extract indentation
        orig_lines = original_code.splitlines()

        # Find the actual class line (with indentation)
        class_line_idx = None
        for i, line in enumerate(orig_lines):
            if line.strip().startswith('class ' + class_name) and (
                line.strip().endswith(':') or 
                line.strip().endswith('(') or 
                '(' in line.strip()
            ):
                class_line_idx = i
                break

        # If we couldn't find the class by this method, return original
        if class_line_idx is None:
            return self.replace_lines(original_code, start_line, end_line, new_class_content)

        # Extract indentation from the original class definition
        orig_indent = ''
        if class_line_idx is not None and class_line_idx < len(orig_lines):
            line = orig_lines[class_line_idx]
            orig_indent = line[:len(line) - len(line.lstrip())]

        # Process new content to maintain proper indentation
        new_lines = new_class_content.splitlines()

        # Strip empty lines at beginning and end
        while new_lines and not new_lines[0].strip():
            new_lines.pop(0)
        while new_lines and not new_lines[-1].strip():
            new_lines.pop()

        # Format each line with proper indentation
        formatted_lines = []
        for line in new_lines:
            if not line.strip():
                formatted_lines.append('')
                continue

            # Determine indentation level
            stripped = line.strip()
            if stripped.startswith('class '):
                # Class definition gets original indentation
                formatted_lines.append(orig_indent + stripped)
            else:
                # Other lines get additional indentation to maintain structure
                # Remove existing indentation first
                line_indent = len(line) - len(stripped)
                if line_indent > 0:
                    # Create indentation that's relative to class indentation
                    formatted_lines.append(orig_indent + '    ' + stripped)
                else:
                    formatted_lines.append(orig_indent + '    ' + stripped)

        # Join formatted lines and replace
        formatted_content = '\n'.join(formatted_lines)

        # Use direct string manipulation for more precise replacement
        lines = orig_lines.copy()
        lines[class_line_idx:class_line_idx + (end_line - start_line) + 1] = formatted_lines
        return '\n'.join(lines)

    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, new_method)

    def replace_property(self, original_code: str, class_name: str, property_name: str, new_property: str) -> str:
        (start_line, end_line) = self.finder.find_property(original_code, class_name, property_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, new_property)

    def add_method_to_class(self, original_code: str, class_name: str, method_code: str) -> str:
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        modified_lines = lines[:end_line] + [method_code] + lines[end_line:]
        return '\n'.join(modified_lines)

    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        modified_lines = lines[:start_line - 1] + lines[end_line:]
        return '\n'.join(modified_lines)

    def replace_entire_file(self, original_code: str, new_content: str) -> str:
        return new_content

    def replace_properties_section(self, original_code: str, class_name: str, new_properties: str) -> str:
        (start_line, end_line) = self.finder.find_properties_section(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, new_properties)

    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        (start_line, end_line) = self.finder.find_imports_section(original_code)
        if start_line == 0 and end_line == 0:
            return new_imports + '\n\n' + original_code
        return self.replace_lines(original_code, start_line, end_line, new_imports)

    def replace_lines(self, original_code: str, start_line: int, end_line: int, new_lines: str) -> str:
        """Replace lines from start_line to end_line (inclusive) with new_lines."""
        from utils.format_utils import process_lines

        if start_line <= 0 or end_line <= 0:
            return original_code

        # Split by lines but preserve empty lines and indentation
        orig_lines = original_code.splitlines()
        if not orig_lines or start_line > len(orig_lines):
            return original_code

        # Convert 1-based line numbers to 0-based indices
        start_idx = start_line - 1
        end_idx = end_line - 1

        # Process the new lines
        new_content_lines = new_lines.splitlines()

        # Use our utility to handle line replacement with proper index handling
        result_lines = process_lines(orig_lines, start_idx, end_idx, new_content_lines)

        return '\n'.join(result_lines)

    def replace_lines_range(self, original_code: str, start_line: int, end_line: int, new_content: str, preserve_formatting: bool=False) -> str:
        """Replace lines from start_line to end_line (inclusive) with new_content."""
        if not original_code:
            return new_content

        # Split code into lines and strip whitespace
        lines = [line.strip() for line in original_code.splitlines()]

        # Remove leading and trailing empty lines
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()

        # If no content lines, return new_content
        if not lines:
            return new_content

        # Get lines from new_content and strip whitespace
        new_lines = [line.strip() for line in new_content.splitlines()]

        # Remove leading empty lines in new_content
        while new_lines and not new_lines[0]:
            new_lines.pop(0)

        # Handle case with negative or zero start_line (replace from beginning)
        if start_line <= 0:
            start_line = 1

        # Adjust start_line and end_line to be within valid range
        total_lines = len(lines)
        start_line = min(start_line, total_lines)
        end_line = min(max(end_line, start_line), total_lines)

        # Convert to 0-indexed
        start_idx = start_line - 1
        end_idx = end_line - 1

        # Handle normal replacement
        if not preserve_formatting:
            result = lines[:start_idx] + new_lines + lines[end_idx+1:]
            return '\n'.join(result)

        # Special handling for preserve_formatting
        result = lines[:start_idx]

        # Handle the case where new content doesn't end with newline
        if new_lines and end_idx+1 < len(lines) and not new_content.endswith('\n'):
            # Add all new lines except the last one
            result.extend(new_lines[:-1])
            # Join last new line with next line after end_idx
            if new_lines[-1]:
                result.append(new_lines[-1] + lines[end_idx+1])
                # Add remaining lines
                result.extend(lines[end_idx+2:])
            else:
                result.extend(lines[end_idx+1:])
        else:
            # Normal addition of new lines
            result.extend(new_lines)
            # Add remaining lines
            result.extend(lines[end_idx+1:])

        return '\n'.join(result)
