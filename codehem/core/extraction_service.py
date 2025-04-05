"""
Main entry point for code extraction functionality.
Acts as a facade for the various extraction strategies.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from copy import deepcopy
import rich
from pydantic import ValidationError
from codehem import CodeElementType, CodeElementXPathNode
from codehem.core.engine.xpath_parser import XPathParser
from codehem.core.error_handling import handle_extraction_errors
from codehem.core.registry import registry
from codehem.languages import (
    get_language_service_for_code,
    get_language_service_for_file,
)
from codehem.models.code_element import CodeElement, CodeElementsResult
from codehem.models.range import CodeRange

logger = logging.getLogger(__name__)


def extract_range(element: dict) -> Tuple[int, int]:
    """
    Extract line range (start_line, end_line) from an element dictionary.
    Returns (0, 0) if the range data is invalid.
    """
    range_data = element.get("range", {})
    if not isinstance(range_data, dict):
        return (0, 0)
    start = range_data.get("start", {})
    end = range_data.get("end", {})
    if not isinstance(start, dict) or not isinstance(end, dict):
        return (0, 0)
    start_line = start.get("start_line", start.get("line", 0))
    end_line = end.get("end_line", end.get("line", 0))
    start_line = start_line if isinstance(start_line, int) else 0
    end_line = end_line if isinstance(end_line, int) else 0
    # Ensure we return 1-based indices if input is 1-based
    return (start_line, end_line)


def find_in_collection(collection: List[dict], element_name: str) -> Tuple[int, int]:
    """
    Find an element by name in a collection and return its line range.
    Returns (0, 0) if not found.
    """
    for element in collection:
        if isinstance(element, dict) and element.get("name") == element_name:
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
            # More informative error message
            raise ValueError(
                f"Failed to get language_service for '{language_code}'. Check if it's registered."
            )

        # Initialize language-specific post-processor
        if language_code.lower() == "python":
            from codehem.core.post_processors.python_post_processor import PythonExtractionPostProcessor
            self.post_processor = PythonExtractionPostProcessor()
        else:
            self.post_processor = None  # Or raise error / fallback

    def _get_raw_extractor_results(
        self, code: str, element_type: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
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
            logger.error(
                f"No language_service for '{self.language_code}' when trying to extract '{element_type}'."
            )
            return []

        extractor_instance = self.language_service.get_extractor(element_type)
        if not extractor_instance:
            logger.warning(
                f"No extractor found for '{element_type}' in language '{self.language_code}'."
            )
            available = [
                k
                for k in registry.all_extractors.keys()
                if k.startswith(self.language_code + "/")
            ]
            logger.debug(f"Available extractors for {self.language_code}: {available}")
            return []

        logger.debug(
            f"Calling {extractor_instance.__class__.__name__}.extract() for '{element_type}'"
        )
        results = extractor_instance.extract(code, context=context)

        # Handle cases when extractor returns a single dict instead of a list
        if isinstance(results, dict):
            results = [results]
        elif not isinstance(results, list):
            logger.error(
                f"Extractor {extractor_instance.__class__.__name__} returned unexpected type: {type(results)} instead of list or dict."
            )
            return []

        # Validate that list items are dictionaries
        valid_results = [item for item in results if isinstance(item, dict)]
        if len(valid_results) != len(results):
            invalid_count = len(results) - len(valid_results)
            logger.warning(
                f"{extractor_instance.__class__.__name__} returned {invalid_count} items that are not dictionaries."
            )

        return valid_results

    @handle_extraction_errors
    def find_element(
        self,
        code: str,
        element_type: str,
        element_name: Optional[str] = None,
        parent_name: Optional[str] = None,
    ) -> Tuple[int, int]:
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
        logger.debug(
            f"==> find_element: type='{element_type}', name='{element_name}', parent='{parent_name}'"
        )

        if not self.language_service:
            logger.error(
                f"No language_service for '{self.language_code}' in find_element."
            )
            return (0, 0)

        # Normalize extraction type - for methods and properties use 'method' extractor
        # and then filter by specific type (METHOD, PROPERTY_GETTER, PROPERTY_SETTER)
        extraction_type = element_type
        is_member = element_type in [
            CodeElementType.METHOD.value,
            CodeElementType.PROPERTY.value,  # 'property' as a collective query
            CodeElementType.PROPERTY_GETTER.value,
            CodeElementType.PROPERTY_SETTER.value,
            CodeElementType.STATIC_PROPERTY.value,
        ]

        raw_elements = []
        if is_member:
            # Get all potential methods/properties
            raw_elements.extend(
                self._get_raw_extractor_results(
                    code, CodeElementType.METHOD.value, context=None
                )
            )
            # Also get static properties if looking for them or generic properties
            if element_type in [
                CodeElementType.PROPERTY.value,
                CodeElementType.STATIC_PROPERTY.value,
            ]:
                raw_elements.extend(
                    self._get_raw_extractor_results(
                        code, CodeElementType.STATIC_PROPERTY.value, context=None
                    )
                )
        else:
            # For other types (class, function, import) use their specific extractors
            raw_elements = self._get_raw_extractor_results(
                code, extraction_type, context=None
            )

        if not raw_elements:
            logger.debug(
                f"  find_element: No raw elements of type '{extraction_type}' (or related)."
            )
            return (0, 0)

        logger.debug(
            f"  find_element: Raw elements ({len(raw_elements)}) before filtering for '{element_name}': {[(e.get('name'), e.get('type'), e.get('class_name')) for e in raw_elements]}"
        )

        matching_elements = []
        for element in raw_elements:
            if not isinstance(element, dict):
                continue

            current_element_type = element.get("type")
            current_element_name = element.get("name")
            # For class members, check 'class_name', for others (functions, classes) parent should be None
            current_parent_name = element.get("class_name") if is_member else None

            type_match = False
            # Handle collective 'property' type
            if element_type == CodeElementType.PROPERTY.value:
                if current_element_type in [
                    CodeElementType.PROPERTY_GETTER.value,
                    CodeElementType.PROPERTY_SETTER.value,
                    CodeElementType.STATIC_PROPERTY.value,
                ]:
                    type_match = True
            else:
                # Exact type matching
                type_match = current_element_type == element_type

            name_match = element_name is None or current_element_name == element_name
            # Compare parent_name only if expected (for class members)
            parent_match = parent_name == current_parent_name

            if type_match and name_match and parent_match:
                matching_elements.append(element)

        logger.debug(
            f"  find_element: After filtering found {len(matching_elements)} matching elements for type='{element_type}', name='{element_name}', parent='{parent_name}'."
        )

        if not matching_elements:
            # Helpful logging if nothing matches
            if element_name:
                all_with_name = [
                    el
                    for el in raw_elements
                    if isinstance(el, dict) and el.get("name") == element_name
                ]
                if all_with_name:
                    logger.debug(
                        f"      find_element: Found elements with name '{element_name}', but they don't match type/parent: {[(e.get('type'), e.get('class_name')) for e in all_with_name]}"
                    )
            return (0, 0)

        # Select the "best" match
        # For properties (getter/setter) prefer the last definition (setter > getter)
        # For other types usually first found (or last, if duplicate) is fine
        if element_type in [
            CodeElementType.PROPERTY.value,
            CodeElementType.PROPERTY_GETTER.value,
            CodeElementType.PROPERTY_SETTER.value,
        ]:
            # Sort by definition line to get the last one
            matching_elements.sort(
                key=lambda el: el.get(
                    "definition_start_line",
                    el.get("range", {}).get("start", {}).get("line", 0),
                )
            )
            # Select the last matching (Python semantics - last definition wins)
            best_match = matching_elements[-1]
        elif len(matching_elements) > 1:
            # If more than one matching element (e.g. duplicated method), take the last one
            matching_elements.sort(
                key=lambda el: el.get(
                    "definition_start_line",
                    el.get("range", {}).get("start", {}).get("line", 0),
                )
            )
            best_match = matching_elements[-1]
            logger.warning(
                f"  find_element: Found {len(matching_elements)} matching elements for '{element_name}'. Selected the last defined one."
            )
        else:
            best_match = matching_elements[0]

        logger.debug(
            f"  find_element: Selected match: {best_match.get('name')} (type: {best_match.get('type')}, class: {best_match.get('class_name')})"
        )
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
    def extract_methods(
        self, code: str, class_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Extract methods from the provided code, optionally filtering by class.
        Returns *all* member types (method, getter, setter) for the given class.
        """
        all_members = self._get_raw_extractor_results(
            code, CodeElementType.METHOD.value
        )
        if not class_name:
            return all_members  # Return all if no class specified
        return [
            m
            for m in all_members
            if isinstance(m, dict) and m.get("class_name") == class_name
        ]

    @handle_extraction_errors
    def extract_imports(self, code: str) -> List[Dict]:
        """
        Extract imports from the provided code.
        This method should return a list of *individual* imports or one collective element.
        """
        results = self._get_raw_extractor_results(code, CodeElementType.IMPORT.value)
        # If ImportExtractor returned one collective element, return it in a list
        if len(results) == 1 and results[0].get("name") == "imports":
            return results
        # If it returned a list of individual imports (which shouldn't happen with current ImportExtractor),
        # we could combine them here, but for now just return what the extractor gave us
        return results

    @handle_extraction_errors
    def extract_any(self, code: str, element_type: str) -> List[Dict]:
        """Extract any code element from the provided code."""
        return self._get_raw_extractor_results(code, element_type)

    def _extract_file_raw(self, code: str) -> Dict[str, List[Dict]]:
        """
        Extract all code elements from the provided code.
        This is a private method that performs raw extraction.

        Args:
            code: Source code as string

        Returns:
            Dictionary with extracted elements categorized by type
        """
        logger.info(f"Starting extraction of all elements for {self.language_code}")
        results = {}

        results["imports"] = self.extract_imports(
            code
        )  # Uses corrected extract_imports
        logger.debug(
            f"Extracted {len(results.get('imports', []))} import elements (may be 1 collective)."
        )

        results["functions"] = self.extract_functions(code)
        logger.debug(f"Extracted {len(results.get('functions', []))} functions.")

        results["classes"] = self.extract_classes(code)
        logger.debug(f"Extracted {len(results.get('classes', []))} classes.")

        # Get *all* potential methods/getters/setters
        all_class_members = self._get_raw_extractor_results(
            code, CodeElementType.METHOD.value
        )
        results["members"] = all_class_members
        logger.debug(
            f"Extracted {len(all_class_members)} potential class members (methods/getters/setters)."
        )

        # Get static properties
        static_props = self._get_raw_extractor_results(
            code, CodeElementType.STATIC_PROPERTY.value
        )
        results["static_properties"] = static_props
        logger.debug(f"Extracted {len(static_props)} static properties.")

        logger.info(f"Completed raw extraction for {self.language_code}.")
        return results

    def _process_import_element(
        self, import_data_list: List[Dict]
    ) -> Optional[CodeElement]:
        """
        Process import data into a CodeElement.

        Args:
            import_data_list: Raw import data list

        Returns:
            Import CodeElement or None
        """
        if not import_data_list:
            return None

        # If we received one collective 'imports' element
        if len(import_data_list) == 1 and import_data_list[0].get("name") == "imports":
            raw_element = import_data_list[0]
            range_data = raw_element.get("range")
            code_range = None
            if range_data:
                code_range = CodeRange(
                    start_line=range_data.get("start", {}).get("line", 1),
                    start_column=range_data.get("start", {}).get("column", 0),
                    end_line=range_data.get("end", {}).get("line", 1),
                    end_column=range_data.get("end", {}).get("column", 0),
                )
            return CodeElement(
                type=CodeElementType.IMPORT,
                name="imports",
                content=raw_element.get("content", ""),
                range=code_range,
                # Store original list as additional_data
                additional_data={"imports_list": raw_element.get("imports", [])},
            )
        else:
            # If (unexpectedly) we got a list of individual imports
            logger.warning(
                "Received a list of individual imports instead of expected collective element."
            )
            # Could implement combining logic here, but for now return None
            return None

    def _process_decorators(self, element_data: Dict) -> List[CodeElement]:
        """
        Create CodeElement list for decorators.

        Args:
            element_data: Raw element data containing decorators

        Returns:
            List of decorator CodeElements
        """
        decorator_elements = []
        decorators_raw = element_data.get("decorators", [])
        parent_name = element_data.get("name")  # Function/method/class name
        parent_class = element_data.get("class_name")
        full_parent_name = (
            f"{parent_class}.{parent_name}" if parent_class else parent_name
        )

        for dec_data in decorators_raw:
            if not isinstance(dec_data, dict):
                logger.warning(f"Skipping invalid decorator data format: {dec_data}")
                continue

            name = dec_data.get("name")
            content = dec_data.get("content")
            range_data = dec_data.get("range")

            if name and content:
                decorator_range: Optional[CodeRange] = None
                if isinstance(range_data, dict):
                    try:
                        # Assume range from extractor is 1-based
                        decorator_range = CodeRange(
                            start_line=range_data.get(
                                "start_line", range_data.get("start", {}).get("line", 1)
                            ),
                            start_column=range_data.get(
                                "start_column",
                                range_data.get("start", {}).get("column", 0),
                            ),
                            end_line=range_data.get(
                                "end_line", range_data.get("end", {}).get("line", 1)
                            ),
                            end_column=range_data.get(
                                "end_column", range_data.get("end", {}).get("column", 0)
                            ),
                        )
                    except (ValidationError, KeyError, Exception) as e:
                        logger.warning(
                            f"Error creating CodeRange for decorator '{name}': {e}. Range data: {range_data}"
                        )
                else:
                    logger.warning(
                        f"Invalid range format for decorator '{name}': {type(range_data)}"
                    )

                decorator_elements.append(
                    CodeElement(
                        type=CodeElementType.DECORATOR,
                        name=name,
                        content=content,
                        range=decorator_range,
                        parent_name=full_parent_name,  # Set parent
                    )
                )
            else:
                logger.warning(
                    f"Skipping decorator without name or content: {dec_data}"
                )

        return decorator_elements

    def _process_function_element(self, function_data: Dict) -> CodeElement:
        """
        Process raw function data into a CodeElement with children.

        Args:
            function_data: Raw function data

        Returns:
            Function CodeElement with children
        """
        func_name = function_data.get("name", "unknown_func")
        logger.debug(f"Processing function: {func_name}")

        # Ensure correct type
        function_data["type"] = CodeElementType.FUNCTION.value
        func_element = CodeElement.from_dict(function_data)
        func_element.parent_name = None  # Global functions have no class parent

        # Process and add children
        func_element.children.extend(
            self._process_decorators(function_data)
        )  # Add decorators
        func_element.children.extend(
            self._process_parameters(func_element, function_data.get("parameters", []))
        )

        return_element = self._process_return_value(
            func_element, function_data.get("return_info", {})
        )
        if return_element:
            func_element.children.append(return_element)

        return func_element

    def _process_method_element(
        self, method_data: Dict, parent_class_element: CodeElement
    ) -> CodeElement:
        """
        Process raw method/property data into a CodeElement with children.

        Args:
            method_data: Raw method/property data
            parent_class_element: Parent class CodeElement

        Returns:
            Method/property CodeElement with children
        """
        element_name = method_data.get("name", "unknown_member")
        parent_name = parent_class_element.name
        logger.debug(
            f"Processing class member: {element_name} (raw type: {method_data.get('type')}) in class {parent_name}"
        )

        # Type is already determined by TemplateMethodExtractor (METHOD, PROPERTY_GETTER, PROPERTY_SETTER)
        element_type_str = method_data.get("type")
        try:
            # Validate type
            element_type_enum = CodeElementType(element_type_str)
        except ValueError:
            logger.warning(
                f"Received invalid type '{element_type_str}' for member '{element_name}' in class '{parent_name}'. Setting to UNKNOWN."
            )
            method_data["type"] = CodeElementType.UNKNOWN.value
            element_type_enum = CodeElementType.UNKNOWN

        element = CodeElement.from_dict(method_data)
        element.parent_name = parent_name  # Set parent

        # Process and add children
        element.children.extend(self._process_decorators(method_data))  # Add decorators
        element.children.extend(
            self._process_parameters(element, method_data.get("parameters", []))
        )

        return_element = self._process_return_value(
            element, method_data.get("return_info", {})
        )
        if return_element:
            element.children.append(return_element)

        return element

    def _process_static_property(
        self, prop_data: Dict, parent_class_element: CodeElement
    ) -> CodeElement:
        """
        Process raw static property data.

        Args:
            prop_data: Raw static property data
            parent_class_element: Parent class CodeElement

        Returns:
            Static property CodeElement
        """
        prop_name = prop_data.get("name", "unknown_static")
        parent_name = parent_class_element.name
        logger.debug(f"Processing static property: {prop_name} in class {parent_name}")

        # Ensure correct type
        prop_data["type"] = CodeElementType.STATIC_PROPERTY.value
        element = CodeElement.from_dict(prop_data)
        element.parent_name = parent_name

        # Static properties typically don't have parameters, return types, or decorators
        # Could add value_type extraction if the extractor supports it
        element.value_type = prop_data.get("value_type")  # Pass type if present

        return element

    def _process_class_element(
        self, class_data: Dict, all_members: List[Dict], all_static_props: List[Dict]
    ) -> CodeElement:
        """
        Process raw class data, finding and processing its members.

        Args:
            class_data: Raw class data
            all_members: All potential class members (methods/properties)
            all_static_props: All potential static properties

        Returns:
            Class CodeElement with processed members
        """
        class_name = class_data.get("name")
        logger.debug(f"Processing class: {class_name}")

        if not class_name:
            logger.error(f"Found class definition without a name! Data: {class_data}")
            # Return empty element to avoid error, but mark the problem
            return CodeElement(
                type=CodeElementType.CLASS,
                name="_ERROR_NO_CLASS_NAME_",
                content=class_data.get("content", ""),
            )

        # Ensure correct type
        class_data["type"] = CodeElementType.CLASS.value
        class_element = CodeElement.from_dict(class_data)

        # Add class decorators
        class_element.children.extend(self._process_decorators(class_data))

        # Filter members (methods/getters/setters) and static properties for this specific class
        members_for_this_class_raw = [
            m
            for m in all_members
            if isinstance(m, dict) and m.get("class_name") == class_name
        ]
        static_props_for_this_class_raw = [
            p
            for p in all_static_props
            if isinstance(p, dict) and p.get("class_name") == class_name
        ]

        logger.debug(
            f"Found {len(members_for_this_class_raw)} potential members (methods/getters/setters) for class {class_name}."
        )
        logger.debug(
            f"Found {len(static_props_for_this_class_raw)} potential static properties for class {class_name}."
        )

        # Process and add members, handling duplicates of the same TYPE
        processed_members: Dict[Tuple[str, str], CodeElement] = {}  # Key: (type, name)

        # Sort raw members by start line so the last definition is processed last
        members_for_this_class_raw.sort(
            key=lambda m: m.get(
                "definition_start_line",
                m.get("range", {}).get("start", {}).get("line", 0),
            )
        )

        for member_data in members_for_this_class_raw:
            if not isinstance(member_data, dict):
                continue

            try:
                processed_member = self._process_method_element(
                    member_data, class_element
                )
                # Uniqueness key is (type, name)
                member_key = (processed_member.type.value, processed_member.name)

                if member_key in processed_members:
                    logger.warning(
                        f"Overwriting previously processed member with key {member_key} in class {class_name} (per last definition rule)."
                    )

                processed_members[member_key] = processed_member

            except Exception as e:
                logger.error(
                    f"Error processing member {member_data.get('name', '???')} for class {class_name}: {e}",
                    exc_info=True,
                )

        # Add processed members to class children
        class_element.children.extend(list(processed_members.values()))

        # Process and add static properties
        processed_static_props: Dict[str, CodeElement] = {}  # Key: name

        static_props_for_this_class_raw.sort(
            key=lambda p: p.get("range", {}).get("start", {}).get("line", 0)
        )

        for prop_data in static_props_for_this_class_raw:
            if not isinstance(prop_data, dict):
                continue

            try:
                processed_prop = self._process_static_property(prop_data, class_element)
                prop_key = processed_prop.name

                if prop_key in processed_static_props:
                    logger.warning(
                        f"Overwriting previously processed static property '{prop_key}' in class {class_name}."
                    )

                processed_static_props[prop_key] = processed_prop

            except Exception as e:
                logger.error(
                    f"Error processing static property {prop_data.get('name', '???')} for class {class_name}: {e}",
                    exc_info=True,
                )

        class_element.children.extend(list(processed_static_props.values()))

        # Sort children for consistency (optional, by start line)
        class_element.children.sort(
            key=lambda child: child.range.start_line if child.range else float("inf")
        )

        return class_element

    def _process_parameters(
        self, element: CodeElement, params_data: List[Dict]
    ) -> List[CodeElement]:
        """
        Process parameter data and create parameter CodeElements.

        Args:
            element: Parent element (function or method)
            params_data: Raw parameter data

        Returns:
            List of parameter CodeElements
        """
        param_elements = []
        parent_path = (
            f"{element.parent_name}.{element.name}"
            if element.parent_name
            else element.name
        )

        for param in params_data:
            if not isinstance(param, dict):
                continue

            name = param.get("name")
            if name:
                # Include 'optional' and 'default' if present in data
                param_elements.append(
                    CodeElement(
                        type=CodeElementType.PARAMETER,
                        name=name,
                        content=name,  # Could be more complex if we want full parameter definition
                        parent_name=parent_path,
                        value_type=param.get("type"),
                        additional_data={
                            "optional": param.get("optional", False),
                            "default": param.get("default"),
                        },
                    )
                )

        return param_elements

    def _process_return_value(
        self, element: CodeElement, return_info: Dict
    ) -> Optional[CodeElement]:
        """
        Process return value information and create a return value CodeElement.

        Args:
            element: Parent element (function or method)
            return_info: Raw return value data

        Returns:
            Return value CodeElement or None
        """
        if not isinstance(return_info, dict):
            return None

        return_type = return_info.get("return_type")
        return_values = return_info.get("return_values", [])  # Actually returned values

        if not return_type and not return_values:
            return None

        parent_path = (
            f"{element.parent_name}.{element.name}"
            if element.parent_name
            else element.name
        )

        # Use return type as content and value_type
        return CodeElement(
            type=CodeElementType.RETURN_VALUE,
            name=f"{element.name}_return",
            content=return_type or "",
            parent_name=parent_path,
            value_type=return_type,
            additional_data={
                "values": return_values
            },  # Preserve list of returned values
        )

    def extract_all(self, code: str) -> CodeElementsResult:
        """
        Extract all code elements and convert them to a structured CodeElementsResult.

        Args:
            code: Source code as string

        Returns:
            CodeElementsResult containing extracted elements
        """
        logger.info(f"Starting full extraction and processing for {self.language_code}")
        result = CodeElementsResult(elements=[])

        try:
            # 1. Get raw elements of different types
            raw_elements = self._extract_file_raw(code)
            print(f"DEBUG RAW EXTRACTION OUTPUT: {raw_elements}")

            if not self.post_processor:
                logger.error(f"No post-processor available for language {self.language_code}")
                return result

            # 2. Process imports
            raw_imports = raw_elements.get("imports", [])
            imports = self.post_processor.process_imports(raw_imports)
            result.elements.extend(imports)

            # 3. Process functions
            raw_functions = raw_elements.get("functions", [])
            functions = self.post_processor.process_functions(raw_functions)
            result.elements.extend(functions)

            # 4. Process classes
            raw_classes = raw_elements.get("classes", [])
            members = raw_elements.get("members", [])
            static_props = raw_elements.get("static_properties", [])
            classes = self.post_processor.process_classes(raw_classes, members, static_props)
            result.elements.extend(classes)

            # 5. Sort top-level elements
            result.elements.sort(
                key=lambda el: el.range.start_line if el.range else float("inf")
            )

        except Exception as e:
            logger.error(
                f"Critical error in `extract_all` for language {self.language_code}: {e}",
                exc_info=True,
            )
            return CodeElementsResult(elements=[])

        logger.info(
            f"Completed full extraction for {self.language_code}. Top-level element count: {len(result.elements)}"
        )
        return result

    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        """
        Find an element's location using an XPath expression.

        Args:
            code: Source code as string
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')

        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        logger.debug(f"Finding range by XPath: '{xpath}'")
        element_name, parent_name, element_type = XPathParser.get_element_info(xpath)
        logger.debug(
            f"XPath parsed: element={element_name}, parent={parent_name}, type={element_type}"
        )

        if not element_name and not element_type:
            logger.warning(
                "XPath must include either element name or type (e.g., [import])."
            )
            return (0, 0)

        # Special handling for '[import]'
        if element_type == CodeElementType.IMPORT.value and not element_name:
            return self._find_import_block_range(code)

        # Handle '[all]' - treat as no type/part specification
        target_type = element_type
        if target_type == "all":
            target_type = None  # Treat [all] as no type specification

        # If type is not specified in XPath, try to find matching element
        if not target_type:
            logger.debug(
                f"XPath without type for '{element_name}' (parent: {parent_name}). Trying find_element with 'property' type."
            )
            # Use find_element with 'property' type, which handles getters, setters and static
            start, end = self.find_element(
                code, CodeElementType.PROPERTY.value, element_name, parent_name
            )
            if start > 0:
                logger.debug(
                    f"Found '{element_name}' as property (getter/setter/static)."
                )
                return (start, end)

            # If not found as property, try as regular method (if has parent) or function/class (if global)
            fallback_type = (
                CodeElementType.METHOD.value
                if parent_name
                else CodeElementType.FUNCTION.value
            )
            logger.debug(f"Not found as property. Trying as '{fallback_type}'.")
            start, end = self.find_element(
                code, fallback_type, element_name, parent_name
            )
            if start > 0:
                logger.debug(f"Found '{element_name}' as '{fallback_type}'.")
                return (start, end)

            # Final fallback for global elements - try as class
            if not parent_name:
                logger.debug(f"Not found as function. Trying as class.")
                start, end = self.find_element(
                    code, CodeElementType.CLASS.value, element_name, parent_name=None
                )
                if start > 0:
                    logger.debug(f"Found '{element_name}' as class.")
                    return (start, end)

            logger.warning(
                f"No element found matching XPath '{xpath}' using default types."
            )
            return (0, 0)
        else:
            # If type is specified in XPath
            return self.find_element(code, target_type, element_name, parent_name)

    def _find_import_block_range(self, code: str) -> Tuple[int, int]:
        """
        Find the line range for the entire import block.

        Args:
            code: Source code as string

        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        imports = self._get_raw_extractor_results(code, CodeElementType.IMPORT.value)
        if imports and isinstance(imports, list):
            # Expect _get_raw_extractor_results to return a list, even if ImportExtractor gives 1 element
            valid_imports_data = []

            if len(imports) == 1 and imports[0].get("name") == "imports":
                # If we have a collective element, use its range
                raw_element = imports[0]
                range_data = raw_element.get("range")
                if range_data:
                    start_line = range_data.get("start", {}).get("line", 0)
                    end_line = range_data.get("end", {}).get("line", 0)
                    if start_line > 0 and end_line >= start_line:
                        return (start_line, end_line)
                # If collective has no range, try from internal list
                valid_imports_data = raw_element.get("imports", [])
            else:
                # If we got a list of individual imports (unexpected)
                valid_imports_data = [imp for imp in imports if isinstance(imp, dict)]

            if not valid_imports_data:
                return (0, 0)

            try:
                first_line = min(
                    imp.get("range", {}).get("start", {}).get("line", float("inf"))
                    for imp in valid_imports_data
                )
                last_line = max(
                    imp.get("range", {}).get("end", {}).get("line", 0)
                    for imp in valid_imports_data
                )

                if first_line == float("inf") or last_line == 0:
                    return (0, 0)

                return (int(first_line), int(last_line))
            except Exception as e:
                logger.error(
                    f"Error calculating import block range: {e}", exc_info=True
                )
                return (0, 0)

        return (0, 0)

    @classmethod
    def from_file_path(cls, file_path: str) -> "ExtractionService":
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
            raise ValueError(f"Unsupported file extension: {ext}")
        return cls(service.language_code)

    @classmethod
    def from_raw_code(
        cls, code: str, language_hints: List[str] = None
    ) -> "ExtractionService":
        """
        Create an extractor by attempting to detect the language from code.

        Args:
            code: Source code string
            language_hints: Optional list of language hints to try

        Returns:
            ExtractionService instance

        Raises:
            ValueError: If language could not be detected
        """
        if language_hints:
            logger.warning(
                "language_hints parameter in `from_raw_code` is not currently implemented."
            )

        service = get_language_service_for_code(code)
        if service:
            return cls(service.language_code)

        # Changed default language to raise error - force detection
        # return cls('python')  # Previously
        raise ValueError(
            "Could not automatically detect code language. Please specify explicitly."
        )

    def get_descriptor(
        self, element_type_descriptor: Union[str, CodeElementType]
    ) -> Optional[Any]:
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