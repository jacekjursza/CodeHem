"""
Generic extractor that can handle any element type using handlers.
"""
from typing import Dict, List, Optional, Any
import logging
from codehem.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.languages.registry import registry
logger = logging.getLogger(__name__)

class GenericExtractor(BaseExtractor):
    """Generic extractor for any element type."""

    def __init__(self, element_type: str):
        super().__init__()
        self._element_type = element_type
        if hasattr(element_type, 'value'):
            self._element_type = element_type.value

    @property
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""
        return getattr(CodeElementType, self._element_type.upper(), CodeElementType.UNKNOWN)

    def supports_language(self, language_code: str) -> bool:
        """Check if this extractor supports the given language."""
        handler = registry.get_handler(language_code, self._element_type)
        return handler is not None

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Extract elements from the provided code.
        
        Args:
            code: The source code to extract from
            context: Optional context information for the extraction
            
        Returns:
            List of extracted elements as dictionaries
        """
        context = context or {}
        language_code = context.get('language_code', 'python').lower()
        handler = registry.get_handler(language_code, self._element_type)
        
        if not handler:
            logger.warning(f"No handler found for {language_code}/{self._element_type}")
            return []
            
        if handler.custom_extract:
            return handler.extract(code, context)
            
        return self._extract_with_patterns(code, handler, context)

    def _extract_with_patterns(self, code: str, handler, context: Dict[str, Any]) -> List[Dict]:
        """Extract using tree-sitter first, fall back to regex if needed."""
        if handler.tree_sitter_query:
            try:
                elements = self._extract_with_tree_sitter(code, handler, context)
                if elements:
                    return elements
            except Exception as e:
                logger.debug(f"Tree-sitter extraction failed: {e}")
                
        if handler.regexp_pattern:
            try:
                return self._extract_with_regex(code, handler, context)
            except Exception as e:
                logger.debug(f"Regex extraction failed: {e}")
                
        return []

    def _extract_with_tree_sitter(self, code: str, handler, context: Dict[str, Any]) -> List[Dict]:
        """Extract elements using tree-sitter."""
        import re
        ast_handler = self._get_ast_handler(handler.language_code)
        if not ast_handler:
            return []
            
        try:
            (tree, code_bytes) = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, tree, code_bytes)
            
            elements = []
            for match in query_results:
                element_def = None
                element_name = None
                element_type = self._element_type
                
                for (node, node_type) in match:
                    if node_type.endswith('_def'):
                        element_def = node
                    elif node_type.endswith('_name'):
                        element_name = node
                
                if element_def and element_name:
                    name = ast_handler.get_node_text(element_name, code_bytes)
                    content = ast_handler.get_node_text(element_def, code_bytes)
                    elements.append({
                        'type': element_type,
                        'name': name,
                        'content': content,
                        'range': {
                            'start': {'line': element_def.start_point[0], 'column': element_def.start_point[1]},
                            'end': {'line': element_def.end_point[0], 'column': element_def.end_point[1]}
                        }
                    })
            
            return elements
        except Exception as e:
            logger.debug(f'Tree-sitter extraction error: {e}')
            return []

    def _extract_with_regex(self, code: str, handler, context: Dict[str, Any]) -> List[Dict]:
        """Extract elements using regex."""
        import re
        try:
            pattern = handler.regexp_pattern
            matches = re.finditer(pattern, code, re.DOTALL)
            
            elements = []
            for match in matches:
                content = match.group(0)
                # Extract the name - usually in group 1
                name = match.group(1) if match.lastindex and match.lastindex >= 1 else ""
                
                start_pos = match.start()
                end_pos = match.end()
                
                # Calculate line numbers
                lines_before = code[:start_pos].count('\n')
                last_newline = code[:start_pos].rfind('\n')
                start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
                
                lines_total = code[:end_pos].count('\n')
                last_newline_end = code[:end_pos].rfind('\n')
                end_column = end_pos - last_newline_end - 1 if last_newline_end >= 0 else end_pos
                
                elements.append({
                    'type': self._element_type,
                    'name': name,
                    'content': content,
                    'range': {
                        'start': {'line': lines_before, 'column': start_column},
                        'end': {'line': lines_total, 'column': end_column}
                    }
                })
            
            return elements
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []