# NEW FILE: Extractor for Python decorators
import logging
import re
from typing import List, Dict, Any, Tuple
from tree_sitter import Node # Import Node type hint
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
from codehem.core.engine.ast_handler import ASTHandler # Import ASTHandler for type hint

logger = logging.getLogger(__name__)

@extractor
class PythonDecoratorExtractor(TemplateExtractor):
    """ Extracts Python decorators. """
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.DECORATOR

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        decorators = []
        processed_node_ids = set()
        for node, capture_name in query_results:
            # Ensure we are processing the correct capture and haven't seen this node
            if capture_name == 'decorator_node' and node.id not in processed_node_ids:
                decorator_content = ast_handler.get_node_text(node, code_bytes)
                decorator_name = None
                # Logic to find the actual name node (identifier, attribute, or call)
                # Tree-sitter structure for decorator: (decorator '@' name_node)
                if node.child_count > 1:
                    name_node = node.child(1) # Node after '@'
                    node_type = name_node.type
                    if node_type == 'identifier':
                        decorator_name = ast_handler.get_node_text(name_node, code_bytes)
                    elif node_type == 'attribute':
                        # Handle object.attribute
                        obj_node = ast_handler.find_child_by_field_name(name_node, 'object')
                        attr_node = ast_handler.find_child_by_field_name(name_node, 'attribute')
                        if obj_node and attr_node:
                            decorator_name = f"{ast_handler.get_node_text(obj_node, code_bytes)}.{ast_handler.get_node_text(attr_node, code_bytes)}"
                        else:
                            decorator_name = ast_handler.get_node_text(name_node, code_bytes) # Fallback
                            logger.warning(f"Incomplete attribute node in decorator: {decorator_name}")
                    elif node_type == 'call':
                        # Handle @decorator() or @decorator(args) -> get the function part
                        func_node = ast_handler.find_child_by_field_name(name_node, 'function')
                        if func_node:
                            # Recursively get name if function itself is attribute/identifier
                            if func_node.type == 'identifier':
                                decorator_name = ast_handler.get_node_text(func_node, code_bytes)
                            elif func_node.type == 'attribute':
                                obj_node = ast_handler.find_child_by_field_name(func_node, 'object')
                                attr_node = ast_handler.find_child_by_field_name(func_node, 'attribute')
                                if obj_node and attr_node:
                                    decorator_name = f"{ast_handler.get_node_text(obj_node, code_bytes)}.{ast_handler.get_node_text(attr_node, code_bytes)}"
                                else:
                                     decorator_name = ast_handler.get_node_text(func_node, code_bytes) # Fallback
                            else:
                                decorator_name = ast_handler.get_node_text(func_node, code_bytes) # Fallback for other call types
                        else:
                            decorator_name = ast_handler.get_node_text(name_node, code_bytes) # Fallback
                            logger.warning(f"Could not find function node in decorator call: {decorator_name}")
                    else:
                        # Fallback for other unexpected structures
                        decorator_name = ast_handler.get_node_text(name_node, code_bytes)
                        logger.warning(f"Unexpected node type for decorator name: {node_type}")
                else:
                     # Basic fallback if structure is not '@' + name_node
                     decorator_name = decorator_content.lstrip('@').split('(')[0].strip()
                     logger.warning(f"Using basic fallback for decorator name: {decorator_name} from {decorator_content}")

                start_point = node.start_point
                end_point = node.end_point
                decorators.append({
                    'type': self.ELEMENT_TYPE.value,
                    'name': decorator_name or decorator_content, # Use content as fallback name
                    'content': decorator_content,
                    'range': {
                        'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                        'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                    }
                })
                processed_node_ids.add(node.id)
        return decorators

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        # Regex implementation based on DECORATOR_TEMPLATE placeholders
        decorators = []
        if not self.descriptor or not self.descriptor.regexp_pattern:
             logger.warning("Decorator regex pattern missing.")
             return []
        pattern = self.descriptor.regexp_pattern # Use formatted pattern from descriptor

        try:
            for match in re.finditer(pattern, code, re.MULTILINE):
                 try:
                     full_match = match.group(0)
                     # Group 1 should be QUALIFIED_NAME_PATTERN
                     name = match.group(1) if match.groups() else full_match.lstrip('@').split('(')[0].strip()
                     start_pos, end_pos = match.span()
                     start_line = code[:start_pos].count('\n') + 1
                     end_line = code[:end_pos].count('\n') + 1
                     decorators.append({
                         'type': self.ELEMENT_TYPE.value,
                         'name': name,
                         'content': full_match.strip(),
                         'range': {'start': {'line': start_line, 'column': 0}, 'end': {'line': end_line, 'column': 0}} # Regex range is approximate
                     })
                 except IndexError:
                     logger.warning(f"Regex decorator match failed to capture group: {match.group(0)}")
                 except Exception as e:
                     logger.error(f"Error processing regex decorator match: {e}", exc_info=True)
        except re.error as e:
            logger.error(f"Invalid regex pattern for decorators: {pattern}. Error: {e}")

        return decorators