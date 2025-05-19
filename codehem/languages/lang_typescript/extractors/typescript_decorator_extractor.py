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
                # Attempt to find the expression node within the decorator node
                if node.named_child_count > 0:
                    expression_node = node.named_child(0)
                elif node.child_count > 1 and node.child(0).type == '@':
                    expression_node = node.child(1) # Skip the '@' symbol
                else:
                     logger.warning(f"TS Decorator Extractor: Decorator node (ID: {node.id}) has unexpected structure, no clear expression found.")

            elif capture_name == 'decorator_expression':
                expression_node = node
                # Find the parent decorator node
                decorator_node = ast_handler.find_parent_of_type(node, 'decorator')
                if not decorator_node:
                    logger.warning(f"TS Decorator Extractor: Could not find parent 'decorator' node for expression capture: {ast_handler.get_node_text(node, code_bytes)}")
                    continue
            else:
                # Skip captures not relevant to this extractor
                continue

            if decorator_node and decorator_node.id not in processed_node_ids:
                node_id = decorator_node.id
                content = ast_handler.get_node_text(decorator_node, code_bytes)
                name = None

                # Extract name based on expression type (identifier or call_expression)
                if expression_node:
                    exp_type = expression_node.type
                    logger.debug(f"TS Decorator Extractor: Analyzing expression node type '{exp_type}' for decorator: {content}") # ADDED LOG
                    if exp_type == 'identifier':
                        name = ast_handler.get_node_text(expression_node, code_bytes)
                    elif exp_type == 'call_expression':
                        func_node = expression_node.child_by_field_name('function')
                        if func_node:
                            if func_node.type == 'identifier':
                                name = ast_handler.get_node_text(func_node, code_bytes)
                            else: # Handle member access like @Namespace.Decorator
                                name = ast_handler.get_node_text(func_node, code_bytes)
                        else:
                             logger.warning(f"TS Decorator Extractor: Decorator call expression missing function node: {content}")
                    else:
                        # Fallback for other potential expression types if needed
                        name = ast_handler.get_node_text(expression_node, code_bytes)
                        logger.warning(f"TS Decorator Extractor: Decorator expression has unexpected type '{exp_type}'. Using raw text: {name}")
                else:
                    # Fallback if expression node wasn't found directly
                    name = content.lstrip('@').split('(')[0].strip()
                    logger.warning(f'TS Decorator Extractor: Using fallback name extraction for decorator: {name} from {content}')

                if not name: name = content # Ensure name is never None

                start_point = decorator_node.start_point
                end_point = decorator_node.end_point

                # Try to find the decorated element to set parent_name
                parent_name = None
                actual_parent_node = decorator_node.parent
                decorated_node = None
                if actual_parent_node:
                     # Find the sibling node that is being decorated
                     dec_index = -1
                     for i, child in enumerate(actual_parent_node.children):
                         if child.id == decorator_node.id:
                             dec_index = i
                             break
                     # The decorated node is often the next named sibling after the last decorator
                     if dec_index != -1:
                        potential_target_node = None
                        for i in range(dec_index + 1, actual_parent_node.child_count):
                             sibling = actual_parent_node.child(i)
                             # Check if it's a meaningful node type (not comment, etc.)
                             if sibling.is_named:
                                 potential_target_node = sibling
                                 break
                        decorated_node = potential_target_node

                if decorated_node:
                    decorated_node_type = decorated_node.type
                    logger.debug(f"TS Decorator Extractor: Decorator '{name}' appears to decorate node type: {decorated_node_type}") # ADDED LOG
                    target_name_node = ast_handler.find_child_by_field_name(decorated_node, 'name')
                    if target_name_node:
                        parent_name = ast_handler.get_node_text(target_name_node, code_bytes)

                        # If the decorated element is a class member, prepend class name
                        if decorated_node_type in ['method_definition', 'public_field_definition']:
                            class_node = ast_handler.find_parent_of_type(decorated_node, 'class_declaration')
                            if class_node:
                                class_name_node = ast_handler.find_child_by_field_name(class_node, 'name')
                                if class_name_node:
                                    parent_name = f'{ast_handler.get_node_text(class_name_node, code_bytes)}.{parent_name}'
                else:
                     logger.warning(f"TS Decorator Extractor: Could not determine the parent element being decorated by '{name}'")

                decorator_info = {
                    'type': CodeElementType.DECORATOR.value,
                    'name': name,
                    'content': content,
                    'range': {
                        'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                        'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                    },
                    'parent_name': parent_name, # Store the potential parent name
                    'node': decorator_node # Keep node temporarily if needed
                }
                decorators.append(decorator_info)
                processed_node_ids.add(node_id)
                logger.debug(f"TS Decorator Extractor: Processed decorator '{name}' decorating '{parent_name or 'Unknown'}'")

        logger.debug(f'TS Decorator Extractor: Finished processing. Found {len(decorators)} decorators.')
        return decorators

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        logger.warning("Regex fallback not implemented for TypeScriptDecoratorExtractor.")
        return []