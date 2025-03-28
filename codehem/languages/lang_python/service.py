# codehem/languages/lang_python/service.py
import re
from typing import List, Optional
from codehem import CodeElementType, CodeElementXPathNode
from codehem.core.service import LanguageService
from codehem.core.registry import language_service
from codehem.core.engine.xpath_parser import XPathParser
from codehem.models import CodeRange
from codehem.models.code_element import CodeElementsResult, CodeElement
import logging

logger = logging.getLogger(__name__)

@language_service
class PythonLanguageService(LanguageService):
    """Python language service implementation."""
    LANGUAGE_CODE = 'python'

    @property
    def file_extensions(self) -> List[str]:
        return ['.py']

    @property
    def supported_element_types(self) -> List[str]:
        return [CodeElementType.CLASS.value, CodeElementType.FUNCTION.value, CodeElementType.METHOD.value, CodeElementType.IMPORT.value, CodeElementType.DECORATOR.value, CodeElementType.PROPERTY.value, CodeElementType.PROPERTY_GETTER.value, CodeElementType.PROPERTY_SETTER.value, CodeElementType.STATIC_PROPERTY.value]

    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of Python code element.
        Args:
            code: The code to analyze
        Returns:
            Element type string (from CodeElementType)
        """
        code = code.strip()
        if re.match('^\\s*class\\s+\\w+', code):
            return CodeElementType.CLASS.value
        if re.search('def\\s+\\w+\\s*\\(\\s*(?:self|cls)[,\\s)]', code) and (not re.match('^\\s*class\\s+', code)):
            return CodeElementType.METHOD.value
        if re.search('@property', code):
            return CodeElementType.PROPERTY_GETTER.value
        if re.search('@\\w+\\.setter', code):
            return CodeElementType.PROPERTY_SETTER.value
        if re.match('^\\s*def\\s+\\w+', code) and (not re.search('def\\s+\\w+\\s*\\(\\s*(?:self|cls)[,\\s)]', code)):
            return CodeElementType.FUNCTION.value
        if re.match('(?:import|from)\\s+\\w+', code):
            return CodeElementType.IMPORT.value
        if re.match('[A-Z][A-Z0-9_]*\\s*=', code):
            return CodeElementType.STATIC_PROPERTY.value
        if re.match('self\\.\\w+\\s*=', code):
            return CodeElementType.PROPERTY.value
        return CodeElementType.UNKNOWN.value

    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    def _extract_and_attach_decorators(self, code: str, element, extractor) -> None:
        """
        Extract decorators and attach them as children to the element.
        Args:
        code: Source code as string
        element: CodeElement to attach decorators to
        extractor: Extractor instance to use
        """
        if element.type not in [CodeElementType.CLASS, CodeElementType.METHOD, CodeElementType.FUNCTION]:
            return
        if not element.content:
            return
        decorator_extractor = extractor.get_descriptor('decorator')
        if not decorator_extractor:
            return
        decorators = decorator_extractor.extract(element.content, {'language_code': self.language_code})
        for dec in decorators:
            if dec.get('parent_name') == element.name:
                decorator_element = self._convert_to_code_element(dec)
                decorator_element.type = CodeElementType.DECORATOR
                decorator_element.parent_name = element.name
                element.children.append(decorator_element)
        if element.type == CodeElementType.METHOD and element.parent_name:
            class_elements = extractor.extract_classes(code)
            for class_elem in class_elements:
                if class_elem.get('name') == element.parent_name:
                    class_decorators = decorator_extractor.extract(class_elem.get('content', ''), {'language_code': self.language_code})
                    for dec in class_decorators:
                        if dec.get('parent_name') == element.name:
                            decorator_element = self._convert_to_code_element(dec)
                            decorator_element.type = CodeElementType.DECORATOR
                            decorator_element.parent_name = element.name
                            element.children.append(decorator_element)
                    break

    def _convert_to_code_element(self, raw_element: dict) -> CodeElement:
        """Helper to convert a raw extracted element dictionary to a CodeElement."""
        element_type_str = raw_element.get('type', 'unknown')
        name = raw_element.get('name', '')
        content = raw_element.get('content', '')
        element_type = CodeElementType.UNKNOWN
        if element_type_str == 'function':
            element_type = CodeElementType.FUNCTION
        elif element_type_str == 'class':
            element_type = CodeElementType.CLASS
        elif element_type_str == 'method':
            element_type = CodeElementType.METHOD
        elif element_type_str == 'property_getter':
            element_type = CodeElementType.PROPERTY_GETTER
        elif element_type_str == 'property_setter':
            element_type = CodeElementType.PROPERTY_SETTER
        elif element_type_str == 'import':
            element_type = CodeElementType.IMPORT
        elif element_type_str == 'decorator':
            element_type = CodeElementType.DECORATOR
        elif element_type_str == 'property':
            element_type = CodeElementType.PROPERTY
        elif element_type_str == 'static_property':
            element_type = CodeElementType.STATIC_PROPERTY
        range_data = raw_element.get('range')
        code_range = None
        if range_data:
            start_line = range_data['start']['line']
            end_line = range_data['end']['line']
            if isinstance(start_line, int) and start_line == 0:
                start_line = 1
            if isinstance(end_line, int) and end_line == 0:
                end_line = 1
            code_range = CodeRange(start_line=start_line, start_column=range_data.get('start', {}).get('column', 0), end_line=end_line, end_column=range_data.get('end', {}).get('column', 0))
        element = CodeElement(type=element_type, name=name, content=content, range=code_range, parent_name=raw_element.get('class_name'), children=[])
        return element

    def get_text_by_xpath_internal(self, code: str, xpath_nodes: List['CodeElementXPathNode']) -> Optional[str]:
        """
        Internal method to retrieve text content based on parsed XPath nodes for Python.
        """
        if not xpath_nodes:
            return None
        from codehem import CodeHem
        element_name = xpath_nodes[-1].name
        element_type = xpath_nodes[-1].type
        parent_name = xpath_nodes[-2].name if len(xpath_nodes) > 1 else None
        include_all = False
        if element_type == 'all':
            include_all = True
            element_type = None
        elements_result = self.extract(code)
        code_lines = code.splitlines()

        def extract_text(element: CodeElement, code_lines: List[str]) -> Optional[str]:
            """Extract text content from code based on element range."""
            if element and element.range:
                start = element.range.start_line
                end = element.range.end_line
                if 1 <= start <= len(code_lines) and 1 <= end <= len(code_lines) and (start <= end):
                    return '\n'.join(code_lines[start - 1:end])
            return None

        if len(xpath_nodes) == 1:
            filtered_element = CodeHem.filter(elements_result, XPathParser.to_string(xpath_nodes))
            if filtered_element:
                text = extract_text(filtered_element, code_lines)
                if include_all:
                    decorators_text = '\n'.join([child.content for child in filtered_element.children if child.type == CodeElementType.DECORATOR])
                    return f'{text}\n{decorators_text}' if decorators_text else text
                return text
            return None

        if parent_name:
            # For property getters/setters, we'll directly search in the code
            if element_name and element_type == CodeElementType.PROPERTY_GETTER.value:
                # Fixed pattern to capture both decorator and method definition
                pattern = fr'@property\s*\n\s*def\s+{re.escape(element_name)}\s*\([^)]*\)'
                match = re.search(pattern, code, re.DOTALL)
                if match:
                    # Find the method start and end
                    start_pos = match.start()
                    start_line = code[:start_pos].count('\n') + 1

                    # Get the base indentation from the decorator line
                    base_indent = None
                    for i in range(start_line-1, min(start_line+2, len(code_lines))):
                        line = code_lines[i]
                        if '@property' in line:
                            base_indent = self.get_indentation(line)
                            break

                    if not base_indent:
                        base_indent = self.get_indentation(code_lines[start_line-1]) if start_line-1 < len(code_lines) else '    '

                    # Extract the complete property method
                    property_block = []
                    in_property = False
                    for i in range(start_line-1, len(code_lines)):
                        line = code_lines[i]

                        # Start capturing at property decorator
                        if '@property' in line:
                            in_property = True

                        if in_property:
                            # Check if we've found the end of the method block
                            line_indent = self.get_indentation(line)
                            if (line.strip() and len(line_indent) <= len(base_indent) and 
                                not line.strip().startswith('@') and i > start_line):
                                break

                            property_block.append(line)

                    if property_block:
                        return '\n'.join(property_block)

            if element_name and element_type == CodeElementType.PROPERTY_SETTER.value:
                # Similar pattern for property setter
                pattern = fr'@{re.escape(element_name)}\.setter\s*\n\s*def\s+{re.escape(element_name)}\s*\([^)]*\)'
                match = re.search(pattern, code, re.DOTALL)
                if match:
                    start_pos = match.start()
                    start_line = code[:start_pos].count('\n') + 1

                    # Get the base indentation from the decorator line
                    base_indent = None
                    for i in range(start_line-1, min(start_line+2, len(code_lines))):
                        line = code_lines[i]
                        if f'@{element_name}.setter' in line:
                            base_indent = self.get_indentation(line)
                            break

                    if not base_indent:
                        base_indent = self.get_indentation(code_lines[start_line-1]) if start_line-1 < len(code_lines) else '    '

                    # Extract the complete setter method
                    property_block = []
                    in_property = False
                    for i in range(start_line-1, len(code_lines)):
                        line = code_lines[i]

                        # Start capturing at setter decorator
                        if f'@{element_name}.setter' in line:
                            in_property = True

                        if in_property:
                            # Check if we've found the end of the method block
                            line_indent = self.get_indentation(line)
                            if (line.strip() and len(line_indent) <= len(base_indent) and 
                                not line.strip().startswith('@') and i > start_line):
                                break

                            property_block.append(line)

                    if property_block:
                        return '\n'.join(property_block)

            # Continue with the original implementation for other cases
            parent_xpath = XPathParser.to_string(xpath_nodes[:-1])
            parent_element = CodeHem.filter(elements_result, parent_xpath)
            if parent_element and hasattr(parent_element, 'children'):
                property_getters = []
                property_setters = []
                regular_methods = []
                for child in parent_element.children:
                    if hasattr(child, 'name') and child.name == element_name:
                        if child.type == CodeElementType.PROPERTY_GETTER:
                            property_getters.append(child)
                        elif child.type == CodeElementType.PROPERTY_SETTER:
                            property_setters.append(child)
                        else:
                            regular_methods.append(child)
                if element_type == CodeElementType.PROPERTY_GETTER.value and property_getters:
                    return extract_text(property_getters[0], code_lines)
                if element_type == CodeElementType.PROPERTY_SETTER.value and property_setters:
                    return extract_text(property_setters[0], code_lines)
                if not element_type or element_type == 'method':
                    if property_getters:
                        return extract_text(property_getters[0], code_lines)
                    if property_setters:
                        return extract_text(property_setters[0], code_lines)
                if regular_methods and (not property_getters) and (not property_setters):
                    return extract_text(regular_methods[-1], code_lines)
        return None
