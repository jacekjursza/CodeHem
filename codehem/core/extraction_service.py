import logging
import os
# Use TYPE_CHECKING to avoid runtime circular imports for type hints
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

import rich

from codehem.core.error_handling import handle_extraction_errors
from codehem.core.registry import registry
from codehem.languages import get_language_service_for_code, get_language_service_for_file
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

# Helper function remains the same
def extract_range(element: dict) -> Tuple[int, int]:
    """
    Extract line range (start_line, end_line) from an element dictionary.
    Returns (0, 0) if the range data is invalid.
    """
    range_data = element.get('range', {})
    if not isinstance(range_data, dict):
        return (0, 0)
    start = range_data.get('start', {})
    end = range_data.get('end', {})
    if not isinstance(start, dict) or not isinstance(end, dict):
        return (0, 0)
    start_line = start.get('start_line', start.get('line'))
    end_line = end.get('end_line', end.get('line'))
    start_line = start_line if isinstance(start_line, int) else 0
    end_line = end_line if isinstance(end_line, int) else 0
    return (start_line, end_line)

# Helper function remains the same
def find_in_collection(collection: List[dict], element_name: str) -> Tuple[int, int]:
    """
    Find an element by name in a collection and return its line range.
    Returns (0, 0) if not found.
    """
    for element in collection:
        if isinstance(element, dict) and element.get('name') == element_name:
            return extract_range(element)
    return (0, 0)

