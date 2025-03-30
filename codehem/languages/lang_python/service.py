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
        # Lista powinna odzwierciedlać faktycznie obsługiwane typy przez ekstraktory i manipulatory
        return [
            CodeElementType.CLASS.value,
            CodeElementType.FUNCTION.value,
            CodeElementType.METHOD.value,
            CodeElementType.IMPORT.value,
            CodeElementType.DECORATOR.value, # Choć nie jest to element najwyższego poziomu
            # CodeElementType.PROPERTY.value, # To jest typ zbiorczy, nie bezpośrednio ekstrahowany
            CodeElementType.PROPERTY_GETTER.value,
            CodeElementType.PROPERTY_SETTER.value,
            CodeElementType.STATIC_PROPERTY.value,
            # Można dodać inne jeśli są obsługiwane, np. PARAMETER, RETURN_VALUE jako dzieci
        ]

    def detect_element_type(self, code: str) -> str:
        """Wykrywa typ elementu kodu Pythona (uproszczona detekcja)."""
        code_stripped = code.strip()
        # Sprawdź dekoratory przed definicjami
        if re.search(r'@\w+\.setter', code_stripped):
            return CodeElementType.PROPERTY_SETTER.value
        if re.search(r'@property', code_stripped):
             return CodeElementType.PROPERTY_GETTER.value
        # Sprawdź definicje
        if re.match(r'^\s*class\s+\w+', code_stripped):
            return CodeElementType.CLASS.value
        # Metoda (musi zawierać 'self' lub 'cls' jako pierwszy argument)
        if re.search(r'def\s+\w+\s*\(\s*(?:self|cls)\b', code_stripped):
            # Upewnijmy się, że to nie jest @property lub @*.setter (już sprawdzone)
             return CodeElementType.METHOD.value
        # Funkcja (nie zawiera 'self'/'cls' jako pierwszego argumentu)
        if re.match(r'^\s*def\s+\w+', code_stripped):
            return CodeElementType.FUNCTION.value
        if re.match(r'^(?:import|from)\s+\w+', code_stripped):
            return CodeElementType.IMPORT.value
        # Statyczna właściwość klasy (proste przypisanie na poziomie klasy)
        # To jest bardzo uproszczone, może wymagać kontekstu klasy
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*[:=]', code_stripped):
             # Może to być static property lub zmienna globalna. Trudne do rozróżnienia bez kontekstu.
             # Zakładamy, że jeśli jest wklejane jako element, to intencją jest static property
             return CodeElementType.STATIC_PROPERTY.value

        return CodeElementType.UNKNOWN.value

    # --- Metoda get_indentation (bez zmian) ---
    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    # --- Metody _extract_and_attach_decorators, _convert_to_code_element (usunięte/zintegrowane) ---
    # Logika dołączania dekoratorów została przeniesiona do ExtractionService._process_*

    def _find_target_element(self, elements_result: CodeElementsResult, xpath_nodes: List['CodeElementXPathNode']) -> Optional[CodeElement]:
        """Znajduje docelowy CodeElement na podstawie sparsowanego XPath."""
        if not xpath_nodes:
            return None

        target_node_info = xpath_nodes[-1]
        target_name = target_node_info.name
        target_type = target_node_info.type # Może być None

        parent_element = None
        # Jeśli XPath ma więcej niż jeden segment, znajdujemy rodzica
        if len(xpath_nodes) > 1:
            parent_xpath_str = XPathParser.to_string(xpath_nodes[:-1])
            # Używamy CodeHem.filter do znalezienia rodzica
            # (Zakładamy dostęp do instancji CodeHem lub jej statycznej metody filter)
            # W kontekście LanguageService może być potrzebne przekazanie elements_result
            from codehem import CodeHem # Unikaj importów wewnątrz metody, jeśli to możliwe
            parent_element = CodeHem.filter(elements_result, parent_xpath_str)
            if not parent_element:
                 logger.debug(f"_find_target_element: Nie znaleziono rodzica dla XPath: {parent_xpath_str}")
                 return None
            logger.debug(f"_find_target_element: Znaleziono rodzica: {parent_element.name} ({parent_element.type.value})")
            # Szukamy w dzieciach rodzica
            search_list = parent_element.children
        else:
            # Szukamy w elementach najwyższego poziomu
            search_list = elements_result.elements

        # --- Logika wyszukiwania celu ---
        matches = []
        for element in search_list:
            # Sprawdź dopasowanie nazwy
            name_match = (element.name == target_name)
            if not name_match: continue

            # Sprawdź dopasowanie typu (jeśli podano w XPath)
            type_match = (target_type is None) or (element.type.value == target_type)
            if not type_match: continue

            # Jeśli nazwa i typ (jeśli podany) pasują, dodaj do listy
            matches.append(element)

        if not matches:
            logger.debug(f"_find_target_element: Nie znaleziono bezpośredniego dopasowania dla '{target_name}' (typ: {target_type})")
             # --- Fallback dla XPath bez typu (np. Klasa.metoda) ---
             # Jeśli szukaliśmy bez typu, a element ma potencjalne gettery/settery
            if target_type is None and parent_element: # Sprawdzamy tylko wewnątrz klas
                 possible_matches = []
                 for element in parent_element.children:
                      if element.name == target_name and element.type in [CodeElementType.PROPERTY_SETTER, CodeElementType.PROPERTY_GETTER, CodeElementType.METHOD]:
                           possible_matches.append(element)

                 if possible_matches:
                      # Sortuj według preferencji: Setter > Getter > Method
                      # Zakładając, że ostatnia definicja ma większy start_line
                      possible_matches.sort(key=lambda el: (
                           2 if el.type == CodeElementType.PROPERTY_SETTER else
                           1 if el.type == CodeElementType.PROPERTY_GETTER else
                           0,
                           el.range.start_line if el.range else 0
                      ), reverse=True) # Najwyższy priorytet i linia na początku
                      logger.debug(f"_find_target_element: Znaleziono {len(possible_matches)} kandydatów (setter/getter/method) dla '{target_name}'. Wybrano: {possible_matches[0].type.value}")
                      return possible_matches[0] # Zwróć najlepszy

            return None # Nie znaleziono nic pasującego

        # Jeśli znaleziono jedno lub więcej dokładnych dopasowań
        # Zwracamy ostatni znaleziony (zgodnie z zasadą ostatniej definicji)
        matches.sort(key=lambda el: el.range.start_line if el.range else 0)
        logger.debug(
            f"_find_target_element: Znaleziono {len(matches)} dokładnych dopasowań dla '{target_name}' (typ: {target_type}). Wybrano ostatni."
        )
        return matches[-1]

    def _extract_part(
        self, code: str, element: CodeElement, part_name: Optional[str]
    ) -> Optional[str]:
        """
        Wyodrębnia określoną część elementu (def, body) lub całość,
        poprawnie obsługując wykluczanie dekoratorów.
        """
        if not element or not element.range:
            logger.warning(
                f"Próba wyodrębnienia części z elementu bez zakresu: {element.name if element else 'None'}"
            )
            return None

        code_lines = code.splitlines()
        # Zakres całego elementu (włącznie z dekoratorami), 0-based index
        element_start_idx = element.range.start_line - 1
        element_end_idx = (
            element.range.end_line
        )  # Indeks linii *po* ostatniej linii elementu

        if (
            element_start_idx < 0
            or element_end_idx > len(code_lines)
            or element_start_idx >= element_end_idx
        ):
            logger.error(
                f"Nieprawidłowy zakres linii dla elementu '{element.name}': {element.range}"
            )
            return None

        # --- Identyfikacja linii dekoratorów i definicji ---
        decorator_line_indices = set()  # Zbiór indeksów linii (0-based, względem początku pliku) zajętych przez dekoratory
        definition_line_idx = (
            -1
        )  # Indeks linii definicji (0-based, względem początku pliku)
        first_body_line_idx = (
            -1
        )  # Indeks pierwszej linii ciała (0-based, względem początku pliku)

        # Znajdź zakresy dekoratorów-dzieci
        for child in element.children:
            if child.type == CodeElementType.DECORATOR and child.range:
                dec_start = child.range.start_line - 1
                dec_end = child.range.end_line - 1  # Zakres dekoratora jest włącznie
                for i in range(dec_start, dec_end + 1):
                    if (
                        element_start_idx <= i < element_end_idx
                    ):  # Upewnij się, że linia jest w zakresie elementu
                        decorator_line_indices.add(i)
            elif child.type == CodeElementType.DECORATOR:
                logger.warning(
                    f"Dekorator '{child.name}' dla elementu '{element.name}' nie ma informacji o zakresie."
                )

        # Znajdź linię definicji (pierwsza linia niebędąca dekoratorem ani pusta)
        for i in range(element_start_idx, element_end_idx):
            if i not in decorator_line_indices and code_lines[i].strip():
                # Proste sprawdzenie dla Pythona
                if code_lines[i].strip().startswith(("def ", "class ")):
                    definition_line_idx = i
                    # Pierwsza linia ciała to następna linia po definicji
                    first_body_line_idx = i + 1
                    break
                else:
                    # Jeśli to nie definicja, a coś innego (np. static prop), traktuj to jako def i body
                    definition_line_idx = i
                    first_body_line_idx = i  # Traktujemy tę samą linię jako "ciało" dla prostych przypadków
                    break  # Znaleziono pierwszą linię kodu

        # Jeśli nie znaleziono definicji (np. pusty element?)
        if definition_line_idx == -1:
            definition_line_idx = element_start_idx  # Ustaw na początek
            first_body_line_idx = element_end_idx  # Ustaw na koniec (brak ciała)
            logger.warning(
                f"Nie znaleziono linii definicji dla elementu '{element.name}' w zakresie {element.range.start_line}-{element.range.end_line}."
            )

        # --- Wyodrębnianie na podstawie 'part_name' ---
        lines_to_include_indices = []

        if part_name == "body":
            # Linie od pierwszej linii ciała do końca elementu
            start_idx = first_body_line_idx
            end_idx = element_end_idx
            if start_idx < end_idx:  # Sprawdź czy jest co brać
                lines_to_include_indices = list(range(start_idx, end_idx))
            else:
                logger.warning(
                    f"Nie można wyodrębnić '[body]' dla '{element.name}', nie znaleziono początku ciała lub ciało jest puste."
                )

        elif part_name == "def":
            # Linie od definicji do końca elementu
            start_idx = definition_line_idx
            end_idx = element_end_idx
            if start_idx < end_idx:
                lines_to_include_indices = list(range(start_idx, end_idx))
            else:
                logger.warning(
                    f"Nie można wyodrębnić '[def]' dla '{element.name}', nie znaleziono linii definicji."
                )

        else:  # Domyślnie lub dla '[all]' zwracamy całość (łącznie z dekoratorami)
            lines_to_include_indices = list(range(element_start_idx, element_end_idx))

        # Filtrujemy linie, aby upewnić się, że są w zakresie kodu
        lines_to_include_indices = [
            i for i in lines_to_include_indices if 0 <= i < len(code_lines)
        ]

        # Składamy wynikowe linie
        result_lines = [code_lines[i] for i in lines_to_include_indices]

        # Normalizacja wcięć (usuwamy wspólne wcięcie z wynikowych linii)
        if result_lines:
            min_indent_len = float("inf")
            for line in result_lines:
                if line.strip():
                    indent_len = len(self.get_indentation(line))
                    min_indent_len = min(min_indent_len, indent_len)

            if min_indent_len == float("inf"):  # Jeśli same puste linie
                min_indent_len = 0

            if min_indent_len > 0:
                dedented_lines = []
                for line in result_lines:
                    # Sprawdzamy czy linia ma przynajmniej minimalne wcięcie
                    # Uważamy na puste linie - zachowujemy je
                    if not line.strip():
                        dedented_lines.append("")
                    elif len(self.get_indentation(line)) >= min_indent_len:
                        dedented_lines.append(line[min_indent_len:])
                    else:
                        # Jeśli linia ma mniejsze wcięcie niż minimalne (dziwne, ale możliwe), zachowaj jak jest
                        dedented_lines.append(line)
                return "\n".join(dedented_lines)
            else:
                # Brak wspólnego wcięcia do usunięcia
                return "\n".join(result_lines)
        else:
            return ""  # Pusty wynik

    def get_text_by_xpath_internal(
        self, code: str, xpath_nodes: List["CodeElementXPathNode"]
    ) -> Optional[str]:
        """
        Implementacja pobierania tekstu dla Pythona, uwzględniająca nowe zasady XPath.
        """
        logger.debug(
            f"get_text_by_xpath_internal: Rozpoczynanie dla XPath: {XPathParser.to_string(xpath_nodes)}"
        )
        if not xpath_nodes:
            return None

        try:
            elements_result = self.extract(code)
            logger.debug(
                f"get_text_by_xpath_internal: Ekstrakcja zakończona, {len(elements_result.elements)} elementów głównych."
            )
        except Exception as e:
            logger.error(
                f"Krytyczny błąd podczas ekstrakcji w get_text_by_xpath_internal: {e}",
                exc_info=True,
            )
            return None

        target_element = self._find_target_element(elements_result, xpath_nodes)

        if not target_element:
            logger.warning(
                f"get_text_by_xpath_internal: Nie znaleziono elementu dla XPath: {XPathParser.to_string(xpath_nodes)}"
            )
            return None

        logger.debug(
            f"get_text_by_xpath_internal: Znaleziono pasujący element: {target_element.name} ({target_element.type.value})"
        )

        requested_part = xpath_nodes[-1].part
        # Obsługa [all] - traktujemy jak brak 'part'
        if xpath_nodes[-1].type == "all":
            requested_part = None
            logger.debug(
                f"get_text_by_xpath_internal: Wykryto typ '[all]', traktowanie jak brak specyfikacji części."
            )

        logger.debug(f"get_text_by_xpath_internal: Żądana część: '{requested_part}'")

        extracted_text = self._extract_part(code, target_element, requested_part)

        if extracted_text is None:
            logger.error(
                f"get_text_by_xpath_internal: Błąd podczas wyodrębniania części '{requested_part}' dla elementu '{target_element.name}'."
            )
            # Można rozważyć zwrócenie pustego stringa zamiast None
            # return ""
            return None

        # logger.debug(f"get_text_by_xpath_internal: Zwracany tekst:\n---\n{extracted_text}\n---")
        return extracted_text