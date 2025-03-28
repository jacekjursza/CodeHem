"""
Python-specific property extractor implementation.
"""
import logging
import re
from typing import Dict, List, Optional, Any
from codehem.extractors.template_property_extractor import TemplatePropertyExtractor
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor

logger = logging.getLogger(__name__)

@extractor
class PythonPropertyExtractor(TemplatePropertyExtractor):
    """Python-specific implementation for property extraction."""
    LANGUAGE_CODE = 'python'
    
    def _extract_property_type(self, node, code_bytes, ast_handler):
        """Extract property type for Python."""
        # Try to find type annotation if available
        type_node = ast_handler.find_child_by_field_name(node, 'type')
        if type_node:
            return ast_handler.get_node_text(type_node, code_bytes)
        
        # Check for assignment to see if we can infer type
        right_node = ast_handler.find_child_by_field_name(node, 'right')
        if right_node:
            value = ast_handler.get_node_text(right_node, code_bytes)
            # Simple type inference
            if value.isdigit():
                return 'int'
            elif value.replace('.', '', 1).isdigit():
                return 'float'
            elif value in ['True', 'False']:
                return 'bool'
            elif (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                return 'str'
            elif value.startswith('[') and value.endswith(']'):
                return 'list'
            elif value.startswith('{') and value.endswith('}'):
                if ':' in value:
                    return 'dict'
                else:
                    return 'set'
        
        return None