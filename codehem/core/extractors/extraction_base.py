# Content of codehem\core\extractors\extraction_base.py
import logging
import re
from typing import Dict, List, Any, Optional, Union
from codehem.core.engine.ast_handler import ASTHandler
from codehem.core.engine.languages import LANGUAGES, get_parser
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType
from abc import ABC, abstractmethod
# Removed QueryError import as it's handled lower down

logger = logging.getLogger(__name__)

class ExtractorHelpers:
    """Common utilities for extraction."""

    @staticmethod
    def extract_parameters(ast_handler, node, code_bytes, is_self_or_this=True):
        """Extract parameters from a function/method node."""
        parameters = []
        params_node = ast_handler.find_child_by_field_name(node, 'parameters')
        if not params_node:
            params_node = ast_handler.find_child_by_field_name(node, 'parameter_list')
            if not params_node:
                # logger.debug(f"Could not find 'parameters' or 'parameter_list' node for node id {node.id}")
                return parameters
        for i in range(params_node.named_child_count):
            param_node = params_node.named_child(i)
            if i == 0 and is_self_or_this:
                if param_node.type == 'identifier':
                    first_param_text = ast_handler.get_node_text(param_node, code_bytes)
                    if first_param_text in ['self', 'cls', 'this']:
                        # logger.debug(f"  Skipping first parameter '{first_param_text}'.")
                        continue
            param_info = ExtractorHelpers.extract_parameter(ast_handler, param_node, code_bytes)
            if param_info:
                parameters.append(param_info)
        return parameters

    @staticmethod
    def extract_parameter(ast_handler: ASTHandler, param_node, code_bytes) -> Optional[Dict[str, Any]]:
        """
        Extract information about a single parameter, handling different node types.
        Returns a dictionary with 'name', 'type', 'default', 'optional'.
        """
        param_info = {'name': None, 'type': None, 'default': None, 'optional': False}
        node_type = param_node.type
        try:
            if node_type == 'identifier':
                param_info['name'] = ast_handler.get_node_text(param_node, code_bytes)
            elif node_type == 'typed_parameter': # Python specific?
                identifier_node = ast_handler.find_child_by_field_name(param_node, 'name')
                if not identifier_node and param_node.child_count > 0 and param_node.child(0).type == 'identifier':
                     identifier_node = param_node.child(0) # Fallback if name field missing
                type_node = ast_handler.find_child_by_field_name(param_node, 'type')
                if identifier_node:
                    param_info['name'] = ast_handler.get_node_text(identifier_node, code_bytes)
                # else: logger.warning(...)
                if type_node:
                    param_info['type'] = ast_handler.get_node_text(type_node, code_bytes)
            elif node_type == 'required_parameter': # Common in TS/JS
                 pattern_node = param_node.child_by_field_name('pattern')
                 if not pattern_node and param_node.child_count > 0 and param_node.child(0).type == 'identifier':
                      pattern_node = param_node.child(0)
                 type_node = param_node.child_by_field_name('type')
                 if pattern_node:
                      if pattern_node.type == 'identifier':
                           param_info['name'] = ast_handler.get_node_text(pattern_node, code_bytes)
                      else:
                           param_info['name'] = ast_handler.get_node_text(pattern_node, code_bytes)
                           # logger.debug(...)
                 if type_node and type_node.child_count > 0:
                     param_info['type'] = ast_handler.get_node_text(type_node.child(0), code_bytes)
            elif node_type == 'optional_parameter': # Common in TS/JS
                 param_info['optional'] = True
                 pattern_node = param_node.child_by_field_name('pattern')
                 if not pattern_node and param_node.child_count > 0 and param_node.child(0).type == 'identifier':
                      pattern_node = param_node.child(0)
                 type_node = param_node.child_by_field_name('type')
                 value_node = param_node.child_by_field_name('value')
                 if pattern_node:
                     if pattern_node.type == 'identifier':
                          param_info['name'] = ast_handler.get_node_text(pattern_node, code_bytes)
                     else: # Destructuring
                          param_info['name'] = ast_handler.get_node_text(pattern_node, code_bytes)
                 if type_node and type_node.child_count > 0:
                     param_info['type'] = ast_handler.get_node_text(type_node.child(0), code_bytes)
                 if value_node:
                     param_info['default'] = ast_handler.get_node_text(value_node, code_bytes)

            elif node_type == 'default_parameter': # Python specific?
                name_field_node = ast_handler.find_child_by_field_name(param_node, 'name')
                value_node = ast_handler.find_child_by_field_name(param_node, 'value')
                if name_field_node:
                    nested_info = ExtractorHelpers.extract_parameter(ast_handler, name_field_node, code_bytes)
                    if nested_info:
                        param_info['name'] = nested_info.get('name')
                        param_info['type'] = nested_info.get('type')
                    else:
                        param_info['name'] = ast_handler.get_node_text(name_field_node, code_bytes)
                if value_node:
                    param_info['default'] = ast_handler.get_node_text(value_node, code_bytes)
                param_info['optional'] = True

            elif node_type == 'typed_default_parameter':
                name_node = ast_handler.find_child_by_field_name(param_node, 'name')
                type_node = ast_handler.find_child_by_field_name(param_node, 'type')
                value_node = ast_handler.find_child_by_field_name(param_node, 'value')
                if name_node:
                    param_info['name'] = ast_handler.get_node_text(name_node, code_bytes)
                if type_node:
                    param_info['type'] = ast_handler.get_node_text(type_node, code_bytes)
                if value_node:
                    param_info['default'] = ast_handler.get_node_text(value_node, code_bytes)
                param_info['optional'] = True

            elif node_type in ['list_splat_pattern', 'dictionary_splat_pattern', 'list_splat', 'dictionary_splat', 'rest_parameter']:
                inner_node = None
                for i in range(param_node.named_child_count):
                    child = param_node.named_child(i)
                    if child.type == 'identifier': inner_node = child; break
                if inner_node is None:
                    for i in range(param_node.child_count):
                        child = param_node.child(i)
                        if child.type == 'identifier': inner_node = child; break
                if inner_node:
                    prefix = ''
                    if node_type.startswith('list') or node_type == 'rest_parameter': prefix = '*' if ast_handler.language_code == 'python' else '...'
                    elif node_type.startswith('dictionary'): prefix = '**' if ast_handler.language_code == 'python' else '...'
                    param_info['name'] = prefix + ast_handler.get_node_text(inner_node, code_bytes)
                    param_info['optional'] = True
                    type_node = param_node.child_by_field_name('type')
                    if type_node and type_node.child_count > 0:
                         param_info['type'] = ast_handler.get_node_text(type_node.child(0), code_bytes)
                # else: logger.warning(...)
            else:
                return None

            if param_info['name']:
                return param_info
            else:
                # logger.warning(...)
                return None
        except Exception as e:
            logger.error(f'Error extracting parameter from node type {node_type} ({ast_handler.get_node_text(param_node, code_bytes)}): {e}', exc_info=True)
            return None

    @staticmethod
    def extract_return_info(ast_handler, function_node, code_bytes):
        """Extract return type information."""
        return_type = None
        return_values = []
        return_type_node = ast_handler.find_child_by_field_name(function_node, 'return_type')
        if return_type_node:
            if return_type_node.type == 'type_annotation' and return_type_node.child_count > 0:
                 return_type = ast_handler.get_node_text(return_type_node.child(0), code_bytes)
            else:
                 return_type = ast_handler.get_node_text(return_type_node, code_bytes)

        body_node = ast_handler.find_child_by_field_name(function_node, 'body')
        if body_node:
            try:
                return_query_value = '(return_statement (_) @return_value)'
                return_query_empty = '(return_statement) @return_empty (#eq? @return_empty "")' # Should use predicate on node text length
                return_query_value = return_query_value.strip()
                return_query_empty = return_query_empty.strip()

                return_value_results = ast_handler.execute_query(return_query_value, body_node, code_bytes)
                return_empty_results = ast_handler.execute_query(return_query_empty, body_node, code_bytes)

                processed_stmts = set()
                for node, capture_name in return_value_results:
                    if capture_name == 'return_value':
                        parent_stmt = node.parent
                        if parent_stmt and parent_stmt.type == 'return_statement' and parent_stmt.id not in processed_stmts:
                            if parent_stmt.named_child_count > 0:
                                return_values.append(ast_handler.get_node_text(node, code_bytes))
                                processed_stmts.add(parent_stmt.id)

                for node, capture_name in return_empty_results:
                     if capture_name == 'return_empty' and node.id not in processed_stmts:
                          is_literal_none_or_undefined = False
                          if node.named_child_count == 1:
                               child_node = node.named_child(0)
                               if child_node.type in ['none', 'undefined']: is_literal_none_or_undefined = True
                          if node.named_child_count == 0 or is_literal_none_or_undefined:
                               return_values.append('None')
                               processed_stmts.add(node.id)

            except Exception as e: # Catch QueryError specifically if needed
                logger.error(f'Error executing return value queries: {e}.', exc_info=False)

        return {'return_type': return_type, 'return_values': list(set(return_values))}

    @staticmethod
    @staticmethod
    def extract_decorators(ast_handler, node, code_bytes):
        """Extract decorators from a node (Improved Logging)."""
        decorators = []
        # Look for decorators attached to the parent node (common pattern)
        parent_node = node.parent
        node_to_check_for_decorators = None

        if parent_node and parent_node.type in ['decorated_definition', 'export_statement']:
            node_to_check_for_decorators = parent_node
            logger.debug(f"ExtractorHelpers.extract_decorators: Checking parent node '{parent_node.type}' (ID: {parent_node.id}) for decorators associated with node ID {node.id}")
        # Add other potential parent structures if necessary for different languages/patterns
        # else:
        #    node_to_check_for_decorators = node # Less common, check the node itself?

        if node_to_check_for_decorators:
            processed_decorator_nodes = set()
            # Iterate children of the potential decorator container
            for child in node_to_check_for_decorators.children:
                if child.type == 'decorator' and child.id not in processed_decorator_nodes:
                     logger.debug(f"ExtractorHelpers.extract_decorators: Found 'decorator' node (ID: {child.id}).")
                     dec_info = ExtractorHelpers._extract_single_decorator_info(ast_handler, child, code_bytes)
                     if dec_info:
                         decorators.append(dec_info)
                         processed_decorator_nodes.add(child.id)
                     else:
                         logger.warning(f"ExtractorHelpers.extract_decorators: Failed to extract info for decorator node ID {child.id}")
                # Stop if we encounter the actual definition node among siblings
                elif child.id == node.id:
                    logger.debug(f"ExtractorHelpers.extract_decorators: Reached the definition node (ID: {node.id}), stopping decorator search for this level.")
                    break # Decorators must precede the definition

        if not decorators:
            logger.debug(f"ExtractorHelpers.extract_decorators: No decorators found directly associated with node ID {node.id} or its common parents.")

        return decorators

    @staticmethod
    def _extract_single_decorator_info(ast_handler, decorator_node, code_bytes):
         """Extracts info from a single decorator node."""
         try:
              content = ast_handler.get_node_text(decorator_node, code_bytes)
              name = 'unknown_decorator'
              expression_node = decorator_node.child_by_field_name('expression')
              if not expression_node and decorator_node.child_count > 0:
                   expression_node = decorator_node.child(0) if decorator_node.child(0).type != '@' else (decorator_node.child(1) if decorator_node.child_count > 1 else None)

              if expression_node:
                  if expression_node.type == 'identifier':
                      name = ast_handler.get_node_text(expression_node, code_bytes)
                  elif expression_node.type == 'attribute':
                      obj_node = expression_node.child_by_field_name('object')
                      attr_node = expression_node.child_by_field_name('attribute')
                      if obj_node and attr_node: name = f"{ast_handler.get_node_text(obj_node, code_bytes)}.{ast_handler.get_node_text(attr_node, code_bytes)}"
                  elif expression_node.type == 'call_expression':
                      func_node = expression_node.child_by_field_name('function')
                      if func_node:
                           if func_node.type == 'identifier': name = ast_handler.get_node_text(func_node, code_bytes)
                           elif func_node.type == 'attribute':
                                obj_node = func_node.child_by_field_name('object'); attr_node = func_node.child_by_field_name('attribute')
                                if obj_node and attr_node: name = f"{ast_handler.get_node_text(obj_node, code_bytes)}.{ast_handler.get_node_text(attr_node, code_bytes)}"
                                else: name = ast_handler.get_node_text(func_node, code_bytes) # Fallback
                           else: name = ast_handler.get_node_text(func_node, code_bytes)
                  else: name = ast_handler.get_node_text(expression_node, code_bytes)

              start = decorator_node.start_point; end = decorator_node.end_point
              return { 'name': name.strip(), 'content': content, 'range': {'start': {'line': start[0] + 1, 'column': start[1]}, 'end': {'line': end[0] + 1, 'column': end[1]}} }
         except Exception as e:
              logger.error(f"Error extracting single decorator info: {e}", exc_info=True); return None

