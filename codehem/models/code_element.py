"""
Models for code elements.
Provides data structures for representing code elements and their relationships.
"""
import logging  # Added logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING  # Added Tuple, TYPE_CHECKING

from pydantic import BaseModel, Field

# Import enums and range directly (no circular dependencies here)
from .enums import CodeElementType
from .range import CodeRange

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from codehem.core.engine.xpath_parser import XPathParser

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

    def filter(self, xpath: str='') -> Optional[CodeElement]:
        """
        Filters code elements within this result based on an XPath expression.
        Delegates to the ElementFilter utility class to avoid circular imports.

        Args:
            xpath: XPath expression (e.g., 'ClassName.method_name',
                   'ClassName[interface].method_name[property_getter]', '[import]')

        Returns:
            Matching CodeElement or None if not found or if xpath is invalid.
        """
        # Use lazy import to avoid circular dependencies
        from .element_filter import ElementFilter
        return ElementFilter.filter(self, xpath)

# Ensure the model rebuilds to include the new method
CodeElement.model_rebuild()
CodeElementsResult.model_rebuild()