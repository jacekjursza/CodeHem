# codehem/core/extractors/extraction_base.py
import logging
import re
from typing import Dict, List, Any, Optional, Union
from codehem.core.engine.ast_handler import ASTHandler
from codehem.core.engine.languages import LANGUAGES, get_parser
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType
from abc import ABC, abstractmethod
logger = logging.getLogger(__name__)

class ExtractorHelpers:
    """Common utilities for extraction."""

    @staticmethod
    def extract_parameters(ast_handler, node, code_bytes, is_self_or_this=True):
        """Extract parameters from a function/method node."""
        parameters = []
        params_node = ast_handler.find_child_by_field_name(node, 'parameters')
        if not params_node:
            params_node = ast_handler.find_child_by_field_name(node, 'parameter_list') # Alternative name
            if not params_node:
                logger.debug(f"Could not find 'parameters' or 'parameter_list' node for node id {node.id}")
                return parameters

        logger.debug(f"Found '{params_node.type}' node, named child count: {params_node.named_child_count}")

        for i in range(params_node.named_child_count):
            param_node = params_node.named_child(i)
            logger.debug(f'  Processing parameter child {i}: type={param_node.type}')

            # Skip 'self' or 'cls' if expected
            if i == 0 and is_self_or_this:
                if param_node.type == 'identifier':
                    first_param_text = ast_handler.get_node_text(param_node, code_bytes)
                    if first_param_text in ['self', 'cls']:
                        logger.debug(f"  Skipping first parameter '{first_param_text}'.")
                        continue

            # Extract parameter info
            param_info = ExtractorHelpers.extract_parameter(ast_handler, param_node, code_bytes)
            if param_info:
                logger.debug(f'  Extracted parameter: {param_info}')
                parameters.append(param_info)
            else:
                logger.debug(f"  Could not extract info for parameter node type: {param_node.type}, text: '{ast_handler.get_node_text(param_node, code_bytes)}'")
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
            elif node_type == 'typed_parameter':
                # --- Corrected logic for typed_parameter ---
                identifier_node = ast_handler.find_child_by_field_name(param_node, 'name') # Usually 'identifier', but use field name
                if not identifier_node: # Fallback: often the first child is the identifier
                     if param_node.child_count > 0 and param_node.child(0).type == 'identifier':
                         identifier_node = param_node.child(0)

                type_node = ast_handler.find_child_by_field_name(param_node, 'type') # Use field name 'type'

                if identifier_node:
                    param_info['name'] = ast_handler.get_node_text(identifier_node, code_bytes)
                else:
                    logger.warning(f"Could not find identifier node for name in typed_parameter: {ast_handler.get_node_text(param_node, code_bytes)}")

                if type_node:
                    param_info['type'] = ast_handler.get_node_text(type_node, code_bytes)
                # --- End of corrected logic ---
            elif node_type == 'default_parameter':
                name_field_node = ast_handler.find_child_by_field_name(param_node, 'name')
                value_node = ast_handler.find_child_by_field_name(param_node, 'value')
                if name_field_node:
                    # Recursively extract info from the name part (could be identifier or typed_parameter)
                    nested_info = ExtractorHelpers.extract_parameter(ast_handler, name_field_node, code_bytes)
                    if nested_info:
                        param_info['name'] = nested_info.get('name')
                        param_info['type'] = nested_info.get('type')
                    else:
                        logger.warning(f"Could not extract info from nested node type '{name_field_node.type}' within default_parameter.")
                        # Fallback if recursion fails
                        param_info['name'] = ast_handler.get_node_text(name_field_node, code_bytes)
                if value_node:
                    param_info['default'] = ast_handler.get_node_text(value_node, code_bytes)
                    param_info['optional'] = True
                else:
                    logger.warning(f"Default parameter node lacks a 'value' node: {ast_handler.get_node_text(param_node, code_bytes)}")
                    param_info['optional'] = True # Assume optional even if value is missing? Or maybe not? For now, True.
            elif node_type == 'typed_default_parameter': # Deprecated in newer tree-sitter-python, but handle just in case
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
            elif node_type in ['list_splat_pattern', 'dictionary_splat_pattern', 'list_splat', 'dictionary_splat']:
                 # Try to find the identifier within the splat
                inner_node = None
                # Check named children first
                for i in range(param_node.named_child_count):
                     child = param_node.named_child(i)
                     if child.type == 'identifier':
                         inner_node = child
                         break
                # Fallback: check unnamed children if no named identifier found
                if inner_node is None:
                     for i in range(param_node.child_count):
                         child = param_node.child(i)
                         if child.type == 'identifier':
                             inner_node = child
                             break

                if inner_node:
                    prefix = '*' if node_type.startswith('list') else '**'
                    param_info['name'] = prefix + ast_handler.get_node_text(inner_node, code_bytes)
                    param_info['optional'] = True # *args/**kwargs are effectively optional
                else:
                    logger.warning(f'Could not find identifier within splat pattern node: {ast_handler.get_node_text(param_node, code_bytes)}')
            else:
                logger.debug(f"Unhandled parameter node type: {node_type}, text: '{ast_handler.get_node_text(param_node, code_bytes)}'")
                return None # Unhandled type

            # Only return if we successfully extracted a name
            if param_info['name']:
                return param_info
            else:
                logger.warning(f"Failed to extract name for parameter node type {node_type}: '{ast_handler.get_node_text(param_node, code_bytes)}'")
                return None
        except Exception as e:
            logger.error(f'Error extracting parameter from node type {node_type}: {e}', exc_info=True)
            return None

    @staticmethod
    def extract_return_info(ast_handler, function_node, code_bytes):
        """Extract return type information."""
        return_type = None
        return_values = []
        return_type_node = ast_handler.find_child_by_field_name(function_node, 'return_type')
        if return_type_node:
            return_type = ast_handler.get_node_text(return_type_node, code_bytes)

        body_node = ast_handler.find_child_by_field_name(function_node, 'body')
        if body_node:
            try:
                # Query for return statements with a value
                return_query_value = '(return_statement (_) @return_value)'
                # Query for return statements without a value (just 'return')
                return_query_empty = '(return_statement) @return_empty'

                return_query_value = return_query_value.strip()
                return_query_empty = return_query_empty.strip()

                return_value_results = ast_handler.execute_query(return_query_value, body_node, code_bytes)
                return_empty_results = ast_handler.execute_query(return_query_empty, body_node, code_bytes)

                processed_stmts = set() # Track statement nodes already processed

                # Process returns with values
                for node, capture_name in return_value_results:
                    if capture_name == 'return_value':
                        parent_stmt = node.parent
                        # Ensure it's a direct child of a return_statement and not already processed
                        if parent_stmt and parent_stmt.type == 'return_statement' and parent_stmt.id not in processed_stmts:
                           # Check if it's not just 'return' (has more than one child: 'return' keyword + value)
                           # Or if it has named children (safer check)
                           if parent_stmt.named_child_count > 0:
                               return_values.append(ast_handler.get_node_text(node, code_bytes))
                               processed_stmts.add(parent_stmt.id)
                               logger.debug(f'  Extracted return value: {return_values[-1]}')

                # Process empty returns ('return' or 'return None')
                for node, capture_name in return_empty_results:
                    if capture_name == 'return_empty' and node.id not in processed_stmts:
                        # Check if it's an empty return statement (child count 1, type 'return')
                        # Or if it returns the literal 'None'
                        is_literal_none = False
                        if node.named_child_count == 1:
                            child_node = node.named_child(0)
                            if child_node.type == 'none':
                                is_literal_none = True

                        if node.named_child_count == 0 or is_literal_none :
                           return_values.append('None') # Represent empty return or 'return None' as 'None'
                           processed_stmts.add(node.id)
                           logger.debug(f'  Extracted empty or None return (-> None)')

                if not processed_stmts:
                     # Fallback if queries failed (less reliable)
                     logger.debug('TreeSitter queries for return yielded no results, trying Regex fallback.')
                     function_text = ast_handler.get_node_text(function_node, code_bytes)
                     # Match 'return' followed by something OR just 'return' at end of line/before comment
                     return_regex = r'^\s*return(?:\s+(.+?))?\s*(?:#.*)?$'
                     for line in function_text.splitlines():
                          match = re.match(return_regex, line)
                          if match:
                              returned_value = match.group(1)
                              return_values.append(returned_value.strip() if returned_value else 'None')

            except Exception as e:
                logger.error(f'Error executing TreeSitter queries for return values: {e}. No return values extracted.', exc_info=False)

        return {'return_type': return_type, 'return_values': list(set(return_values))} # Return unique values

    @staticmethod
    def extract_decorators(ast_handler, node, code_bytes):
        """Extract decorators from a node."""
        # Placeholder - implementation is in TemplateMethodExtractor
        return []


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
             logger.warning(f'Extractor {self.__class__.__name__} initialized without a descriptor for language {self.language_code}.')


    def _get_ast_handler(self) -> Optional[ASTHandler]:
        """Get or create an AST handler for the language."""
        if self._ast_handler is None:
            try:
                parser = get_parser(self.language_code)
                language = LANGUAGES.get(self.language_code)
                if not parser or not language:
                    logger.error(f'Cannot get parser or language for: {self.language_code}')
                    return None
                self._ast_handler = ASTHandler(self.language_code, parser, language)
            except ValueError as e:
                logger.error(f'Error initializing AST Handler for {self.language_code}: {e}')
                return None
            except Exception as e:
                logger.error(f'Unexpected error initializing AST Handler for {self.language_code}: {e}', exc_info=True)
                return None
        return self._ast_handler


    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> Union[List[Dict], Dict]:
        """Extract elements from the provided code."""
        context = context or {}
        result: Union[List[Dict], Dict] = []

        # Check if descriptor exists before proceeding
        if not self.descriptor:
            # Allow TemplateExtractor base class to exist without a descriptor initially
             if self.__class__.__name__ not in ['TemplateExtractor']:
                  logger.error(f'Cannot extract for {self.__class__.__name__} - no descriptor provided.')
             return result # Return empty list if no descriptor

        # Use custom extract if defined in the descriptor
        if hasattr(self.descriptor, 'custom_extract') and self.descriptor.custom_extract:
            if hasattr(self.descriptor, 'extract') and callable(self.descriptor.extract):
                logger.debug(f'Using custom extract() method from descriptor for {self.language_code}/{self.descriptor.element_type.value}')
                try:
                    result = self.descriptor.extract(code, context=context)
                except Exception as e:
                    logger.error(f'Error in custom descriptor extract() method {self.descriptor.__class__.__name__}: {e}', exc_info=True)
                    result = []
            else:
                logger.error(f'Descriptor {self.descriptor.__class__.__name__} marked custom_extract=True but is missing extract() method.')
                result = []
        # Otherwise, use pattern-based extraction
        else:
            result = self._extract_with_patterns(code, self.descriptor, context)

        # Filter results based on context if context is provided
        if isinstance(result, list) and context:
             filtered_result = []
             for item in result:
                 if isinstance(item, dict):
                     # Check if all context key-value pairs match the item's keys/values
                     if all(item.get(k) == v for k, v in context.items()):
                         filtered_result.append(item)
             result = filtered_result
        elif isinstance(result, dict) and context:
            # If result is a single dict, check if it matches context
            if not all(result.get(k) == v for k, v in context.items()):
                 result = [] # Return empty list if the single dict doesn't match

        # Ensure result is a list for most element types (except potentially IMPORT)
        # Note: This check might need refinement if some extractors legitimately return a single dict
        if self.ELEMENT_TYPE != CodeElementType.IMPORT and not isinstance(result, list):
            if isinstance(result, dict):
                result = [result] # Wrap single dict in a list
            elif result is None:
                result = [] # Convert None to empty list
            else:
                # Log warning for unexpected types and return empty list
                logger.warning(f'Extractor {self.__class__.__name__} returned non-list/non-dict/non-None result: {type(result)}. Returning empty list.')
                result = []

        return result


    @abstractmethod
    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Abstract method for pattern-based extraction."""
        pass


class TemplateExtractor(BaseExtractor):
    """Example template extractor implementing the abstract method."""

    @abstractmethod
    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context) -> List[Dict]:
        raise NotImplementedError

    @abstractmethod
    def _process_regex_results(self, matches, code, context) -> List[Dict]:
        raise NotImplementedError

    def _extract_with_patterns(self, code: str, handler: Optional[ElementTypeLanguageDescriptor], context: Dict[str, Any]) -> List[Dict]:
        """Extract using TreeSitter first, fall back to regex if needed.
        [DEBUGGING: Reverted to direct logic, removed undefined helper methods]"""
        if not handler:
            logger.error(f'Cannot extract patterns for {self.__class__.__name__} - no handler (descriptor) provided.')
            return []

        elements = []
        tree_sitter_attempted = False
        tree_sitter_error = False
        regex_attempted = False
        regex_error = False # Keep track of regex errors too

        # --- TreeSitter Attempt ---
        # Check if we should attempt TreeSitter
        should_try_ts = bool(handler.tree_sitter_query) and self._get_ast_handler() is not None
        if should_try_ts:
            tree_sitter_attempted = True
            ast_handler = self._get_ast_handler()
            handler_type_name = handler.element_type.value if handler.element_type else 'unknown_handler'
            logger.debug(f'Attempting TreeSitter extraction for {self.language_code} (handler: {handler_type_name}).')
            # --- Removed Inner Try-Except ---
            # Allow exceptions during parsing or processing to propagate for debugging
            root, code_bytes = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
            elements = self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
            # --- End Removed Inner Try-Except ---
            # except Exception as e:
            #    logger.error(f'Error during TreeSitter extraction for {self.language_code} ({handler_type_name}): {e}', exc_info=False)
            #    elements = []
            #    tree_sitter_error = True # Mark TS attempt as failed

        # --- Regex Fallback/Attempt ---
        # Determine if fallback is needed
        should_fallback = (not tree_sitter_attempted or tree_sitter_error or (tree_sitter_attempted and not elements))

        if handler.regexp_pattern and should_fallback:
            regex_attempted = True
            handler_type_name = handler.element_type.value if handler.element_type else 'unknown_handler'
            logger.debug(f'Using Regex fallback for {self.language_code} (handler: {handler_type_name}).')
            # --- Removed Inner Try-Except ---
            # Allow exceptions during regex processing to propagate
            matches = re.finditer(handler.regexp_pattern, code, re.MULTILINE | re.DOTALL)
            regex_elements = self._process_regex_results(matches, code, context)
            # Only use regex results if TS failed or returned nothing
            if not elements or tree_sitter_error:
                 elements = regex_elements
            # --- End Removed Inner Try-Except ---
            # except Exception as e:
            #     logger.error(f'Error during Regex extraction for {self.language_code} (handler: {handler_type_name}): {e}', exc_info=False)
            #     # If TS also failed, ensure elements is empty
            #     if tree_sitter_error:
            #         elements = []
            #     regex_error = True

        # --- Logging after attempts ---
        handler_type_name = handler.element_type.value if handler.element_type else 'unknown_handler'
        if not elements:
            if tree_sitter_attempted and not tree_sitter_error:
                 logger.debug(f'TreeSitter extraction for {self.language_code} (handler: {handler_type_name}) returned no elements.')
            if regex_attempted and not regex_error and should_fallback:
                 logger.debug(f'Regex extraction for {self.language_code} (handler: {handler_type_name}) returned no elements.')

        return elements
