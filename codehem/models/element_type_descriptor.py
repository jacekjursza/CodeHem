from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from codehem.models.enums import CodeElementType


@dataclass
class ElementTypeLanguageDescriptor:
    """Abstract base class for language handlers.
    
    Provides patterns (tree_sitter_query and regexp_pattern) for element finding,
    but does not implement the search logic itself. The actual element finding
    is implemented in higher-level components (extractors, finders) that use
    these patterns.
    
    When custom_extract=True, the handler implements its own extraction logic
    in the extract() method.
    """
    language_code: str = None
    element_type: CodeElementType = None
    tree_sitter_query: Optional[str] = None
    regexp_pattern: Optional[str] = None
    custom_extract: bool = False

    def __post_init__(self):
        # Ensure class variables override instance defaults
        cls = self.__class__
        if self.language_code is None and hasattr(cls, 'language_code'):
            self.language_code = cls.language_code
        if self.element_type is None and hasattr(cls, 'element_type'):
            self.element_type = cls.element_type
        if self.tree_sitter_query is None and hasattr(cls, 'tree_sitter_query'):
            self.tree_sitter_query = cls.tree_sitter_query
        if self.regexp_pattern is None and hasattr(cls, 'regexp_pattern'):
            self.regexp_pattern = cls.regexp_pattern
        if not self.custom_extract and hasattr(cls, 'custom_extract'):
            self.custom_extract = cls.custom_extract

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Custom extraction logic for language handlers with custom_extract=True.
        
        Args:
            code: The source code to extract from
            context: Optional context information for the extraction
            
        Returns:
            List of extracted elements as dictionaries
        """
        return []