from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field

from codehem.models.enums import CodeElementType
from codehem.models.range import CodeRange


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
    @staticmethod
    def from_dict(raw_element: dict) -> 'CodeElement':
        element_type_str = raw_element.get('type', 'unknown')
        name = raw_element.get('name', '')
        content = raw_element.get('content', '')
        element_type = CodeElementType.UNKNOWN
        if element_type_str == 'function':
            element_type = CodeElementType.FUNCTION
        elif element_type_str == 'class':
            element_type = CodeElementType.CLASS
        elif element_type_str == 'method':
            element_type = CodeElementType.METHOD
        elif element_type_str == 'property_getter':
            element_type = CodeElementType.PROPERTY_GETTER
        elif element_type_str == 'property_setter':
            element_type = CodeElementType.PROPERTY_SETTER
        elif element_type_str == 'import':
            element_type = CodeElementType.IMPORT
        elif element_type_str == 'decorator':
            element_type = CodeElementType.DECORATOR
        elif element_type_str == 'property':
            element_type = CodeElementType.PROPERTY
        elif element_type_str == 'static_property':
            element_type = CodeElementType.STATIC_PROPERTY
        range_data = raw_element.get('range')
        code_range = None
        if range_data:
            # Ensure line numbers are 1-indexed
            start_line = range_data['start']['line']
            end_line = range_data['end']['line']

            # Ensure we don't convert already 1-indexed values
            if isinstance(start_line, int) and start_line == 0:
                start_line = 1
            if isinstance(end_line, int) and end_line == 0:
                end_line = 1

            code_range = CodeRange(
                start_line=start_line, 
                start_column=range_data.get('start', {}).get('column', 0),
                end_line=end_line, 
                end_column=range_data.get('end', {}).get('column', 0)
            )
        element = CodeElement(type=element_type, name=name, content=content, range=code_range, parent_name=raw_element.get('class_name'), children=[])
        return element

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
