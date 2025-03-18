from finder.factory import get_code_finder
from manipulator.abstract import AbstractCodeManipulator


class BaseCodeManipulator(AbstractCodeManipulator):

    def __init__(self, language: str='python'):
        self.language = language
        self.finder = get_code_finder(language)

    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        """Replace a function definition with new content."""
        # Get the function boundaries including decorators
        (start_line, end_line) = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code

        # Look for decorators that should be included in the replacement
        orig_lines = original_code.splitlines()
        adjusted_start = start_line

        # Check for decorators above the function
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(orig_lines):
                continue
            line = orig_lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and not line.startswith('#'):
                break

        # Normalize the new function content - remove leading/trailing whitespace
        # and ensure it doesn't contain the original function signature
        new_function_clean = new_function.strip()

        # Use our fixed replace_lines method for the actual replacement
        return self.replace_lines(original_code, adjusted_start, end_line, new_function_clean)

    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        """Replace a class definition with new content."""
        # Get the class boundaries including decorators
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code

        # Look for decorators that should be included in the replacement
        orig_lines = original_code.splitlines()
        adjusted_start = start_line

        # Check for decorators above the class
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(orig_lines):
                continue
            line = orig_lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and not line.startswith('#'):
                break

        # Normalize the new class content
        new_class_clean = new_class_content.strip()

        # Use our fixed replace_lines method for the actual replacement
        return self.replace_lines(original_code, adjusted_start, end_line, new_class_clean)

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
        """Replace properties section in a class with new content."""
        # Get the properties section boundaries
        (start_line, end_line) = self.finder.find_properties_section(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code

        # Find class indentation for proper formatting
        class_indent = ''
        for line in original_code.splitlines():
            if line.strip().startswith(f"class {class_name}"):
                class_indent = line[:len(line) - len(line.lstrip())]
                break

        # Format properties with proper indentation
        property_indent = class_indent + '    '  # Standard Python indentation
        formatted_lines = []

        for line in new_properties.strip().splitlines():
            if not line.strip():
                formatted_lines.append('')
                continue
            formatted_lines.append(property_indent + line.strip())

        formatted_properties = '\n'.join(formatted_lines)

        # Use our fixed replace_lines method
        return self.replace_lines(original_code, start_line, end_line, formatted_properties)

    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        """Replace imports section with new content."""
        (start_line, end_line) = self.finder.find_imports_section(original_code)
        if start_line == 0 and end_line == 0:
            # No imports found, add at the beginning
            # Add a blank line after imports for readability
            if not new_imports.endswith('\n\n'):
                new_imports = new_imports.rstrip() + '\n\n'
            return new_imports + original_code

        # Format the new imports
        formatted_imports = new_imports.strip()

        # Ensure there's a blank line after imports
        orig_lines = original_code.splitlines()
        if end_line < len(orig_lines) and orig_lines[end_line].strip() and not formatted_imports.endswith('\n'):
            formatted_imports += '\n'

        # Use our fixed replace_lines method
        return self.replace_lines(original_code, start_line, end_line, formatted_imports)

    def replace_lines(self, original_code: str, start_line: int, end_line: int, new_lines: str) -> str:
        """
        Replace lines from start_line to end_line (inclusive) with new_lines.

        Args:
        original_code: The original code content
        start_line: The starting line number (1-indexed)
        end_line: The ending line number (1-indexed, inclusive)
        new_lines: The new content to replace the lines with

        Returns:
        The modified code with the lines replaced
        """
        # Normalize inputs by stripping leading/trailing whitespace
        orig_code = original_code.rstrip()
        new_content = new_lines.rstrip()

        # Handle edge cases
        if start_line <= 0 or end_line < start_line:
            return original_code

        # Split into lines for processing
        orig_lines = orig_code.splitlines()

        # Check bounds
        if not orig_lines or start_line > len(orig_lines):
            return original_code

        # Convert to 0-indexed for array operations
        start_idx = start_line - 1
        end_idx = min(end_line - 1, len(orig_lines) - 1)

        # Perform the replacement
        result_lines = orig_lines[:start_idx] + new_content.splitlines() + orig_lines[end_idx + 1:]

        # Join back to a string
        result = '\n'.join(result_lines)

        # Preserve original trailing newline if it existed
        if original_code.endswith('\n'):
            result += '\n'

        return result

    def replace_lines_range(self, original_code: str, start_line: int, end_line: int, new_content: str, preserve_formatting: bool=False) -> str:
        """
        Replace a range of lines in the original code with new content.

        Args:
        original_code: The original code content
        start_line: The starting line number (1-indexed)
        end_line: The ending line number (1-indexed, inclusive)
        new_content: The new content to replace the lines with
        preserve_formatting: If True, preserves exact formatting of new_content without normalization

        Returns:
        The modified code with the lines replaced
        """
        if not original_code:
            return new_content

        # Split the original and new content into lines
        orig_lines = original_code.splitlines()
        new_lines = new_content.splitlines()

        # Normalize line ranges
        if start_line <= 0:
            start_line = 1

        total_lines = len(orig_lines)
        start_line = min(start_line, total_lines)
        end_line = min(max(end_line, start_line), total_lines)

        # Convert to 0-indexed for internal use
        start_idx = start_line - 1
        end_idx = end_line - 1

        if not preserve_formatting:
            # Simple replacement - reuse base method for consistency
            return self.replace_lines(original_code, start_line, end_line, new_content)
        else:
            # Preserve formatting with special handling for line endings
            result = orig_lines[:start_idx]

            if new_lines and end_idx + 1 < len(orig_lines) and not new_content.endswith('\n'):
                # Handle special case for joining with next line
                result.extend(new_lines[:-1])
                if new_lines[-1]:
                    result.append(new_lines[-1] + orig_lines[end_idx + 1])
                    result.extend(orig_lines[end_idx + 2:])
                else:
                    result.extend(orig_lines[end_idx + 1:])
            else:
                result.extend(new_lines)
                result.extend(orig_lines[end_idx + 1:])

            return '\n'.join(result)
            
    def _get_indentation(self, line: str) -> str:
        """
        Extract the whitespace indentation from the beginning of a line.
        
        Args:
            line: The line to extract indentation from
            
        Returns:
            The indentation string (spaces, tabs, etc.)
        """
        import re
        match = re.match(r'^(\s*)', line)
        return match.group(1) if match else ''
        
    def _apply_indentation(self, content: str, base_indent: str) -> str:
        """
        Apply consistent indentation to a block of content.
        
        Args:
            content: The content to indent
            base_indent: The base indentation to apply
            
        Returns:
            The indented content
        """
        lines = content.splitlines()
        result = []
        
        for line in lines:
            if line.strip():  # Non-empty line
                result.append(base_indent + line.lstrip())
            else:  # Empty line
                result.append('')
                
        return '\n'.join(result)