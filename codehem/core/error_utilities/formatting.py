"""
User-friendly error formatting utilities.

This module provides classes and functions for formatting exceptions
into user-friendly error messages with suggestions and severity levels.
"""
import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from codehem.core.error_handling import (
    CodeHemError, ValidationError, ConfigurationError, ParsingError,
    SyntaxError, QueryError, ASTNavigationError, NodeNotFoundError,
    ExtractionError, ElementNotFoundError, ManipulationError,
    InvalidManipulationError, UnsupportedLanguageError, LanguageDetectionError,
    MissingParameterError, InvalidParameterError, InvalidTypeError,
    MissingConfigurationError, InvalidConfigurationError
)

# Type variables
T = TypeVar('T')

# Get the logger for codehem
logger = logging.getLogger('codehem')


class ErrorSeverity:
    """
    Constants representing error severity levels.
    
    These can be used to classify errors according to their impact and
    communicate this to users in a consistent way.
    """
    INFO = 'info'          # Informational messages
    WARNING = 'warning'    # Issues that don't prevent the operation but may cause problems
    ERROR = 'error'        # Issues that prevent the operation from completing
    CRITICAL = 'critical'  # Serious issues that may affect system stability


class UserFriendlyError:
    """
    Container for user-friendly error information.
    
    This class formats errors into user-friendly messages with additional
    context like severity, suggestions, and troubleshooting information.
    """
    
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        severity: str = ErrorSeverity.ERROR,
        suggestions: Optional[List[str]] = None,
        details: Optional[str] = None,
        code: Optional[str] = None
    ):
        """
        Initialize a user-friendly error.
        
        Args:
            message: The main error message in user-friendly language
            original_error: The original exception that caused this error
            severity: The error severity (one of ErrorSeverity constants)
            suggestions: List of suggestions for fixing the error
            details: Technical details for developers
            code: Error code for reference
        """
        self.message = message
        self.original_error = original_error
        self.severity = severity
        self.suggestions = suggestions or []
        self.details = details
        self.code = code
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.message
    
    def format(self, include_details: bool = False) -> str:
        """
        Format the error as a human-readable string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted error string
        """
        lines = [f"{self.severity.upper()}: {self.message}"]
        
        if self.code:
            lines[0] = f"{lines[0]} [Code: {self.code}]"
        
        if self.suggestions:
            lines.append("\nSuggestions:")
            for suggestion in self.suggestions:
                lines.append(f"- {suggestion}")
        
        if include_details and self.details:
            lines.append("\nTechnical details:")
            lines.append(self.details)
        
        if include_details and self.original_error:
            lines.append("\nOriginal error:")
            error_type = type(self.original_error).__name__
            error_msg = str(self.original_error)
            lines.append(f"{error_type}: {error_msg}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error to a dictionary for API responses.
        
        Returns:
            A dictionary representation of the error
        """
        result = {
            'message': self.message,
            'severity': self.severity
        }
        
        if self.code:
            result['code'] = self.code
            
        if self.suggestions:
            result['suggestions'] = self.suggestions
            
        if self.details:
            result['details'] = self.details
        
        return result


class ErrorFormatter:
    """
    Utility class for formatting exceptions as user-friendly errors.
    
    This class provides methods for converting exceptions to UserFriendlyError
    objects with appropriate messages, suggestions, and context.
    """
    
    def __init__(self):
        """Initialize with default mappings and suggestion templates."""
        # Default error message templates for different exception types
        self._message_templates = {
            # Validation errors
            ValidationError: "Invalid input: {message}",
            MissingParameterError: "Missing required input: {parameter}",
            InvalidParameterError: "Invalid value for {parameter}: {value}",
            InvalidTypeError: "Invalid type for {parameter}: expected {expected}",
            
            # Configuration errors
            ConfigurationError: "Configuration error: {message}",
            MissingConfigurationError: "Missing configuration setting: {setting}",
            InvalidConfigurationError: "Invalid configuration: {message}",
            
            # Parsing and AST errors
            ParsingError: "Error parsing code: {message}",
            SyntaxError: "Syntax error in code: {message}",
            QueryError: "Invalid query: {message}",
            ASTNavigationError: "Error navigating code structure: {message}",
            NodeNotFoundError: "Could not find {node_type} in code",
            
            # Extraction errors
            ExtractionError: "Failed to extract code elements: {message}",
            ElementNotFoundError: "Could not find {element_type}{element_name_str} in code",
            
            # Manipulation errors
            ManipulationError: "Failed to modify code: {message}",
            InvalidManipulationError: "Invalid operation: {reason}",
            
            # Language errors
            UnsupportedLanguageError: "Language '{language}' is not supported{operation_str}",
            LanguageDetectionError: "Could not detect the programming language",
            
            # Generic errors
            Exception: "An unexpected error occurred: {message}",
            TimeoutError: "Operation timed out: {message}",
            ValueError: "Invalid value: {message}",
            TypeError: "Type error: {message}",
            KeyError: "Key not found: {message}",
            IndexError: "Index out of range: {message}",
            ImportError: "Failed to import module: {message}",
            FileNotFoundError: "File not found: {message}",
            PermissionError: "Permission denied: {message}"
        }
        
        # Default suggestion templates for different exception types
        self._suggestion_templates = {
            # Validation errors
            ValidationError: [
                "Check the input values and try again",
                "Ensure all required fields are provided"
            ],
            MissingParameterError: [
                "Provide a value for the '{parameter}' parameter"
            ],
            InvalidParameterError: [
                "Change the value for '{parameter}' to match the expected format"
            ],
            InvalidTypeError: [
                "Change the type of '{parameter}' to {expected}"
            ],
            
            # Configuration errors
            ConfigurationError: [
                "Check your configuration settings and try again"
            ],
            MissingConfigurationError: [
                "Add the '{setting}' setting to your configuration"
            ],
            InvalidConfigurationError: [
                "Fix the invalid configuration setting and try again"
            ],
            
            # Parsing and AST errors
            ParsingError: [
                "Check the syntax of your code",
                "Make sure the code is valid for the specified language"
            ],
            SyntaxError: [
                "Fix the syntax error in your code"
            ],
            QueryError: [
                "Check the format of your query"
            ],
            
            # Extraction errors
            ExtractionError: [
                "Verify that the code structure is valid",
                "Check if the element exists in the code"
            ],
            ElementNotFoundError: [
                "Verify that the element exists in the code",
                "Check the element name and type"
            ],
            
            # Manipulation errors
            ManipulationError: [
                "Check that the code structure is valid for the requested operation"
            ],
            
            # Language errors
            UnsupportedLanguageError: [
                "Use one of the supported languages: Python, JavaScript, TypeScript"
            ],
            
            # Generic errors
            TimeoutError: [
                "Try the operation again",
                "If the problem persists, increase the timeout value"
            ],
            FileNotFoundError: [
                "Check if the file exists and the path is correct"
            ],
            PermissionError: [
                "Check that you have the necessary permissions to access the file or resource"
            ]
        }
        
        # Default severity levels for different exception types
        self._severity_mapping = {
            # Critical errors affect system stability
            Exception: ErrorSeverity.ERROR,
            
            # Errors prevent the operation from completing
            ValidationError: ErrorSeverity.ERROR,
            ConfigurationError: ErrorSeverity.ERROR,
            ParsingError: ErrorSeverity.ERROR,
            ExtractionError: ErrorSeverity.ERROR,
            ManipulationError: ErrorSeverity.ERROR,
            UnsupportedLanguageError: ErrorSeverity.ERROR,
            TimeoutError: ErrorSeverity.ERROR,
            
            # Warnings don't prevent the operation but may cause problems
            LanguageDetectionError: ErrorSeverity.WARNING,
            
            # Informational errors are mostly for user awareness
            # (none defined by default)
        }
    
    def register_message_template(self, exception_type: Type[Exception], template: str) -> None:
        """
        Register a custom message template for an exception type.
        
        Args:
            exception_type: The exception type to match
            template: The message template to use
        """
        self._message_templates[exception_type] = template
    
    def register_suggestions(self, exception_type: Type[Exception], suggestions: List[str]) -> None:
        """
        Register custom suggestions for an exception type.
        
        Args:
            exception_type: The exception type to match
            suggestions: List of suggestion strings
        """
        self._suggestion_templates[exception_type] = suggestions
    
    def register_severity(self, exception_type: Type[Exception], severity: str) -> None:
        """
        Register a custom severity level for an exception type.
        
        Args:
            exception_type: The exception type to match
            severity: The severity level (use ErrorSeverity constants)
        """
        self._severity_mapping[exception_type] = severity
    
    def format_exception(
        self, 
        exception: Exception, 
        include_details: bool = False
    ) -> UserFriendlyError:
        """
        Format an exception as a user-friendly error.
        
        Args:
            exception: The exception to format
            include_details: Whether to include technical details
            
        Returns:
            A UserFriendlyError object
        """
        # Find the most specific message template
        template = self._get_template_for_exception(exception, self._message_templates)
        
        # Format the message
        message = self._format_message(template, exception)
        
        # Get suggestions
        suggestions = self._get_suggestions_for_exception(exception)
        
        # Get severity
        severity = self._get_severity_for_exception(exception)
        
        # Get details if requested
        details = None
        if include_details:
            details = self._get_details_for_exception(exception)
        
        # Create the user-friendly error
        return UserFriendlyError(
            message=message,
            original_error=exception,
            severity=severity,
            suggestions=suggestions,
            details=details
        )
    
    def format_exception_as_string(
        self, 
        exception: Exception, 
        include_details: bool = False
    ) -> str:
        """
        Format an exception as a user-friendly error string.
        
        Args:
            exception: The exception to format
            include_details: Whether to include technical details
            
        Returns:
            A formatted error string
        """
        error = self.format_exception(exception, include_details)
        return error.format(include_details)
    
    def format_exception_as_dict(
        self, 
        exception: Exception, 
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Format an exception as a dictionary for API responses.
        
        Args:
            exception: The exception to format
            include_details: Whether to include technical details
            
        Returns:
            A dictionary representation of the error
        """
        error = self.format_exception(exception, include_details)
        return error.to_dict()
    
    def _get_template_for_exception(
        self, 
        exception: Exception, 
        templates: Dict[Type[Exception], str]
    ) -> str:
        """
        Find the most specific template for an exception.
        
        Args:
            exception: The exception to match
            templates: Dictionary of exception types to templates
            
        Returns:
            The most specific template string
        """
        exception_type = type(exception)
        
        # Direct match
        if exception_type in templates:
            return templates[exception_type]
        
        # Check for match by inheritance
        for base_type, template in templates.items():
            if isinstance(exception, base_type):
                return template
        
        # Default template
        return "An error occurred: {message}"
    
    def _format_message(self, template: str, exception: Exception) -> str:
        """
        Format a message template with exception data.
        
        Args:
            template: The message template
            exception: The exception to format
            
        Returns:
            The formatted message
        """
        # Prepare format variables
        format_vars = {
            'message': str(exception),
            'type': type(exception).__name__
        }
        
        # Add all attributes of the exception as format variables
        for attr in dir(exception):
            if not attr.startswith('_') and not callable(getattr(exception, attr)):
                format_vars[attr] = getattr(exception, attr)
        
        # Special handling for some error types
        if isinstance(exception, ElementNotFoundError) and hasattr(exception, 'element_name'):
            # Format element name string
            element_name = getattr(exception, 'element_name')
            format_vars['element_name_str'] = f" '{element_name}'" if element_name else ""
        
        if isinstance(exception, UnsupportedLanguageError) and hasattr(exception, 'operation'):
            # Format operation string
            operation = getattr(exception, 'operation')
            format_vars['operation_str'] = f" for operation: {operation}" if operation else ""
        
        # Format the template
        try:
            return template.format(**format_vars)
        except (KeyError, AttributeError):
            # Fallback to simple message
            return f"{type(exception).__name__}: {str(exception)}"
    
    def _get_suggestions_for_exception(self, exception: Exception) -> List[str]:
        """
        Get suggestions for fixing an exception.
        
        Args:
            exception: The exception to match
            
        Returns:
            List of suggestion strings
        """
        # Find the most specific suggestions
        suggestion_templates = []
        exception_type = type(exception)
        
        # Direct match
        if exception_type in self._suggestion_templates:
            suggestion_templates = self._suggestion_templates[exception_type]
        else:
            # Check for match by inheritance
            for base_type, templates in self._suggestion_templates.items():
                if isinstance(exception, base_type):
                    suggestion_templates = templates
                    break
        
        if not suggestion_templates:
            return []
        
        # Process each suggestion template
        result = []
        for suggestion in suggestion_templates:
            try:
                # Format with exception attributes
                format_vars = {
                    attr: getattr(exception, attr) 
                    for attr in dir(exception) 
                    if not attr.startswith('_') and not callable(getattr(exception, attr))
                }
                
                # Add the message for formatting
                format_vars['message'] = str(exception)
                
                result.append(suggestion.format(**format_vars))
            except (KeyError, AttributeError):
                # If formatting fails, use the raw suggestion
                result.append(suggestion)
        
        return result
    
    def _get_severity_for_exception(self, exception: Exception) -> str:
        """
        Get the severity level for an exception.
        
        Args:
            exception: The exception to match
            
        Returns:
            A severity level string
        """
        exception_type = type(exception)
        
        # Direct match
        if exception_type in self._severity_mapping:
            return self._severity_mapping[exception_type]
        
        # Check for match by inheritance
        for base_type, severity in self._severity_mapping.items():
            if isinstance(exception, base_type):
                return severity
        
        # Default severity
        return ErrorSeverity.ERROR
    
    def _get_details_for_exception(self, exception: Exception) -> str:
        """
        Get technical details for an exception.
        
        Args:
            exception: The exception to get details for
            
        Returns:
            A formatted string with technical details
        """
        details = []
        
        # Add exception type and message
        details.append(f"Exception type: {type(exception).__name__}")
        details.append(f"Message: {str(exception)}")
        
        # Add relevant attributes
        attributes = []
        for attr in dir(exception):
            if not attr.startswith('_') and not callable(getattr(exception, attr)):
                value = getattr(exception, attr)
                if value is not None and attr != 'args':
                    attributes.append(f"{attr}: {value}")
        
        if attributes:
            details.append("Attributes:")
            details.extend([f"  {attr}" for attr in attributes])
        
        # Add context for CodeHemError
        if isinstance(exception, CodeHemError) and hasattr(exception, 'context'):
            context_items = [f"{k}: {v}" for k, v in exception.context.items()]
            if context_items:
                details.append("Context:")
                details.extend([f"  {item}" for item in context_items])
        
        # Join all details
        return "\n".join(details)


# Create a global instance of ErrorFormatter
error_formatter = ErrorFormatter()


def format_user_friendly_error(
    exception: Exception, 
    include_details: bool = False
) -> UserFriendlyError:
    """
    Format an exception as a user-friendly error.
    
    This is a convenience function for using the global error formatter.
    
    Args:
        exception: The exception to format
        include_details: Whether to include technical details
        
    Returns:
        A UserFriendlyError object
        
    Example:
        ```python
        try:
            # Some operation that might fail
        except Exception as e:
            error = format_user_friendly_error(e)
            print(error.format())
        ```
    """
    return error_formatter.format_exception(exception, include_details)


def format_error_message(
    exception: Exception, 
    include_details: bool = False
) -> str:
    """
    Format an exception as a user-friendly error message string.
    
    This is a convenience function for using the global error formatter.
    
    Args:
        exception: The exception to format
        include_details: Whether to include technical details
        
    Returns:
        A formatted error string
        
    Example:
        ```python
        try:
            # Some operation that might fail
        except Exception as e:
            error_msg = format_error_message(e)
            print(error_msg)
        ```
    """
    return error_formatter.format_exception_as_string(exception, include_details)


def format_error_for_api(
    exception: Exception, 
    include_details: bool = False
) -> Dict[str, Any]:
    """
    Format an exception as a dictionary for API responses.
    
    This is a convenience function for using the global error formatter.
    
    Args:
        exception: The exception to format
        include_details: Whether to include technical details
        
    Returns:
        A dictionary representation of the error
        
    Example:
        ```python
        try:
            # Some operation that might fail
        except Exception as e:
            error_dict = format_error_for_api(e)
            return jsonify({"error": error_dict})
        ```
    """
    return error_formatter.format_exception_as_dict(exception, include_details)


def with_friendly_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to catch and format exceptions as user-friendly errors.
    
    This decorator catches exceptions, formats them using the global error
    formatter, and re-raises them as UserFriendlyError objects.
    
    Args:
        func: The function to wrap
        
    Returns:
        A decorated function that formats errors
        
    Example:
        ```python
        @with_friendly_errors
        def process_data(data):
            # Implementation...
        ```
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Format the exception
            friendly_error = format_user_friendly_error(e)
            
            # Raise a new exception with the formatted error
            raise RuntimeError(friendly_error.format()) from e
    
    return wrapper
