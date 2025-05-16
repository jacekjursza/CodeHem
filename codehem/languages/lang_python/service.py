"""
Refactored Python language service with orchestration support.

This module provides the refactored Python-specific language service implementation
that supports the new component-based architecture.
"""

import re
import logging
from typing import List, Optional, TYPE_CHECKING

from codehem.models.enums import CodeElementType
from codehem.models.xpath import CodeElementXPathNode
from codehem.core.language_service_extended import ExtendedLanguageService
from codehem.core.registry import language_service
from codehem.core.engine.xpath_parser import XPathParser
from codehem.languages.lang_python.components.orchestrator import PythonExtractionOrchestrator
from codehem.languages.lang_python.components.post_processor import PythonPostProcessor

if TYPE_CHECKING:
    from codehem.models.code_element import CodeElement, CodeElementsResult

logger = logging.getLogger(__name__)

@language_service
class PythonLanguageService(ExtendedLanguageService):
    """
    Python language service implementation with component architecture support.
    
    This class extends the ExtendedLanguageService to provide Python-specific
    language service functionality with orchestration support.
    """
    LANGUAGE_CODE = 'python'

    def __init__(self, formatter_class=None, **kwargs):
        """Initialize the service and create the orchestrator."""
        super().__init__(formatter_class, **kwargs)
        
        # Create the post-processor instance
        post_processor = PythonPostProcessor()
        
        # Create the orchestrator
        self._orchestrator = PythonExtractionOrchestrator(post_processor)

    def get_orchestrator(self):
        """Get the Python extraction orchestrator."""
        return self._orchestrator

    @property
    def file_extensions(self) -> List[str]:
        """Get file extensions supported by this language."""
        return ['.py']

    @property
    def supported_element_types(self) -> List[str]:
        """Get element type string values supported by this language."""
        # Return list of string values from the enum
        return [
            CodeElementType.CLASS.value,
            CodeElementType.FUNCTION.value,
            CodeElementType.METHOD.value,
            CodeElementType.IMPORT.value,
            CodeElementType.DECORATOR.value,
            CodeElementType.PROPERTY_GETTER.value,
            CodeElementType.PROPERTY_SETTER.value,
            CodeElementType.STATIC_PROPERTY.value
        ]

    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of element in the code.
        
        Args:
            code: The code to analyze
            
        Returns:
            Element type string (value from CodeElementType)
        """
        code_stripped = code.strip()
        # Prioritize setter detection
        if re.search(r'@([a-zA-Z_][a-zA-Z0-9_]*)\.setter', code_stripped):
             return CodeElementType.PROPERTY_SETTER.value
        if re.search(r'@property', code_stripped):
            return CodeElementType.PROPERTY_GETTER.value
        # Use raw strings for regex patterns with backslashes
        if re.match(r'^\s*class\s+\w+', code_stripped):
            return CodeElementType.CLASS.value
        # Check for 'self' or 'cls' as first argument for method detection
        if re.search(r'def\s+\w+\s*\(\s*(?:self|cls)\b', code_stripped):
            return CodeElementType.METHOD.value
        # General function detection
        if re.match(r'^\s*def\s+\w+', code_stripped):
            return CodeElementType.FUNCTION.value
        if re.match(r'^(?:import|from)\s+\w+', code_stripped):
            return CodeElementType.IMPORT.value
        # Basic check for class-level assignment (static property)
        # This regex is very basic and might need refinement
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*[:=]', code_stripped) and not re.match(r'^\s*def\s', code_stripped):
             # Avoid matching function defs that might have type hints like 'var: type = val' in signature
             return CodeElementType.STATIC_PROPERTY.value
        if re.match(r'^@', code_stripped):
             return CodeElementType.DECORATOR.value # Basic decorator check

        return CodeElementType.UNKNOWN.value

    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match(r'^(\s*)', line) # Use raw string for regex
        return match.group(1) if match else ''

    def _find_target_element(self, elements_result: 'CodeElementsResult', xpath_nodes: List['CodeElementXPathNode']) -> Optional['CodeElement']:
        """Finds the target CodeElement based on parsed XPath, handling FILE prefix."""
        if not xpath_nodes:
            return None

        current_nodes = xpath_nodes
        search_list: List['CodeElement'] = [] # Define type hint

        # Handle FILE prefix
        if current_nodes and current_nodes[0].type == CodeElementType.FILE.value:
            logger.debug('_find_target_element: Detected FILE prefix, searching top-level elements.')
            search_list = elements_result.elements # Start search at top level
            current_nodes = current_nodes[1:] # Consume FILE node
            if not current_nodes:
                logger.warning('_find_target_element: XPath contains only FILE node, cannot select specific element.')
                return None
        else:
             # If no FILE prefix, assume search starts at top level anyway
             search_list = elements_result.elements

        # Iteratively search through levels defined by XPath nodes
        current_search_context = search_list
        target_element = None

        for i, node in enumerate(current_nodes):
            target_name = node.name
            target_type = node.type # Explicit type from XPath (e.g., 'method', 'property_getter')
            found_in_level = None
            possible_matches = []

            logger.debug(f"_find_target_element: Level {i}, searching for name='{target_name}', type='{target_type}' in {len(current_search_context)} elements.")

            for element in current_search_context:
                # Basic validation of element structure
                if not hasattr(element, 'name') or not hasattr(element, 'type') or not hasattr(element, 'children'):
                    continue

                name_match = (element.name == target_name)

                # Type matching logic
                type_match = False
                if target_type is None: # No specific type requested in XPath part
                    type_match = True
                elif element.type.value == target_type: # Exact type match
                    type_match = True
                # Allow matching 'property' type against specific property kinds
                elif target_type == CodeElementType.PROPERTY.value and element.type in [
                    CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER, CodeElementType.STATIC_PROPERTY
                ]:
                    type_match = True
                    logger.debug(f'  -> Allowing match for PROPERTY type on specific property element {element.name} ({element.type.value})')
                # Allow matching 'method' type against getters/setters (as they are methods)
                # Note: This might need refinement depending on desired specificity vs. flexibility
                elif target_type == CodeElementType.METHOD.value and element.type in [
                    CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER
                ]:
                     type_match = True
                     logger.debug(f'  -> Allowing potential match for METHOD type on property element {element.name} ({element.type.value})')

                if name_match and type_match:
                    logger.debug(f'  -> Potential match: {element.name} (Type: {element.type.value})')
                    possible_matches.append(element)

            if not possible_matches:
                logger.warning(f"_find_target_element: No element found at level {i} for name='{target_name}', type='{target_type}'.")
                return None # Stop search if level fails

            # Sort matches to prioritize specific types if multiple found for the same name
            def sort_key(el: 'CodeElement'):
                el_type_val = el.type.value
                specificity = 0
                if el_type_val == target_type: specificity = 10 # Exact type match is best
                # Define order of preference for properties/methods if type is ambiguous in XPath
                if el_type_val == CodeElementType.PROPERTY_SETTER.value: specificity = max(specificity, 8)
                elif el_type_val == CodeElementType.PROPERTY_GETTER.value: specificity = max(specificity, 7)
                elif el_type_val == CodeElementType.STATIC_PROPERTY.value: specificity = max(specificity, 6)
                elif el_type_val == CodeElementType.METHOD.value: specificity = max(specificity, 5)
                elif el_type_val == CodeElementType.CLASS.value: specificity = max(specificity, 4)
                elif el_type_val == CodeElementType.FUNCTION.value: specificity = max(specificity, 3)
                # Use start line as secondary sort key
                line = el.range.start_line if el.range else 0
                return (specificity, line)

            possible_matches.sort(key=sort_key, reverse=True) # Highest specificity first
            found_in_level = possible_matches[0]
            logger.debug(f'_find_target_element: Selected best match: {found_in_level.name} ({found_in_level.type.value}) from {len(possible_matches)} candidates.')

            # Check if this is the last node in the XPath
            if i == len(current_nodes) - 1:
                target_element = found_in_level
                break # Found the final target
            else:
                # Prepare for the next level search within the children of the found element
                if hasattr(found_in_level, 'children') and found_in_level.children:
                    current_search_context = found_in_level.children
                else:
                    # Reached an element that should have children according to XPath, but doesn't
                    logger.warning(f"_find_target_element: Element '{found_in_level.name}' found, but has no children to continue search for next XPath part '{current_nodes[i+1].name}'.")
                    return None # Cannot continue search

        # Final check and return
        if target_element:
            logger.debug(f'_find_target_element: Final target element found: {target_element.name} ({target_element.type.value})')
        else:
            logger.warning(f'_find_target_element: Could not find target element for XPath: {XPathParser.to_string(xpath_nodes)}')

        return target_element

    def _extract_part(self, code: str, element: 'CodeElement', part_name: Optional[str]) -> Optional[str]:
        """
        Extracts a specific part of the element (def, body) or the whole element,
        attempting to correctly handle decorators.

        Args:
            code: The full source code.
            element: The CodeElement object (must have range).
            part_name: The requested part ('def', 'body', or None for whole).

        Returns:
            The extracted code part as a string, or None if extraction fails.
        """
        if not element or not element.range or element.range.start_line <= 0 or element.range.end_line < element.range.start_line:
            logger.warning(f"Attempting to extract part from element without valid range: {(element.name if element else 'None')}, Range: {getattr(element, 'range', 'N/A')}")
            return None

        code_lines = code.splitlines()
        element_start_idx = element.range.start_line - 1 # 0-based index
        element_end_idx = element.range.end_line       # Exclusive index for slicing

        # Ensure indices are within bounds
        if element_start_idx < 0 or element_start_idx >= len(code_lines) or element_end_idx > len(code_lines):
             logger.error(f"Invalid line indices calculated for element '{element.name}': start={element_start_idx}, end={element_end_idx}, total_lines={len(code_lines)}")
             return None

        # Get the lines belonging to the element based on its range
        element_lines = code_lines[element_start_idx:element_end_idx]
        if not element_lines:
             logger.warning(f"No lines found for element '{element.name}' in range {element.range.start_line}-{element.range.end_line}")
             return "" # Return empty string if range yielded no lines

        # Find the definition line (first line starting with 'def ' or 'class ')
        # after skipping any potential decorator lines ('@')
        definition_line_local_idx = -1 # Index relative to element_lines
        first_non_decorator_line_idx = -1
        for i, line in enumerate(element_lines):
            stripped_line = line.lstrip()
            if stripped_line.startswith('@'):
                continue # Skip decorator
            if stripped_line: # Found first non-decorator, non-empty line
                 first_non_decorator_line_idx = i
                 # Check if this line is the actual definition
                 if stripped_line.startswith(('def ', 'class ')):
                      definition_line_local_idx = i
                 # Handle cases like static properties which might not start with def/class
                 elif element.type == CodeElementType.STATIC_PROPERTY:
                      definition_line_local_idx = i # Treat the assignment line as the 'definition'
                 # If the first non-decorator line doesn't start with def/class (e.g., just body),
                 # we might not have a separate definition line in this view.
                 break # Stop after finding the first non-decorator line

        # If no non-decorator line found (e.g., only decorators), definition is problematic
        if first_non_decorator_line_idx == -1:
             logger.warning(f"Could not find non-decorator lines within element '{element.name}' range.")
             # Fallback: maybe treat the first line as definition? Or return full content?
             # Let's return full content for safety if def/body requested but cannot be found.
             if part_name in ['def', 'body']:
                  logger.warning(f"  Cannot extract '[{part_name}]' part, returning full content.")
                  part_name = None
             definition_line_local_idx = 0 # Fallback for 'all' case

        # If we didn't find a 'def' or 'class' line explicitly, but found *some* code,
        # assume the first non-decorator line is the definition start for part extraction.
        if definition_line_local_idx == -1 and first_non_decorator_line_idx != -1:
             definition_line_local_idx = first_non_decorator_line_idx

        # Calculate body start index (relative to element_lines)
        # Body starts on the line *after* the definition line ends (often just def_line + 1)
        # Need to handle potential multiline definitions/signatures later if required
        body_start_local_idx = -1
        if definition_line_local_idx != -1:
             # Find the end of the definition signature (simple case: assume it ends with ':')
             def_line_content = element_lines[definition_line_local_idx]
             if def_line_content.rstrip().endswith(':'):
                  body_start_local_idx = definition_line_local_idx + 1
             else:
                  # More complex sig ending? For now, assume next line or end.
                  body_start_local_idx = definition_line_local_idx + 1
                  logger.debug(f"Definition line for {element.name} doesn't end with ':', assuming body starts on next line.")

             # Ensure body start is within the element lines
             if body_start_local_idx >= len(element_lines):
                   body_start_local_idx = -1 # No body lines found after definition

        # Extract based on part_name
        lines_to_extract = []
        if part_name == 'body':
            if body_start_local_idx != -1:
                lines_to_extract = element_lines[body_start_local_idx:]
                logger.debug(f"Extracting body for '{element.name}' from relative index {body_start_local_idx}")
            else:
                logger.warning(f"Cannot extract '[body]' for '{element.name}', body start not reliably found.")
                return "" # Return empty string for missing body
        elif part_name == 'def':
            if definition_line_local_idx != -1:
                lines_to_extract = element_lines[definition_line_local_idx:]
                logger.debug(f"Extracting def+body for '{element.name}' from relative index {definition_line_local_idx}")
            else:
                 logger.warning(f"Cannot extract '[def]' for '{element.name}', definition start not reliably found.")
                 # Return full content as fallback? Or None? Let's return None for failed part extraction.
                 return None
        else: # No part specified or 'all', return everything in the element's range
            lines_to_extract = element_lines
            logger.debug(f"Extracting full content for '{element.name}'")

        # Reconstruct the string, preserving original relative indentation
        if not lines_to_extract:
             return ""
        else:
             # Find common minimum indent within the extracted lines to keep relative indent correct
             min_indent_len = float('inf')
             for line in lines_to_extract:
                  if line.strip():
                       min_indent_len = min(min_indent_len, len(self.get_indentation(line)))
             if min_indent_len == float('inf'): min_indent_len = 0 # Handle case of only blank lines

             # Dedent based on the minimum indent *within the extracted part*
             # This might not be strictly necessary if original lines are returned,
             # but can help normalize output if needed. For now, just join original lines.
             # result_lines = [line[min_indent_len:] if line.strip() else '' for line in lines_to_extract]
             # return '\n'.join(result_lines)
             return '\n'.join(lines_to_extract) # Return original lines as found

    def get_text_by_xpath_internal(self, code: str, xpath_nodes: List['CodeElementXPathNode']) -> Optional[str]:
        """
        Internal method to retrieve text content based on parsed XPath nodes for Python.
        
        Args:
            code: The source code
            xpath_nodes: The parsed XPath nodes
            
        Returns:
            The extracted text or None if extraction fails
        """
        logger.debug(f'get_text_by_xpath_internal: Starting for XPath: {XPathParser.to_string(xpath_nodes)}')
        if not xpath_nodes:
            return None

        # Perform extraction to get the element tree
        # Use the orchestrator for extraction
        try:
            elements_result = self._orchestrator.extract_all(code)
        except Exception as e:
            logger.error(f"Error during orchestrator extraction within get_text_by_xpath_internal: {e}", exc_info=True)
            return None # Cannot proceed if extraction fails

        logger.debug(f'get_text_by_xpath_internal: Extraction completed, {len(elements_result.elements)} top-level elements.')

        # Find the specific target element based on the parsed XPath
        target_element = self._find_target_element(elements_result, xpath_nodes)

        if not target_element:
            logger.warning(f'get_text_by_xpath_internal: Element not found for XPath: {XPathParser.to_string(xpath_nodes)}')
            return None

        logger.debug(f'get_text_by_xpath_internal: Found matching element: {target_element.name} ({target_element.type.value}) with range {target_element.range}')

        # Determine the requested part (e.g., 'body', 'def') from the last XPath node
        requested_part = xpath_nodes[-1].part
        if requested_part == 'all': # Treat 'all' like no part specified
            requested_part = None
        logger.debug(f"get_text_by_xpath_internal: Requested part: '{requested_part}'")

        # Extract the specific part using the refactored _extract_part method
        extracted_text = self._extract_part(code, target_element, requested_part)

        if extracted_text is None:
            # _extract_part returns None on failure to find the specific part
            logger.error(f"get_text_by_xpath_internal: Error extracting part '{requested_part}' for element '{target_element.name}'.")
            return None
        elif not extracted_text and requested_part == 'body':
             # Handle empty body case specifically - return empty string not None
             logger.debug(f"get_text_by_xpath_internal: Extracted empty body for '{target_element.name}'.")
             return ""

        return extracted_text
