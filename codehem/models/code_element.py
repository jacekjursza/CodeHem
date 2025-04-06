import logging  # Added logging
from typing import Any, Dict, List, Optional  # Added Tuple

from pydantic import BaseModel, Field

from codehem.core.engine.xpath_parser import XPathParser  # Added XPathParser

# Assuming imports are correctly handled relative to this file location
from .enums import CodeElementType
from .range import CodeRange

logger = logging.getLogger(__name__) # Added logger

class CodeElement(BaseModel):
    """Unified model for all code elements"""
    type: CodeElementType
    name: str
    content: str
    range: Optional[CodeRange] = None
    parent_name: Optional[str] = None
    value_type: Optional[str] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)
    children: List['CodeElement'] = Field(default_factory=list)

    @staticmethod
    def from_dict(raw_element: dict) -> 'CodeElement':
        element_type_str = raw_element.get('type', 'unknown')
        name = raw_element.get('name', '')
        # Removed print statement, use logging if needed
        # print(f'[from_dict] name={name}, type={element_type_str}') 
        logger.debug(f'CodeElement.from_dict: Creating element name={name}, type_str={element_type_str}')
        content = raw_element.get('content', '')
        
        # Attempt to convert string to enum, default to UNKNOWN
        try:
             element_type = CodeElementType(element_type_str.lower())
        except ValueError:
             logger.warning(f"Unknown element type string '{element_type_str}' encountered for element '{name}'. Defaulting to UNKNOWN.")
             element_type = CodeElementType.UNKNOWN
        
        range_data = raw_element.get('range')
        code_range = None
        if isinstance(range_data, dict): # Check if range_data is a dict before accessing
            try:
                start_line = range_data.get('start', {}).get('line', 0)
                end_line = range_data.get('end', {}).get('line', 0)
                # Ensure lines are at least 1 if they are 0 (often means not set properly)
                start_line = 1 if start_line == 0 else start_line 
                end_line = 1 if end_line == 0 else end_line

                code_range = CodeRange(
                     start_line=start_line, 
                     start_column=range_data.get('start', {}).get('column', 0), 
                     end_line=end_line, 
                     end_column=range_data.get('end', {}).get('column', 0),
                     # Pass node if available - check type?
                     node=range_data.get('node') 
                )
            except Exception as e:
                 logger.error(f"Error creating CodeRange for element '{name}': {e}. Range data: {range_data}", exc_info=True)
                 code_range = None # Ensure range is None if creation fails
        elif range_data is not None:
             logger.warning(f"Invalid range data format for element '{name}': {type(range_data)}. Expected dict.")

        # Handle potential 'class_name' vs 'parent_name' inconsistency if needed
        parent_name = raw_element.get('parent_name', raw_element.get('class_name'))

        element = CodeElement(
            type=element_type,
            name=name,
            content=content,
            range=code_range,
            parent_name=parent_name,
            value_type=raw_element.get('value_type'),
            additional_data=raw_element.get('additional_data', {}), # Ensure default is dict
            children=[] # Initialize children, they will be added by post-processor
        )
        return element

    # Properties remain the same
    @property
    def is_method(self) -> bool:
        return self.type == CodeElementType.METHOD

    @property
    def is_property(self) -> bool:
        return self.type in [CodeElementType.PROPERTY, CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER, CodeElementType.STATIC_PROPERTY]

    @property
    def is_interface(self) -> bool:
        return self.type == CodeElementType.INTERFACE

    @property
    def is_parameter(self) -> bool:
        return self.type == CodeElementType.PARAMETER

    @property
    def meta_elements(self) -> List['CodeElement']:
        """Get all metaelement children"""
        meta_types = [CodeElementType.DECORATOR, CodeElementType.ANNOTATION, CodeElementType.ATTRIBUTE, CodeElementType.DOC_COMMENT, CodeElementType.TYPE_HINT, CodeElementType.DOCSTRING]
        return [child for child in self.children if child.type in meta_types] # Simplified check

    @property
    def is_static_property(self) -> bool:
        return self.type == CodeElementType.STATIC_PROPERTY

    @property
    def decorators(self) -> List['CodeElement']:
        """Get all decorator children"""
        # Ensure this matches how decorators are added as children
        return [child for child in self.children if child.type == CodeElementType.DECORATOR]

    @property
    def is_return_value(self) -> bool:
        return self.type == CodeElementType.RETURN_VALUE

    @property
    def parameters(self) -> List['CodeElement']:
        """Get all parameter children"""
        return [child for child in self.children if child.is_parameter]

    @property
    def is_property_getter(self) -> bool:
        return self.type == CodeElementType.PROPERTY_GETTER

    @property
    def is_property_setter(self) -> bool:
        return self.type == CodeElementType.PROPERTY_SETTER

    @property
    def is_function(self) -> bool:
        return self.type == CodeElementType.FUNCTION

    @property
    def return_value(self) -> Optional['CodeElement']:
        """Get the return value element if it exists"""
        return_vals = [child for child in self.children if child.is_return_value]
        return return_vals[0] if return_vals else None

    @property
    def is_class(self) -> bool:
        return self.type == CodeElementType.CLASS

    @property
    def is_meta_element(self) -> bool:
        # Check against actual meta types
        meta_types = [CodeElementType.DECORATOR, CodeElementType.ANNOTATION, CodeElementType.ATTRIBUTE, CodeElementType.DOC_COMMENT, CodeElementType.TYPE_HINT, CodeElementType.DOCSTRING, CodeElementType.META_ELEMENT]
        return self.type in meta_types

