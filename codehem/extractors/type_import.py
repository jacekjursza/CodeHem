"""
Import extractor that uses language-specific handlers.
"""
from typing import Dict, List, Optional, Any
import re
import logging
from codehem.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler
from codehem.core.registry import extractor

logger = logging.getLogger(__name__)

@extractor
class ImportExtractor(BaseExtractor):
    """Import extractor using language-specific handlers."""

    @property
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""
        return CodeElementType.IMPORT

    def supports_language(self, language_code: str) -> bool:
        """Check if this extractor supports the given language."""
        return language_code.lower() in self.handlers

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Extract imports from the provided code.
        
        Args:
            code: The source code to extract from
            context: Optional context information for the extraction
            
        Returns:
            List of extracted imports as dictionaries
        """
        context = context or {}
        language_code = context.get('language_code', 'python').lower()
        if not self.supports_language(language_code):
            return []
        handler = self.handlers[language_code]
        if handler.custom_extract:
            return handler.extract(code, context)
        
        # First try with tree-sitter
        imports = []
        if handler.tree_sitter_query:
            imports = self._extract_with_tree_sitter(code, handler, context)
            
        # If no imports found with tree-sitter, try with regex
        if not imports and handler.regexp_pattern:
            imports = self._extract_with_regex(code, handler, context)
            
        # If we found individual imports, combine them into one block for easier manipulation
        if imports:
            # Sort imports to ensure consistent order
            imports.sort(key=lambda x: x.get('range', {}).get('start', {}).get('line', 0))
            
            # Get the full import section from the first to the last import
            first_import = imports[0]
            last_import = imports[-1]
            first_line = first_import['range']['start']['line']
            last_line = last_import['range']['end']['line']
            
            # Extract the entire import section
            code_lines = code.splitlines()
            import_section = '\n'.join(code_lines[first_line:last_line+1])
            
            # Create a combined import entry
            combined_import = {
                'type': 'import',
                'name': 'imports',  # Generic name for the import section
                'content': import_section,
                'range': {
                    'start': {'line': first_line, 'column': first_import['range']['start']['column']},
                    'end': {'line': last_line, 'column': last_import['range']['end']['column']}
                }
            }
            
            return [combined_import]
        
        return []

    def _extract_with_tree_sitter(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract imports using TreeSitter."""
        ast_handler = self._get_ast_handler(handler.language_code)
        if not ast_handler:
            return []
        try:
            (tree, code_bytes) = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, tree, code_bytes)
            imports = []
            for match in query_results:
                import_node = None
                for (node, node_type) in match:
                    if node_type in ('import', 'import_from'):
                        import_node = node
                        break
                
                if import_node:
                    content = ast_handler.get_node_text(import_node, code_bytes)
                    
                    # Try to extract the module name
                    name = "import"  # Default generic name
                    if 'from ' in content:
                        # Extract module from "from X import Y"
                        try:
                            name = re.search(r'from\s+([^\s]+)', content).group(1)
                        except:
                            pass
                    elif 'import ' in content:
                        # Extract module from "import X"
                        try:
                            name = re.search(r'import\s+([^\s]+)', content).group(1)
                        except:
                            pass
                    
                    imports.append({
                        'type': 'import',
                        'name': name,
                        'content': content,
                        'range': {
                            'start': {'line': import_node.start_point[0], 'column': import_node.start_point[1]},
                            'end': {'line': import_node.end_point[0], 'column': import_node.end_point[1]}
                        }
                    })
            return imports
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {e}')
            return []

    def _extract_with_regex(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract imports using regex."""
        try:
            pattern = handler.regexp_pattern
            matches = re.finditer(pattern, code, re.DOTALL|re.MULTILINE)
            imports = []
            for match in matches:
                content = match.group(0)
                
                # Try to extract a name for the import
                name = "import"  # Default generic name
                if match.groups():
                    name = match.group(1) if match.group(1) else match.group(2) if len(match.groups()) > 1 else "import"
                
                start_pos = match.start()
                end_pos = match.end()
                lines_before = code[:start_pos].count('\n')
                last_newline = code[:start_pos].rfind('\n')
                start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
                lines_total = code[:end_pos].count('\n')
                last_newline_end = code[:end_pos].rfind('\n')
                end_column = end_pos - last_newline_end - 1 if last_newline_end >= 0 else end_pos
                
                imports.append({
                    'type': 'import',
                    'name': name,
                    'content': content,
                    'range': {
                        'start': {'line': lines_before, 'column': start_column},
                        'end': {'line': lines_total, 'column': end_column}
                    }
                })
            return imports
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []