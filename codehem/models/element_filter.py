"""
Utility module for filtering code elements using XPath expressions.
This module breaks the circular dependency between code_element.py and xpath_parser.py.
"""
import logging
from typing import List, Optional, TYPE_CHECKING

# Import direct types we need to access
from .enums import CodeElementType

if TYPE_CHECKING:
    from .code_element import CodeElement, CodeElementsResult
    from codehem.core.engine.xpath_parser import XPathParser

logger = logging.getLogger(__name__)

class ElementFilter:
    """
    Utility class for filtering CodeElements using XPath expressions.
    Handles parsing XPath expressions and navigating code element trees.
    """

    @staticmethod
    def filter(elements_result: 'CodeElementsResult', xpath: str = '') -> Optional['CodeElement']:
        """
        Filters code elements within a CodeElementsResult based on an XPath expression.
        Handles automatic prefixing with 'FILE.' if missing.

        Args:
            elements_result: CodeElementsResult containing code elements to filter
            xpath: XPath expression (e.g., 'ClassName.method_name',
                   'ClassName[interface].method_name[property_getter]', '[import]')

        Returns:
            Matching CodeElement or None if not found or if xpath is invalid.
        """
        if not xpath or not elements_result or not hasattr(elements_result, 'elements') or not elements_result.elements:
            return None

        # Import XPathParser lazily to avoid circular imports
        from codehem.core.engine.xpath_parser import XPathParser

        # Ensure XPath starts with FILE. (Adapted from CodeHem._ensure_file_prefix_static)
        root_prefix = XPathParser.ROOT_ELEMENT + '.'
        if not xpath.startswith(root_prefix) and (not xpath.startswith('[')):
            processed_xpath = root_prefix + xpath
        else:
            processed_xpath = xpath

        logger.debug(f"ElementFilter.filter: Filtering with processed XPath: '{processed_xpath}'")

        try:
            nodes = XPathParser.parse(processed_xpath)
            if not nodes:
                logger.warning(f"ElementFilter.filter: Could not parse XPath: '{processed_xpath}'")
                return None

            # Start search from top-level elements in elements_result.elements
            current_search_context = elements_result.elements
            target_element = None
            parent_element_context = None  # Keep track of the parent CodeElement

            for i, node in enumerate(nodes):
                # Skip the FILE node itself, start search from its potential children
                if i == 0 and node.type == CodeElementType.FILE.value:
                    logger.debug(f"Skipping FILE node, starting search in top-level elements.")
                    continue

                target_name = node.name
                target_type = node.type  # Type specified in the XPath node (e.g., 'method', 'property_getter')
                target_part = node.part  # Specific part like 'body', 'def' (currently filter doesn't use this, but parser supports it)

                if not target_name and target_type == CodeElementType.IMPORT.value:
                    # Special case for finding the combined import block by type
                    logger.debug("Special case: Searching for combined import block.")
                    for element in current_search_context:
                        # Assuming the post-processor creates a single 'imports' element
                        if element.type == CodeElementType.IMPORT and element.name == 'imports':
                            # If this is the last node in XPath, we found it
                            if i == len(nodes) - 1:
                                return element
                            else:
                                # Cannot search inside an import block with current model
                                logger.warning("Filtering inside an import block is not supported.")
                                return None
                    logger.debug("Combined import block not found.")
                    return None  # Not found

                found_in_level = None
                possible_matches = []
                logger.debug(f"Filter Level {i}: Searching for name='{target_name}', type='{target_type}' in {len(current_search_context)} elements.")

                for element in current_search_context:
                    # Check name match
                    name_match = element.name == target_name

                    # Check type match (more flexible)
                    # If XPath specifies a type, it must match element's type
                    # If XPath *doesn't* specify a type, allow match initially
                    type_match = target_type is None or element.type.value == target_type

                    # --- Refined Type Matching ---
                    # Handle property special case: if XPath requests 'property', match getter/setter/static too
                    if target_type == CodeElementType.PROPERTY.value and \
                       element.type in [CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER, CodeElementType.STATIC_PROPERTY]:
                        type_match = True
                        logger.debug(f"  -> Allowing match for PROPERTY type on element {element.name} ({element.type.value})")

                    # Ensure specific property requests match specific types ONLY
                    elif target_type == CodeElementType.PROPERTY_GETTER.value:
                        type_match = (element.type == CodeElementType.PROPERTY_GETTER)
                    elif target_type == CodeElementType.PROPERTY_SETTER.value:
                        type_match = (element.type == CodeElementType.PROPERTY_SETTER)
                    elif target_type == CodeElementType.STATIC_PROPERTY.value:
                        type_match = (element.type == CodeElementType.STATIC_PROPERTY)
                    # --- End Refined Type Matching ---

                    # Add to possible matches if name and type align
                    if name_match and type_match:
                        logger.debug(f"  -> Match found: {element.name} (Type: {element.type.value})")
                        possible_matches.append(element)

                if not possible_matches:
                    logger.warning(f"Filter: No element found at level {i} for name='{target_name}', type='{target_type}'.")
                    return None  # Not found at this level

                # Refine selection if multiple matches (e.g., prefer setter over getter if type wasn't specified)
                if len(possible_matches) > 1:
                    if target_type is None:  # Only apply preference if type wasn't specified in XPath
                        # Simple preference: setter > getter > method > other
                        def sort_key(el):
                            if el.type == CodeElementType.PROPERTY_SETTER:
                                return 4
                            if el.type == CodeElementType.PROPERTY_GETTER:
                                return 3
                            if el.type == CodeElementType.METHOD:
                                return 2
                            # Add other preferences if needed
                            return 1
                        possible_matches.sort(key=sort_key, reverse=True)
                        logger.debug(f"Multiple matches for name '{target_name}', selected best type via preference: {possible_matches[0].type.value}")
                    else:
                        # Type was specified, multiple matches indicate ambiguity or duplicate names
                        logger.warning(f"Multiple elements found for specific type '{target_type}' and name '{target_name}'. Returning the first one found.")
                        # Optionally, could sort by line number here if needed.

                found_in_level = possible_matches[0]  # Select the best/only match

                # If this is the last node in the XPath, we found our target
                if i == len(nodes) - 1:
                    target_element = found_in_level
                    break
                else:
                    # Otherwise, set context for the next level search
                    parent_element_context = found_in_level
                    if hasattr(found_in_level, 'children') and found_in_level.children:
                        current_search_context = found_in_level.children
                    else:
                        logger.warning(f"Filter: Element '{found_in_level.name}' found, but has no children to continue search for next XPath part.")
                        return None  # Cannot continue search

            # Final result
            if target_element:
                logger.debug(f'Filter: Final target element found: {target_element.name} ({target_element.type.value})')
            else:
                # This case might happen if XPath was just 'FILE'
                if len(nodes) == 1 and nodes[0].type == CodeElementType.FILE.value:
                    logger.warning("Filter: XPath resolves to FILE node, cannot return a specific element. Use extract_all().")
                else:
                    logger.warning(f'Filter: Could not find target element for XPath: {processed_xpath}')

            return target_element

        except Exception as e:
            logger.error(f"Error during filtering with XPath '{xpath}': {e}", exc_info=True)
            return None
