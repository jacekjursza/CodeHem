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
        """Finds the target CodeElement based on parsed XPath, handling FILE prefix."""
        if not xpath_nodes:
            return None

        current_nodes = xpath_nodes
        search_list = elements_result.elements # Domyślnie szukamy w elementach głównych

        # Sprawdź, czy pierwszy węzeł to FILE i zignoruj go w dalszym przetwarzaniu ścieżki
        if current_nodes and current_nodes[0].type == CodeElementType.FILE.value:
            logger.debug("_find_target_element: Detected FILE prefix, searching top-level elements.")
            current_nodes = current_nodes[1:] # Pomiń węzeł FILE
            if not current_nodes: # Jeśli XPath to tylko FILE, co zwrócić? Na razie None.
                 logger.warning("_find_target_element: XPath contains only FILE node, cannot select specific element.")
                 return None
            # Nadal szukamy w elementach głównych
            search_list = elements_result.elements
            parent_element_context = None # Jesteśmy na najwyższym poziomie

        # Przetwarzanie pozostałych węzłów (lub wszystkich, jeśli nie było FILE)
        target_element = None
        current_search_context = search_list # Lista elementów do przeszukania na danym poziomie

        for i, node in enumerate(current_nodes):
            target_name = node.name
            target_type = node.type # Może być None
            found_in_level = None
            possible_matches = [] # Dla obsługi getter/setter/method fallback

            logger.debug(f"_find_target_element: Level {i}, searching for name='{target_name}', type='{target_type}' in {len(current_search_context)} elements.")

            for element in current_search_context:
                # Sprawdź dopasowanie nazwy
                name_match = (element.name == target_name)
                if not name_match: continue

                # Sprawdź dopasowanie typu
                type_match = (target_type is None) or (element.type.value == target_type)

                if name_match and type_match:
                     # Dokładne dopasowanie nazwy i typu (jeśli podany)
                     possible_matches.append(element)
                     logger.debug(f"  -> Found exact match: {element.name} ({element.type.value})")
                elif name_match and target_type is None:
                     # Dopasowanie nazwy, ale typ nie był specyfikowany w XPath
                     # Sprawdź czy to potencjalny getter/setter/method (jeśli szukamy w klasie)
                     if element.type in [CodeElementType.PROPERTY_SETTER, CodeElementType.PROPERTY_GETTER, CodeElementType.METHOD]:
                          possible_matches.append(element)
                          logger.debug(f"  -> Found potential match (name only): {element.name} ({element.type.value})")
                     # Jeśli szukamy na najwyższym poziomie, a typ nie podany, może to być klasa lub funkcja
                     elif parent_element_context is None and element.type in [CodeElementType.CLASS, CodeElementType.FUNCTION]:
                          possible_matches.append(element)
                          logger.debug(f"  -> Found potential top-level match (name only): {element.name} ({element.type.value})")


            if not possible_matches:
                logger.warning(f"_find_target_element: No element found at level {i} for name='{target_name}', type='{target_type}'.")
                return None # Nie znaleziono na tym poziomie, przerwij

            # Wybierz najlepszy z możliwych dopasowań
            if len(possible_matches) == 1:
                 found_in_level = possible_matches[0]
            else:
                 # Sortuj wg preferencji (Setter > Getter > Method > Class > Function) i linii
                 possible_matches.sort(key=lambda el: (
                      3 if el.type == CodeElementType.PROPERTY_SETTER else
                      2 if el.type == CodeElementType.PROPERTY_GETTER else
                      1 if el.type == CodeElementType.METHOD else
                      0, # Domyślny priorytet dla reszty (np. klasa, funkcja)
                      el.range.start_line if el.range else 0
                 ), reverse=True) # Najwyższy priorytet i linia jako pierwsi
                 found_in_level = possible_matches[0] # Wybierz najlepszy
                 logger.debug(f"_find_target_element: Multiple candidates found ({len(possible_matches)}). Selected best: {found_in_level.name} ({found_in_level.type.value})")


            # Jeśli to ostatni węzeł w XPath, znaleźliśmy cel
            if i == len(current_nodes) - 1:
                target_element = found_in_level
                break
            else:
                # Jeśli są dalsze węzły, ustawiamy kontekst wyszukiwania na dzieci znalezionego elementu
                parent_element_context = found_in_level # Zapamiętaj obecny element jako rodzica dla następnej iteracji
                current_search_context = found_in_level.children
                if not current_search_context:
                     logger.warning(f"_find_target_element: Element '{found_in_level.name}' found, but has no children to continue search.")
                     return None # Przerwij, jeśli nie ma dzieci do dalszego szukania


        if target_element:
             logger.debug(f"_find_target_element: Final target element found: {target_element.name} ({target_element.type.value})")
        else:
             logger.warning(f"_find_target_element: Could not find target element for XPath: {XPathParser.to_string(xpath_nodes)}")

        return target_element

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
        element_end_idx = element.range.end_line

        if element_start_idx < 0 or element_end_idx > len(code_lines) or element_start_idx >= element_end_idx:
             logger.error(f"Invalid line range for element '{element.name}': {element.range}")
             return None

        decorator_line_indices = set()
        definition_line_idx = -1
        first_body_line_idx = -1

        for child in element.children:
            if child.type == CodeElementType.DECORATOR and child.range:
                dec_start = child.range.start_line - 1
                dec_end = child.range.end_line - 1
                for i in range(dec_start, dec_end + 1):
                     if element_start_idx <= i < element_end_idx:
                          decorator_line_indices.add(i)
            elif child.type == CodeElementType.DECORATOR:
                 logger.warning(f"Decorator '{child.name}' for element '{element.name}' lacks range info.")

        for i in range(element_start_idx, element_end_idx):
             if i not in decorator_line_indices and code_lines[i].strip():
                  # Sprawdzamy czy to linia definicji dla Pythona
                  # Dodajemy Static Property jako możliwy początek elementu
                  if code_lines[i].strip().startswith(('def ', 'class ')) or element.type == CodeElementType.STATIC_PROPERTY:
                       definition_line_idx = i
                       # Dla static property cała linia to definicja i ciało
                       first_body_line_idx = i if element.type == CodeElementType.STATIC_PROPERTY else i + 1
                       break
                  else: # Traktuj pierwszą linię nie-dekoratora jako definicję
                      definition_line_idx = i
                      first_body_line_idx = i # Zakładamy, że ciało może zacząć się od tej samej linii (np. dla prostych przypisań)
                      break

        if definition_line_idx == -1: # Fallback
             # Jeśli element to tylko dekoratory (lub pusty), ustaw indeksy na początek/koniec
             is_only_decorators = all(idx in decorator_line_indices for idx in range(element_start_idx, element_end_idx) if code_lines[idx].strip())
             if is_only_decorators:
                  definition_line_idx = element_start_idx
                  first_body_line_idx = element_end_idx # Brak ciała
             else: # Domyślny fallback
                 definition_line_idx = element_start_idx
                 first_body_line_idx = element_end_idx
             logger.warning(f"Could not reliably find definition line for element '{element.name}' in range {element.range.start_line}-{element.range.end_line}. Using fallback indices.")


        start_idx_to_extract = -1
        end_idx_to_extract = -1

        if part_name == 'body':
            start_idx_to_extract = first_body_line_idx
            end_idx_to_extract = element_end_idx
            if start_idx_to_extract >= end_idx_to_extract:
                 logger.debug(f"Cannot extract '[body]' for '{element.name}', no body lines found or calculated range invalid.")
                 return ""

        elif part_name == 'def':
            start_idx_to_extract = definition_line_idx
            end_idx_to_extract = element_end_idx
            if start_idx_to_extract == -1 or start_idx_to_extract >= end_idx_to_extract:
                logger.warning(f"Cannot extract '[def]' for '{element.name}', definition line not found or range invalid.")
                return None # Zwracamy None jeśli nie można znaleźć definicji

        else: # Default or '[all]' -> return everything
            start_idx_to_extract = element_start_idx
            end_idx_to_extract = element_end_idx


        if 0 <= start_idx_to_extract < end_idx_to_extract <= len(code_lines):
             result_lines = code_lines[start_idx_to_extract:end_idx_to_extract]
             # Zwracamy linie z oryginalnymi wcięciami
             return '\n'.join(result_lines)
        elif start_idx_to_extract == end_idx_to_extract:
             return ""
        else:
             logger.error(f"Calculated invalid extraction range [{start_idx_to_extract}:{end_idx_to_extract}] for element '{element.name}'.")
             return None



    def get_text_by_xpath_internal(self, code: str, xpath_nodes: List['CodeElementXPathNode']) -> Optional[str]:
        """Internal implementation for getting text based on parsed XPath nodes for Python."""
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
        if xpath_nodes[-1].type == 'all':
             requested_part = None
             logger.debug(f"get_text_by_xpath_internal: Detected type '[all]', treating as no specific part requested.")

        logger.debug(f"get_text_by_xpath_internal: Requested part: '{requested_part}'")

        extracted_text = self._extract_part(code, target_element, requested_part)

        if extracted_text is None:
             logger.error(f"get_text_by_xpath_internal: Error extracting part '{requested_part}' for element '{target_element.name}'.")
             return None

        return extracted_text
