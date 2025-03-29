# codehem/languages/lang_python/service.py
import re
from typing import List, Optional
from codehem import CodeElementType, CodeElementXPathNode
from codehem.core.Language_service import LanguageService
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
        Supports part-based selectors like [body], [def], etc.
        """
        if not xpath_nodes:
            return None
        from codehem import CodeHem
        element_name = xpath_nodes[-1].name
        element_type = xpath_nodes[-1].type
        element_part = xpath_nodes[-1].part
        parent_name = xpath_nodes[-2].name if len(xpath_nodes) > 1 else None
        include_all = False
        if element_type == 'all':
            include_all = True
            element_type = None
        elements_result = self.extract(code)
        print(f'[DEBUG] Extracted top-level elements:')
        for el in elements_result.elements:
            print(f'[DEBUG] - {el.name} ({el.type})')
            for child in el.children:
                print(f'[DEBUG]     -> {child.name} ({child.type})')
        code_lines = code.splitlines()

        def extract_text(element: CodeElement, code_lines: List[str]) -> Optional[str]:
            if element and element.range:
                start = element.range.start_line
                end = element.range.end_line
                if 1 <= start <= len(code_lines) and 1 <= end <= len(code_lines) and (start <= end):
                    return '\n'.join(code_lines[start - 1:end])
            return None

        def extract_body_only(text: str) -> str:
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith('def ') or line.strip().startswith('class '):
                    return '\n'.join(lines[i + 1:])
            return '\n'.join(lines)

        def extract_def_only(text: str) -> str:
            lines = text.splitlines()
            result = []
            in_body = False
            for line in lines:
                if not in_body and (line.strip().startswith('def ') or line.strip().startswith('class ')):
                    in_body = True
                if in_body:
                    result.append(line)
            return '\n'.join(result)
        parent_xpath = XPathParser.to_string(xpath_nodes[:-1])
        target_xpath = XPathParser.to_string(xpath_nodes)
        filtered_element = CodeHem.filter(elements_result, parent_xpath if parent_name else target_xpath)
        if parent_name and filtered_element:
            print(f'\n[DEBUG] XPath: {XPathParser.to_string(xpath_nodes)}')
            print(f'[DEBUG] Parent: {parent_name} | Target: {element_name} | Type: {element_type} | Part: {element_part}')
            print(f'[DEBUG] Found parent element: {filtered_element.name} with {len(filtered_element.children)} children')
            all_children = filtered_element.children[:]
            for child in filtered_element.children:
                if hasattr(child, 'children'):
                    all_children.extend(child.children)

            # First look for exact matches if element_type is specified
            if element_type:
                exact_matches = []
                for child in all_children:
                    child_type_str = child.type.value if hasattr(child.type, 'value') else str(child.type)
                    print(f'[DEBUG]   -> Child: {child.name}, type={child_type_str}')
                    if child.name == element_name and child_type_str == element_type:
                        exact_matches.append(child)
                        print(f"[DEBUG] MATCHED child '{child.name}'")

                if exact_matches:
                    # Use the last match if we have multiple
                    matched_child = exact_matches[-1]
                    text = extract_text(matched_child, code_lines)
                    if element_part == 'body':
                        return extract_body_only(text or '')
                    if element_part == 'def':
                        return extract_def_only(text or '')
                    return text

            # If no exact type match or no type specified, search by name only
            # Prioritize property_setter over property_getter when no type specified
            property_getter = None
            property_setter = None
            fallback_method = None

            for child in all_children:
                child_type_str = child.type.value if hasattr(child.type, 'value') else str(child.type)
                print(f'[DEBUG]   -> Child: {child.name}, type={child_type_str}')
                if child.name == element_name:
                    if child_type_str == 'property_setter':
                        property_setter = child
                    elif child_type_str == 'property_getter':
                        property_getter = child
                    elif child_type_str == 'method':
                        fallback_method = child
                    # Match found if we're not looking for a specific type
                    if not element_type:
                        print(f"[DEBUG] MATCHED child '{child.name}'")

            # Choose the match in order of priority: property_setter, property_getter, method
            matched_child = property_setter or property_getter or fallback_method

            if matched_child:
                text = extract_text(matched_child, code_lines)
                if element_part == 'body':
                    return extract_body_only(text or '')
                if element_part == 'def':
                    return extract_def_only(text or '')
                return text

            print('[DEBUG] No matching child found.')
            return None
        if filtered_element:
            text = extract_text(filtered_element, code_lines)
            if not element_type and filtered_element.children:
                preferred = None
                property_setter = None
                property_getter = None

                # First look for property_setter with matching name
                for child in filtered_element.children:
                    child_type_str = child.type.value if hasattr(child.type, 'value') else str(child.type)
                    if child.name == element_name:
                        if child_type_str == 'property_setter':
                            property_setter = child
                        elif child_type_str == 'property_getter':
                            property_getter = child

                # Priority: setter, getter
                preferred = property_setter or property_getter

                if preferred:
                    text = extract_text(preferred, code_lines)
                    filtered_element = preferred
            element_type_str = filtered_element.type.value if hasattr(filtered_element.type, 'value') else str(filtered_element.type)
            if element_part is None and (not include_all) and (element_type_str in ['property_getter', 'property_setter', 'method']):
                decorator_lines = [child.content for child in filtered_element.children if child.type == CodeElementType.DECORATOR]
                if decorator_lines:
                    text = '\n'.join(decorator_lines + [text])
            if element_part == 'body':
                return extract_body_only(text or '')
            if element_part == 'def':
                return extract_def_only(text or '')
            if include_all:
                decorators_text = '\n'.join([child.content for child in filtered_element.children if child.type == CodeElementType.DECORATOR])
                return f'{text}\n{decorators_text}' if decorators_text else text
            return text
        return None
