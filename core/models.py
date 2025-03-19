from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field

class CodeElementType(str, Enum):
    """Types of code elements that can be identified and manipulated"""
    CLASS = "class"
    METHOD = "method"
    FUNCTION = "function"
    PROPERTY = "property"
    IMPORT = "import"
    MODULE = "module"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    RETURN_VALUE = "return_value"

class CodeRange(BaseModel):
    """Represents a range in source code (line numbers)"""
    start_line: int
    end_line: int
    node: Any = None  # tree-sitter Node object (not serializable directly)
    
    class Config:
        arbitrary_types_allowed = True

class CodeElement(BaseModel):
    """Unified model for all code elements"""
    type: CodeElementType
    name: str
    content: str
    range: Optional[CodeRange] = None
    parent_name: Optional[str] = None  # For methods, properties (class name)
    value_type: Optional[str] = None  # For variables, parameters, return values
    additional_data: Dict[str, Any] = Field(default_factory=dict)
    children: List["CodeElement"] = Field(default_factory=list)
    
    @property
    def is_class(self) -> bool:
        return self.type == CodeElementType.CLASS
        
    @property
    def is_method(self) -> bool:
        return self.type == CodeElementType.METHOD
        
    @property
    def is_function(self) -> bool:
        return self.type == CodeElementType.FUNCTION
        
    @property
    def is_property(self) -> bool:
        return self.type == CodeElementType.PROPERTY
        
    @property
    def is_parameter(self) -> bool:
        return self.type == CodeElementType.PARAMETER
        
    @property
    def is_return_value(self) -> bool:
        return self.type == CodeElementType.RETURN_VALUE
        
    @property
    def parameters(self) -> List["CodeElement"]:
        """Get all parameter children"""
        return [child for child in self.children if child.is_parameter]
        
    @property
    def return_value(self) -> Optional["CodeElement"]:
        """Get the return value element if it exists"""
        return_vals = [child for child in self.children if child.is_return_value]
        return return_vals[0] if return_vals else None

class CodeElementsResult(BaseModel):
    """Collection of extracted code elements"""
    elements: List[CodeElement] = Field(default_factory=list)
    
    @property
    def classes(self) -> List[CodeElement]:
        return [e for e in self.elements if e.is_class]
        
    @property
    def methods(self) -> List[CodeElement]:
        return [e for e in self.elements if e.is_method]
        
    @property
    def functions(self) -> List[CodeElement]:
        return [e for e in self.elements if e.is_function]
        
    @property
    def properties(self) -> List[CodeElement]:
        return [e for e in self.elements if e.is_property]

# Handle circular references
CodeElement.model_rebuild()