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

    # process_imports and process_classes remain the same as the previous step
    def process_imports(self, raw_imports: List[Dict]) -> List[CodeElement]:
        """ Processes raw import data into CodeElement objects. """
        processed_imports = []
        if not raw_imports:
            logger.debug('ProcessImports (TS): No raw imports received.')
            return []
        valid_imports = [imp for imp in raw_imports if isinstance(imp, dict) and 'range' in imp and imp.get('type') == CodeElementType.IMPORT.value]
        if not valid_imports:
             if len(raw_imports) == 1 and raw_imports[0].get('name') == 'imports' and 'individual_imports' in raw_imports[0].get('additional_data', {}):
                  logger.debug("ProcessImports (TS): Received already combined import block.")
                  try:
                      combined_element = CodeElement.from_dict(raw_imports[0])
                      return [combined_element]
                  except (ValidationError, Exception) as e:
                      logger.error(f"ProcessImports (TS): Failed to process pre-combined import block: {e}", exc_info=True)
                      return []
             else:
                  logger.debug('ProcessImports (TS): No valid individual or combined imports found.')
                  return []
        logger.debug(f"ProcessImports (TS): Processing {len(valid_imports)} individual import dicts to combine.")
        try:
            valid_imports.sort(key=lambda x: x.get('range', {}).get('start', {}).get('line', float('inf')))
        except Exception as e:
            logger.error(f'ProcessImports (TS): Error sorting valid_imports: {e}. Proceeding unsorted.', exc_info=True)
        first_import = valid_imports[0]; last_import = valid_imports[-1]
        first_range = first_import.get('range', {}); last_range = last_import.get('range', {})
        start_data = first_range.get('start', {}); end_data = last_range.get('end', {})
        start_line = start_data.get('line'); start_col = start_data.get('column', 0)
        end_line = end_data.get('line'); end_col = end_data.get('column', 0)
        combined_range = None
        if isinstance(start_line, int) and isinstance(end_line, int) and start_line > 0 and end_line >= start_line:
            try:
                start_col_int = start_col if isinstance(start_col, int) else 0
                end_col_int = end_col if isinstance(end_col, int) else 0
                combined_range = CodeRange(start_line=start_line, start_column=start_col_int, end_line=end_line, end_column=end_col_int)
            except (ValidationError, Exception) as e: logger.error(f'ProcessImports (TS): Failed to create combined CodeRange: {e}', exc_info=True)
        else: logger.warning(f'ProcessImports (TS): Invalid lines for combined range: start={start_line}, end={end_line}.')
        combined_content = '\n'.join([imp.get('content', '') for imp in valid_imports])
        try:
            combined_element = CodeElement(type=CodeElementType.IMPORT, name='imports', content=combined_content, range=combined_range, additional_data={'individual_imports': valid_imports})
            logger.debug("ProcessImports (TS): Successfully created combined 'imports' CodeElement from individual parts.")
            return [combined_element]
        except (ValidationError, Exception) as e:
            logger.error(f"ProcessImports (TS): Failed to create combined 'imports' CodeElement: {e}", exc_info=True)
            return []

    def process_functions(self, raw_functions: List[Dict]) -> List[CodeElement]:
        """ Processes raw function data into CodeElement objects. (Detailed Children) """
        processed_functions = []
        for func_data in raw_functions:
            if not isinstance(func_data, dict):
                logger.warning(f'Skipping non-dict item in raw_functions (TS): {type(func_data)}')
                continue
            func_name = func_data.get('name', 'unknown_func')
            logger.debug(f'Processing function (TS Detailed): {func_name}')
            func_data['type'] = CodeElementType.FUNCTION.value
            try:
                # Create the main function element first
                func_element = CodeElement.from_dict(func_data)
                func_element.parent_name = None # Standalone function

                # --- Process children using helpers ---
                func_element.children.extend(self._process_decorators(func_data, func_name))
                # Use the potentially detailed parameters list from the enhanced extractor
                func_element.children.extend(self._process_parameters(func_element, func_data.get('parameters', [])))
                # Use the potentially detailed return info from the enhanced extractor
                return_element = self._process_return_value(func_element, func_data.get('return_info', {}))
                if return_element:
                    func_element.children.append(return_element)
                # --------------------------------------

                func_element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))
                processed_functions.append(func_element)
            except (ValidationError, Exception) as e:
                logger.error(f"Failed to process function (TS Detailed) '{func_name}': {e}. Data: {func_data}", exc_info=True)
        return processed_functions

    def process_classes(self, raw_classes: List[Dict], members: List[Dict], static_props: List[Dict]) -> List[CodeElement]:
        """ Processes raw class/interface data, associating members and static properties. """
        # (Keep the existing implementation from the previous step)
        processed_containers = []
        member_lookup = self._build_lookup(members, 'class_name')
        static_prop_lookup = self._build_lookup(static_props, 'class_name')
        for container_data in raw_classes:
            if not isinstance(container_data, dict): continue
            container_name = container_data.get('name'); container_type_str = container_data.get('type', CodeElementType.CLASS.value)
            logger.debug(f'Processing container (TS): {container_name} (type: {container_type_str})')
            if not container_name: logger.error(f'Found container definition without a name (TS)! Data: {container_data}'); continue
            try: container_type = CodeElementType(container_type_str); container_data['type'] = container_type.value
            except ValueError: logger.error(f"Invalid container type '{container_type_str}' for {container_name}. Defaulting to CLASS."); container_type = CodeElementType.CLASS; container_data['type'] = container_type.value
            try:
                container_element = CodeElement.from_dict(container_data); container_element.parent_name = None
                container_element.children.extend(self._process_decorators(container_data, container_name))
                members_for_this = member_lookup.get(container_name, [])
                members_for_this.sort(key=lambda m: m.get('definition_start_line', m.get('range', {}).get('start', {}).get('line', 0)))
                processed_members = {}
                for member_data in members_for_this:
                    if not isinstance(member_data, dict): continue
                    processed_member = self._process_member_element(member_data, container_element)
                    if processed_member: processed_members[(processed_member.type.value, processed_member.name)] = processed_member
                container_element.children.extend(list(processed_members.values()))
                static_props_for_this = static_prop_lookup.get(container_name, [])
                static_props_for_this.sort(key=lambda p: p.get('range', {}).get('start', {}).get('line', 0))
                processed_static_props = {}
                for prop_data in static_props_for_this:
                     if not isinstance(prop_data, dict): continue
                     prop_name = prop_data.get('name')
                     if prop_name and not any(mem.name == prop_name for mem in processed_members.values()):
                          processed_prop = self._process_static_property(prop_data, container_element)
                          if processed_prop: processed_static_props[processed_prop.name] = processed_prop
                container_element.children.extend(list(processed_static_props.values()))
                container_element.children.sort(key=lambda child: child.range.start_line if child.range else float('inf'))
                processed_containers.append(container_element)
            except (ValidationError, Exception) as e: logger.error(f"Failed to process container (TS) '{container_name}': {e}. Data: {container_data}", exc_info=True)
        return processed_containers

    # --- Helper methods ---

    def _build_lookup(self, items: List[Dict], key_field: str) -> Dict[str, List[Dict]]:
         """ Helper to group items by a specific key field. """
         lookup = {}
         for item in items:
             if isinstance(item, dict) and key_field in item:
                 key_value = item[key_field]
                 if key_value not in lookup: lookup[key_value] = []
                 lookup[key_value].append(item)
         return lookup

    def _process_parameters(self, element: 'CodeElement', params_data: List[Dict]) -> List['CodeElement']:
        """ Processes raw parameter data into CodeElement objects. (TS Enhanced)"""
        param_elements = []
        parent_path = f'{element.parent_name}.{element.name}' if element.parent_name else element.name
        for i, param in enumerate(params_data):
            if not isinstance(param, dict): continue
            name = param.get('name')
            if name:
                try:
                    # Use name provided by the detailed extractor
                    param_content = name # Or more detailed representation if available
                    value_type = param.get('type') # Get type extracted
                    additional_data = {
                         'optional': param.get('optional', False),
                         'default': param.get('default'),
                         # Add other TS specific things if extractor provides them (e.g., 'readonly')
                    }
                    # Parameter range might still be tricky unless extractor provides node refs
                    param_element = CodeElement(
                        type=CodeElementType.PARAMETER, name=name, content=param_content,
                        parent_name=parent_path, value_type=value_type,
                        additional_data=additional_data
                    )
                    param_elements.append(param_element)
                except (ValidationError, Exception) as e:
                    logger.error(f"Failed to create parameter CodeElement for '{name}' in {parent_path} (TS): {e}", exc_info=False)
        return param_elements

    def _process_return_value(self, element: 'CodeElement', return_info: Dict) -> Optional['CodeElement']:
        """ Processes raw return info into a CodeElement. (TS Enhanced)"""
        if not isinstance(return_info, dict): return None
        # Get type directly from extractor result
        return_type = return_info.get('return_type')
        # 'return_values' might not be relevant if we only care about the annotation
        # return_values = return_info.get('return_values', [])
        if not return_type: return None # Only create if type annotation exists

        parent_path = f'{element.parent_name}.{element.name}' if element.parent_name else element.name
        try:
            return_content = return_type # Use the extracted type as content
            return_element = CodeElement(
                type=CodeElementType.RETURN_VALUE, name=f'{element.name}_return', content=return_content,
                parent_name=parent_path, value_type=return_type,
                # additional_data={'values': return_values} # Might omit values
            )
            return return_element
        except (ValidationError, Exception) as e:
            logger.error(f'Failed to create return value CodeElement for {element.name} (TS): {e}', exc_info=False)
            return None

    # _process_decorators, _process_member_element, _process_static_property
    # remain the same as the previous step for now. Further refinement needed for TS specifics.
    def _process_decorators(self, element_data: Dict, element_name_for_parent: str) -> List['CodeElement']:
        """ Processes raw decorator data into CodeElement objects. """
        decorator_elements = []
        decorators_raw = element_data.get('decorators', [])
        parent_class = element_data.get('class_name')
        full_parent_name = f'{parent_class}.{element_name_for_parent}' if parent_class else element_name_for_parent
        if not isinstance(decorators_raw, list): return []
        for dec_data in decorators_raw:
            if not isinstance(dec_data, dict): continue
            name = dec_data.get('name')
            content = dec_data.get('content')
            range_data = dec_data.get('range')
            if name and content:
                decorator_range = None
                if isinstance(range_data, dict):
                    try:
                        start = range_data.get('start', {}); end = range_data.get('end', {})
                        start_line = start.get('line', start.get('start_line')); start_col = start.get('column', start.get('start_column', 0))
                        end_line = end.get('line', end.get('end_line')); end_col = end.get('column', end.get('end_column', 0))
                        if isinstance(start_line, int) and isinstance(end_line, int) and start_line > 0 and end_line >= start_line:
                            start_col_int = start_col if isinstance(start_col, int) else 0
                            end_col_int = end_col if isinstance(end_col, int) else 0
                            decorator_range = CodeRange(start_line=start_line, start_column=start_col_int, end_line=end_line, end_column=end_col_int)
                    except (ValidationError, KeyError, Exception): pass
                try:
                    decorator_element = CodeElement(type=CodeElementType.DECORATOR, name=name, content=content, range=decorator_range, parent_name=full_parent_name)
                    decorator_elements.append(decorator_element)
                except (ValidationError, Exception) as e: logger.error(f"Failed to create decorator CodeElement for '{name}' in {full_parent_name} (TS): {e}", exc_info=False)
        return decorator_elements

    def _process_member_element(self, member_data: Dict, parent_container_element: 'CodeElement') -> Optional['CodeElement']:
         """ Processes raw member data (method, property, etc.) into a CodeElement. """
         element_name = member_data.get('name', 'unknown_member'); parent_name = parent_container_element.name
         initial_type_str = member_data.get('type', CodeElementType.METHOD.value)
         logger.debug(f'PostProcessing member (TS): {element_name} (initial type: {initial_type_str}) in {parent_name}')
         try:
             element_type_enum = CodeElementType(initial_type_str) if initial_type_str in CodeElementType._value2member_map_ else CodeElementType.METHOD
             content = member_data.get('content', ''); decorators = member_data.get('decorators', [])
             is_getter = False; is_setter = False; is_property_field = False
             definition_line = content.splitlines()[0].strip() if content else ''
             if element_type_enum == CodeElementType.PROPERTY_GETTER or re.match(r'^\s*(static\s+)?get\s+\w+', definition_line): is_getter = True
             elif element_type_enum == CodeElementType.PROPERTY_SETTER or re.match(r'^\s*(static\s+)?set\s+\w+', definition_line): is_setter = True
             angular_prop_decorators = ['Input', 'Output', 'ViewChild', 'ContentChild']
             if any(d.get('name') in angular_prop_decorators for d in decorators if isinstance(d, dict)): is_property_field = True
             if not is_getter and not is_setter and '(' not in definition_line and '=>' not in definition_line and 'function' not in definition_line:
                  if ':' in definition_line or '=' in definition_line: is_property_field = True
             if is_setter: element_type_enum = CodeElementType.PROPERTY_SETTER
             elif is_getter: element_type_enum = CodeElementType.PROPERTY_GETTER
             elif is_property_field: element_type_enum = CodeElementType.PROPERTY
             member_data['type'] = element_type_enum.value
             element = CodeElement.from_dict(member_data); element.parent_name = parent_name
             element.children.extend(self._process_decorators(member_data, element_name))
             if element_type_enum in [CodeElementType.METHOD, CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER]:
                 # Use updated parameter/return processing
                 element.children.extend(self._process_parameters(element, member_data.get('parameters', [])))
                 return_element = self._process_return_value(element, member_data.get('return_info', {}))
                 if return_element: element.children.append(return_element)
             element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))
             return element
         except (ValidationError, Exception) as e:
             logger.error(f"Failed to process member element '{element_name}' in container '{parent_name}' (TS): {e}. Data: {member_data}", exc_info=False)
             return None

    def _process_static_property(self, prop_data: Dict, parent_container_element: 'CodeElement') -> Optional['CodeElement']:
        """ Processes raw static property data into a CodeElement. """
        prop_name = prop_data.get('name', 'unknown_static'); parent_name = parent_container_element.name
        logger.debug(f'Processing static property (TS): {prop_name} in {parent_name}')
        if not isinstance(prop_data, dict): return None
        prop_data['type'] = CodeElementType.STATIC_PROPERTY.value
        try:
            element = CodeElement.from_dict(prop_data); element.parent_name = parent_name
            element.value_type = prop_data.get('value_type')
            if 'value' in prop_data: element.additional_data['value'] = prop_data.get('value')
            element.children.extend(self._process_decorators(prop_data, prop_name))
            element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))
            return element
        except (ValidationError, Exception) as e:
            logger.error(f"Failed to process static property '{prop_name}' in container '{parent_name}' (TS): {e}. Data: {prop_data}", exc_info=False)
            return None

