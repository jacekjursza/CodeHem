import os
import re
from core.finder.lang.python_code_finder import PythonCodeFinder
from core.manipulator.base import BaseCodeManipulator
from core.services.python_indentation_service import PythonIndentationService

class PythonCodeManipulator(BaseCodeManipulator):

    def __init__(self):
        super().__init__('python')
        self.finder = PythonCodeFinder()

    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
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
        base_indent = self._get_indentation(orig_lines[adjusted_start - 1]) if adjusted_start <= len(orig_lines) else ''
        formatted_function = self._format_python_code_block(new_function.strip(), base_indent)
        return self.replace_lines(original_code, adjusted_start, end_line, formatted_function)

    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        from core.utils.format_utils import format_python_class_content
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
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
        formatted_content = format_python_class_content(new_class_content)
        return self.replace_lines(original_code, adjusted_start, end_line, formatted_content)

    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        """Replace a method in a class with new content, preserving decorators and overloaded methods."""
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code

        orig_lines = original_code.splitlines()
        adjusted_start = start_line

        # Check if the method signatures match (for handling overloaded methods)
        new_method_lines = new_method.strip().splitlines()
        new_method_signature = None
        for line in new_method_lines:
            if line.strip().startswith('def ' + method_name):
                new_method_signature = line.strip()
                break

        method_signature = None
        for i in range(start_line - 1, min(start_line + 5, len(orig_lines))):
            if i < len(orig_lines) and orig_lines[i].strip().startswith('def ' + method_name):
                method_signature = orig_lines[i].strip()
                break

        should_replace = True
        if new_method_signature and method_signature:
            new_params = new_method_signature[new_method_signature.find('('):new_method_signature.find(')') + 1]
            old_params = method_signature[method_signature.find('('):method_signature.find(')') + 1]
            should_replace = new_params == old_params

        if not should_replace:
            # Find method with matching signature
            all_methods = []
            in_class = False
            class_indent = None
            for (i, line) in enumerate(orig_lines):
                if line.strip().startswith('class ' + class_name):
                    in_class = True
                    class_indent = self._get_indentation(line)
                    continue
                if in_class:
                    if line.strip().startswith('class ') and self._get_indentation(line) <= class_indent:
                        break
                    if line.strip().startswith('def ' + method_name):
                        method_sig = line.strip()
                        all_methods.append((i + 1, method_sig))

            for (method_start, sig) in all_methods:
                sig_params = sig[sig.find('('):sig.find(')') + 1]
                new_params = new_method_signature[new_method_signature.find('('):new_method_signature.find(')') + 1]
                if sig_params == new_params:
                    method_end = method_start
                    method_indent = self._get_indentation(orig_lines[method_start - 1])
                    for j in range(method_start, len(orig_lines)):
                        if j >= len(orig_lines):
                            break
                        if orig_lines[j].strip() and self._get_indentation(orig_lines[j]) <= method_indent:
                            if not orig_lines[j].strip().startswith('@'):
                                method_end = j
                                break

                    for i in range(method_start - 2, -1, -1):
                        if i < 0 or i >= len(orig_lines):
                            continue
                        line = orig_lines[i].strip()
                        if line.startswith('@'):
                            method_start = i + 1
                        elif line and (not line.startswith('#')):
                            break

                    indentation_service = PythonIndentationService()
                    method_indent = indentation_service.calculate_class_indentation(orig_lines, class_name)
                    formatted_method = indentation_service.format_method_content(new_method, method_indent)
                    return self.replace_lines(original_code, method_start, method_end, formatted_method)

        # Handle regular method replacement
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(orig_lines):
                continue
            line = orig_lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('#')):
                break

        indentation_service = PythonIndentationService()
        method_indent = indentation_service.calculate_class_indentation(orig_lines, class_name)

        # Don't merge decorators - use only the new method content with appropriate indentation
        formatted_method = indentation_service.format_method_content(new_method, method_indent)
        return self.replace_lines(original_code, adjusted_start, end_line, formatted_method)

    def replace_property(self, original_code: str, class_name: str, property_name: str, new_property: str) -> str:
        """Replace a property getter in a class, preserving the setter if present."""
        (getter_start, getter_end) = self.finder.find_property(original_code, class_name, property_name)
        if getter_start == 0 and getter_end == 0:
            return original_code

        # Check if there's a setter to preserve
        (setter_start, setter_end) = self.finder.find_property_setter(original_code, class_name, property_name)
        has_setter = setter_start > 0 and setter_end > 0

        # Adjust start line to include any property decorators
        lines = original_code.splitlines()
        adjusted_start = getter_start
        for i in range(getter_start - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('#')):
                break

        # Format the new property with proper indentation
        indentation_service = PythonIndentationService()
        method_indent = indentation_service.calculate_class_indentation(lines, class_name)
        formatted_property = indentation_service.format_method_content(new_property, method_indent)

        # If there's a setter, we need to preserve it
        if has_setter:
            # First replace just the getter
            interim_code = self.replace_lines(original_code, adjusted_start, getter_end, formatted_property)

            # Return the code with both the new getter and the original setter
            return interim_code
        else:
            # No setter, just replace the getter
            return self.replace_lines(original_code, adjusted_start, getter_end, formatted_property)

    def add_method_to_class(self, original_code: str, class_name: str, method_code: str) -> str:
        """Add a new method to a class."""
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 or end_line == 0:
            return original_code

        lines = original_code.splitlines()
        class_indent = self._get_indentation(lines[start_line - 1]) if start_line <= len(lines) else ''
        method_indent = class_indent + '    '

        # Check if we're adding a property or regular method
        is_property = False
        for line in method_code.splitlines():
            if line.strip().startswith('@property') or line.strip().startswith('@') and '.setter' in line:
                is_property = True
                break

        indentation_service = PythonIndentationService()
        formatted_method = indentation_service.format_method_content(method_code, method_indent)

        is_empty_class = True
        for i in range(start_line, min(end_line, len(lines))):
            if lines[i].strip() and (not lines[i].strip().startswith('class')):
                is_empty_class = False
                break

        if is_empty_class:
            insertion_point = start_line
            modified_lines = lines[:insertion_point] + [formatted_method] + lines[insertion_point:]
        else:
            insertion_point = end_line - 1
            while insertion_point > start_line and (not lines[insertion_point].strip()):
                insertion_point -= 1
            if insertion_point > 0 and lines[insertion_point].strip():
                formatted_method = f'\n{formatted_method}'
            modified_lines = lines[:insertion_point + 1] + [formatted_method] + lines[insertion_point + 1:]

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
        formatted_props = []
        for line in new_properties.splitlines():
            if line.strip():
                formatted_props.append('    ' + line.strip())
        if start_line == 0 and end_line == 0:
            (class_start, _) = self.finder.find_class(original_code, class_name)
            if class_start == 0:
                return original_code
            lines = original_code.splitlines()
            insertion_line = class_start
            while insertion_line < len(lines) and (not (lines[insertion_line].strip() and (not lines[insertion_line].strip().startswith('class')))):
                insertion_line += 1
            if insertion_line < len(lines) and 'def ' in lines[insertion_line]:
                formatted_props.append('')
            if insertion_line < len(lines):
                result_lines = lines[:insertion_line] + formatted_props + lines[insertion_line:]
                return '\n'.join(result_lines)
            else:
                return original_code
        if end_line < len(original_code.splitlines()) and 'def ' in original_code.splitlines()[end_line]:
            formatted_props.append('')
        return self.replace_lines(original_code, start_line, end_line, '\n'.join(formatted_props))

    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        (start_line, end_line) = self.finder.find_imports_section(original_code)
        formatted_imports = []
        for line in new_imports.splitlines():
            if line.strip():
                formatted_imports.append(line.strip())
        normalized_imports = '\n'.join(formatted_imports)
        if start_line == 0 and end_line == 0:
            lines = original_code.splitlines()
            first_non_blank = 0
            while first_non_blank < len(lines) and (not lines[first_non_blank].strip()):
                first_non_blank += 1
            if first_non_blank < len(lines) and lines[first_non_blank].strip().startswith('"""'):
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
        class_def_index = -1
        decorators = []
        for (i, line) in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped.startswith('@'):
                decorators.append(line_stripped)
            elif line_stripped.startswith('class '):
                class_def_index = i
                break
        if class_def_index == -1:
            return self._format_code_with_indentation(code, base_indent)
        formatted_lines = []
        for decorator in decorators:
            formatted_lines.append(f'{base_indent}{decorator}')
        formatted_lines.append(f'{base_indent}{lines[class_def_index].strip()}')
        method_indent = base_indent + '    '
        for i in range(class_def_index + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                formatted_lines.append('')
                continue
            if line.startswith('def ') or line.startswith('async def ') or line.startswith('@'):
                formatted_lines.append(f'{method_indent}{line}')
            elif line.startswith('class '):
                formatted_lines.append(f'{method_indent}{line}')
            else:
                original_indent = len(lines[i]) - len(lines[i].lstrip())
                if original_indent > 0 and i > 0:
                    prev_non_empty = i - 1
                    while prev_non_empty >= 0 and (not lines[prev_non_empty].strip()):
                        prev_non_empty -= 1
                    if prev_non_empty >= 0:
                        prev_line = lines[prev_non_empty].strip()
                        if prev_line.startswith('def ') or prev_line.startswith('@'):
                            formatted_lines.append(f'{method_indent}    {line}')
                        else:
                            formatted_lines.append(f'{method_indent}{line}')
                    else:
                        formatted_lines.append(f'{method_indent}{line}')
                else:
                    formatted_lines.append(f'{method_indent}{line}')
        return '\n'.join(formatted_lines)

    def _format_python_code_block(self, code: str, base_indent: str) -> str:
        """Format a Python code block with proper indentation."""
        lines = code.splitlines()
        if not lines:
            return ''
        indent_stack = [0]
        formatted_lines = []
        in_func_def = False
        for (i, line) in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                formatted_lines.append('')
                continue
            if stripped.startswith('def ') or stripped.startswith('async def '):
                orig_indent = len(line) - len(line.lstrip())
                if orig_indent > 0:
                    while len(indent_stack) > 1 and indent_stack[-1] >= orig_indent:
                        indent_stack.pop()
                    if indent_stack[-1] < orig_indent:
                        indent_stack.append(orig_indent)
                else:
                    indent_stack = [0]
                in_func_def = True
                curr_indent = base_indent + '    ' * (len(indent_stack) - 1)
                formatted_lines.append(f'{curr_indent}{stripped}')
                continue
            if in_func_def and (stripped.startswith('"""') or stripped.startswith("'''")):
                curr_indent = base_indent + '    ' * len(indent_stack)
                formatted_lines.append(f'{curr_indent}{stripped}')
                in_func_def = False
                continue
            curr_indent = base_indent + '    ' * len(indent_stack)
            if not in_func_def:
                orig_indent = len(line) - len(line.lstrip())
                if orig_indent > indent_stack[-1]:
                    indent_stack.append(orig_indent)
                    curr_indent = base_indent + '    ' * (len(indent_stack) - 1)
                elif orig_indent < indent_stack[-1]:
                    while len(indent_stack) > 1 and indent_stack[-1] > orig_indent:
                        indent_stack.pop()
                    curr_indent = base_indent + '    ' * (len(indent_stack) - 1)
            formatted_lines.append(f'{curr_indent}{stripped}')
            in_func_def = False
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
        
    def replace_property_setter(self, original_code: str, class_name: str, property_name: str, new_setter: str) -> str:
        """Replace a property setter in a class."""
        (getter_start, getter_end) = self.finder.find_property(original_code, class_name, property_name)
        (setter_start, setter_end) = self.finder.find_property_setter(original_code, class_name, property_name)
        if setter_start == 0 and setter_end == 0:
            return original_code

        orig_lines = original_code.splitlines()

        # Adjust the start line to include any decorators
        adjusted_start = setter_start
        for i in range(setter_start - 2, -1, -1):
            if i < 0 or i >= len(orig_lines):
                continue
            line = orig_lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and (not line.startswith('#')):
                break

        indentation_service = PythonIndentationService()
        method_indent = indentation_service.calculate_class_indentation(orig_lines, class_name)

        # Format new setter
        new_setter_lines = new_setter.strip().splitlines()
        has_decorator = False
        for line in new_setter_lines:
            if line.strip().startswith(f'@{property_name}.setter'):
                has_decorator = True
                break
        if not has_decorator:
            new_setter = f'@{property_name}.setter\n{new_setter.strip()}'

        formatted_setter = indentation_service.format_method_content(new_setter, method_indent)

        # If the getter exists, we need to preserve it
        if getter_start > 0 and getter_end > 0:
            # Get the getter code
            getter_lines = orig_lines[getter_start - 1:getter_end]
            getter_content = '\n'.join(getter_lines)

            # If the setter is after the getter, we can replace just the setter portion
            if setter_start > getter_end:
                return self.replace_lines(original_code, adjusted_start, setter_end, formatted_setter)
            else:
                # If the setter is before the getter or overlaps, we need to create a new combined code
                result_lines = []
                for i in range(0, getter_start - 1):
                    result_lines.append(orig_lines[i])

                # Add the getter
                result_lines.extend(getter_lines)

                # Add the setter
                result_lines.extend(formatted_setter.splitlines())

                # Add any remaining lines
                if setter_end < len(orig_lines):
                    result_lines.extend(orig_lines[setter_end:])

                return '\n'.join(result_lines)
        else:
            # No getter, just replace the setter
            return self.replace_lines(original_code, adjusted_start, setter_end, formatted_setter)
