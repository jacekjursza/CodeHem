import logging
import re
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor
from codehem.core.engine.ast_handler import ASTHandler

logger = logging.getLogger(__name__)

@extractor
class TypeScriptStaticPropertyExtractor(TemplateExtractor):
    """ Extracts TypeScript/JavaScript static properties (static class fields). """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.STATIC_PROPERTY

    def _get_parent_class_name(self, node: Node, ast_handler: ASTHandler, code_bytes: bytes) -> Optional[str]:
        """ Finds the name of the containing class definition """
        container_node_types = ['class_declaration'] # Static props only in classes
        current_node = node.parent
        while current_node:
            if current_node.type in container_node_types:
                name_node = ast_handler.find_child_by_field_name(current_node, 'name')
                if name_node and name_node.type in ['type_identifier', 'identifier']:
                    return ast_handler.get_node_text(name_node, code_bytes)
                return f"Class_{current_node.type}" # Placeholder
            if current_node.type == 'program': break
            current_node = current_node.parent
        return None

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Processes TreeSitter results for static property definitions. """
        properties = []
        processed_node_ids = set()
        logger.debug(f'TS Static Property Extractor: Processing {len(query_results)} captures.')

        # Use a map to collect info based on definition node ID
        node_map: Dict[int, Dict[str, Any]] = {}

        for node, capture_name in query_results:
            definition_node = None
            # Identify the core definition node based on captures
            if capture_name == 'property_def': # Using the same query as regular property for now
                 if node.type == 'public_field_definition':
                     # Check if 'static' modifier is present
                     is_static = False
                     for child in node.children:
                          if child.type == 'static':
                              is_static = True
                              break
                     if is_static:
                          definition_node = node
                     else: continue # Skip non-static fields
                 # Handle export statement case
                 elif node.type == 'export_statement':
                     decl = node.child_by_field_name('declaration')
                     if decl and decl.type == 'public_field_definition':
                          is_static = False
                          for child in decl.children:
                              if child.type == 'static':
                                  is_static = True
                                  break
                          if is_static:
                              definition_node = decl
                          else: continue
                     else: continue
                 else:
                     logger.warning(f"Capture 'property_def' on unexpected node type for static: {node.type}")
                     continue
            elif capture_name in ['property_name', 'type', 'value']:
                 parent_def = ast_handler.find_parent_of_type(node, 'public_field_definition')
                 if parent_def:
                      is_static = False
                      for child in parent_def.children:
                           if child.type == 'static':
                               is_static = True
                               break
                      if is_static:
                          definition_node = parent_def
                      else: continue # Skip if name/type/value is not part of a static definition
                 else:
                     # Check if part of exported static definition
                     parent_export = ast_handler.find_parent_of_type(node, 'export_statement')
                     if parent_export:
                         decl = parent_export.child_by_field_name('declaration')
                         if decl and decl.type == 'public_field_definition':
                             is_static = False
                             for child in decl.children:
                                 if child.type == 'static':
                                     is_static = True
                                     break
                             if is_static:
                                 parent_def_check = ast_handler.find_parent_of_type(node, 'public_field_definition')
                                 if parent_def_check == decl:
                                     definition_node = decl
                                 else: continue
                             else: continue
                         else: continue
                     else: continue # Skip if not part of a valid definition

            if definition_node:
                node_id = definition_node.id
                if node_id not in processed_node_ids:
                     if node_id not in node_map:
                         class_name = self._get_parent_class_name(definition_node, ast_handler, code_bytes)
                         if class_name:
                              node_map[node_id] = {'definition_node': definition_node, 'class_name': class_name, 'node_for_range': definition_node}
                              # Adjust range node if exported
                              parent_export = ast_handler.find_parent_of_type(definition_node, 'export_statement')
                              if parent_export and parent_export.child_by_field_name('declaration') == definition_node:
                                  node_map[node_id]['node_for_range'] = parent_export
                         else:
                              processed_node_ids.add(node_id) # Skip if not in class
                              continue

                     # Store related nodes
                     if node_id in node_map:
                          if capture_name == 'property_name':
                              node_map[node_id]['name_node'] = node
                          elif capture_name == 'type':
                              node_map[node_id]['type_node'] = node
                          elif capture_name == 'value':
                              node_map[node_id]['value_node'] = node

        # Process the collected information
        for node_id, data in node_map.items():
            if node_id in processed_node_ids: continue

            definition_node = data['definition_node']
            class_name = data['class_name']
            node_for_range = data['node_for_range']

            name_node = data.get('name_node') or ast_handler.find_child_by_field_name(definition_node, 'name')
            type_node = data.get('type_node') or ast_handler.find_child_by_field_name(definition_node, 'type')
            value_node = data.get('value_node') or ast_handler.find_child_by_field_name(definition_node, 'value')

            if not name_node:
                logger.warning(f"Could not find name node for static property definition node id {node_id}")
                processed_node_ids.add(node_id)
                continue

            prop_name = ast_handler.get_node_text(name_node, code_bytes)
            prop_type = ast_handler.get_node_text(type_node, code_bytes) if type_node else None
            prop_value = ast_handler.get_node_text(value_node, code_bytes) if value_node else None
            content = ast_handler.get_node_text(node_for_range, code_bytes)

            if prop_type and isinstance(prop_type, str) and prop_type.startswith(':'):
                 prop_type = prop_type[1:].strip()

            start_point = node_for_range.start_point
            end_point = node_for_range.end_point

            decorators = ExtractorHelpers.extract_decorators(ast_handler, definition_node, code_bytes)

            prop_info = {
                'type': CodeElementType.STATIC_PROPERTY.value,
                'name': prop_name,
                'content': content,
                'class_name': class_name,
                'range': {'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                          'end': {'line': end_point[0] + 1, 'column': end_point[1]}},
                'value_type': prop_type,
                'additional_data': {'value': prop_value} if prop_value else {},
                'decorators': decorators,
                'node': definition_node
            }
            properties.append(prop_info)
            processed_node_ids.add(node_id)
            logger.debug(f"TS Static Property Extractor: Processed '{class_name}.{prop_name}'")

        logger.debug(f'TS Static Property Extractor: Finished processing. Found {len(properties)} static properties.')
        return properties

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        """ Regex fallback for static properties. """
        logger.warning("Regex fallback used for TypeScriptStaticPropertyExtractor.")
        # This regex is basic and might miss cases or have false positives
        pattern = self.descriptor.regexp_pattern if self.descriptor else None
        if not pattern:
            pattern = r"(?:^|\n)\s*static\s+(?:readonly\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)(?:\s*:\s*[\w.<>|&\[\]\s]+)?\s*=\s*(.+?)(?:;|$)"

        properties = []
        class_name_context = context.get('class_name') if context else None
        try:
            for match in re.finditer(pattern, code, re.MULTILINE):
                 prop_name = match.group(1)
                 prop_value = match.group(2).strip()
                 content = match.group(0)
                 start_pos, end_pos = match.span()
                 start_line = code[:start_pos].count('\n') + 1
                 end_line = start_line + content.count('\n')

                 prop_info = {
                      'type': CodeElementType.STATIC_PROPERTY.value,
                      'name': prop_name,
                      'content': content.strip(),
                      'class_name': class_name_context,
                      'range': {'start': {'line': start_line, 'column': 0},
                                'end': {'line': end_line, 'column': len(content.splitlines()[-1])}},
                      'value_type': None, # Regex cannot reliably determine type
                      'additional_data': {'value': prop_value},
                      'decorators': [] # Regex cannot reliably get decorators
                 }
                 properties.append(prop_info)
        except Exception as e:
            logger.error(f"Error during regex static property extraction: {e}", exc_info=False)

        return properties