"""
Template implementation for class extractor.
"""
import logging
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class TemplateClassExtractor(TemplateExtractor):
    """Template implementation for class extraction."""
    ELEMENT_TYPE = CodeElementType.CLASS

    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results for classes."""
        classes = []
        class_nodes = {}
        for node, capture_name in query_results:
            if capture_name == 'class_def':
                class_def = node
                name_node = ast_handler.find_child_by_field_name(class_def, 'name')
                if name_node:
                    class_name = ast_handler.get_node_text(name_node, code_bytes)
                    class_nodes[class_name] = class_def
            elif capture_name == 'class_name':
                class_name = ast_handler.get_node_text(node, code_bytes)
                parent_node = ast_handler.find_parent_of_type(node, 'class_definition')
                if parent_node:
                    class_nodes[class_name] = parent_node
        for class_name, class_def in class_nodes.items():
            content = ast_handler.get_node_text(class_def, code_bytes)
            decorators = ExtractorHelpers.extract_decorators(ast_handler, class_def, code_bytes)
            class_info = {'type': 'class', 'name': class_name, 'content': content, 'range': {'start': {'line': class_def.start_point[0] + 1, 'column': class_def.start_point[1]}, 'end': {'line': class_def.end_point[0] + 1, 'column': class_def.end_point[1]}}, 'decorators': decorators, 'members': {'methods': [], 'properties': [], 'static_properties': []}}
            classes.append(class_info)
        return classes

    def _process_regex_results(self, matches, code, context):
        """Process regex match results for classes."""
        classes = []
        for match in matches:
            name = match.group(1)
            content = match.group(0)
            start_pos = match.start()
            end_pos = match.end()
            lines_before = code[:start_pos].count('\n')
            last_newline = code[:start_pos].rfind('\n')
            start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
            lines_total = code[:end_pos].count('\n')
            last_newline_end = code[:end_pos].rfind('\n')
            end_column = end_pos - last_newline_end - 1 if last_newline_end >= 0 else end_pos
            decorators = []
            lines = code[:start_pos].splitlines()
            if lines:
                i = len(lines) - 1
                while i >= 0:
                    line = lines[i].strip()
                    if line.startswith('@'):
                        decorators.insert(0, {'name': line[1:].split('(')[0] if '(' in line else line[1:], 'content': line})
                    elif line and (not line.startswith('#')):
                        break
                    i -= 1
            class_info = {'type': 'class', 'name': name, 'content': content, 'range': {'start': {'line': lines_before + 1, 'column': start_column}, 'end': {'line': lines_total + 1, 'column': end_column}}, 'decorators': decorators, 'members': {'methods': [], 'properties': [], 'static_properties': []}}
            classes.append(class_info)
        return classes