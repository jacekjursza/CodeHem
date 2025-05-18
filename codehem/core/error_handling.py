"""
Error handling utilities for CodeHem.

This module provides a comprehensive exception hierarchy and utilities
for error handling throughout the CodeHem codebase. It includes specialized
exception types for various error categories, context enrichment mechanisms,
and decorators for common error handling patterns.
"""
import functools
import logging
import traceback
from typing import Optional, Type, Any, Callable, Dict, List, Union, Tuple

logger = logging.getLogger('codehem')

class CodeHemError(Exception):
    """Base class for all CodeHem exceptions.
    
    All exceptions specific to CodeHem should inherit from this class to allow
    for consistent error handling and identification.
    """
    def __init__(self, message: str, **kwargs):
        self.message = message
        self.context = kwargs.get('context', {})
        
        # Capture any additional context information
        for key, value in kwargs.items():
            if key != 'context':
                self.context[key] = value
                
        super().__init__(message)
    
    def add_context(self, key: str, value: Any) -> None:
        """Add additional context information to the exception.
        
        Args:
            key: The context key
            value: The context value
        """
        self.context[key] = value
    
    def __str__(self) -> str:
        """Return a string representation of the exception.
        
        If context information is available, it will be included in the string.
        """
        if not self.context:
            return self.message
        
        context_str = ', '.join(f"{k}={v}" for k, v in self.context.items())
        return f"{self.message} [Context: {context_str}]"

# ===== Validation Errors =====

class ValidationError(CodeHemError):
    """Exception raised for input validation failures.
    
    This exception should be used when input parameters to functions or methods
    fail to meet required conditions.
    """
    def __init__(self, message: str, parameter: Optional[str] = None, 
                 value: Optional[Any] = None, expected: Optional[str] = None, **kwargs):
        super().__init__(message, parameter=parameter, value=value, expected=expected, **kwargs)
        self.parameter = parameter
        self.value = value
        self.expected = expected

class MissingParameterError(ValidationError):
    """Exception raised when a required parameter is missing."""
    def __init__(self, parameter: str, **kwargs):
        message = f"Required parameter '{parameter}' is missing"
        super().__init__(message, parameter=parameter, **kwargs)

class InvalidParameterError(ValidationError):
    """Exception raised when a parameter has an invalid value."""
    def __init__(self, parameter: str, value: Any, expected: str, **kwargs):
        message = f"Invalid value for parameter '{parameter}': {value}. Expected: {expected}"
        super().__init__(message, parameter=parameter, value=value, expected=expected, **kwargs)

class InvalidTypeError(ValidationError):
    """Exception raised when a parameter has an incorrect type."""
    def __init__(self, parameter: str, value: Any, expected_type: Union[Type, Tuple[Type, ...], str], **kwargs):
        if isinstance(expected_type, str):
            expected_type_str = expected_type
        elif isinstance(expected_type, tuple):
            expected_type_str = ', '.join(t.__name__ for t in expected_type)
        else:
            expected_type_str = expected_type.__name__
        message = f"Invalid type for parameter '{parameter}': {type(value).__name__}. Expected: {expected_type_str}"
        super().__init__(message, parameter=parameter, value=value, expected=expected_type_str, **kwargs)

# ===== Configuration Errors =====

class ConfigurationError(CodeHemError):
    """Exception raised for issues with configuration settings.
    
    This exception should be used when there are problems with the configuration
    of CodeHem or its components.
    """
    pass

class MissingConfigurationError(ConfigurationError):
    """Exception raised when a required configuration setting is missing."""
    def __init__(self, setting: str, **kwargs):
        message = f"Required configuration setting '{setting}' is missing"
        super().__init__(message, setting=setting, **kwargs)

class InvalidConfigurationError(ConfigurationError):
    """Exception raised when a configuration setting has an invalid value."""
    def __init__(self, setting: str, value: Any, reason: str, **kwargs):
        message = f"Invalid configuration setting '{setting}': {value}. Reason: {reason}"
        super().__init__(message, setting=setting, value=value, reason=reason, **kwargs)

# ===== Parsing Errors =====

class ParsingError(CodeHemError):
    """Exception raised for failures during code parsing.
    
    This exception should be used when there are issues parsing source code
    with tree-sitter or other parsing mechanisms.
    """
    def __init__(self, message: str, code_snippet: Optional[str] = None, 
                 position: Optional[Tuple[int, int]] = None, **kwargs):
        super().__init__(message, code_snippet=code_snippet, position=position, **kwargs)
        self.code_snippet = code_snippet
        self.position = position

class SyntaxError(ParsingError):
    """Exception raised for syntax errors in the source code being parsed."""
    def __init__(self, message: str, language: str, code_snippet: Optional[str] = None,
                 line: Optional[int] = None, column: Optional[int] = None, **kwargs):
        position = (line, column) if line is not None and column is not None else None
        super().__init__(
            message, code_snippet=code_snippet, position=position, 
            language=language, line=line, column=column, **kwargs
        )
        self.language = language
        self.line = line
        self.column = column

