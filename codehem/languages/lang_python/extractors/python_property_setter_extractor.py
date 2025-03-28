"""
Python-specific property setter extractor implementation.
"""
import logging
import re
from codehem.core.extractors.template_property_setter_extractor import TemplatePropertySetterExtractor
from codehem.core.registry import extractor

logger = logging.getLogger(__name__)

@extractor
class PythonPropertySetterExtractor(TemplatePropertySetterExtractor):
    """Python-specific implementation for property setter extraction."""
    LANGUAGE_CODE = 'python'
    
    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results with Python-specific handling."""
        # The standard template implementation works well for Python
        properties = super()._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
        
        # For Python, ensure we extract the original property name from the decorator
        for property_info in properties:
            if 'content' in property_info:
                # Find the property name from @property_name.setter pattern
                setter_pattern = r'@(\w+)\.setter'
                setter_match = re.search(setter_pattern, property_info['content'])
                if setter_match:
                    property_info['property_name'] = setter_match.group(1)
                
        return properties