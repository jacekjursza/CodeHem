"""
Python-specific property getter extractor implementation.
"""
import logging
from codehem.core.extractors.template_property_getter_extractor import TemplatePropertyGetterExtractor
from codehem.core.registry import extractor

logger = logging.getLogger(__name__)

@extractor
class PythonPropertyGetterExtractor(TemplatePropertyGetterExtractor):
    """Python-specific implementation for property getter extraction."""
    LANGUAGE_CODE = 'python'
    
    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results with Python-specific handling."""
        # The standard template implementation works well for Python
        properties = super()._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
        
        # For Python, ensure we handle @property correctly
        for property_info in properties:
            # Check for complete @property decorator
            if 'content' in property_info and '@property' in property_info['content']:
                property_info['has_property_decorator'] = True
                
        return properties