class QueryError(ParsingError):
    """Exception raised for errors in tree-sitter queries."""
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        super().__init__(message, query=query, **kwargs)
        self.query = query

# ===== AST Navigation Errors =====

class ASTNavigationError(CodeHemError):
    """Exception raised for problems navigating the abstract syntax tree.
    
    This exception should be used when there are issues traversing or
    manipulating the AST during code analysis.
    """
    pass

class NodeNotFoundError(ASTNavigationError):
    """Exception raised when a node is not found in the AST."""
    def __init__(self, node_type: str, query: Optional[str] = None, **kwargs):
        message = f"Node of type '{node_type}' not found"
        if query:
            message += f" with query: {query}"
        super().__init__(message, node_type=node_type, query=query, **kwargs)
        self.node_type = node_type
        self.query = query

class InvalidNodeTypeError(ASTNavigationError):
    """Exception raised when a node has an unexpected type."""
    def __init__(self, expected_type: str, actual_type: str, **kwargs):
        message = f"Invalid node type: '{actual_type}'. Expected: '{expected_type}'"
        super().__init__(message, expected_type=expected_type, actual_type=actual_type, **kwargs)
        self.expected_type = expected_type
        self.actual_type = actual_type

# ===== Extraction Errors =====

class ExtractionError(CodeHemError):
    """Exception raised for errors during code element extraction.
    
    This exception should be used when there are problems extracting code
    elements from source code.
    """
    pass

class ElementNotFoundError(ExtractionError):
    """Exception raised when an element is not found in the code."""
    def __init__(self, element_type: str, element_name: Optional[str] = None, 
                 parent_name: Optional[str] = None, **kwargs):
        message = f"Element of type '{element_type}' not found"
        if element_name:
            message += f": '{element_name}'"
        if parent_name:
            message += f" in parent '{parent_name}'"
        super().__init__(message, element_type=element_type, element_name=element_name, 
                         parent_name=parent_name, **kwargs)
        self.element_type = element_type
        self.element_name = element_name
        self.parent_name = parent_name

class ExtractorError(ExtractionError):
    """Exception raised for errors in specific extractors."""
    def __init__(self, extractor_type: str, message: str, **kwargs):
        full_message = f"Error in {extractor_type} extractor: {message}"
        super().__init__(full_message, extractor_type=extractor_type, **kwargs)
        self.extractor_type = extractor_type

class FunctionExtractorError(ExtractorError):
    """Exception raised for errors in function extractors."""
    def __init__(self, message: str, **kwargs):
        super().__init__("function", message, **kwargs)

class ClassExtractorError(ExtractorError):
    """Exception raised for errors in class extractors."""
    def __init__(self, message: str, **kwargs):
        super().__init__("class", message, **kwargs)

class MethodExtractorError(ExtractorError):
    """Exception raised for errors in method extractors."""
    def __init__(self, message: str, **kwargs):
        super().__init__("method", message, **kwargs)

class PropertyExtractorError(ExtractorError):
    """Exception raised for errors in property extractors."""
    def __init__(self, message: str, **kwargs):
        super().__init__("property", message, **kwargs)

class ImportExtractorError(ExtractorError):
    """Exception raised for errors in import extractors."""
    def __init__(self, message: str, **kwargs):
        super().__init__("import", message, **kwargs)

# ===== Manipulation Errors =====

class ManipulationError(CodeHemError):
    """Exception raised for errors during code manipulation.
    
    This exception should be used when there are problems manipulating
    code elements (adding, removing, modifying).
    """
    pass

class InvalidManipulationError(ManipulationError):
    """Exception raised when a manipulation operation is invalid."""
    def __init__(self, operation: str, reason: str, **kwargs):
        message = f"Invalid manipulation operation '{operation}': {reason}"
        super().__init__(message, operation=operation, reason=reason, **kwargs)
        self.operation = operation
        self.reason = reason

class ManipulatorError(ManipulationError):
    """Exception raised for errors in specific manipulators."""
    def __init__(self, manipulator_type: str, message: str, **kwargs):
        full_message = f"Error in {manipulator_type} manipulator: {message}"
        super().__init__(full_message, manipulator_type=manipulator_type, **kwargs)
        self.manipulator_type = manipulator_type

class AddElementError(ManipulationError):
    """Exception raised when adding an element fails."""
    def __init__(self, element_type: str, reason: str, **kwargs):
        message = f"Failed to add element of type '{element_type}': {reason}"
        super().__init__(message, element_type=element_type, reason=reason, **kwargs)
        self.element_type = element_type
        self.reason = reason

class RemoveElementError(ManipulationError):
    """Exception raised when removing an element fails."""
    def __init__(self, element_type: str, element_name: str, reason: str, **kwargs):
        message = f"Failed to remove element '{element_name}' of type '{element_type}': {reason}"
        super().__init__(message, element_type=element_type, element_name=element_name, 
                         reason=reason, **kwargs)
        self.element_type = element_type
        self.element_name = element_name
        self.reason = reason

