from codehem.core.finder.factory import get_code_finder
from codehem.core.manipulator.abstract import AbstractCodeManipulator
from codehem.core.formatting import get_formatter

class BaseCodeManipulator(AbstractCodeManipulator):

    def __init__(self, language: str='python'):
        self.language = language
        self.finder = get_code_finder(language)
        self.formatter = get_formatter(language)

    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        """Replace a function definition with new content."""
        (start_line, end_line) = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code
        orig_lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(orig_lines):
                continue
            line = orig_lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('#')):
                break
        new_function_clean = self.formatter.format_function(new_function.strip())
        return self.replace_lines(original_code, adjusted_start, end_line, new_function_clean)

    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        """Replace a class definition with new content."""
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        orig_lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(orig_lines):
                continue
            line = orig_lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('#')):
                break
        new_class_clean = self.formatter.format_class(new_class_content.strip())
        return self.replace_lines(original_code, adjusted_start, end_line, new_class_clean)

    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code
        orig_lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(orig_lines):
                continue
            line = orig_lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('#')):
                break
        
        # Get indentation from the class definition
        class_indent = ''
        for line in orig_lines:
            if line.strip().startswith(f'class {class_name}'):
                class_indent = self.formatter.get_indentation(line)
                break
        
        # Format the method with proper indentation
        method_indent = class_indent + self.formatter.indent_string
        new_method_clean = self.formatter.format_method(new_method.strip())
        indented_method = self.formatter.apply_indentation(new_method_clean, method_indent)
        
        return self.replace_lines(original_code, adjusted_start, end_line, indented_method)

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
        class_indent = self.formatter.get_indentation(lines[start_line - 1]) if start_line <= len(lines) else ''
        method_indent = class_indent + self.formatter.indent_string
        
        # Format the method with proper indentation
        formatted_method = self.formatter.format_method(method_code.strip())
        indented_method = self.formatter.apply_indentation(formatted_method, method_indent)
        
        # Find the appropriate insertion point
        # We want to add the method at the end of the class body before the closing line
        insertion_point = end_line
        for i in range(end_line - 1, start_line - 1, -1):
            if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('#'):
                insertion_point = i + 1
                break
        
        # Add a blank line if needed
        if insertion_point > 0 and insertion_point < len(lines) and lines[insertion_point - 1].strip():
            indented_method = f"\n{indented_method}"
        
        modified_lines = lines[:insertion_point] + [indented_method] + lines[insertion_point:]
        return '\n'.join(modified_lines)

    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        
        # Find the starting point of the method, including decorators
        decorator_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                decorator_start = i + 1
            elif line and (not line.startswith('#')):
                break
        
        # Remove the method and clean up any trailing blank lines
        modified_lines = lines[:decorator_start - 1] + lines[end_line:]
        result = '\n'.join(modified_lines)
        
        # Remove excessive blank lines
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
            
        return result

    def replace_entire_file(self, original_code: str, new_content: str) -> str:
        return new_content.strip()

    def replace_properties_section(self, original_code: str, class_name: str, new_properties: str) -> str:
        """Replace properties section in a class with new content."""
        (start_line, end_line) = self.finder.find_properties_section(original_code, class_name)
        if start_line == 0 and end_line == 0:
            # No properties section found, need to add it to the class
            (class_start, class_end) = self.finder.find_class(original_code, class_name)
            if class_start == 0:
                return original_code
                
            lines = original_code.splitlines()
            class_indent = self.formatter.get_indentation(lines[class_start - 1]) if class_start <= len(lines) else ''
            property_indent = class_indent + self.formatter.indent_string
            
            # Format the properties
            formatted_properties = self.formatter.apply_indentation(new_properties.strip(), property_indent)
            
            # Find insertion point (after class declaration line)
            insertion_point = class_start
            for i in range(class_start, min(class_start + 5, len(lines))):
                if '{' in lines[i]:
                    insertion_point = i + 1
                    break
            
            # Add a blank line after if needed
            if insertion_point < len(lines) and lines[insertion_point].strip():
                formatted_properties += '\n'
                
            modified_lines = lines[:insertion_point] + [formatted_properties] + lines[insertion_point:]
            return '\n'.join(modified_lines)
            
        # Properties section found, replace it
        formatted_properties = new_properties.strip()
        orig_lines = original_code.splitlines()
        
        # Get class indentation
        class_indent = ''
        for line in orig_lines:
            if line.strip().startswith(f'class {class_name}'):
                class_indent = self.formatter.get_indentation(line)
                break
        
        # Format with correct indentation
        property_indent = class_indent + self.formatter.indent_string
        formatted_lines = []
        for line in formatted_properties.splitlines():
            if line.strip():
                formatted_lines.append(f"{property_indent}{line.strip()}")
            else:
                formatted_lines.append('')
                
        formatted_properties = '\n'.join(formatted_lines)
        
        # Add a blank line after properties if next line is a method
        if end_line < len(orig_lines) and orig_lines[end_line].strip().startswith('def '):
            formatted_properties += '\n'
            
        return self.replace_lines(original_code, start_line, end_line, formatted_properties)

    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        """Replace imports section with new content."""
        (start_line, end_line) = self.finder.find_imports_section(original_code)
        if start_line == 0 and end_line == 0:
            # No imports section found, add at the beginning
            formatted_imports = new_imports.strip()
            
            # Check if there's a docstring at the beginning
            lines = original_code.splitlines()
            if len(lines) > 0 and (lines[0].strip().startswith('"""') or lines[0].strip().startswith("'''")):
                # Find end of docstring
                in_docstring = True
                docstring_end = 0
                for i, line in enumerate(lines):
                    if i == 0:
                        continue
                    if '"""' in line or "'''" in line:
                        docstring_end = i
                        in_docstring = False
                        break
                
                if not in_docstring:
                    # Add imports after docstring
                    return '\n'.join(lines[:docstring_end + 1]) + '\n\n' + formatted_imports + '\n\n' + '\n'.join(lines[docstring_end + 1:])
            
            # No docstring or couldn't find end, add at top
            if not formatted_imports.endswith('\n\n'):
                formatted_imports += '\n\n'
                
            return formatted_imports + original_code.lstrip()
            
        # Imports section found, replace it
        formatted_imports = new_imports.strip()
        orig_lines = original_code.splitlines()
        
        # Add blank line after imports if next section isn't blank
        if end_line < len(orig_lines) and orig_lines[end_line].strip() and not formatted_imports.endswith('\n'):
            formatted_imports += '\n'
            
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
        orig_code = original_code.rstrip()
        new_content = new_lines.rstrip()
        if start_line <= 0 or end_line < start_line:
            return original_code
        orig_lines = orig_code.splitlines()
        if not orig_lines or start_line > len(orig_lines):
            return original_code
        start_idx = start_line - 1
        end_idx = min(end_line - 1, len(orig_lines) - 1)
        result_lines = orig_lines[:start_idx] + new_content.splitlines() + orig_lines[end_idx + 1:]
        result = '\n'.join(result_lines)
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
        orig_lines = original_code.splitlines()
        new_lines = new_content.splitlines()
        if start_line <= 0:
            start_line = 1
        total_lines = len(orig_lines)
        start_line = min(start_line, total_lines)
        end_line = min(max(end_line, start_line), total_lines)
        start_idx = start_line - 1
        end_idx = end_line - 1
        
        if not preserve_formatting:
            return self.replace_lines(original_code, start_line, end_line, new_content)
        else:
            result = orig_lines[:start_idx]
            if new_lines and end_idx + 1 < len(orig_lines) and (not new_content.endswith('\n')):
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
        return self.formatter.get_indentation(line)

    def _apply_indentation(self, content: str, base_indent: str) -> str:
        """
        Apply consistent indentation to a block of content.
        
        Args:
            content: The content to indent
            base_indent: The base indentation to apply
            
        Returns:
            The indented content
        """
        return self.formatter.apply_indentation(content, base_indent)

    def fix_special_characters(self, content: str, xpath: str) -> tuple[str, str]:
        """
        Fix special characters in method names and xpaths.
        Default implementation, can be overridden by language-specific manipulators.

        Args:
            content: The code content
            xpath: The xpath string

        Returns:
            Tuple of (updated_content, updated_xpath)
        """
        return (content, xpath)

    def fix_class_method_xpath(self, content: str, xpath: str, file_path: str=None) -> tuple[str, dict]:
        """
        Fix xpath for class methods when only class name is provided in xpath.
        Default implementation, should be overridden by language-specific manipulators.

        Args:
            content: The code content
            xpath: The xpath string
            file_path: Optional path to the file

        Returns:
            Tuple of (updated_xpath, attributes_dict)
        """
        return (xpath, {})