class CodeElementsResult(BaseModel):
    """Collection of extracted code elements"""
    elements: List[CodeElement] = Field(default_factory=list)

    @property
    def classes(self) -> List[CodeElement]:
        return [e for e in self.elements if e.is_class or e.type == CodeElementType.INTERFACE]

    @property
    def properties(self) -> List[CodeElement]:
        return [e for e in self.elements if e.is_property]

    @property
    def methods(self) -> List[CodeElement]:
        return [e for e in self.elements if e.is_method]

    @property
    def functions(self) -> List[CodeElement]:
        return [e for e in self.elements if e.is_function]

    # --- Added filter method (moved from CodeHem static) ---
    def filter(self, xpath: str='') -> Optional['CodeElement']:
        """
        Filters code elements within this result based on an XPath expression.
        Handles automatic prefixing with 'FILE.' if missing.

        Args:
            xpath: XPath expression (e.g., 'ClassName.method_name',
                   'ClassName[interface].method_name[property_getter]', '[import]')

        Returns:
            Matching CodeElement or None if not found or if xpath is invalid.
        """
        if not xpath or not self.elements:
            return None

        # Ensure XPath starts with FILE. (Adapted from CodeHem._ensure_file_prefix_static)
        root_prefix = XPathParser.ROOT_ELEMENT + '.'
        if not xpath.startswith(root_prefix) and (not xpath.startswith('[')):
            processed_xpath = root_prefix + xpath
        else:
            processed_xpath = xpath

        logger.debug(f"CodeElementsResult.filter: Filtering with processed XPath: '{processed_xpath}'")

        try:
            nodes = XPathParser.parse(processed_xpath)
            if not nodes:
                logger.warning(f"CodeElementsResult.filter: Could not parse XPath: '{processed_xpath}'")
                return None

            # Start search from top-level elements in self.elements
            current_search_context = self.elements
            target_element = None
            parent_element_context = None # Keep track of the parent CodeElement

            for i, node in enumerate(nodes):
                # Skip the FILE node itself, start search from its potential children
                if i == 0 and node.type == CodeElementType.FILE.value:
                     logger.debug(f"Skipping FILE node, starting search in top-level elements.")
                     continue

                target_name = node.name
                target_type = node.type # Type specified in the XPath node (e.g., 'method', 'property_getter')
                target_part = node.part # Specific part like 'body', 'def' (currently filter doesn't use this, but parser supports it)

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
                     return None # Not found

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
                    return None # Not found at this level

                # Refine selection if multiple matches (e.g., prefer setter over getter if type wasn't specified)
                if len(possible_matches) > 1:
                     if target_type is None: # Only apply preference if type wasn't specified in XPath
                         # Simple preference: setter > getter > method > other
                         def sort_key(el):
                              if el.type == CodeElementType.PROPERTY_SETTER: return 4
                              if el.type == CodeElementType.PROPERTY_GETTER: return 3
                              if el.type == CodeElementType.METHOD: return 2
                              # Add other preferences if needed
                              return 1
                         possible_matches.sort(key=sort_key, reverse=True)
                         logger.debug(f"Multiple matches for name '{target_name}', selected best type via preference: {possible_matches[0].type.value}")
                     else:
                          # Type was specified, multiple matches indicate ambiguity or duplicate names
                          logger.warning(f"Multiple elements found for specific type '{target_type}' and name '{target_name}'. Returning the first one found.")
                          # Optionally, could sort by line number here if needed.

                found_in_level = possible_matches[0] # Select the best/only match

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
                         return None # Cannot continue search

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

# Ensure the model rebuilds to include the new method
CodeElement.model_rebuild()
CodeElementsResult.model_rebuild()