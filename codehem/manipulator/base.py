from typing import Dict, Optional

from codehem import CodeElementType
from codehem.manipulator.abstract import AbstractManipulator
from codehem.manipulator.registry import registry

class BaseManipulator(AbstractManipulator):
    def __init__(self):
        self.handlers = {}
        self._load_handlers()
    
    def _load_handlers(self):
        """Load handlers from registry"""
        for language_code in registry.get_supported_languages():
            handler = registry.get_handler(language_code, self.element_type.value)
            if handler:
                self.handlers[language_code] = handler
                
    def replace_element(self, original_code: str, element_name: str, 
                       new_element: str, language_code: str, 
                       parent_name: Optional[str] = None) -> str:
        """Replace element in code"""
        handler = self.handlers.get(language_code.lower())
        if not handler:
            return original_code
        return handler.replace_element(original_code, element_name, new_element, parent_name)
        
    def add_element(self, original_code: str, new_element: str, 
                   language_code: str, parent_name: Optional[str] = None) -> str:
        """Add element to code"""
        handler = self.handlers.get(language_code.lower())
        if not handler:
            return original_code
        return handler.add_element(original_code, new_element, parent_name)
        
    def remove_element(self, original_code: str, element_name: str,
                      language_code: str, parent_name: Optional[str] = None) -> str:
        """Remove element from code"""
        handler = self.handlers.get(language_code.lower())
        if not handler:
            return original_code
        return handler.remove_element(original_code, element_name, parent_name)