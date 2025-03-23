"""
Core data models for the CodeHem code manipulation library.
"""
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field

class CodeElementType(str, Enum):
    """Types of code elements that can be identified and manipulated"""
    CLASS = 'class'
    METHOD = 'method'
    FUNCTION = 'function'
    PROPERTY = 'property'
    PROPERTY_GETTER = 'property_getter'
    PROPERTY_SETTER = 'property_setter'
    STATIC_PROPERTY = 'static_property'
    IMPORT = 'import'
    MODULE = 'module'
    VARIABLE = 'variable'
    PARAMETER = 'parameter'
    RETURN_VALUE = 'return_value'
    META_ELEMENT = 'meta_element'
    INTERFACE = 'interface'
    DECORATOR = 'decorator'
    ANNOTATION = 'annotation'
    ATTRIBUTE = 'attribute'
    DOC_COMMENT = 'doc_comment'
    TYPE_HINT = 'type_hint'
    FILE = 'file'
    DOCSTRING = 'docstring'

class CodeRange(BaseModel):
    """Represents a range in source code (line numbers)"""
    start_line: int
    end_line: int
    node: Any = None
    model_config = {'arbitrary_types_allowed': True}

class CodeElementXPathNode(BaseModel):
    """Represents a node in an XPath expression for code elements"""
    name: Optional[str] = None
    type: Optional[str] = None
    
    def __str__(self) -> str:
        """Convert to string representation"""
        result = ""
        
        # Add name if present
        if self.name:
            result = self.name
            
        # Add type if present
        if self.type:
            result += f"[{self.type}]"
        
        return result
    
    @property
    def is_valid(self) -> bool:
        """Check if this node is valid (has a name or type)"""
        return bool(self.name) or bool(self.type)

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

    @property
    def is_method(self) -> bool:
        return self.type == CodeElementType.METHOD

    @property
    def is_property(self) -> bool:
        return self.type == CodeElementType.PROPERTY or self.type == CodeElementType.PROPERTY_GETTER or self.type == CodeElementType.PROPERTY_SETTER or (self.type == CodeElementType.STATIC_PROPERTY)

    @property
    def is_interface(self) -> bool:
        return self.type == CodeElementType.INTERFACE

    @property
    def is_parameter(self) -> bool:
        return self.type == CodeElementType.PARAMETER

    @property
    def meta_elements(self) -> List['CodeElement']:
        """Get all metaelement children"""
        return [child for child in self.children if child.is_meta_element]

    @property
    def is_static_property(self) -> bool:
        return self.type == CodeElementType.STATIC_PROPERTY

    @property
    def decorators(self) -> List['CodeElement']:
        """Get all decorator metaelements"""
        return [child for child in self.meta_elements if child.type == CodeElementType.DECORATOR]

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
        return self.type == CodeElementType.META_ELEMENT or self.type == CodeElementType.DECORATOR or self.type == CodeElementType.ANNOTATION or self.type == CodeElementType.ATTRIBUTE or self.type == CodeElementType.DOC_COMMENT or self.type == CodeElementType.TYPE_HINT

    @property
    def is_instance_property(self) -> bool:
        return self.type == CodeElementType.INSTANCE_PROPERTY

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
        
CodeElement.model_rebuild()