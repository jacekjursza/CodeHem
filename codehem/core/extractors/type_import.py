"""
Import extractor that uses language-specific handlers.
"""
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
        """Extract imports using TreeSitter. [Added Print Logging]"""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            # Use print for visibility with pytest -s
            print("ImportExtractor: ERROR - No AST handler available.", file=sys.stderr)
            return []
        imports = []
        processed_node_ids = set()
        try:
            root, code_bytes = ast_handler.parse(code)
            print(f"ImportExtractor: DEBUG - Executing TreeSitter query: {repr(handler.tree_sitter_query)}", file=sys.stderr)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
            print(f"ImportExtractor: DEBUG - TreeSitter query returned {len(query_results)} captures.", file=sys.stderr)

            for node, capture_name in query_results:
                 # Use node.id directly as the key identifier
                 node_id = node.id
                 if node_id in processed_node_ids:
                      continue

                 # Check if the capture name matches expected captures from the query
                 if capture_name in ('import_simple', 'import_from'):
                    node_type = node.type # Check the actual node type
                    if node_type not in ('import_statement', 'import_from_statement'):
                         print(f"ImportExtractor: WARNING - Captured node via '{capture_name}' has unexpected type '{node_type}'. Skipping.", file=sys.stderr)
                         continue # Skip if the node type doesn't match the capture name intent

                    content = ast_handler.get_node_text(node, code_bytes)
                    name = 'import' # Default
                    try:
                        if node_type == 'import_from_statement':
                            module_node = node.child_by_field_name('module_name')
                            if module_node:
                                 name = ast_handler.get_node_text(module_node, code_bytes)
                        # Keep name = 'import' for simple import_statement for simplicity
                    except Exception as e:
                        print(f"ImportExtractor: WARNING - Error deriving name for import content '{content[:50]}...': {e}", file=sys.stderr)

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
                    print(f"ImportExtractor: DEBUG - Extracted individual import: {import_data['name']} at line {import_data['range']['start']['line']}", file=sys.stderr)
                 else:
                     print(f"ImportExtractor: DEBUG - Skipping capture '{capture_name}' with node type '{node.type}'", file=sys.stderr)

            print(f"ImportExtractor: DEBUG - Finished TreeSitter processing, found {len(imports)} individual imports.", file=sys.stderr)
            return imports
        except QueryError as qe:
             # Make QueryError visible
             print(f"ImportExtractor: ERROR - TreeSitter Query FAILED with QueryError: {qe}", file=sys.stderr)
             print(f"  Error Type: {qe.error_type}", file=sys.stderr)
             print(f"  Offset: {qe.offset}", file=sys.stderr)
             print(f"  Row: {qe.row}", file=sys.stderr)
             print(f"  Column: {qe.column}", file=sys.stderr)
             return []
        except Exception as e:
            print(f'ImportExtractor: ERROR - Unexpected error during TreeSitter execution: {e}', file=sys.stderr)
            # Optionally print traceback for unexpected errors:
            # import traceback
            # traceback.print_exc(file=sys.stderr)
            return []

    def _extract_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract imports using regex."""
        pattern = handler.regexp_pattern
        matches = re.finditer(pattern, code, re.MULTILINE)
        imports = []
        for match in matches:
            content = match.group(0)
            name = 'import'
            if content.startswith('from '):
                try:
                    name = re.search('from\\s+([^\\s]+)', content).group(1)
                except Exception as e:
                    logger.warning(f"Failed to parse 'from' import name in content: '{content}'. Error: {e}")
                    raise
            elif content.startswith('import '):
                try:
                    name = re.search('import\\s+([^\\s]+)', content).group(1)
                except Exception as e:
                    logger.warning(f"Failed to parse 'import' name in content: '{content}'. Error: {e}")
                    raise
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
