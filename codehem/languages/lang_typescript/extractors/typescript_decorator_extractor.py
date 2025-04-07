import logging
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor
from codehem.core.engine.ast_handler import ASTHandler

logger = logging.getLogger(__name__)

@extractor
class TypeScriptDecoratorExtractor(TemplateExtractor):
    """ Extracts TypeScript/JavaScript decorators. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.DECORATOR

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Processes TreeSitter results for decorator nodes. """
        decorators = []
        processed_node_ids = set()
        logger.debug(f'TS Decorator Extractor: Processing {len(query_results)} captures.')

        for node, capture_name in query_results:
            decorator_node = None
            expression_node = None

            if capture_name == 'decorator_node' and node.type == 'decorator':
                 decorator_node = node
                 # The actual expression (identifier or call) is usually the first named child after '@'
                 if node.named_child_count > 0:
                      expression_node = node.named_child(0)
                 elif node.child_count > 1 and node.child(0).type == '@': # Handle cases where '@' is separate node
                     expression_node = node.child(1)

            elif capture_name == 'decorator_expression':
                 expression_node = node
                 # Need to find the parent 'decorator' node for full range/content
                 decorator_node = ast_handler.find_parent_of_type(node, 'decorator')
                 if not decorator_node:
                      logger.warning(f"Could not find parent 'decorator' node for expression capture: {ast_handler.get_node_text(node, code_bytes)}")
                      continue

            if decorator_node and decorator_node.id not in processed_node_ids:
                node_id = decorator_node.id
                content = ast_handler.get_node_text(decorator_node, code_bytes)
                name = None

                if expression_node:
                    if expression_node.type == 'identifier':
                         name = ast_handler.get_node_text(expression_node, code_bytes)
                    elif expression_node.type == 'call_expression':
                         func_node = expression_node.child_by_field_name('function')
                         if func_node and func_node.type == 'identifier':
                              name = ast_handler.get_node_text(func_node, code_bytes)
                         elif func_node: # Handle member expressions etc. if needed
                              name = ast_handler.get_node_text(func_node, code_bytes) # Fallback to full text
                    else: # Handle member expressions etc. directly if not a call
                         name = ast_handler.get_node_text(expression_node, code_bytes) # Fallback
                else:
                     # Fallback if expression node wasn't found easily
                     name = content.lstrip('@').split('(')[0].strip()
                     logger.warning(f"Using fallback name extraction for decorator: {name} from {content}")

                if not name: # If name extraction failed, use content as fallback
                    name = content

                start_point = decorator_node.start_point
                end_point = decorator_node.end_point

                # Try to determine parent element (class or method/property)
                parent_name = None
                parent_node = decorator_node.parent
                if parent_node:
                     # Common patterns: decorator -> export_statement -> class/func OR decorator -> class/method
                     target_node = None
                     if parent_node.type == 'export_statement':
                          target_node = parent_node.child_by_field_name('declaration')
                     elif parent_node.type in ['class_declaration', 'method_definition', 'public_field_definition', 'function_declaration']:
                           target_node = parent_node

                     if target_node:
                          target_name_node = ast_handler.find_child_by_field_name(target_node, 'name')
                          if target_name_node:
                               parent_name = ast_handler.get_node_text(target_name_node, code_bytes)
                               # If parent is a class member, find the class name
                               if target_node.type in ['method_definition', 'public_field_definition']:
                                   class_node = ast_handler.find_parent_of_type(target_node, 'class_declaration')
                                   if class_node:
                                       class_name_node = ast_handler.find_child_by_field_name(class_node, 'name')
                                       if class_name_node:
                                           parent_name = f"{ast_handler.get_node_text(class_name_node, code_bytes)}.{parent_name}"

                decorator_info = {
                    'type': CodeElementType.DECORATOR.value,
                    'name': name,
                    'content': content,
                    'range': {'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                              'end': {'line': end_point[0] + 1, 'column': end_point[1]}},
                    'parent_name': parent_name, # Store the associated element name if found
                    'node': decorator_node
                }
                decorators.append(decorator_info)
                processed_node_ids.add(node_id)
                logger.debug(f"TS Decorator Extractor: Processed decorator '{name}' attached to '{parent_name or 'Unknown'}'")

        logger.debug(f'TS Decorator Extractor: Finished processing. Found {len(decorators)} decorators.')
        return decorators

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        logger.warning("Regex fallback not implemented for TypeScriptDecoratorExtractor.")
        return []