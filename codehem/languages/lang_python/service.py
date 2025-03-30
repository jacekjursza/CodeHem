# codehem/languages/lang_python/service.py
import re
import logging
from typing import List, Optional, Tuple
from codehem import CodeElementType, CodeElementXPathNode
from codehem.core.Language_service import LanguageService
from codehem.core.registry import language_service
from codehem.core.engine.xpath_parser import XPathParser
from codehem.models import CodeRange
from codehem.models.code_element import CodeElementsResult, CodeElement

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
        return [
            CodeElementType.CLASS.value,
            CodeElementType.FUNCTION.value,
            CodeElementType.METHOD.value,
            CodeElementType.IMPORT.value,
            CodeElementType.DECORATOR.value,
            CodeElementType.PROPERTY_GETTER.value,
            CodeElementType.PROPERTY_SETTER.value,
            CodeElementType.STATIC_PROPERTY.value,
        ]

    def detect_element_type(self, code: str) -> str:
        """Detects the type of Python code element (simplified detection)."""
        code_stripped = code.strip()
        if re.search(r'@\w+\.setter', code_stripped):
            return CodeElementType.PROPERTY_SETTER.value
        if re.search(r'@property', code_stripped):
             return CodeElementType.PROPERTY_GETTER.value
        if re.match(r'^\s*class\s+\w+', code_stripped):
            return CodeElementType.CLASS.value
        if re.search(r'def\s+\w+\s*\(\s*(?:self|cls)\b', code_stripped):
             return CodeElementType.METHOD.value
        if re.match(r'^\s*def\s+\w+', code_stripped):
            return CodeElementType.FUNCTION.value
        if re.match(r'^(?:import|from)\s+\w+', code_stripped):
            return CodeElementType.IMPORT.value
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*[:=]', code_stripped):
             return CodeElementType.STATIC_PROPERTY.value

        return CodeElementType.UNKNOWN.value

    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    def _find_target_element(self, elements_result: CodeElementsResult, xpath_nodes: List['CodeElementXPathNode']) -> Optional[CodeElement]:
        """Finds the target CodeElement based on parsed XPath."""
        if not xpath_nodes:
            return None

        target_node_info = xpath_nodes[-1]
        target_name = target_node_info.name
        target_type = target_node_info.type # Can be None

        parent_element = None
        if len(xpath_nodes) > 1:
            parent_xpath_str = XPathParser.to_string(xpath_nodes[:-1])
            from codehem import CodeHem # Avoid import inside method if possible
            parent_element = CodeHem.filter(elements_result, parent_xpath_str)
            if not parent_element:
                 logger.debug(f"_find_target_element: Parent not found for XPath: {parent_xpath_str}")
                 return None
            logger.debug(f"_find_target_element: Found parent: {parent_element.name} ({parent_element.type.value})")
            search_list = parent_element.children
        else:
            search_list = elements_result.elements

        matches = []
        for element in search_list:
            name_match = (element.name == target_name)
            if not name_match: continue
            type_match = (target_type is None) or (element.type.value == target_type)
            if not type_match: continue
            matches.append(element)

        if not matches:
            logger.debug(f"_find_target_element: No direct match found for '{target_name}' (type: {target_type})")
            if target_type is None and parent_element: # Fallback for type-less XPath in class
                 possible_matches = []
                 for element in parent_element.children:
                      if element.name == target_name and element.type in [CodeElementType.PROPERTY_SETTER, CodeElementType.PROPERTY_GETTER, CodeElementType.METHOD]:
                           possible_matches.append(element)

                 if possible_matches:
                      possible_matches.sort(key=lambda el: (
                           2 if el.type == CodeElementType.PROPERTY_SETTER else
                           1 if el.type == CodeElementType.PROPERTY_GETTER else
                           0,
                           el.range.start_line if el.range else 0
                      ), reverse=True)
                      logger.debug(f"_find_target_element: Found {len(possible_matches)} candidates for '{target_name}'. Selected: {possible_matches[0].type.value}")
                      return possible_matches[0]
            return None

        matches.sort(key=lambda el: el.range.start_line if el.range else 0)
        logger.debug(f"_find_target_element: Found {len(matches)} exact matches for '{target_name}' (type: {target_type}). Selected last.")
        return matches[-1]

    def _extract_part(self, code: str, element: CodeElement, part_name: Optional[str]) -> Optional[str]:
        """
        Extracts a specific part of the element (def, body) or the whole,
        preserving original indentation.
        """
        if not element or not element.range:
             logger.warning(f"Attempting to extract part from element without range: {element.name if element else 'None'}")
             return None

        code_lines = code.splitlines()
        element_start_idx = element.range.start_line - 1
        element_end_idx = element.range.end_line # Index of the line *after* the element's last line

        if element_start_idx < 0 or element_end_idx > len(code_lines) or element_start_idx >= element_end_idx:
             logger.error(f"Invalid line range for element '{element.name}': {element.range}")
             return None

        # --- Identify decorator and definition lines ---
        decorator_line_indices = set()
        definition_line_idx = -1
        first_body_line_idx = -1

        # Get decorator line ranges
        for child in element.children:
            if child.type == CodeElementType.DECORATOR and child.range:
                dec_start = child.range.start_line - 1
                dec_end = child.range.end_line - 1 # Decorator range is inclusive
                for i in range(dec_start, dec_end + 1):
                     if element_start_idx <= i < element_end_idx:
                          decorator_line_indices.add(i)
            elif child.type == CodeElementType.DECORATOR:
                 logger.warning(f"Decorator '{child.name}' for element '{element.name}' lacks range info.")

        # Find definition line (first non-decorator, non-empty line)
        for i in range(element_start_idx, element_end_idx):
             if i not in decorator_line_indices and code_lines[i].strip():
                  # Check if it looks like a Python definition
                  if code_lines[i].strip().startswith(('def ', 'class ')):
                       definition_line_idx = i
                       first_body_line_idx = i + 1
                       break
                  else: # Treat first non-empty, non-decorator as definition (e.g., for static props)
                      definition_line_idx = i
                      first_body_line_idx = i # Body starts on the same line
                      break

        if definition_line_idx == -1: # Fallback if no definition line found
             definition_line_idx = element_start_idx
             first_body_line_idx = element_end_idx
             logger.warning(f"Could not find definition line for element '{element.name}' in range {element.range.start_line}-{element.range.end_line}.")

        # --- Select lines based on 'part_name' ---
        start_idx_to_extract = -1
        end_idx_to_extract = -1 # Exclusive end index

        if part_name == 'body':
            start_idx_to_extract = first_body_line_idx
            end_idx_to_extract = element_end_idx
            if start_idx_to_extract >= end_idx_to_extract:
                 logger.warning(f"Cannot extract '[body]' for '{element.name}', no body lines found.")
                 return "" # Return empty string for empty body

        elif part_name == 'def':
            start_idx_to_extract = definition_line_idx
            end_idx_to_extract = element_end_idx
            if start_idx_to_extract == -1: # Should not happen with fallback, but check
                logger.warning(f"Cannot extract '[def]' for '{element.name}', definition line not found.")
                return None


        else: # Default or '[all]' -> return everything including decorators
            start_idx_to_extract = element_start_idx
            end_idx_to_extract = element_end_idx


        # --- Get the final lines ---
        if 0 <= start_idx_to_extract < end_idx_to_extract <= len(code_lines):
             result_lines = code_lines[start_idx_to_extract:end_idx_to_extract]
             # --- ZMIANA: Usunięto logikę usuwania wcięć ---
             # Zwracamy linie z oryginalnymi wcięciami
             return '\n'.join(result_lines)
        elif start_idx_to_extract == end_idx_to_extract: # Empty selection (e.g., empty body)
             return ""
        else:
             logger.error(f"Calculated invalid extraction range [{start_idx_to_extract}:{end_idx_to_extract}] for element '{element.name}'.")
             return None


    def get_text_by_xpath_internal(self, code: str, xpath_nodes: List['CodeElementXPathNode']) -> Optional[str]:
        """
        Internal implementation for getting text based on parsed XPath nodes for Python.
        """
        logger.debug(f"get_text_by_xpath_internal: Starting for XPath: {XPathParser.to_string(xpath_nodes)}")
        if not xpath_nodes:
            return None

        try:
            elements_result = self.extract(code)
            logger.debug(f"get_text_by_xpath_internal: Extraction completed, {len(elements_result.elements)} top-level elements.")
        except Exception as e:
             logger.error(f"Critical error during extraction in get_text_by_xpath_internal: {e}", exc_info=True)
             return None

        target_element = self._find_target_element(elements_result, xpath_nodes)

        if not target_element:
            logger.warning(f"get_text_by_xpath_internal: Element not found for XPath: {XPathParser.to_string(xpath_nodes)}")
            return None

        logger.debug(f"get_text_by_xpath_internal: Found matching element: {target_element.name} ({target_element.type.value})")

        requested_part = xpath_nodes[-1].part
        # Handle '[all]' - treat as no 'part' requested
        if xpath_nodes[-1].type == 'all':
             requested_part = None
             logger.debug(f"get_text_by_xpath_internal: Detected type '[all]', treating as no specific part requested.")

        logger.debug(f"get_text_by_xpath_internal: Requested part: '{requested_part}'")

        extracted_text = self._extract_part(code, target_element, requested_part)

        if extracted_text is None:
             logger.error(f"get_text_by_xpath_internal: Error extracting part '{requested_part}' for element '{target_element.name}'.")
             return None

        return extracted_text