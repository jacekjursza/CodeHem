import os
import re

from finder.lang.python_code_finder import PythonCodeFinder
from manipulator.base import BaseCodeManipulator


class PythonCodeManipulator(BaseCodeManipulator):

    def __init__(self):
        super().__init__('python')
        self.finder = PythonCodeFinder()

    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        (start_line, end_line) = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code

        # Handle decorators by looking backward
        lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('#')):
                break

        # Get base indentation of the original function
        base_indent = self._get_indentation(lines[adjusted_start - 1]) if adjusted_start <= len(lines) else ''

        # Format the new function with proper indentation
        formatted_function = []
        in_func_def = False
        for line in new_function.splitlines():
            stripped = line.strip()
            if not stripped:
                formatted_function.append('')
            elif stripped.startswith('@'):
                formatted_function.append(base_indent + stripped)
            elif stripped.startswith('def '):
                formatted_function.append(base_indent + stripped)
                in_func_def = True
            elif in_func_def:
                # Add extra indent for function body
                formatted_function.append(base_indent + '    ' + stripped)

        # Replace the old function with the new formatted function
        return self.replace_lines(original_code, adjusted_start, end_line, '\n'.join(formatted_function))

    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        from utils.format_utils import format_python_class_content

        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code

        # Handle decorators by looking backward
        lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('#')):
                break

        # Format the class content with proper indentation
        formatted_content = format_python_class_content(new_class_content)

        # Replace the class in the original code
        return self.replace_lines(original_code, adjusted_start, end_line, formatted_content)

    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        """Replace a method in a class with new content."""
        # Get the method boundaries
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code

        # Find method decorators to include in replacement range
        orig_lines = original_code.splitlines()
        adjusted_start = start_line

        # Check for decorators above the method
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(orig_lines):
                continue
            line = orig_lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and not line.startswith('#'):
                break

        # Find the class indentation to properly format the new method
        class_indent = ''
        for line in orig_lines:
            if line.strip().startswith(f"class {class_name}"):
                class_indent = line[:len(line) - len(line.lstrip())]
                break

        # Method indentation is one level deeper than class
        method_indent = class_indent + '    '  # Standard 4-space Python indentation

        # Format the new method content with proper indentation
        formatted_lines = []
        for line in new_method.strip().splitlines():
            stripped = line.strip()
            if not stripped:
                formatted_lines.append('')
                continue

            # Handle different line types
            if stripped.startswith('@'):
                # Decorator
                formatted_lines.append(method_indent + stripped)
            elif stripped.startswith('def '):
                # Method signature
                formatted_lines.append(method_indent + stripped)
            else:
                # Method body - add one more level of indentation
                formatted_lines.append(method_indent + '    ' + stripped)

        formatted_method = '\n'.join(formatted_lines)

        # Use our fixed replace_lines method for the actual replacement
        return self.replace_lines(original_code, adjusted_start, end_line, formatted_method)

    def replace_property(self, original_code: str, class_name: str, property_name: str, new_property: str) -> str:
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
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        class_indent = self._get_indentation(lines[start_line - 1]) if start_line <= len(lines) else ''
        method_indent = class_indent + '    '
        formatted_method = self._format_python_code_block(method_code, method_indent)
        is_empty_class = True
        for i in range(start_line, min(end_line, len(lines))):
            if lines[i].strip() and (not lines[i].strip().startswith('class')):
                is_empty_class = False
                break
        if is_empty_class:
            insertion_point = start_line
            modified_lines = lines[:insertion_point] + [formatted_method] + lines[insertion_point:]
        else:
            if end_line > 1 and lines[end_line - 2].strip():
                formatted_method = f'\n{formatted_method}'
            modified_lines = lines[:end_line] + [formatted_method] + lines[end_line:]
        return '\n'.join(modified_lines)

    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
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

        # Format new properties with proper indentation
        formatted_props = []
        for line in new_properties.splitlines():
            if line.strip():
                formatted_props.append("    " + line.strip())  # 4 spaces for class members

        if start_line == 0 and end_line == 0:
            # No properties found, need to add them
            (class_start, _) = self.finder.find_class(original_code, class_name)
            if class_start == 0:
                return original_code

            lines = original_code.splitlines()

            # Find insertion point - after class definition
            insertion_line = class_start
            while insertion_line < len(lines) and not (lines[insertion_line].strip() and not lines[insertion_line].strip().startswith('class')):
                insertion_line += 1

            # Add blank line after properties if a method follows
            if insertion_line < len(lines) and ('def ' in lines[insertion_line]):
                formatted_props.append("")

            # Insert properties
            if insertion_line < len(lines):
                result_lines = lines[:insertion_line] + formatted_props + lines[insertion_line:]
                return '\n'.join(result_lines)
            else:
                return original_code

        # Properties section found - replace it
        # Add blank line if followed by a method definition
        if end_line < len(original_code.splitlines()) and 'def ' in original_code.splitlines()[end_line]:
            formatted_props.append("")

        return self.replace_lines(original_code, start_line, end_line, '\n'.join(formatted_props))

    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        (start_line, end_line) = self.finder.find_imports_section(original_code)

        # Format the imports
        formatted_imports = []
        for line in new_imports.splitlines():
            if line.strip():
                formatted_imports.append(line.strip())
        normalized_imports = '\n'.join(formatted_imports)

        if start_line == 0 and end_line == 0:
            # If no imports found, add at the beginning, preserving docstrings
            lines = original_code.splitlines()
            first_non_blank = 0
            while first_non_blank < len(lines) and not lines[first_non_blank].strip():
                first_non_blank += 1

            if first_non_blank < len(lines) and lines[first_non_blank].strip().startswith('"""'):
                # Handle docstring
                docstring_end = first_non_blank
                in_docstring = True
                for i in range(first_non_blank + 1, len(lines)):
                    docstring_end = i
                    if '"""' in lines[i]:
                        in_docstring = False
                        break

                if not in_docstring:
                    return '\n'.join(lines[:docstring_end + 1]) + '\n\n' + normalized_imports + '\n\n' + '\n'.join(lines[docstring_end + 1:])

            return normalized_imports + '\n\n' + original_code.lstrip()

        # If imports found, replace them
        return self.replace_lines(original_code, start_line, end_line, normalized_imports)

    def _replace_element(self, original_code: str, start_line: int, end_line: int, new_content: str) -> str:
        lines = original_code.splitlines()
        if start_line > 0 and start_line <= len(lines):
            original_line = lines[start_line - 1]
            indent = self._get_indentation(original_line)
            if self._is_function_or_method(original_line):
                formatted_content = self._format_python_code_block(new_content, indent)
            elif self._is_class_definition(original_line):
                formatted_content = self._format_class_content(new_content, indent)
            else:
                formatted_content = self._format_code_with_indentation(new_content, indent)
            return self.replace_lines(original_code, start_line, end_line, formatted_content)
        return original_code

    def _is_function_or_method(self, line: str) -> bool:
        return re.match('^\\s*(async\\s+)?def\\s+', line.strip()) is not None

    def _is_class_definition(self, line: str) -> bool:
        return re.match('^\\s*class\\s+', line.strip()) is not None

    def _get_indentation(self, line: str) -> str:
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    def _format_property_lines(self, properties: str, indent: str) -> str:
        lines = properties.splitlines()
        formatted_lines = []
        for line in lines:
            if line.strip():
                formatted_lines.append(f'{indent}{line.strip()}')
            else:
                formatted_lines.append('')
        return '\n'.join(formatted_lines)

    def _format_class_content(self, code: str, base_indent: str) -> str:
        """Format class content with proper indentation for methods and properties."""
        lines = code.splitlines()
        if not lines:
            return ''

        # Find decorators and class definition line
        class_def_index = -1
        decorators = []

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped.startswith('@'):
                decorators.append(line_stripped)
            elif line_stripped.startswith('class '):
                class_def_index = i
                break

        if class_def_index == -1:
            # If no class definition found, use regular indentation
            return self._format_code_with_indentation(code, base_indent)

        # Format decorators and class definition line
        formatted_lines = []
        for decorator in decorators:
            formatted_lines.append(f"{base_indent}{decorator}")

        formatted_lines.append(f"{base_indent}{lines[class_def_index].strip()}")

        # Format all lines after the class definition with proper indentation
        method_indent = base_indent + '    '

        for i in range(class_def_index + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                formatted_lines.append('')
                continue

            if line.startswith('def ') or line.startswith('async def ') or line.startswith('@'):
                # Method or decorator starts at the class body level
                formatted_lines.append(f"{method_indent}{line}")
            elif line.startswith('class '):
                # Nested class
                formatted_lines.append(f"{method_indent}{line}")
            else:
                # Regular class body content or method body
                # Try to determine if this is part of a method body by its indentation
                original_indent = len(lines[i]) - len(lines[i].lstrip())
                if original_indent > 0 and i > 0:
                    # Check previous non-empty line's indentation to determine context
                    prev_non_empty = i - 1
                    while prev_non_empty >= 0 and not lines[prev_non_empty].strip():
                        prev_non_empty -= 1

                    if prev_non_empty >= 0:
                        prev_line = lines[prev_non_empty].strip()
                        if prev_line.startswith('def ') or prev_line.startswith('@'):
                            # This is inside a method body
                            formatted_lines.append(f"{method_indent}    {line}")
                        else:
                            # This appears to be a class-level attribute
                            formatted_lines.append(f"{method_indent}{line}")
                    else:
                        # Default to class-level indentation
                        formatted_lines.append(f"{method_indent}{line}")
                else:
                    # Class-level attribute or statement
                    formatted_lines.append(f"{method_indent}{line}")

        return '\n'.join(formatted_lines)

    def _format_python_code_block(self, code: str, base_indent: str) -> str:
        lines = code.splitlines()
        if not lines:
            return ''

        # Find decorators and the function/method definition line
        decorators = []
        def_line = None
        def_index = -1

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('@'):
                decorators.append(stripped)
            elif stripped.startswith('def ') or stripped.startswith('async def '):
                def_line = stripped
                def_index = i
                break

        if def_line is None:
            # If no function definition found, use regular indentation
            return self._format_code_with_indentation(code, base_indent)

        # Format decorators and function definition
        formatted_lines = []
        for decorator in decorators:
            formatted_lines.append(f'{base_indent}{decorator}')

        formatted_lines.append(f'{base_indent}{def_line}')

        # Format function body
        body_indent = base_indent + '    '

        # Find the appropriate indentation level for the body
        min_indent = float('inf')
        body_lines = lines[def_index+1:]

        for line in body_lines:
            if line.strip():
                indent_level = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent_level) if indent_level > 0 else min_indent

        if min_indent == float('inf'):
            min_indent = 4  # Default indentation if we can't determine it

        # Format docstring if present
        if body_lines and (body_lines[0].strip().startswith('"""') or body_lines[0].strip().startswith("'''")):
            docstring_delimiter = '"""' if body_lines[0].strip().startswith('"""') else "'''"
            docstring_lines = []
            docstring_end_index = 0
            in_docstring = True

            docstring_lines.append(body_lines[0].strip())
            for i in range(1, len(body_lines)):
                docstring_end_index = i
                line = body_lines[i]
                docstring_lines.append(line)
                if docstring_delimiter in line:
                    in_docstring = False
                    break

            # Add formatted docstring
            for i, line in enumerate(docstring_lines):
                if i == 0:
                    formatted_lines.append(f'{body_indent}{line.strip()}')
                else:
                    line_content = line.strip()
                    if line_content:
                        formatted_lines.append(f'{body_indent}{line_content}')
                    else:
                        formatted_lines.append('')

            # Process remaining body after docstring
            if not in_docstring and docstring_end_index + 1 < len(body_lines):
                remaining_body = body_lines[docstring_end_index+1:]
                for line in remaining_body:
                    if not line.strip():
                        formatted_lines.append('')
                        continue

                    indent_level = len(line) - len(line.lstrip())
                    if indent_level >= min_indent:
                        relative_indent = indent_level - min_indent
                        formatted_lines.append(f"{body_indent}{' ' * relative_indent}{line.lstrip()}")
                    else:
                        formatted_lines.append(f'{body_indent}{line.lstrip()}')
        else:
            # Process body without docstring
            for line in body_lines:
                if not line.strip():
                    formatted_lines.append('')
                    continue

                indent_level = len(line) - len(line.lstrip())
                if indent_level >= min_indent:
                    relative_indent = indent_level - min_indent
                    formatted_lines.append(f"{body_indent}{' ' * relative_indent}{line.lstrip()}")
                else:
                    formatted_lines.append(f'{body_indent}{line.lstrip()}')

        return '\n'.join(formatted_lines)

    def _format_body_lines(self, body_lines, formatted_lines, original_indent, base_indent):
        if not body_lines:
            return
        min_indent = float('inf')
        for line in body_lines:
            if line.strip():
                line_indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, line_indent)
        if min_indent == float('inf'):
            min_indent = original_indent
        for line in body_lines:
            if not line.strip():
                formatted_lines.append('')
                continue
            line_indent = len(line) - len(line.lstrip())
            if line_indent >= min_indent:
                relative_indent = line_indent - min_indent
                formatted_lines.append(f"{base_indent}{' ' * relative_indent}{line.lstrip()}")
            else:
                formatted_lines.append(f'{base_indent}{line.lstrip()}')

    def _format_code_with_indentation(self, code: str, base_indent: str) -> str:
        lines = code.splitlines()
        if not lines:
            return ''
        is_class_def = False
        class_body_indent = base_indent + '    '
        if lines and lines[0].strip().startswith('class '):
            is_class_def = True
        min_indent = float('inf')
        for line in lines:
            if line.strip():
                line_indent = len(line) - len(line.lstrip())
                if line_indent > 0:
                    min_indent = min(min_indent, line_indent)
        if min_indent == float('inf'):
            formatted_lines = []
            for (i, line) in enumerate(lines):
                line_content = line.strip()
                if not line_content:
                    formatted_lines.append('')
                    continue
                if i == 0:
                    formatted_lines.append(f'{base_indent}{line_content}')
                elif is_class_def and line_content.startswith('def '):
                    formatted_lines.append(f'{class_body_indent}{line_content}')
                elif is_class_def:
                    formatted_lines.append(f'{class_body_indent}{line_content}')
                else:
                    formatted_lines.append(f'{base_indent}{line_content}')
        else:
            formatted_lines = []
            for (i, line) in enumerate(lines):
                line_content = line.strip()
                if not line_content:
                    formatted_lines.append('')
                    continue
                if i == 0:
                    formatted_lines.append(f'{base_indent}{line_content}')
                    continue
                line_indent = len(line) - len(line.lstrip())
                if is_class_def and line_content.startswith('def '):
                    if line_indent <= min_indent:
                        formatted_lines.append(f'{class_body_indent}{line_content}')
                        continue
                if line_indent >= min_indent:
                    relative_indent = line_indent - min_indent
                    if is_class_def:
                        formatted_lines.append(f"{class_body_indent}{' ' * relative_indent}{line.lstrip()}")
                    else:
                        formatted_lines.append(f"{base_indent}{' ' * relative_indent}{line.lstrip()}")
                elif is_class_def:
                    formatted_lines.append(f'{class_body_indent}{line_content}')
                else:
                    formatted_lines.append(f'{base_indent}{line_content}')
        return '\n'.join(formatted_lines)

    def fix_special_characters(self, content: str, xpath: str) -> tuple[str, str]:
        updated_content = content
        updated_xpath = xpath
        if content:
            pattern = 'def\\s+\\*+(\\w+)\\*+\\s*\\('
            replacement = 'def \\1('
            if re.search(pattern, content):
                updated_content = re.sub(pattern, replacement, content)
        if xpath:
            method_pattern = '\\*+(\\w+)\\*+'
            if '.' in xpath:
                (class_name, method_name) = xpath.split('.')
                if '*' in method_name:
                    clean_method_name = re.sub(method_pattern, '\\1', method_name)
                    updated_xpath = f'{class_name}.{clean_method_name}'
            elif '*' in xpath:
                clean_name = re.sub(method_pattern, '\\1', xpath)
                updated_xpath = clean_name
        return (updated_content, updated_xpath)

    def fix_class_method_xpath(self, content: str, xpath: str, file_path: str=None) -> tuple[str, dict]:
        if '.' in xpath:
            return (xpath, {})
        func_def_match = re.search('^\\s*(?:@\\w+)?\\s*(?:async\\s+)?def\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(\\s*self\\b', content, re.MULTILINE)
        if not func_def_match:
            return (xpath, {})
        method_name = func_def_match.group(1)
        potential_class_name = xpath
        if method_name == potential_class_name:
            return (xpath, {})
        attributes = {'target_type': 'method', 'class_name': potential_class_name, 'method_name': method_name}
        if not file_path or not os.path.exists(file_path):
            return (f'{potential_class_name}.{method_name}', attributes)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            (class_start, class_end) = self.finder.find_class(file_content, potential_class_name)
            if class_start > 0 and class_end > 0:
                return (f'{potential_class_name}.{method_name}', attributes)
        except Exception:
            pass
        return (xpath, {})