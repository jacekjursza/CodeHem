"""
Function extractor that uses language-specific handlers.
"""
from typing import Dict, List, Any
import re
import logging
from codehem.core.extractors.base import BaseExtractor
from codehem.core.extractors.extraction_base import ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class FunctionExtractor(BaseExtractor):
    """Function extractor using language-specific handlers."""
    ELEMENT_TYPE = CodeElementType.FUNCTION

    @property
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""

        return self.ELEMENT_TYPE

    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract using TreeSitter first, fall back to regex if needed."""
        if handler.tree_sitter_query:
            functions = self._extract_with_tree_sitter(code, handler, context)
            if functions:
                return functions
        if handler.regexp_pattern:
            return self._extract_with_regex(code, handler, context)
        return []

    def _extract_with_tree_sitter(
        self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]
    ) -> List[Dict]:
        """Extract functions using TreeSitter.
        [MODIFIED V2: Correctly capture full range including decorators and body]"""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            return []
        try:
            root, code_bytes = ast_handler.parse(code)
            # Use the function definition query provided by the handler
            query_results = ast_handler.execute_query(
                handler.tree_sitter_query, root, code_bytes
            )
            functions = []
            processed_node_ids = set()

            for node, capture_name in query_results:
                definition_node = None
                node_for_content_start = (
                    None  # Node representing the absolute start (incl. decorators)
                )
                node_for_content_end = None  # Node representing the absolute end

                # Identify the core function_definition node
                if capture_name == "function_def":
                    # Ensure it's actually a function definition node type
                    if node.type == "function_definition":
                        definition_node = node
                    else:
                        logger.warning(
                            f"Node captured as 'function_def' has unexpected type: {node.type}"
                        )
                        continue
                elif capture_name == "function_name":
                    parent_def = ast_handler.find_parent_of_type(
                        node, "function_definition"
                    )
                    if parent_def:
                        definition_node = parent_def
                    else:
                        continue  # Name outside a function def

                if definition_node and definition_node.id not in processed_node_ids:
                    # --- Check if it's inside a class (skip methods) ---
                    parent_class = ast_handler.find_parent_of_type(
                        definition_node, "class_definition"
                    )
                    if parent_class:
                        # logger.debug(f"Skipping node {definition_node.id} (function query); it's inside a class.")
                        processed_node_ids.add(definition_node.id)
                        continue
                    # --- End Class Check ---

                    # Determine the full range node
                    node_for_range = definition_node
                    parent_node = definition_node.parent
                    if parent_node and parent_node.type == "decorated_definition":
                        node_for_range = parent_node  # decorated_definition covers decorators + function_definition

                    # Extract common info using the core definition node
                    from codehem.core.engine.code_node_wrapper import CodeNodeWrapper

                    wrapper = CodeNodeWrapper(
                        ast_handler,
                        definition_node,
                        code_bytes,
                        language_code=self.language_code,
                        element_type="function",
                    )
                    func_name = wrapper.get_name()
                    if not func_name:
                        logger.warning(
                            f"Could not extract name for function node id {definition_node.id}"
                        )
                        processed_node_ids.add(definition_node.id)
                        continue

                    # Get full content and precise range using the node_for_range
                    content = ast_handler.get_node_text(node_for_range, code_bytes)
                    start_point = node_for_range.start_point
                    end_point = node_for_range.end_point

                    # Extract other details
                    parameters = wrapper.get_parameters(skip_self_or_cls=False)
                    return_info = wrapper.get_return_info()
                    # Use helper for decorators based on the definition_node's parent context
                    decorators_raw = ExtractorHelpers.extract_decorators(
                        ast_handler, definition_node, code_bytes
                    )

                    functions.append(
                        {
                            "type": CodeElementType.FUNCTION.value,  # Use enum value
                            "name": func_name,
                            "content": content,  # Full content
                            "range": {
                                "start": {
                                    "line": start_point[0] + 1,
                                    "column": start_point[1],
                                },
                                "end": {
                                    "line": end_point[0] + 1,
                                    "column": end_point[1],
                                },
                            },
                            "parameters": parameters,
                            "return_info": return_info,
                            "decorators": decorators_raw,
                            # Keep definition start line for reference if needed
                            "definition_start_line": definition_node.start_point[0] + 1,
                        }
                    )
                    processed_node_ids.add(definition_node.id)  # Mark as processed

            return functions
        except Exception as e:
            logger.error(
                f"TreeSitter extraction error in FunctionExtractor: {str(e)}",
                exc_info=True,
            )
            return []

    def _extract_parameters(self, function_node, code_bytes, ast_handler) -> List[Dict]:
        """
        Extract detailed parameter information from a function.
        
        Args:
            function_node: Function node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            List of parameter dictionaries with name, type, and default value
        """
        parameters = []
        params_node = None
        for child_idx in range(function_node.named_child_count):
            child = function_node.named_child(child_idx)
            if child.type == 'parameters':
                params_node = child
                break
        if not params_node:
            return parameters
        for child_idx in range(params_node.named_child_count):
            child = params_node.named_child(child_idx)
            if child.type == 'identifier':
                name = ast_handler.get_node_text(child, code_bytes)
                parameters.append({'name': name, 'type': None})
            elif child.type == 'typed_parameter':
                name_node = child.child_by_field_name('name')
                type_node = child.child_by_field_name('type')
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    param_dict = {'name': name, 'type': None}
                    if type_node:
                        param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                    parameters.append(param_dict)
            elif child.type == 'default_parameter':
                name_node = child.child_by_field_name('name')
                value_node = child.child_by_field_name('value')
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    param_dict = {'name': name, 'type': None, 'optional': True}
                    if value_node:
                        param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                    parameters.append(param_dict)
            elif child.type == 'typed_default_parameter':
                name_node = child.child_by_field_name('name')
                type_node = child.child_by_field_name('type')
                value_node = child.child_by_field_name('value')
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    param_dict = {'name': name, 'type': None, 'optional': True}
                    if type_node:
                        param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                    if value_node:
                        param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                    parameters.append(param_dict)
        return parameters

    def _extract_return_info(self, function_node, code_bytes, ast_handler) -> Dict:
        """
        Extract return type information from a function.
        
        Args:
            function_node: Function node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            Dictionary with return_type and return_values
        """
        return_type = None
        return_values = []
        return_type_node = function_node.child_by_field_name('return_type')
        if return_type_node:
            return_type = ast_handler.get_node_text(return_type_node, code_bytes)
        body_node = function_node.child_by_field_name('body')
        if body_node:
            try:
                return_query = '(return_statement (_) @return_value)'
                return_results = ast_handler.execute_query(return_query, body_node, code_bytes)
                for (node, capture_name) in return_results:
                    if capture_name == 'return_value':
                        return_values.append(ast_handler.get_node_text(node, code_bytes))
            except Exception as e:
                try:
                    alt_query = '(return_statement) @return_stmt'
                    return_stmts = ast_handler.execute_query(alt_query, body_node, code_bytes)
                    for (node, capture_name) in return_stmts:
                        if capture_name == 'return_stmt':
                            stmt_text = ast_handler.get_node_text(node, code_bytes)
                            if stmt_text.startswith('return '):
                                return_values.append(stmt_text[7:].strip())
                except Exception:
                    function_text = ast_handler.get_node_text(function_node, code_bytes)
                    return_regex = 'return\\s+(.+?)(?:\\n|$)'
                    for match in re.finditer(return_regex, function_text):
                        return_values.append(match.group(1).strip())
        return {'return_type': return_type, 'return_values': return_values}

    def _extract_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract functions using regex."""
        try:
            pattern = handler.regexp_pattern
            matches = re.finditer(pattern, code, re.DOTALL)
            functions = []
            for match in matches:
                name = match.group(1)
                signature = match.group(0)
                start_pos = match.start()
                sig_end_pos = match.end()

                # Get the indentation level of the function definition
                code_lines = code.splitlines()
                func_line_num = code[:start_pos].count('\n')
                func_indent = self.get_indentation(signature) if signature.startswith(' ') else ''

                # Parse the function body based on indentation
                content_lines = [signature]

                # Find the end of the function by analyzing indentation
                function_end_line = func_line_num
                for i, line in enumerate(code_lines[func_line_num + 1:], func_line_num + 1):
                    line_indent = self.get_indentation(line)
                    # Skip empty lines
                    if not line.strip():
                        content_lines.append(line)
                        continue

                    # If indentation is less than or equal to function indentation and not an empty line,
                    # we've exited the function
                    if len(line_indent) <= len(func_indent):
                        break

                    # Still in the function body
                    content_lines.append(line)
                    function_end_line = i

                # Combine the function signature and body
                content = '\n'.join(content_lines)

                # Calculate start line (1-indexed)
                start_line = func_line_num + 1

                # Calculate end line (1-indexed)
                end_line = function_end_line + 1

                # Get column positions
                last_newline = code[:start_pos].rfind('\n')
                start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
                end_column = len(code_lines[function_end_line]) if function_end_line < len(code_lines) else 0

                # Extract parameters
                param_pattern = 'def\\s+\\w+\\s*\\((.*?)\\)'
                param_match = re.search(param_pattern, content)
                parameters = []
                if param_match:
                    params_str = param_match.group(1)
                    param_list = [p.strip() for p in params_str.split(',') if p.strip()]
                    for param in param_list:
                        param_dict = {'name': param, 'type': None}
                        if ':' in param:
                            name_part, type_part = param.split(':', 1)
                            param_dict['name'] = name_part.strip()
                            param_dict['type'] = type_part.strip()
                        if '=' in param_dict['name']:
                            name_part, value_part = param_dict['name'].split('=', 1)
                            param_dict['name'] = name_part.strip()
                            param_dict['default'] = value_part.strip()
                            param_dict['optional'] = True
                        parameters.append(param_dict)

                # Extract return information correctly from the function body only
                return_info = {'return_type': None, 'return_values': []}
                return_type_pattern = 'def\\s+\\w+\\s*\\([^)]*\\)\\s*->\\s*([^:]+):'
                return_type_match = re.search(return_type_pattern, content)
                if return_type_match:
                    return_info['return_type'] = return_type_match.group(1).strip()

                return_pattern = 'return\\s+([^\\n;]+)'
                return_matches = re.finditer(return_pattern, content)
                for return_match in return_matches:
                    return_info['return_values'].append(return_match.group(1).strip())

                # Create function info with correct boundaries
                functions.append({
                    'type': 'function', 
                    'name': name, 
                    'content': content, 
                    'range': {
                        'start': {'line': start_line, 'column': start_column}, 
                        'end': {'line': end_line, 'column': end_column}
                    }, 
                    'parameters': parameters, 
                    'return_info': return_info
                })
            return functions
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []

    def _get_class_name_from_node(self, class_node, ast_handler, code_bytes):
        name_node = ast_handler.find_child_by_field_name(class_node, 'name')
        if name_node:
            return ast_handler.get_node_text(name_node, code_bytes)
        return "UnnamedClass?"