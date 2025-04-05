# codehem/core/extractors/template_method_extractor.py
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from tree_sitter import Node

from codehem.core.extractors.extraction_base import ExtractorHelpers, TemplateExtractor
from codehem.core.registry import extractor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

@extractor
class TemplateMethodExtractor(TemplateExtractor):
    """
    Skonsolidowany ekstraktor dla metod, getterów i setterów.
    Wersja 8.
    --- ZMIANY ---
    - Poprawiono _extract_all_decorators do lepszego rozpoznawania nazw (identifier, attribute, call).
    - Poprawiono _determine_element_type do prawidłowego rozpoznawania PROPERTY_GETTER i PROPERTY_SETTER.
    """
    ELEMENT_TYPE = CodeElementType.METHOD

    def __init__(self, language_code: str, language_type_descriptor: ElementTypeLanguageDescriptor):
        super().__init__(language_code, language_type_descriptor)
        if not self.descriptor or not (self.descriptor.tree_sitter_query or self.descriptor.regexp_pattern):
            logger.warning(f'Deskryptor dla {language_code}/{self.ELEMENT_TYPE.value} nie dostarczył wzorców.')

    def _get_actual_parent_class_name(self, node: Node, ast_handler: Any, code_bytes: bytes) -> Optional[str]:
        class_node_types = ['class_definition', 'class_declaration'] # Dodaj inne typy węzłów klas dla innych języków
        current_node = node.parent
        while current_node:
            if current_node.type in class_node_types:
                # Spróbuj znaleźć nazwę przez pole 'name'
                name_node = ast_handler.find_child_by_field_name(current_node, 'name')
                if name_node:
                    return ast_handler.get_node_text(name_node, code_bytes)
                else:
                    # Fallback: poszukaj pierwszego identyfikatora (przydatne np. w TS)
                    for child in current_node.children:
                        if child.type in ['identifier', 'type_identifier']:
                            return ast_handler.get_node_text(child, code_bytes)
                return None # Nie znaleziono nazwy w węźle klasy
            current_node = current_node.parent
        return None  # Nie znaleziono węzła klasy nadrzędnej

    def _extract_all_decorators(
        self, definition_node: Node, ast_handler: Any, code_bytes: bytes
    ) -> List[Dict[str, Any]]:
        """Wyodrębnia wszystkie dekoratory powiązane z danym węzłem definicji (Poprawiona wersja)."""
        decorators = []
        parent_node = definition_node.parent

        if parent_node and parent_node.type == "decorated_definition":
            for child_idx, child in enumerate(parent_node.children):
                if child.type == "decorator":
                    decorator_content = ast_handler.get_node_text(child, code_bytes)
                    decorator_name = None
                    # Nazwa dekoratora jest zwykle węzłem wewnątrz węzła 'decorator'
                    # Może to być 'identifier', 'attribute' lub 'call'
                    # Tree-sitter dla Pythona często opakowuje to w 'expression_statement'

                    actual_name_node = child.child(
                        0
                    )  # Potencjalny 'expression_statement' lub bezpośrednio nazwa
                    if (
                        actual_name_node
                        and actual_name_node.type == "expression_statement"
                        and actual_name_node.child_count > 0
                    ):
                        actual_name_node = actual_name_node.child(
                            0
                        )  # Przechodzimy do właściwego węzła
                    elif (
                        actual_name_node and actual_name_node.type == "@"
                    ):  # Czasem '@' jest osobnym węzłem
                        if child.child_count > 1:
                            actual_name_node = child.child(1)  # Bierzemy następny węzeł
                        else:
                            actual_name_node = None  # Nie ma nic po '@' ?

                    if actual_name_node:
                        node_type = actual_name_node.type
                        logger.debug(
                            f"    _extract_all_decorators: Analizowanie węzła nazwy typu '{node_type}' dla: {decorator_content}"
                        )

                        if node_type == "identifier":
                            decorator_name = ast_handler.get_node_text(
                                actual_name_node, code_bytes
                            )
                            logger.debug(
                                f"      -> Rozpoznano 'identifier': name='{decorator_name}'"
                            )

                        elif node_type == "attribute":
                            obj_node = ast_handler.find_child_by_field_name(
                                actual_name_node, "object"
                            )
                            attr_node = ast_handler.find_child_by_field_name(
                                actual_name_node, "attribute"
                            )
                            if (
                                obj_node
                                and attr_node
                                and obj_node.type == "identifier"
                                and attr_node.type == "identifier"
                            ):
                                obj_name = ast_handler.get_node_text(
                                    obj_node, code_bytes
                                )
                                attr_name = ast_handler.get_node_text(
                                    attr_node, code_bytes
                                )
                                decorator_name = f"{obj_name}.{attr_name}"
                                logger.debug(
                                    f"      -> Rozpoznano 'attribute': object='{obj_name}', attribute='{attr_name}' -> name='{decorator_name}'"
                                )
                            else:
                                logger.warning(
                                    f"      -> Niekompletny lub nieoczekiwany węzeł 'attribute': obj={obj_node.type if obj_node else 'None'}, attr={attr_node.type if attr_node else 'None'} w {decorator_content}"
                                )

                        elif node_type == "call":
                            func_node = ast_handler.find_child_by_field_name(
                                actual_name_node, "function"
                            )
                            if func_node:
                                if func_node.type == "identifier":
                                    decorator_name = ast_handler.get_node_text(
                                        func_node, code_bytes
                                    )
                                    logger.debug(
                                        f"      -> Rozpoznano 'call(identifier)': name='{decorator_name}'"
                                    )
                                elif func_node.type == "attribute":
                                    obj_node = ast_handler.find_child_by_field_name(
                                        func_node, "object"
                                    )
                                    attr_node = ast_handler.find_child_by_field_name(
                                        func_node, "attribute"
                                    )
                                    if (
                                        obj_node
                                        and attr_node
                                        and obj_node.type == "identifier"
                                        and attr_node.type == "identifier"
                                    ):
                                        obj_name = ast_handler.get_node_text(
                                            obj_node, code_bytes
                                        )
                                        attr_name = ast_handler.get_node_text(
                                            attr_node, code_bytes
                                        )
                                        decorator_name = f"{obj_name}.{attr_name}"
                                        logger.debug(
                                            f"      -> Rozpoznano 'call(attribute)': object='{obj_name}', attribute='{attr_name}' -> name='{decorator_name}'"
                                        )
                                    else:
                                        logger.warning(
                                            f"      -> Niekompletny 'attribute' w wywołaniu dekoratora: obj={obj_node.type if obj_node else 'None'}, attr={attr_node.type if attr_node else 'None'} w {decorator_content}"
                                        )
                                else:
                                    logger.warning(
                                        f"      -> Nieoczekiwany typ funkcji '{func_node.type}' w wywołaniu dekoratora: {decorator_content}"
                                    )
                            else:
                                logger.warning(
                                    f"      -> Brak węzła funkcji w wywołaniu dekoratora: {decorator_content}"
                                )
                        else:
                            logger.warning(
                                f"    _extract_all_decorators: Nieobsługiwany główny typ węzła nazwy dekoratora '{node_type}': {decorator_content}"
                            )

                    else:
                        logger.warning(
                            f"    _extract_all_decorators: Nie znaleziono węzła nazwy wewnątrz dekoratora: {decorator_content}"
                        )

                    if decorator_name is None:
                        # Zastosuj fallback tylko jeśli absolutnie nic nie znaleziono
                        decorator_name = decorator_content.lstrip("@").strip()
                        logger.warning(
                            f'    _extract_all_decorators: Użyto fallback dla nazwy dekoratora: "{decorator_name}" z {decorator_content}'
                        )

                    # Tworzenie słownika dla dekoratora
                    dec_range_dict = {
                        "start_line": child.start_point[0] + 1,
                        "start_column": child.start_point[1],
                        "end_line": child.end_point[0] + 1,
                        "end_column": child.end_point[1],
                    }
                    decorators.append(
                        {
                            "name": decorator_name,
                            "content": decorator_content,
                            "range": dec_range_dict,
                        }
                    )
                    logger.debug(
                        f"    _extract_all_decorators: Finalnie dodano dekorator [{child_idx}]: name='{decorator_name}', content='{decorator_content[:50]}...'"
                    ) # Skrócony content w logu

        return decorators


    def _determine_element_type(self, decorators: List[Dict[str, Any]], element_name: str) -> Tuple[CodeElementType, Optional[str]]:
        # ... (Implementacja z poprzedniej odpowiedzi, która używa poprawionych nazw) ...
        is_getter, is_setter, setter_prop_name = (False, False, None)
        logger.debug(f"  _determine_element_type: Sprawdzanie typu dla '{element_name}' na podstawie {len(decorators)} dekoratorów...")
        for idx, dec in enumerate(decorators):
            dec_name = dec.get('name') # Teraz powinno być poprawnie sparsowane
            logger.debug(f"    _determine_element_type: Sprawdzanie dekoratora [{idx}]: name='{dec_name}'")
            if dec_name == 'property':
                is_getter = True
                logger.debug(f'      -> Rozpoznano jako @property (potencjalny GETTER).')
            # Poprawione sprawdzanie settera
            if isinstance(dec_name, str) and dec_name.endswith('.setter'):
                 prop_name_candidate = dec_name[:-len('.setter')]
                 # Sprawdzamy, czy nazwa właściwości z dekoratora pasuje do nazwy metody
                 if prop_name_candidate == element_name:
                      is_setter = True
                      setter_prop_name = prop_name_candidate
                      logger.debug(f'      -> Rozpoznano jako {dec_name} (SETTER dla właściwości {setter_prop_name}).')
                      break # Setter ma pierwszeństwo

        final_type = CodeElementType.METHOD
        if is_setter:
            final_type = CodeElementType.PROPERTY_SETTER
        elif is_getter:
            final_type = CodeElementType.PROPERTY_GETTER
        logger.debug(f"  _determine_element_type: Finalna klasyfikacja dla '{element_name}' -> {final_type.value}")
        return (final_type, setter_prop_name)


    def _extract_common_info(self, definition_node: Node, ast_handler: Any, code_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Wyodrębnia wspólne informacje (nazwa, parametry, typ zwrotny, treść, zakres)."""
        info = {}
        name_node = ast_handler.find_child_by_field_name(definition_node, 'name')
        if not name_node:
            logger.warning(f"Węzeł definicji (type: {definition_node.type}, id: {definition_node.id}) nie ma pola 'name'.")
            return None

        info['name'] = ast_handler.get_node_text(name_node, code_bytes)
        # Używamy zaktualizowanej logiki z ExtractorHelpers
        info['parameters'] = ExtractorHelpers.extract_parameters(ast_handler, definition_node, code_bytes, is_self_or_this=True)
        info['return_info'] = ExtractorHelpers.extract_return_info(ast_handler, definition_node, code_bytes)

        # Zakres i treść powinny obejmować dekoratory, jeśli istnieją
        parent_node = definition_node.parent
        node_for_range_and_content = definition_node # Domyślnie sam węzeł definicji
        if parent_node and parent_node.type == 'decorated_definition':
            # Jeśli jest dekorowany, bierzemy cały węzeł 'decorated_definition'
            node_for_range_and_content = parent_node
            logger.debug(f"    _extract_common_info: Element '{info['name']}' jest dekorowany, użyto parent node dla zakresu/treści.")

        try:
            info['content'] = ast_handler.get_node_text(node_for_range_and_content, code_bytes)
            info['range'] = {
                'start': {
                    'line': node_for_range_and_content.start_point[0] + 1,
                    'column': node_for_range_and_content.start_point[1]
                },
                'end': {
                    'line': node_for_range_and_content.end_point[0] + 1,
                    'column': node_for_range_and_content.end_point[1]
                }
            }
            # Dodajemy też informację o początku samej definicji (bez dekoratorów), może być przydatne
            info['definition_start_line'] = definition_node.start_point[0] + 1
            info['definition_start_col'] = definition_node.start_point[1]
        except Exception as e:
            logger.error(f"Błąd podczas pobierania treści/zakresu dla node id {node_for_range_and_content.id} (name: {info.get('name', 'N/A')}): {e}", exc_info=True)
            return None

        return info


    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: Any, context: Dict[str, Any]) -> List[Dict]:
        """Przetwarza wyniki zapytania TreeSitter, identyfikując metody/gettery/settery."""
        potential_elements = []
        processed_definition_node_ids = set() # Aby uniknąć duplikatów

        logger.debug(f"_process_tree_sitter_results: Otrzymano {len(query_results)} wyników z zapytania TreeSitter.")

        for node, capture_name in query_results:
            definition_node = None

            # Znajdź właściwy węzeł definicji (np. function_definition)
            # Może to być sam węzeł, lub dziecko węzła 'decorated_definition'
            if node.type == 'function_definition':
                definition_node = node
            elif node.type == 'decorated_definition':
                def_child = ast_handler.find_child_by_field_name(node, 'definition')
                if def_child and def_child.type == 'function_definition':
                    definition_node = def_child
            elif capture_name in ['method_name', 'property_name', 'function_name']: # Rozszerzamy o inne możliwe nazwy capture
                # Szukamy nadrzędnej definicji funkcji/metody
                parent_func = ast_handler.find_parent_of_type(node, 'function_definition')
                if parent_func:
                    definition_node = parent_func

            # Jeśli znaleźliśmy węzeł definicji i jeszcze go nie przetwarzaliśmy
            if definition_node and definition_node.id not in processed_definition_node_ids:
                # Sprawdź, czy element należy do klasy
                class_name = self._get_actual_parent_class_name(definition_node, ast_handler, code_bytes)

                # Przetwarzamy tylko metody klasowe (w tym gettery/settery)
                # Funkcje poza klasami są obsługiwane przez FunctionExtractor
                if class_name:
                    logger.debug(f"  _process_tree_sitter_results: Przetwarzanie definicji (Node ID: {definition_node.id}) w klasie '{class_name}'.")
                    # Wyodrębnij wspólne informacje
                    common_info = self._extract_common_info(definition_node, ast_handler, code_bytes)

                    if common_info:
                        element_name = common_info['name']
                        # Wyodrębnij wszystkie dekoratory dla tej definicji
                        decorators = self._extract_all_decorators(definition_node, ast_handler, code_bytes)
                        # Określ typ (METHOD, GETTER, SETTER) na podstawie dekoratorów
                        element_type, setter_prop_name = self._determine_element_type(decorators, element_name)

                        # Zbuduj finalny słownik informacji o elemencie
                        element_info = {
                            'node_id': definition_node.id, # Tymczasowo, do deduplikacji
                            'type': element_type.value,
                            'name': element_name,
                            'content': common_info['content'],
                            'class_name': class_name,
                            'range': common_info['range'],
                            'decorators': decorators, # Przechowujemy info o dekoratorach
                            'parameters': common_info['parameters'],
                            'return_info': common_info['return_info'],
                            'definition_start_line': common_info['definition_start_line'], # Dodatkowe info
                            'definition_start_col': common_info['definition_start_col'],  # Dodatkowe info
                        }
                        # Jeśli to setter, dodaj informację o nazwie właściwości
                        if element_type == CodeElementType.PROPERTY_SETTER and setter_prop_name:
                           element_info['property_name'] = setter_prop_name

                        potential_elements.append(element_info)
                        processed_definition_node_ids.add(definition_node.id) # Oznacz jako przetworzony
                    else:
                        logger.warning(f'  _process_tree_sitter_results: Nie udało się wyodrębnić common_info dla node id {definition_node.id}.')
                # else: logger.debug(f"  _process_tree_sitter_results: Pominięto definicję (Node ID: {definition_node.id}), ponieważ nie jest w klasie.")
            # else: if definition_node: logger.debug(f"  _process_tree_sitter_results: Pominięto już przetworzony node id {definition_node.id}.")

        # Usuwamy tymczasowe 'node_id'
        final_results = []
        for elem in potential_elements:
            logger.debug(f"Przetworzono finalnie: {elem['class_name']}.{elem['name']} jako {elem['type']} (Start def: L{elem['definition_start_line']})")
            elem.pop('node_id', None) # Usuwamy node_id
            final_results.append(elem)

        logger.debug(f'Zakończono przetwarzanie TreeSitter. Zwrócono {len(final_results)} unikalnych elementów (metod/getterów/setterów).')
        return final_results


    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        """Przetwarza wyniki dopasowania regex (obecnie mniej priorytetowe)."""
        # Ta metoda jest mniej ważna, jeśli TreeSitter działa poprawnie.
        # W razie potrzeby można ją zaimplementować/rozbudować.
        logger.warning('Przetwarzanie regex w TemplateMethodExtractor wymaga weryfikacji/rozbudowy.')
        # Przykładowa, bardzo podstawowa implementacja:
        results = []
        class_name = context.get("class_name") if context else None
        # Zakładamy, że regex zwraca grupę z nazwą metody
        # Trzeba by dodać logikę rozpoznawania dekoratorów i typu (getter/setter)
        for match in matches:
             try:
                 name = match.group(1) # Zakładając, że grupa 1 to nazwa
                 content = match.group(0)
                 start_pos, end_pos = match.span()
                 start_line = code[:start_pos].count('\n') + 1
                 end_line = code[:end_pos].count('\n') + 1
                 # Uproszczone - brak analizy dekoratorów, parametrów, typu zwrotnego
                 results.append({
                     'type': CodeElementType.METHOD.value, # Domyślnie metoda
                     'name': name,
                     'content': content,
                     'class_name': class_name,
                     'range': {
                         'start': {'line': start_line, 'column': 0}, # Uproszczone kolumny
                         'end': {'line': end_line, 'column': 0}    # Uproszczone kolumny
                     },
                     'decorators': [],
                     'parameters': [],
                     'return_info': {},
                     'definition_start_line': start_line # Przybliżone
                 })
             except IndexError:
                 logger.error(f"Regex match nie zawierał oczekiwanej grupy dla nazwy: {match.group(0)}")
             except Exception as e:
                 logger.error(f"Błąd przetwarzania regex match: {e}", exc_info=True)
        return results

    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Wyodrębnia elementy, próbując TreeSitter, a potem ewentualnie Regex."""
        current_handler = handler or self.descriptor
        if not current_handler or not (current_handler.tree_sitter_query or current_handler.regexp_pattern):
            logger.error(f'Brak deskryptora lub wzorców dla {self.language_code}/{self.ELEMENT_TYPE.value}')
            return []

        elements = []
        tree_sitter_attempted = False
        tree_sitter_error = False

        # --- Próba z TreeSitter ---
        tree_sitter_query = current_handler.tree_sitter_query
        if tree_sitter_query:
            ast_handler = self._get_ast_handler()
            if ast_handler:
                tree_sitter_attempted = True
                try:
                    handler_type_name = current_handler.element_type.value if current_handler.element_type else 'unknown_handler'
                    logger.debug(f'Próba ekstrakcji TreeSitter dla {self.language_code} (handler: {handler_type_name}).')
                    root, code_bytes = ast_handler.parse(code)
                    query_results = ast_handler.execute_query(tree_sitter_query, root, code_bytes)
                    elements = self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
                except Exception as e:
                    logger.error(f'Błąd podczas ekstrakcji TreeSitter dla {self.language_code} ({handler_type_name}): {e}', exc_info=False) # Ustaw exc_info=True dla pełnego śladu
                    elements = []
                    tree_sitter_error = True # Zapisujemy informację o błędzie
            else:
                logger.warning(f'Brak AST Handler dla {self.language_code}. Nie można użyć TreeSitter.')
        else:
            logger.debug(f"Brak zapytania TreeSitter dla {self.language_code} (handler: {(current_handler.element_type.value if current_handler.element_type else 'unknown_handler')}).")

        # --- Fallback do Regex (jeśli TreeSitter nie był próbowany, zawiódł lub nie dał wyników LUB jeśli konfiguracja tego wymaga) ---
        # Decyzja o fallbacku może zależeć od konfiguracji, np. `config.get('extraction', 'fallback_to_regex', True)`
        # Tutaj uproszczona logika: fallback jeśli nie było próby TreeSitter lub jeśli TreeSitter zawiódł i jest wzorzec regex
        should_fallback_to_regex = (not tree_sitter_attempted or tree_sitter_error)

        regexp_pattern = current_handler.regexp_pattern
        if regexp_pattern and should_fallback_to_regex:
            logger.debug(f"Używanie Regex fallback dla {self.language_code} (handler: {(current_handler.element_type.value if current_handler.element_type else 'unknown_handler')}).")
            try:
                # Upewniamy się, że flagi są odpowiednie
                elements = self._process_regex_results(re.finditer(regexp_pattern, code, re.MULTILINE | re.DOTALL), code, context)
            except Exception as e:
                logger.error(f"Błąd podczas ekstrakcji Regex dla {self.language_code} (handler: {(current_handler.element_type.value if current_handler.element_type else 'unknown_handler')}): {e}", exc_info=False)
                elements = [] # Zwracamy pustą listę w razie błędu regex
        elif not regexp_pattern:
            logger.debug(f"Brak wzorca Regex dla {self.language_code} (handler: {(current_handler.element_type.value if current_handler.element_type else 'unknown_handler')}).")

        if not elements and tree_sitter_attempted and not tree_sitter_error:
            # Jeśli TreeSitter był próbowany, nie było błędu, ale nie znaleziono elementów
            logger.debug(f"Ekstrakcja TreeSitter dla {self.language_code} (handler: {(current_handler.element_type.value if current_handler.element_type else 'unknown_handler')}) nie zwróciła żadnych elementów.")
        elif not elements and regexp_pattern and should_fallback_to_regex:
             logger.debug(f"Ekstrakcja Regex dla {self.language_code} (handler: {(current_handler.element_type.value if current_handler.element_type else 'unknown_handler')}) nie zwróciła żadnych elementów.")


        return elements