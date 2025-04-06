"""
Main entry point for code extraction functionality.
Acts as a facade for the various extraction strategies.
"""
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

# Keep existing direct imports
from codehem.core.error_handling import handle_extraction_errors
from codehem.core.registry import registry
from codehem.languages import (
    get_language_service_for_code,
    get_language_service_for_file,
)

# Changed imports to be more specific and avoid circular dependency
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

# Function extract_range remains the same
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
    start_line = start.get('start_line', start.get('line', 0))
    end_line = end.get('end_line', end.get('line', 0))
    start_line = start_line if isinstance(start_line, int) else 0
    end_line = end_line if isinstance(end_line, int) else 0
    return (start_line, end_line)

# Function find_in_collection remains the same
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

        # Assign post-processor based on language
        if language_code.lower() == 'python':
            # Use local import to potentially help with import issues if needed, though unlikely here
            from codehem.core.post_processors.python_post_processor import (
                PythonExtractionPostProcessor,
            )
            self.post_processor = PythonExtractionPostProcessor()
        else:
            self.post_processor = None # No post-processor for other languages yet

    # Method _get_raw_extractor_results remains the same
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
            available = [k for k in registry.all_extractors.keys() if k.startswith(self.language_code + '/')]
            logger.debug(f'Available extractors for {self.language_code}: {available}')
            return []

        logger.debug(f"Calling {extractor_instance.__class__.__name__}.extract() for '{element_type}'")
        results = extractor_instance.extract(code, context=context)

        # Ensure results are a list of dicts
        if isinstance(results, dict):
            results = [results] # Wrap single dict in a list
        elif not isinstance(results, list):
            logger.error(f'Extractor {extractor_instance.__class__.__name__} returned unexpected type: {type(results)} instead of list or dict.')
            return []

        # Filter out non-dict items from the list
        valid_results = [item for item in results if isinstance(item, dict)]
        if len(valid_results) != len(results):
            invalid_count = len(results) - len(valid_results)
            logger.warning(f'{extractor_instance.__class__.__name__} returned {invalid_count} items that are not dictionaries.')

        return valid_results

    # Method find_element remains the same
    @handle_extraction_errors
    @handle_extraction_errors # Keep this decorator if it provides useful high-level handling
    def find_element(self, code: str, element_type: str, element_name: Optional[str]=None, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find a specific element in the code based on type, name, and parent.
        Returns line range (start_line, end_line) of the found element or (0, 0) if not found.
        [DEBUGGING: Removed internal broad try-except, relies on @handle_extraction_errors or lets fail]
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

        # Determine the primary type to extract (e.g., 'method' covers properties too initially)
        extraction_type = element_type
        is_member = element_type in [CodeElementType.METHOD.value, CodeElementType.PROPERTY.value, CodeElementType.PROPERTY_GETTER.value, CodeElementType.PROPERTY_SETTER.value, CodeElementType.STATIC_PROPERTY.value]

        # --- Start Removed Try ---
        # Use _get_raw_extractor_results which might raise errors now
        raw_elements = []
        if is_member:
            # Extract all potential member types
            raw_elements.extend(self._get_raw_extractor_results(code, CodeElementType.METHOD.value, context=None))
            # Include static properties if searching for general property or static property
            if element_type in [CodeElementType.PROPERTY.value, CodeElementType.STATIC_PROPERTY.value]:
                 raw_elements.extend(self._get_raw_extractor_results(code, CodeElementType.STATIC_PROPERTY.value, context=None))
        else:
            # Extract only the specific non-member type
            raw_elements = self._get_raw_extractor_results(code, extraction_type, context=None)

        if not raw_elements:
            logger.debug(f"  find_element: No raw elements found for extraction type '{extraction_type}' (or related member types).")
            return (0, 0)

        logger.debug(f"  find_element: Raw elements ({len(raw_elements)}) before filtering for '{element_name}': {[(e.get('name'), e.get('type'), e.get('class_name')) for e in raw_elements]}")

        matching_elements = []
        for element in raw_elements:
            if not isinstance(element, dict):
                continue
            current_element_type = element.get('type')
            current_element_name = element.get('name')
            # Determine the effective parent name *of the raw element*
            current_parent_name = element.get('class_name') # Assumes extractor provides this

            # Check type match (handle PROPERTY as a general case)
            type_match = current_element_type == element_type or \
                         (element_type == CodeElementType.PROPERTY.value and
                          current_element_type in [CodeElementType.PROPERTY_GETTER.value, CodeElementType.PROPERTY_SETTER.value, CodeElementType.STATIC_PROPERTY.value])

            # Check name match
            name_match = element_name is None or current_element_name == element_name

            # Check parent match
            parent_match = (not is_member and current_parent_name is None) or \
                           (is_member and parent_name == current_parent_name)

            if type_match and name_match and parent_match:
                matching_elements.append(element)

        logger.debug(f"  find_element: After filtering found {len(matching_elements)} matching elements for type='{element_type}', name='{element_name}', parent='{parent_name}'.")

        if not matching_elements:
            # Add debug for near misses
            if element_name:
                 all_with_name = [el for el in raw_elements if isinstance(el, dict) and el.get('name') == element_name]
                 if all_with_name:
                      logger.debug(f"      find_element: Found elements with name '{element_name}', but they don't match type/parent: {[(e.get('type'), e.get('class_name')) for e in all_with_name]}")
            return (0, 0)

        # Sort to prioritize more specific types (setter > getter > static > method)
        # and then by line number (preferring later definitions in case of duplicates)
        def sort_key(el):
            el_type = el.get('type')
            specificity = 0
            if el_type == CodeElementType.PROPERTY_SETTER.value: specificity = 4
            elif el_type == CodeElementType.PROPERTY_GETTER.value: specificity = 3
            elif el_type == CodeElementType.STATIC_PROPERTY.value: specificity = 2
            elif el_type == CodeElementType.METHOD.value: specificity = 1
            # Use definition_start_line if available, otherwise fallback to range start
            line = el.get('definition_start_line', el.get('range', {}).get('start', {}).get('line', 0))
            return (specificity, line)

        matching_elements.sort(key=sort_key, reverse=True) # Higher specificity first, later line first

        best_match = matching_elements[0]
        if len(matching_elements) > 1:
            logger.warning(f"  find_element: Found {len(matching_elements)} potential matches for '{element_name}'. Selected best match: {best_match.get('name')} (type: {best_match.get('type')})")

        logger.debug(f"  find_element: Selected match: {best_match.get('name')} (type: {best_match.get('type')}, class: {best_match.get('class_name')})")
        return extract_range(best_match)
        # --- End Removed Try ---
        # except Exception as e:
        #     logger.error(f'Error finding element ({self.element_type.value if self.element_type else "UnknownType"}, {element_name}, {parent_name}): {e}')
        #     return (0, 0)

    # Methods extract_functions, extract_classes, extract_methods, extract_imports, extract_any remain the same
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
        # This should fetch methods/getters/setters based on the TemplateMethodExtractor query
        all_members = self._get_raw_extractor_results(code, CodeElementType.METHOD.value)
        if not class_name:
            return all_members
        # Filter based on the 'class_name' field added by the extractor
        return [m for m in all_members if isinstance(m, dict) and m.get('class_name') == class_name]

    @handle_extraction_errors
    def extract_imports(self, code: str) -> List[Dict]:
        """
        Extract imports from the provided code.
        This method should return a list of *individual* imports or one collective element.
        """
        results = self._get_raw_extractor_results(code, CodeElementType.IMPORT.value)
        # Post-processor might combine these later, but raw result could be list or single dict
        return results

    @handle_extraction_errors
    def extract_any(self, code: str, element_type: str) -> List[Dict]:
        """Extract any code element from the provided code."""
        return self._get_raw_extractor_results(code, element_type)

    # Method _extract_file_raw remains the same (but uses updated extract_* methods)
    def _extract_file_raw(self, code: str) -> Dict[str, List[Dict]]:
        """
        Extract all code elements from the provided code.
        This is a private method that performs raw extraction.

        Args:
            code: Source code as string

        Returns:
            Dictionary with extracted elements categorized by type
        """
        logger.info(f'Starting raw extraction of all elements for {self.language_code}')
        results = {}

        results['imports'] = self.extract_imports(code) # Uses IMPORT extractor
        logger.debug(f"Raw extracted {len(results.get('imports', []))} import elements (may be individual or 1 collective).")

        results['functions'] = self.extract_functions(code) # Uses FUNCTION extractor
        logger.debug(f"Raw extracted {len(results.get('functions', []))} functions.")

        results['classes'] = self.extract_classes(code) # Uses CLASS extractor
        logger.debug(f"Raw extracted {len(results.get('classes', []))} classes.")

        # Fetch potential members (methods, getters, setters) using METHOD extractor
        all_members = self._get_raw_extractor_results(code, CodeElementType.METHOD.value)
        results['members'] = all_members
        logger.debug(f'Raw extracted {len(all_members)} potential class members (methods/getters/setters).')

        # Fetch static properties using STATIC_PROPERTY extractor
        static_props = self._get_raw_extractor_results(code, CodeElementType.STATIC_PROPERTY.value)
        results['static_properties'] = static_props
        logger.debug(f'Raw extracted {len(static_props)} static properties.')

        logger.info(f'Completed raw extraction for {self.language_code}.')
        return results

    # Method extract_all remains the same (but uses updated _extract_file_raw and post-processor)
    def extract_all(self, code: str) -> 'CodeElementsResult':
        """
        Extract all code elements and convert them to a structured CodeElementsResult.
        [DEBUGGING: Removed broad try-except, allows failure propagation]
        Args:
        code: Source code as string

        Returns:
        CodeElementsResult containing extracted elements
        """
        from codehem.models.code_element import CodeElementsResult, CodeElement # Import inside
        logger.info(f'Starting full extraction and post-processing for {self.language_code}')
        result = CodeElementsResult(elements=[])

        # --- Start Removed Try ---
        raw_elements = self._extract_file_raw(code)

        if not self.post_processor:
            # Log error but potentially return empty result instead of raising?
            # Or re-raise a specific configuration error?
            # For debugging, let it potentially fail later if post_processor is None.
            logger.error(f'No post-processor available for language {self.language_code}')
            # return result # Optionally return empty result gracefully
            # raise ConfigurationError(f'No post-processor for {self.language_code}') # Or raise

        # Allow exceptions in post-processing to propagate
        imports = self.post_processor.process_imports(raw_elements.get('imports', []))
        result.elements.extend(imports)

        functions = self.post_processor.process_functions(raw_elements.get('functions', []))
        result.elements.extend(functions)

        # Pass members (methods/getters/setters) and static props to class processor
        classes = self.post_processor.process_classes(
            raw_classes=raw_elements.get('classes', []),
            members=raw_elements.get('members', []),
            static_props=raw_elements.get('static_properties', [])
        )
        result.elements.extend(classes)

        # Sort final elements by starting line
        result.elements.sort(key=lambda el: el.range.start_line if el.range else float('inf'))

        # --- End Removed Try ---
        # except Exception as e:
        #     logger.error(f'Critical error in `extract_all` for language {self.language_code}: {e}', exc_info=True)
        #     # Return empty result on failure
        #     return CodeElementsResult(elements=[])

        logger.info(f'Completed full extraction for {self.language_code}. Top-level element count: {len(result.elements)}')
        return result

    # Method find_by_xpath uses the corrected approach (extract_all + filter)
    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        """
        Find an element's location using an XPath expression by running a full
        extraction and then filtering the results.
        [DEBUGGING: Removed broad try-except]

        Args:
        code: Source code as string
        xpath: XPath expression (e.g., 'ClassName.method_name',
        'ClassName[interface].method_name[property_getter]')

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        # Import locally to avoid potential circular dependencies at module level
        from codehem.models.code_element import CodeElementsResult, CodeElement

        logger.debug(f"Finding range by XPath: '{xpath}' using extract_all and filter.")
        # --- Start Removed Try ---
        # Allow exceptions from extract_all or filter to propagate
        elements_result: CodeElementsResult = self.extract_all(code)

        if not elements_result or not elements_result.elements:
            logger.warning(f"extract_all returned no elements for find_by_xpath('{xpath}').")
            return (0, 0)

        target_element: Optional[CodeElement] = elements_result.filter(xpath)

        if target_element and target_element.range:
            start_line = target_element.range.start_line
            end_line = target_element.range.end_line
            # Add basic validation for the range itself
            if isinstance(start_line, int) and isinstance(end_line, int) and start_line > 0 and end_line >= start_line:
                logger.debug(f"Found element via XPath '{xpath}' at lines {start_line}-{end_line}.")
                return (start_line, end_line)
            else:
                logger.warning(f"Found element via XPath '{xpath}' but range is invalid: {target_element.range}")
                return (0, 0)
        else:
            logger.warning(f"Element not found or has no range for XPath: '{xpath}'")
            return (0, 0)
        # --- End Removed Try ---
        # except Exception as e:
        #     logger.error(f"Error during find_by_xpath for '{xpath}': {e}", exc_info=True)
        #     return (0, 0)

    # Class methods from_file_path and from_raw_code remain the same
    @classmethod
    def from_file_path(cls, file_path: str) -> 'ExtractionService':
        """
        Create an extractor for a file based on its extension.
        Args:
            file_path: Path to the file

        Returns:
            ExtractionService instance

        Raises:
            ValueError: If file extension not supported
        """
        service = get_language_service_for_file(file_path)
        if not service:
            _, ext = os.path.splitext(file_path)
            raise ValueError(f'Unsupported file extension: {ext}')
        return cls(service.language_code)

    @classmethod
    def from_raw_code(cls, code: str, language_hints: List[str]=None) -> 'ExtractionService':
        """
        Create an extractor by attempting to detect the language from code.
        Args:
            code: Source code string
            language_hints: Optional list of language hints to try (Currently not implemented)

        Returns:
            ExtractionService instance

        Raises:
            ValueError: If language could not be detected
        """
        if language_hints:
            logger.warning('language_hints parameter in `from_raw_code` is not currently implemented.')

        service = get_language_service_for_code(code)
        if service:
            return cls(service.language_code)

        raise ValueError('Could not automatically detect code language. Please specify explicitly.')

    # Method get_descriptor remains the same
    def get_descriptor(self, element_type_descriptor: Union[str, CodeElementType]) -> Optional[Any]:
        """
        Get the appropriate descriptor for the given type and language.

        Args:
            element_type_descriptor: Element type or type name

        Returns:
            Element type descriptor or None
        """
        if not self.language_service:
            logger.error(f"Attempt to get descriptor without initialized language_service for '{self.language_code}'.")
            return None

        element_type_str = element_type_descriptor.value if isinstance(element_type_descriptor, CodeElementType) else str(element_type_descriptor)
        descriptor = self.language_service.get_element_descriptor(element_type_str)

        if not descriptor:
            logger.warning(f"No descriptor found for element type '{element_type_str}' in language '{self.language_code}'.")
        return descriptor