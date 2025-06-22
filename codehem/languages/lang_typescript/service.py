import re
import logging
from typing import List, Optional, Tuple
from codehem.models.enums import CodeElementType
from codehem.models.xpath import CodeElementXPathNode
from codehem.core.language_service import LanguageService
from codehem.core.registry import language_service, registry
from codehem.core.engine.xpath_parser import XPathParser
from codehem.models.code_element import CodeElement, CodeElementsResult
from .components.orchestrator import TypeScriptExtractionOrchestrator
from .components.post_processor import TypeScriptPostProcessor

logger = logging.getLogger(__name__)

@language_service
class TypeScriptLanguageService(LanguageService):
    """TypeScript/JavaScript language service implementation."""
    LANGUAGE_CODE = 'typescript'

    @property
    def file_extensions(self) -> List[str]:
        return ['.ts', '.tsx', '.js', '.jsx']

    @property
    def supported_element_types(self) -> List[str]:
        # List core supported types
        return [
            CodeElementType.CLASS.value,
            CodeElementType.FUNCTION.value,
            CodeElementType.METHOD.value,
            CodeElementType.INTERFACE.value,
            CodeElementType.PROPERTY.value, # Includes class fields
            CodeElementType.STATIC_PROPERTY.value, # May overlap with PROPERTY depending on extractor
            CodeElementType.IMPORT.value,
            CodeElementType.DECORATOR.value,
            CodeElementType.TYPE_ALIAS.value,
            CodeElementType.ENUM.value,
            CodeElementType.NAMESPACE.value, # If needed
            # Note: Getters/Setters might be handled as METHOD or PROPERTY by tree-sitter
            CodeElementType.PROPERTY_GETTER.value,
            CodeElementType.PROPERTY_SETTER.value,
        ]

    def detect_element_type(self, code: str) -> str:
        """Detects the type of TypeScript/JavaScript code element (simplified)."""
        code_stripped = code.strip()

        # More specific checks first
        if re.search(r'^\s*interface\s+\w+', code_stripped):
            return CodeElementType.INTERFACE.value
        if re.search(r'^\s*type\s+\w+\s*=', code_stripped):
            return CodeElementType.TYPE_ALIAS.value
        if re.search(r'^\s*enum\s+\w+', code_stripped):
            return CodeElementType.ENUM.value
        if re.search(r'^\s*namespace\s+\w+', code_stripped):
             return CodeElementType.NAMESPACE.value
        if re.search(r'^\s*@\w+', code_stripped): # Decorator check
            # Check if it's decorating a class/method/property
             lines = code_stripped.splitlines()
             if len(lines) > 1:
                  next_line = lines[1].strip()
                  if re.match(r'(public|private|protected|static|readonly)?\s*(async)?\s*(class|get|set)?', next_line):
                      # Likely decorating something else, return decorator
                      return CodeElementType.DECORATOR.value
                  # Else, could be just the decorator itself? Need context.
                  # For simplicity, return DECORATOR if it starts with @
             return CodeElementType.DECORATOR.value

        if re.search(r'^\s*(export\s+)?(abstract\s+)?class\s+\w+', code_stripped):
            return CodeElementType.CLASS.value
        # Method check (within a class context - harder without full parse)
        # Basic check for function signature potentially inside class-like structure
        if re.search(r'^\s*(public|private|protected|static|readonly|async)?\s*\w+\s*\(.*\)\s*{', code_stripped) and not code_stripped.startswith('function'):
            # Could be method or property function (getter/setter)
            if re.search(r'^\s*(get|set)\s+\w+\s*\(', code_stripped):
                 if code_stripped.startswith('get '):
                      return CodeElementType.PROPERTY_GETTER.value
                 else:
                      return CodeElementType.PROPERTY_SETTER.value
            return CodeElementType.METHOD.value
        if re.search(r'^\s*(export\s+)?(async\s+)?function\s+\w+', code_stripped):
            return CodeElementType.FUNCTION.value
        # Arrow function assigned to const/let/var
        if re.search(r'^\s*(export\s+)?(const|let|var)\s+\w+\s*=\s*(async)?\s*\(.*\)\s*=>', code_stripped):
            return CodeElementType.FUNCTION.value
        if re.search(r'^\s*import\s+', code_stripped):
            return CodeElementType.IMPORT.value
        # Property/Field check (simplified)
        if re.search(r'^\s*(public|private|protected|static|readonly)?\s*\w+\s*(:|;| =)', code_stripped) and not re.search(r'\(.*\)\s*=>', code_stripped):
             # Check if it looks like a static prop (often UPPERCASE by convention, but not strictly)
             match = re.match(r'^\s*(static\s+)?(readonly\s+)?([A-Z_0-9]+)\s*[:=]', code_stripped)
             if match:
                  return CodeElementType.STATIC_PROPERTY.value
             return CodeElementType.PROPERTY.value

        return CodeElementType.UNKNOWN.value

    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match(r'^(\s*)', line)
        return match.group(1) if match else ''

    def _find_target_element(self, elements_result: 'CodeElementsResult', xpath_nodes: List['CodeElementXPathNode']) -> Optional['CodeElement']:
        """
        Finds the target CodeElement based on parsed XPath.
        (Similar to Python version, may need TS/JS specific adjustments later).
        """
        if not xpath_nodes:
            return None

        current_nodes = xpath_nodes
        search_list: List['CodeElement'] = []

        # Handle FILE prefix
        if current_nodes and current_nodes[0].type == CodeElementType.FILE.value:
            logger.debug('_find_target_element: Detected FILE prefix, searching top-level elements.')
            search_list = elements_result.elements
            current_nodes = current_nodes[1:]
            if not current_nodes:
                logger.warning('_find_target_element: XPath contains only FILE node.')
                return None
        else:
            # If no FILE prefix, assume root search context is top-level elements
            search_list = elements_result.elements

        current_search_context = search_list
        target_element = None

        for i, node in enumerate(current_nodes):
            target_name = node.name
            target_type = node.type # Explicit type from XPath like [class]
            logger.debug(f"_find_target_element: Level {i}, searching for name='{target_name}', type='{target_type}' in {len(current_search_context)} elements.")

            found_in_level = None
            possible_matches = []

            for element in current_search_context:
                # Basic checks
                if not hasattr(element, 'name') or not hasattr(element, 'type'):
                    continue

                name_match = (element.name == target_name)

                # Type matching logic
                type_match = False
                if target_type is None: # No specific type requested in XPath part
                    type_match = True
                elif isinstance(element.type, CodeElementType) and element.type.value == target_type:
                    type_match = True
                # Allow fuzzy match for 'property' type in XPath
                elif target_type == CodeElementType.PROPERTY.value and isinstance(element.type, CodeElementType) and element.type in [
                    CodeElementType.PROPERTY,
                    CodeElementType.PROPERTY_GETTER,
                    CodeElementType.PROPERTY_SETTER,
                    CodeElementType.STATIC_PROPERTY,
                ]:
                    type_match = True
                    logger.debug(f'  -> Allowing match for PROPERTY type on element {element.name} ({element.type.value})')
                 # Allow fuzzy match for 'method' type in XPath (can include getters/setters)
                elif target_type == CodeElementType.METHOD.value and isinstance(element.type, CodeElementType) and element.type in [
                    CodeElementType.METHOD,
                    CodeElementType.PROPERTY_GETTER,
                    CodeElementType.PROPERTY_SETTER,
                ]:
                    type_match = True
                    logger.debug(f'  -> Allowing match for METHOD type on element {element.name} ({element.type.value})')

                if name_match and type_match:
                    logger.debug(f'  -> Potential match: {element.name} (Type: {element.type.value})')
                    possible_matches.append(element)

            if not possible_matches:
                logger.warning(f"_find_target_element: No element found at level {i} for name='{target_name}', type='{target_type}'.")
                return None

            # Select the best match if multiple possibilities exist (e.g., getter vs setter)
            if len(possible_matches) > 1:
                 # Prioritize more specific types if requested, or default preference order
                 def sort_key(el: 'CodeElement'):
                     el_type_val = el.type.value if isinstance(el.type, CodeElementType) else 'unknown'
                     specificity = 0
                     # Higher specificity for exact type match if provided
                     if target_type and el_type_val == target_type:
                         specificity = 10
                     # General preference order (can be adjusted)
                     if el_type_val == CodeElementType.PROPERTY_SETTER.value: specificity = max(specificity, 8)
                     elif el_type_val == CodeElementType.PROPERTY_GETTER.value: specificity = max(specificity, 7)
                     elif el_type_val == CodeElementType.METHOD.value: specificity = max(specificity, 6)
                     elif el_type_val == CodeElementType.STATIC_PROPERTY.value: specificity = max(specificity, 5)
                     elif el_type_val == CodeElementType.PROPERTY.value: specificity = max(specificity, 4)
                     elif el_type_val == CodeElementType.CLASS.value: specificity = max(specificity, 3)
                     elif el_type_val == CodeElementType.INTERFACE.value: specificity = max(specificity, 3)
                     elif el_type_val == CodeElementType.FUNCTION.value: specificity = max(specificity, 2)
                     # Use line number as a tie-breaker (preferring earlier definitions?)
                     line = el.range.start_line if el.range else 0
                     return (specificity, -line) # Negative line to prefer earlier definition

                 possible_matches.sort(key=sort_key, reverse=True)
                 found_in_level = possible_matches[0]
                 logger.debug(f'_find_target_element: Selected best match: {found_in_level.name} ({found_in_level.type.value}) from {len(possible_matches)} candidates.')
            else:
                 found_in_level = possible_matches[0]

            # Check if this is the last node in the XPath
            if i == len(current_nodes) - 1:
                target_element = found_in_level
                break
            # Otherwise, prepare to search within the children of the found element
            elif hasattr(found_in_level, 'children') and found_in_level.children:
                current_search_context = found_in_level.children
            else:
                logger.warning(f"_find_target_element: Element '{found_in_level.name}' found, but has no children to continue search for next XPath part '{current_nodes[i+1].name}'.")
                return None

        if target_element:
            logger.debug(f'_find_target_element: Final target element found: {target_element.name} ({target_element.type.value if isinstance(target_element.type, CodeElementType) else target_element.type})')
        else:
            logger.warning(f'_find_target_element: Could not find target element for XPath: {XPathParser.to_string(xpath_nodes)}')

        return target_element

    def _extract_part(self, code: str, element: 'CodeElement', part_name: Optional[str]) -> Optional[str]:
        """
        Extracts a specific part of the element (def, body) or the whole element.
        Needs refinement for TS/JS syntax (e.g., handling braces `{}`).
        """
        if not element or not element.range or element.range.start_line <= 0 or element.range.end_line < element.range.start_line:
            logger.warning(f"Attempting to extract part from element without valid range: {(element.name if element else 'None')}, Range: {getattr(element, 'range', 'N/A')}")
            return None

        code_lines = code.splitlines()
        element_start_idx = element.range.start_line - 1
        element_end_idx = element.range.end_line

        if element_start_idx < 0 or element_start_idx >= len(code_lines) or element_end_idx > len(code_lines):
            logger.error(f"Invalid line indices for element '{element.name}': start={element_start_idx}, end={element_end_idx}, total_lines={len(code_lines)}")
            return None

        element_lines = code_lines[element_start_idx:element_end_idx]
        if not element_lines:
            logger.warning(f"No lines found for element '{element.name}' in range {element.range.start_line}-{element.range.end_line}")
            return ''

        # --- Logic to find definition and body start ---
        # This needs significant adjustment for TS/JS syntax (decorators, braces, keywords)
        definition_line_local_idx = -1
        body_start_local_idx = -1
        first_non_decorator_line_idx = -1
        brace_level = 0
        first_brace_found = False

        for i, line in enumerate(element_lines):
            stripped_line = line.lstrip()

            # Skip decorator lines to find the actual definition start
            if stripped_line.startswith('@') and first_non_decorator_line_idx == -1:
                continue
            elif first_non_decorator_line_idx == -1 and stripped_line:
                first_non_decorator_line_idx = i

            if first_non_decorator_line_idx != -1 and i >= first_non_decorator_line_idx:
                # Look for keywords indicating the start of the definition
                 keywords = ['class ', 'interface ', 'function ', 'enum ', 'namespace ', 'type ']
                 # Also check for method/property syntax (might need refinement)
                 method_prop_pattern = r'(public |private |protected |static |get |set |async )*\w+\s*\('
                 if any(kw in stripped_line for kw in keywords) or re.search(method_prop_pattern, stripped_line):
                     if definition_line_local_idx == -1: # Found the main definition line
                          definition_line_local_idx = i

                 # Find the start of the body (first opening brace '{' after definition)
                 if definition_line_local_idx != -1 and '{' in stripped_line and not first_brace_found:
                      # Find column of first '{'
                      brace_col = stripped_line.find('{')
                      # Assume body starts on the next line or after the brace on the same line
                      if len(stripped_line) > brace_col + 1 and stripped_line[brace_col+1:].strip():
                           body_start_local_idx = i # Body starts after brace on same line
                           # Need column info here for precise body extraction... complex
                      else:
                           body_start_local_idx = i + 1 # Body starts on next line
                      first_brace_found = True
                      # Don't break yet, need full element lines for 'def' or 'all'

        # If indices weren't found, make safe assumptions (e.g., use first non-decorator line)
        if definition_line_local_idx == -1:
             definition_line_local_idx = first_non_decorator_line_idx if first_non_decorator_line_idx != -1 else 0
        if body_start_local_idx == -1:
             # Could try finding first '{' line + 1 as a guess
             first_brace_line = -1
             for idx, ln in enumerate(element_lines):
                  if '{' in ln:
                       first_brace_line = idx
                       break
             if first_brace_line != -1:
                  body_start_local_idx = first_brace_line + 1
             else:
                  body_start_local_idx = definition_line_local_idx + 1 # Fallback guess

        body_start_local_idx = min(body_start_local_idx, len(element_lines)) # Ensure index is within bounds

        # --- Extraction based on part_name ---
        lines_to_extract = []
        if part_name == 'body':
            if body_start_local_idx < len(element_lines):
                # Need to find matching closing brace '}' - complex with nesting!
                # Simple approach: extract until the end of the element's original range
                # This won't be accurate for just the body in nested scenarios without full parsing.
                # For now, return lines from body_start_local_idx to the end of the element list.
                lines_to_extract = element_lines[body_start_local_idx:]
                logger.debug(f"Extracting approximate body for '{element.name}' from relative index {body_start_local_idx}")
                # TODO: Implement proper brace matching for accurate body extraction
            else:
                logger.warning(f"Cannot extract '[body]' for '{element.name}', body start not reliably found or out of bounds.")
                return ''
        elif part_name == 'def': # Definition line(s) + body
            if definition_line_local_idx != -1:
                lines_to_extract = element_lines[definition_line_local_idx:]
                logger.debug(f"Extracting def+body for '{element.name}' from relative index {definition_line_local_idx}")
            else:
                logger.warning(f"Cannot extract '[def]' for '{element.name}', definition start not reliably found.")
                return None # Or return full content as fallback?
        else: # 'all' or None -> Extract full content including decorators
            lines_to_extract = element_lines
            logger.debug(f"Extracting full content for '{element.name}'")

        if not lines_to_extract:
            return ''
        else:
            # Simple dedent based on the first non-empty line of the extracted part
            min_indent_len = float('inf')
            for line in lines_to_extract:
                if line.strip():
                    min_indent_len = len(self.get_indentation(line))
                    break # Use indent of the first significant line
            if min_indent_len == float('inf'):
                 min_indent_len = 0

            # Return lines, removing the common minimum indent
            dedented_lines = []
            for line in lines_to_extract:
                 if line.strip():
                      dedented_lines.append(line[min_indent_len:])
                 else:
                      dedented_lines.append('') # Preserve blank lines
            return '\n'.join(dedented_lines)

    def extract(self, code: str) -> 'CodeElementsResult':
        """Extract code elements using the TypeScript orchestrator instead of template extractors."""
        print(f'=== TypeScript service extract method called ===')
        logger.debug(f'TypeScript service: Starting extraction using component-based orchestrator')
        try:
            # Create orchestrator with post-processor
            post_processor = TypeScriptPostProcessor()
            orchestrator = TypeScriptExtractionOrchestrator(post_processor)
            
            # Use orchestrator to extract elements
            result = orchestrator.extract_all(code)
            print(f'=== TypeScript orchestrator found {len(result.elements)} elements ===')
            logger.debug(f'TypeScript service: Completed extraction. Found {len(result.elements)} top-level elements.')
            return result
        except Exception as e:
            logger.error(f'TypeScript service: Error during extraction: {e}', exc_info=True)
            from codehem.models.code_element import CodeElementsResult # Local import
            return CodeElementsResult(elements=[]) # Return empty result

    def get_text_by_xpath_internal(self, code: str, xpath_nodes: List['CodeElementXPathNode']) -> Optional[str]:
        """Internal implementation for getting text based on parsed XPath nodes for TS/JS."""
        logger.debug(f'get_text_by_xpath_internal: Starting for XPath: {XPathParser.to_string(xpath_nodes)}')
        if not xpath_nodes:
            return None

        try:
            # Use the service's own extraction method which should use the post-processor
            elements_result: 'CodeElementsResult' = self.extract(code)
            if not elements_result or not elements_result.elements:
                 logger.warning("get_text_by_xpath_internal: Extraction returned no elements.")
                 return None
        except Exception as e:
            logger.error(f'Error during extraction within get_text_by_xpath_internal: {e}', exc_info=True)
            return None

        logger.debug(f'get_text_by_xpath_internal: Extraction completed, {len(elements_result.elements)} top-level elements.')

        # Use the filtering logic to find the target element
        target_element = self._find_target_element(elements_result, xpath_nodes)

        if not target_element:
            logger.warning(f'get_text_by_xpath_internal: Element not found for XPath: {XPathParser.to_string(xpath_nodes)}')
            return None

        logger.debug(f'get_text_by_xpath_internal: Found matching element: {target_element.name} ({target_element.type.value}) with range {target_element.range}')

        requested_part = xpath_nodes[-1].part
        if requested_part == 'all':
            requested_part = None # Treat 'all' as requesting the full element content

        logger.debug(f"get_text_by_xpath_internal: Requested part: '{requested_part}'")

        # Use the _extract_part logic (needs refinement for TS/JS)
        extracted_text = self._extract_part(code, target_element, requested_part)

        if extracted_text is None:
            logger.error(f"get_text_by_xpath_internal: Error extracting part '{requested_part}' for element '{target_element.name}'.")
            return None
        elif not extracted_text and requested_part == 'body':
             # Handle case where body might legitimately be empty
             logger.debug(f"get_text_by_xpath_internal: Extracted empty body for '{target_element.name}'.")
             return '' # Return empty string for empty body

        # Ensure consistent newline at the end? Or leave as is from _extract_part?
        # Let's leave as is for now.
        return extracted_text