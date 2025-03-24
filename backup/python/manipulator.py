"""
Python-specific manipulator implementation.
"""
import re
from typing import Optional, Tuple, Callable, Dict
from ..common.manipulator import CommonManipulator
from ...models import CodeElementType

class PythonManipulator(CommonManipulator):
    """
    Python-specific implementation of the code manipulator.
    """

    def __init__(self, analyzer, formatter):
        """
        Initialize the Python manipulator.
        
        Args:
            analyzer: Python analyzer instance
            formatter: Python formatter instance
        """
        super().__init__(analyzer, formatter)

    def _get_add_handler(self, element_type: str) -> Optional[Callable]:
        """
        Get the handler function for adding an element of the specified type.

        Args:
        element_type: Element type

        Returns:
        Handler function or None if no specific handler
        """
        handlers = {
            CodeElementType.CLASS.value: self._add_class,
            CodeElementType.METHOD.value: self._add_method_to_class,
            CodeElementType.FUNCTION.value: self._add_function,
            CodeElementType.PROPERTY.value: self._add_property_to_class,
            CodeElementType.PROPERTY_GETTER.value: self._add_property_getter_to_class,
            CodeElementType.PROPERTY_SETTER.value: self._add_property_setter_to_class,
            CodeElementType.STATIC_PROPERTY.value: self._add_static_property_to_class,
            CodeElementType.IMPORT.value: self._add_import
        }
        return handlers.get(element_type)

    def _add_class(self, original_code: str, class_name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add a new class to the code.
        
        Args:
            original_code: Original source code
            class_name: Name of the class to add
            new_code: Class code
            parent_name: Not used for classes
            
        Returns:
            Modified code
        """
        return original_code.rstrip() + '\n\n\n' + new_code

    def _add_function(self, original_code: str, function_name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add a new function to the code.
        
        Args:
            original_code: Original source code
            function_name: Name of the function to add
            new_code: Function code
            parent_name: Not used for functions
            
        Returns:
            Modified code
        """
        return original_code.rstrip() + '\n\n\n' + new_code

    def _add_method_to_class(self, original_code: str, method_name: str, new_code: str, class_name: Optional[str]=None) -> str:
        """
        Add a new method to a class.
        
        Args:
            original_code: Original source code
            method_name: Name of the method to add
            new_code: Method code
            class_name: Name of the class to add the method to
            
        Returns:
            Modified code
        """
        if not class_name:
            return self._add_function(original_code, method_name, new_code)
        (start_line, end_line) = self.analyzer.find_element(original_code, CodeElementType.CLASS.value, class_name)
        if start_line == 0 or end_line == 0:
            return original_code
        lines = original_code.splitlines()
        class_line = lines[start_line - 1]
        class_indent = self.formatter.get_indentation(class_line)
        method_indent = class_indent + self.formatter.indent_string
        formatted_method = self.formatter.format_method(new_code)
        indented_method = self.formatter.apply_indentation(formatted_method, method_indent)
        insertion_point = end_line - 1
        for i in range(end_line - 1, start_line - 1, -1):
            if i < len(lines) and lines[i].strip():
                insertion_point = i + 1
                break
        if insertion_point > 0 and insertion_point < len(lines) and lines[insertion_point - 1].strip():
            indented_method = f'\n{indented_method}'
        modified_lines = lines[:insertion_point] + [indented_method] + lines[insertion_point:]
        return '\n'.join(modified_lines)

    def _add_property_to_class(self, original_code: str, property_name: str, new_code: str, class_name: Optional[str]=None) -> str:
        """
        Add a new property to a class.
        
        Args:
            original_code: Original source code
            property_name: Name of the property to add
            new_code: Property code
            class_name: Name of the class to add the property to
            
        Returns:
            Modified code
        """
        return self._add_method_to_class(original_code, property_name, new_code, class_name)

    def _add_property_getter_to_class(self, original_code: str, property_name: str, new_code: str, class_name: Optional[str]=None) -> str:
        """
        Add a new property getter to a class.
        
        Args:
            original_code: Original source code
            property_name: Name of the property getter to add
            new_code: Property getter code
            class_name: Name of the class to add the property getter to
            
        Returns:
            Modified code
        """
        if not new_code.strip().startswith('@property'):
            new_code = '@property\n' + new_code
        return self._add_method_to_class(original_code, property_name, new_code, class_name)

    def _add_property_setter_to_class(self, original_code: str, property_name: str, new_code: str, class_name: Optional[str]=None) -> str:
        """
        Add a new property setter to a class.
        
        Args:
            original_code: Original source code
            property_name: Name of the property setter to add
            new_code: Property setter code
            class_name: Name of the class to add the property setter to
            
        Returns:
            Modified code
        """
        setter_decorator = f'@{property_name}.setter'
        if not new_code.strip().startswith(setter_decorator):
            new_code = setter_decorator + '\n' + new_code
        return self._add_method_to_class(original_code, property_name, new_code, class_name)

    def _add_static_property_to_class(self, original_code: str, property_name: str, new_code: str, class_name: Optional[str]=None) -> str:
        """
        Add a new static property (class variable) to a class.
        
        Args:
            original_code: Original source code
            property_name: Name of the static property to add
            new_code: Static property code
            class_name: Name of the class to add the static property to
            
        Returns:
            Modified code
        """
        if not class_name:
            return original_code.rstrip() + '\n\n' + new_code
        (start_line, end_line) = self.analyzer.find_element(original_code, CodeElementType.CLASS.value, class_name)
        if start_line == 0 or end_line == 0:
            return original_code
        lines = original_code.splitlines()
        class_line = lines[start_line - 1]
        class_indent = self.formatter.get_indentation(class_line)
        prop_indent = class_indent + self.formatter.indent_string
        formatted_prop = self.formatter.format_static_property(new_code)
        indented_prop = self.formatter.apply_indentation(formatted_prop, prop_indent)
        insertion_point = start_line
        for i in range(start_line, end_line):
            if i < len(lines):
                line = lines[i].strip()
                if line.startswith('def ') or line.startswith('@'):
                    insertion_point = i
                    break
                elif line and (not line.startswith('#')) and (not line == 'pass'):
                    insertion_point = i + 1
        if insertion_point == start_line:
            if insertion_point < len(lines) and '{' in lines[insertion_point]:
                insertion_point += 1
            indented_prop = '\n' + indented_prop
        modified_lines = lines[:insertion_point] + [indented_prop] + lines[insertion_point:]
        return '\n'.join(modified_lines)

    def _add_import(self, original_code: str, import_name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add new import statements to the code.

        Args:
        original_code: Original source code
        import_name: Not used for imports
        new_code: Import statements
        parent_name: Not used for imports

        Returns:
        Modified code
        """
        formatted_imports = self.formatter.format_import(new_code)
        (start_line, end_line) = self.analyzer.find_element(original_code, CodeElementType.IMPORT.value, '')
        if start_line > 0 and end_line > 0:
            lines = original_code.splitlines()
            existing_imports = '\n'.join(lines[start_line - 1:end_line])
            combined_imports = existing_imports + '\n' + formatted_imports
            return original_code[:original_code.find(existing_imports)] + combined_imports + original_code[original_code.find(existing_imports) + len(existing_imports):]
        else:
            lines = original_code.splitlines()
            first_non_blank = 0
            while first_non_blank < len(lines) and (not lines[first_non_blank].strip()):
                first_non_blank += 1
            if first_non_blank < len(lines) and lines[first_non_blank].strip().startswith('"""'):
                in_docstring = True
                docstring_end = first_non_blank
                for i in range(first_non_blank + 1, len(lines)):
                    if '"""' in lines[i]:
                        docstring_end = i
                        in_docstring = False
                        break
                if not in_docstring:
                    return '\n'.join(lines[:docstring_end + 1]) + '\n\n' + formatted_imports + '\n\n' + '\n'.join(lines[docstring_end + 1:])
            return formatted_imports + '\n\n' + original_code.lstrip()

    # Implement the missing abstract methods 
    def remove_element(self, original_code: str, element_type: str, name: str, parent_name: Optional[str]=None) -> str:
        """
        Remove an element from the code.
        
        Args:
            original_code: Original source code
            element_type: Type of element to remove
            name: Name of the element to remove
            parent_name: Name of parent element (e.g., class name for methods)
            
        Returns:
            Modified code
        """
        (start_line, end_line) = self.analyzer.find_element(original_code, element_type, name, parent_name)
        if start_line > 0 and end_line > 0:
            return self.replace_lines(original_code, start_line, end_line, '')
        return original_code

    def replace_lines(self, original_code: str, start_line: int, end_line: int, new_content: str) -> str:
        """
        Replace specific lines in the code.
        
        Args:
            original_code: Original source code
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)
            new_content: New content to replace the lines with
            
        Returns:
            Modified code
        """
        if start_line <= 0 or end_line < start_line:
            return original_code
        lines = original_code.splitlines()
        if start_line > len(lines):
            if new_content:
                return original_code.rstrip() + '\n\n' + new_content
            return original_code
        start_idx = start_line - 1
        end_idx = min(end_line - 1, len(lines) - 1)
        new_lines = []
        if start_idx > 0:
            new_lines.extend(lines[:start_idx])
        if new_content:
            new_content_lines = new_content.splitlines()
            new_lines.extend(new_content_lines)
        if end_idx < len(lines) - 1:
            new_lines.extend(lines[end_idx + 1:])
        result = '\n'.join(new_lines)
        if original_code.endswith('\n') and (not result.endswith('\n')):
            result += '\n'
        return result

    def fix_special_characters(self, content: str, xpath: str) -> Tuple[str, str]:
        """
        Fix special characters in content and xpath for Python code.
        
        Args:
            content: Code content
            xpath: XPath expression
            
        Returns:
            Tuple of (fixed_content, fixed_xpath)
        """
        updated_content = content
        updated_xpath = xpath
        if content:
            pattern = 'def\\s+\\*+([A-Za-z_][A-Za-z0-9_]*)\\*+\\s*\\('
            replacement = 'def \\1('
            if re.search(pattern, content):
                updated_content = re.sub(pattern, replacement, content)
        if xpath:
            method_pattern = '\\*+([A-Za-z_][A-Za-z0-9_]*)\\*+'
            if '.' in xpath:
                (class_name, method_name) = xpath.split('.')
                if '*' in method_name:
                    clean_method_name = re.sub(method_pattern, '\\1', method_name)
                    updated_xpath = f'{class_name}.{clean_method_name}'
            elif '*' in xpath:
                clean_name = re.sub(method_pattern, '\\1', xpath)
                updated_xpath = clean_name
        return (updated_content, updated_xpath)