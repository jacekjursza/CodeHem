# codehem/core/extractors/extraction_base.py
"""
Base extraction logic for standardizing extraction across languages.
"""
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
            params_node = ast_handler.find_child_by_field_name(node, 'parameter_list')
            if not params_node:
                 logger.debug(f"Could not find 'parameters' or 'parameter_list' node for node id {node.id}")
                 return parameters

        logger.debug(f"Found '{params_node.type}' node, named child count: {params_node.named_child_count}")
        for i in range(params_node.named_child_count):
            param_node = params_node.named_child(i)
            logger.debug(f"  Processing parameter child {i}: type={param_node.type}")

            if i == 0 and is_self_or_this:
                if param_node.type == 'identifier':
                    first_param_text = ast_handler.get_node_text(param_node, code_bytes)
                    if first_param_text in ['self', 'cls']:
                        logger.debug(f"  Skipping first parameter '{first_param_text}'.")
                        continue

            param_info = ExtractorHelpers.extract_parameter(ast_handler, param_node, code_bytes)
            if param_info:
                logger.debug(f"  Extracted parameter: {param_info}")
                parameters.append(param_info)
            else:
                 logger.warning(f"  Failed to extract info for parameter node type: {param_node.type}, text: '{ast_handler.get_node_text(param_node, code_bytes)}'")

        return parameters

    # --- ZMIANA ---
    # Poprawiona logika dla typed_parameter i default_parameter
    @staticmethod
    def extract_parameter(ast_handler, param_node, code_bytes) -> Optional[Dict[str, Any]]:
        """
        Extract information about a single parameter, handling different node types (Python specific).
        Returns a dictionary with 'name', 'type', 'default', 'optional'.
        """
        param_info = {'name': None, 'type': None, 'default': None, 'optional': False}
        node_type = param_node.type

        try:
            if node_type == 'identifier':
                # Simple parameter: name
                param_info['name'] = ast_handler.get_node_text(param_node, code_bytes)

            elif node_type == 'typed_parameter':
                # Parameter with type: name: type
                # Usually contains 'identifier' and 'type' children directly
                identifier_node = None
                type_node = None
                for child in param_node.children:
                     if child.type == 'identifier' and identifier_node is None: # Bierzemy pierwszy identyfikator
                          identifier_node = child
                     elif child.type == 'type' and type_node is None:
                          type_node = child
                     # Można też szukać po field_name, jeśli gramatyka to wspiera
                     # identifier_node = param_node.child_by_field_name('name')
                     # type_node = param_node.child_by_field_name('type')

                if identifier_node:
                    param_info['name'] = ast_handler.get_node_text(identifier_node, code_bytes)
                if type_node:
                    param_info['type'] = ast_handler.get_node_text(type_node, code_bytes)
                
                # Jeśli nadal nie ma nazwy, spróbujmy znaleźć przez field name (fallback)
                if param_info['name'] is None:
                     name_node_fallback = param_node.child_by_field_name('name') # W starszych wersjach?
                     if name_node_fallback and name_node_fallback.type == 'identifier':
                          param_info['name'] = ast_handler.get_node_text(name_node_fallback, code_bytes)
                          logger.debug("  Used fallback child_by_field_name('name') for typed_parameter name.")

            elif node_type == 'default_parameter':
                # Parameter with default value: name = value OR name: type = value
                name_field_node = ast_handler.find_child_by_field_name(param_node, 'name') # Usually 'identifier' or 'typed_parameter'
                value_node = ast_handler.find_child_by_field_name(param_node, 'value')

                if name_field_node:
                    if name_field_node.type == 'typed_parameter':
                         # Extract name and type from the nested typed_parameter
                         # Re-use logic by calling self recursively (or inline similar logic)
                         nested_info = ExtractorHelpers.extract_parameter(ast_handler, name_field_node, code_bytes)
                         if nested_info:
                              param_info['name'] = nested_info.get('name')
                              param_info['type'] = nested_info.get('type')
                         else:
                              logger.warning(f"Could not extract info from nested typed_parameter within default_parameter.")
                    elif name_field_node.type == 'identifier':
                         param_info['name'] = ast_handler.get_node_text(name_field_node, code_bytes)
                    else:
                         logger.warning(f"Unexpected node type '{name_field_node.type}' within 'default_parameter' name field.")
                         param_info['name'] = ast_handler.get_node_text(name_field_node, code_bytes) # Fallback

                if value_node:
                    param_info['default'] = ast_handler.get_node_text(value_node, code_bytes)
                    param_info['optional'] = True

            elif node_type == 'typed_default_parameter': # Direct handling for name: type = value
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

            # Handle *args, **kwargs
            elif node_type in ['list_splat_pattern', 'dictionary_splat_pattern', 'list_splat', 'dictionary_splat']:
                 inner_node = None
                 # Try common structures
                 if param_node.named_child_count > 0:
                      inner_node = param_node.named_child(0)
                 elif param_node.child_count > 0:
                      inner_node = param_node.child(0)
                      if inner_node and inner_node.type in ['*', '**'] and param_node.child_count > 1:
                           inner_node = param_node.child(1)

                 if inner_node and inner_node.type == 'identifier':
                      prefix = '*' if node_type.startswith('list') else '**'
                      param_info['name'] = prefix + ast_handler.get_node_text(inner_node, code_bytes)
                      param_info['optional'] = True
                 elif inner_node:
                     logger.warning(f"Unexpected inner node type '{inner_node.type}' for splat pattern.")
                     text = ast_handler.get_node_text(param_node, code_bytes)
                     param_info['name'] = text # Fallback
                     param_info['optional'] = True
                 else:
                     logger.warning(f"Could not find identifier within splat pattern node: {ast_handler.get_node_text(param_node, code_bytes)}")

            else:
                 logger.warning(f"Unhandled parameter node type: {node_type}, text: '{ast_handler.get_node_text(param_node, code_bytes)}'")
                 return None

            # Check if name was extracted
            if param_info['name']:
                return param_info
            else:
                logger.warning(f"Failed to extract name for parameter node type {node_type}: '{ast_handler.get_node_text(param_node, code_bytes)}'")
                return None

        except Exception as e:
            logger.error(f"Error extracting parameter from node type {node_type}: {e}", exc_info=True)
            return None

    # --- ZMIANA ---
    # Poprawione zapytania TreeSitter dla return
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
                # Query 1: Capture the node representing the returned value (if any)
                # We capture any node (*) that follows the 'return' keyword inside the statement.
                return_query_value = """
                (return_statement
                    value: (_) @return_value)
                """
                # Query 2: Capture 'return' statements that *don't* have a value following them.
                # We capture the statement itself.
                return_query_empty = """
                (return_statement) @return_empty
                (#unless-eq? @return_empty node (return_statement value: (_)))
                """

                return_value_results = ast_handler.execute_query(return_query_value, body_node, code_bytes)
                return_empty_results = ast_handler.execute_query(return_query_empty, body_node, code_bytes)

                processed_stmts = set()

                # Process returns with values
                for node, capture_name in return_value_results:
                    if capture_name == 'return_value':
                        parent_stmt = node.parent # The return_statement node
                        if parent_stmt and parent_stmt.id not in processed_stmts:
                            return_values.append(ast_handler.get_node_text(node, code_bytes))
                            processed_stmts.add(parent_stmt.id)
                            logger.debug(f"  Extracted return value: {return_values[-1]}")

                # Process empty returns
                for node, capture_name in return_empty_results:
                    if capture_name == 'return_empty' and node.id not in processed_stmts:
                        return_values.append("None") # Represent empty return as None
                        processed_stmts.add(node.id)
                        logger.debug(f"  Extracted empty return (-> None)")

                # Fallback if queries failed or yielded no results (less likely now)
                if not processed_stmts:
                     logger.debug("TreeSitter queries for return yielded no results, trying Regex fallback.")
                     function_text = ast_handler.get_node_text(function_node, code_bytes)
                     return_regex = r'^\s*return(?:\s+(.+?))?\s*(?:#.*)?$'
                     for line in function_text.splitlines():
                          match = re.match(return_regex, line)
                          if match:
                               returned_value = match.group(1)
                               return_values.append(returned_value.strip() if returned_value else "None")

            except Exception as e:
                logger.error(f"Error executing TreeSitter queries for return values: {e}. No return values extracted.", exc_info=False)
                # Fallback can be added here if needed, but queries should ideally work or fail clearly

        return {'return_type': return_type, 'return_values': return_values}

    @staticmethod
    def extract_decorators(ast_handler, node, code_bytes):
        """Extract decorators from a node."""
        # Keep empty as logic is in TemplateMethodExtractor
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

        if not self.descriptor and self.__class__.__name__ not in ['TemplateExtractor']: # TemplateExtractor jest ok bez deskryptora
             logger.warning(f"Extractor {self.__class__.__name__} initialized without a descriptor for language {self.language_code}.")

    def _get_ast_handler(self) -> Optional[ASTHandler]:
        """Get or create an AST handler for the language."""
        if self._ast_handler is None:
            try:
                parser = get_parser(self.language_code)
                language = LANGUAGES.get(self.language_code)
                if not parser or not language:
                     logger.error(f"Cannot get parser or language for: {self.language_code}")
                     return None
                self._ast_handler = ASTHandler(self.language_code, parser, language)
            except ValueError as e:
                 logger.error(f"Error initializing AST Handler for {self.language_code}: {e}")
                 return None
            except Exception as e:
                 logger.error(f"Unexpected error initializing AST Handler for {self.language_code}: {e}", exc_info=True)
                 return None
        return self._ast_handler

    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match(r'^(\s*)', line)
        return match.group(1) if match else ''

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> Union[List[Dict], Dict]:
        """Extract elements from the provided code."""
        context = context or {}
        result: Union[List[Dict], Dict] = [] # Default to empty list

        if not self.descriptor:
             # Allow TemplateExtractor base class to proceed without descriptor maybe?
             if self.__class__.__name__ not in ['TemplateExtractor']:
                 logger.error(f"Cannot extract for {self.__class__.__name__} - no descriptor provided.")
                 return result
             # If it's just the template base, maybe it doesn't need to extract directly
             pass

        # Check for custom extraction logic in the descriptor
        if self.descriptor and hasattr(self.descriptor, 'custom_extract') and self.descriptor.custom_extract:
             if hasattr(self.descriptor, 'extract') and callable(self.descriptor.extract):
                  logger.debug(f"Using custom extract() method from descriptor for {self.language_code}/{self.descriptor.element_type.value}")
                  try:
                       result = self.descriptor.extract(code, context=context)
                  except Exception as e:
                       logger.error(f"Error in custom descriptor extract() method {self.descriptor.__class__.__name__}: {e}", exc_info=True)
                       result = []
             else:
                  logger.error(f"Descriptor {self.descriptor.__class__.__name__} marked custom_extract=True but is missing extract() method.")
                  result = []
        elif self.descriptor: # Use pattern-based extraction if descriptor exists and is not custom
             result = self._extract_with_patterns(code, self.descriptor, context)
        # else: # No descriptor and not custom - likely an abstract base or template, do nothing

        # Filter list results based on context
        if isinstance(result, list) and context:
             filtered_result = []
             for item in result:
                  if isinstance(item, dict):
                       if all(item.get(k) == v for k, v in context.items()):
                            filtered_result.append(item)
             result = filtered_result
        elif isinstance(result, dict) and context:
             if not all(result.get(k) == v for k, v in context.items()):
                 result = [] # Return empty list if single dict doesn't match context

        # Ensure result type consistency (mostly lists, except special cases)
        if self.ELEMENT_TYPE != CodeElementType.IMPORT and not isinstance(result, list):
             if isinstance(result, dict):
                  result = [result]
             elif result is None: # Handle None case explicitly
                  result = []
             else:
                  logger.warning(f"Extractor {self.__class__.__name__} returned non-list/non-dict/non-None result: {type(result)}. Returning empty list.")
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
        """Extract using TreeSitter first, fall back to regex if needed."""
        if not handler:
            logger.error(f"Cannot extract patterns for {self.__class__.__name__} - no handler (descriptor) provided.")
            return []

        elements = []
        tree_sitter_attempted = False
        tree_sitter_error = False

        if handler.tree_sitter_query:
            ast_handler = self._get_ast_handler()
            if ast_handler:
                tree_sitter_attempted = True
                try:
                    logger.debug(f"Attempting TreeSitter extraction for {self.language_code}/{handler.element_type.value}")
                    root, code_bytes = ast_handler.parse(code)
                    query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
                    elements = self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
                except Exception as e:
                    logger.error(f"TreeSitter error for {self.language_code}/{handler.element_type.value}: {e}", exc_info=False)
                    elements = []
                    tree_sitter_error = True
            else:
                 logger.warning(f"No AST Handler for {self.language_code}, skipping TreeSitter.")

        should_fallback = (not tree_sitter_attempted or tree_sitter_error or not elements)
        if handler.regexp_pattern and should_fallback:
            logger.debug(f"Using Regex fallback for {self.language_code}/{handler.element_type.value}")
            try:
                matches = re.finditer(handler.regexp_pattern, code, re.MULTILINE | re.DOTALL)
                elements = self._process_regex_results(matches, code, context)
            except Exception as e:
                logger.error(f"Regex error for {self.language_code}/{handler.element_type.value}: {e}", exc_info=False)
                elements = []

        return elements