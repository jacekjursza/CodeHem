"""
Import extractor that uses language-specific handlers.
"""
from typing import Dict, List, Optional, Any
import re
import logging
from codehem.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class ImportExtractor(BaseExtractor):
    """Import extractor using language-specific handlers."""
    ELEMENT_TYPE = CodeElementType.IMPORT

    @property
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""
        return self.ELEMENT_TYPE

    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract using TreeSitter first, fall back to regex if needed."""
        imports = []
        
        # Try TreeSitter extraction first
        if handler.tree_sitter_query:
            imports = self._extract_with_tree_sitter(code, handler, context)
        
        # Fall back to regex if no imports were found
        if not imports and handler.regexp_pattern:
            imports = self._extract_with_regex(code, handler, context)
        
        # If we found imports, combine them into a section
        if imports:
            # Sort imports by line number
            imports.sort(key=lambda x: x.get('range', {}).get('start', {}).get('line', 0))
            first_import = imports[0]
            last_import = imports[-1]
            first_line = first_import['range']['start']['line']
            last_line = last_import['range']['end']['line']
            
            # Get the complete import section
            code_lines = code.splitlines()
            import_section = '\n'.join(code_lines[first_line:last_line + 1])
            
            # Create a combined import element
            combined_import = {
                'type': 'import',
                'name': 'imports',
                'content': import_section,
                'range': {
                    'start': {'line': first_line, 'column': first_import['range']['start']['column']},
                    'end': {'line': last_line, 'column': last_import['range']['end']['column']}
                },
                'imports': imports  # Store individual imports for reference
            }
            return [combined_import]
        
        return []

    def _extract_with_tree_sitter(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract imports using TreeSitter."""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            return []
        try:
            root, code_bytes = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
            imports = []
            for node, capture_name in query_results:
                if capture_name in ('import', 'import_from'):
                    content = ast_handler.get_node_text(node, code_bytes)
                    name = 'import'
                    if 'from ' in content:
                        try:
                            name = re.search('from\\s+([^\\s]+)', content).group(1)
                        except:
                            pass
                    elif 'import ' in content:
                        try:
                            name = re.search('import\\s+([^\\s]+)', content).group(1)
                        except:
                            pass
                    imports.append({'type': 'import', 'name': name, 'content': content, 'range': {'start': {'line': node.start_point[0] + 1, 'column': node.start_point[1]}, 'end': {'line': node.end_point[0] + 1, 'column': node.end_point[1]}}})
            return imports
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {e}')
            return []

    def _extract_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract imports using regex."""
        try:
            pattern = handler.regexp_pattern
            matches = re.finditer(pattern, code, re.MULTILINE)
            imports = []
            for match in matches:
                content = match.group(0)
                name = 'import'
                if content.startswith('from '):
                    try:
                        name = re.search('from\\s+([^\\s]+)', content).group(1)
                    except:
                        pass
                elif content.startswith('import '):
                    try:
                        name = re.search('import\\s+([^\\s]+)', content).group(1)
                    except:
                        pass
                start_pos = match.start()
                end_pos = match.end()
                lines_before = code[:start_pos].count('\n')
                last_newline = code[:start_pos].rfind('\n')
                start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
                lines_total = code[:end_pos].count('\n')
                last_newline_end = code[:end_pos].rfind('\n')
                end_column = end_pos - last_newline_end - 1 if last_newline_end >= 0 else end_pos
                imports.append({'type': 'import', 'name': name, 'content': content, 'range': {'start': {'line': lines_before + 1, 'column': start_column}, 'end': {'line': lines_total + 1, 'column': end_column}}})
            return imports
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []
