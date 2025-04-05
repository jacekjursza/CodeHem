import logging
from typing import List, Dict

from codehem.models.code_element import CodeElement
from .base import BaseExtractionPostProcessor

logger = logging.getLogger(__name__)

class PythonExtractionPostProcessor(BaseExtractionPostProcessor):
    """
    Python-specific implementation of extraction post-processing.
    Transforms raw extraction dicts into structured CodeElement objects.
    """

    def process_imports(self, raw_imports: List[Dict]) -> List[CodeElement]:
        if not raw_imports:
            return []

        # If we received one collective 'imports' element
        if len(raw_imports) == 1 and raw_imports[0].get("name") == "imports":
            raw_element = raw_imports[0]
            range_data = raw_element.get("range")
            code_range = None
            if range_data:
                from codehem.models.code_element import CodeRange
                from codehem.models.enums import CodeElementType

                code_range = CodeRange(
                    start_line=range_data.get("start", {}).get("line", 1),
                    start_column=range_data.get("start", {}).get("column", 0),
                    end_line=range_data.get("end", {}).get("line", 1),
                    end_column=range_data.get("end", {}).get("column", 0),
                )
            element = CodeElement(
                type=CodeElementType.IMPORT,
                name="imports",
                content=raw_element.get("content", ""),
                range=code_range,
                additional_data={"imports_list": raw_element.get("imports", [])},
            )
            return [element]
        else:
            # If (unexpectedly) we got a list of individual imports
            logger.warning(
                "Received a list of individual imports instead of expected collective element."
            )
            # Could implement combining logic here, but for now return empty list
            return []

    def process_functions(self, raw_functions: List[Dict]) -> List[CodeElement]:
        from codehem.models.enums import CodeElementType
        from codehem.models.code_element import CodeElement

        processed_functions = []

        for function_data in raw_functions:
            if not isinstance(function_data, dict):
                continue

            func_name = function_data.get("name", "unknown_func")
            logger.debug(f"Processing function: {func_name}")

            # Ensure correct type
            function_data["type"] = CodeElementType.FUNCTION.value
            func_element = CodeElement.from_dict(function_data)
            func_element.parent_name = None  # Global functions have no class parent

            # Process and add children
            func_element.children.extend(
                self._process_decorators(function_data)
            )
            func_element.children.extend(
                self._process_parameters(func_element, function_data.get("parameters", []))
            )

            return_element = self._process_return_value(
                func_element, function_data.get("return_info", {})
            )
            if return_element:
                func_element.children.append(return_element)

            processed_functions.append(func_element)

        return processed_functions

    def process_classes(
        self,
        raw_classes: List[Dict],
        members: List[Dict],
        static_props: List[Dict]
    ) -> List[CodeElement]:
        from codehem.models.enums import CodeElementType
        from codehem.models.code_element import CodeElement

        processed_classes = []

        for class_data in raw_classes:
            if not isinstance(class_data, dict):
                continue

            class_name = class_data.get("name")
            logger.debug(f"Processing class: {class_name}")

            if not class_name:
                logger.error(f"Found class definition without a name! Data: {class_data}")
                class_element = CodeElement(
                    type=CodeElementType.CLASS,
                    name="_ERROR_NO_CLASS_NAME_",
                    content=class_data.get("content", ""),
                )
                processed_classes.append(class_element)
                continue

            class_data["type"] = CodeElementType.CLASS.value
            class_element = CodeElement.from_dict(class_data)

            # Add class decorators
            class_element.children.extend(self._process_decorators(class_data))

            # Filter members and static properties for this class
            members_for_class = [
                m for m in members
                if isinstance(m, dict) and m.get("class_name") == class_name
            ]
            static_props_for_class = [
                p for p in static_props
                if isinstance(p, dict) and p.get("class_name") == class_name
            ]
            # Ignore class_data.get('members') as it is empty in raw extraction
            # Ignore class_data.get('members') as it is empty in raw extraction
            # Ignore class_data.get('members') as it is empty in raw extraction

            # Process members
            processed_members = {}
            members_for_class.sort(
                key=lambda m: m.get(
                    "definition_start_line",
                    m.get("range", {}).get("start", {}).get("line", 0),
                )
            )
            for member_data in members_for_class:
                if not isinstance(member_data, dict):
                    continue
                processed_member = self._process_method_element(
                    member_data, class_element
                )
                member_key = (processed_member.type.value, processed_member.name)
                processed_members[member_key] = processed_member

            class_element.children.extend(list(processed_members.values()))

            # Process static properties
            processed_static_props = {}
            static_props_for_class.sort(
                key=lambda p: p.get("range", {}).get("start", {}).get("line", 0)
            )
            for prop_data in static_props_for_class:
                if not isinstance(prop_data, dict):
                    continue
                processed_prop = self._process_static_property(
                    prop_data, class_element
                )
                processed_static_props[processed_prop.name] = processed_prop

            class_element.children.extend(list(processed_static_props.values()))

            # Sort children by start line
            class_element.children.sort(
                key=lambda child: child.range.start_line if child.range else float("inf")
            )

            processed_classes.append(class_element)

        return processed_classes

    def _process_parameters(
        self, element: 'CodeElement', params_data: List[Dict]
    ) -> List['CodeElement']:
        from codehem.models.code_element import CodeElement
        from codehem.models.enums import CodeElementType

        param_elements = []
        parent_path = (
            f"{element.parent_name}.{element.name}"
            if element.parent_name
            else element.name
        )

        for param in params_data:
            if not isinstance(param, dict):
                continue

            name = param.get("name")
            if name:
                param_elements.append(
                    CodeElement(
                        type=CodeElementType.PARAMETER,
                        name=name,
                        content=name,
                        parent_name=parent_path,
                        value_type=param.get("type"),
                        additional_data={
                            "optional": param.get("optional", False),
                            "default": param.get("default"),
                        },
                    )
                )

        return param_elements

    def _process_return_value(
        self, element: 'CodeElement', return_info: Dict
    ) -> 'CodeElement | None':
        from codehem.models.code_element import CodeElement
        from codehem.models.enums import CodeElementType

        if not isinstance(return_info, dict):
            return None

        return_type = return_info.get("return_type")
        return_values = return_info.get("return_values", [])

        if not return_type and not return_values:
            return None

        parent_path = (
            f"{element.parent_name}.{element.name}"
            if element.parent_name
            else element.name
        )

        return CodeElement(
            type=CodeElementType.RETURN_VALUE,
            name=f"{element.name}_return",
            content=return_type or "",
            parent_name=parent_path,
            value_type=return_type,
            additional_data={
                "values": return_values
            },
        )
        return_type = return_info.get("return_type")
        return_values = return_info.get("return_values", [])

        if not return_type and not return_values:
            return None

        parent_path = (
            f"{element.parent_name}.{element.name}"
            if element.parent_name
            else element.name
        )

        return CodeElement(
            type=CodeElementType.RETURN_VALUE,
            name=f"{element.name}_return",
            content=return_type or "",
            parent_name=parent_path,
            value_type=return_type,
            additional_data={
                "values": return_values
            },
        )


        return param_elements

    def _process_method_element(
        self, method_data: Dict, parent_class_element: 'CodeElement'
    ) -> 'CodeElement':
        from codehem.models.code_element import CodeElement
        from codehem.models.enums import CodeElementType

        element_name = method_data.get("name", "unknown_member")
        parent_name = parent_class_element.name
        logger.debug(
            f"Processing class member: {element_name} (raw type: {method_data.get('type')}) in class {parent_name}"
        )

        element_type_str = method_data.get("type")
        try:
            element_type_enum = CodeElementType(element_type_str)
        except ValueError:
            logger.warning(
                f"Received invalid type '{element_type_str}' for member '{element_name}' in class '{parent_name}'. Setting to UNKNOWN."
            )
            method_data["type"] = CodeElementType.UNKNOWN.value
            element_type_enum = CodeElementType.UNKNOWN

        element = CodeElement.from_dict(method_data)
        element.parent_name = parent_name

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

    def _process_static_property(
        self, prop_data: Dict, parent_class_element: 'CodeElement'
    ) -> 'CodeElement':
        from codehem.models.code_element import CodeElement
        from codehem.models.enums import CodeElementType

        prop_name = prop_data.get("name", "unknown_static")
        parent_name = parent_class_element.name
        logger.debug(f"Processing static property: {prop_name} in class {parent_name}")

        prop_data["type"] = CodeElementType.STATIC_PROPERTY.value
        element = CodeElement.from_dict(prop_data)
        element.parent_name = parent_name
        element.value_type = prop_data.get("value_type")

        return element

    def _process_decorators(self, element_data: Dict) -> List['CodeElement']:
        from codehem.models.code_element import CodeElement, CodeRange
        from codehem.models.enums import CodeElementType
        from pydantic import ValidationError

        decorator_elements = []
        decorators_raw = element_data.get("decorators", [])
        parent_name = element_data.get("name")
        parent_class = element_data.get("class_name")
        full_parent_name = f"{parent_class}.{parent_name}" if parent_class else parent_name

        for dec_data in decorators_raw:
            if not isinstance(dec_data, dict):
                logger.warning(f"Skipping invalid decorator data format: {dec_data}")
                continue

            name = dec_data.get("name")
            content = dec_data.get("content")
            range_data = dec_data.get("range")

            if name and content:
                decorator_range = None
                if isinstance(range_data, dict):
                    try:
                        decorator_range = CodeRange(
                            start_line=range_data.get(
                                "start_line", range_data.get("start", {}).get("line", 1)
                            ),
                            start_column=range_data.get(
                                "start_column", range_data.get("start", {}).get("column", 0)
                            ),
                            end_line=range_data.get(
                                "end_line", range_data.get("end", {}).get("line", 1)
                            ),
                            end_column=range_data.get(
                                "end_column", range_data.get("end", {}).get("column", 0)
                            ),
                        )
                    except (ValidationError, KeyError, Exception) as e:
                        logger.warning(
                            f"Error creating CodeRange for decorator '{name}': {e}. Range data: {range_data}"
                        )
                else:
                    logger.warning(
                        f"Invalid range format for decorator '{name}': {type(range_data)}"
                    )

                decorator_elements.append(
                    CodeElement(
                        type=CodeElementType.DECORATOR,
                        name=name,
                        content=content,
                        range=decorator_range,
                        parent_name=full_parent_name,
                    )
                )
            else:
                logger.warning(
                    f"Skipping decorator without name or content: {dec_data}"
                )

        return decorator_elements

