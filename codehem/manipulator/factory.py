from typing import Optional, Any
from codehem.models.enums import CodeElementType
from codehem.manipulator.registry import registry

def get_manipulator(element_type: str) -> Optional[Any]:
    """
    Get a manipulator for the specified element type.
    
    Args:
        element_type: Element type code (e.g., 'class', 'function')
        
    Returns:
        A manipulator for the specified element type or None if not supported
    """
    manipulator_class = registry.get_manipulator(element_type)
    if manipulator_class:
        return manipulator_class()
    return None