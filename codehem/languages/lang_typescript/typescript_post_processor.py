import logging
from typing import List, Dict, Optional
from codehem.models.code_element import CodeElement, CodeRange
from codehem.models.enums import CodeElementType
from pydantic import ValidationError
from ..post_processor_base import BaseExtractionPostProcessor
import re # Import re for regex used in _process_member_element

logger = logging.getLogger(__name__)

class TypeScriptExtractionPostProcessor(BaseExtractionPostProcessor):
    """
    TypeScript/JavaScript specific implementation of extraction post-processing.
    Transforms raw extraction dicts into structured CodeElement objects.
    """

    def process_imports(self, raw_imports: List[Dict]) -> List[CodeElement]:
        """ Processes raw import data into CodeElement objects. """
        processed_imports = []
        if not raw_imports:
            logger.debug('ProcessImports (TS): No raw imports received.')
            return []

        # Check if imports were already combined by the extractor
        if len(raw_imports) == 1 and raw_imports[0].get('name') == 'imports' and 'individual_imports' in raw_imports[0].get('additional_data', {}):
             logger.debug("ProcessImports (TS): Received already combined import block.")
             try:
                 # Re-create the CodeElement to ensure consistency
                 combined_data = raw_imports[0]
                 combined_element = CodeElement.from_dict(combined_data)
                 # Optionally process individual imports if needed later
                 # for imp_data in combined_data['additional_data']['individual_imports']:
                 #     pass # Could create child elements if required by model
                 return [combined_element]
             except (ValidationError, Exception) as e:
                 logger.error(f"ProcessImports (TS): Failed to process pre-combined import block: {e}", exc_info=True)
                 return [] # Failed to process, return empty

        logger.debug(f"ProcessImports (TS): Processing {len(raw_imports)} individual import dicts.")
        # If not pre-combined, process individually (or combine here if preferred)
        # Current Python approach combines them. Let's replicate that.
        valid_imports = [imp for imp in raw_imports if isinstance(imp, dict) and 'range' in imp]
        if not valid_imports:
            logger.error('ProcessImports (TS): No valid raw imports with range data found.')
            return []
        try:
            valid_imports.sort(key=lambda x: x.get('range', {}).get('start', {}).get('line', float('inf')))
        except Exception as e:
            logger.error(f'ProcessImports (TS): Error sorting valid_imports: {e}. Proceeding unsorted.', exc_info=True)

        first_import = valid_imports[0]
        last_import = valid_imports[-1]
        first_range = first_import.get('range', {})
        last_range = last_import.get('range', {})
        start_data = first_range.get('start', {})
        end_data = last_range.get('end', {})
        start_line = start_data.get('line')
        start_col = start_data.get('column', 0)
        end_line = end_data.get('line')
        end_col = end_data.get('column', 0)

        combined_range = None
        if isinstance(start_line, int) and isinstance(end_line, int) and start_line > 0 and end_line >= start_line:
            try:
                combined_range = CodeRange(start_line=start_line, start_column=start_col, end_line=end_line, end_column=end_col)
            except (ValidationError, Exception) as e:
                logger.error(f'ProcessImports (TS): Failed to create combined CodeRange: {e}', exc_info=True)
        else:
            logger.warning(f'ProcessImports (TS): Invalid lines for combined range: start={start_line}, end={end_line}.')

        # Extract content based on combined range from the original code if possible
        # This requires the original code, which isn't passed here.
        # Fallback: Join individual contents (less accurate for spacing/comments)
        combined_content = '\n'.join([imp.get('content', '') for imp in valid_imports])

        try:
            combined_element = CodeElement(
                type=CodeElementType.IMPORT,
                name='imports',
                content=combined_content, # Content might be inaccurate if just joined
                range=combined_range,
                additional_data={'individual_imports': valid_imports} # Keep raw data
            )
            logger.debug("ProcessImports (TS): Successfully created combined 'imports' CodeElement.")
            return [combined_element]
        except (ValidationError, Exception) as e:
            logger.error(f"ProcessImports (TS): Failed to create combined 'imports' CodeElement: {e}", exc_info=True)
            return []

    def process_functions(self, raw_functions: List[Dict]) -> List[CodeElement]:
        """ Processes raw function data into CodeElement objects. """
        processed_functions = []
        for func_data in raw_functions:
            if not isinstance(func_data, dict):
                logger.warning(f'Skipping non-dict item in raw_functions (TS): {type(func_data)}')
                continue
            func_name = func_data.get('name', 'unknown_func')
            logger.debug(f'Processing function (TS): {func_name}')
            # Ensure type is set correctly
            func_data['type'] = CodeElementType.FUNCTION.value
            try:
                func_element = CodeElement.from_dict(func_data)
                func_element.parent_name = None # Standalone functions have no parent
                # Process children like decorators, parameters, return value
                func_element.children.extend(self._process_decorators(func_data, func_name))
                func_element.children.extend(self._process_parameters(func_element, func_data.get('parameters', [])))
                return_element = self._process_return_value(func_element, func_data.get('return_info', {}))
                if return_element:
                    func_element.children.append(return_element)
                # Sort children by start line if range is available
                func_element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))
                processed_functions.append(func_element)
            except (ValidationError, Exception) as e:
                logger.error(f"Failed to process function (TS) '{func_name}': {e}. Data: {func_data}", exc_info=True)
        return processed_functions

    def process_classes(self, raw_classes: List[Dict], members: List[Dict], static_props: List[Dict]) -> List[CodeElement]:
        """ Processes raw class/interface data, associating members and static properties. """
        processed_containers = [] # Holds classes and interfaces
        member_lookup = self._build_lookup(members, 'class_name') # Includes methods, getters, setters, fields
        # Note: static_props might be redundant if properties extractor handles static fields
        static_prop_lookup = self._build_lookup(static_props, 'class_name')

        for container_data in raw_classes: # This list might contain classes and interfaces
            if not isinstance(container_data, dict):
                logger.warning(f'Skipping non-dict item in raw_classes (TS): {type(container_data)}')
                continue

            container_name = container_data.get('name')
            container_type_str = container_data.get('type', CodeElementType.CLASS.value) # Default to class
            logger.debug(f'Processing container (TS): {container_name} (type: {container_type_str})')

            if not container_name:
                logger.error(f'Found container definition without a name (TS)! Data: {container_data}')
                continue

            try:
                 # Ensure type is correct Enum value
                container_type = CodeElementType(container_type_str)
                container_data['type'] = container_type.value
            except ValueError:
                 logger.error(f"Invalid container type '{container_type_str}' for {container_name}. Defaulting to CLASS.")
                 container_type = CodeElementType.CLASS
                 container_data['type'] = container_type.value

            try:
                container_element = CodeElement.from_dict(container_data)
                container_element.parent_name = None # Top-level element

                # Process decorators for the container itself
                container_element.children.extend(self._process_decorators(container_data, container_name))

                # Process members (methods, properties, getters, setters)
                members_for_this = member_lookup.get(container_name, [])
                # --- CORRECTED LINE 170 ---
                members_for_this.sort(key=lambda m: m.get('definition_start_line', m.get('range', {}).get('start', {}).get('line', 0)))

                processed_members = {} # Use dict to handle potential duplicates/overrides?
                for member_data in members_for_this:
                    if not isinstance(member_data, dict): continue
                    processed_member = self._process_member_element(member_data, container_element)
                    if processed_member:
                         # Use tuple key (type, name) for potential getter/setter pairs under same name
                         member_key = (processed_member.type.value, processed_member.name)
                         processed_members[member_key] = processed_member

                container_element.children.extend(list(processed_members.values()))

                # Process static properties (if not already handled by member processing)
                # This might need adjustment depending on how 'PROPERTY' extractor works
                static_props_for_this = static_prop_lookup.get(container_name, [])
                static_props_for_this.sort(key=lambda p: p.get('range', {}).get('start', {}).get('line', 0))
                processed_static_props = {}
                for prop_data in static_props_for_this:
                     if not isinstance(prop_data, dict): continue
                     # Avoid duplicating if already processed as a member property
                     prop_name = prop_data.get('name')
                     # Check against processed_members values (which are CodeElement objects)
                     if prop_name and not any(mem.name == prop_name for mem in processed_members.values()):
                          processed_prop = self._process_static_property(prop_data, container_element)
                          if processed_prop:
                               processed_static_props[processed_prop.name] = processed_prop

                container_element.children.extend(list(processed_static_props.values()))

                # Sort all children by start line
                container_element.children.sort(key=lambda child: child.range.start_line if child.range else float('inf'))

                processed_containers.append(container_element)

            except (ValidationError, Exception) as e:
                logger.error(f"Failed to process container (TS) '{container_name}': {e}. Data: {container_data}", exc_info=True)

        return processed_containers

    # --- Helper methods ---

    def _build_lookup(self, items: List[Dict], key_field: str) -> Dict[str, List[Dict]]:
         """ Helper to group items by a specific key field. """
         lookup = {}
         for item in items:
             if isinstance(item, dict) and key_field in item:
                 key_value = item[key_field]
                 if key_value not in lookup:
                     lookup[key_value] = []
                 lookup[key_value].append(item)
         return lookup

    def _process_parameters(self, element: 'CodeElement', params_data: List[Dict]) -> List['CodeElement']:
        """ Processes raw parameter data into CodeElement objects. """
        param_elements = []
        parent_path = f'{element.parent_name}.{element.name}' if element.parent_name else element.name
        for i, param in enumerate(params_data):
            if not isinstance(param, dict):
                logger.warning(f'Skipping non-dict item in params_data for {parent_path} (TS): {type(param)}')
                continue
            name = param.get('name')
            if name:
                try:
                    # Use index in name temporarily if real ranges aren't available yet
                    param_name_for_element = f"{name}" # Could add index: _{i}
                    param_content = name # Basic content, could be enhanced
                    # Parameter range is tricky without AST nodes passed through
                    param_element = CodeElement(
                        type=CodeElementType.PARAMETER,
                        name=name, # Actual name
                        content=param_content,
                        parent_name=parent_path,
                        value_type=param.get('type'),
                        additional_data={'optional': param.get('optional', False), 'default': param.get('default')}
                        # Range ideally comes from extractor, but is None here
                    )
                    param_elements.append(param_element)
                except (ValidationError, Exception) as e:
                    logger.error(f"Failed to create parameter CodeElement for '{name}' in {parent_path} (TS): {e}", exc_info=True)
            else:
                logger.warning(f'Skipping parameter data without a name for {parent_path} (TS): {param}')
        return param_elements

    def _process_return_value(self, element: 'CodeElement', return_info: Dict) -> Optional['CodeElement']:
        """ Processes raw return info into a CodeElement. """
        if not isinstance(return_info, dict):
            logger.warning(f'Invalid return_info format for {element.name} (TS): {type(return_info)}')
            return None

        return_type = return_info.get('return_type')
        return_values = return_info.get('return_values', []) # Extractor should provide this if possible

        # Only create element if type is specified OR extractor found return statements
        if not return_type and not return_values:
            return None # No return type and no return statements found

        parent_path = f'{element.parent_name}.{element.name}' if element.parent_name else element.name
        try:
            # Content could be the type string, or represent the return statements? Use type for now.
            return_content = return_type if return_type else "return"
            return_element = CodeElement(
                type=CodeElementType.RETURN_VALUE,
                name=f'{element.name}_return',
                content=return_content,
                parent_name=parent_path,
                value_type=return_type,
                additional_data={'values': return_values}
                # Range ideally comes from extractor (e.g. range of ': type'), but is None here
            )
            return return_element
        except (ValidationError, Exception) as e:
            logger.error(f'Failed to create return value CodeElement for {element.name} (TS): {e}', exc_info=True)
            return None

    def _process_decorators(self, element_data: Dict, element_name_for_parent: str) -> List['CodeElement']:
        """ Processes raw decorator data into CodeElement objects. """
        decorator_elements = []
        decorators_raw = element_data.get('decorators', [])
        parent_class = element_data.get('class_name') # Check if element is member
        full_parent_name = f'{parent_class}.{element_name_for_parent}' if parent_class else element_name_for_parent

        if not isinstance(decorators_raw, list):
            logger.warning(f'Invalid decorators format for {full_parent_name} (TS): Expected list, got {type(decorators_raw)}')
            return []

        for dec_data in decorators_raw:
            if not isinstance(dec_data, dict):
                logger.warning(f'Skipping invalid decorator data format for {full_parent_name} (TS): {dec_data}')
                continue

            name = dec_data.get('name')
            content = dec_data.get('content')
            range_data = dec_data.get('range') # Expecting {'start': {'line': L, 'column': C}, 'end': ...}

            if name and content:
                decorator_range = None
                if isinstance(range_data, dict):
                    try:
                        # Adapt to potential variations in range data structure
                        start = range_data.get('start', {})
                        end = range_data.get('end', {})
                        start_line = start.get('line', start.get('start_line'))
                        start_col = start.get('column', start.get('start_column', 0))
                        end_line = end.get('line', end.get('end_line'))
                        end_col = end.get('column', end.get('end_column', 0))

                        if isinstance(start_line, int) and isinstance(end_line, int) and start_line > 0 and end_line >= start_line:
                            # Ensure columns are integers
                            start_col_int = start_col if isinstance(start_col, int) else 0
                            end_col_int = end_col if isinstance(end_col, int) else 0
                            decorator_range = CodeRange(start_line=start_line, start_column=start_col_int, end_line=end_line, end_column=end_col_int)
                        else:
                             logger.warning(f"Invalid line numbers for decorator '{name}' range (TS): start={start_line}, end={end_line}")
                    except (ValidationError, KeyError, Exception) as e:
                        logger.warning(f"Error creating CodeRange for decorator '{name}' (TS): {e}. Range data: {range_data}", exc_info=False)
                elif range_data is not None:
                     logger.warning(f"Invalid range format for decorator '{name}' (TS): {type(range_data)}")

                try:
                    decorator_element = CodeElement(
                        type=CodeElementType.DECORATOR,
                        name=name,
                        content=content,
                        range=decorator_range,
                        parent_name=full_parent_name
                    )
                    decorator_elements.append(decorator_element)
                except (ValidationError, Exception) as e:
                    logger.error(f"Failed to create decorator CodeElement for '{name}' in {full_parent_name} (TS): {e}", exc_info=True)
            else:
                logger.warning(f'Skipping decorator for {full_parent_name} (TS) without name or content: {dec_data}')
        return decorator_elements

    def _process_member_element(self, member_data: Dict, parent_container_element: 'CodeElement') -> Optional['CodeElement']:
         """
         Process raw member data (method, property, getter, setter) into a CodeElement.
         Determines the specific type (METHOD, PROPERTY_GETTER, PROPERTY_SETTER, PROPERTY).
         """
         element_name = member_data.get('name', 'unknown_member')
         parent_name = parent_container_element.name
         initial_type_str = member_data.get('type', CodeElementType.METHOD.value) # Default guess
         logger.debug(f'PostProcessing member (TS): {element_name} (initial type: {initial_type_str}) in {parent_name}')

         try:
             element_type_enum = CodeElementType(initial_type_str) if initial_type_str in CodeElementType._value2member_map_ else CodeElementType.METHOD

             # Refine type based on TS specifics (e.g., 'get'/'set' keywords, decorators)
             content = member_data.get('content', '')
             decorators = member_data.get('decorators', []) # Expect list of dicts from extractor
             is_getter = False
             is_setter = False
             is_property_field = False # Is it a class field/property definition?

             # Check for 'get'/'set' keywords (more reliable than just content matching)
             # This relies on the extractor providing accurate initial type or specific flags
             if element_type_enum == CodeElementType.PROPERTY_GETTER:
                  is_getter = True
             elif element_type_enum == CodeElementType.PROPERTY_SETTER:
                  is_setter = True
             # Check for common Angular property decorators
             angular_prop_decorators = ['Input', 'Output', 'ViewChild', 'ContentChild']
             if any(d.get('name') in angular_prop_decorators for d in decorators if isinstance(d, dict)):
                  is_property_field = True
                  element_type_enum = CodeElementType.PROPERTY

             # If it looks like a field definition (often has no function body markers like '() =>' or 'function()')
             # And might just be name: type; or name = value;
             definition_line = content.splitlines()[0].strip() if content else ''
             # Heuristic: if it doesn't look like a function/method call/def and isn't getter/setter
             if not is_getter and not is_setter and '(' not in definition_line and '=>' not in definition_line and 'function' not in definition_line:
                   # It's likely a property field if it has type annotation or initializer
                   if ':' in definition_line or '=' in definition_line:
                        is_property_field = True
                        element_type_enum = CodeElementType.PROPERTY

             # Final type assignment - prioritize getter/setter if detected
             if is_setter:
                  element_type_enum = CodeElementType.PROPERTY_SETTER
             elif is_getter:
                  element_type_enum = CodeElementType.PROPERTY_GETTER
             elif is_property_field:
                  element_type_enum = CodeElementType.PROPERTY
             # else keep as METHOD (or whatever initial type was)

             member_data['type'] = element_type_enum.value # Update the data dict

             element = CodeElement.from_dict(member_data)
             element.parent_name = parent_name

             # Process children
             element.children.extend(self._process_decorators(member_data, element_name))
             # Only process params/return for methods/getters/setters
             if element_type_enum in [CodeElementType.METHOD, CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER]:
                 element.children.extend(self._process_parameters(element, member_data.get('parameters', [])))
                 return_element = self._process_return_value(element, member_data.get('return_info', {}))
                 if return_element:
                     element.children.append(return_element)

             # Sort children by start line
             element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))

             return element
         except (ValidationError, Exception) as e:
             logger.error(f"Failed to process member element '{element_name}' in container '{parent_name}' (TS): {e}. Data: {member_data}", exc_info=True)
             return None

    def _process_static_property(self, prop_data: Dict, parent_container_element: 'CodeElement') -> Optional['CodeElement']:
        """ Processes raw static property data into a CodeElement. """
        prop_name = prop_data.get('name', 'unknown_static')
        parent_name = parent_container_element.name
        logger.debug(f'Processing static property (TS): {prop_name} in {parent_name}')

        if not isinstance(prop_data, dict):
            logger.warning(f'Skipping non-dict item in static_props data for {parent_name} (TS): {type(prop_data)}')
            return None

        # Ensure type is set
        prop_data['type'] = CodeElementType.STATIC_PROPERTY.value

        try:
            element = CodeElement.from_dict(prop_data)
            element.parent_name = parent_name
            # Value type and value might be directly in prop_data from extractor
            element.value_type = prop_data.get('value_type')
            if 'value' in prop_data:
                element.additional_data['value'] = prop_data.get('value')

            # Process decorators if any were extracted for the static property
            element.children.extend(self._process_decorators(prop_data, prop_name))
            element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))

            return element
        except (ValidationError, Exception) as e:
            logger.error(f"Failed to process static property '{prop_name}' in container '{parent_name}' (TS): {e}. Data: {prop_data}", exc_info=True)
            return None