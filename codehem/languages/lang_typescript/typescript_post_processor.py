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
    V2: Simplified _process_member_element assuming dedicated extractors provide correct types.
    """

    def process_imports(self, raw_imports: List[Dict]) -> List[CodeElement]:
        """Processes raw import data into CodeElement objects."""
        processed_imports = []
        if not raw_imports:
            logger.debug("ProcessImports (TS): No raw imports received.")
            return []
        # Check if already combined by the extractor
        if (
            len(raw_imports) == 1
            and raw_imports[0].get("name") == "imports"
            and ("individual_imports" in raw_imports[0].get("additional_data", {}))
        ):
            logger.debug("ProcessImports (TS): Received already combined import block.")
            try:
                # Ensure the type is correct before creating the element
                raw_imports[0]["type"] = CodeElementType.IMPORT.value
                combined_element = CodeElement.from_dict(raw_imports[0])
                return [combined_element]
            except (ValidationError, Exception) as e:
                logger.error(
                    f"ProcessImports (TS): Failed to process pre-combined import block: {e}",
                    exc_info=True,
                )
                return []
        # If not combined, assume individual imports and combine them
        valid_imports = [
            imp
            for imp in raw_imports
            if isinstance(imp, dict)
            and "range" in imp
            and (imp.get("type") == CodeElementType.IMPORT.value)
        ]
        if not valid_imports:
            logger.debug(
                "ProcessImports (TS): No valid individual imports found to combine."
            )
            return []
        logger.debug(
            f"ProcessImports (TS): Processing {len(valid_imports)} individual import dicts to combine."
        )
        try:
            valid_imports.sort(
                key=lambda x: x.get("range", {})
                .get("start", {})
                .get("line", float("inf"))
            )
        except Exception as e:
            logger.error(
                f"ProcessImports (TS): Error sorting valid_imports: {e}. Proceeding unsorted.",
                exc_info=True,
            )
            # If sorting failed, reset to original valid list to avoid potential errors with partial sort
            valid_imports = [
                imp
                for imp in raw_imports
                if isinstance(imp, dict)
                and "range" in imp
                and (imp.get("type") == CodeElementType.IMPORT.value)
            ]
            if not valid_imports:
                return []  # Ensure we still have valid imports
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
            and (start_line > 0)
            and (end_line >= start_line)
        ):
            try:
                start_col_int = start_col if isinstance(start_col, int) else 0
                end_col_int = end_col if isinstance(end_col, int) else 0
                # Ensure lines are at least 1
                start_line = max(1, start_line)
                end_line = max(start_line, end_line)
                combined_range = CodeRange(
                    start_line=start_line,
                    start_column=start_col_int,
                    end_line=end_line,
                    end_column=end_col_int,
                )
            except (ValidationError, Exception) as e:
                logger.error(
                    f"ProcessImports (TS): Failed to create combined CodeRange: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"ProcessImports (TS): Invalid lines for combined range: start={start_line}, end={end_line}."
            )
        combined_content = "\n".join([imp.get("content", "") for imp in valid_imports])
        try:
            # Create the combined element, store individual ones in additional_data
            combined_element = CodeElement(
                type=CodeElementType.IMPORT,
                name="imports",
                content=combined_content,
                range=combined_range,
                additional_data={"individual_imports": valid_imports},
            )
            logger.debug(
                "ProcessImports (TS): Successfully created combined 'imports' CodeElement from individual parts."
            )
            return [combined_element]
        except (ValidationError, Exception) as e:
            logger.error(
                f"ProcessImports (TS): Failed to create combined 'imports' CodeElement: {e}",
                exc_info=True,
            )
            # Attempt to return individual elements as a fallback if combination fails
            individual_elements = []
            for imp_data in valid_imports:
                try:
                    imp_data["type"] = CodeElementType.IMPORT.value  # Ensure type
                    individual_elements.append(CodeElement.from_dict(imp_data))
                except Exception as ind_err:
                    logger.error(
                        f"Failed to create individual import element: {ind_err}"
                    )
            return individual_elements

    def process_functions(
        self, raw_functions: List[Dict], all_decorators: List[Dict] = None
    ) -> List[CodeElement]:
        """Processes raw function data into CodeElement objects. Accepts all_decorators list."""
        processed_functions = []
        logger.debug(
            f"TS process_functions received {len(all_decorators or [])} total decorators to consider."
        )
        for func_data in raw_functions or []:  # Handle potential None
            if not isinstance(func_data, dict):
                logger.warning(
                    f"Skipping non-dict item in raw_functions (TS): {type(func_data)}"
                )
                continue
            func_name = func_data.get("name", "unknown_func")
            logger.debug(f"Processing function (TS Detailed): {func_name}")
            func_data["type"] = CodeElementType.FUNCTION.value
            try:
                func_element = CodeElement.from_dict(func_data)
                func_element.parent_name = None
                # TODO: Enhance _process_decorators to use all_decorators list based on func_element range
                func_element.children.extend(
                    self._process_decorators(func_data, func_name)
                )  # Current limited approach
                func_element.children.extend(
                    self._process_parameters(
                        func_element, func_data.get("parameters", [])
                    )
                )
                return_element = self._process_return_value(
                    func_element, func_data.get("return_info", {})
                )
                if return_element:
                    func_element.children.append(return_element)
                func_element.children.sort(
                    key=lambda c: c.range.start_line if c.range else float("inf")
                )
                processed_functions.append(func_element)
            except (ValidationError, Exception) as e:
                logger.error(
                    f"Failed to process function (TS Detailed) '{func_name}': {e}. Data: {func_data}",
                    exc_info=True,
                )
        return processed_functions

    def process_classes(
        self,
        raw_classes: List[Dict],
        members: List[Dict],
        static_props: List[Dict],
        properties: List[Dict] = None,
        all_decorators: List[Dict] = None,
    ) -> List[CodeElement]:
        """Processes raw class/interface data, associating members, static properties, and regular properties. Accepts all_decorators list."""
        processed_containers = []
        member_lookup = self._build_lookup(members, "class_name")
        static_prop_lookup = self._build_lookup(static_props, "class_name")
        prop_lookup = self._build_lookup(properties, "class_name")
        logger.debug(
            f"TS process_classes received {len(all_decorators or [])} total decorators to consider."
        )
        for container_data in raw_classes or []:
            if not isinstance(container_data, dict):
                logger.warning(
                    f"Skipping non-dict item in raw_classes (TS): {type(container_data)}"
                )
                continue
            container_name = container_data.get("name")
            container_type_str = container_data.get("type", CodeElementType.CLASS.value)
            logger.debug(
                f"Processing container (TS): {container_name} (type: {container_type_str})"
            )
            if not container_name:
                logger.error(
                    f"Found container definition without a name (TS)! Data: {container_data}"
                )
                continue
            try:
                container_type = CodeElementType(container_type_str)
                container_data["type"] = container_type.value
            except ValueError:
                logger.error(
                    f"Invalid container type '{container_type_str}' for {container_name}. Defaulting to CLASS."
                )
                container_type = CodeElementType.CLASS
                container_data["type"] = container_type.value
            try:
                container_element = CodeElement.from_dict(container_data)
                container_element.parent_name = None
                processed_children = {}
                # Process decorators directly associated with the class/interface
                # TODO: Enhance _process_decorators to use all_decorators list based on container_element range
                container_element.children.extend(
                    self._process_decorators(container_data, container_name)
                )
                # Process members (methods, getters, setters)
                members_for_this = member_lookup.get(container_name, [])
                members_for_this.sort(
                    key=lambda m: m.get(
                        "definition_start_line",
                        m.get("range", {}).get("start", {}).get("line", 0),
                    )
                )
                for member_data in members_for_this:
                    if not isinstance(member_data, dict):
                        continue
                    # TODO: Pass all_decorators to _process_member_element
                    processed_member = self._process_member_element(
                        member_data, container_element
                    )
                    if processed_member:
                        processed_children[
                            (processed_member.type.value, processed_member.name)
                        ] = processed_member
                # Process regular properties (fields)
                props_for_this = prop_lookup.get(container_name, [])
                props_for_this.sort(
                    key=lambda p: p.get("range", {}).get("start", {}).get("line", 0)
                )
                for prop_data in props_for_this:
                    if not isinstance(prop_data, dict):
                        continue
                    prop_name = prop_data.get("name")
                    member_exists = any(
                        key[1] == prop_name for key in processed_children.keys()
                    )
                    if prop_name and not member_exists:
                        # TODO: Pass all_decorators to _process_property
                        processed_prop = self._process_property(
                            prop_data, container_element
                        )
                        if processed_prop:
                            processed_children[
                                (processed_prop.type.value, processed_prop.name)
                            ] = processed_prop
                    elif prop_name and member_exists:
                        logger.debug(
                            f"Skipping regular property '{prop_name}' as a member with the same name already exists."
                        )
                # Process static properties
                static_props_for_this = static_prop_lookup.get(container_name, [])
                static_props_for_this.sort(
                    key=lambda p: p.get("range", {}).get("start", {}).get("line", 0)
                )
                for prop_data in static_props_for_this:
                    if not isinstance(prop_data, dict):
                        continue
                    prop_name = prop_data.get("name")
                    if prop_name and not any(
                        key[1] == prop_name for key in processed_children.keys()
                    ):
                        # TODO: Pass all_decorators to _process_static_property
                        processed_prop = self._process_static_property(
                            prop_data, container_element
                        )
                        if processed_prop:
                            processed_children[
                                (processed_prop.type.value, processed_prop.name)
                            ] = processed_prop
                    elif prop_name:
                        logger.debug(
                            f"Skipping static property '{prop_name}' as an element with the same name already exists."
                        )
                # Add all processed children and sort
                container_element.children.extend(list(processed_children.values()))
                container_element.children.sort(
                    key=lambda child: child.range.start_line
                    if child.range
                    else float("inf")
                )
                processed_containers.append(container_element)
            except (ValidationError, Exception) as e:
                logger.error(
                    f"Failed to process container (TS) '{container_name}': {e}. Data: {container_data}",
                    exc_info=True,
                )
        return processed_containers

    def _process_property(
        self, prop_data: Dict, parent_container_element: "CodeElement"
    ) -> Optional["CodeElement"]:
        """Processes raw regular property (field) data into a CodeElement."""
        prop_name = prop_data.get("name", "unknown_property")
        parent_name = parent_container_element.name
        logger.debug(f"Processing property (TS): {prop_name} in {parent_name}")
        if not isinstance(prop_data, dict):
            logger.warning(
                f"Skipping non-dict item in prop data for {parent_name} (TS): {type(prop_data)}"
            )
            return None
        prop_data["type"] = CodeElementType.PROPERTY.value  # Set the correct type
        try:
            element = CodeElement.from_dict(prop_data)
            element.parent_name = parent_name
            # Value type and value might already be set by from_dict if keys match
            if element.value_type is None:
                element.value_type = prop_data.get(
                    "value_type"
                )  # Ensure value_type is set
            if "value" not in element.additional_data and "value" in prop_data:
                element.additional_data["value"] = prop_data.get("value")
            # Process decorators associated with this property
            # This needs the 'all_decorators' list passed down eventually
            # element.children.extend(self._process_decorators(prop_data, prop_name, all_decorators)) # Placeholder for future decorator handling
            element.children.extend(
                self._process_decorators(prop_data, prop_name)
            )  # Current limited decorator processing
            element.children.sort(
                key=lambda c: c.range.start_line if c.range else float("inf")
            )
            return element
        except (ValidationError, Exception) as e:
            logger.error(
                f"Failed to process property '{prop_name}' in container '{parent_name}' (TS): {e}. Data: {prop_data}",
                exc_info=False,
            )
            return None

    def _build_lookup(self, items: List[Dict], key_field: str) -> Dict[str, List[Dict]]:
        """Helper to group items by a specific key field."""
        lookup = {}
        for item in items:
            # Ensure item is a dict and has the key_field before accessing
            if isinstance(item, dict) and key_field in item:
                key_value = item[key_field]
                # Ensure key_value is hashable (e.g., string)
                if key_value is not None and isinstance(
                    key_value, (str, int, float, bool)
                ):
                    if key_value not in lookup:
                        lookup[key_value] = []
                    lookup[key_value].append(item)
                else:
                    logger.warning(
                        f"Skipping item in _build_lookup due to unhashable or None key '{key_value}' in field '{key_field}'. Item: {item}"
                    )
            elif isinstance(item, dict):
                logger.warning(
                    f"Item is missing key_field '{key_field}' in _build_lookup. Item: {item}"
                )
            # else: # Optionally log if item is not a dict
            # logger.warning(f"Skipping non-dict item in _build_lookup: {type(item)}")
        return lookup

    def _process_parameters(
        self, element: "CodeElement", params_data: List[Dict]
    ) -> List["CodeElement"]:
        """Processes raw parameter data into CodeElement objects. (TS Enhanced)"""
        param_elements = []
        parent_path = (
            f"{element.parent_name}.{element.name}"
            if element.parent_name
            else element.name
        )
        for i, param in enumerate(params_data):
            if not isinstance(param, dict):
                logger.warning(
                    f"Skipping non-dict item in params_data for {parent_path} (TS): {type(param)}"
                )
                continue
            name = param.get("name")
            if name:
                try:
                    # Construct content string based on available info (more representative)
                    param_content_parts = [name]
                    value_type = param.get("type")
                    is_optional_marker = param.get("optional", False) and not param.get(
                        "default"
                    )  # Check if optional via '?'
                    if is_optional_marker:
                        param_content_parts[0] += (
                            "?"  # Add '?' to name if optional without default
                        )
                    if value_type:
                        param_content_parts.append(f": {value_type}")
                    default_value = param.get("default")
                    if default_value:
                        param_content_parts.append(f" = {default_value}")
                    param_content = "".join(param_content_parts)
                    # Keep original 'optional' flag from extractor if present
                    additional_data = {
                        "optional": param.get("optional", False),
                        "default": default_value,
                    }
                    # Parameter range is tricky without the node, maybe skip or estimate if needed
                    param_element = CodeElement(
                        type=CodeElementType.PARAMETER,
                        name=name,  # Keep original name without '?'
                        content=param_content,  # Use reconstructed content
                        parent_name=parent_path,
                        value_type=value_type,
                        additional_data=additional_data,
                        range=None,  # Range typically not available/needed at this level post-extraction
                    )
                    param_elements.append(param_element)
                except (ValidationError, Exception) as e:
                    logger.error(
                        f"Failed to create parameter CodeElement for '{name}' in {parent_path} (TS): {e}",
                        exc_info=False,
                    )
            else:
                logger.warning(
                    f"Skipping parameter data without name in {parent_path} (TS): {param}"
                )
        return param_elements

    def _process_return_value(
        self, element: "CodeElement", return_info: Dict
    ) -> Optional["CodeElement"]:
        """Processes raw return info into a CodeElement. (TS Enhanced)"""
        if not isinstance(return_info, dict):
            logger.warning(
                f"Invalid return_info format for {element.name} (TS): {type(return_info)}"
            )
            return None
        return_type = return_info.get("return_type")
        # TS extractors should provide the type string directly if available
        if not return_type:
            return None  # No return type specified
        parent_path = (
            f"{element.parent_name}.{element.name}"
            if element.parent_name
            else element.name
        )
        try:
            # Clean up potential leading ':' from type string if extractor included it
            cleaned_return_type = (
                return_type.lstrip(":").strip()
                if isinstance(return_type, str)
                else return_type
            )
            return_content = f": {cleaned_return_type}"  # Represent as ': Type'
            # Range is not applicable here post-extraction
            return_element = CodeElement(
                type=CodeElementType.RETURN_VALUE,
                name=f"{element.name}_return",
                content=return_content,
                parent_name=parent_path,
                value_type=cleaned_return_type,  # Store the actual type string
                range=None,
                # Store original raw values if provided by extractor
                additional_data={"values": return_info.get("return_values", [])},
            )
            return return_element
        except (ValidationError, Exception) as e:
            logger.error(
                f"Failed to create return value CodeElement for {element.name} (TS): {e}",
                exc_info=False,
            )
            return None

    def _process_decorators(
        self, element_data: Dict, element_name_for_parent: str
    ) -> List["CodeElement"]:
        """Processes raw decorator data into CodeElement objects."""
        decorator_elements = []
        decorators_raw = element_data.get("decorators", [])
        parent_class = element_data.get("class_name")  # Get potential class context
        # Construct full parent name for context (e.g., 'MyClass.myMethod' or just 'myFunction')
        full_parent_name = (
            f"{parent_class}.{element_name_for_parent}"
            if parent_class
            else element_name_for_parent
        )
        if not isinstance(decorators_raw, list):
            logger.warning(
                f"Invalid decorators format for {full_parent_name} (TS): Expected list, got {type(decorators_raw)}"
            )
            return []
        for dec_data in decorators_raw:
            if not isinstance(dec_data, dict):
                logger.warning(
                    f"Skipping invalid decorator data format for {full_parent_name} (TS): {dec_data}"
                )
                continue
            name = dec_data.get("name")
            content = dec_data.get("content")
            range_data = dec_data.get("range")
            if name and content:
                decorator_range = None
                if isinstance(range_data, dict):
                    try:
                        # Try parsing range data robustly
                        start = range_data.get("start", {})
                        end = range_data.get("end", {})
                        start_line = start.get("line", start.get("start_line"))
                        start_col = start.get("column", start.get("start_column", 0))
                        end_line = end.get("line", end.get("end_line"))
                        end_col = end.get("column", end.get("end_column", 0))
                        if (
                            isinstance(start_line, int)
                            and isinstance(end_line, int)
                            and (start_line > 0)
                            and (end_line >= start_line)
                        ):
                            start_col_int = (
                                start_col if isinstance(start_col, int) else 0
                            )
                            end_col_int = end_col if isinstance(end_col, int) else 0
                            # Ensure lines are valid
                            start_line = max(1, start_line)
                            end_line = max(start_line, end_line)
                            decorator_range = CodeRange(
                                start_line=start_line,
                                start_column=start_col_int,
                                end_line=end_line,
                                end_column=end_col_int,
                            )
                        else:
                            logger.warning(
                                f"Invalid line numbers for decorator '{name}' range (TS): start={start_line}, end={end_line}"
                            )
                    except (ValidationError, KeyError, Exception) as e:
                        logger.warning(
                            f"Error creating CodeRange for decorator '{name}' (TS): {e}. Range data: {range_data}",
                            exc_info=False,
                        )
                elif range_data is not None:
                    logger.warning(
                        f"Invalid range format for decorator '{name}' (TS): {type(range_data)}"
                    )
                try:
                    decorator_element = CodeElement(
                        type=CodeElementType.DECORATOR,
                        name=name,
                        content=content,
                        range=decorator_range,
                        parent_name=full_parent_name,  # Associate with the element it decorates
                    )
                    decorator_elements.append(decorator_element)
                except (ValidationError, Exception) as e:
                    logger.error(
                        f"Failed to create decorator CodeElement for '{name}' in {full_parent_name} (TS): {e}",
                        exc_info=True,
                    )
            else:
                logger.warning(
                    f"Skipping decorator for {full_parent_name} (TS) without name or content: {dec_data}"
                )
        return decorator_elements

    def _process_member_element(
        self, member_data: Dict, parent_container_element: "CodeElement"
    ) -> Optional["CodeElement"]:
        """
        Processes raw member data (method, property, getter, setter) into a CodeElement.
        V2: Assumes the correct type is provided by a dedicated extractor. Focuses on structure.
        """
        element_name = member_data.get("name", "unknown_member")
        parent_name = parent_container_element.name
        member_type_str = member_data.get(
            "type"
        )  # Get type directly from extractor result
        if not member_type_str:
            logger.error(
                f"Member data for '{element_name}' in container '{parent_name}' (TS) is missing 'type'. Data: {member_data}"
            )
            return None
        logger.debug(
            f"PostProcessing member (TS V2): {element_name} (type: {member_type_str}) in {parent_name}"
        )
        try:
            element_type_enum = CodeElementType(member_type_str)
        except ValueError:
            logger.error(
                f"Invalid element type '{member_type_str}' provided by extractor for member '{element_name}' (TS). Skipping."
            )
            return None
        try:
            # Create the CodeElement using the type provided by the extractor
            # Ensure range data is correctly passed to from_dict
            element = CodeElement.from_dict(
                member_data
            )  # from_dict handles range creation
            element.parent_name = parent_name  # Set parent relationship
            # Process children (decorators, parameters, return value) based on type
            element.children.extend(self._process_decorators(member_data, element_name))
            if element_type_enum in [
                CodeElementType.METHOD,
                CodeElementType.PROPERTY_GETTER,
                CodeElementType.PROPERTY_SETTER,
            ]:
                element.children.extend(
                    self._process_parameters(element, member_data.get("parameters", []))
                )
                return_element = self._process_return_value(
                    element, member_data.get("return_info", {})
                )
                if return_element:
                    element.children.append(return_element)
            # Properties and Static Properties might have value/type info processed if needed,
            # but core structure is handled by from_dict and decorators. Add value from additional_data if present.
            elif element_type_enum in [
                CodeElementType.PROPERTY,
                CodeElementType.STATIC_PROPERTY,
            ]:
                element.value_type = member_data.get(
                    "value_type"
                )  # Ensure value_type is set
                if "value" in member_data.get("additional_data", {}):
                    # Value is already handled by from_dict if it exists in additional_data
                    pass
                elif "value" in member_data:  # Handle if value was at top level
                    element.additional_data["value"] = member_data.get("value")
            # Sort children for consistency
            element.children.sort(
                key=lambda c: c.range.start_line if c.range else float("inf")
            )
            return element
        except (ValidationError, Exception) as e:
            logger.error(
                f"Failed to process member element '{element_name}' in container '{parent_name}' (TS V2): {e}. Data: {member_data}",
                exc_info=False,
            )
            return None

    def _process_static_property(
        self, prop_data: Dict, parent_container_element: "CodeElement"
    ) -> Optional["CodeElement"]:
        """Processes raw static property data into a CodeElement."""
        prop_name = prop_data.get("name", "unknown_static")
        parent_name = parent_container_element.name
        logger.debug(f"Processing static property (TS): {prop_name} in {parent_name}")
        if not isinstance(prop_data, dict):
            logger.warning(
                f"Skipping non-dict item in static prop data for {parent_name} (TS): {type(prop_data)}"
            )
            return None
        prop_data["type"] = CodeElementType.STATIC_PROPERTY.value  # Ensure type
        try:
            element = CodeElement.from_dict(prop_data)
            element.parent_name = parent_name
            # Ensure value_type and value are correctly assigned if present
            element.value_type = prop_data.get("value_type")
            if "value" in prop_data.get("additional_data", {}):
                pass  # Already handled by from_dict
            elif "value" in prop_data:
                element.additional_data["value"] = prop_data.get("value")
            element.children.extend(self._process_decorators(prop_data, prop_name))
            element.children.sort(key=lambda c: c.range.start_line if c.range else float('inf'))
            return element
        except (ValidationError, Exception) as e:
            logger.error(f"Failed to process static property '{prop_name}' in container '{parent_name}' (TS): {e}. Data: {prop_data}", exc_info=False)
            return None