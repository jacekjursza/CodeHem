import os
import re
from codehem.core.finder.lang.python_code_finder import PythonCodeFinder
from codehem.core.manipulator.base import BaseCodeManipulator
from codehem.core.services.python_indentation_service import PythonIndentationService


class PythonCodeManipulator(BaseCodeManipulator):
    def __init__(self):
        super().__init__("python")
        self.finder = PythonCodeFinder()
        self.indentation_service = PythonIndentationService()

    def replace_function(
        self, original_code: str, function_name: str, new_function: str
    ) -> str:
        (start_line, end_line) = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code
        orig_lines = original_code.splitlines()
        adjusted_start = self._find_decorator_adjusted_start(orig_lines, start_line)
        base_indent = (
            self._get_indentation(orig_lines[adjusted_start - 1])
            if adjusted_start <= len(orig_lines)
            else ""
        )
        formatted_function = self._format_python_code_block(
            new_function.strip(), base_indent
        )
        return self.replace_lines(
            original_code, adjusted_start, end_line, formatted_function
        )

    def replace_class(
        self, original_code: str, class_name: str, new_class_content: str
    ) -> str:
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        adjusted_start = self._find_decorator_adjusted_start(lines, start_line)
        formatted_content = new_class_content
        return self.replace_lines(
            original_code, adjusted_start, end_line, formatted_content
        )

    def replace_method(
        self, original_code: str, class_name: str, method_name: str, new_method: str
    ) -> str:
        """Replace a method in a class with new content, preserving decorators and overloaded methods."""
        (start_line, end_line) = self.finder.find_method(
            original_code, class_name, method_name
        )
        if start_line == 0 and end_line == 0:
            # Method not found, add it to the class
            return self.add_method_to_class(original_code, class_name, new_method)

        orig_lines = original_code.splitlines()
        new_method_signature = self._extract_method_signature(new_method, method_name)
        method_signature = self._find_method_signature(
            orig_lines, method_name, start_line - 1, start_line + 5
        )

        should_replace = True
        if new_method_signature and method_signature:
            should_replace = self._compare_method_signatures(
                new_method_signature, method_signature
            )

        if not should_replace:
            # Try to find the overloaded method with matching signature
            method_match = self._find_overloaded_method(
                orig_lines, class_name, method_name, new_method_signature
            )
            if method_match:
                method_start, method_end, method_indent = method_match
                formatted_method = self.indentation_service.format_method_content(
                    new_method, method_indent
                )
                return self.replace_lines(
                    original_code, method_start, method_end, formatted_method
                )

        # Standard replacement
        adjusted_start = self._find_decorator_adjusted_start(orig_lines, start_line)
        method_indent = self.indentation_service.calculate_class_indentation(
            orig_lines, class_name
        )
        formatted_method = self.indentation_service.format_method_content(
            new_method, method_indent
        )
        return self.replace_lines(
            original_code, adjusted_start, end_line, formatted_method
        )

    def replace_property(
        self, original_code: str, class_name: str, property_name: str, new_property: str
    ) -> str:
        """Replace a property getter in a class, preserving the setter if present."""
        return self._handle_property_replacement(
            original_code, class_name, property_name, new_property, is_setter=False
        )

    def add_method_to_class(
        self, original_code: str, class_name: str, method_code: str
    ) -> str:
        """Add a new method to a class."""
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 or end_line == 0:
            return original_code

        lines = original_code.splitlines()
        class_indent = (
            self._get_indentation(lines[start_line - 1])
            if start_line <= len(lines)
            else ""
        )
        method_indent = class_indent + "    "

        # Format the method content
        formatted_method = self.indentation_service.format_method_content(
            method_code, method_indent
        )

        # Check if class is empty
        is_empty_class = self._is_empty_class(lines, start_line, end_line)

        if is_empty_class:
            insertion_point = start_line
            modified_lines = (
                lines[:insertion_point] + [formatted_method] + lines[insertion_point:]
            )
        else:
            insertion_point = end_line - 1
            while insertion_point > start_line and (not lines[insertion_point].strip()):
                insertion_point -= 1
            if insertion_point > 0 and lines[insertion_point].strip():
                formatted_method = f"\n{formatted_method}"
            modified_lines = (
                lines[: insertion_point + 1]
                + [formatted_method]
                + lines[insertion_point + 1 :]
            )

        return "\n".join(modified_lines)

    def remove_method_from_class(
        self, original_code: str, class_name: str, method_name: str
    ) -> str:
        (start_line, end_line) = self.finder.find_method(
            original_code, class_name, method_name
        )
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        decorator_start = self._find_decorator_adjusted_start(lines, start_line)
        modified_lines = lines[: decorator_start - 1] + lines[end_line:]
        result = "\n".join(modified_lines)
        while "\n\n\n" in result:
            result = result.replace("\n\n\n", "\n\n")
        return result

    def replace_properties_section(
        self, original_code: str, class_name: str, new_properties: str
    ) -> str:
        (start_line, end_line) = self.finder.find_properties_section(
            original_code, class_name
        )
        formatted_props = self._format_property_lines(new_properties, "    ")

        if start_line == 0 and end_line == 0:
            return self._insert_properties_into_class(
                original_code, class_name, formatted_props
            )

        # Add newline if the next line after properties is a method
        if (
            end_line < len(original_code.splitlines())
            and "def " in original_code.splitlines()[end_line]
        ):
            formatted_props.append("")

        return self.replace_lines(
            original_code, start_line, end_line, "\n".join(formatted_props)
        )

    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        (start_line, end_line) = self.finder.find_imports_section(original_code)
        formatted_imports = []
        for line in new_imports.splitlines():
            if line.strip():
                formatted_imports.append(line.strip())
        normalized_imports = "\n".join(formatted_imports)

        if start_line == 0 and end_line == 0:
            return self._insert_imports_at_beginning(original_code, normalized_imports)

        return self.replace_lines(
            original_code, start_line, end_line, normalized_imports
        )

    def replace_property_setter(
        self, original_code: str, class_name: str, property_name: str, new_setter: str
    ) -> str:
        """Replace a property setter in a class."""
        return self._handle_property_replacement(
            original_code, class_name, property_name, new_setter, is_setter=True
        )

    def _find_decorator_adjusted_start(self, lines, start_line):
        """Find the adjusted start line that includes any decorators."""
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith("@"):
                adjusted_start = i + 1
            elif line and (not line.startswith("#")):
                break
        return adjusted_start

    def _extract_method_signature(self, method_code, method_name):
        """Extract method signature from method code."""
        for line in method_code.strip().splitlines():
            if line.strip().startswith(f"def {method_name}"):
                return line.strip()
        return None

    def _find_method_signature(self, lines, method_name, start_idx, end_idx):
        """Find the method signature in a range of lines."""
        for i in range(start_idx, min(end_idx, len(lines))):
            if i < len(lines) and lines[i].strip().startswith(f"def {method_name}"):
                return lines[i].strip()
        return None

    def _compare_method_signatures(self, sig1, sig2):
        """Compare two method signatures by parameter list."""
        if not sig1 or not sig2:
            return False

        def extract_params(sig):
            start_idx = sig.find("(")
            end_idx = sig.find(")")
            if start_idx == -1 or end_idx == -1:
                return ""
            return sig[start_idx : end_idx + 1]

        return extract_params(sig1) == extract_params(sig2)

    def _find_overloaded_method(self, lines, class_name, method_name, method_signature):
        """Find overloaded method with matching signature in class."""
        in_class = False
        class_indent = None
        all_methods = []

        # Find all methods with the same name in the class
        for i, line in enumerate(lines):
            if line.strip().startswith(f"class {class_name}"):
                in_class = True
                class_indent = self._get_indentation(line)
                continue
            if in_class:
                if (
                    line.strip().startswith("class ")
                    and self._get_indentation(line) <= class_indent
                ):
                    break
                if line.strip().startswith(f"def {method_name}"):
                    method_sig = line.strip()
                    all_methods.append((i + 1, method_sig))

        # Find the method with matching signature
        for method_start, sig in all_methods:
            if self._compare_method_signatures(sig, method_signature):
                method_indent = self._get_indentation(lines[method_start - 1])
                method_end = self._find_method_end(lines, method_start, method_indent)
                adjusted_start = self._find_decorator_adjusted_start(
                    lines, method_start
                )
                method_indent = self.indentation_service.calculate_class_indentation(
                    lines, class_name
                )

                return adjusted_start, method_end, method_indent

        return None

    def _find_method_end(self, lines, start_line, method_indent):
        """Find the end of a method based on indentation."""
        for j in range(start_line, len(lines)):
            if j >= len(lines):
                break
            if lines[j].strip() and self._get_indentation(lines[j]) <= method_indent:
                if not lines[j].strip().startswith("@"):
                    return j
        return len(lines)

    def _handle_property_replacement(
        self, original_code, class_name, property_name, new_content, is_setter=False
    ):
        """Common logic for handling property getter/setter replacement."""
        (getter_start, getter_end) = self.finder.find_property(
            original_code, class_name, property_name
        )
        (setter_start, setter_end) = self.finder.find_property_setter(
            original_code, class_name, property_name
        )

        if is_setter:
            if setter_start == 0 and setter_end == 0:
                return original_code
            target_start, target_end = setter_start, setter_end
        else:
            if getter_start == 0 and getter_end == 0:
                return original_code
            target_start, target_end = getter_start, getter_end

        orig_lines = original_code.splitlines()
        adjusted_start = self._find_decorator_adjusted_start(orig_lines, target_start)

        # Ensure setter has decorator if needed
        content_to_format = new_content
        if is_setter:
            has_decorator = False
            for line in new_content.strip().splitlines():
                if line.strip().startswith(f"@{property_name}.setter"):
                    has_decorator = True
                    break
            if not has_decorator:
                content_to_format = f"@{property_name}.setter\n{new_content.strip()}"

        method_indent = self.indentation_service.calculate_class_indentation(
            orig_lines, class_name
        )
        formatted_content = self.indentation_service.format_method_content(
            content_to_format, method_indent
        )

        # Handle property getter and setter interactions
        has_getter = getter_start > 0 and getter_end > 0
        has_setter = setter_start > 0 and setter_end > 0

        if is_setter and has_getter:
            if setter_start > getter_end:
                return self.replace_lines(
                    original_code, adjusted_start, target_end, formatted_content
                )
            else:
                # Complex case where setter is before getter
                result_lines = []
                for i in range(0, getter_start - 1):
                    result_lines.append(orig_lines[i])

                # Add the getter
                getter_lines = orig_lines[getter_start - 1 : getter_end]
                result_lines.extend(getter_lines)

                # Add the setter
                result_lines.extend(formatted_content.splitlines())

                # Add any remaining lines
                if setter_end < len(orig_lines):
                    result_lines.extend(orig_lines[setter_end:])

                return "\n".join(result_lines)

        return self.replace_lines(
            original_code, adjusted_start, target_end, formatted_content
        )

    def _is_empty_class(self, lines, start_line, end_line):
        """Check if a class has no content other than the class definition."""
        for i in range(start_line, min(end_line, len(lines))):
            if lines[i].strip() and (not lines[i].strip().startswith("class")):
                return False
        return True

    def _format_property_lines(self, properties, indent):
        """Format property lines with consistent indentation."""
        formatted_props = []
        for line in properties.splitlines():
            if line.strip():
                formatted_props.append(f"{indent}{line.strip()}")
        return formatted_props

    def _insert_properties_into_class(self, original_code, class_name, formatted_props):
        """Insert properties into a class when no properties section exists."""
        (class_start, _) = self.finder.find_class(original_code, class_name)
        if class_start == 0:
            return original_code

        lines = original_code.splitlines()
        insertion_line = class_start
        while insertion_line < len(lines) and (
            not (
                lines[insertion_line].strip()
                and (not lines[insertion_line].strip().startswith("class"))
            )
        ):
            insertion_line += 1

        if insertion_line < len(lines) and "def " in lines[insertion_line]:
            formatted_props.append("")

        if insertion_line < len(lines):
            result_lines = (
                lines[:insertion_line] + formatted_props + lines[insertion_line:]
            )
            return "\n".join(result_lines)
        else:
            return original_code

    def _insert_imports_at_beginning(self, original_code, normalized_imports):
        """Insert imports at the beginning of the file, respecting docstrings."""
        lines = original_code.splitlines()

        # Handle docstrings
        first_non_blank = 0
        while first_non_blank < len(lines) and (not lines[first_non_blank].strip()):
            first_non_blank += 1

        if first_non_blank < len(lines) and lines[first_non_blank].strip().startswith(
            '"""'
        ):
            # We have a module docstring, add imports after it
            docstring_end = first_non_blank
            in_docstring = True
            for i in range(first_non_blank + 1, len(lines)):
                docstring_end = i
                if '"""' in lines[i]:
                    in_docstring = False
                    break

            if not in_docstring:
                return (
                    "\n".join(lines[: docstring_end + 1])
                    + "\n\n"
                    + normalized_imports
                    + "\n\n"
                    + "\n".join(lines[docstring_end + 1 :])
                )

        # No docstring, add imports at beginning
        return normalized_imports + "\n\n" + original_code.lstrip()

    def _get_indentation(self, line: str) -> str:
        match = re.match("^(\\s*)", line)
        return match.group(1) if match else ""

    def _is_function_or_method(self, line: str) -> bool:
        return re.match("^\\s*(async\\s+)?def\\s+", line.strip()) is not None

    def _is_class_definition(self, line: str) -> bool:
        return re.match("^\\s*class\\s+", line.strip()) is not None

    def _format_python_code_block(self, code: str, base_indent: str) -> str:
        """Format a Python code block with proper indentation."""
        lines = code.splitlines()
        if not lines:
            return ""
        indent_stack = [0]
        formatted_lines = []
        in_func_def = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                formatted_lines.append("")
                continue
            if stripped.startswith("def ") or stripped.startswith("async def "):
                orig_indent = len(line) - len(line.lstrip())
                if orig_indent > 0:
                    while len(indent_stack) > 1 and indent_stack[-1] >= orig_indent:
                        indent_stack.pop()
                    if indent_stack[-1] < orig_indent:
                        indent_stack.append(orig_indent)
                else:
                    indent_stack = [0]
                in_func_def = True
                curr_indent = base_indent + "    " * (len(indent_stack) - 1)
                formatted_lines.append(f"{curr_indent}{stripped}")
                continue
            if in_func_def and (
                stripped.startswith('"""') or stripped.startswith("'''")
            ):
                curr_indent = base_indent + "    " * len(indent_stack)
                formatted_lines.append(f"{curr_indent}{stripped}")
                in_func_def = False
                continue
            curr_indent = base_indent + "    " * len(indent_stack)
            if not in_func_def:
                orig_indent = len(line) - len(line.lstrip())
                if orig_indent > indent_stack[-1]:
                    indent_stack.append(orig_indent)
                    curr_indent = base_indent + "    " * (len(indent_stack) - 1)
                elif orig_indent < indent_stack[-1]:
                    while len(indent_stack) > 1 and indent_stack[-1] > orig_indent:
                        indent_stack.pop()
                    curr_indent = base_indent + "    " * (len(indent_stack) - 1)
            formatted_lines.append(f"{curr_indent}{stripped}")
            in_func_def = False
        return "\n".join(formatted_lines)

    def _format_class_content(self, code: str, base_indent: str) -> str:
        """Format class content with proper indentation for methods and properties."""
        lines = code.splitlines()
        if not lines:
            return ""
        class_def_index = -1
        decorators = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped.startswith("@"):
                decorators.append(line_stripped)
            elif line_stripped.startswith("class "):
                class_def_index = i
                break
        if class_def_index == -1:
            return self._format_code_with_indentation(code, base_indent)
        formatted_lines = []
        for decorator in decorators:
            formatted_lines.append(f"{base_indent}{decorator}")
        formatted_lines.append(f"{base_indent}{lines[class_def_index].strip()}")
        method_indent = base_indent + "    "
        for i in range(class_def_index + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                formatted_lines.append("")
                continue
            if (
                line.startswith("def ")
                or line.startswith("async def ")
                or line.startswith("@")
            ):
                formatted_lines.append(f"{method_indent}{line}")
            elif line.startswith("class "):
                formatted_lines.append(f"{method_indent}{line}")
            else:
                original_indent = len(lines[i]) - len(lines[i].lstrip())
                if original_indent > 0 and i > 0:
                    prev_non_empty = i - 1
                    while prev_non_empty >= 0 and (not lines[prev_non_empty].strip()):
                        prev_non_empty -= 1
                    if prev_non_empty >= 0:
                        prev_line = lines[prev_non_empty].strip()
                        if prev_line.startswith("def ") or prev_line.startswith("@"):
                            formatted_lines.append(f"{method_indent}    {line}")
                        else:
                            formatted_lines.append(f"{method_indent}{line}")
                    else:
                        formatted_lines.append(f"{method_indent}{line}")
                else:
                    formatted_lines.append(f"{method_indent}{line}")
        return "\n".join(formatted_lines)

    def _format_code_with_indentation(self, code: str, base_indent: str) -> str:
        lines = code.splitlines()
        if not lines:
            return ""
        is_class_def = False
        class_body_indent = base_indent + "    "
        if lines and lines[0].strip().startswith("class "):
            is_class_def = True
        min_indent = float("inf")
        for line in lines:
            if line.strip():
                line_indent = len(line) - len(line.lstrip())
                if line_indent > 0:
                    min_indent = min(min_indent, line_indent)
        if min_indent == float("inf"):
            formatted_lines = []
            for i, line in enumerate(lines):
                line_content = line.strip()
                if not line_content:
                    formatted_lines.append("")
                    continue
                if i == 0:
                    formatted_lines.append(f"{base_indent}{line_content}")
                elif is_class_def and line_content.startswith("def "):
                    formatted_lines.append(f"{class_body_indent}{line_content}")
                elif is_class_def:
                    formatted_lines.append(f"{class_body_indent}{line_content}")
                else:
                    formatted_lines.append(f"{base_indent}{line_content}")
        else:
            formatted_lines = []
            for i, line in enumerate(lines):
                line_content = line.strip()
                if not line_content:
                    formatted_lines.append("")
                    continue
                if i == 0:
                    formatted_lines.append(f"{base_indent}{line_content}")
                    continue
                line_indent = len(line) - len(line.lstrip())
                if is_class_def and line_content.startswith("def "):
                    if line_indent <= min_indent:
                        formatted_lines.append(f"{class_body_indent}{line_content}")
                        continue
                if line_indent >= min_indent:
                    relative_indent = line_indent - min_indent
                    if is_class_def:
                        formatted_lines.append(
                            f"{class_body_indent}{' ' * relative_indent}{line.lstrip()}"
                        )
                    else:
                        formatted_lines.append(
                            f"{base_indent}{' ' * relative_indent}{line.lstrip()}"
                        )
                elif is_class_def:
                    formatted_lines.append(f"{class_body_indent}{line_content}")
                else:
                    formatted_lines.append(f"{base_indent}{line_content}")
        return "\n".join(formatted_lines)

    def fix_special_characters(self, content: str, xpath: str) -> tuple[str, str]:
        updated_content = content
        updated_xpath = xpath
        if content:
            pattern = "def\\s+\\*+(\\w+)\\*+\\s*\\("
            replacement = "def \\1("
            if re.search(pattern, content):
                updated_content = re.sub(pattern, replacement, content)
        if xpath:
            method_pattern = "\\*+(\\w+)\\*+"
            if "." in xpath:
                (class_name, method_name) = xpath.split(".")
                if "*" in method_name:
                    clean_method_name = re.sub(method_pattern, "\\1", method_name)
                    updated_xpath = f"{class_name}.{clean_method_name}"
            elif "*" in xpath:
                clean_name = re.sub(method_pattern, "\\1", xpath)
                updated_xpath = clean_name
        return (updated_content, updated_xpath)

    def fix_class_method_xpath(
        self, content: str, xpath: str, file_path: str = None
    ) -> tuple[str, dict]:
        if "." in xpath:
            return (xpath, {})
        func_def_match = re.search(
            "^\\s*(?:@\\w+)?\\s*(?:async\\s+)?def\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(\\s*self\\b",
            content,
            re.MULTILINE,
        )
        if not func_def_match:
            return (xpath, {})
        method_name = func_def_match.group(1)
        potential_class_name = xpath
        if method_name == potential_class_name:
            return (xpath, {})
        attributes = {
            "target_type": "method",
            "class_name": potential_class_name,
            "method_name": method_name,
        }
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