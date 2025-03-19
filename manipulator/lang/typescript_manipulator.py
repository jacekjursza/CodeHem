import os
import re
from typing import Optional

from finder.lang.typescript_code_finder import TypeScriptCodeFinder
from manipulator.base import BaseCodeManipulator


class TypeScriptCodeManipulator(BaseCodeManipulator):
    """TypeScript-specific code manipulator that handles TypeScript's syntax requirements."""

    def __init__(self):
        super().__init__('typescript')
        self.finder = TypeScriptCodeFinder()

    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        """
        Replace a function definition with new content, maintaining TypeScript syntax.
        """
        (start_line, end_line) = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('//') or line.startswith('/*') or line.startswith('*') or line.startswith('@'):
                adjusted_start = i + 1
            elif line:
                break

        func_indent = self._get_indentation(lines[adjusted_start - 1]) if adjusted_start <= len(lines) else ''
        function_body_indent = func_indent + '    '

        # Process JSDoc comments and function body with correct indentation
        new_func_lines = new_function.strip().splitlines()
        formatted_lines = []
        in_jsdoc = False
        in_func_body = False

        for line in new_func_lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append('')
                continue

            # JSDoc comments handling
            if stripped.startswith('/**'):
                in_jsdoc = True
                formatted_lines.append(f'{func_indent}{stripped}')
            elif in_jsdoc and stripped == '*/':
                in_jsdoc = False
                formatted_lines.append(f'{func_indent} {stripped}')
            elif in_jsdoc and stripped.startswith('*'):
                # Ensure proper spacing after asterisk in JSDoc
                if stripped == '*':
                    formatted_lines.append(f'{func_indent} *')
                else:
                    formatted_lines.append(f'{func_indent} {stripped}')
            # Function definition
            elif stripped.startswith('function') or stripped.startswith('async function'):
                formatted_lines.append(f'{func_indent}{stripped}')
                if '{' in stripped:
                    in_func_body = True
            # Opening brace
            elif stripped == '{':
                formatted_lines.append(f'{func_indent}{stripped}')
                in_func_body = True
            # Closing brace
            elif stripped == '}' or stripped == '};':
                in_func_body = False
                formatted_lines.append(f'{func_indent}{stripped}')
            # Function body
            elif in_func_body:
                formatted_lines.append(f'{function_body_indent}{stripped}')
            # Other content
            else:
                formatted_lines.append(f'{func_indent}{stripped}')

        return '\n'.join(lines[:adjusted_start - 1] + formatted_lines + lines[end_line:])

    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        """
        Replace the specified class with new content, preserving TypeScript syntax.
        """
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code

        lines = original_code.splitlines()

        # Find the real start of the class, including any decorators
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('//')):
                break

        # Get the indentation of the original class
        class_indent = self._get_indentation(lines[start_line - 1]) if start_line <= len(lines) else ''

        # Process new class content with proper indentation
        new_class_lines = new_class_content.strip().splitlines()
        formatted_lines = []

        # Extract decorators from the new class
        new_decorators = []
        class_line_index = -1
        for i, line in enumerate(new_class_lines):
            if line.strip().startswith('@'):
                new_decorators.append(line.strip())
            elif line.strip().startswith('class '):
                class_line_index = i
                break

        # If we didn't find the class line, default to first non-empty line
        if class_line_index == -1:
            for i, line in enumerate(new_class_lines):
                if line.strip():
                    class_line_index = i
                    break

        # Process the class, handling indentation correctly
        is_method_body = False
        current_indent = ''
        brace_stack = []

        # First add any decorators from the new content (skipping old decorators)
        for decorator in new_decorators:
            formatted_lines.append(f"{class_indent}{decorator}")

        # Then process the rest of the class
        for i in range(class_line_index, len(new_class_lines)):
            line = new_class_lines[i]
            stripped = line.strip()

            if not stripped:
                formatted_lines.append('')
                continue

            # Track braces to determine context
            if '{' in stripped:
                brace_stack.append('{')
            if '}' in stripped:
                if brace_stack:
                    brace_stack.pop()

            # Class declaration
            if stripped.startswith('class '):
                formatted_lines.append(f"{class_indent}{stripped}")
                current_indent = class_indent
            # Method declaration
            elif '(' in stripped and i > class_line_index:
                is_method_body = True
                formatted_lines.append(f"{class_indent}    {stripped}")
                current_indent = f"{class_indent}    "
            # Closing brace at method level
            elif stripped == '}' and is_method_body and len(brace_stack) == 1:
                formatted_lines.append(f"{class_indent}    {stripped}")
                is_method_body = False
                current_indent = class_indent
            # Closing brace at class level
            elif stripped == '}' and not is_method_body and len(brace_stack) == 0:
                formatted_lines.append(f"{class_indent}{stripped}")
            # Method body content
            elif is_method_body:
                formatted_lines.append(f"{class_indent}        {stripped}")
            # Class-level content (properties, etc.)
            else:
                formatted_lines.append(f"{class_indent}    {stripped}")

        # Replace the entire class with the formatted content
        result = '\n'.join(lines[:adjusted_start - 1] + formatted_lines + lines[end_line:])
        return result

    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        """Replace a method in a class with new content."""
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code

        (class_start, _) = self.finder.find_class(original_code, class_name)
        if class_start == 0:
            return original_code

        lines = original_code.splitlines()
        class_indent = self._get_indentation(lines[class_start - 1]) if class_start <= len(lines) else ''
        method_indent = class_indent + '    '  # 4 spaces for class members

        # Format the method with proper indentation
        new_method_lines = new_method.strip().splitlines()
        formatted_lines = []

        for i, line in enumerate(new_method_lines):
            stripped = line.strip()
            if not stripped:
                formatted_lines.append('')
                continue

            if i == 0:  # Method signature
                formatted_lines.append(f"{method_indent}{stripped}")
            elif stripped == '}' or stripped == '};':
                formatted_lines.append(f"{method_indent}{stripped}")
            else:
                # Method body gets another level of indentation (8 spaces from class level)
                formatted_lines.append(f"{method_indent}    {stripped}")

        formatted_method = '\n'.join(formatted_lines)

        # Replace the method in the original code
        return '\n'.join(lines[:start_line - 1] + formatted_lines + lines[end_line:])

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
        """
        Add a new method to the specified class, with proper TypeScript indentation.
        """
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        class_indent = self._get_indentation(lines[start_line - 1]) if start_line <= len(lines) else ''
        method_indent = class_indent + '    '
        method_lines = method_code.strip().splitlines()
        formatted_method_lines = []
        for (i, line) in enumerate(method_lines):
            stripped = line.strip()
            if not stripped:
                formatted_method_lines.append('')
                continue
            if i == 0:
                formatted_method_lines.append(f'{method_indent}{stripped}')
            elif stripped == '}' or stripped == '};':
                formatted_method_lines.append(f'{method_indent}{stripped}')
            else:
                formatted_method_lines.append(f'{method_indent}    {stripped}')
        formatted_method = '\n'.join(formatted_method_lines)
        is_empty_class = True
        for i in range(start_line, min(end_line, len(lines))):
            if lines[i].strip() and (not (lines[i].strip() == '{' or lines[i].strip() == '}')):
                is_empty_class = False
                break
        if is_empty_class:
            opening_brace_line = -1
            for i in range(start_line - 1, min(start_line + 3, len(lines))):
                if i < len(lines) and '{' in lines[i] and ('}' not in lines[i]):
                    opening_brace_line = i
                    break
            if opening_brace_line >= 0:
                modified_lines = lines[:opening_brace_line + 1] + formatted_method_lines + lines[opening_brace_line + 1:]
            else:
                modified_lines = lines[:start_line] + [class_indent + '{', formatted_method, class_indent + '}'] + lines[start_line:]
        else:
            closing_brace_line = -1
            for i in range(end_line - 1, start_line - 1, -1):
                if i < len(lines) and '}' in lines[i]:
                    closing_brace_line = i
                    break
            if closing_brace_line > 0:
                if closing_brace_line > 0 and lines[closing_brace_line - 1].strip():
                    modified_lines = lines[:closing_brace_line] + [''] + formatted_method_lines + lines[closing_brace_line:]
                else:
                    modified_lines = lines[:closing_brace_line] + formatted_method_lines + lines[closing_brace_line:]
            else:
                modified_lines = lines[:end_line] + formatted_method_lines + lines[end_line:]
        return '\n'.join(modified_lines)

    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
        """
        Remove the specified method from a class, maintaining TypeScript syntax.
        """
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code

        lines = original_code.splitlines()

        # Find the start line considering decorators
        decorator_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                decorator_start = i + 1
            elif line and (not line.startswith('//')):
                break

        # Count blank lines before this method to potentially preserve one
        blank_lines_before = 0
        for i in range(decorator_start - 2, 0, -1):
            if i < len(lines) and not lines[i].strip():
                blank_lines_before += 1
            else:
                break

        # Count blank lines after this method
        blank_lines_after = 0
        for i in range(end_line, len(lines)):
            if i < len(lines) and not lines[i].strip():
                blank_lines_after += 1
            else:
                break

        # Extract the method that follows (if any)
        has_next_method = False
        for i in range(end_line + blank_lines_after, len(lines)):
            if i < len(lines) and (lines[i].strip().startswith('private') or 
                                    lines[i].strip().startswith('public') or 
                                    lines[i].strip().startswith('protected') or
                                    lines[i].strip().startswith('static') or
                                    '(' in lines[i]):
                has_next_method = True
                break

        # Create modified code with correct spacing
        modified_lines = lines[:decorator_start - 1]

        # Add the appropriate lines after this method was removed
        if has_next_method and blank_lines_before > 0:
            # Preserve a single blank line before the next method
            modified_lines.append('')

        # Add the remaining lines after the removed method
        modified_lines.extend(lines[end_line + blank_lines_after:])

        return '\n'.join(modified_lines)

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
        """
        Replace the imports section of a file, preserving TypeScript syntax.
        """
        (start_line, end_line) = self.finder.find_imports_section(original_code)
        if start_line == 0 and end_line == 0:
            formatted_imports = new_imports.strip()
            return f'{formatted_imports}\n\n{original_code.lstrip()}'

        lines = original_code.splitlines()

        # Find all comments before imports to exclude them
        comment_lines = []
        for i in range(0, start_line - 1):
            if i < len(lines) and lines[i].strip().startswith('//'):
                comment_lines.append(i)

        # Format new imports
        new_import_lines = new_imports.strip().splitlines()
        import_indent = self._get_indentation(lines[start_line - 1]) if start_line <= len(lines) else ''

        formatted_imports = []
        for line in new_import_lines:
            if line.strip():
                formatted_imports.append(f'{import_indent}{line.lstrip()}')
            else:
                formatted_imports.append(line)

        # Replace old imports with new ones, skipping old comments
        modified_lines = lines[:start_line - 1 - len(comment_lines)] + formatted_imports + lines[end_line:]
        return '\n'.join(modified_lines)

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
        This handles the TypeScript-specific indentation rules (typically 4 spaces).
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
        body_start_index = start_index
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if not signature_line and (line.startswith('function') or line.startswith('async function') or '(' in line):
                signature_line = line
                body_start_index = i + 1 if '{' in line else i + 2
                if not '{' in line:
                    for j in range(i + 1, len(lines)):
                        if '{' in lines[j].strip():
                            body_start_index = j + 1
                            break
                break
        if not signature_line:
            return self._format_code_with_indentation(code, base_indent)
        formatted_lines.append(f'{base_indent}{signature_line}')
        body_indent = base_indent + '    '  # Use 4 spaces rather than 2
        for i in range(body_start_index, len(lines)):
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
                        # Double the indent to match 4-space indentation
                        formatted_lines.append(f"{base_indent}{' ' * (2 * relative_indent)}{line.lstrip()}")
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

        if content:
            # Fix generator method with asterisks
            pattern = r'(\s*)\*+(\w+)\*+\s*\('
            if re.search(pattern, content):
                updated_content = re.sub(pattern, r'\1\2(', content)

            # Fix other types of method patterns
            method_pattern = r'(public|private|protected|static|async)?\s*\*+(\w+)\*+\s*\('
            if re.search(method_pattern, updated_content):
                updated_content = re.sub(method_pattern, r'\1 \2(', updated_content)

            # Fix class formatting if needed
            if re.search(r'class\s+\w+\s*{\s*\w+', updated_content):
                updated_content = re.sub(r'class\s+(\w+)\s*{\s*(\w+)', r'class \1 {\n    \2', updated_content)

        if xpath:
            # Fix xpath with asterisks
            method_pattern = r'\*+(\w+)\*+'
            if '.' in xpath:
                (class_name, method_name) = xpath.split('.')
                if '*' in method_name:
                    clean_method_name = re.sub(method_pattern, r'\1', method_name)
                    updated_xpath = f'{class_name}.{clean_method_name}'
            elif '*' in xpath:
                clean_name = re.sub(method_pattern, r'\1', xpath)
                updated_xpath = clean_name

        return (updated_content, updated_xpath)

    def replace_interface(self, original_code: str, interface_name: str, new_interface: str) -> str:
        """
        Replace an interface definition with new content, maintaining TypeScript syntax.
        """
        (start_line, end_line) = self.finder.find_interface(original_code, interface_name)
        if start_line == 0 and end_line == 0:
            return original_code

        lines = original_code.splitlines()
        interface_indent = self._get_indentation(lines[start_line - 1]) if start_line <= len(lines) else ''

        # Process the new interface with correct indentation
        new_interface_lines = new_interface.strip().splitlines()
        formatted_lines = []
        brace_count = 0

        for i, line in enumerate(new_interface_lines):
            stripped = line.strip()
            if not stripped:
                formatted_lines.append('')
                continue

            # Track braces to handle nesting
            if '{' in stripped:
                brace_count += 1
            if '}' in stripped:
                brace_count -= 1

            # Apply indentation based on line type
            if i == 0 or stripped == '}':
                formatted_lines.append(f'{interface_indent}{stripped}')
            else:
                formatted_lines.append(f'{interface_indent}  {stripped}')

        # Replace old interface with new one
        result = '\n'.join(lines[:start_line - 1] + formatted_lines + lines[end_line:])

        # Remove any duplicate closing braces
        result = result.replace('}\n}', '}')

        return result

    def replace_type_alias(self, original_code: str, type_name: str, new_type_alias: str) -> str:
        """
        Replace a type alias definition with new content.

        Args:
        original_code: The original code content
        type_name: Name of the type alias to replace
        new_type_alias: New type alias code

        Returns:
        Modified code with the type alias replaced
        """
        (start_line, end_line) = self.finder.find_type_alias(original_code, type_name)
        if start_line == 0 and end_line == 0:
            return original_code

        lines = original_code.splitlines()
        type_indent = self._get_indentation(lines[start_line - 1]) if start_line <= len(lines) else ''

        # Format the type alias with proper indentation
        new_type_lines = new_type_alias.strip().splitlines()
        formatted_lines = []

        for i, line in enumerate(new_type_lines):
            stripped = line.strip()
            if i == 0:  # Type declaration line
                formatted_lines.append(f"{type_indent}{stripped}")
            elif stripped == '};' or stripped == '}':
                formatted_lines.append(f"{type_indent}{stripped}")
            elif stripped:
                formatted_lines.append(f"{type_indent}  {stripped}")
            else:
                formatted_lines.append("")

        # Replace the type alias in the original code
        modified_lines = lines[:start_line - 1] + formatted_lines + lines[end_line:]
        return '\n'.join(modified_lines)

    def replace_jsx_component(self, original_code: str, component_name: str, new_component: str) -> str:
        """
        Replace a JSX/TSX component with new content.
        """
        (start_line, end_line) = self.finder.find_jsx_component(original_code, component_name)
        if start_line == 0 and end_line == 0:
            return original_code

        # Use the entire range from the original code
        original_lines = original_code.splitlines()
        original_component = '\n'.join(original_lines[start_line-1:end_line])

        # Get the base indentation
        indent = self._get_indentation(original_lines[start_line-1]) if start_line <= len(original_lines) else ''

        # Take the new component content and apply the same indentation
        new_component_lines = new_component.strip().splitlines()
        formatted_new_component = []

        for line in new_component_lines:
            if not line.strip():
                formatted_new_component.append('')
            else:
                formatted_new_component.append(f"{indent}{line.strip()}")

        formatted_component = '\n'.join(formatted_new_component)

        # Replace the old component with the new one, preserving leading/trailing parts
        result_lines = original_lines[:start_line-1] + formatted_new_component + original_lines[end_line:]
        result = '\n'.join(result_lines)

        return result

    def build_interface_query(self, interface_name: Optional[str] = None) -> str:
        """
        Build a query to find an interface, optionally with a specific name.

        Args:
            interface_name: Optional name of the interface to find

        Returns:
            Query string
        """
        if self.language != "typescript":
            raise ValueError(
                f"Interface queries not supported for language: {self.language}"
            )

        if interface_name:
            return f'(interface_declaration name: (type_identifier) @interface_name (#eq? @interface_name "{interface_name}"))'
        return "(interface_declaration name: (type_identifier) @interface_name)"

    def build_type_alias_query(self, type_name: Optional[str] = None) -> str:
        """
        Build a query to find a type alias, optionally with a specific name.

        Args:
            type_name: Optional name of the type alias to find

        Returns:
            Query string
        """
        if self.language != "typescript":
            raise ValueError(
                f"Type alias queries not supported for language: {self.language}"
            )

        if type_name:
            return f'(type_alias_declaration name: (type_identifier) @type_name (#eq? @type_name "{type_name}"))'
        return "(type_alias_declaration name: (type_identifier) @type_name)"

    def build_jsx_component_query(self, component_name: Optional[str] = None) -> str:
        """
        Build a query to find a JSX/TSX component, optionally with a specific name.

        Args:
            component_name: Optional name of the component to find

        Returns:
            Query string
        """
        if self.language not in ["typescript", "javascript"]:
            raise ValueError(
                f"JSX component queries not supported for language: {self.language}"
            )

        # Functional component query
        functional_query = f"""
            (lexical_declaration
              (variable_declarator
                name: (identifier) @component_name {f'(#eq? @component_name "{component_name}")' if component_name else ""}
                value: (arrow_function
                        body: (jsx_element))))
        """

        # Class component query
        class_query = f'''
            (class_declaration
              name: (identifier) @component_name {f'(#eq? @component_name "{component_name}")' if component_name else ''}
              body: (class_body
                     (method_definition
                       name: (property_identifier) @method_name (#eq? @method_name "render")
                       body: (statement_block (return_statement (jsx_element))))))
        '''

        return f'{functional_query}\n{class_query}'

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