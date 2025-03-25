"""
Main entry point for code extraction functionality.
Acts as a facade for the various extraction strategies.
"""
import re
from typing import Dict, List, Optional, Any, Tuple, Union
import os
import logging

import rich

from codehem import CodeElementType
from codehem.core.engine.xpath_parser import XPathParser
from codehem.core.registry import registry
from codehem.core.error_handling import handle_extraction_errors
from codehem.core.service import LanguageService
from codehem.languages import get_language_service_for_file, get_language_service_for_code
from codehem.models.code_element import CodeElement, CodeElementsResult
logger = logging.getLogger(__name__)

class ExtractionService:
    """Main extractor class that delegates to specific extractors based on language."""

    def __init__(self, language_code: str):
        self.language_code = language_code
        self.language_service: LanguageService = registry.get_language_service(language_code)
        logger.debug(f'Created extractor for language: {language_code}')

    def find_element(self, code: str, element_type: str, element_name: Optional[str]=None, parent_name: Optional[str]=None) -> Tuple[int, int]:
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
        logger.debug(f"Finding element of type '{element_type}', name '{element_name}', parent '{parent_name}'")
        if element_name is None and parent_name is None:
            elements = self.extract_any(code, element_type)
            if elements and len(elements) > 0:
                first_element = elements[0]
                return (first_element.get('start_line', 0), first_element.get('end_line', 0))
            return (0, 0)
        if element_type == CodeElementType.METHOD.value and parent_name:
            methods = self.extract_methods(code, parent_name)
            for method in methods:
                if method.get('name') == element_name:
                    return (method.get('start_line', 0), method.get('end_line', 0))
        elif element_type == CodeElementType.FUNCTION.value:
            functions = self.extract_functions(code)
            for func in functions:
                if func.get('name') == element_name:
                    return (func.get('start_line', 0), func.get('end_line', 0))
        elif element_type == CodeElementType.CLASS.value:
            classes = self.extract_classes(code)
            for cls in classes:
                if cls.get('name') == element_name:
                    return (cls.get('start_line', 0), cls.get('end_line', 0))
        elif element_type == CodeElementType.IMPORT.value:
            imports = self.extract_imports(code)
            for imp in imports:
                if imp.get('name') == element_name:
                    return (imp.get('start_line', 0), imp.get('end_line', 0))
        elif element_type in [CodeElementType.PROPERTY.value, CodeElementType.PROPERTY_GETTER.value, CodeElementType.PROPERTY_SETTER.value, CodeElementType.STATIC_PROPERTY.value] and parent_name:
            all_elements = self._extract_file(code)
            for cls in all_elements.get('classes', []):
                if cls.get('name') == parent_name:
                    for prop in cls.get('methods', []):
                        if prop.get('name') == element_name and prop.get('type') == element_type:
                            return (prop.get('start_line', 0), prop.get('end_line', 0))
        return (0, 0)

    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        """
        Find an element in the code using an XPath-like expression.

        Args:
            code: Source code as string
            xpath: XPath-like expression (e.g., 'ClassName.method_name')

        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        (element_name, parent_name, element_type) = XPathParser.get_element_info(xpath)
        if not element_name and (not element_type):
            return (0, 0)
        if element_type == CodeElementType.IMPORT.value and (not element_name):
            return self.extract_any(code, element_type)
        if element_name and element_type:
            return self.extract_any(code, element_type, element_name, parent_name)
        if element_name and (not element_type):
            if parent_name:
                element_types = [CodeElementType.METHOD.value, CodeElementType.PROPERTY.value, CodeElementType.PROPERTY_GETTER.value, CodeElementType.PROPERTY_SETTER.value, CodeElementType.STATIC_PROPERTY.value]
            else:
                element_types = [CodeElementType.CLASS.value, CodeElementType.FUNCTION.value, CodeElementType.INTERFACE.value]
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
            (_, ext) = os.path.splitext(file_path)
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
        descriptor = self.language_service.get_element_descriptor(element_type_descriptor)
        return descriptor

    @handle_extraction_errors
    def _extract_element_type(self, code: str, element_type: str, context: Dict[str, Any] = None) -> List[Dict]:
        """
        Generic method to extract a specific element type from code.
        
        Args:
            code: Source code as string
            element_type: Type of element to extract
            context: Additional context for extraction
            
        Returns:
            List of extracted elements as dictionaries
        """
        extractor = self.language_service.get_extractor(element_type=element_type)
        if not extractor:
            logger.warning(f'Could not find extractor for {element_type} / {self.language_code}')
            return []

        logger.debug(f'Extracting {element_type} using {extractor.__class__.__name__}')
        results = extractor.extract(code)
        logger.debug(f'Extracted {len(results)} {element_type}s')
        return results

    @handle_extraction_errors
    def extract_functions(self, code: str) -> List[Dict]:
        """Extract functions from the provided code."""
        return self._extract_element_type(code, 'function')

    @handle_extraction_errors
    def extract_classes(self, code: str) -> List[Dict]:
        """Extract classes from the provided code."""
        return self._extract_element_type(code, 'class')

    @handle_extraction_errors
    def extract_methods(self, code: str, class_name: Optional[str]=None) -> List[Dict]:
        """Extract methods from the provided code, optionally filtering by class."""
        context = None
        if class_name:
            context = {'class_name': class_name}
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
        logger.debug(f'Starting extraction for all elements')
        imports = self.extract_imports(code)
        classes = self.extract_classes(code)
        functions = self.extract_functions(code)
        results = {'imports': imports, 'classes': classes, 'functions': functions}
        for cls in classes:
            class_name = cls.get('name')
            if class_name:
                methods = self.extract_methods(code, class_name)
                cls['methods'] = methods
                logger.debug(f"Added {len(methods)} methods to class '{class_name}'")
        logger.debug(f'Completed extraction: {len(imports)} imports, {len(classes)} classes, {len(functions)} functions')
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
                param_element = CodeElement(
                    type=CodeElementType.PARAMETER,
                    name=param_name,
                    content=param_name,
                    parent_name=element.name if element.type == CodeElementType.FUNCTION else f'{element.parent_name}.{element.name}',
                    value_type=param_type,
                    additional_data={
                        'optional': param.get('optional', False),
                        'default': param.get('default')
                    }
                )
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
        
        if not return_type and not return_values:
            return None
            
        return CodeElement(
            type=CodeElementType.RETURN_VALUE,
            name=f'{element.name}_return',
            content=return_type if return_type else '',
            parent_name=element.name if element.type == CodeElementType.FUNCTION else f'{element.parent_name}.{element.name}',
            value_type=return_type,
            additional_data={'values': return_values}
        )
        
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
                decorator_element = CodeElement(
                    type=CodeElementType.DECORATOR,
                    name=dec_name,
                    content=dec_content,
                    parent_name=element.name if element.type != CodeElementType.METHOD else f'{element.parent_name}.{element.name}'
                )
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
        logger.debug(f"Processing function: {function_data.get('name')}")
        func_element = CodeElement.from_dict(function_data)
        
        # Process parameters
        parameters = function_data.get('parameters', [])
        for param_element in self._process_parameters(func_element, parameters):
            func_element.children.append(param_element)
        
        # Process return value
        return_info = function_data.get('return_info', {})
        return_element = self._process_return_value(func_element, return_info)
        if return_element:
            func_element.children.append(return_element)
        
        # Process decorators
        decorators = function_data.get('decorators', [])
        for dec_element in self._process_decorators(func_element, decorators):
            func_element.children.append(dec_element)
            
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
        logger.debug(f"Processing method: {method_data.get('name')} in class {parent_name}")
        method_element = CodeElement.from_dict(method_data)
        method_element.parent_name = parent_name
        
        # Process method parameters
        parameters = method_data.get('parameters', [])
        for param_element in self._process_parameters(method_element, parameters):
            method_element.children.append(param_element)
        
        # Process method return value
        return_info = method_data.get('return_info', {})
        return_element = self._process_return_value(method_element, return_info)
        if return_element:
            method_element.children.append(return_element)
        
        # Process method decorators
        method_decorators = method_data.get('decorators', [])
        for dec_element in self._process_decorators(method_element, method_decorators):
            method_element.children.append(dec_element)
            
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
        
        # Process class decorators
        cls_decorators = class_data.get('decorators', [])
        for dec_element in self._process_decorators(class_element, cls_decorators):
            class_element.children.append(dec_element)
        
        # Process methods
        methods = class_data.get('methods', [])
        for method_data in methods:
            method_element = self._process_method_element(method_data, class_element.name)
            class_element.children.append(method_element)
            
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
            # Extract raw elements
            raw_elements = self._extract_file(code)
            result = CodeElementsResult()
            
            # Process imports
            for import_data in raw_elements.get('imports', []):
                import_element = self._process_import_element(import_data)
                result.elements.append(import_element)
            
            # Process functions
            for function_data in raw_elements.get('functions', []):
                function_element = self._process_function_element(function_data)
                result.elements.append(function_element)
            
            # Process classes
            for class_data in raw_elements.get('classes', []):
                class_element = self._process_class_element(class_data)
                result.elements.append(class_element)
            
            return result
        except Exception as e:
            logger.error(f'Error in extract_all: {str(e)}')
            return CodeElementsResult()