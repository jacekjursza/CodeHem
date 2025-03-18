import os
import re

from finder.lang.typescript_code_finder import TypeScriptCodeFinder
from manipulator.base import BaseCodeManipulator


class TypeScriptCodeManipulator(BaseCodeManipulator):
    """TypeScript-specific code manipulator that handles TypeScript's syntax requirements."""

    def __init__(self):
        super().__init__('typescript')
        self.finder = TypeScriptCodeFinder()

    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        """Replace the specified function with new content, preserving TypeScript syntax."""
        (start_line, end_line) = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self._replace_element(original_code, start_line, end_line, new_function)

    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        """Replace the specified class with new content, preserving TypeScript syntax."""
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code

        # Check for decorators before the class
        lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('//')):
                break

        # Format the new class content
        class_indent = self._get_indentation(lines[adjusted_start - 1]) if adjusted_start <= len(lines) else ''
        formatted_class = self._format_typescript_code_block(new_class_content, class_indent)

        return self.replace_lines(original_code, adjusted_start, end_line, formatted_class)

    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code
        (class_start, _) = self.finder.find_class(original_code, class_name)
        if class_start == 0:
            return original_code
        lines = original_code.splitlines()
        class_indent = self._get_indentation(lines[class_start - 1]) if class_start <= len(lines) else ''
        method_indent = class_indent + '  '
        formatted_method = self._format_typescript_code_block(new_method, method_indent)
        return self.replace_lines(original_code, start_line, end_line, formatted_method)

    def replace_property(self, original_code: str, class_name: str, property_name: str, new_property: str) -> str:
        """Replace the specified property within a class, preserving TypeScript syntax."""
        (start_line, end_line) = self.finder.find_property(original_code, class_name, property_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        if start_line > 0 and start_line <= len(lines):
            original_line = lines[start_line - 1]
            indent = self._get_indentation(original_line)
            if not new_property.startswith(indent):
                new_property = indent + new_property.lstrip()
            return self.replace_lines(original_code, start_line, end_line, new_property)
        return original_code

    def add_method_to_class(self, original_code: str, class_name: str, method_code: str) -> str:
        """Add a new method to the specified class, with proper TypeScript indentation."""
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        class_indent = self._get_indentation(lines[start_line - 1]) if start_line <= len(lines) else ''
        method_indent = class_indent + '  '
        formatted_method = self._format_typescript_code_block(method_code, method_indent)
        class_end_brace = -1
        for i in range(end_line - 1, start_line - 1, -1):
            if i < len(lines) and lines[i].strip() == '}':
                class_end_brace = i
                break
        if class_end_brace > 0:
            is_empty_class = True
            for i in range(start_line, class_end_brace):
                if i < len(lines) and lines[i].strip() and (not (lines[i].strip().startswith('class') or lines[i].strip() == '{')):
                    is_empty_class = False
                    break
            if is_empty_class:
                insertion_point = start_line + 1
                if insertion_point < len(lines) and lines[insertion_point - 1].strip() == '{':
                    modified_lines = lines[:insertion_point] + [formatted_method] + lines[insertion_point:]
                else:
                    modified_lines = lines[:start_line] + [class_indent + '{', formatted_method] + lines[start_line:]
            else:
                if class_end_brace > 1 and lines[class_end_brace - 1].strip():
                    formatted_method = f'\n{formatted_method}'
                modified_lines = lines[:class_end_brace] + [formatted_method] + lines[class_end_brace:]
            return '\n'.join(modified_lines)
        modified_lines = lines[:end_line] + [formatted_method] + lines[end_line:]
        return '\n'.join(modified_lines)

    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
        """Remove the specified method from a class, maintaining TypeScript syntax."""
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        i = start_line - 2
        decorator_start = start_line
        while i >= 0 and i < len(lines):
            line = lines[i].strip()
            if line.startswith('@'):
                decorator_start = i + 1
                i -= 1
            else:
                break
        modified_lines = lines[:decorator_start - 1] + lines[end_line:]
        result = '\n'.join(modified_lines)
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        return result

    def replace_properties_section(self, original_code: str, class_name: str, new_properties: str) -> str:
        (start_line, end_line) = self.finder.find_properties_section(original_code, class_name)
        if start_line == 0 and end_line == 0:
            (class_start, class_end) = self.finder.find_class(original_code, class_name)
            if class_start == 0:
                return original_code
            lines = original_code.splitlines()
            for i in range(class_start, min(class_start + 5, len(lines))):
                if i < len(lines) and '{' in lines[i]:
                    class_indent = self._get_indentation(lines[class_start - 1])
                    property_indent = class_indent + '  '
                    formatted_properties = self._format_property_lines(new_properties, property_indent)
                    modified_lines = lines[:i + 1] + [formatted_properties] + lines[i + 1:]
                    return '\n'.join(modified_lines)
            return original_code
        return self._replace_element(original_code, start_line, end_line, new_properties)

    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        """Replace the imports section of a file, preserving TypeScript syntax."""
        (start_line, end_line) = self.finder.find_imports_section(original_code)
        if start_line == 0 and end_line == 0:
            return new_imports + '\n\n' + original_code
        return self._replace_element(original_code, start_line, end_line, new_imports)

    def _replace_element(self, original_code: str, start_line: int, end_line: int, new_content: str) -> str:
        """Helper method to replace code elements with proper indentation."""
        lines = original_code.splitlines()
        if start_line > 0 and start_line <= len(lines):
            original_line = lines[start_line - 1]
            indent = self._get_indentation(original_line)
            is_function = self._is_function_or_method(original_line)
            if is_function:
                formatted_content = self._format_typescript_code_block(new_content, indent)
            else:
                formatted_content = self._format_code_with_indentation(new_content, indent)
            return self.replace_lines(original_code, start_line, end_line, formatted_content)
        return original_code

    def _is_function_or_method(self, line: str) -> bool:
        """Check if a line is a function or method definition."""
        return re.match('^\\s*(async\\s+)?function\\s+', line.strip()) is not None or re.match('^\\s*(public|private|protected|static|async)?\\s*\\w+\\s*\\(', line.strip()) is not None

    def _get_indentation(self, line: str) -> str:
        """Get the whitespace indentation from a line of code."""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    def _format_typescript_code_block(self, code: str, base_indent: str) -> str:
        """
        Format a TypeScript code block (function/method) with correct indentation.
        This handles the TypeScript-specific indentation rules (typically 2 spaces).
        """
        lines = code.splitlines()
        if not lines:
            return ''
        decorators = []
        start_index = 0
        for (i, line) in enumerate(lines):
            if line.strip().startswith('@'):
                decorators.append(line.strip())
                start_index = i + 1
            else:
                break
        if start_index >= len(lines):
            return '\n'.join([f'{base_indent}{dec}' for dec in decorators])
        formatted_lines = [f'{base_indent}{dec}' for dec in decorators]
        signature_line = None
        opening_brace_index = -1
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if not signature_line and (line.startswith('function') or line.startswith('async function') or '(' in line):
                signature_line = line
                if '{' in line:
                    opening_brace_index = i
                    break
            elif signature_line and '{' in line:
                opening_brace_index = i
                break
        if not signature_line:
            return self._format_code_with_indentation(code, base_indent)
        formatted_lines.append(f'{base_indent}{signature_line}')
        body_indent = base_indent + '  '
        if opening_brace_index > start_index and '{' in lines[opening_brace_index].strip():
            if opening_brace_index != start_index:
                formatted_lines.append(f'{base_indent}{lines[opening_brace_index].strip()}')
            for i in range(opening_brace_index + 1, len(lines)):
                line = lines[i].strip()
                if line == '}':
                    formatted_lines.append(f'{base_indent}{line}')
                elif line:
                    formatted_lines.append(f'{body_indent}{line}')
                else:
                    formatted_lines.append('')
        else:
            in_body = True
            for i in range(start_index + 1, len(lines)):
                line = lines[i].strip()
                if line == '}':
                    formatted_lines.append(f'{base_indent}{line}')
                elif line:
                    formatted_lines.append(f'{body_indent}{line}')
                else:
                    formatted_lines.append('')
        return '\n'.join(formatted_lines)

    def _format_property_lines(self, properties: str, indent: str) -> str:
        """Format class property lines with correct indentation."""
        lines = properties.splitlines()
        formatted_lines = []
        for line in lines:
            if line.strip():
                formatted_lines.append(f'{indent}{line.strip()}')
            else:
                formatted_lines.append('')
        return '\n'.join(formatted_lines)

    def _format_code_with_indentation(self, code: str, base_indent: str) -> str:
        """
        Format general code with indentation (fallback method).
        Used for code that isn't a TypeScript function/method/class.
        """
        lines = code.splitlines()
        if not lines:
            return ''
        has_indentation = False
        min_indent = float('inf')
        for line in lines:
            if line.strip():
                spaces = len(line) - len(line.lstrip())
                if spaces > 0:
                    has_indentation = True
                    min_indent = min(min_indent, spaces)
        if not has_indentation or min_indent == float('inf'):
            formatted_lines = []
            for line in lines:
                if line.strip():
                    formatted_lines.append(f'{base_indent}{line.strip()}')
                else:
                    formatted_lines.append('')
            return '\n'.join(formatted_lines)
        else:
            formatted_lines = []
            for line in lines:
                if line.strip():
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent >= min_indent:
                        relative_indent = current_indent - min_indent
                        formatted_lines.append(f"{base_indent}{' ' * relative_indent}{line.lstrip()}")
                    else:
                        formatted_lines.append(f'{base_indent}{line.lstrip()}')
                else:
                    formatted_lines.append('')
            return '\n'.join(formatted_lines)

    def fix_special_characters(self, content: str, xpath: str) -> tuple[str, str]:
        """
        Fix special characters in method names and xpaths for TypeScript/JavaScript code.

        Args:
            content: The code content
            xpath: The xpath string

        Returns:
            Tuple of (updated_content, updated_xpath)
        """
        updated_content = content
        updated_xpath = xpath

        # Fix special characters in content
        if content:
            pattern = r'function\s+\*+(\w+)\*+\s*\('
            replacement = r'function \1('
            if re.search(pattern, content):
                updated_content = re.sub(pattern, replacement, content)

        # Fix special characters in xpath
        if xpath:
            method_pattern = r'\*+(\w+)\*+'
            if '.' in xpath:
                class_name, method_name = xpath.split('.')
                if '*' in method_name:
                    clean_method_name = re.sub(method_pattern, r'\1', method_name)
                    updated_xpath = f'{class_name}.{clean_method_name}'
            elif '*' in xpath:
                clean_name = re.sub(method_pattern, r'\1', xpath)
                updated_xpath = clean_name

        return updated_content, updated_xpath

    def fix_class_method_xpath(self, content: str, xpath: str, file_path: str = None) -> tuple[str, dict]:
        """
        Fix xpath for class methods when only class name is provided in xpath for TypeScript/JavaScript code.

        Args:
            content: The code content
            xpath: The xpath string
            file_path: Optional path to the file

        Returns:
            Tuple of (updated_xpath, attributes_dict)
        """
        if '.' in xpath:
            return xpath, {}

        # TypeScript/JavaScript would need its own method detection logic
        # For example, checking for 'this' usage, but that's more complex
        # than the Python version and would require parsing the method body

        # For now, just use the file content to check if there's a class with this name
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                # Check if there's a class with this name in the file
                class_start, class_end = self.finder.find_class(file_content, xpath)
                if class_start > 0 and class_end > 0:
                    # If there is, it's likely this xpath is a class name
                    # But we can't determine the method name without more context
                    return xpath, {}
            except Exception:
                pass

        return xpath, {}