class ReplaceElementError(ManipulationError):
    """Exception raised when replacing an element fails."""
    def __init__(self, element_type: str, element_name: str, reason: str, **kwargs):
        message = f"Failed to replace element '{element_name}' of type '{element_type}': {reason}"
        super().__init__(message, element_type=element_type, element_name=element_name, 
                         reason=reason, **kwargs)
        self.element_type = element_type
        self.element_name = element_name
        self.reason = reason

class WriteConflictError(ManipulationError):
    """Raised when apply_patch detects hash mismatch for the target fragment."""

    def __init__(self, expected_hash: str, actual_hash: str, **kwargs):
        message = (
            f"Write conflict: expected hash {expected_hash} but found {actual_hash}"
        )
        super().__init__(message, expected_hash=expected_hash, actual_hash=actual_hash, **kwargs)
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash

# ===== Post-Processing Errors =====

class PostProcessorError(CodeHemError):
    """Exception raised for issues during post-processing.
    
    This exception should be used when there are problems during the
    post-processing phase of code extraction.
    """
    def __init__(self, message: str, language: Optional[str] = None, **kwargs):
        super().__init__(message, language=language, **kwargs)
        self.language = language

class LanguagePostProcessorError(PostProcessorError):
    """Exception raised for errors in language-specific post-processors."""
    def __init__(self, language: str, message: str, **kwargs):
        full_message = f"Error in {language} post-processor: {message}"
        super().__init__(full_message, language=language, **kwargs)

# ===== Language Support Errors =====

class UnsupportedLanguageError(CodeHemError):
    """Exception raised when an operation is attempted with an unsupported language."""
    def __init__(self, language: str, operation: Optional[str] = None, **kwargs):
        message = f"Unsupported language: '{language}'"
        if operation:
            message += f" for operation: {operation}"
        super().__init__(message, language=language, operation=operation, **kwargs)
        self.language = language
        self.operation = operation

class LanguageDetectionError(CodeHemError):
    """Exception raised when language detection fails."""
    def __init__(self, message: str, code_snippet: Optional[str] = None, **kwargs):
        super().__init__(message, code_snippet=code_snippet, **kwargs)
        self.code_snippet = code_snippet

# ===== Plugin Errors =====

class PluginError(CodeHemError):
    """Exception raised for problems with plugins and their loading.
    
    This exception should be used when there are issues with plugin
    discovery, loading, initialization, or execution.
    """
    pass

class PluginLoadError(PluginError):
    """Exception raised when a plugin fails to load."""
    def __init__(self, plugin_name: str, reason: str, **kwargs):
        message = f"Failed to load plugin '{plugin_name}': {reason}"
        super().__init__(message, plugin_name=plugin_name, reason=reason, **kwargs)
        self.plugin_name = plugin_name
        self.reason = reason

class PluginInitializationError(PluginError):
    """Exception raised when a plugin fails to initialize."""
    def __init__(self, plugin_name: str, reason: str, **kwargs):
        message = f"Failed to initialize plugin '{plugin_name}': {reason}"
        super().__init__(message, plugin_name=plugin_name, reason=reason, **kwargs)
        self.plugin_name = plugin_name
        self.reason = reason

class PluginExecutionError(PluginError):
    """Exception raised when a plugin operation fails."""
    def __init__(self, plugin_name: str, operation: str, reason: str, **kwargs):
        message = f"Plugin '{plugin_name}' operation '{operation}' failed: {reason}"
        super().__init__(message, plugin_name=plugin_name, operation=operation, 
                         reason=reason, **kwargs)
        self.plugin_name = plugin_name
        self.operation = operation
        self.reason = reason

# ===== Utility Decorators and Functions =====

def handle_extraction_errors(func: Callable) -> Callable:
    """
    Decorator to handle extraction errors gracefully.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ExtractionError as e:
            logger.error(f"Extraction error: {str(e)}")
            # Return empty result instead of raising exception
            if func.__name__ == 'extract_all':
                from codehem.models.code_element import CodeElementsResult
                return CodeElementsResult(elements=[])
            elif func.__name__.startswith('extract_'):
                return []
            elif func.__name__ == 'find_by_xpath' or func.__name__ == 'find_element':
                return (0, 0)
            else:
                return None
        except UnsupportedLanguageError as e:
            logger.error(f"Unsupported language: {str(e)}")
            # Return empty result instead of raising exception
            if func.__name__.startswith('extract_'):
                return []
            elif func.__name__ == 'find_by_xpath' or func.__name__ == 'find_element':
                return (0, 0)
            else:
                return None
        except AttributeError as e:
            logger.error(f"Attribute error during {func.__name__}: {str(e)}")
            # Return empty result instead of raising exception
            if func.__name__.startswith('extract_'):
                return []
            elif func.__name__ == 'find_by_xpath' or func.__name__ == 'find_element':
                return (0, 0)
            else:
                return None
        except Exception as e:
            logger.exception(f"Unexpected error during {func.__name__}: {str(e)}")
            # Re-raise other exceptions
            raise
    
    return wrapper
