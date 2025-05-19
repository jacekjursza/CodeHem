# MOVED FILE: Python-specific post-processor
import logging
from typing import List, Dict, Optional
from codehem.models.code_element import CodeElement, CodeRange  # Added CodeRange
from codehem.models.enums import CodeElementType  # Added CodeElementType
from pydantic import ValidationError  # Added ValidationError

# Updated import path for the base class
from ..post_processor_base import BaseExtractionPostProcessor

logger = logging.getLogger(__name__)


class PythonExtractionPostProcessor(BaseExtractionPostProcessor):
    """
    Python-specific implementation of extraction post-processing.
    Transforms raw extraction dicts into structured CodeElement objects.
    """

    def process_imports(self, raw_imports: List[Dict]) -> List[CodeElement]:
        """Processes raw import data into a single combined CodeElement"""
        if not raw_imports:
            logger.debug(
                "ProcessImports: No raw imports received, returning empty list."
            )
            return []
        valid_imports = [
            imp for imp in raw_imports if isinstance(imp, dict) and "range" in imp
        ]
        if not valid_imports:
            logger.error("ProcessImports: No valid raw imports with range data found.")
            return []
        # Sort by start line
        try:
            valid_imports.sort(
                key=lambda x: x.get("range", {})
                .get("start", {})
                .get("line", float("inf"))
            )
            logger.debug(
                f"ProcessImports: Sorted {len(valid_imports)} valid imports by line."
            )
        except Exception as e:
            logger.error(
                f"ProcessImports: Error sorting valid_imports: {e}. Proceeding without sorting.",
                exc_info=True,
            )
            # Fallback to original list if sorting fails critically
            valid_imports = [
                imp for imp in raw_imports if isinstance(imp, dict) and "range" in imp
            ]
            if not valid_imports:
                return []
        # Determine combined range
        first_import = valid_imports[0]
        last_import = valid_imports[-1]
        first_range = first_import.get("range", {})
        last_range = last_import.get("range", {})
        start_data = first_range.get("start", {})
        end_data = last_range.get("end", {})
        start_line = start_data.get("line")
        start_col = start_data.get("column", 0)
        end_line = end_data.get("line")
        end_col = end_data.get("column", 0)
        combined_range = None
        if (
            isinstance(start_line, int)
            and isinstance(end_line, int)
            and start_line > 0
            and end_line >= start_line
        ):
            try:
                combined_range = CodeRange(
                    start_line=start_line,
                    start_column=start_col,
                    end_line=end_line,
                    end_column=end_col,
                )
                logger.debug(
                    f"ProcessImports: Created combined CodeRange: {combined_range}"
                )
            except (ValidationError, Exception) as e:
                logger.error(
                    f"ProcessImports: Failed to create combined CodeRange: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"ProcessImports: Invalid calculated lines for combined range: start={start_line}, end={end_line}. Range will be None."
            )
        # Combine content (ensure content exists and is string)
        combined_content_parts = [
            imp.get("content", "")
            for imp in valid_imports
            if isinstance(imp.get("content"), str)
        ]
        combined_content = "\n".join(combined_content_parts)
        logger.debug(
            f"ProcessImports: Combining {len(valid_imports)} imports from estimated line {start_line} to {end_line}."
        )
        try:
            # Create the combined CodeElement
            combined_element = CodeElement(
                type=CodeElementType.IMPORT,
                name="imports",  # Standardized name for the combined block
                content=combined_content,
                range=combined_range,
                additional_data={
                    "individual_imports": valid_imports
                },  # Keep raw data if needed
            )
            logger.debug(
                "ProcessImports: Successfully created combined 'imports' CodeElement."
            )
            return [combined_element]
        except (ValidationError, Exception) as e:
            logger.error(
                f"ProcessImports: Failed to create combined 'imports' CodeElement: {e}",
                exc_info=True,
            )
            return []  # Return empty list on failure

    def process_functions(self, raw_functions: List[Dict], all_decorators: List[Dict] = None) -> List[CodeElement]:
        """ Processes raw standalone function data. Accepts all_decorators but doesn't use it yet. """
        processed_functions = []
        logger.debug(f"Python process_functions received {len(all_decorators or [])} decorators (currently unused).")
        for function_data in raw_functions:
            if not isinstance(function_data, dict):
                    logger.warning(f'Skipping non-dict item in raw_functions: {type(function_data)}')
                    continue
            func_name = function_data.get('name', 'unknown_func')
            logger.debug(f'Processing function: {func_name}')
            function_data['type'] = CodeElementType.FUNCTION.value
            try:
                    func_element = CodeElement.from_dict(function_data)
                    func_element.parent_name = None
                    # Process decorators associated directly by the extractor (if any)
                    func_element.children.extend(self._process_decorators(function_data))
                    func_element.children.extend(self._process_parameters(func_element, function_data.get('parameters', [])))
                    return_element = self._process_return_value(func_element, function_data.get('return_info', {}))
                    if return_element:
                        func_element.children.append(return_element)
                    # TODO: Add logic here to use 'all_decorators' to find and add decorators if needed
                    processed_functions.append(func_element)
            except (ValidationError, Exception) as e:
                logger.error(f"Failed to process function '{func_name}': {e}. Data: {function_data}", exc_info=True)
        return processed_functions

    def process_classes(self, raw_classes: List[Dict], members: List[Dict], static_props: List[Dict], properties: List[Dict] = None, all_decorators: List[Dict] = None) -> List[CodeElement]:
        """
        Processes raw Python class data, associating members and static properties.
        Accepts 'properties' and 'all_decorators' arguments for signature compatibility but does not currently use them extensively.
        """
        processed_classes = []
        member_lookup = {}
        # Simplified: Build lookups only if data is not None
        if members:
            for m in members:
                if isinstance(m, dict) and 'class_name' in m:
                    class_name = m['class_name']
                    if class_name not in member_lookup: member_lookup[class_name] = []
                    member_lookup[class_name].append(m)
        if static_props:
            static_prop_lookup = {}
            for p in static_props:
                if isinstance(p, dict) and 'class_name' in p:
                    class_name = p['class_name']
                    if class_name not in static_prop_lookup: static_prop_lookup[class_name] = []
                    static_prop_lookup[class_name].append(p)
        else:
            static_prop_lookup = {} # Ensure it exists even if static_props is None

        # Log received arguments for debugging
        logger.debug(f"Python process_classes received {len(properties or [])} regular properties (unused).")
        logger.debug(f"Python process_classes received {len(all_decorators or [])} decorators (unused).")

        for class_data in raw_classes or []: # Handle potential None for raw_classes
            if not isinstance(class_data, dict):
                    logger.warning(f'Skipping non-dict item in raw_classes: {type(class_data)}')
                    continue
            class_name = class_data.get('name')
            logger.debug(f'Processing class: {class_name}')
            if not class_name:
                logger.error(f'Found class definition without a name! Data: {class_data}')
                continue
            class_data['type'] = CodeElementType.CLASS.value
            try:
                class_element = CodeElement.from_dict(class_data)
                class_element.parent_name = None
                    # Process decorators directly associated with the class - current limited approach
                class_element.children.extend(self._process_decorators(class_data))

                processed_members = {}
                members_for_this_class = member_lookup.get(class_name, [])
                members_for_this_class.sort(key=lambda m: m.get('definition_start_line', m.get('range', {}).get('start', {}).get('line', 0)))
                for member_data in members_for_this_class:
                    if not isinstance(member_data, dict): continue
                    processed_member = self._process_method_element(member_data, class_element)
                    if processed_member:
                        processed_members[(processed_member.type.value, processed_member.name)] = processed_member

                processed_static_props = {}
                static_props_for_this_class = static_prop_lookup.get(class_name, [])
                static_props_for_this_class.sort(key=lambda p: p.get('range', {}).get('start', {}).get('line', 0))
                for prop_data in static_props_for_this_class:
                        if not isinstance(prop_data, dict): continue
                        prop_name = prop_data.get('name')
                        if prop_name and not any(key[1] == prop_name for key in processed_members.keys()):
                            processed_prop = self._process_static_property(prop_data, class_element)
                            if processed_prop:
                                processed_static_props[processed_prop.name] = processed_prop
                        elif prop_name:
                            logger.debug(f"Skipping static property '{prop_name}' as a member with the same name already exists.")

                class_element.children.extend(list(processed_members.values()))
                class_element.children.extend(list(processed_static_props.values()))
                class_element.children.sort(key=lambda child: child.range.start_line if child.range else float('inf'))
                processed_classes.append(class_element)
            except (ValidationError, Exception) as e:
                    logger.error(f"Failed to process class '{class_name}': {e}. Data: {class_data}", exc_info=True)
        return processed_classes

    def _process_parameters(
        self, element: "CodeElement", params_data: List[Dict]
    ) -> List["CodeElement"]:
        param_elements = []
        parent_path = (
            f"{element.parent_name}.{element.name}"
            if element.parent_name
            else element.name
        )
        for param in params_data:
            if not isinstance(param, dict):
                logger.warning(
                    f"Skipping non-dict item in params_data for {parent_path}: {type(param)}"
                )
                continue
            name = param.get("name")
            if name:
                try:
                    param_element = CodeElement(
                        type=CodeElementType.PARAMETER,
                        name=name,
                        content=name,  # Content might need refinement if we store full param string later
                        parent_name=parent_path,
                        value_type=param.get("type"),
                        additional_data={
                            "optional": param.get("optional", False),
                            "default": param.get("default"),
                        },
                        # Range is usually not extracted for individual parameters here
                    )
                    param_elements.append(param_element)
                except (ValidationError, Exception) as e:
                    logger.error(
                        f"Failed to create parameter CodeElement for '{name}' in {parent_path}: {e}",
                        exc_info=True,
                    )
            else:
                logger.warning(
                    f"Skipping parameter data without a name for {parent_path}: {param}"
                )
        return param_elements

    def _process_return_value(
        self, element: "CodeElement", return_info: Dict
    ) -> Optional["CodeElement"]:
        if not isinstance(return_info, dict):
            logger.warning(
                f"Invalid return_info format for {element.name}: {type(return_info)}"
            )
            return None
        return_type = return_info.get("return_type")
        return_values = return_info.get("return_values", [])
        # Only create a return element if there's a type hint or explicit return values found
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
                    "values": return_values
                },  # Store observed return values
                # Range usually not applicable here
            )
            return return_element
        except (ValidationError, Exception) as e:
            logger.error(
                f"Failed to create return value CodeElement for {element.name}: {e}",
                exc_info=True,
            )
            return None

    def _process_method_element(
        self, method_data: Dict, parent_class_element: "CodeElement"
    ) -> Optional["CodeElement"]:
        """
        Process raw method/property data into a CodeElement with children,
        including classification based on Python decorators (@property, @name.setter).
        """
        element_name = method_data.get("name", "unknown_member")
        parent_name = parent_class_element.name
        initial_type_str = method_data.get("type", CodeElementType.METHOD.value)
        logger.debug(
            f"PostProcessing member: {element_name} (initial type: {initial_type_str}) in class {parent_name}"
        )
        try:
            # Use METHOD as default if type is missing or invalid
            element_type_enum = (
                CodeElementType(initial_type_str)
                if initial_type_str in CodeElementType._value2member_map_
                else CodeElementType.METHOD
            )
            method_data["type"] = (
                element_type_enum.value
            )  # Ensure data has valid type string
            element = CodeElement.from_dict(method_data)
            element.parent_name = parent_name
            # Classify based on decorators
            raw_decorators = method_data.get("decorators", [])
            is_getter = False
            is_setter = False
            for dec_info in raw_decorators:
                if isinstance(dec_info, dict):
                    dec_name = dec_info.get("name")
                    if dec_name == "property":
                        is_getter = True
                        logger.debug(
                            f"  Decorator '@property' found for {element_name}."
                        )
                    elif (
                        isinstance(dec_name, str)
                        and dec_name == f"{element_name}.setter"
                    ):
                        is_setter = True
                        logger.debug(
                            f"  Decorator '@{element_name}.setter' found for {element_name}."
                        )
                        break  # Setter is definitive
            if is_setter:
                element.type = CodeElementType.PROPERTY_SETTER
                logger.debug(f"  Classifying {element_name} as PROPERTY_SETTER.")
                # Optionally add the base property name if needed later
                # element.additional_data['property_name'] = element_name
            elif is_getter:
                element.type = CodeElementType.PROPERTY_GETTER
                logger.debug(f"  Classifying {element_name} as PROPERTY_GETTER.")
            # else: it remains METHOD (or whatever was initially set if valid)
            # Process children
            element.children.extend(self._process_decorators(method_data))
            element.children.extend(
                self._process_parameters(element, method_data.get("parameters", []))
            )
            return_element = self._process_return_value(
                element, method_data.get("return_info", {})
            )
            if return_element:
                element.children.append(return_element)
            return element
        except (ValidationError, Exception) as e:
            logger.error(
                f"Failed to process method element '{element_name}' in class '{parent_name}': {e}. Data: {method_data}",
                exc_info=True,
            )
            return None

    def _process_static_property(
        self, prop_data: Dict, parent_class_element: "CodeElement"
    ) -> Optional["CodeElement"]:
        prop_name = prop_data.get("name", "unknown_static")
        parent_name = parent_class_element.name
        logger.debug(f"Processing static property: {prop_name} in class {parent_name}")
        if not isinstance(prop_data, dict):
            logger.warning(
                f"Skipping non-dict item in static_props data for {parent_name}: {type(prop_data)}"
            )
            return None
        prop_data["type"] = CodeElementType.STATIC_PROPERTY.value  # Ensure type is set
        try:
            element = CodeElement.from_dict(prop_data)
            element.parent_name = parent_name
            element.value_type = prop_data.get("value_type")  # Keep potential type hint
            # Store the extracted value if available from extractor
            if "value" in prop_data:
                element.additional_data["value"] = prop_data.get("value")
            return element
        except (ValidationError, Exception) as e:
            logger.error(
                f"Failed to process static property '{prop_name}' in class '{parent_name}': {e}. Data: {prop_data}",
                exc_info=True,
            )
            return None

    def _process_decorators(self, element_data: Dict) -> List["CodeElement"]:
        decorator_elements = []
        decorators_raw = element_data.get("decorators", [])
        # Determine parent name for context
        parent_name = element_data.get("name")
        parent_class = element_data.get("class_name")
        full_parent_name = (
            f"{parent_class}.{parent_name}" if parent_class else parent_name
        )
        if not isinstance(decorators_raw, list):
            logger.warning(
                f"Invalid decorators format for {full_parent_name}: Expected list, got {type(decorators_raw)}"
            )
            return []
        for dec_data in decorators_raw:
            if not isinstance(dec_data, dict):
                logger.warning(
                    f"Skipping invalid decorator data format for {full_parent_name}: {dec_data}"
                )
                continue
            name = dec_data.get("name")
            content = dec_data.get("content")
            range_data = dec_data.get("range")
            if name and content:
                decorator_range = None
                if isinstance(range_data, dict):
                    try:
                        # Attempt to extract line/col robustly
                        start_line = range_data.get(
                            "start_line", range_data.get("start", {}).get("line")
                        )
                        start_col = range_data.get(
                            "start_column", range_data.get("start", {}).get("column", 0)
                        )
                        end_line = range_data.get(
                            "end_line", range_data.get("end", {}).get("line")
                        )
                        end_col = range_data.get(
                            "end_column", range_data.get("end", {}).get("column", 0)
                        )
                        if (
                            isinstance(start_line, int)
                            and isinstance(end_line, int)
                            and start_line > 0
                            and end_line >= start_line
                        ):
                            decorator_range = CodeRange(
                                start_line=start_line,
                                start_column=start_col
                                if isinstance(start_col, int)
                                else 0,
                                end_line=end_line,
                                end_column=end_col if isinstance(end_col, int) else 0,
                            )
                        else:
                            logger.warning(
                                f"Invalid line numbers for decorator '{name}' range: start={start_line}, end={end_line}"
                            )
                    except (ValidationError, KeyError, Exception) as e:
                        logger.warning(
                            f"Error creating CodeRange for decorator '{name}': {e}. Range data: {range_data}",
                            exc_info=False,
                        )
                elif range_data is not None:
                    logger.warning(
                        f"Invalid range format for decorator '{name}': {type(range_data)}"
                    )
                try:
                    decorator_element = CodeElement(
                        type=CodeElementType.DECORATOR,
                        name=name,
                        content=content,
                        range=decorator_range,
                        parent_name=full_parent_name,
                    )
                    decorator_elements.append(decorator_element)
                except (ValidationError, Exception) as e:
                    logger.error(
                        f"Failed to create decorator CodeElement for '{name}' in {full_parent_name}: {e}",
                        exc_info=True,
                    )
            else:
                logger.warning(f'Skipping decorator for {full_parent_name} without name or content: {dec_data}')
        return decorator_elements