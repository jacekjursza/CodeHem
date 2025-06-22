"""
TypeScript post-processor component.

This module provides the TypeScript implementation of the IPostProcessor interface,
transforming raw extraction data into structured CodeElement objects.
"""

import logging
from typing import Any, Dict, List, Optional

from codehem.core.components.interfaces import IPostProcessor
from codehem.core.post_processors.base import LanguagePostProcessor
from codehem.models.code_element import CodeElement, CodeElementsResult
from codehem.models.enums import CodeElementType
from codehem.models.range import CodeRange
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class TypeScriptPostProcessor(LanguagePostProcessor):
    """
    TypeScript implementation of the IPostProcessor interface.
    
    Transforms raw extraction data into structured CodeElement objects with proper
    relationships, handling TypeScript/JavaScript-specific features like interfaces, 
    type aliases, decorators, and JSX/TSX components.
    """
    
    def __init__(self):
        """Initialize the TypeScript post-processor."""
        super().__init__('typescript')
    
    def process_imports(self, raw_imports: List[Dict]) -> List[CodeElement]:
        """
        Process raw import data into CodeElement objects.
        
        For TypeScript, imports can be ES modules, CommonJS requires, or namespace imports.
        This method handles all import types and creates a single CodeElement representing
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
        
        Handles both regular functions and arrow functions, processing parameters,
        return types, and decorators.
        
        Args:
            raw_functions: List of raw function dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing functions
        """
        processed_functions = []
        logger.debug(f"process_functions: Processing {len(raw_functions or [])} functions with {len(all_decorators or [])} decorators")
        
        # Build decorator lookup by parent name
        decorator_lookup = self._build_lookup(all_decorators, 'parent_name')
        
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
                
                # Process decorators from the global decorator list
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
                
                # Add TypeScript-specific information
                if 'is_async' in function_data and function_data['is_async']:
                    func_element.additional_data['is_async'] = True
                if 'is_arrow_function' in function_data and function_data['is_arrow_function']:
                    func_element.additional_data['is_arrow_function'] = True
                if 'is_generator' in function_data and function_data['is_generator']:
                    func_element.additional_data['is_generator'] = True
                
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
        member_lookup = self._build_lookup(members, 'class_name')
        static_prop_lookup = self._build_lookup(static_props, 'class_name')
        property_lookup = self._build_lookup(properties or [], 'class_name')
        decorator_lookup = self._build_lookup(all_decorators, 'parent_name')
        
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
            
            # Ensure type is set correctly - could be CLASS or INTERFACE in TypeScript
            class_type = class_data.get('type', CodeElementType.CLASS.value)
            if class_type not in [CodeElementType.CLASS.value, CodeElementType.INTERFACE.value]:
                class_type = CodeElementType.CLASS.value
            class_data['type'] = class_type
            
            try:
                # Create CodeElement from raw data
                class_element = CodeElement.from_dict(class_data)
                class_element.parent_name = None
                
                # Store TypeScript-specific information
                if 'extends' in class_data:
                    class_element.additional_data['extends'] = class_data['extends']
                if 'implements' in class_data:
                    class_element.additional_data['implements'] = class_data['implements']
                if 'abstract' in class_data and class_data['abstract']:
                    class_element.additional_data['abstract'] = True
                
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
                        
                    processed_member = self._process_member_element(member_data, class_element, decorator_lookup)
                    if processed_member:
                        processed_members[(processed_member.type.value, processed_member.name)] = processed_member
                
                # Process regular properties (class fields in TS)
                processed_props = {}
                props_for_this_class = property_lookup.get(class_name, [])
                
                # Sort properties by line number
                props_for_this_class.sort(key=lambda p: 
                    p.get('range', {}).get('start', {}).get('line', 0)
                )
                
                for prop_data in props_for_this_class:
                    if not isinstance(prop_data, dict):
                        continue
                        
                    prop_name = prop_data.get('name')
                    if prop_name and not any(key[1] == prop_name for key in processed_members.keys()):
                        processed_prop = self._process_property(prop_data, class_element, decorator_lookup)
                        if processed_prop:
                            processed_props[processed_prop.name] = processed_prop
                    elif prop_name:
                        logger.debug(f"process_classes: Skipping property '{prop_name}' as a member with the same name already exists.")
                
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
                        processed_prop = self._process_static_property(prop_data, class_element, decorator_lookup)
                        if processed_prop:
                            processed_static_props[processed_prop.name] = processed_prop
                    elif prop_name:
                        logger.debug(f"process_classes: Skipping static property '{prop_name}' as a member with the same name already exists.")
                
                # Add all children to the class
                class_element.children.extend(list(processed_members.values()))
                class_element.children.extend(list(processed_props.values()))
                class_element.children.extend(list(processed_static_props.values()))
                
                # Sort children by line number for consistent order
                class_element.children.sort(key=lambda child: 
                    child.range.start_line if child.range else float('inf')
                )
                
                processed_classes.append(class_element)
                
            except (ValidationError, Exception) as e:
                logger.error(f"process_classes: Failed to process class '{class_name}': {e}", exc_info=True)
        
        return processed_classes
    
    def process_interfaces(self, raw_interfaces: List[Dict], 
                         all_decorators: Optional[List[Dict]]=None) -> List[CodeElement]:
        """
        Process raw interface data into CodeElement objects.
        
        Args:
            raw_interfaces: List of raw interface dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing interfaces
        """
        processed_interfaces = []
        logger.debug(f"process_interfaces: Processing {len(raw_interfaces or [])} interfaces")
        
        # Build decorator lookup by parent name
        decorator_lookup = self._build_lookup(all_decorators, 'parent_name')
        
        for interface_data in raw_interfaces or []:
            if not isinstance(interface_data, dict):
                logger.warning(f'process_interfaces: Skipping non-dict item: {type(interface_data)}')
                continue
                
            interface_name = interface_data.get('name')
            if not interface_name:
                logger.warning(f'process_interfaces: Found interface without a name: {interface_data}')
                continue
                
            logger.debug(f'process_interfaces: Processing interface: {interface_name}')
            
            # Ensure type is set correctly
            interface_data['type'] = CodeElementType.INTERFACE.value
            
            try:
                # Create CodeElement from raw data
                interface_element = CodeElement.from_dict(interface_data)
                interface_element.parent_name = None
                
                # Store TypeScript-specific information for interfaces
                if 'extends' in interface_data:
                    interface_element.additional_data['extends'] = interface_data['extends']
                
                # Process methods and properties
                methods = interface_data.get('methods', [])
                properties = interface_data.get('properties', [])
                
                # Process methods
                for method_data in methods:
                    if not isinstance(method_data, dict):
                        continue
                    
                    method_data['parent_name'] = interface_name
                    processed_method = self._process_interface_method(method_data)
                    if processed_method:
                        interface_element.children.append(processed_method)
                
                # Process properties
                for prop_data in properties:
                    if not isinstance(prop_data, dict):
                        continue
                    
                    prop_data['parent_name'] = interface_name
                    processed_prop = self._process_interface_property(prop_data)
                    if processed_prop:
                        interface_element.children.append(processed_prop)
                
                # Sort children by line number
                interface_element.children.sort(key=lambda child: 
                    child.range.start_line if child.range else float('inf')
                )
                
                processed_interfaces.append(interface_element)
                
            except (ValidationError, Exception) as e:
                logger.error(f"process_interfaces: Failed to process interface '{interface_name}': {e}", exc_info=True)
        
        return processed_interfaces
    
    def process_type_aliases(self, raw_type_aliases: List[Dict],
                           all_decorators: Optional[List[Dict]]=None) -> List[CodeElement]:
        """
        Process raw type alias data into CodeElement objects.
        
        Args:
            raw_type_aliases: List of raw type alias dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing type aliases
        """
        processed_type_aliases = []
        logger.debug(f"process_type_aliases: Processing {len(raw_type_aliases or [])} type aliases")
        
        for type_alias_data in raw_type_aliases or []:
            if not isinstance(type_alias_data, dict):
                logger.warning(f'process_type_aliases: Skipping non-dict item: {type(type_alias_data)}')
                continue
                
            type_alias_name = type_alias_data.get('name')
            if not type_alias_name:
                logger.warning(f'process_type_aliases: Found type alias without a name: {type_alias_data}')
                continue
                
            logger.debug(f'process_type_aliases: Processing type alias: {type_alias_name}')
            
            # Ensure type is set correctly
            type_alias_data['type'] = CodeElementType.TYPE_ALIAS.value
            
            try:
                # Create CodeElement from raw data
                type_alias_element = CodeElement.from_dict(type_alias_data)
                type_alias_element.parent_name = None
                
                # Store TypeScript-specific information
                if 'type_parameters' in type_alias_data:
                    type_alias_element.additional_data['type_parameters'] = type_alias_data['type_parameters']
                
                # Store the type value
                if 'value_type' in type_alias_data:
                    type_alias_element.value_type = type_alias_data['value_type']
                
                processed_type_aliases.append(type_alias_element)
                
            except (ValidationError, Exception) as e:
                logger.error(f"process_type_aliases: Failed to process type alias '{type_alias_name}': {e}", exc_info=True)
        
        return processed_type_aliases
    
    def process_enums(self, raw_enums: List[Dict],
                    all_decorators: Optional[List[Dict]]=None) -> List[CodeElement]:
        """
        Process raw enum data into CodeElement objects.
        
        Args:
            raw_enums: List of raw enum dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing enums
        """
        processed_enums = []
        logger.debug(f"process_enums: Processing {len(raw_enums or [])} enums")
        
        # Build decorator lookup by parent name
        decorator_lookup = self._build_lookup(all_decorators, 'parent_name')
        
        for enum_data in raw_enums or []:
            if not isinstance(enum_data, dict):
                logger.warning(f'process_enums: Skipping non-dict item: {type(enum_data)}')
                continue
                
            enum_name = enum_data.get('name')
            if not enum_name:
                logger.warning(f'process_enums: Found enum without a name: {enum_data}')
                continue
                
            logger.debug(f'process_enums: Processing enum: {enum_name}')
            
            # Ensure type is set correctly
            enum_data['type'] = CodeElementType.ENUM.value
            
            try:
                # Create CodeElement from raw data
                enum_element = CodeElement.from_dict(enum_data)
                enum_element.parent_name = None
                
                # Store TypeScript-specific information (const enum, etc.)
                if 'is_const' in enum_data and enum_data['is_const']:
                    enum_element.additional_data['is_const'] = True
                
                # Add decorators from the global decorator list
                if decorator_lookup:
                    enum_decorators = decorator_lookup.get(enum_name, [])
                    for dec_data in enum_decorators:
                        decorator = self._process_decorator_element(dec_data)
                        if decorator:
                            enum_element.children.append(decorator)
                
                # Process enum members
                for member_data in enum_data.get('members', []):
                    if not isinstance(member_data, dict):
                        continue
                    
                    member_name = member_data.get('name')
                    if not member_name:
                        continue
                    
                    try:
                        member_element = CodeElement(
                            type=CodeElementType.ENUM_MEMBER,
                            name=member_name,
                            content=member_data.get('content', ''),
                            parent_name=enum_name,
                            additional_data={
                                'value': member_data.get('value')
                            }
                        )
                        enum_element.children.append(member_element)
                    except (ValidationError, Exception) as e:
                        logger.error(f"process_enums: Failed to create enum member '{member_name}': {e}", exc_info=True)
                
                # Sort enum members by line number if range information is available
                enum_element.children.sort(key=lambda child: 
                    child.range.start_line if child.range else float('inf')
                )
                
                processed_enums.append(enum_element)
                
            except (ValidationError, Exception) as e:
                logger.error(f"process_enums: Failed to process enum '{enum_name}': {e}", exc_info=True)
        
        return processed_enums
    
    def process_namespaces(self, raw_namespaces: List[Dict],
                         all_decorators: Optional[List[Dict]]=None) -> List[CodeElement]:
        """
        Process raw namespace data into CodeElement objects.
        
        Args:
            raw_namespaces: List of raw namespace dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing namespaces
        """
        processed_namespaces = []
        logger.debug(f"process_namespaces: Processing {len(raw_namespaces or [])} namespaces")
        
        # Build decorator lookup by parent name
        decorator_lookup = self._build_lookup(all_decorators, 'parent_name')
        
        for namespace_data in raw_namespaces or []:
            if not isinstance(namespace_data, dict):
                logger.warning(f'process_namespaces: Skipping non-dict item: {type(namespace_data)}')
                continue
                
            namespace_name = namespace_data.get('name')
            if not namespace_name:
                logger.warning(f'process_namespaces: Found namespace without a name: {namespace_data}')
                continue
                
            logger.debug(f'process_namespaces: Processing namespace: {namespace_name}')
            
            # Ensure type is set correctly
            namespace_data['type'] = CodeElementType.NAMESPACE.value
            
            try:
                # Create CodeElement from raw data
                namespace_element = CodeElement.from_dict(namespace_data)
                namespace_element.parent_name = None
                
                # Add decorators from the global decorator list
                if decorator_lookup:
                    namespace_decorators = decorator_lookup.get(namespace_name, [])
                    for dec_data in namespace_decorators:
                        decorator = self._process_decorator_element(dec_data)
                        if decorator:
                            namespace_element.children.append(decorator)
                
                # Process child elements
                for element_type, elements in namespace_data.get('members', {}).items():
                    if not isinstance(elements, list):
                        continue
                    
                    processor_method = None
                    if element_type == 'functions':
                        processor_method = self.process_functions
                    elif element_type == 'classes':
                        # Simplified version - actual implementation would need members, props, etc.
                        processor_method = lambda x, _: self.process_classes(x, [], [], [])
                    elif element_type == 'interfaces':
                        processor_method = self.process_interfaces
                    elif element_type == 'type_aliases':
                        processor_method = self.process_type_aliases
                    elif element_type == 'enums':
                        processor_method = self.process_enums
                    
                    if processor_method:
                        for member in processor_method(elements, []):
                            if not member.parent_name:
                                member.parent_name = namespace_name
                            namespace_element.children.append(member)
                
                # Sort children by line number
                namespace_element.children.sort(key=lambda child: 
                    child.range.start_line if child.range else float('inf')
                )
                
                processed_namespaces.append(namespace_element)
                
            except (ValidationError, Exception) as e:
                logger.error(f"process_namespaces: Failed to process namespace '{namespace_name}': {e}", exc_info=True)
        
        return processed_namespaces
    
    def process_all(self, raw_elements: Dict[str, List[Dict]]) -> CodeElementsResult:
        """
        Process all raw extracted elements into a structured CodeElementsResult.
        
        Args:
            raw_elements: Dictionary mapping element types to lists of raw element dictionaries
            
        Returns:
            A CodeElementsResult containing all processed CodeElement objects
        """
        logger.debug(f"process_all: Processing {sum(len(elems) for elems in raw_elements.values())} raw elements")
        
        all_elements = []
        
        # Extract decorators first since they are used by other processors
        all_decorators = raw_elements.get('decorators', [])
        
        # Process imports
        imports = self.process_imports(raw_elements.get('imports', []))
        all_elements.extend(imports)
        
        # Process functions
        functions = self.process_functions(
            raw_elements.get('functions', []), 
            all_decorators
        )
        all_elements.extend(functions)
        
        # Process classes with their members, static properties, and properties
        classes = self.process_classes(
            raw_elements.get('classes', []),
            raw_elements.get('members', []),  # Fixed: Use 'members' instead of 'methods'
            raw_elements.get('static_properties', []),
            raw_elements.get('properties', []),
            all_decorators
        )
        all_elements.extend(classes)
        
        # Process interfaces
        interfaces = self.process_interfaces(
            raw_elements.get('interfaces', []),
            all_decorators
        )
        all_elements.extend(interfaces)
        
        # Process type aliases
        type_aliases = self.process_type_aliases(
            raw_elements.get('type_aliases', []),
            all_decorators
        )
        all_elements.extend(type_aliases)
        
        # Process enums
        enums = self.process_enums(
            raw_elements.get('enums', []),
            all_decorators
        )
        all_elements.extend(enums)
        
        # Process namespaces
        namespaces = self.process_namespaces(
            raw_elements.get('namespaces', []),
            all_decorators
        )
        all_elements.extend(namespaces)
        
        logger.debug(f"process_all: Created {len(all_elements)} CodeElement objects")
        
        try:
            # Create the final CodeElementsResult
            result = CodeElementsResult(elements=all_elements)
            return result
        except (ValidationError, Exception) as e:
            logger.error(f"process_all: Failed to create CodeElementsResult: {e}", exc_info=True)
            # Return an empty result if creation fails
            return CodeElementsResult(elements=[])
    
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
                # Create content with TypeScript type annotations and default values
                content_parts = [name]
                value_type = param.get("type")
                
                # Handle optional parameters in TypeScript style
                is_optional = param.get("optional", False)
                has_default = "default" in param
                
                # Add ? to parameter name if optional and no default value
                if is_optional and not has_default:
                    content_parts[0] += "?"
                
                # Add type annotation
                if value_type:
                    content_parts.append(f": {value_type}")
                
                # Add default value
                default_value = param.get("default")
                if default_value is not None:
                    content_parts.append(f" = {default_value}")
                
                content = "".join(content_parts)
                
                param_element = CodeElement(
                    type=CodeElementType.PARAMETER,
                    name=name,
                    content=content,
                    parent_name=parent_path,
                    value_type=value_type,
                    additional_data={
                        "optional": is_optional,
                        "default": default_value,
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
            # Format the return type appropriately for TypeScript
            content = f": {return_type}" if return_type else ""
            
            return_element = CodeElement(
                type=CodeElementType.RETURN_VALUE,
                name=f"{element.name}_return",  # Standardized name
                content=content,
                parent_name=parent_path,
                value_type=return_type,
                additional_data={
                    "values": return_values  # Store observed return values
                },
            )
            return return_element
        except (ValidationError, Exception) as e:
            logger.error(f"_process_return_value: Failed to create return value CodeElement for {element.name}: {e}", exc_info=True)
            return None
    
    def _process_member_element(self, method_data: Dict, parent_class_element: CodeElement, 
                              decorator_lookup: Optional[Dict[str, List[Dict]]]=None) -> Optional[CodeElement]:
        """
        Process raw method data into a CodeElement object.
        
        Handles classification of methods, including property accessors.
        
        Args:
            method_data: Raw method dictionary
            parent_class_element: The parent class CodeElement
            decorator_lookup: Optional dictionary mapping parent names to decorator lists
            
        Returns:
            CodeElement representing the method or None if processing fails
        """
        element_name = method_data.get("name", "unknown_member")
        parent_name = parent_class_element.name
        initial_type_str = method_data.get("type", CodeElementType.METHOD.value)
        
        logger.debug(f"_process_member_element: Processing member: {element_name} (initial type: {initial_type_str}) in class {parent_name}")
        
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
            
            # Add TypeScript-specific information
            if 'access_modifier' in method_data:
                element.additional_data['access_modifier'] = method_data['access_modifier']
            if 'is_async' in method_data and method_data['is_async']:
                element.additional_data['is_async'] = True
            if 'is_generator' in method_data and method_data['is_generator']:
                element.additional_data['is_generator'] = True
            if 'is_abstract' in method_data and method_data['is_abstract']:
                element.additional_data['is_abstract'] = True
            if 'is_readonly' in method_data and method_data['is_readonly']:
                element.additional_data['is_readonly'] = True
            
            # Add decorators using decorator lookup if available
            if decorator_lookup:
                full_name = f"{parent_name}.{element_name}"
                for dec_data in decorator_lookup.get(full_name, []):
                    decorator = self._process_decorator_element(dec_data, full_name)
                    if decorator:
                        element.children.append(decorator)
            
            # Process parameters and return type
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
            logger.error(f"_process_member_element: Failed to process method '{element_name}' in class '{parent_name}': {e}", exc_info=True)
            return None
    
    def _process_property(self, prop_data: Dict, parent_class_element: CodeElement,
                        decorator_lookup: Optional[Dict[str, List[Dict]]]=None) -> Optional[CodeElement]:
        """
        Process raw property data into a CodeElement object.
        
        Args:
            prop_data: Raw property dictionary
            parent_class_element: The parent class CodeElement
            decorator_lookup: Optional dictionary mapping parent names to decorator lists
            
        Returns:
            CodeElement representing the property or None if processing fails
        """
        prop_name = prop_data.get("name", "unknown_property")
        parent_name = parent_class_element.name
        
        logger.debug(f"_process_property: Processing property: {prop_name} in class {parent_name}")
        
        if not isinstance(prop_data, dict):
            logger.warning(f"_process_property: Invalid prop_data format: {type(prop_data)}")
            return None
            
        # Ensure type is set correctly
        prop_data["type"] = CodeElementType.PROPERTY.value
        
        try:
            # Create CodeElement from raw data
            element = CodeElement.from_dict(prop_data)
            element.parent_name = parent_name
            element.value_type = prop_data.get("value_type")  # Keep potential type hint
            
            # Add TypeScript-specific information
            if 'access_modifier' in prop_data:
                element.additional_data['access_modifier'] = prop_data['access_modifier']
            if 'is_readonly' in prop_data and prop_data['is_readonly']:
                element.additional_data['is_readonly'] = True
            if 'is_optional' in prop_data and prop_data['is_optional']:
                element.additional_data['is_optional'] = True
            
            # Store the extracted value if available
            if "value" in prop_data:
                element.additional_data["value"] = prop_data["value"]
            
            # Add decorators using decorator lookup if available
            if decorator_lookup:
                full_name = f"{parent_name}.{prop_name}"
                for dec_data in decorator_lookup.get(full_name, []):
                    decorator = self._process_decorator_element(dec_data, full_name)
                    if decorator:
                        element.children.append(decorator)
            
            return element
        except (ValidationError, Exception) as e:
            logger.error(f"_process_property: Failed to process property '{prop_name}' in class '{parent_name}': {e}", exc_info=True)
            return None
    
    def _process_static_property(self, prop_data: Dict, parent_class_element: CodeElement,
                               decorator_lookup: Optional[Dict[str, List[Dict]]]=None) -> Optional[CodeElement]:
        """
        Process raw static property data into a CodeElement object.
        
        Args:
            prop_data: Raw static property dictionary
            parent_class_element: The parent class CodeElement
            decorator_lookup: Optional dictionary mapping parent names to decorator lists
            
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
            
            # Add TypeScript-specific information
            if 'access_modifier' in prop_data:
                element.additional_data['access_modifier'] = prop_data['access_modifier']
            if 'is_readonly' in prop_data and prop_data['is_readonly']:
                element.additional_data['is_readonly'] = True
            
            # Store the extracted value if available
            if "value" in prop_data:
                element.additional_data["value"] = prop_data["value"]
            
            # Add decorators using decorator lookup if available
            if decorator_lookup:
                full_name = f"{parent_name}.{prop_name}"
                for dec_data in decorator_lookup.get(full_name, []):
                    decorator = self._process_decorator_element(dec_data, full_name)
                    if decorator:
                        element.children.append(decorator)
            
            return element
        except (ValidationError, Exception) as e:
            logger.error(f"_process_static_property: Failed to process static property '{prop_name}' in class '{parent_name}': {e}", exc_info=True)
            return None
    
    def _process_interface_method(self, method_data: Dict) -> Optional[CodeElement]:
        """
        Process raw interface method data into a CodeElement object.
        
        Args:
            method_data: Raw method dictionary from an interface
            
        Returns:
            CodeElement representing the interface method or None if processing fails
        """
        method_name = method_data.get("name", "unknown_method")
        parent_name = method_data.get("parent_name")
        
        if not parent_name:
            logger.warning(f"_process_interface_method: Method '{method_name}' has no parent name")
            return None
        
        logger.debug(f"_process_interface_method: Processing interface method: {method_name} in interface {parent_name}")
        
        try:
            # Set the correct type for interface methods
            method_data["type"] = CodeElementType.METHOD.value
            
            # Create CodeElement from raw data
            element = CodeElement.from_dict(method_data)
            element.parent_name = parent_name
            
            # Add TypeScript-specific information
            if 'is_optional' in method_data and method_data['is_optional']:
                element.additional_data['is_optional'] = True
            
            # Process parameters and return type
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
            logger.error(f"_process_interface_method: Failed to process interface method '{method_name}': {e}", exc_info=True)
            return None
    
    def _process_interface_property(self, prop_data: Dict) -> Optional[CodeElement]:
        """
        Process raw interface property data into a CodeElement object.
        
        Args:
            prop_data: Raw property dictionary from an interface
            
        Returns:
            CodeElement representing the interface property or None if processing fails
        """
        prop_name = prop_data.get("name", "unknown_property")
        parent_name = prop_data.get("parent_name")
        
        if not parent_name:
            logger.warning(f"_process_interface_property: Property '{prop_name}' has no parent name")
            return None
        
        logger.debug(f"_process_interface_property: Processing interface property: {prop_name} in interface {parent_name}")
        
        try:
            # Set the correct type for interface properties
            prop_data["type"] = CodeElementType.PROPERTY.value
            
            # Create CodeElement from raw data
            element = CodeElement.from_dict(prop_data)
            element.parent_name = parent_name
            element.value_type = prop_data.get("value_type")  # Keep potential type hint
            
            # Add TypeScript-specific information
            if 'is_readonly' in prop_data and prop_data['is_readonly']:
                element.additional_data['is_readonly'] = True
            if 'is_optional' in prop_data and prop_data['is_optional']:
                element.additional_data['is_optional'] = True
            
            return element
        except (ValidationError, Exception) as e:
            logger.error(f"_process_interface_property: Failed to process interface property '{prop_name}': {e}", exc_info=True)
            return None
    
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
            
            # Add decorator arguments if available
            if 'arguments' in dec_data:
                decorator_element.additional_data['arguments'] = dec_data['arguments']
            
            return decorator_element
        except (ValidationError, Exception) as e:
            logger.error(f"_process_decorator_element: Failed to create decorator CodeElement for '{name}': {e}", exc_info=True)
            return None
    
    def _build_lookup(self, items: List[Dict], key_field: str) -> Dict[str, List[Dict]]:
        """
        Build a lookup dictionary for items based on a key field.
        
        Args:
            items: List of dictionaries containing the items
            key_field: The field to use as key in the lookup dictionary
            
        Returns:
            Dictionary mapping key field values to lists of items
        """
        result = {}
        if not items:
            return result
            
        for item in items:
            if not isinstance(item, dict):
                continue
                
            key = item.get(key_field)
            if not key:
                continue
                
            if key not in result:
                result[key] = []
                
            result[key].append(item)
            
        return result
