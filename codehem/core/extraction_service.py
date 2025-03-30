"""
Main entry point for code extraction functionality.
Acts as a facade for the various extraction strategies.
"""
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

from codehem import CodeElementType
from codehem.core.engine.xpath_parser import XPathParser
from codehem.core.error_handling import handle_extraction_errors
from codehem.core.registry import registry
from codehem.languages import (
    get_language_service_for_code,
    get_language_service_for_file,
)
from codehem.models.code_element import CodeElement, CodeElementsResult

logger = logging.getLogger(__name__)

def extract_range(element: dict) -> Tuple[int, int]:
    range_data = element.get("range", {})
    return (
        range_data.get("start", {}).get("line", 0),
        range_data.get("end", {}).get("line", 0),
    )

def find_in_collection(collection: List[dict], element_name) -> Tuple[int, int]:
    for element in collection:
        if element.get("name") == element_name:
            return extract_range(element)
    return (0, 0)

class ExtractionService:
    """Main extractor class that delegates to specific extractors based on language."""

    def __init__(self, language_code: str):
        """
        Initialize the extraction service for a language.
        
        Args:
            language_code: The language code to extract from
        """
        self.language_code = language_code
        # Get the language service in a way that avoids circular dependencies
        self.language_service = None
        try:
            self.language_service = registry.get_language_service(language_code)
        except Exception as e:
            logger.error(f"Failed to get language service for {language_code}: {e}")

    def find_element(
        self,
        code: str,
        element_type: str,
        element_name: Optional[str] = None,
        parent_name: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        Find a specific element in the code based on type, name, and parent.

        Args:
            code: Source code as string
            element_type: Type of element to find (e.g., 'function', 'class', 'method')
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)

        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        logger.debug(
            f"Finding element of type '{element_type}', name '{element_name}', parent '{parent_name}'"
        )

        if self.language_service is None:
            logger.error("No language service available for extraction")
            return (0, 0)

        if element_name is None and parent_name is None:
            elements = self.extract_any(code, element_type)
            return extract_range(elements[0]) if elements else (0, 0)

        match element_type:
            case CodeElementType.METHOD.value if parent_name:
                methods = self.extract_methods(code, parent_name)
                return find_in_collection(methods, element_name)

            case CodeElementType.FUNCTION.value:
                return find_in_collection(self.extract_functions(code), element_name)

            case CodeElementType.CLASS.value:
                return find_in_collection(self.extract_classes(code), element_name)

            case CodeElementType.IMPORT.value:
                return find_in_collection(self.extract_imports(code), element_name)

            case t if (
                t
                in {
                    CodeElementType.PROPERTY.value,
                    CodeElementType.PROPERTY_GETTER.value,
                    CodeElementType.PROPERTY_SETTER.value,
                    CodeElementType.STATIC_PROPERTY.value,
                }
                and parent_name
            ):
                file_data = self._extract_file(code)
                for cls in file_data.get("classes", []):
                    if cls.get("name") == parent_name:
                        for method in cls.get("methods", []):
                            if (
                                method.get("name") == element_name
                                and method.get("type") == element_type
                            ):
                                return extract_range(method)

            case t if t in {
                CodeElementType.INTERFACE.value,
                CodeElementType.ENUM.value,
                CodeElementType.TYPE_ALIAS.value,
                CodeElementType.NAMESPACE.value,
            }:
                return find_in_collection(self.extract_any(code, element_type))

        return (0, 0)

    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        element_name, parent_name, element_type = XPathParser.get_element_info(xpath)
        logger.debug(
            f"XPath parsed: element_name={element_name}, parent_name={parent_name}, element_type={element_type}"
        )

        if not element_name and not element_type:
            return (0, 0)

        if element_type == CodeElementType.IMPORT.value and not element_name:
            return self._find_first_import(code)

        if element_type == "all":
            return self._find_with_all_qualifier(code, xpath)

        if element_name and element_type:
            return self.find_element(code, element_type, element_name, parent_name)

        if element_name and parent_name and not element_type:
            return self._find_last_method_with_name(code, element_name, parent_name)

        if element_name and not element_type:
            return self._try_common_element_types(code, element_name, parent_name)

        return (0, 0)

    def _find_first_import(self, code: str) -> Tuple[int, int]:
        imports = self.extract_imports(code)
        if imports:
            range_data = imports[0].get("range", {})
            return (
                range_data.get("start", {}).get("line", 0),
                range_data.get("end", {}).get("line", 0),
            )
        return (0, 0)

    def _find_with_all_qualifier(self, code: str, xpath: str) -> Tuple[int, int]:
        temp_xpath = xpath.replace("[all]", "")
        start_line, end_line = self.find_by_xpath(code, temp_xpath)
        if start_line == 0:
            return (0, 0)

        lines = code.splitlines()
        adjusted_start = start_line

        for i in range(start_line - 2, max(0, start_line - 10), -1):
            line = lines[i].strip()
            if line.startswith("@"):
                adjusted_start = i + 1
            elif line and not line.startswith("#"):
                break

        return (adjusted_start, end_line)

    def _find_last_method_with_name(
        self, code: str, method_name: str, class_name: str
    ) -> Tuple[int, int]:
        all_elements = self._extract_file(code)
        last_method = None
        latest_line = -1

        for cls in all_elements.get("classes", []):
            if cls.get("name") == class_name:
                for method in cls.get("methods", []):
                    if method.get("name") == method_name:
                        method_start_line = (
                            method.get("range", {}).get("start", {}).get("line", 0)
                        )
                        if method_start_line > latest_line:
                            latest_line = method_start_line
                            last_method = method

        if last_method:
            range_data = last_method.get("range", {})
            return (
                range_data.get("start", {}).get("line", 0),
                range_data.get("end", {}).get("line", 0),
            )

        return (0, 0)

    def _try_common_element_types(
        self, code: str, element_name: str, parent_name: Optional[str]
    ) -> Tuple[int, int]:
        if parent_name:
            element_types = [
                CodeElementType.METHOD.value,
                CodeElementType.PROPERTY.value,
                CodeElementType.PROPERTY_GETTER.value,
                CodeElementType.PROPERTY_SETTER.value,
                CodeElementType.STATIC_PROPERTY.value,
            ]
        else:
            element_types = [
                CodeElementType.CLASS.value,
                CodeElementType.FUNCTION.value,
                CodeElementType.INTERFACE.value,
                CodeElementType.ENUM.value,
                CodeElementType.TYPE_ALIAS.value,
                CodeElementType.NAMESPACE.value,
            ]

        for type_to_try in element_types:
            result = self.find_element(code, type_to_try, element_name, parent_name)
            if result[0] > 0:
                return result
        return (0, 0)


    @classmethod
    def from_file_path(cls, file_path: str) -> 'ExtractionService':
        """Create an extractor for a file based on its extension."""
        service = get_language_service_for_file(file_path)
        if not service:
            _, ext = os.path.splitext(file_path)
            raise ValueError(f'Unsupported file extension: {ext}')
        return cls(service.language_code)

    @classmethod
    def from_raw_code(cls, code: str, language_hints: List[str]=None) -> 'ExtractionService':
        """Create an extractor by attempting to detect the language from code."""
        if language_hints:
            for lang in language_hints:
                temp_extractor = cls(lang)
                if temp_extractor.extract_functions(code) or temp_extractor.extract_classes(code):
                    return temp_extractor
        service = get_language_service_for_code(code)
        if service:
            return cls(service.language_code)
        return cls('python')

    def get_descriptor(self, element_type_descriptor: Union[str, CodeElementType]) -> Optional[Any]:
        """Get the appropriate extractor for the given type and language."""
        if self.language_service is None:
            logger.error("No language service available for getting descriptor")
            return None
            
        descriptor = self.language_service.get_element_descriptor(element_type_descriptor)
        return descriptor

    @handle_extraction_errors
    def _extract_element_type(self, code: str, element_type: str, context: Dict[str, Any]=None) -> List[Dict]:
        """
        Generic method to extract a specific element type from code.
        
        Args:
            code: Source code as string
            element_type: Type of element to extract
            context: Additional context for extraction
            
        Returns:
            List of extracted elements as dictionaries
        """
        if self.language_service is None:
            logger.error("No language service available for extraction")
            return []
            
        extractor = self.language_service.get_extractor(element_type=element_type)
        if not extractor:
            logger.warning(f'Could not find extractor for {element_type} / {self.language_code}')
            return []
        logger.debug(f'Extracting {element_type} using {extractor.__class__.__name__}')
        results = extractor.extract(code, context=context)
        logger.debug(f'Extracted {len(results)} {element_type}s')
        return results

    @handle_extraction_errors
    def extract_functions(self, code: str) -> List[Dict]:
        """Extract functions from the provided code."""
        return self._extract_element_type(code, "function")

    @handle_extraction_errors
    def extract_classes(self, code: str) -> List[Dict]:
        """Extract classes from the provided code."""
        return self._extract_element_type(code, "class")

    @handle_extraction_errors
    def extract_methods(
        self, code: str, class_name: Optional[str] = None
    ) -> List[Dict]:
        """Extract methods from the provided code, optionally filtering by class."""
        context = {'class_name': class_name} if class_name else None
        return self._extract_element_type(code, 'method', context)

    @handle_extraction_errors
    def extract_imports(self, code: str) -> List[Dict]:
        """Extract imports from the provided code."""
        return self._extract_element_type(code, 'import')

    @handle_extraction_errors
    def extract_any(self, code, element_type: str) -> List[Dict]:
        """Extract any code element from the provided code."""
        return self._extract_element_type(code, element_type)

    def _extract_file(self, code: str) -> Dict[str, List[Dict]]:
        """
        Extract all code elements from the provided code.

        This is a private method that performs raw extraction.

        Args:
        code: Source code as string

        Returns:
        Dictionary with extracted elements categorized by type
        """
        print(f'Starting extraction for all elements')
        imports = self.extract_imports(code)
        print(f'Extracted {len(imports)} imports')
        classes = self.extract_classes(code)
        functions = self.extract_functions(code)
        results = {
            'imports': imports,
            'classes': classes,
            'functions': functions
        }
        for cls in classes:
            class_name = cls.get('name')
            if class_name:
                methods = self.extract_methods(code, class_name)
                getters = self._extract_element_type(code, CodeElementType.PROPERTY_GETTER.value, {'class_name': class_name})
                setters = self._extract_element_type(code, CodeElementType.PROPERTY_SETTER.value, {'class_name': class_name})
                statics = self._extract_element_type(code, CodeElementType.STATIC_PROPERTY.value, {'class_name': class_name})
                all_members = methods + getters + setters + statics
                cls['methods'] = all_members
                print(f"Added {len(all_members)} members to class '{class_name}'")
        print(f'Completed extraction: {len(imports)} imports, {len(classes)} classes, {len(functions)} functions')
        return results

    def _process_parameters(self, element: CodeElement, params_data: List[Dict]) -> List[CodeElement]:
        """
        Process parameter data and create parameter CodeElements.
        
        Args:
            element: Parent element (function or method)
            params_data: Raw parameter data
            
        Returns:
            List of parameter CodeElements
        """
        result = []
        for param in params_data:
            param_name = param.get('name')
            param_type = param.get('type')
            if param_name:
                param_element = CodeElement(type=CodeElementType.PARAMETER, name=param_name, content=param_name, parent_name=element.name if element.type == CodeElementType.FUNCTION else f'{element.parent_name}.{element.name}', value_type=param_type, additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                result.append(param_element)
        return result

    def _process_return_value(self, element: CodeElement, return_info: Dict) -> Optional[CodeElement]:
        """
        Process return value information and create a return value CodeElement.
        
        Args:
            element: Parent element (function or method)
            return_info: Raw return value data
            
        Returns:
            Return value CodeElement or None
        """
        return_type = return_info.get('return_type')
        return_values = return_info.get('return_values', [])
        if not return_type and (not return_values):
            return None
        return CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{element.name}_return', content=return_type if return_type else '', parent_name=element.name if element.type == CodeElementType.FUNCTION else f'{element.parent_name}.{element.name}', value_type=return_type, additional_data={'values': return_values})

    def _process_decorators(self, element: CodeElement, decorators_data: List[Dict]) -> List[CodeElement]:
        """
        Process decorator data and create decorator CodeElements.
        
        Args:
            element: Parent element (function, method, or class)
            decorators_data: Raw decorator data
            
        Returns:
            List of decorator CodeElements
        """
        result = []
        for dec in decorators_data:
            dec_name = dec.get('name')
            dec_content = dec.get('content')
            if dec_name:
                decorator_element = CodeElement(type=CodeElementType.DECORATOR, name=dec_name, content=dec_content, parent_name=element.name if element.type != CodeElementType.METHOD else f'{element.parent_name}.{element.name}')
                result.append(decorator_element)
        return result

    def _process_import_element(self, import_data: Dict) -> CodeElement:
        """
        Process import data and create an import CodeElement.
        
        Args:
            import_data: Raw import data
            
        Returns:
            Import CodeElement
        """
        logger.debug(f"Processing import: {import_data.get('name')}")
        return CodeElement.from_dict(import_data)

    def _process_function_element(self, function_data: Dict) -> CodeElement:
        """
        Process function data and create a function CodeElement with all its children.

        Args:
        function_data: Raw function data

        Returns:
        Function CodeElement with children
        """
        func_name = function_data.get('name', 'unknown')
        logger.debug(f'Processing function: {func_name}')
        func_element = CodeElement.from_dict(function_data)
        parameters = function_data.get('parameters', [])
        logger.debug(f'Function {func_name} has {len(parameters)} parameters')
        for param in parameters:
            param_name = param.get('name')
            param_type = param.get('type')
            if param_name:
                param_element = CodeElement(type=CodeElementType.PARAMETER, name=param_name, content=param_name, parent_name=func_name, value_type=param_type, additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                func_element.children.append(param_element)
        return_info = function_data.get('return_info', {})
        return_type = return_info.get('return_type')
        return_values = return_info.get('return_values', [])
        if return_type or return_values:
            return_element = CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{func_name}_return', content=return_type if return_type else '', parent_name=func_name, value_type=return_type, additional_data={'values': return_values})
            func_element.children.append(return_element)
        decorators = function_data.get('decorators', [])
        logger.debug(f'Function {func_name} has {len(decorators)} decorators')
        for dec in decorators:
            dec_name = dec.get('name')
            dec_content = dec.get('content')
            if dec_name:
                decorator_element = CodeElement(type=CodeElementType.DECORATOR, name=dec_name, content=dec_content, parent_name=func_name)
                func_element.children.append(decorator_element)
        return func_element

    def _process_method_element(self, method_data: Dict, parent_name: str) -> CodeElement:
        """
        Process method data and create a method CodeElement with all its children.

        Args:
        method_data: Raw method data
        parent_name: Name of the parent class

        Returns:
        Method CodeElement with children
        """
        method_name = method_data.get('name', 'unknown')
        logger.debug(f'Processing method: {method_name} in class {parent_name}')
        method_element = CodeElement.from_dict(method_data)
        method_element.parent_name = parent_name
        parameters = method_data.get('parameters', [])
        logger.debug(f'Method {method_name} has {len(parameters)} parameters')
        for param in parameters:
            param_name = param.get('name')
            param_type = param.get('type')
            if param_name:
                param_element = CodeElement(type=CodeElementType.PARAMETER, name=param_name, content=param_name, parent_name=f'{parent_name}.{method_name}', value_type=param_type, additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                method_element.children.append(param_element)
        return_info = method_data.get('return_info', {})
        return_type = return_info.get('return_type')
        return_values = return_info.get('return_values', [])
        if return_type or return_values:
            return_element = CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{method_name}_return', content=return_type if return_type else '', parent_name=f'{parent_name}.{method_name}', value_type=return_type, additional_data={'values': return_values})
            method_element.children.append(return_element)
        decorators = method_data.get("decorators", [])
        logger.debug(f"Method {method_name} has {len(decorators)} decorators")
        for dec in decorators:
            dec_name = dec.get("name")
            dec_content = dec.get("content")
            if dec_name:
                decorator_element = CodeElement(
                    type=CodeElementType.DECORATOR,
                    name=dec_name,
                    content=dec_content,
                    parent_name=f"{parent_name}.{method_name}",
                )
                method_element.children.append(decorator_element)
        return method_element

    def _process_class_element(self, class_data: Dict) -> CodeElement:
        """
        Process class data and create a class CodeElement with all its children (including methods).

        Args:
        class_data: Raw class data

        Returns:
        Class CodeElement with children
        """
        logger.debug(f"Processing class: {class_data.get('name')}")
        class_element = CodeElement.from_dict(class_data)

        # decorators
        cls_decorators = class_data.get("decorators", [])
        for dec_element in self._process_decorators(class_element, cls_decorators):
            class_element.children.append(dec_element)

        # methods (including getters/setters/statics)
        methods = class_data.get("methods", [])
        method_map: Dict[str, List[CodeElement]] = {}

        for method_data in methods:
            method_name = method_data.get("name")
            method_element = self._process_method_element(
                method_data, class_element.name
            )
            if method_name not in method_map:
                method_map[method_name] = []
            method_map[method_name].append(method_element)

        for method_name, versions in method_map.items():
            latest = versions[-1]
            for older in versions[:-1]:
                from copy import deepcopy
                latest.children.append(deepcopy(older))
            class_element.children.append(latest)

        return class_element


    def extract_all(self, code: str) -> CodeElementsResult:
        """
        Extract all code elements and convert them to a structured CodeElementsResult.

        Args:
            code: Source code as string

        Returns:
            CodeElementsResult containing extracted elements
        """
        try:
            raw_elements = self._extract_file(code)
            result = CodeElementsResult()
            for import_data in raw_elements.get('imports', []):
                import_element = self._process_import_element(import_data)
                result.elements.append(import_element)
            for function_data in raw_elements.get('functions', []):
                function_element = self._process_function_element(function_data)
                result.elements.append(function_element)
            for class_data in raw_elements.get('classes', []):
                class_element = self._process_class_element(class_data)
                result.elements.append(class_element)
            return result
        except Exception as e:
            logger.error(f'Error in extract_all: {str(e)}')
            return CodeElementsResult()