class BaseExtractor(ABC):
    """Abstract base class for all extractors."""
    ELEMENT_TYPE: CodeElementType
    LANGUAGE_CODE = '__all__'

    def __init__(self, language_code: str, language_type_descriptor: Optional[ElementTypeLanguageDescriptor]):
        """Initialize the extractor."""
        self.language_code = language_code.lower()
        self.descriptor = language_type_descriptor
        self._ast_handler: Optional[ASTHandler] = None
        if not self.descriptor and self.__class__.__name__ not in ['TemplateExtractor']:
            logger.warning(f'Extractor {self.__class__.__name__} initialized without a descriptor for language {self.language_code}. Extraction might fail.')

    def _get_ast_handler(self) -> Optional[ASTHandler]:
        """Get or create an AST handler for the language."""
        if self._ast_handler is None:
            try:
                parser = get_parser(self.language_code); language = LANGUAGES.get(self.language_code)
                if not parser or not language: logger.error(f'Cannot get parser or language for: {self.language_code}'); return None
                self._ast_handler = ASTHandler(self.language_code, parser, language)
            except Exception as e: logger.error(f'Error initializing AST Handler for {self.language_code}: {e}', exc_info=True); return None
        return self._ast_handler

    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match('^(\\s*)', line); return match.group(1) if match else ''

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> Union[List[Dict], Dict]:
        """Extract elements from the provided code."""
        context = context or {}
        result: Union[List[Dict], Dict] = []
        if not self.descriptor:
            if self.__class__.__name__ not in ['TemplateExtractor']: logger.error(f'Cannot extract for {self.__class__.__name__} - no descriptor provided.')
            return []
        if not self.descriptor._patterns_initialized:
             logger.error(f"Cannot extract using {self.__class__.__name__} - descriptor patterns for {self.descriptor.language_code}/{getattr(self.descriptor.element_type,'value','N/A')} were not initialized successfully.")
             return []
        if hasattr(self.descriptor, 'custom_extract') and self.descriptor.custom_extract:
            if hasattr(self.descriptor, 'extract') and callable(self.descriptor.extract):
                # logger.debug(...)
                try: result = self.descriptor.extract(code, context=context)
                except Exception as e: logger.error(f'Error in custom descriptor extract() method {self.descriptor.__class__.__name__}: {e}', exc_info=True); result = []
            else: logger.error(f'Descriptor {self.descriptor.__class__.__name__} marked custom_extract=True but is missing extract() method.'); result = []
        else:
            try: result = self._extract_with_patterns(code, self.descriptor, context)
            except Exception as e: logger.error(f"Error during _extract_with_patterns in {self.__class__.__name__}: {e}", exc_info=True); result = []
        if isinstance(result, list) and context:
            filtered_result = [item for item in result if isinstance(item, dict) and all(item.get(k) == v for k, v in context.items())]
            # Log discarded items?
            result = filtered_result
        elif isinstance(result, dict) and context:
            if not all(result.get(k) == v for k, v in context.items()): result = []
        elif not isinstance(result, (list, dict)) and result is not None:
             logger.warning(f'Extractor {self.__class__.__name__} returned unexpected type: {type(result)}. Returning empty list.'); result = []
        if self.ELEMENT_TYPE != CodeElementType.IMPORT:
            if isinstance(result, dict): result = [result]
            elif result is None: result = []
            elif not isinstance(result, list): logger.warning(f'Extractor {self.__class__.__name__} returned non-list/non-dict/non-None result: {type(result)}. Coercing to empty list.'); result = []
        return result

    @abstractmethod
    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Abstract method for pattern-based extraction. Must return List[Dict]."""
        pass

class TemplateExtractor(BaseExtractor):
    """Base template extractor implementing the pattern extraction flow."""

    @abstractmethod
    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context) -> List[Dict]:
       """Subclasses must implement how to turn TreeSitter captures into dicts."""
       raise NotImplementedError

    @abstractmethod
    def _process_regex_results(self, matches, code, context) -> List[Dict]:
        """Subclasses must implement how to turn Regex matches into dicts."""
        raise NotImplementedError

    def _extract_with_patterns(self, code: str, handler: Optional[ElementTypeLanguageDescriptor], context: Dict[str, Any]) -> List[Dict]:
        """Extracts elements, trying TreeSitter, then possibly Regex."""
        current_handler = handler or self.descriptor
        if not current_handler: logger.error(f'Cannot extract patterns for {self.__class__.__name__} - no handler provided.'); return []
        if not current_handler._patterns_initialized: logger.error(f"Cannot extract using {self.__class__.__name__} - descriptor patterns not initialized."); return []

        elements = []
        tree_sitter_attempted, tree_sitter_error = False, False
        regex_attempted, regex_error = False, False

        if self._should_attempt_tree_sitter(current_handler):
            tree_sitter_attempted = True
            try:
                self._before_tree_sitter(current_handler)
                # --- Simplified Logging ---
                logger.debug(f"Extractor {self.__class__.__name__} using TS query: {repr(current_handler.tree_sitter_query)}")
                # --- End Logging ---
                elements = self._parse_code_with_tree_sitter(code, current_handler, context)
            except Exception as e:
                self._handle_tree_sitter_exception(e, current_handler); elements = []; tree_sitter_error = True
        # else: logger.debug(...)

        should_fallback = self._should_fallback_to_regex(tree_sitter_attempted, tree_sitter_error, elements, current_handler)
        if should_fallback and current_handler.regexp_pattern:
             regex_attempted = True
             try:
                  self._before_regex(current_handler)
                  regex_elements = self._parse_code_with_regex(code, current_handler, context)
                  if not elements or tree_sitter_error: elements = regex_elements
             except Exception as e:
                  self._handle_regex_exception(e, current_handler)
                  if not elements or tree_sitter_error: elements = []
                  regex_error = True
        # else: logger.debug(...)

        self._after_extraction(elements, tree_sitter_attempted, tree_sitter_error, regex_attempted, regex_error, current_handler)
        return elements

    # --- Helper methods for the extraction flow ---
    def _should_attempt_tree_sitter(self, handler: ElementTypeLanguageDescriptor) -> bool: return bool(handler.tree_sitter_query) and self._get_ast_handler() is not None
    def _before_tree_sitter(self, handler: ElementTypeLanguageDescriptor): logger.debug(f'Attempting TreeSitter extraction for {self.language_code}/{getattr(handler.element_type,"value","?")}.')
    def _parse_code_with_tree_sitter(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        ast_handler = self._get_ast_handler()
        root, code_bytes = ast_handler.parse(code)
        if root.has_error: logger.warning(f"Syntax errors detected during TS parse for {self.language_code}/{getattr(handler.element_type,'value','?')}.")
        # Import QueryError here locally if needed, or handle generic Exception
        from tree_sitter import QueryError
        query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
        return self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
    def _handle_tree_sitter_exception(self, e: Exception, handler: ElementTypeLanguageDescriptor):
        from tree_sitter import QueryError # Import locally for check
        err_type = type(e).__name__
        logger.error(f'Error during TreeSitter extraction for {self.language_code}/{getattr(handler.element_type,"value","?")}: {err_type}: {e}', exc_info=False) # Less verbose exc_info
        if isinstance(e, QueryError): logger.error(f"Failed Query: {repr(handler.tree_sitter_query)}")
    def _should_fallback_to_regex(self, ts_attempted: bool, ts_error: bool, elements: List[Dict], handler: ElementTypeLanguageDescriptor) -> bool: return not ts_attempted or ts_error or (ts_attempted and not elements)
    def _before_regex(self, handler: ElementTypeLanguageDescriptor): logger.debug(f'Using Regex fallback for {self.language_code}/{getattr(handler.element_type,"value","?")}.') # Pattern: {repr(handler.regexp_pattern)} # Too verbose
    def _parse_code_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        matches = re.finditer(handler.regexp_pattern, code, re.MULTILINE | re.DOTALL); return self._process_regex_results(matches, code, context)
    def _handle_regex_exception(self, e: Exception, handler: ElementTypeLanguageDescriptor):
        err_type = type(e).__name__
        logger.error(f'Error during Regex extraction for {self.language_code}/{getattr(handler.element_type,"value","?")}: {err_type}: {e}', exc_info=False)
        if isinstance(e, re.error): logger.error(f"Failed Pattern: {repr(handler.regexp_pattern)}")
    def _after_extraction(self, elements: List[Dict], ts_attempted: bool, ts_error: bool, rx_attempted: bool, rx_error: bool, handler: ElementTypeLanguageDescriptor):
        status = f"TS Tried: {ts_attempted}, TS Err: {ts_error}, RX Tried: {rx_attempted}, RX Err: {rx_error}"
        logger.debug(f"Extraction finished for {self.language_code}/{getattr(handler.element_type,'value','?')}. Found {len(elements)} elements. Status: [{status}]")