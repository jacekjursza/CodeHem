"""
Base interfaces for language implementations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from codehem import CodeElementType
from codehem.extractor import Extractor
from codehem.models import CodeRange
from codehem.models.code_element import CodeElementsResult, CodeElement
from codehem.core.registry import registry
import logging

logger = logging.getLogger(__name__)

class LanguageService(ABC):
    """
    Base class for language-specific services.
    Defines the interface for language-specific operations and combines finder, formatter, and manipulator.
    """

    @property
    @abstractmethod
    def language_code(self) -> str:
        """Get the language code (e.g., 'python', 'typescript')."""
        pass

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Get file extensions supported by this language."""
        pass

    @property
    @abstractmethod
    def supported_element_types(self) -> List[str]:
        """Get element types supported by this language."""
        pass

    @abstractmethod
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of element in the code.

        Args:
            code: Code to analyze

        Returns:
            Element type string
        """
        pass

    def extract(self, code: str) -> CodeElementsResult:
        """Extract code elements from source code."""
        logger.debug(f"Starting extraction for {self.language_code}")
        result = self._extract_common_elements(code)
        logger.debug(f"Completed extraction with {len(result.elements)} elements")
        return result

    def extract_language_specific(self, code: str, current_result: CodeElementsResult) -> CodeElementsResult:
        return current_result

    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add or replace a code element.

        Args:
            original_code: Original source code
            element_type: Type of element to add/replace
            name: Name of the element
            new_code: New content for the element
            parent_name: Name of parent element (e.g., class name for methods)

        Returns:
            Modified code
        """
        handler = None
        handlers = registry.get_handlers(self.language_code)
        for h in handlers:
            if h.element_type.value == element_type:
                handler = h
                break
        if handler:
            return handler.upsert_element(original_code, name, new_code, parent_name)
        return original_code

    def resolve_xpath(self, xpath: str) -> Tuple[str, Optional[str]]:
        """Resolve an XPath expression to element name and parent name."""
        parts = xpath.split('.')
        if len(parts) == 1:
            return (parts[0], None)
        return (parts[-1], parts[-2])

    def _convert_to_code_element(self, raw_element: dict) -> CodeElement:
        """Convert raw extractor output to CodeElement."""
        return CodeElement.from_dict(raw_element)

    def _extract_and_attach_parameters(self, element, function_data, extractor) -> None:
        """
        Extract parameters and attach them as children to the function or method element.

        Args:
        element: CodeElement to attach parameters to
        function_data: Raw function data from the extractor
        extractor: Extractor instance to use
        """
        if element.type not in [CodeElementType.FUNCTION, CodeElementType.METHOD]:
            return

        # Check if parameters data exists
        parameters = function_data.get("parameters", [])
        if not parameters:
            return

        # Convert each parameter to a CodeElement and attach it
        for param in parameters:
            param_name = param.get("name")
            param_type = param.get("type")

            param_element = CodeElement(
                type=CodeElementType.PARAMETER,
                name=param_name,
                content=param_name,
                parent_name=element.name
                if element.type == CodeElementType.FUNCTION
                else f"{element.parent_name}.{element.name}",
                value_type=param_type,
                additional_data={
                    "optional": param.get("optional", False),
                    "default": param.get("default"),
                },
            )
            element.children.append(param_element)

    def _extract_and_attach_return_value(
        self, element, function_data, extractor
    ) -> None:
        """
        Extract return value info and attach it as a child to the function or method element.

        Args:
        element: CodeElement to attach return value to
        function_data: Raw function data from the extractor
        extractor: Extractor instance to use
        """
        if element.type not in [CodeElementType.FUNCTION, CodeElementType.METHOD]:
            return

        # Check if return_info data exists
        return_info = function_data.get("return_info", {})
        if not return_info:
            return

        return_type = return_info.get("return_type")
        return_values = return_info.get("return_values", [])

        if not return_type and not return_values:
            return

        return_element = CodeElement(
            type=CodeElementType.RETURN_VALUE,
            name=f"{element.name}_return",
            content=return_type if return_type else "",
            parent_name=element.name
            if element.type == CodeElementType.FUNCTION
            else f"{element.parent_name}.{element.name}",
            value_type=return_type,
            additional_data={"values": return_values},
        )
        element.children.append(return_element)

    def _extract_common_elements(self, code: str) -> CodeElementsResult:
        """
        Base implementation for extract() that language services can call.
        This is a helper method that implements common extraction behavior.

        Args:
            code: Source code as string

        Returns:
            CodeElementsResult containing extracted elements
        """
        try:
            extractor = Extractor(self.language_code)
            raw_elements = extractor.extract_all(code)
            result = CodeElementsResult()
            
            # Process imports
            for imp in raw_elements.get('imports', []):
                logger.debug(f"Processing import: {imp.get('name')}")
                result.elements.append(CodeElement.from_dict(imp))
            
            # Process functions
            for func in raw_elements.get('functions', []):
                logger.debug(f"Processing function: {func.get('name')}")
                func_element = CodeElement.from_dict(func)
                
                # Add parameters as children
                parameters = func.get('parameters', [])
                for param in parameters:
                    param_name = param.get('name')
                    param_type = param.get('type')
                    if param_name:
                        param_element = CodeElement(
                            type=CodeElementType.PARAMETER,
                            name=param_name,
                            content=param_name,
                            parent_name=func_element.name,
                            value_type=param_type,
                            additional_data={
                                'optional': param.get('optional', False),
                                'default': param.get('default')
                            }
                        )
                        func_element.children.append(param_element)
                
                # Add return value as child
                return_info = func.get('return_info', {})
                return_type = return_info.get('return_type')
                return_values = return_info.get('return_values', [])
                if return_type or return_values:
                    return_element = CodeElement(
                        type=CodeElementType.RETURN_VALUE,
                        name=f"{func_element.name}_return",
                        content=return_type if return_type else "",
                        parent_name=func_element.name,
                        value_type=return_type,
                        additional_data={'values': return_values}
                    )
                    func_element.children.append(return_element)
                
                # Add decorators as children
                decorators = func.get('decorators', [])
                for dec in decorators:
                    dec_name = dec.get('name')
                    dec_content = dec.get('content')
                    if dec_name:
                        dec_element = CodeElement(
                            type=CodeElementType.DECORATOR,
                            name=dec_name,
                            content=dec_content,
                            parent_name=func_element.name
                        )
                        func_element.children.append(dec_element)
                
                result.elements.append(func_element)
            
            # Process classes
            for cls in raw_elements.get('classes', []):
                logger.debug(f"Processing class: {cls.get('name')}")
                class_element = self._convert_to_code_element(cls)
                
                # Add decorators as children
                cls_decorators = cls.get('decorators', [])
                for dec in cls_decorators:
                    dec_name = dec.get('name')
                    dec_content = dec.get('content')
                    if dec_name:
                        dec_element = CodeElement(
                            type=CodeElementType.DECORATOR,
                            name=dec_name,
                            content=dec_content,
                            parent_name=class_element.name
                        )
                        class_element.children.append(dec_element)
                
                # Process methods
                methods = cls.get('methods', [])
                for method in methods:
                    logger.debug(f"Processing method: {method.get('name')} in class {cls.get('name')}")
                    method_element = self._convert_to_code_element(method)
                    method_element.parent_name = class_element.name
                    
                    # Add parameters as children
                    parameters = method.get('parameters', [])
                    for param in parameters:
                        param_name = param.get('name')
                        param_type = param.get('type')
                        if param_name:
                            param_element = CodeElement(
                                type=CodeElementType.PARAMETER,
                                name=param_name,
                                content=param_name,
                                parent_name=f"{class_element.name}.{method_element.name}",
                                value_type=param_type,
                                additional_data={
                                    'optional': param.get('optional', False),
                                    'default': param.get('default')
                                }
                            )
                            method_element.children.append(param_element)
                    
                    # Add return value as child
                    return_info = method.get('return_info', {})
                    return_type = return_info.get('return_type')
                    return_values = return_info.get('return_values', [])
                    if return_type or return_values:
                        return_element = CodeElement(
                            type=CodeElementType.RETURN_VALUE,
                            name=f"{method_element.name}_return",
                            content=return_type if return_type else "",
                            parent_name=f"{class_element.name}.{method_element.name}",
                            value_type=return_type,
                            additional_data={'values': return_values}
                        )
                        method_element.children.append(return_element)
                    
                    # Add decorators as children
                    method_decorators = method.get('decorators', [])
                    for dec in method_decorators:
                        dec_name = dec.get('name')
                        dec_content = dec.get('content')
                        if dec_name:
                            dec_element = CodeElement(
                                type=CodeElementType.DECORATOR,
                                name=dec_name,
                                content=dec_content,
                                parent_name=f"{class_element.name}.{method_element.name}"
                            )
                            method_element.children.append(dec_element)
                    
                    class_element.children.append(method_element)
                
                result.elements.append(class_element)
            
            return result
        except Exception as e:
            logger.error(f"Error in _base_extract: {str(e)}")
            return CodeElementsResult()