class ExtractionService:
    """Main extractor class that delegates to specific extractors based on language."""

    def __init__(self, language_code: str):
        """
        Initialize the extraction service for a language.
        Args:
            language_code: The language code to extract from
        """
        self.language_code = language_code
        self.language_service = registry.get_language_service(language_code)
        if not self.language_service:
            raise ValueError(f"Failed to get language_service for '{language_code}'. Check if it's registered.")

        lang_config = registry.get_language_config(language_code)

        post_processor_class = None
        if lang_config:
            post_processor_class = lang_config.get('post_processor_class')

        if post_processor_class:
             try:
                 self.post_processor = post_processor_class()
                 logger.debug(f"Initialized post-processor {post_processor_class.__name__} for {language_code}")
             except Exception as e:
                 logger.error(f"Failed to initialize post-processor {post_processor_class.__name__} for {language_code}: {e}", exc_info=True)
                 self.post_processor = None
        else:
             logger.warning(f"No post-processor class configured for language {language_code}.")
             self.post_processor = None

    def _get_raw_extractor_results(self, code: str, element_type: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Get raw extraction results for a specific element type.
        Args:
            code: Source code as string
            element_type: Type of elements to extract
            context: Optional context for extraction

        Returns:
            List of extracted elements as dictionaries
        """
        if not self.language_service:
            logger.error(f"No language_service for '{self.language_code}' when trying to extract '{element_type}'.")
            return []
        extractor_instance = self.language_service.get_extractor(element_type)
        if not extractor_instance:
            logger.warning(f"No extractor found for '{element_type}' in language '{self.language_code}'.")
            available = [k for k in self.language_service.extractors.keys() if k.startswith(self.language_code + '/')]
            logger.debug(f'Available extractors for {self.language_code}: {available}')
            return []

        logger.debug(f"Calling {extractor_instance.__class__.__name__}.extract() for '{element_type}'")
        try:
            results = extractor_instance.extract(code, context=context)
        except Exception as e:
             logger.error(f"Error during {extractor_instance.__class__.__name__}.extract(): {e}", exc_info=True)
             results = []

        if isinstance(results, dict):
            results = [results]
        elif not isinstance(results, list):
            logger.error(f'Extractor {extractor_instance.__class__.__name__} returned unexpected type: {type(results)} instead of list or dict.')
            return []

        valid_results = [item for item in results if isinstance(item, dict)]
        if len(valid_results) != len(results):
            invalid_count = len(results) - len(valid_results)
            logger.warning(f'{extractor_instance.__class__.__name__} returned {invalid_count} items that are not dictionaries.')

        return valid_results

    @handle_extraction_errors
    def find_element(self, code: str, element_type: str, element_name: Optional[str]=None, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find a specific element in the code based on type, name, and parent.
        Returns line range (start_line, end_line) of the found element or (0, 0) if not found.
        Args:
        code: Source code as string
        element_type: Type of element to find (e.g., 'function', 'class', 'method')
        element_name: Optional name of the element to find
        parent_name: Optional name of the parent element (e.g., class name for methods)

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        logger.debug(f"==> find_element: type='{element_type}', name='{element_name}', parent='{parent_name}'")
        if not self.language_service:
            logger.error(f"No language_service for '{self.language_code}' in find_element.")
            return (0, 0)

        extraction_types_to_try = {element_type}
        is_member_search = element_type in [
            CodeElementType.METHOD.value,
            CodeElementType.PROPERTY.value,
            CodeElementType.PROPERTY_GETTER.value,
            CodeElementType.PROPERTY_SETTER.value,
            CodeElementType.STATIC_PROPERTY.value
        ]

        if element_type == CodeElementType.PROPERTY.value:
             extraction_types_to_try.update({
                 CodeElementType.METHOD.value,
                 CodeElementType.PROPERTY_GETTER.value,
                 CodeElementType.PROPERTY_SETTER.value,
                 CodeElementType.STATIC_PROPERTY.value
             })
        elif is_member_search:
             extraction_types_to_try.add(CodeElementType.METHOD.value)
             extraction_types_to_try.add(CodeElementType.STATIC_PROPERTY.value)

        raw_elements = []
        for ext_type in extraction_types_to_try:
            raw_elements.extend(self._get_raw_extractor_results(code, ext_type, context=None))

        if not raw_elements:
            logger.debug(f"  find_element: No raw elements found for extraction types '{extraction_types_to_try}'.")
            return (0, 0)

        logger.debug(f"  find_element: Raw elements ({len(raw_elements)}) before filtering for '{element_name}': {[(e.get('name'), e.get('type'), e.get('class_name')) for e in raw_elements]}")

        matching_elements = []
        for element in raw_elements:
            if not isinstance(element, dict): continue

            current_element_type = element.get('type')
            current_element_name = element.get('name')
            current_parent_name = element.get('class_name')

            type_match = (current_element_type == element_type) or \
                         (element_type == CodeElementType.PROPERTY.value and current_element_type in [
                             CodeElementType.PROPERTY_GETTER.value,
                             CodeElementType.PROPERTY_SETTER.value,
                             CodeElementType.STATIC_PROPERTY.value
                         ])
            name_match = (element_name is None) or (current_element_name == element_name)
            parent_match = (not is_member_search and current_parent_name is None) or \
                           (is_member_search and parent_name == current_parent_name)

            if type_match and name_match and parent_match:
                matching_elements.append(element)

        logger.debug(f"  find_element: After filtering found {len(matching_elements)} matching elements for type='{element_type}', name='{element_name}', parent='{parent_name}'.")

        if not matching_elements:
            if element_name:
                all_with_name = [el for el in raw_elements if isinstance(el, dict) and el.get('name') == element_name]
                if all_with_name:
                    logger.debug(f"      find_element: Found elements with name '{element_name}', but they don't match type/parent: {[(e.get('type'), e.get('class_name')) for e in all_with_name]}")
            return (0, 0)

        def sort_key(el):
            el_type = el.get('type')
            specificity = 0
            if el_type == CodeElementType.PROPERTY_SETTER.value: specificity = 4
            elif el_type == CodeElementType.PROPERTY_GETTER.value: specificity = 3
            elif el_type == CodeElementType.STATIC_PROPERTY.value: specificity = 2
            elif el_type == CodeElementType.METHOD.value: specificity = 1
            line = el.get('definition_start_line', el.get('range', {}).get('start', {}).get('line', 0))
            return (specificity, line)

        matching_elements.sort(key=sort_key, reverse=True)

        best_match = matching_elements[0]
        if len(matching_elements) > 1:
            logger.warning(f"  find_element: Found {len(matching_elements)} potential matches for '{element_name}'. Selected best match based on specificity/line: {best_match.get('name')} (type: {best_match.get('type')})")

        logger.debug(f"  find_element: Selected match: {best_match.get('name')} (type: {best_match.get('type')}, class: {best_match.get('class_name')})")
        return extract_range(best_match)

    @handle_extraction_errors
    def extract_functions(self, code: str) -> List[Dict]:
        """Extract functions from the provided code."""
        return self._get_raw_extractor_results(code, CodeElementType.FUNCTION.value)

    @handle_extraction_errors
    def extract_classes(self, code: str) -> List[Dict]:
        """Extract classes from the provided code."""
        return self._get_raw_extractor_results(code, CodeElementType.CLASS.value)

    @handle_extraction_errors
    def extract_methods(self, code: str, class_name: Optional[str]=None) -> List[Dict]:
        """
        Extract methods from the provided code, optionally filtering by class.
        Returns *all* member types (method, getter, setter) for the given class.
        """
        all_raw_members = []
        all_raw_members.extend(self._get_raw_extractor_results(code, CodeElementType.METHOD.value))
        all_raw_members.extend(self._get_raw_extractor_results(code, CodeElementType.PROPERTY_GETTER.value))
        all_raw_members.extend(self._get_raw_extractor_results(code, CodeElementType.PROPERTY_SETTER.value))

        if not class_name:
            return all_raw_members

        return [m for m in all_raw_members if isinstance(m, dict) and m.get('class_name') == class_name]

    @handle_extraction_errors
    def extract_imports(self, code: str) -> List[Dict]:
        """
        Extract imports from the provided code.
        """
        results = self._get_raw_extractor_results(code, CodeElementType.IMPORT.value)
        return results

    @handle_extraction_errors
    def extract_any(self, code: str, element_type: str) -> List[Dict]:
        """Extract any code element from the provided code."""
        return self._get_raw_extractor_results(code, element_type)

    def _extract_file_raw(self, code: str) -> Dict[str, List[Dict]]:
        """
        Extract all supported code elements from the provided code.
        Now includes PROPERTY and DECORATOR types.
        """
        logger.info(f'Starting raw extraction of all elements for {self.language_code}')
        results = {'imports': self.extract_imports(code)}
        # Extract imports
        logger.debug(f"Raw extracted {len(results.get('imports', []))} import elements.")
        # Extract standalone functions
        results['functions'] = self.extract_functions(code)
        logger.debug(f"Raw extracted {len(results.get('functions', []))} functions.")
        # Extract classes (and potentially interfaces depending on language service)
        results['classes'] = self.extract_classes(code)
        logger.debug(f"Raw extracted {len(results.get('classes', []))} classes.")
        # Extract members (methods, getters, setters)
        all_members = self.extract_methods(code, class_name=None)
        results['members'] = all_members
        logger.debug(f'Raw extracted {len(all_members)} potential class members (methods/getters/setters).')
        # Extract regular properties (fields) - ADDED
        props = self._get_raw_extractor_results(code, CodeElementType.PROPERTY.value)
        results['properties'] = props
        logger.debug(f'Raw extracted {len(props)} regular properties.')
        # Extract static properties (class variables)
        static_props = self._get_raw_extractor_results(code, CodeElementType.STATIC_PROPERTY.value)
        results['static_properties'] = static_props
        logger.debug(f'Raw extracted {len(static_props)} static properties.')
        # Extract decorators - ADDED
        decorators = self._get_raw_extractor_results(code, CodeElementType.DECORATOR.value)
        results['decorators'] = decorators
        logger.debug(f'Raw extracted {len(decorators)} decorators.')


        results['interfaces'] = self._get_raw_extractor_results(code, CodeElementType.INTERFACE.value)
        logger.debug(f"Raw extracted {len(results.get('interfaces', []))} interfaces.")
        results['enums'] = self._get_raw_extractor_results(code, CodeElementType.ENUM.value)
        logger.debug(f"Raw extracted {len(results.get('enums', []))} enums.")
        results['type_aliases'] = self._get_raw_extractor_results(code, CodeElementType.TYPE_ALIAS.value)
        logger.debug(f"Raw extracted {len(results.get('type_aliases', []))} type aliases.")
        results['namespaces'] = self._get_raw_extractor_results(code, CodeElementType.NAMESPACE.value)
        logger.debug(f"Raw extracted {len(results.get('namespaces', []))} namespaces.")

        logger.info(f'Completed raw extraction for {self.language_code}. Collected types: {list(results.keys())}')
        return results

    # *** CHANGE START ***
    # Updated type hint to use string literal
    def extract_all(self, code: str) -> 'CodeElementsResult':
        """
        Extract all code elements and convert them to a structured CodeElementsResult.
        Relies on the language-specific post-processor.
        Args:
        code: Source code as string

        Returns:
        CodeElementsResult containing extracted elements
        """
        from codehem.models.code_element import CodeElementsResult # Local import
        logger.info(f'ExtractionService: Starting full extraction and post-processing for {self.language_code}') # MODIFIED LOG LEVEL
        result = CodeElementsResult(elements=[])
        try:
            raw_elements = self._extract_file_raw(code)
            if not self.post_processor:
                logger.error(f'ExtractionService: No post-processor available for language {self.language_code}. Cannot structure results.')
                return result

            logger.debug(f"ExtractionService: Using post-processor: {self.post_processor.__class__.__name__}") # ADDED LOG

            # Ensure all_decorators are extracted if the post-processor needs them
            all_decorators_list = raw_elements.get('decorators', [])
            logger.debug(f"ExtractionService: Passing {len(all_decorators_list)} raw decorators to post-processor.") # ADDED LOG

            imports = self.post_processor.process_imports(raw_elements.get('imports', []))
            logger.debug(f"ExtractionService: Post-processor returned {len(imports)} import elements.") # ADDED LOG
            result.elements.extend(imports)

            functions = self.post_processor.process_functions(
                raw_functions=raw_elements.get('functions', []),
                all_decorators=all_decorators_list # Pass decorators
            )
            logger.debug(f"ExtractionService: Post-processor returned {len(functions)} function elements.") # ADDED LOG
            result.elements.extend(functions)

            # Pass all relevant raw data to process_classes
            classes = self.post_processor.process_classes(
                raw_classes=raw_elements.get('classes', []),
                members=raw_elements.get('members', []), # Includes methods, getters, setters
                static_props=raw_elements.get('static_properties', []),
                properties=raw_elements.get('properties', []), # Pass regular properties
                all_decorators=all_decorators_list # Pass decorators
            )
            logger.debug(f"ExtractionService: Post-processor returned {len(classes)} class/container elements.") # ADDED LOG
            result.elements.extend(classes)

            # Sort final top-level elements by start line
            result.elements.sort(key=lambda el: el.range.start_line if el.range else float('inf'))
            logger.info(f'ExtractionService: Completed full extraction for {self.language_code}. Top-level element count: {len(result.elements)}') # MODIFIED LOG LEVEL

        except Exception as e:
            logger.error(f'Error during extract_all for {self.language_code}: {e}', exc_info=True)
            # Return empty result on error, but ensure it's the correct type
            return CodeElementsResult(elements=[])

        # Final type check before returning
        if not isinstance(result, CodeElementsResult):
            logger.error(f'extract_all final result is not CodeElementsResult, but {type(result)}')
            return CodeElementsResult(elements=getattr(result, 'elements', []))

        # Log final elements for debugging
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Final Extracted Elements Structure (Top-Level):")
            for i, element in enumerate(result.elements):
                 children_summary = f", Children: {[(c.name, c.type.value) for c in element.children]}" if element.children else ""
                 logger.debug(f"  [{i}] Name: {element.name}, Type: {element.type.value}, Parent: {element.parent_name}, Range: {element.range.start_line if element.range else 'N/A'}{children_summary}")

        return result

    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        """
        Find an element's location using an XPath expression by running a full
        extraction and then filtering the results.
        """
        logger.debug(f"Finding range by XPath: '{xpath}' using extract_all and filter.")
        try:
            # *** CHANGE START ***
            # Use string hint for the type that was causing the cycle
            elements_result: 'CodeElementsResult' = self.extract_all(code)
            # *** CHANGE END ***

            if not elements_result or not elements_result.elements:
                logger.warning(f"extract_all returned no elements for find_by_xpath('{xpath}').")
                return (0, 0)

            # *** CHANGE START ***
            # Import locally if needed for filtering logic, or use string hint
            # from codehem.models.code_element import CodeElement # Example if needed locally
            target_element: Optional['CodeElement'] = elements_result.filter(xpath)
            # *** CHANGE END ***

            if target_element and target_element.range:
                start_line = target_element.range.start_line
                end_line = target_element.range.end_line
                if isinstance(start_line, int) and isinstance(end_line, int) and start_line > 0 and end_line >= start_line:
                    logger.debug(f"Found element via XPath '{xpath}' at lines {start_line}-{end_line}.")
                    return (start_line, end_line)
                else:
                    logger.warning(f"Found element via XPath '{xpath}' but range is invalid: {target_element.range}")
                    return (0, 0)
            else:
                logger.info(f"Element not found or has no range for XPath: '{xpath}'")
                return (0, 0)

        except Exception as e:
             logger.error(f"Error during find_by_xpath('{xpath}'): {e}", exc_info=True)
             return (0, 0)

    @classmethod
    def from_file_path(cls, file_path: str) -> 'ExtractionService':
        """ Create an extractor for a file based on its extension. """
        service = get_language_service_for_file(file_path)
        if not service:
            _, ext = os.path.splitext(file_path)
            raise ValueError(f'Unsupported file extension: {ext}')
        return cls(service.language_code)

    @classmethod
    def from_raw_code(cls, code: str, language_hints: List[str]=None) -> 'ExtractionService':
        """ Create an extractor by attempting to detect the language from code. """
        if language_hints:
            logger.warning('language_hints parameter in `from_raw_code` is not currently implemented.')

        service = get_language_service_for_code(code)
        if service:
            return cls(service.language_code)

        raise ValueError('Could not automatically detect code language. Please specify explicitly.')

    def get_descriptor(self, element_type_descriptor: Union[str, CodeElementType]) -> Optional[Any]:
        """ Get the appropriate descriptor for the given type and language. """
        if not self.language_service:
            logger.error(f"Attempt to get descriptor without initialized language_service for '{self.language_code}'.")
            return None

        element_type_str = element_type_descriptor.value if isinstance(element_type_descriptor, CodeElementType) else str(element_type_descriptor)
        descriptor = self.language_service.get_element_descriptor(element_type_str)
        if not descriptor:
            logger.warning(f"No descriptor found for element type '{element_type_str}' in language '{self.language_code}'.")
        return descriptor