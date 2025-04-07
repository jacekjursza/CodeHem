import logging
from typing import List, Dict, Optional
from codehem.models.code_element import CodeElement, CodeRange
from codehem.models.enums import CodeElementType
from pydantic import ValidationError
from ..post_processor_base import BaseExtractionPostProcessor

logger = logging.getLogger(__name__)

class TypeScriptExtractionPostProcessor(BaseExtractionPostProcessor):
    """
    TypeScript/JavaScript specific implementation of extraction post-processing.
    Transforms raw extraction dicts into structured CodeElement objects.
    V3: Adds helper for decorator processing, passes decorator lookup.
    """

    # --- process_imports (unchanged from previous thought process, assuming it's mostly correct) ---
    def process_imports(self, raw_imports: List[Dict]) -> List[CodeElement]:
        """Processes raw import data into CodeElement objects."""
        processed_imports = []
        if not raw_imports:
            logger.debug('ProcessImports (TS): No raw imports received.')
            return []

        # Check if already combined
        if len(raw_imports) == 1 and raw_imports[0].get('name') == 'imports' and ('individual_imports' in raw_imports[0].get('additional_data', {})):
            logger.debug('ProcessImports (TS): Received already combined import block.')
            try:
                # Ensure type is correct enum value
                raw_imports[0]['type'] = CodeElementType.IMPORT.value
                combined_element = CodeElement.from_dict(raw_imports[0])
                return [combined_element]
            except (ValidationError, Exception) as e:
                logger.error(f'ProcessImports (TS): Failed to process pre-combined import block: {e}', exc_info=True)
                return [] # Return empty on error

        # Filter for valid individual import dicts
        valid_imports = [imp for imp in raw_imports if isinstance(imp, dict) and 'range' in imp and imp.get('type') == CodeElementType.IMPORT.value]

        if not valid_imports:
            logger.debug('ProcessImports (TS): No valid individual imports found to combine.')
            return []

        logger.debug(f'ProcessImports (TS): Processing {len(valid_imports)} individual import dicts to combine.')

        # Sort by start line
        try:
            valid_imports.sort(key=lambda x: x.get('range', {}).get('start', {}).get('line', float('inf')))
        except Exception as e:
            logger.error(f'ProcessImports (TS): Error sorting valid_imports: {e}. Proceeding unsorted.', exc_info=True)
            # Re-filter just in case sorting failed due to bad data missed earlier
            valid_imports = [imp for imp in raw_imports if isinstance(imp, dict) and 'range' in imp and imp.get('type') == CodeElementType.IMPORT.value]
            if not valid_imports: return [] # If still no valid imports, return empty

        # Combine imports
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
                start_col_int = start_col if isinstance(start_col, int) else 0
                end_col_int = end_col if isinstance(end_col, int) else 0
                # Ensure lines are at least 1
                start_line = max(1, start_line)
                end_line = max(start_line, end_line) # Ensure end is not before start
                combined_range = CodeRange(start_line=start_line, start_column=start_col_int, end_line=end_line, end_column=end_col_int)
            except (ValidationError, Exception) as e:
                logger.error(f'ProcessImports (TS): Failed to create combined CodeRange: {e}', exc_info=True)
        else:
            logger.warning(f'ProcessImports (TS): Invalid calculated lines for combined range: start={start_line}, end={end_line}. Range will be None.')

        # Join content, handling potential non-strings gracefully
        combined_content = '\n'.join([imp.get('content', '') for imp in valid_imports if isinstance(imp.get('content'), str)])

        # Create combined element
        try:
            combined_element = CodeElement(
                type=CodeElementType.IMPORT,
                name='imports',
                content=combined_content,
                range=combined_range,
                additional_data={'individual_imports': valid_imports} # Keep original data if needed
            )
            logger.debug("ProcessImports (TS): Successfully created combined 'imports' CodeElement from individual parts.")
            return [combined_element]
        except (ValidationError, Exception) as e:
            logger.error(f"ProcessImports (TS): Failed to create combined 'imports' CodeElement: {e}", exc_info=True)
            # Fallback: return individual elements if combination fails
            individual_elements = []
            for imp_data in valid_imports:
                try:
                    imp_data['type'] = CodeElementType.IMPORT.value
                    individual_elements.append(CodeElement.from_dict(imp_data))
                except Exception as ind_err:
                    logger.error(f'Failed to create individual import element: {ind_err}')
            return individual_elements

    # --- process_functions (unchanged from previous thought process) ---
    def process_functions(self, raw_functions: List[Dict], all_decorators: List[Dict]=None) -> List[CodeElement]:
        """Processes raw function data into CodeElement objects. Accepts all_decorators list."""
        processed_functions = []
        logger.debug(f'TS process_functions received {len(all_decorators or [])} total decorators to consider.')
        # Build decorator lookup based on parent_name extracted by DecoratorExtractor
        decorator_lookup = self._build_lookup(all_decorators, 'parent_name')

        for func_data in raw_functions or []:
            if not isinstance(func_data, dict):
                logger.warning(f'Skipping non-dict item in raw_functions (TS): {type(func_data)}')
                continue

            func_name = func_data.get('name', 'unknown_func')
            logger.debug(f'TS PostProcessor: Processing function: {func_name}') # MODIFIED LOG
            func_data['type'] = CodeElementType.FUNCTION.value # Ensure correct type

            try:
                func_element = CodeElement.from_dict(func_data)
                func_element.parent_name = None # Standalone functions have no parent element

                # Process and add associated decorators
                decorators_for_func = decorator_lookup.get(func_name, [])
                logger.debug(f"TS PostProcessor: Found {len(decorators_for_func)} decorators for function '{func_name}'") # ADDED LOG
                for dec_data in decorators_for_func:
                    try:
                        # Ensure parent_name is set correctly for the decorator element
                        dec_data['parent_name'] = func_name
                        decorator_child = self._process_decorator_element(dec_data) # Use helper
                        if decorator_child:
                            func_element.children.append(decorator_child)
                    except Exception as dec_err:
                        logger.error(f"Error processing decorator for function {func_name}: {dec_err}", exc_info=False)

                # Process parameters and return value
                func_element.children.extend(self._process_parameters(func_element, func_data.get('parameters', [])))
                return_element = self._process_return_value(func_element, func_data.get('return_info', {}))
                if return_element:
                    func_element.children.append(return_element)

                # Sort children (decorators, params, return) by start line
                func_element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))
                processed_functions.append(func_element)
                logger.debug(f"TS PostProcessor: Finished processing function {func_name}. Total children: {len(func_element.children)}") # ADDED LOG

            except (ValidationError, Exception) as e:
                logger.error(f"Failed to process function (TS) '{func_name}': {e}. Data: {func_data}", exc_info=True)

        logger.debug(f"TS PostProcessor: Finished process_functions. Returning {len(processed_functions)} functions.") # ADDED LOG
        return processed_functions

    # --- process_classes (modified as per patch) ---
    def process_classes(self, raw_classes: List[Dict], members: List[Dict], static_props: List[Dict], properties: List[Dict]=None, all_decorators: List[Dict]=None) -> List[CodeElement]:
        """Processes raw class/interface data, associating members, static properties, and regular properties.
        Accepts all_decorators list."""
        processed_containers = []
        member_lookup = self._build_lookup(members, 'class_name')
        static_prop_lookup = self._build_lookup(static_props, 'class_name')
        prop_lookup = self._build_lookup(properties, 'class_name')
        # Build a lookup for decorators based on their determined parent_name
        decorator_lookup = self._build_lookup(all_decorators, 'parent_name') # CHANGED: Use parent_name from decorator extraction

        logger.debug(f'TS process_classes received {len(raw_classes or [])} raw containers, {len(members)} members, {len(static_props)} static_props, {len(properties or [])} props, {len(all_decorators or [])} decorators.') # ADDED LOG

        for container_data in raw_classes or []:
            if not isinstance(container_data, dict):
                logger.warning(f'Skipping non-dict item in raw_classes (TS): {type(container_data)}')
                continue

            container_name = container_data.get('name')
            container_type_str = container_data.get('type', CodeElementType.CLASS.value)
            logger.debug(f'TS PostProcessor: Processing container: {container_name} (type: {container_type_str})') # MODIFIED LOG

            if not container_name:
                logger.error(f'Found container definition without a name (TS)! Data: {container_data}')
                continue

            # Ensure type is correctly set
            try:
                container_type = CodeElementType(container_type_str)
                container_data['type'] = container_type.value
            except ValueError:
                logger.error(f"Invalid container type '{container_type_str}' for {container_name}. Defaulting to CLASS.")
                container_type = CodeElementType.CLASS
                container_data['type'] = container_type.value

            try:
                container_element = CodeElement.from_dict(container_data)
                container_element.parent_name = None
                processed_children = {} # Use a dict to avoid duplicates if extractors overlap

                # Add decorators associated with the class/interface itself
                decorators_for_container = decorator_lookup.get(container_name, [])
                logger.debug(f"TS PostProcessor: Found {len(decorators_for_container)} decorators directly for container '{container_name}'") # ADDED LOG
                for dec_data in decorators_for_container:
                     try:
                         # Ensure parent_name is correctly set for the decorator element
                         dec_data['parent_name'] = container_name
                         decorator_child = self._process_decorator_element(dec_data) # Use helper
                         if decorator_child:
                             processed_children[decorator_child.type.value, decorator_child.name] = decorator_child
                     except Exception as dec_err:
                         logger.error(f"Error processing decorator for container {container_name}: {dec_err}", exc_info=False)

                # Process Members (Methods, Getters, Setters)
                members_for_this = member_lookup.get(container_name, [])
                members_for_this.sort(key=lambda m: m.get('definition_start_line', m.get('range', {}).get('start', {}).get('line', 0)))
                logger.debug(f"TS PostProcessor: Processing {len(members_for_this)} members for '{container_name}'") # ADDED LOG
                for member_data in members_for_this:
                    if not isinstance(member_data, dict):
                        continue
                    # Pass decorator lookup to member processing
                    processed_member = self._process_member_element(member_data, container_element, decorator_lookup) # PASS decorator_lookup
                    if processed_member:
                        # Use tuple key (type, name) to prevent duplicates
                        processed_children[processed_member.type.value, processed_member.name] = processed_member

                # Process Regular Properties
                props_for_this = prop_lookup.get(container_name, [])
                props_for_this.sort(key=lambda p: p.get('range', {}).get('start', {}).get('line', 0))
                logger.debug(f"TS PostProcessor: Processing {len(props_for_this)} regular properties for '{container_name}'") # ADDED LOG
                for prop_data in props_for_this:
                    if not isinstance(prop_data, dict):
                        continue
                    prop_name = prop_data.get('name')
                    member_key = (CodeElementType.PROPERTY.value, prop_name) # Key to check
                    if prop_name and member_key not in processed_children:
                         # Pass decorator lookup
                        processed_prop = self._process_property(prop_data, container_element, decorator_lookup) # PASS decorator_lookup
                        if processed_prop:
                            processed_children[processed_prop.type.value, processed_prop.name] = processed_prop
                    elif prop_name and member_key in processed_children:
                        logger.debug(f"Skipping regular property '{prop_name}' as an element with the same name already exists.")

                # Process Static Properties
                static_props_for_this = static_prop_lookup.get(container_name, [])
                static_props_for_this.sort(key=lambda p: p.get('range', {}).get('start', {}).get('line', 0))
                logger.debug(f"TS PostProcessor: Processing {len(static_props_for_this)} static properties for '{container_name}'") # ADDED LOG
                for prop_data in static_props_for_this:
                    if not isinstance(prop_data, dict):
                        continue
                    prop_name = prop_data.get('name')
                    member_key = (CodeElementType.STATIC_PROPERTY.value, prop_name) # Key to check
                    if prop_name and member_key not in processed_children:
                         # Pass decorator lookup
                        processed_prop = self._process_static_property(prop_data, container_element, decorator_lookup) # PASS decorator_lookup
                        if processed_prop:
                            processed_children[processed_prop.type.value, processed_prop.name] = processed_prop
                    elif prop_name:
                        logger.debug(f"Skipping static property '{prop_name}' as an element with the same name already exists.")

                # Finalize children
                container_element.children = list(processed_children.values())
                container_element.children.sort(key=lambda child: child.range.start_line if child.range else float('inf'))
                processed_containers.append(container_element)
                logger.debug(f"TS PostProcessor: Finished processing container '{container_name}', added {len(container_element.children)} children.") # ADDED LOG

            except (ValidationError, Exception) as e:
                logger.error(f"Failed to process container (TS) '{container_name}': {e}. Data: {container_data}", exc_info=True)

        logger.debug(f"TS PostProcessor: Finished process_classes. Returning {len(processed_containers)} containers.") # ADDED LOG
        return processed_containers

    # --- _process_property (modified as per patch) ---
    def _process_property(self, prop_data: Dict, parent_container_element: 'CodeElement', decorator_lookup: Dict[str, List[Dict]]) -> Optional['CodeElement']:
        """Processes raw regular property (field) data into a CodeElement."""
        prop_name = prop_data.get('name', 'unknown_property')
        parent_name = parent_container_element.name
        logger.debug(f'TS PostProcessor: Processing property: {parent_name}.{prop_name}') # MODIFIED LOG
        if not isinstance(prop_data, dict):
            logger.warning(f'Skipping non-dict item in prop data for {parent_name} (TS): {type(prop_data)}')
            return None

        prop_data['type'] = CodeElementType.PROPERTY.value
        try:
            element = CodeElement.from_dict(prop_data)
            element.parent_name = parent_name

            # Add type info if missing
            if element.value_type is None:
                element.value_type = prop_data.get('value_type')

            # Add value info if missing in additional_data
            if 'value' not in element.additional_data and 'value' in prop_data:
                element.additional_data['value'] = prop_data.get('value')

            # Process and add associated decorators
            full_prop_name_for_lookup = f"{parent_name}.{prop_name}"
            decorators_for_prop = decorator_lookup.get(full_prop_name_for_lookup, [])
            logger.debug(f"TS PostProcessor: Found {len(decorators_for_prop)} decorators for property '{full_prop_name_for_lookup}'") # ADDED LOG
            for dec_data in decorators_for_prop:
                 try:
                     # Ensure parent_name is set correctly for the decorator CodeElement
                     dec_data['parent_name'] = full_prop_name_for_lookup
                     decorator_child = self._process_decorator_element(dec_data) # Use helper
                     if decorator_child:
                         element.children.append(decorator_child)
                 except Exception as dec_err:
                     logger.error(f"Error processing decorator for property {full_prop_name_for_lookup}: {dec_err}", exc_info=False)

            element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))
            logger.debug(f"TS PostProcessor: Finished processing property {parent_name}.{prop_name}. Total children: {len(element.children)}") # ADDED LOG
            return element
        except (ValidationError, Exception) as e:
            logger.error(f"Failed to process property '{prop_name}' in container '{parent_name}' (TS): {e}. Data: {prop_data}", exc_info=False)
            return None

    # --- _build_lookup (unchanged from previous thought process) ---
    def _build_lookup(self, items: List[Dict], key_field: str) -> Dict[str, List[Dict]]:
        """Helper to group items by a specific key field."""
        lookup = {}
        if not items: return lookup # Handle empty list
        for item in items:
            if isinstance(item, dict) and key_field in item:
                key_value = item[key_field]
                # Ensure key is hashable and not None
                if key_value is not None and isinstance(key_value, (str, int, float, bool)):
                    if key_value not in lookup:
                        lookup[key_value] = []
                    lookup[key_value].append(item)
                else:
                    # Log if key is problematic (e.g., list, dict, None)
                     logger.warning(f"Skipping item in _build_lookup due to unhashable or None key '{key_value}' in field '{key_field}'. Item keys: {list(item.keys())}")
            elif isinstance(item, dict):
                logger.warning(f"Item is missing key_field '{key_field}' in _build_lookup. Item keys: {list(item.keys())}")
            # else: # Optional: Log if item is not a dict at all
            #    logger.warning(f"Skipping non-dict item in _build_lookup: {type(item)}")
        return lookup

    # --- _process_parameters (unchanged from previous thought process) ---
    def _process_parameters(self, element: 'CodeElement', params_data: List[Dict]) -> List['CodeElement']:
        """Processes raw parameter data into CodeElement objects (TS Enhanced)"""
        param_elements = []
        parent_path = f'{element.parent_name}.{element.name}' if element.parent_name else element.name
        for i, param in enumerate(params_data):
            if not isinstance(param, dict):
                logger.warning(f'Skipping non-dict item in params_data for {parent_path} (TS): {type(param)}')
                continue

            name = param.get('name')
            if name:
                try:
                    param_content_parts = [name]
                    value_type = param.get('type')
                    # Determine if '?' should be added for optional parameters *without* defaults
                    is_optional_marker = param.get('optional', False) and not param.get('default')
                    if is_optional_marker:
                        param_content_parts[0] += '?' # Add '?' directly after name

                    # Add type annotation
                    if value_type:
                        param_content_parts.append(f': {value_type}')

                    # Add default value
                    default_value = param.get('default')
                    if default_value:
                        param_content_parts.append(f' = {default_value}')

                    param_content = ''.join(param_content_parts)

                    # Store optional and default in additional_data
                    additional_data = {'optional': param.get('optional', False), 'default': default_value}

                    # Create CodeElement for the parameter (range is typically None here)
                    param_element = CodeElement(
                        type=CodeElementType.PARAMETER,
                        name=name,
                        content=param_content,
                        parent_name=parent_path,
                        value_type=value_type,
                        additional_data=additional_data,
                        range=None # Parameter ranges are harder to get consistently here
                    )
                    param_elements.append(param_element)

                except (ValidationError, Exception) as e:
                    logger.error(f"Failed to create parameter CodeElement for '{name}' in {parent_path} (TS): {e}", exc_info=False)
            else:
                logger.warning(f'Skipping parameter data without name in {parent_path} (TS): {param}')
        return param_elements

    # --- _process_return_value (unchanged from previous thought process) ---
    def _process_return_value(self, element: 'CodeElement', return_info: Dict) -> Optional['CodeElement']:
        """Processes raw return info into a CodeElement (TS Enhanced)"""
        if not isinstance(return_info, dict):
            logger.warning(f'Invalid return_info format for {element.name} (TS): {type(return_info)}')
            return None

        return_type = return_info.get('return_type')

        # Only create return element if there's a type annotation
        if not return_type:
            return None

        parent_path = f'{element.parent_name}.{element.name}' if element.parent_name else element.name
        try:
            # Clean the type string (remove leading ':')
            cleaned_return_type = return_type.lstrip(':').strip() if isinstance(return_type, str) else return_type
            return_content = f': {cleaned_return_type}' # Content is just the type annotation part

            return_element = CodeElement(
                type=CodeElementType.RETURN_VALUE,
                name=f'{element.name}_return', # Consistent naming convention
                content=return_content,
                parent_name=parent_path,
                value_type=cleaned_return_type, # Store the cleaned type here
                range=None, # Range is hard to determine accurately here
                additional_data={'values': return_info.get('return_values', [])} # Keep raw return values if found
            )
            return return_element
        except (ValidationError, Exception) as e:
            logger.error(f'Failed to create return value CodeElement for {element.name} (TS): {e}', exc_info=False)
            return None

    # --- _process_decorators (modified as per patch) ---
    def _process_decorators(self, element_data: Dict, element_name_for_parent: str) -> List['CodeElement']:
        """Processes raw decorator data associated with a *specific element* into CodeElement objects."""
        # NOTE: This processes decorators passed *within* element_data (like from Python extractors)
        # For TypeScript, decorators are often extracted separately. Consider relying on the all_decorators list passed higher up.
        # This method is kept for potential compatibility but might need adjustment or removal for TS.

        decorator_elements = []
        decorators_raw = element_data.get('decorators', []) # Decorators found associated *by the initial extractor*
        parent_class = element_data.get('class_name')
        full_parent_name = f'{parent_class}.{element_name_for_parent}' if parent_class else element_name_for_parent

        logger.debug(f"TS PostProcessor: _process_decorators called for '{full_parent_name}'. Raw decorator data in element_data: {decorators_raw}") # ADDED LOG

        if not isinstance(decorators_raw, list):
            logger.warning(f'Invalid decorators format for {full_parent_name} (TS) within element_data: Expected list, got {type(decorators_raw)}')
            return []

        for dec_data in decorators_raw:
            try:
                 # Use helper to create CodeElement, ensures consistent processing
                 decorator_element = self._process_decorator_element(dec_data, full_parent_name)
                 if decorator_element:
                     decorator_elements.append(decorator_element)
            except Exception as e:
                 logger.error(f"Error processing decorator from element_data for {full_parent_name}: {e}", exc_info=False)

        logger.debug(f"TS PostProcessor: _process_decorators finished for '{full_parent_name}'. Found {len(decorator_elements)} decorators from element_data.") # ADDED LOG
        return decorator_elements

    # --- _process_member_element (modified as per patch) ---
    def _process_member_element(self, member_data: Dict, parent_container_element: 'CodeElement', decorator_lookup: Dict[str, List[Dict]]) -> Optional['CodeElement']:
        """
        Processes raw member data (method, property, getter, setter) into a CodeElement.
        V3: Accepts decorator_lookup to find associated decorators.
        """
        element_name = member_data.get('name', 'unknown_member')
        parent_name = parent_container_element.name
        member_type_str = member_data.get('type')

        if not member_type_str:
            logger.error(f"Member data for '{element_name}' in container '{parent_name}' (TS) is missing 'type'. Data: {member_data}")
            return None

        logger.debug(f'TS PostProcessor: Processing member: {parent_name}.{element_name} (type: {member_type_str})') # MODIFIED LOG

        try:
            element_type_enum = CodeElementType(member_type_str)
        except ValueError:
            logger.error(f"Invalid element type '{member_type_str}' provided by extractor for member '{element_name}' (TS). Skipping.")
            return None

        try:
            # Create CodeElement from raw data
            element = CodeElement.from_dict(member_data)
            element.parent_name = parent_name

            # Process and add associated decorators
            full_member_name_for_lookup = f"{parent_name}.{element_name}"
            decorators_for_member = decorator_lookup.get(full_member_name_for_lookup, [])
            logger.debug(f"TS PostProcessor: Found {len(decorators_for_member)} decorators for member '{full_member_name_for_lookup}'") # ADDED LOG
            for dec_data in decorators_for_member:
                 try:
                     # Ensure parent_name is set correctly for the decorator CodeElement
                     dec_data['parent_name'] = full_member_name_for_lookup
                     decorator_child = self._process_decorator_element(dec_data) # Use helper
                     if decorator_child:
                         element.children.append(decorator_child)
                 except Exception as dec_err:
                     logger.error(f"Error processing decorator for member {full_member_name_for_lookup}: {dec_err}", exc_info=False)

            # Process parameters and return value for relevant types
            if element_type_enum in [CodeElementType.METHOD, CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER]:
                logger.debug(f"TS PostProcessor: Processing parameters/return for {parent_name}.{element_name}") # ADDED LOG
                element.children.extend(self._process_parameters(element, member_data.get('parameters', [])))
                return_element = self._process_return_value(element, member_data.get('return_info', {}))
                if return_element:
                    element.children.append(return_element)

            # Additional processing for properties (already handled by _process_property/_process_static_property?)
            # This might be redundant if separate extractors are used and processed in process_classes
            # elif element_type_enum in [CodeElementType.PROPERTY, CodeElementType.STATIC_PROPERTY]:
            #     element.value_type = member_data.get('value_type')
            #     if 'value' in member_data.get('additional_data', {}):
            #         pass # Already set by from_dict
            #     elif 'value' in member_data:
            #         element.additional_data['value'] = member_data.get('value')

            # Sort children (decorators, params, return) by start line
            element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))
            logger.debug(f"TS PostProcessor: Finished processing member {parent_name}.{element_name}. Total children: {len(element.children)}") # ADDED LOG
            return element

        except (ValidationError, Exception) as e:
            logger.error(f"Failed to process member element '{element_name}' in container '{parent_name}' (TS V3): {e}. Data: {member_data}", exc_info=False)
            return None

    # --- _process_static_property (modified as per patch) ---
    def _process_static_property(self, prop_data: Dict, parent_container_element: 'CodeElement', decorator_lookup: Dict[str, List[Dict]]) -> Optional['CodeElement']:
        """Processes raw static property data into a CodeElement."""
        prop_name = prop_data.get('name', 'unknown_static')
        parent_name = parent_container_element.name
        logger.debug(f'TS PostProcessor: Processing static property: {parent_name}.{prop_name}') # MODIFIED LOG
        if not isinstance(prop_data, dict):
            logger.warning(f'Skipping non-dict item in static prop data for {parent_name} (TS): {type(prop_data)}')
            return None

        prop_data['type'] = CodeElementType.STATIC_PROPERTY.value
        try:
            element = CodeElement.from_dict(prop_data)
            element.parent_name = parent_name

            # Add type info if missing
            if element.value_type is None:
                element.value_type = prop_data.get('value_type')

            # Add value info if missing in additional_data
            if 'value' not in element.additional_data and 'value' in prop_data:
                element.additional_data['value'] = prop_data.get('value')

            # Process and add associated decorators
            full_prop_name_for_lookup = f"{parent_name}.{prop_name}"
            decorators_for_prop = decorator_lookup.get(full_prop_name_for_lookup, [])
            logger.debug(f"TS PostProcessor: Found {len(decorators_for_prop)} decorators for static property '{full_prop_name_for_lookup}'") # ADDED LOG
            for dec_data in decorators_for_prop:
                 try:
                     # Ensure parent_name is set correctly for the decorator CodeElement
                     dec_data['parent_name'] = full_prop_name_for_lookup
                     decorator_child = self._process_decorator_element(dec_data) # Use helper
                     if decorator_child:
                         element.children.append(decorator_child)
                 except Exception as dec_err:
                     logger.error(f"Error processing decorator for static property {full_prop_name_for_lookup}: {dec_err}", exc_info=False)

            element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))
            logger.debug(f"TS PostProcessor: Finished processing static property {parent_name}.{prop_name}. Total children: {len(element.children)}") # ADDED LOG
            return element
        except (ValidationError, Exception) as e:
            logger.error(f"Failed to process static property '{prop_name}' in container '{parent_name}' (TS): {e}. Data: {prop_data}", exc_info=False)
            return None

    # --- NEW HELPER METHOD ---
    def _process_decorator_element(self, dec_data: Dict, explicit_parent_name: Optional[str] = None) -> Optional[CodeElement]:
        """Helper to create a CodeElement for a decorator from its raw data."""
        if not isinstance(dec_data, dict):
            logger.warning(f"Skipping invalid decorator data (not a dict): {dec_data}")
            return None

        name = dec_data.get('name')
        content = dec_data.get('content')
        range_data = dec_data.get('range')
        # Use explicit parent name if provided, otherwise fallback to data from extractor
        parent_name = explicit_parent_name if explicit_parent_name else dec_data.get('parent_name')

        if not name or not content:
            logger.warning(f"Skipping decorator data missing name or content: Name='{name}', Content='{content is not None}'")
            return None

        decorator_range = None
        if isinstance(range_data, dict):
            try:
                start = range_data.get('start', {})
                end = range_data.get('end', {})
                start_line = start.get('line', start.get('start_line'))
                start_col = start.get('column', start.get('start_column', 0))
                end_line = end.get('line', end.get('end_line'))
                end_col = end.get('column', end.get('end_column', 0))

                if isinstance(start_line, int) and isinstance(end_line, int) and start_line > 0 and end_line >= start_line:
                    start_col_int = start_col if isinstance(start_col, int) else 0
                    end_col_int = end_col if isinstance(end_col, int) else 0
                    start_line = max(1, start_line)
                    end_line = max(start_line, end_line)
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
                parent_name=parent_name # Use the determined parent name
            )
            logger.debug(f"TS PostProcessor: Successfully created decorator CodeElement for '{name}' (parent: '{parent_name}')") # ADDED LOG
            return decorator_element
        except (ValidationError, Exception) as e:
            logger.error(f"Failed to create decorator CodeElement for '{name}' (parent: '{parent_name}'): {e}", exc_info=False)
            return None