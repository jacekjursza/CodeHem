from typing import Optional, List, Dict, Any
from codehem.core.engine.ast_handler import ASTHandler

import importlib

class CodeNodeWrapper:
    def __init__(self, ast_handler: ASTHandler, node, code_bytes: bytes, language_code: str, element_type: str = 'function'):
        self.ast_handler = ast_handler
        self.node = node
        self.code_bytes = code_bytes
        self.language_code = language_code
        self.element_type = element_type
        try:
            lang_module = importlib.import_module(f"codehem.languages.lang_{language_code}")
            node_config_map = getattr(lang_module, "NODE_CONFIG", {})
            self.config = node_config_map.get(element_type, {})
        except ModuleNotFoundError:
            self.config = {}

    def get_name(self) -> Optional[str]:
        name_field = self.config.get('name_field', 'name')
        name_node = self.ast_handler.find_child_by_field_name(self.node, name_field)
        if name_node:
            return self.ast_handler.get_node_text(name_node, self.code_bytes)
        return None

    def get_parameters(self, skip_self_or_cls=True) -> List[Dict[str, Any]]:
        params_field = self.config.get('parameters_field', 'parameters')
        params_node = self.ast_handler.find_child_by_field_name(self.node, params_field)
        if not params_node:
            params_node = self.ast_handler.find_child_by_field_name(self.node, 'parameter_list')  # fallback
            if not params_node:
                return []

        parameters = []
        for i in range(params_node.named_child_count):
            param_node = params_node.named_child(i)
            # Skip 'self' or 'cls' if expected
            if i == 0 and skip_self_or_cls:
                if param_node.type == 'identifier':
                    text = self.ast_handler.get_node_text(param_node, self.code_bytes)
                    if text in ('self', 'cls'):
                        continue
            param_info = self._extract_parameter(param_node)
            if param_info:
                parameters.append(param_info)
        return parameters

    def _extract_parameter(self, param_node) -> Optional[Dict[str, Any]]:
        param_info = {'name': None, 'type': None, 'default': None, 'optional': False}
        node_type = param_node.type
        ah = self.ast_handler

        if node_type == 'identifier':
            param_info['name'] = ah.get_node_text(param_node, self.code_bytes)

        elif node_type == 'typed_parameter':
            name_node = ah.find_child_by_field_name(param_node, 'name') or (param_node.child(0) if param_node.child_count > 0 else None)
            type_node = ah.find_child_by_field_name(param_node, 'type')
            if name_node:
                param_info['name'] = ah.get_node_text(name_node, self.code_bytes)
            if type_node:
                param_info['type'] = ah.get_node_text(type_node, self.code_bytes)

        elif node_type == 'default_parameter':
            name_node = ah.find_child_by_field_name(param_node, 'name')
            value_node = ah.find_child_by_field_name(param_node, 'value')
            if name_node:
                nested = self._extract_parameter(name_node)
                if nested:
                    param_info.update({k: nested.get(k) for k in ['name', 'type']})
            if value_node:
                param_info['default'] = ah.get_node_text(value_node, self.code_bytes)
                param_info['optional'] = True
            else:
                param_info['optional'] = True

        elif node_type == 'typed_default_parameter':
            name_node = ah.find_child_by_field_name(param_node, 'name')
            type_node = ah.find_child_by_field_name(param_node, 'type')
            value_node = ah.find_child_by_field_name(param_node, 'value')
            if name_node:
                param_info['name'] = ah.get_node_text(name_node, self.code_bytes)
            if type_node:
                param_info['type'] = ah.get_node_text(type_node, self.code_bytes)
            if value_node:
                param_info['default'] = ah.get_node_text(value_node, self.code_bytes)
                param_info['optional'] = True
            else:
                param_info['optional'] = True

        return param_info if param_info['name'] else None

    def get_body(self):
        body_field = self.config.get('body_field', 'body')
        return self.ast_handler.find_child_by_field_name(self.node, body_field)

    def get_decorators(self) -> List:
        decorators_field = self.config.get('decorators_field', 'decorators')
        decorators_node = self.ast_handler.find_child_by_field_name(self.node, decorators_field)
        if not decorators_node:
            return []
        return [decorators_node.named_child(i) for i in range(decorators_node.named_child_count)]

    def get_parent_class_name(self) -> Optional[str]:
        parent_type = self.config.get('parent_class_type', 'class_definition')
        parent_node = self.ast_handler.find_parent_of_type(self.node, parent_type)
        if not parent_node:
            return None
        name_node = self.ast_handler.find_child_by_field_name(parent_node, 'name')
        if name_node:
            return self.ast_handler.get_node_text(name_node, self.code_bytes)
        return None

    def get_return_info(self) -> Dict[str, Any]:
        ah = self.ast_handler
        function_node = self.node
        code_bytes = self.code_bytes

        return_type = None
        return_values = []

        return_type_node = ah.find_child_by_field_name(function_node, 'return_type')
        if return_type_node:
            return_type = ah.get_node_text(return_type_node, code_bytes)

        body_node = ah.find_child_by_field_name(function_node, 'body')
        if body_node:
            try:
                return_query_value = '(return_statement (_) @return_value)'
                return_query_empty = '(return_statement) @return_empty'

                return_value_results = ah.execute_query(return_query_value, body_node, code_bytes)
                return_empty_results = ah.execute_query(return_query_empty, body_node, code_bytes)

                processed_stmts = set()
                for node, capture_name in return_value_results:
                    if capture_name == 'return_value':
                        parent_stmt = node.parent
                        if parent_stmt and parent_stmt.type == 'return_statement' and parent_stmt.id not in processed_stmts:
                            if parent_stmt.named_child_count > 0:
                                return_values.append(ah.get_node_text(node, code_bytes))
                                processed_stmts.add(parent_stmt.id)
            except Exception:
                pass

        return {
            'return_type': return_type,
            'return_values': return_values
        }