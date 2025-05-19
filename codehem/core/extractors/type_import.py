"""
Import extractor that uses language-specific handlers.
"""
import sys # Added missing import
from tree_sitter import QueryError # Added missing import
from typing import Dict, List, Any
import re
import logging
from codehem.core.extractors.base import BaseExtractor
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
        tree_sitter_attempted = False
        tree_sitter_error = False

        if handler.tree_sitter_query:
            tree_sitter_attempted = True
            try:
                imports = self._extract_with_tree_sitter(code, handler, context)
            except QueryError as qe:
                 logger.error(f"TreeSitter query failed for imports in {self.language_code}: {qe}")
                 tree_sitter_error = True
                 imports = [] # Ensure imports is empty on error
            except Exception as e:
                 logger.error(f"Unexpected error during TreeSitter import extraction in {self.language_code}: {e}", exc_info=True)
                 tree_sitter_error = True
                 imports = [] # Ensure imports is empty on error

        if not imports and handler.regexp_pattern and (not tree_sitter_attempted or tree_sitter_error):
            # Only fallback if TS wasn't attempted, failed, or returned nothing
            logger.debug(f"Using Regex fallback for imports in {self.language_code}.")
            imports = self._extract_with_regex(code, handler, context)

        # Consolidate individual imports into one 'imports' block AFTER extraction
        if imports:
            try:
                imports.sort(key=lambda x: x.get('range', {}).get('start', {}).get('line', float('inf')))
                first_import = imports[0]
                last_import = imports[-1]
                first_line = first_import['range']['start']['line']
                last_line = last_import['range']['end']['line']

                # Recalculate combined content directly from original code lines
                code_lines = code.splitlines()
                # Ensure line numbers are within bounds
                start_idx = max(0, first_line - 1)
                end_idx = min(len(code_lines), last_line) # Use last_line directly as splitlines index is 0-based end
                if start_idx < end_idx:
                     import_section = '\n'.join(code_lines[start_idx:end_idx])
                else:
                     logger.warning(f"Invalid line range calculated for combined import section: {start_idx}-{end_idx}. Using first import content.")
                     import_section = first_import.get('content', '')

                combined_import = {
                    'type': CodeElementType.IMPORT.value,
                    'name': 'imports', # Standardized name for the combined block
                    'content': import_section,
                    'range': {
                        'start': first_import['range']['start'],
                        'end': last_import['range']['end']
                    },
                    'additional_data': {'individual_imports': imports} # Keep original data if needed
                }
                return [combined_import] # Return list with ONE combined element
            except Exception as e:
                logger.error(f"Error consolidating import elements: {e}", exc_info=True)
                # Fallback to returning individual imports if consolidation fails
                return imports

        return [] # Return empty list if no imports found by either method

    def _extract_with_tree_sitter(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract imports using TreeSitter."""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            logger.error("ImportExtractor: ERROR - No AST handler available.")
            return []

        imports = []
        processed_node_ids = set()
        # Removed print statements and rely on QueryError import
        # try/except block moved to _extract_with_patterns
        root, code_bytes = ast_handler.parse(code)
        logger.debug(f"ImportExtractor: Executing TreeSitter query: {repr(handler.tree_sitter_query)}")
        query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
        logger.debug(f"ImportExtractor: TreeSitter query returned {len(query_results)} captures.")

        for node, capture_name in query_results:
            node_id = node.id
            if node_id in processed_node_ids:
                continue

            if capture_name in ('import_simple', 'import_from'):
                node_type = node.type
                if node_type not in ('import_statement', 'import_from_statement'):
                    logger.warning(f"ImportExtractor: Captured node via '{capture_name}' has unexpected type '{node_type}'. Skipping.")
                    continue

                content = ast_handler.get_node_text(node, code_bytes)
                name = 'import' # Default
                try:
                    if node_type == 'import_from_statement':
                        module_node = node.child_by_field_name('module_name')
                        if module_node:
                            name = ast_handler.get_node_text(module_node, code_bytes)
                except Exception as e:
                    logger.warning(f"ImportExtractor: Error deriving name for import content '{content[:50]}...': {e}")

                start_point = node.start_point
                end_point = node.end_point
                import_data = {
                    'type': CodeElementType.IMPORT.value,
                    'name': name,
                    'content': content,
                    'range': {
                        'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                        'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                    }
                }
                imports.append(import_data)
                processed_node_ids.add(node_id)
                logger.debug(f"ImportExtractor: Extracted individual import: {import_data['name']} at line {import_data['range']['start']['line']}")
            else:
                logger.debug(f"ImportExtractor: Skipping capture '{capture_name}' with node type '{node.type}'")

        logger.debug(f"ImportExtractor: Finished TreeSitter processing, found {len(imports)} individual imports.")
        return imports

    def _extract_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract imports using regex."""
        pattern = handler.regexp_pattern
        if not pattern:
             logger.warning("Import regex pattern is missing.")
             return []
        try:
            matches = re.finditer(pattern, code, re.MULTILINE)
        except re.error as e:
            logger.error(f"Invalid regex pattern for imports: {pattern}. Error: {e}")
            return []

        imports = []
        for match in matches:
            content = match.group(0).strip() # Get the whole match and strip whitespace
            name = 'import' # Default name
            try:
                 # Try to get a more specific name (e.g., the module)
                 if content.startswith('from '):
                     name_match = re.search(r'from\s+([a-zA-Z0-9_.]+)', content)
                     if name_match:
                         name = name_match.group(1)
                 elif content.startswith('import '):
                     # For 'import a, b, c' take the first module name
                     name_match = re.search(r'import\s+([a-zA-Z0-9_.]+)', content)
                     if name_match:
                         name = name_match.group(1)
            except Exception as e:
                 logger.warning(f"Failed to parse name from regex import content: '{content}'. Error: {e}")

            start_pos = match.start()
            end_pos = match.end()
            # Calculate accurate line/column numbers
            lines_before = code[:start_pos].count('\n')
            last_newline_before = code[:start_pos].rfind('\n')
            start_column = start_pos - (last_newline_before + 1) if last_newline_before != -1 else start_pos

            lines_in_match = content.count('\n')
            end_line = lines_before + 1 + lines_in_match
            last_newline_in_match = content.rfind('\n')
            if last_newline_in_match != -1:
                 end_column = len(content) - (last_newline_in_match + 1)
            else: # Single line match
                 end_column = start_column + len(content)

            imports.append({
                'type': CodeElementType.IMPORT.value,
                'name': name,
                'content': content,
                'range': {
                    'start': {'line': lines_before + 1, 'column': start_column},
                    'end': {'line': end_line, 'column': end_column}
                }
            })
        return imports