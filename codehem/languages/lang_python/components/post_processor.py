"""
Python-specific post-processor implementation.

This module provides Python-specific implementation of the LanguagePostProcessor
class, transforming raw extraction data into structured CodeElement objects with
proper relationships.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from codehem.core.post_processors.base import LanguagePostProcessor
from codehem.models.enums import CodeElementType
from codehem.models.code_element import CodeElement, CodeElementsResult
from codehem.models.range import CodeRange
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class PythonPostProcessor(LanguagePostProcessor):
    """
    Python-specific implementation of the language post-processor.
    
    Transforms raw extraction data into structured CodeElement objects with proper
    relationships, handling Python-specific features like decorators, properties,
    and type annotations.
    """
    
    def __init__(self):
        """Initialize the Python post-processor."""
        super().__init__('python')
    
    def process_imports(self, raw_imports: List[Dict]) -> List[CodeElement]:
        """
        Process raw import data into CodeElement objects.
        
        For Python, imports are typically combined into a single CodeElement representing
        the import section of the file.
        
        Args:
            raw_imports: List of raw import dictionaries
            
        Returns:
            List of CodeElement objects representing imports
        """
        if not raw_imports:
            logger.debug("process_imports: No raw imports received, returning empty list.")
            return []
        
        # Filter out imports without range data
        valid_imports = [imp for imp in raw_imports if isinstance(imp, dict) and "range" in imp]
        if not valid_imports:
            logger.warning("process_imports: No valid raw imports with range data found.")
            return []
        
        # Sort imports by line number
        try:
            valid_imports.sort(key=lambda x: 
                x.get("range", {}).get("start", {}).get("line", float("inf"))
            )
            logger.debug(f"process_imports: Sorted {len(valid_imports)} valid imports by line.")
        except Exception as e:
            logger.error(
                f"process_imports: Error sorting valid_imports: {e}. Proceeding without sorting.",
                exc_info=True,
            )
            # Fallback to original list if sorting fails
            valid_imports = [imp for imp in raw_imports if isinstance(imp, dict) and "range" in imp]
            if not valid_imports:
                return []
        
        # Get range for combined imports
        first_import = valid_imports[0]
        last_import = valid_imports[-1]
        first_range = first_import.get("range", {})
        last_range = last_import.get("range", {})
        
        # Extract range information carefully
        start_data = first_range.get("start", {})
        end_data = last_range.get("end", {})
        start_line = start_data.get("line")
        start_col = start_data.get("column", 0)
        end_line = end_data.get("line")
        end_col = end_data.get("column", 0)
        
        # Create CodeRange if we have valid line numbers
        combined_range = None
        if (isinstance(start_line, int) and isinstance(end_line, int) and 
            start_line > 0 and end_line >= start_line):
            try:
                combined_range = CodeRange(
                    start_line=start_line,
                    start_column=start_col,
                    end_line=end_line,
                    end_column=end_col,
                )
                logger.debug(f"process_imports: Created combined CodeRange: {combined_range}")
            except (ValidationError, Exception) as e:
                logger.error(
                    f"process_imports: Failed to create combined CodeRange: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"process_imports: Invalid calculated lines for combined range: start={start_line}, end={end_line}. Range will be None."
            )
        
        # Combine content from all imports
        combined_content_parts = [
            imp.get("content", "")
            for imp in valid_imports
            if isinstance(imp.get("content"), str)
        ]
        combined_content = "\n".join(combined_content_parts)
        
        logger.debug(f"process_imports: Combining {len(valid_imports)} imports from line {start_line} to {end_line}.")
        
        try:
            # Create the combined CodeElement
            combined_element = CodeElement(
                type=CodeElementType.IMPORT,
                name="imports",  # Standardized name for the combined block
                content=combined_content,
                range=combined_range,
                additional_data={
                    "individual_imports": valid_imports  # Keep raw data for reference
                },
            )
            logger.debug("process_imports: Successfully created combined 'imports' CodeElement.")
            return [combined_element]
        except (ValidationError, Exception) as e:
            logger.error(
                f"process_imports: Failed to create combined 'imports' CodeElement: {e}",
                exc_info=True,
            )
            return []  # Return empty list on failure
    
    def process_functions(self, raw_functions: List[Dict], 
                        all_decorators: Optional[List[Dict]]=None) -> List[CodeElement]:
        """
        Process raw function data into CodeElement objects.
        
        Args:
            raw_functions: List of raw function dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing functions
        """
        processed_functions = []
        logger.debug(f"process_functions: Processing {len(raw_functions or [])} functions with {len(all_decorators or [])} decorators")
        
        # Build decorator lookup by parent name
        decorator_lookup = self._build_decorator_lookup(all_decorators)
        
        for function_data in raw_functions:
            if not isinstance(function_data, dict):
                logger.warning(f'process_functions: Skipping non-dict item: {type(function_data)}')
                continue
                
            func_name = function_data.get('name', 'unknown_func')
            logger.debug(f'process_functions: Processing function: {func_name}')
            
            # Ensure type is set correctly
            function_data['type'] = CodeElementType.FUNCTION.value
            
            try:
                # Create CodeElement from raw data
                func_element = CodeElement.from_dict(function_data)
                func_element.parent_name = None
                
                # Process decorators directly associated with the function
                func_element.children.extend(self._process_decorators(function_data))
                
                # Add decorators from the global decorator list
                if decorator_lookup:
                    func_decorators = decorator_lookup.get(func_name, [])
                    for dec_data in func_decorators:
                        decorator = self._process_decorator_element(dec_data)
                        if decorator:
                            func_element.children.append(decorator)
                
                # Process parameters
                func_element.children.extend(
                    self._process_parameters(func_element, function_data.get('parameters', []))
                )
                
                # Process return value
                return_element = self._process_return_value(
                    func_element, function_data.get('return_info', {})
                )
                if return_element:
                    func_element.children.append(return_element)
                
                processed_functions.append(func_element)
                
            except (ValidationError, Exception) as e:
                logger.error(f"process_functions: Failed to process function '{func_name}': {e}", exc_info=True)
        
        return processed_functions
    
    def process_classes(self, raw_classes: List[Dict], members: List[Dict], 
                      static_props: List[Dict], properties: Optional[List[Dict]]=None,
                      all_decorators: Optional[List[Dict]]=None) -> List[CodeElement]:
        """
        Process raw class data into CodeElement objects.
        
        Args:
            raw_classes: List of raw class dictionaries
            members: List of raw member dictionaries (methods, getters, setters)
            static_props: List of raw static property dictionaries
            properties: Optional list of raw property dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing classes with their members
        """
        processed_classes = []
        logger.debug(f"process_classes: Processing {len(raw_classes or [])} classes")
        
        # Build lookup dictionaries for efficient processing
        member_lookup = self._build_lookup(members, 'parent_name')
        static_prop_lookup = self._build_lookup(static_props, 'parent_name')
        property_lookup = self._build_lookup(properties or [], 'parent_name')
        decorator_lookup = self._build_decorator_lookup(all_decorators)
        
        # Process each class
        for class_data in raw_classes or []:
            if not isinstance(class_data, dict):
                logger.warning(f'process_classes: Skipping non-dict item: {type(class_data)}')
                continue
            
            class_name = class_data.get('name')
            if not class_name:
                logger.warning(f'process_classes: Found class without a name: {class_data}')
                continue
                
            logger.debug(f'process_classes: Processing class: {class_name}')
            
            # Ensure type is set correctly
            class_data['type'] = CodeElementType.CLASS.value
            
            try:
                # Create CodeElement from raw data
                class_element = CodeElement.from_dict(class_data)
                class_element.parent_name = None
                
                # Process decorators directly associated with the class
                class_element.children.extend(self._process_decorators(class_data))
                
                # Add decorators from the global decorator list
                if decorator_lookup:
                    class_decorators = decorator_lookup.get(class_name, [])
                    for dec_data in class_decorators:
                        decorator = self._process_decorator_element(dec_data)
                        if decorator:
                            class_element.children.append(decorator)
                
                # Process methods and properties
                processed_members = {}
                members_for_this_class = member_lookup.get(class_name, [])
                
                # Sort members by line number for consistent order
                members_for_this_class.sort(key=lambda m: 
                    m.get('definition_start_line', 
                          m.get('range', {}).get('start', {}).get('line', 0))
                )
                
                for member_data in members_for_this_class:
                    if not isinstance(member_data, dict):
                        continue
                        
                    processed_member = self._process_method_element(member_data, class_element)
                    if processed_member:
                        processed_members[(processed_member.type.value, processed_member.name)] = processed_member
                
                # Process static properties
                processed_static_props = {}
                static_props_for_this_class = static_prop_lookup.get(class_name, [])
                
                # Sort static properties by line number
                static_props_for_this_class.sort(key=lambda p: 
                    p.get('range', {}).get('start', {}).get('line', 0)
                )
                
                for prop_data in static_props_for_this_class:
                    if not isinstance(prop_data, dict):
                        continue
                        
                    prop_name = prop_data.get('name')
                    if prop_name and not any(key[1] == prop_name for key in processed_members.keys()):
                        processed_prop = self._process_static_property(prop_data, class_element)
                        if processed_prop:
                            processed_static_props[processed_prop.name] = processed_prop
                    elif prop_name:
                        logger.debug(f"process_classes: Skipping static property '{prop_name}' as a member with the same name already exists.")
                
                # Add all children to the class
                class_element.children.extend(list(processed_members.values()))
                class_element.children.extend(list(processed_static_props.values()))
                
                # Sort children by line number for consistent order
                class_element.children.sort(key=lambda child: 
                    child.range.start_line if child.range else float('inf')
                )
                
                processed_classes.append(class_element)
                
            except (ValidationError, Exception) as e:
                logger.error(f"process_classes: Failed to process class '{class_name}': {e}", exc_info=True)
        
        return processed_classes
    
    def _process_parameters(self, element: CodeElement, params_data: List[Dict]) -> List[CodeElement]:
        """
        Process raw parameter data into CodeElement objects.
        
        Args:
            element: The parent element (function or method)
            params_data: List of raw parameter dictionaries
            
        Returns:
            List of CodeElement objects representing parameters
        """
        param_elements = []
        parent_path = (
            f"{element.parent_name}.{element.name}"
            if element.parent_name
            else element.name
        )
        
        for param in params_data:
            if not isinstance(param, dict):
                logger.warning(
                    f"_process_parameters: Skipping non-dict item for {parent_path}: {type(param)}"
                )
                continue
                
            name = param.get("name")
            if not name:
                logger.warning(f"_process_parameters: Skipping parameter without a name for {parent_path}: {param}")
                continue
                
            try:
                param_element = CodeElement(
                    type=CodeElementType.PARAMETER,
                    name=name,
                    content=name,  # Content is just the name for parameters
                    parent_name=parent_path,
                    value_type=param.get("type"),
                    additional_data={
                        "optional": param.get("optional", False),
                        "default": param.get("default"),
                    },
                )
                param_elements.append(param_element)
            except (ValidationError, Exception) as e:
                logger.error(
                    f"_process_parameters: Failed to create parameter CodeElement for '{name}' in {parent_path}: {e}",
                    exc_info=True,
                )
        
        return param_elements
    
    def _process_return_value(self, element: CodeElement, return_info: Dict) -> Optional[CodeElement]:
        """
        Process raw return info into a CodeElement object.
        
        Args:
            element: The parent element (function or method)
            return_info: Raw return info dictionary
            
        Returns:
            CodeElement representing the return value or None if not applicable
        """
        if not isinstance(return_info, dict):
            logger.warning(f"_process_return_value: Invalid return_info format for {element.name}: {type(return_info)}")
            return None
            
        return_type = return_info.get("return_type")
        return_values = return_info.get("return_values", [])
        
        # Only create a return element if there's a type hint or explicit return values
        if not return_type and not return_values:
            return None
            
        parent_path = (
            f"{element.parent_name}.{element.name}"
            if element.parent_name
            else element.name
        )
        
        try:
            return_element = CodeElement(
                type=CodeElementType.RETURN_VALUE,
                name=f"{element.name}_return",  # Standardized name
                content=return_type or "",  # Content is the type hint string
                parent_name=parent_path,
                value_type=return_type,  # Store the type hint specifically
                additional_data={
                    "values": return_values  # Store observed return values
                },
            )
            return return_element
        except (ValidationError, Exception) as e:
            logger.error(f"_process_return_value: Failed to create return value CodeElement for {element.name}: {e}", exc_info=True)
            return None
    
    def _process_method_element(self, method_data: Dict, parent_class_element: CodeElement) -> Optional[CodeElement]:
        """
        Process raw method data into a CodeElement object.
        
        Handles classification of methods, property getters, and property setters
        based on decorators.
        
        Args:
            method_data: Raw method dictionary
            parent_class_element: The parent class CodeElement
            
        Returns:
            CodeElement representing the method or None if processing fails
        """
        element_name = method_data.get("name", "unknown_member")
        parent_name = parent_class_element.name
        initial_type_str = method_data.get("type", CodeElementType.METHOD.value)
        
        logger.debug(f"_process_method_element: Processing member: {element_name} (initial type: {initial_type_str}) in class {parent_name}")
        
        try:
            # Use METHOD as default if type is missing or invalid
            element_type_enum = (
                CodeElementType(initial_type_str)
                if initial_type_str in CodeElementType._value2member_map_
                else CodeElementType.METHOD
            )
            
            # Ensure data has valid type string
            method_data["type"] = element_type_enum.value
            
            # Create CodeElement from raw data
            element = CodeElement.from_dict(method_data)
            element.parent_name = parent_name
            
            # Classify based on decorators
            raw_decorators = method_data.get("decorators", [])
            is_getter = False
            is_setter = False
            
            for dec_info in raw_decorators:
                if not isinstance(dec_info, dict):
                    continue
                    
                dec_name = dec_info.get("name")
                if dec_name == "property":
                    is_getter = True
                    logger.debug(f"_process_method_element: Decorator '@property' found for {element_name}.")
                elif isinstance(dec_name, str) and dec_name == f"{element_name}.setter":
                    is_setter = True
                    logger.debug(f"_process_method_element: Decorator '@{element_name}.setter' found for {element_name}.")
                    break  # Setter is definitive
            
            # Update element type based on decorators
            if is_setter:
                element.type = CodeElementType.PROPERTY_SETTER
                logger.debug(f"_process_method_element: Classifying {element_name} as PROPERTY_SETTER.")
            elif is_getter:
                element.type = CodeElementType.PROPERTY_GETTER
                logger.debug(f"_process_method_element: Classifying {element_name} as PROPERTY_GETTER.")
            
            # Process children
            element.children.extend(self._process_decorators(method_data))
            element.children.extend(self._process_parameters(element, method_data.get("parameters", [])))
            
            return_element = self._process_return_value(element, method_data.get("return_info", {}))
            if return_element:
                element.children.append(return_element)
                
            return element
            
        except (ValidationError, Exception) as e:
            logger.error(f"_process_method_element: Failed to process method '{element_name}' in class '{parent_name}': {e}", exc_info=True)
            return None
    
    def _process_static_property(self, prop_data: Dict, parent_class_element: CodeElement) -> Optional[CodeElement]:
        """
        Process raw static property data into a CodeElement object.
        
        Args:
            prop_data: Raw static property dictionary
            parent_class_element: The parent class CodeElement
            
        Returns:
            CodeElement representing the static property or None if processing fails
        """
        prop_name = prop_data.get("name", "unknown_static")
        parent_name = parent_class_element.name
        
        logger.debug(f"_process_static_property: Processing static property: {prop_name} in class {parent_name}")
        
        if not isinstance(prop_data, dict):
            logger.warning(f"_process_static_property: Invalid prop_data format: {type(prop_data)}")
            return None
            
        # Ensure type is set correctly
        prop_data["type"] = CodeElementType.STATIC_PROPERTY.value
        
        try:
            # Create CodeElement from raw data
            element = CodeElement.from_dict(prop_data)
            element.parent_name = parent_name
            element.value_type = prop_data.get("value_type")  # Keep potential type hint
            
            # Store the extracted value if available
            if "value" in prop_data or "additional_data" in prop_data and "value" in prop_data["additional_data"]:
                value = prop_data.get("value", prop_data.get("additional_data", {}).get("value"))
                element.additional_data["value"] = value
                
            return element
            
        except (ValidationError, Exception) as e:
            logger.error(f"_process_static_property: Failed to process static property '{prop_name}' in class '{parent_name}': {e}", exc_info=True)
            return None
    
    def _process_decorators(self, element_data: Dict) -> List[CodeElement]:
        """
        Process raw decorator data into CodeElement objects.
        
        Args:
            element_data: Raw element dictionary containing decorators
            
        Returns:
            List of CodeElement objects representing decorators
        """
        decorator_elements = []
        decorators_raw = element_data.get("decorators", [])
        
        # Determine parent name for context
        parent_name = element_data.get("name")
        parent_class = element_data.get("parent_name", element_data.get("class_name"))
        full_parent_name = f"{parent_class}.{parent_name}" if parent_class else parent_name
        
        if not isinstance(decorators_raw, list):
            logger.warning(f"_process_decorators: Invalid decorators format for {full_parent_name}: Expected list, got {type(decorators_raw)}")
            return []
            
        for dec_data in decorators_raw:
            dec_element = self._process_decorator_element(dec_data, full_parent_name)
            if dec_element:
                decorator_elements.append(dec_element)
                
        return decorator_elements
    
    def _process_decorator_element(self, dec_data: Dict, parent_name: Optional[str] = None) -> Optional[CodeElement]:
        """
        Process a single raw decorator into a CodeElement.
        
        Args:
            dec_data: Raw decorator dictionary
            parent_name: Optional name of the decorated element
            
        Returns:
            CodeElement representing the decorator or None if processing fails
        """
        if not isinstance(dec_data, dict):
            logger.warning(f"_process_decorator_element: Invalid decorator data format: {dec_data}")
            return None
            
        name = dec_data.get("name")
        content = dec_data.get("content")
        
        if not name or not content:
            logger.warning(f"_process_decorator_element: Decorator missing name or content: {dec_data}")
            return None
            
        # Use provided parent name or try to extract from data
        actual_parent_name = parent_name
        if not actual_parent_name:
            data_parent = dec_data.get("parent_name")
            if data_parent:
                actual_parent_name = data_parent
        
        # Extract range data
        range_data = dec_data.get("range")
        decorator_range = None
        
        if isinstance(range_data, dict):
            try:
                # Extract line/column information robustly
                start_line = range_data.get("start_line", range_data.get("start", {}).get("line"))
                start_col = range_data.get("start_column", range_data.get("start", {}).get("column", 0))
                end_line = range_data.get("end_line", range_data.get("end", {}).get("line"))
                end_col = range_data.get("end_column", range_data.get("end", {}).get("column", 0))
                
                if (isinstance(start_line, int) and isinstance(end_line, int) and 
                    start_line > 0 and end_line >= start_line):
                    decorator_range = CodeRange(
                        start_line=start_line,
                        start_column=start_col if isinstance(start_col, int) else 0,
                        end_line=end_line,
                        end_column=end_col if isinstance(end_col, int) else 0,
                    )
                else:
                    logger.warning(f"_process_decorator_element: Invalid line numbers for decorator '{name}' range: start={start_line}, end={end_line}")
            except (ValidationError, KeyError, Exception) as e:
                logger.warning(f"_process_decorator_element: Error creating CodeRange for decorator '{name}': {e}")
        
        try:
            # Create CodeElement for the decorator
            decorator_element = CodeElement(
                type=CodeElementType.DECORATOR,
                name=name,
                content=content,
                range=decorator_range,
                parent_name=actual_parent_name,
            )
            return decorator_element
        except (ValidationError, Exception) as e:
            logger.error(f"_process_decorator_element: Failed to create decorator CodeElement for '{name}': {e}", exc_info=True)
            return None
    
    def _build_decorator_lookup(self, decorators: Optional[List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Build a lookup dictionary for decorators based on the parent name.
        
        Args:
            decorators: List of raw decorator dictionaries
            
        Returns:
            Dictionary mapping parent names to lists of decorators
        """
        result = {}
        if not decorators:
            return result
            
        for dec in decorators:
            if not isinstance(dec, dict):
                continue
                
            parent = dec.get("parent_name")
            if not parent:
                continue
                
            if parent not in result:
                result[parent] = []
                
            result[parent].append(dec)
            
        return result
