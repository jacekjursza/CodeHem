"""
Error handling utilities for CodeHem.

This module provides advanced error handling utilities that complement
the existing error handling system, including retry mechanisms, standardized
error logging, graceful degradation patterns, and more.
"""
import functools
import logging
import random
import re
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, Tuple, Pattern

from codehem.core.error_handling import CodeHemError
from codehem.core.error_context import error_context, ErrorContext, format_error_with_context

# Type variables
T = TypeVar('T')
R = TypeVar('R')

# Constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_WAIT = 1.0
DEFAULT_MAX_WAIT = 60.0
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_JITTER = 0.1

# Get the logger for codehem
logger = logging.getLogger('codehem')

# ===== Retry Mechanisms =====

def linear_backoff(attempt: int, initial_wait: float = 1.0, increment: float = 1.0) -> float:
    """
    Linear backoff strategy.
    
    Increases wait time linearly: initial_wait, initial_wait + increment, ...
    
    Args:
        attempt: The current attempt number (starting from 1)
        initial_wait: Initial wait time in seconds
        increment: Increment amount for each subsequent attempt
        
    Returns:
        The wait time in seconds
    """
    return initial_wait + (attempt - 1) * increment


def exponential_backoff(
    attempt: int, 
    initial_wait: float = 1.0, 
    factor: float = 2.0, 
    max_wait: float = DEFAULT_MAX_WAIT
) -> float:
    """
    Exponential backoff strategy.
    
    Increases wait time exponentially: initial_wait, initial_wait * factor, ...
    
    Args:
        attempt: The current attempt number (starting from 1)
        initial_wait: Initial wait time in seconds
        factor: Multiplication factor for each subsequent attempt
        max_wait: Maximum wait time in seconds
        
    Returns:
        The wait time in seconds, capped at max_wait
    """
    wait_time = initial_wait * (factor ** (attempt - 1))
    return min(wait_time, max_wait)


def jittered_backoff(
    attempt: int, 
    initial_wait: float = 1.0, 
    factor: float = 2.0, 
    max_wait: float = DEFAULT_MAX_WAIT, 
    jitter: float = DEFAULT_JITTER
) -> float:
    """
    Jittered exponential backoff strategy.
    
    Similar to exponential backoff but adds randomness to avoid thundering herd.
    
    Args:
        attempt: The current attempt number (starting from 1)
        initial_wait: Initial wait time in seconds
        factor: Multiplication factor for each subsequent attempt
        max_wait: Maximum wait time in seconds
        jitter: Maximum fraction to randomly adjust wait time by
        
    Returns:
        The wait time in seconds with jitter applied
    """
    wait_time = exponential_backoff(attempt, initial_wait, factor, max_wait)
    # Apply jitter: wait_time * random value between (1-jitter) and (1+jitter)
    jitter_multiplier = 1.0 + jitter * (2 * random.random() - 1)
    return wait_time * jitter_multiplier


def retry(max_attempts: int = DEFAULT_MAX_RETRIES, 
         exceptions: Tuple[Type[Exception], ...] = (Exception,), 
         logger: Optional[logging.Logger] = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying a function if it raises specified exceptions.
    
    This is a simple retry decorator that does not implement backoff. For more
    advanced retry behavior, use retry_with_backoff() or can_retry().
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        exceptions: Tuple of exception classes that should trigger a retry
        logger: Logger instance for logging retries
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
        def fetch_data(url):
            # Implementation...
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 1
            last_exception = None
            
            while attempt <= max_attempts:
                try:
                    with error_context("retry", 
                                      operation=func.__name__, 
                                      attempt=attempt, 
                                      max_attempts=max_attempts):
                        return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if logger:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {str(e)}"
                        )
                    
                    attempt += 1
                    
                    # If this was the last attempt, don't log about retrying
                    if attempt <= max_attempts:
                        if logger:
                            logger.info(f"Retrying {func.__name__} (attempt {attempt}/{max_attempts})...")
            
            # If we get here, all attempts failed
            if logger:
                logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            
            # Re-raise the last exception
            raise last_exception
        
        return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)
    
    return decorator


# ===== User-Friendly Error Formatting =====

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
        suggestions = self._get_template_for_exception(
            exception, self._suggestion_templates
        )
        
        if not suggestions:
            return []
        
        # Process each suggestion template
        result = []
        for suggestion in suggestions:
            try:
                # Format with exception attributes
                format_vars = {attr: getattr(exception, attr) 
                           for attr in dir(exception) 
                           if not attr.startswith('_') and not callable(getattr(exception, attr))}
                
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


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)


def retry_with_backoff(
    max_attempts: int = DEFAULT_MAX_RETRIES, 
    exceptions: Tuple[Type[Exception], ...] = (Exception,), 
    backoff_strategy: Callable = exponential_backoff,
    initial_wait: float = DEFAULT_INITIAL_WAIT,
    factor: float = DEFAULT_BACKOFF_FACTOR,
    max_wait: float = DEFAULT_MAX_WAIT,
    jitter: float = DEFAULT_JITTER,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying a function with backoff if it raises specified exceptions.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        exceptions: Tuple of exception classes that should trigger a retry
        backoff_strategy: Function to calculate wait time between retries
        initial_wait: Initial wait time in seconds (default: 1.0)
        factor: Multiplication factor for backoff strategies that use it (default: 2.0)
        max_wait: Maximum wait time in seconds (default: 60.0)
        jitter: Maximum fraction to randomly adjust wait time by (default: 0.1)
        logger: Logger instance for logging retries
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @retry_with_backoff(
            max_attempts=5, 
            exceptions=(ConnectionError, TimeoutError),
            backoff_strategy=jittered_backoff
        )
        def fetch_data(url):
            # Implementation...
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 1
            last_exception = None
            
            while attempt <= max_attempts:
                try:
                    with error_context("retry", 
                                      operation=func.__name__, 
                                      attempt=attempt, 
                                      max_attempts=max_attempts):
                        return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        # Calculate wait time
                        if backoff_strategy == linear_backoff:
                            wait_time = backoff_strategy(attempt, initial_wait, factor)
                        elif backoff_strategy == jittered_backoff:
                            wait_time = backoff_strategy(attempt, initial_wait, factor, max_wait, jitter)
                        else:  # exponential_backoff or custom
                            wait_time = backoff_strategy(attempt, initial_wait, factor, max_wait)
                        
                        if logger:
                            logger.warning(
                                f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                                f"Retrying in {wait_time:.2f} seconds."
                            )
                        
                        # Wait before the next attempt
                        time.sleep(wait_time)
                    else:
                        # This was the last attempt
                        if logger:
                            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
                    
                    attempt += 1
            
            # If we get here, all attempts failed
            # Re-raise the last exception
            raise last_exception
        
        return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)
    
    return decorator


# ===== User-Friendly Error Formatting =====

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
        suggestions = self._get_template_for_exception(
            exception, self._suggestion_templates
        )
        
        if not suggestions:
            return []
        
        # Process each suggestion template
        result = []
        for suggestion in suggestions:
            try:
                # Format with exception attributes
                format_vars = {attr: getattr(exception, attr) 
                           for attr in dir(exception) 
                           if not attr.startswith('_') and not callable(getattr(exception, attr))}
                
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


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)


def retry_exponential(
    max_attempts: int = DEFAULT_MAX_RETRIES, 
    exceptions: Tuple[Type[Exception], ...] = (Exception,), 
    initial_wait: float = DEFAULT_INITIAL_WAIT, 
    factor: float = DEFAULT_BACKOFF_FACTOR, 
    max_wait: float = DEFAULT_MAX_WAIT, 
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying a function with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        exceptions: Tuple of exception classes that should trigger a retry
        initial_wait: Initial wait time in seconds (default: 1.0)
        factor: Multiplication factor for each subsequent attempt (default: 2.0)
        max_wait: Maximum wait time in seconds (default: 60.0)
        logger: Logger instance for logging retries
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @retry_exponential(max_attempts=5, exceptions=(ConnectionError, TimeoutError))
        def fetch_data(url):
            # Implementation...
        ```
    """
    return retry_with_backoff(
        max_attempts=max_attempts,
        exceptions=exceptions,
        backoff_strategy=exponential_backoff,
        initial_wait=initial_wait,
        factor=factor,
        max_wait=max_wait,
        logger=logger
    )


def retry_jittered(
    max_attempts: int = DEFAULT_MAX_RETRIES, 
    exceptions: Tuple[Type[Exception], ...] = (Exception,), 
    initial_wait: float = DEFAULT_INITIAL_WAIT, 
    factor: float = DEFAULT_BACKOFF_FACTOR, 
    max_wait: float = DEFAULT_MAX_WAIT, 
    jitter: float = DEFAULT_JITTER, 
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying a function with jittered exponential backoff.
    
    This is recommended for scenarios where many concurrent actors might retry 
    the same operation, as it helps avoid the "thundering herd" problem.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        exceptions: Tuple of exception classes that should trigger a retry
        initial_wait: Initial wait time in seconds (default: 1.0)
        factor: Multiplication factor for each subsequent attempt (default: 2.0)
        max_wait: Maximum wait time in seconds (default: 60.0)
        jitter: Maximum fraction to randomly adjust wait time by (default: 0.1)
        logger: Logger instance for logging retries
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @retry_jittered(max_attempts=5, exceptions=(ConnectionError, TimeoutError))
        def fetch_data(url):
            # Implementation...
        ```
    """
    return retry_with_backoff(
        max_attempts=max_attempts,
        exceptions=exceptions,
        backoff_strategy=jittered_backoff,
        initial_wait=initial_wait,
        factor=factor,
        max_wait=max_wait,
        jitter=jitter,
        logger=logger
    )


# Conditional retry functions

def retry_if_exception_type(*exception_types: Type[Exception]) -> Callable[[Exception], bool]:
    """
    Return a function that returns True if the exception is of one of the given types.
    
    Args:
        *exception_types: Exception types to retry on
        
    Returns:
        A function that takes an exception and returns a boolean
        
    Example:
        ```python
        @can_retry(retry_on_exception=retry_if_exception_type(ConnectionError, TimeoutError))
        def fetch_data(url):
            # Implementation...
        ```
    """
    def _retry_if_exception_type(exception: Exception) -> bool:
        return isinstance(exception, exception_types)
    
    return _retry_if_exception_type


def retry_if_exception_message(message_pattern: Union[str, Pattern]) -> Callable[[Exception], bool]:
    """
    Return a function that returns True if the exception message matches a pattern.
    
    Args:
        message_pattern: String or regex pattern to match in the exception message
        
    Returns:
        A function that takes an exception and returns a boolean
        
    Example:
        ```python
        @can_retry(retry_on_exception=retry_if_exception_message("connection reset"))
        def fetch_data(url):
            # Implementation...
        ```
    """
    if isinstance(message_pattern, str):
        pattern = re.compile(re.escape(message_pattern))
    else:
        pattern = message_pattern
    
    def _retry_if_exception_message(exception: Exception) -> bool:
        return bool(pattern.search(str(exception)))
    
    return _retry_if_exception_message


def retry_if_result_none(result: Any) -> bool:
    """
    Return True if the result is None.
    
    This can be used with can_retry to retry if a function returns None.
    
    Args:
        result: The result to check
        
    Returns:
        True if the result is None, False otherwise
        
    Example:
        ```python
        @can_retry(retry_on_result=retry_if_result_none)
        def fetch_data(url):
            # Implementation...
        ```
    """
    return result is None


def retry_if_falsy_result(result: Any) -> bool:
    """
    Return True if the result is falsy (None, False, empty string, etc.).
    
    This can be used with can_retry to retry if a function returns a falsy value.
    
    Args:
        result: The result to check
        
    Returns:
        True if the result is falsy, False otherwise
        
    Example:
        ```python
        @can_retry(retry_on_result=retry_if_falsy_result)
        def fetch_data(url):
            # Implementation...
        ```
    """
    return not bool(result)


def can_retry(
    func: Optional[Callable[..., T]] = None,
    retry_on_exception: Optional[Callable[[Exception], bool]] = None,
    retry_on_result: Optional[Callable[[Any], bool]] = None,
    max_attempts: int = DEFAULT_MAX_RETRIES,
    wait_strategy: Callable = exponential_backoff,
    initial_wait: float = DEFAULT_INITIAL_WAIT,
    factor: float = DEFAULT_BACKOFF_FACTOR,
    max_wait: float = DEFAULT_MAX_WAIT,
    jitter: float = DEFAULT_JITTER,
    logger: Optional[logging.Logger] = None
) -> Union[Callable[[Callable[..., T]], Callable[..., T]], Callable[..., T]]:
    """
    Advanced retry decorator with extensive customization options.
    
    This decorator allows for conditional retries based on both exceptions and
    function results, with customizable wait strategies.
    
    Args:
        func: The function to wrap (used when decorator is applied without arguments)
        retry_on_exception: Function that takes an exception and returns True if retry should occur
        retry_on_result: Function that takes a result and returns True if retry should occur
        max_attempts: Maximum number of attempts (default: 3)
        wait_strategy: Function to calculate wait time between retries
        initial_wait: Initial wait time in seconds (default: 1.0)
        factor: Multiplication factor for backoff strategies that use it (default: 2.0)
        max_wait: Maximum wait time in seconds (default: 60.0)
        jitter: Maximum fraction to randomly adjust wait time by (default: 0.1)
        logger: Logger instance for logging retries
        
    Returns:
        A decorator function or a wrapped function if func is provided
        
    Example:
        ```python
        @can_retry(
            retry_on_exception=retry_if_exception_type(ConnectionError),
            retry_on_result=retry_if_result_none,
            wait_strategy=jittered_backoff
        )
        def fetch_data(url):
            # Implementation...
        ```
    """
    # Default retry predicates
    if retry_on_exception is None:
        retry_on_exception = retry_if_exception_type(Exception)
    
    if retry_on_result is None:
        retry_on_result = lambda result: False
    
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 1
            last_exception = None
            result = None
            
            while attempt <= max_attempts:
                try:
                    with error_context("retry", 
                                      operation=f.__name__, 
                                      attempt=attempt, 
                                      max_attempts=max_attempts):
                        result = f(*args, **kwargs)
                    
                    # Check if we need to retry based on the result
                    if retry_on_result(result):
                        if logger:
                            logger.warning(
                                f"Attempt {attempt}/{max_attempts} returned retry-triggering result for {f.__name__}"
                            )
                        
                        if attempt < max_attempts:
                            # Calculate wait time
                            if wait_strategy == linear_backoff:
                                wait_time = wait_strategy(attempt, initial_wait, factor)
                            elif wait_strategy == jittered_backoff:
                                wait_time = wait_strategy(
                                    attempt, initial_wait, factor, max_wait, jitter
                                )
                            else:  # exponential_backoff or custom
                                wait_time = wait_strategy(
                                    attempt, initial_wait, factor, max_wait
                                )
                            
                            if logger:
                                logger.warning(f"Retrying {f.__name__} in {wait_time:.2f} seconds...")
                            
                            # Wait before the next attempt
                            time.sleep(wait_time)
                            attempt += 1
                            continue
                    
                    # If we get here, the result doesn't trigger a retry
                    return result
                
                except Exception as e:
                    last_exception = e
                    
                    # Check if we need to retry based on the exception
                    if retry_on_exception(e):
                        if attempt < max_attempts:
                            # Calculate wait time
                            if wait_strategy == linear_backoff:
                                wait_time = wait_strategy(attempt, initial_wait, factor)
                            elif wait_strategy == jittered_backoff:
                                wait_time = wait_strategy(
                                    attempt, initial_wait, factor, max_wait, jitter
                                )
                            else:  # exponential_backoff or custom
                                wait_time = wait_strategy(
                                    attempt, initial_wait, factor, max_wait
                                )
                            
                            if logger:
                                logger.warning(
                                    f"Attempt {attempt}/{max_attempts} failed for {f.__name__}: {str(e)}. "
                                    f"Retrying in {wait_time:.2f} seconds."
                                )
                            
                            # Wait before the next attempt
                            time.sleep(wait_time)
                            attempt += 1
                            continue
                    
                    # If we get here, the exception doesn't trigger a retry
                    raise
            
            # If we get here, all attempts failed
            if logger:
                logger.error(f"All {max_attempts} attempts failed for {f.__name__}")
            
            # Re-raise the last exception if there was one
            if last_exception:
                raise last_exception
                
            # Otherwise, return the last result (which must have triggered retry_on_result)
            return result
        
        return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)
    
    # Handle using the decorator without arguments
    if func is not None:
        return decorator


# ===== User-Friendly Error Formatting =====

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
        suggestions = self._get_template_for_exception(
            exception, self._suggestion_templates
        )
        
        if not suggestions:
            return []
        
        # Process each suggestion template
        result = []
        for suggestion in suggestions:
            try:
                # Format with exception attributes
                format_vars = {attr: getattr(exception, attr) 
                           for attr in dir(exception) 
                           if not attr.startswith('_') and not callable(getattr(exception, attr))}
                
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


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)(func)
    
    return decorator


# ===== User-Friendly Error Formatting =====

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
        suggestions = self._get_template_for_exception(
            exception, self._suggestion_templates
        )
        
        if not suggestions:
            return []
        
        # Process each suggestion template
        result = []
        for suggestion in suggestions:
            try:
                # Format with exception attributes
                format_vars = {attr: getattr(exception, attr) 
                           for attr in dir(exception) 
                           if not attr.startswith('_') and not callable(getattr(exception, attr))}
                
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


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)


def with_timeout(
    timeout_seconds: float, 
    timeout_exception: Type[Exception] = TimeoutError
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to apply a timeout to a function.
    
    This decorator will raise a TimeoutError (or other specified exception)
    if the decorated function takes longer than the specified timeout to run.
    
    Note: This implementation depends on the signal module, which means:
    1. It only works on Unix-based systems (Linux, macOS)
    2. It only works in the main thread
    
    For more robust timeout handling, consider using concurrent.futures 
    or the timeout utilities from a library like tenacity.
    
    Args:
        timeout_seconds: Number of seconds before timeout
        timeout_exception: Exception class to raise on timeout
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @with_timeout(5.0)  # 5 second timeout
        def slow_operation():
            # Implementation...
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import signal
            
            def timeout_handler(signum, frame):
                raise timeout_exception(f"Function '{func.__name__}' timed out after {timeout_seconds} seconds")
            
            # Set the timeout handler
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            # Set the alarm
            signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
            
            try:
                # Call the function
                return func(*args, **kwargs)
            finally:
                # Reset the alarm and handler
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_handler)
        
        return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)
    
    return decorator


# ===== User-Friendly Error Formatting =====

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
        suggestions = self._get_template_for_exception(
            exception, self._suggestion_templates
        )
        
        if not suggestions:
            return []
        
        # Process each suggestion template
        result = []
        for suggestion in suggestions:
            try:
                # Format with exception attributes
                format_vars = {attr: getattr(exception, attr) 
                           for attr in dir(exception) 
                           if not attr.startswith('_') and not callable(getattr(exception, attr))}
                
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


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)


# ===== Error Logging =====

class ErrorLogFormatter:
    """
    Formatter for error logs that provides consistent formatting across the codebase.
    
    This class provides methods for formatting error messages with various levels
    of detail and context, suitable for different logging levels and scenarios.
    """
    
    @staticmethod
    def format_basic(error: Exception) -> str:
        """
        Format an error with minimal details (just the error message).
        
        Args:
            error: The exception to format
            
        Returns:
            A formatted error string
        """
        return f"{type(error).__name__}: {str(error)}"
    
    @staticmethod
    def format_with_context(error: Exception) -> str:
        """
        Format an error with context information.
        
        Args:
            error: The exception to format
            
        Returns:
            A formatted error string with context
        """
        if isinstance(error, CodeHemError) and hasattr(error, 'context'):
            return format_error_with_context(error)
        else:
            return ErrorLogFormatter.format_basic(error)
    
    @staticmethod
    def format_with_trace(error: Exception, limit: int = 10) -> str:
        """
        Format an error with traceback information.
        
        Args:
            error: The exception to format
            limit: Maximum number of stack frames to include
            
        Returns:
            A formatted error string with traceback
        """
        if not error.__traceback__:
            return ErrorLogFormatter.format_with_context(error)
        
        # Get the traceback as a string
        tb_lines = traceback.format_tb(error.__traceback__, limit=limit)
        tb_string = ''.join(tb_lines)
        
        # Format with context if available
        error_str = ErrorLogFormatter.format_with_context(error)
        
        return f"{error_str}\n\nTraceback:\n{tb_string}"
    
    @staticmethod
    def format_for_user(error: Exception) -> str:
        """
        Format an error for display to end users (less technical, more actionable).
        
        Args:
            error: The exception to format
            
        Returns:
            A user-friendly error message
        """
        # Start with a basic message
        message = str(error)
        
        # Remove any technical details
        message = re.sub(r'File ".*?", line \d+', '', message)
        message = re.sub(r'in [a-zA-Z0-9_]+', '', message)
        
        # If it's a CodeHemError, we can provide more context
        if isinstance(error, CodeHemError):
            error_type = type(error).__name__
            
            # Specific messaging based on error type
            if error_type == 'ValidationError':
                return f"Input validation failed: {message}"
            elif error_type == 'ConfigurationError':
                return f"Configuration error: {message}"
            elif error_type == 'ParsingError':
                return f"Code parsing error: {message}"
            elif error_type == 'ExtractionError':
                return f"Code element extraction error: {message}"
            elif error_type == 'ManipulationError':
                return f"Code manipulation error: {message}"
            elif error_type == 'UnsupportedLanguageError':
                return f"Unsupported language: {message}"
            else:
                return f"Error: {message}"
        
        # For non-CodeHemError exceptions, just return a clean version of the message
        return f"Error: {message}"


class ErrorLogger:
    """
    Utility class for logging errors with consistent formatting.
    
    This class provides methods for logging errors at different levels with
    consistent formatting, context information, and optional stack traces.
    """
    
    def __init__(self, logger_name: str = 'codehem'):
        """
        Initialize an ErrorLogger with a specific logger.
        
        Args:
            logger_name: Name of the logger to use
        """
        self.logger = logging.getLogger(logger_name)
    
    def debug(self, message: str, error: Optional[Exception] = None, include_trace: bool = False) -> None:
        """
        Log a debug message with optional error details.
        
        Args:
            message: The message to log
            error: Optional exception to include
            include_trace: Whether to include a stack trace (if error is provided)
        """
        if error:
            if include_trace:
                self.logger.debug(f"{message}\n{ErrorLogFormatter.format_with_trace(error)}")
            else:
                self.logger.debug(f"{message}: {ErrorLogFormatter.format_with_context(error)}")
        else:
            self.logger.debug(message)
    
    def info(self, message: str, error: Optional[Exception] = None) -> None:
        """
        Log an info message with optional error details.
        
        Args:
            message: The message to log
            error: Optional exception to include
        """
        if error:
            self.logger.info(f"{message}: {ErrorLogFormatter.format_with_context(error)}")
        else:
            self.logger.info(message)
    
    def warning(self, message: str, error: Optional[Exception] = None, include_trace: bool = False) -> None:
        """
        Log a warning message with optional error details.
        
        Args:
            message: The message to log
            error: Optional exception to include
            include_trace: Whether to include a stack trace (if error is provided)
        """
        if error:
            if include_trace:
                self.logger.warning(f"{message}\n{ErrorLogFormatter.format_with_trace(error)}")
            else:
                self.logger.warning(f"{message}: {ErrorLogFormatter.format_with_context(error)}")
        else:
            self.logger.warning(message)
    
    def error(self, message: str, error: Optional[Exception] = None, include_trace: bool = True) -> None:
        """
        Log an error message with optional error details.
        
        Args:
            message: The message to log
            error: Optional exception to include
            include_trace: Whether to include a stack trace (if error is provided)
        """
        if error:
            if include_trace:
                self.logger.error(f"{message}\n{ErrorLogFormatter.format_with_trace(error)}")
            else:
                self.logger.error(f"{message}: {ErrorLogFormatter.format_with_context(error)}")
        else:
            self.logger.error(message)
    
    def critical(self, message: str, error: Optional[Exception] = None, include_trace: bool = True) -> None:
        """
        Log a critical message with optional error details.
        
        Args:
            message: The message to log
            error: Optional exception to include
            include_trace: Whether to include a stack trace (if error is provided)
        """
        if error:
            if include_trace:
                self.logger.critical(f"{message}\n{ErrorLogFormatter.format_with_trace(error)}")
            else:
                self.logger.critical(f"{message}: {ErrorLogFormatter.format_with_context(error)}")
        else:
            self.logger.critical(message)
    
    def log_exception(
        self, 
        error: Exception, 
        level: int = logging.ERROR, 
        message: Optional[str] = None, 
        include_trace: bool = True
    ) -> None:
        """
        Log an exception with appropriate context and formatting.
        
        Args:
            error: The exception to log
            level: The logging level to use
            message: Optional message to include
            include_trace: Whether to include a stack trace
        """
        msg = message or f"An exception of type {type(error).__name__} occurred"
        
        if level == logging.DEBUG:
            self.debug(msg, error, include_trace)
        elif level == logging.INFO:
            self.info(msg, error)  # No trace for INFO
        elif level == logging.WARNING:
            self.warning(msg, error, include_trace)
        elif level == logging.ERROR:
            self.error(msg, error, include_trace)
        elif level == logging.CRITICAL:
            self.critical(msg, error, include_trace)
        else:
            # Default to ERROR if an invalid level is provided
            self.error(msg, error, include_trace)


# Create a default error logger
error_logger = ErrorLogger()


def log_error(
    message: str, 
    error: Optional[Exception] = None, 
    level: int = logging.ERROR, 
    include_trace: bool = True,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Log an error message with optional exception details.
    
    This function provides a simpler interface to ErrorLogger for quick logging.
    
    Args:
        message: The message to log
        error: Optional exception to include
        level: The logging level to use
        include_trace: Whether to include a stack trace (if error is provided)
        logger: Optional custom logger to use
    """
    custom_logger = ErrorLogger(logger.name) if logger else error_logger
    custom_logger.log_exception(error, level, message, include_trace) if error else custom_logger.debug(message)


def log_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to automatically log any exceptions raised by a function.
    
    This decorator catches exceptions, logs them with full context, and re-raises
    them to allow normal exception handling to continue.
    
    Args:
        func: The function to wrap
        
    Returns:
        A decorated function that logs errors before re-raising them
        
    Example:
        ```python
        @log_errors
        def process_data(data):
            # Implementation...
        ```
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log the exception with full context
            log_error(
                f"Error in {func.__name__}",
                e,
                level=logging.ERROR,
                include_trace=True
            )
            # Re-raise the exception
            raise
    
    return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)


# ===== Graceful Degradation Patterns =====

class CircuitBreaker:
    """
    Implementation of the Circuit Breaker pattern to prevent cascading failures.
    
    The Circuit Breaker monitors for failures in operations and prevents operation
    execution when the failure rate exceeds a threshold, allowing the system to recover.
    
    It has three states:
    - CLOSED: Operations execute normally, failures are counted
    - OPEN: Operations fail fast without execution when failure threshold is exceeded
    - HALF-OPEN: After a recovery time, allows a limited number of test operations
    """
    
    # Circuit states
    CLOSED = 'closed'  # Normal operation
    OPEN = 'open'      # Failing fast
    HALF_OPEN = 'half-open'  # Testing if system has recovered
    
    def __init__(
        self, 
        failure_threshold: int = 5, 
        recovery_timeout: float = 30.0, 
        test_attempts: int = 1,
        excluded_exceptions: Tuple[Type[Exception], ...] = ()
    ):
        """
        Initialize a CircuitBreaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Time in seconds to wait before transitioning from OPEN to HALF-OPEN
            test_attempts: Number of test attempts allowed in HALF-OPEN state
            excluded_exceptions: Exception types that should not count as failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.test_attempts = test_attempts
        self.excluded_exceptions = excluded_exceptions
        
        # Internal state
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.remaining_test_attempts = test_attempts
        
        # Logging
        self.logger = logging.getLogger('codehem.circuit_breaker')
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorate a function with circuit breaker protection.
        
        Args:
            func: The function to protect
            
        Returns:
            A decorated function
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.execute(lambda: func(*args, **kwargs))
        
        return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)
    
    def execute(self, func: Callable[[], T]) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: The function to execute (must take no arguments)
            
        Returns:
            The result of the function
            
        Raises:
            CircuitBreakerError: If the circuit is OPEN
            Any exceptions raised by the function (if not excluded)
        """
        self._update_state()
        
        if self.state == self.OPEN:
            raise CircuitBreakerError(
                f"Circuit is OPEN until {time.ctime(self.last_failure_time + self.recovery_timeout)}"
            )
        
        try:
            result = func()
            
            # Success handling
            if self.state == self.HALF_OPEN:
                self._transition_to_closed()
            
            return result
            
        except Exception as e:
            # Don't count excluded exceptions as failures
            if isinstance(e, self.excluded_exceptions):
                raise
            
            # Failure handling
            self._on_failure()
            raise
    
    def _update_state(self) -> None:
        """Update the circuit state based on current conditions."""
        if self.state == self.OPEN:
            # Check if recovery timeout has elapsed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self._transition_to_half_open()
    
    def _on_failure(self) -> None:
        """Handle a failure event."""
        self.last_failure_time = time.time()
        
        if self.state == self.CLOSED:
            self.failure_count += 1
            
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()
                
        elif self.state == self.HALF_OPEN:
            self._transition_to_open()
    
    def _transition_to_open(self) -> None:
        """Transition to the OPEN state."""
        if self.state != self.OPEN:
            self.logger.warning("Circuit changed from %s to OPEN", self.state)
            self.state = self.OPEN
            self.last_failure_time = time.time()
    
    def _transition_to_half_open(self) -> None:
        """Transition to the HALF-OPEN state."""
        if self.state != self.HALF_OPEN:
            self.logger.info("Circuit changed from %s to HALF-OPEN", self.state)
            self.state = self.HALF_OPEN
            self.remaining_test_attempts = self.test_attempts
    
    def _transition_to_closed(self) -> None:
        """Transition to the CLOSED state."""
        if self.state != self.CLOSED:
            self.logger.info("Circuit changed from %s to CLOSED", self.state)
            self.state = self.CLOSED
            self.failure_count = 0
    
    def reset(self) -> None:
        """
        Reset the circuit breaker to its initial state.
        
        This can be useful for testing or manual intervention.
        """
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.remaining_test_attempts = self.test_attempts
        self.logger.info("Circuit reset to CLOSED state")


class CircuitBreakerError(Exception):
    """Exception raised when a circuit breaker prevents an operation."""
    pass


def fallback(
    backup_function: Callable[..., T], 
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_errors: bool = True,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that provides a fallback function if the primary function fails.
    
    This implements a simple graceful degradation pattern by executing an alternative
    implementation when the primary implementation raises an exception.
    
    Args:
        backup_function: The function to call if the primary function fails
        exceptions: Tuple of exception types that should trigger fallback
        log_errors: Whether to log errors from the primary function
        logger: Optional custom logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        def offline_data():
            return {"name": "Offline Data", "timestamp": time.time()}
            
        @fallback(offline_data, exceptions=(ConnectionError, TimeoutError))
        def fetch_online_data():
            # Implementation that might fail...
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if log_errors:
                    custom_logger = logger or logging.getLogger('codehem.fallback')
                    custom_logger.warning(
                        f"Function {func.__name__} failed with {type(e).__name__}: {str(e)}. "
                        f"Using fallback function {backup_function.__name__}."
                    )
                
                # Call the backup function with the same arguments
                return backup_function(*args, **kwargs)
        
        return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)
    
    return decorator


# ===== User-Friendly Error Formatting =====

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
        suggestions = self._get_template_for_exception(
            exception, self._suggestion_templates
        )
        
        if not suggestions:
            return []
        
        # Process each suggestion template
        result = []
        for suggestion in suggestions:
            try:
                # Format with exception attributes
                format_vars = {attr: getattr(exception, attr) 
                           for attr in dir(exception) 
                           if not attr.startswith('_') and not callable(getattr(exception, attr))}
                
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


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)


class FeatureFlags:
    """
    Simple feature flag management for controlling behavior during failures.
    
    This class provides a way to enable or disable features at runtime, which
    can be useful for disabling problematic components or activating fallback
    behavior.
    """
    
    def __init__(self):
        """Initialize with an empty set of flags."""
        self._flags = {}
        self._defaults = {}
        self._locks = {}
        self.logger = logging.getLogger('codehem.feature_flags')
    
    def register(self, flag_name: str, default_value: bool = True) -> None:
        """
        Register a new feature flag with a default value.
        
        Args:
            flag_name: The name of the flag
            default_value: The default value (True=enabled, False=disabled)
        """
        self._defaults[flag_name] = default_value
        if flag_name not in self._flags:
            self._flags[flag_name] = default_value
        self._locks[flag_name] = False
    
    def enable(self, flag_name: str) -> None:
        """
        Enable a feature flag.
        
        Args:
            flag_name: The name of the flag to enable
            
        Raises:
            ValueError: If the flag is locked
        """
        if self._locks.get(flag_name, False):
            raise ValueError(f"Feature flag '{flag_name}' is locked and cannot be changed")
        
        self._flags[flag_name] = True
        self.logger.info(f"Feature '{flag_name}' enabled")
    
    def disable(self, flag_name: str) -> None:
        """
        Disable a feature flag.
        
        Args:
            flag_name: The name of the flag to disable
            
        Raises:
            ValueError: If the flag is locked
        """
        if self._locks.get(flag_name, False):
            raise ValueError(f"Feature flag '{flag_name}' is locked and cannot be changed")
        
        self._flags[flag_name] = False
        self.logger.info(f"Feature '{flag_name}' disabled")
    
    def is_enabled(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_name: The name of the flag to check
            
        Returns:
            True if the flag is enabled, False otherwise
            
        Raises:
            KeyError: If the flag is not registered
        """
        if flag_name not in self._flags and flag_name not in self._defaults:
            raise KeyError(f"Feature flag '{flag_name}' is not registered")
        
        return self._flags.get(flag_name, self._defaults.get(flag_name, False))
    
    def reset(self, flag_name: str) -> None:
        """
        Reset a feature flag to its default value.
        
        Args:
            flag_name: The name of the flag to reset
            
        Raises:
            KeyError: If the flag is not registered
            ValueError: If the flag is locked
        """
        if flag_name not in self._defaults:
            raise KeyError(f"Feature flag '{flag_name}' is not registered")
        
        if self._locks.get(flag_name, False):
            raise ValueError(f"Feature flag '{flag_name}' is locked and cannot be changed")
        
        self._flags[flag_name] = self._defaults[flag_name]
        self.logger.info(f"Feature '{flag_name}' reset to default ({self._defaults[flag_name]})")
    
    def reset_all(self) -> None:
        """Reset all feature flags to their default values."""
        for flag_name in list(self._defaults.keys()):
            if not self._locks.get(flag_name, False):
                self._flags[flag_name] = self._defaults[flag_name]
        
        self.logger.info("All feature flags reset to defaults")
    
    def lock(self, flag_name: str) -> None:
        """
        Lock a feature flag to prevent changes.
        
        Args:
            flag_name: The name of the flag to lock
        """
        self._locks[flag_name] = True
        self.logger.info(f"Feature '{flag_name}' locked")
    
    def unlock(self, flag_name: str) -> None:
        """
        Unlock a feature flag to allow changes.
        
        Args:
            flag_name: The name of the flag to unlock
        """
        self._locks[flag_name] = False
        self.logger.info(f"Feature '{flag_name}' unlocked")


# Create a global instance of FeatureFlags
feature_flags = FeatureFlags()


def with_feature_flag(
    flag_name: str, 
    default_behavior: bool = True
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to enable/disable a function based on a feature flag.
    
    When the feature is disabled, the function will not be executed and
    a fallback value will be returned if provided.
    
    Args:
        flag_name: The name of the feature flag to check
        default_behavior: What to do if the flag doesn't exist (True=enable, False=disable)
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @with_feature_flag('advanced_analysis')
        def analyze_data(data):
            # Complex implementation...
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Ensure the flag is registered
        try:
            feature_flags.register(flag_name, default_behavior)
        except Exception:
            # Silently handle registration errors
            pass
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            try:
                if feature_flags.is_enabled(flag_name):
                    return func(*args, **kwargs)
                else:
                    logger = logging.getLogger('codehem.feature_flags')
                    logger.info(
                        f"Function {func.__name__} skipped because feature '{flag_name}' is disabled"
                    )
                    
                    # Check if the user provided a fallback value
                    fallback_value = kwargs.pop('fallback_value', None)
                    if 'fallback_value' in kwargs:
                        del kwargs['fallback_value']
                    
                    return fallback_value
            except KeyError:
                # If the flag doesn't exist, use default behavior
                if default_behavior:
                    return func(*args, **kwargs)
                else:
                    return None
        
        return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)
    
    return decorator


# ===== User-Friendly Error Formatting =====

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
        suggestions = self._get_template_for_exception(
            exception, self._suggestion_templates
        )
        
        if not suggestions:
            return []
        
        # Process each suggestion template
        result = []
        for suggestion in suggestions:
            try:
                # Format with exception attributes
                format_vars = {attr: getattr(exception, attr) 
                           for attr in dir(exception) 
                           if not attr.startswith('_') and not callable(getattr(exception, attr))}
                
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


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)


# ===== Exception Conversion Utilities =====

class ExceptionMapper:
    """
    Maps exceptions from external libraries to CodeHem's exception hierarchy.
    
    This class provides a consistent way to convert external exceptions to
    CodeHem's exception types, preserving context and adding helpful information.
    """
    
    def __init__(self):
        """Initialize with an empty mapping."""
        self._mapping = {}
        self.logger = logging.getLogger('codehem.exception_mapper')
    
    def register(
        self, 
        source_exception: Type[Exception], 
        target_exception: Type[Exception],
        message_template: Optional[str] = None,
        context_mapping: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Register a mapping from a source exception to a target exception.
        
        Args:
            source_exception: The exception type to convert from
            target_exception: The exception type to convert to
            message_template: Optional template for the new exception message
            context_mapping: Optional mapping of source attributes to context keys
        """
        self._mapping[source_exception] = {
            'target': target_exception,
            'message_template': message_template,
            'context_mapping': context_mapping or {}
        }
    
    def convert(self, exception: Exception) -> Exception:
        """
        Convert an exception using the registered mappings.
        
        Args:
            exception: The exception to convert
            
        Returns:
            A new exception of the mapped type, or the original if no mapping exists
        """
        exception_type = type(exception)
        
        # Look for a direct mapping
        if exception_type in self._mapping:
            return self._convert_exception(exception, self._mapping[exception_type])
        
        # Look for a mapping based on inheritance
        for source_type, mapping in self._mapping.items():
            if isinstance(exception, source_type):
                return self._convert_exception(exception, mapping)
        
        # No mapping found, return the original
        return exception
    
    def _convert_exception(self, exception: Exception, mapping: Dict[str, Any]) -> Exception:
        """
        Convert an exception using a specific mapping.
        
        Args:
            exception: The exception to convert
            mapping: The mapping configuration
            
        Returns:
            A new exception of the mapped type
        """
        target_type = mapping['target']
        message_template = mapping['message_template']
        context_mapping = mapping['context_mapping']
        
        # Prepare the message
        if message_template:
            # Use string formatting with exception attributes
            try:
                message = message_template.format(
                    original=str(exception),
                    **{attr: getattr(exception, attr) for attr in dir(exception) if not attr.startswith('_')}
                )
            except (AttributeError, KeyError, TypeError):
                # Fallback to a simple message
                message = f"{message_template} ({str(exception)})"
        else:
            # Use the original message
            message = str(exception)
        
        # Create the new exception
        if issubclass(target_type, CodeHemError):
            # For CodeHemError types, we can use the context mechanism
            context = {}
            
            # Map attributes from the original exception to context keys
            for source_attr, target_key in context_mapping.items():
                try:
                    context[target_key] = getattr(exception, source_attr)
                except AttributeError:
                    pass
            
            # Add the original exception as context
            context['original_exception'] = str(exception)
            context['original_type'] = exception_type.__name__
            
            # Create the new exception
            new_exception = target_type(message, **context)
        else:
            # For non-CodeHemError types, just create a new instance
            new_exception = target_type(message)
        
        # Preserve the original cause
        if exception.__cause__:
            new_exception.__cause__ = exception.__cause__
        else:
            new_exception.__cause__ = exception
        
        # Preserve the traceback
        if hasattr(exception, '__traceback__') and exception.__traceback__:
            new_exception.__traceback__ = exception.__traceback__
        
        return new_exception
    
    def wrap(
        self, 
        func: Callable[..., T], 
        *source_exceptions: Type[Exception]
    ) -> Callable[..., T]:
        """
        Decorator to wrap a function's exceptions using the mapper.
        
        Args:
            func: The function to wrap
            *source_exceptions: Exception types to convert (default: all in mapper)
            
        Returns:
            A decorated function that converts exceptions
            
        Example:
            ```python
            @exception_mapper.wrap
            def connect_to_database():
                # Implementation...
            ```
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check if we should convert this exception
                if source_exceptions and not isinstance(e, source_exceptions):
                    raise
                
                # Convert the exception
                converted = self.convert(e)
                
                # If conversion didn't change anything, re-raise the original
                if converted is e:
                    raise
                
                # Log the conversion
                self.logger.debug(
                    f"Converted {type(e).__name__} to {type(converted).__name__} "
                    f"in function {func.__name__}"
                )
                
                # Raise the converted exception
                raise converted from e
        
        return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)


# Create a global instance of ExceptionMapper
exception_mapper = ExceptionMapper()


def map_exception(
    source_exception: Type[Exception], 
    target_exception: Type[Exception],
    message_template: Optional[str] = None,
    context_mapping: Optional[Dict[str, str]] = None
) -> None:
    """
    Register a mapping from one exception type to another.
    
    This is a convenience function for adding mappings to the global exception mapper.
    
    Args:
        source_exception: The exception type to convert from
        target_exception: The exception type to convert to
        message_template: Optional template for the new exception message
        context_mapping: Optional mapping of source attributes to context keys
        
    Example:
        ```python
        # Map SQLAlchemy exceptions to CodeHem's database exceptions
        map_exception(
            sqlalchemy.exc.OperationalError,
            codehem.core.error_handling.DatabaseError,
            "Database operation failed: {original}",
            {"connection_invalid": "connection_state"}
        )
        ```
    """
    exception_mapper.register(
        source_exception,
        target_exception,
        message_template,
        context_mapping
    )


def convert_exception(
    exception: Exception, 
    target_exception: Type[Exception],
    message: Optional[str] = None,
    preserve_context: bool = True,
    **context
) -> Exception:
    """
    Convert an exception to a different type.
    
    Args:
        exception: The exception to convert
        target_exception: The type to convert to
        message: Optional message for the new exception (default: original message)
        preserve_context: Whether to preserve context from CodeHemError exceptions
        **context: Additional context to add to the new exception
        
    Returns:
        A new exception of the target type
        
    Example:
        ```python
        try:
            # Some operation that might fail
        except Exception as e:
            # Convert to a more specific exception
            new_e = convert_exception(
                e, 
                ValidationError, 
                "Validation failed while processing input",
                parameter="input_data"
            )
            raise new_e from e
        ```
    """
    # Prepare the message
    if message is None:
        message = str(exception)
    
    # Prepare the context
    if preserve_context and isinstance(exception, CodeHemError) and hasattr(exception, 'context'):
        # Copy the context from the original exception
        combined_context = exception.context.copy()
        # Add the new context
        combined_context.update(context)
    else:
        combined_context = context
    
    # Add original exception info to context
    combined_context['original_exception'] = str(exception)
    combined_context['original_type'] = type(exception).__name__
    
    # Create the new exception
    if issubclass(target_exception, CodeHemError):
        # For CodeHemError types, we can pass context directly
        new_exception = target_exception(message, **combined_context)
    else:
        # For other types, just create with the message
        new_exception = target_exception(message)
    
    # Preserve the cause
    if exception.__cause__:
        new_exception.__cause__ = exception.__cause__
    else:
        new_exception.__cause__ = exception
    
    # Preserve the traceback
    if hasattr(exception, '__traceback__') and exception.__traceback__:
        new_exception.__traceback__ = exception.__traceback__
    
    return new_exception


def catching(
    *exception_types: Type[Exception],
    reraise_as: Optional[Type[Exception]] = None,
    message: Optional[str] = None,
    log_level: Optional[int] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that catches specific exceptions and optionally converts them.
    
    This decorator provides a simple way to catch and handle exceptions in a
    more structured way than a basic try/except block.
    
    Args:
        *exception_types: The exception types to catch
        reraise_as: Optional exception type to convert to (if None, exceptions are re-raised as-is)
        message: Optional message for the new exception (if reraise_as is provided)
        log_level: Optional logging level to use (if None, no logging is done)
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @catching(ValueError, TypeError, reraise_as=ValidationError, log_level=logging.WARNING)
        def parse_input(data):
            # Implementation...
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                # Log the exception if requested
                if log_level is not None:
                    logger = logging.getLogger('codehem.catching')
                    logger.log(
                        log_level,
                        f"Caught {type(e).__name__} in {func.__name__}: {str(e)}"
                    )
                
                # Convert and re-raise if requested
                if reraise_as is not None:
                    converted = convert_exception(
                        e,
                        reraise_as,
                        message or f"Error in {func.__name__}: {str(e)}",
                        function=func.__name__
                    )
                    raise converted from e
                else:
                    # Re-raise the original exception
                    raise
            
        return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)
    
    return decorator


# ===== User-Friendly Error Formatting =====

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
        suggestions = self._get_template_for_exception(
            exception, self._suggestion_templates
        )
        
        if not suggestions:
            return []
        
        # Process each suggestion template
        result = []
        for suggestion in suggestions:
            try:
                # Format with exception attributes
                format_vars = {attr: getattr(exception, attr) 
                           for attr in dir(exception) 
                           if not attr.startswith('_') and not callable(getattr(exception, attr))}
                
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


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines) check
        default_behavior: What to do if the flag doesn't exist (True=enable, False=disable)
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @with_feature_flag('advanced_analysis')
        def analyze_data(data):
            # Complex implementation...
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Ensure the flag is registered
        try:
            feature_flags.register(flag_name, default_behavior)
        except Exception:
            # Silently handle registration errors
            pass
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            try:
                if feature_flags.is_enabled(flag_name):
                    return func(*args, **kwargs)
                else:
                    logger = logging.getLogger('codehem.feature_flags')
                    logger.info(
                        f"Function {func.__name__} skipped because feature '{flag_name}' is disabled"
                    )
                    
                    # Check if the user provided a fallback value
                    fallback_value = kwargs.pop('fallback_value', None)
                    if 'fallback_value' in kwargs:
                        del kwargs['fallback_value']
                    
                    return fallback_value
            except KeyError:
                # If the flag doesn't exist, use default behavior
                if default_behavior:
                    return func(*args, **kwargs)
                else:
                    return None
        
        return wrapper


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)
    
    return decorator


# ===== User-Friendly Error Formatting =====

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
        suggestions = self._get_template_for_exception(
            exception, self._suggestion_templates
        )
        
        if not suggestions:
            return []
        
        # Process each suggestion template
        result = []
        for suggestion in suggestions:
            try:
                # Format with exception attributes
                format_vars = {attr: getattr(exception, attr) 
                           for attr in dir(exception) 
                           if not attr.startswith('_') and not callable(getattr(exception, attr))}
                
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


# ===== Batch Error Handling =====

class ErrorCollection:
    """
    Container for collecting multiple errors during batch operations.
    
    This class allows batch operations to continue processing items even when
    some fail, collecting all errors for later reporting.
    """
    
    def __init__(self):
        """Initialize an empty error collection."""
        self.errors = []
        self.logger = logging.getLogger('codehem.error_collection')
    
    def add(
        self, 
        error: Exception, 
        item: Optional[Any] = None, 
        operation: Optional[str] = None
    ) -> None:
        """
        Add an error to the collection.
        
        Args:
            error: The exception to add
            item: The item being processed when the error occurred
            operation: The operation being performed when the error occurred
        """
        self.errors.append({
            'error': error,
            'item': item,
            'operation': operation,
            'timestamp': time.time()
        })
        
        # Log the error
        self.logger.error(
            f"Error {len(self.errors)} collecting for batch operation: "
            f"{type(error).__name__}: {str(error)}"
        )
    
    def is_empty(self) -> bool:
        """
        Check if the collection is empty.
        
        Returns:
            True if no errors have been collected, False otherwise
        """
        return len(self.errors) == 0
    
    def count(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors in the collection.
        
        Returns:
            A list of error dictionaries
        """
        return self.errors
    
    def get_exceptions(self) -> List[Exception]:
        """
        Get just the exception objects from the collection.
        
        Returns:
            A list of exceptions
        """
        return [entry['error'] for entry in self.errors]
    
    def format(self, include_details: bool = False) -> str:
        """
        Format all errors as a string.
        
        Args:
            include_details: Whether to include technical details
            
        Returns:
            A formatted string with all errors
        """
        if not self.errors:
            return "No errors collected"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        
        for i, entry in enumerate(self.errors, 1):
            error = entry['error']
            item = entry['item']
            operation = entry['operation']
            
            # Format the error
            friendly_error = format_user_friendly_error(error, include_details)
            error_str = friendly_error.format(include_details)
            
            # Format the entry
            entry_lines = [f"Error {i}:"]
            if operation:
                entry_lines.append(f"Operation: {operation}")
            if item is not None:
                item_str = repr(item) if len(repr(item)) < 100 else f"{repr(item)[:97]}..."
                entry_lines.append(f"Item: {item_str}")
            
            # Add the formatted error
            for line in error_str.split('\n'):
                entry_lines.append(f"  {line}")
            
            # Add a separator
            entry_str = '\n'.join(entry_lines)
            lines.append(entry_str)
            lines.append('-' * 40)
        
        return '\n'.join(lines)
    
    def raise_combined_error(self) -> None:
        """
        Raise a combined error with all collected errors.
        
        This aggregates all errors into a single BatchOperationError.
        
        Raises:
            BatchOperationError: If there are any errors in the collection
        """
        if not self.errors:
            return
        
        raise BatchOperationError(self)
    
    def __bool__(self) -> bool:
        """
        Check if the collection has any errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors)
    
    def __len__(self) -> int:
        """
        Get the number of errors in the collection.
        
        Returns:
            The number of errors
        """
        return len(self.errors)
    
    def __iter__(self):
        """
        Iterate over errors in the collection.
        
        Yields:
            Error entries (dictionaries)
        """
        return iter(self.errors)


class BatchOperationError(Exception):
    """
    Exception raised when a batch operation encounters multiple errors.
    
    This exception aggregates multiple errors from a batch operation into
    a single exception that can be raised.
    """
    
    def __init__(self, error_collection: ErrorCollection):
        """
        Initialize with an error collection.
        
        Args:
            error_collection: The collection of errors
        """
        self.error_collection = error_collection
        message = f"Batch operation failed with {len(error_collection)} errors"
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        return self.error_collection.format(include_details=False)


def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Any],
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    max_errors: Optional[int] = None,
    raise_on_error: bool = False,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Any], ErrorCollection]:
    """
    Process a batch of items, collecting errors for failures.
    
    This function allows batch operations to continue even when some items fail,
    collecting all errors for later reporting.
    
    Args:
        items: The items to process
        process_func: Function to process each item
        error_handler: Optional function to handle errors for each item
        max_errors: Maximum number of errors before aborting (None for no limit)
        raise_on_error: Whether to raise an exception if any errors occur
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A tuple of (successful_results, error_collection)
        
    Raises:
        BatchOperationError: If raise_on_error is True and any errors occur
        
    Example:
        ```python
        def process_item(item):
            # Implementation...
            
        results, errors = batch_process(items, process_item)
        if errors:
            print(errors.format())
        else:
            print(f"All {len(results)} items processed successfully")
        ```
    """
    # Initialize the error collection
    errors = ErrorCollection()
    
    # Initialize the results list
    results = []
    
    # Get a logger
    log = logger or logging.getLogger('codehem.batch_process')
    
    # Process each item
    for i, item in enumerate(items):
        try:
            # Process the item
            result = process_func(item)
            results.append(result)
            
            # Log the success
            log.debug(f"Successfully processed item {i+1}/{len(items)}")
            
        except Exception as e:
            # Add the error to the collection
            errors.add(e, item, operation_name)
            
            # Call the error handler if provided
            if error_handler:
                try:
                    error_handler(e, item)
                except Exception as handler_error:
                    log.warning(
                        f"Error in error handler for item {i+1}/{len(items)}: "
                        f"{type(handler_error).__name__}: {str(handler_error)}"
                    )
            
            # Check if we've reached the maximum number of errors
            if max_errors is not None and len(errors) >= max_errors:
                log.warning(
                    f"Reached maximum number of errors ({max_errors}), "
                    f"aborting batch operation"
                )
                break
    
    # Raise an exception if requested and there are errors
    if raise_on_error and errors:
        raise BatchOperationError(errors)
    
    # Return the results and error collection
    return results, errors


def collect_errors(
    max_errors: Optional[int] = None,
    error_handler: Optional[Callable[[Exception, Any], None]] = None,
    operation_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Tuple[List[T], ErrorCollection]]]:
    """
    Decorator that collects errors during batch operations.
    
    This decorator wraps a function that processes a list of items, collecting
    errors for each item that fails processing.
    
    Args:
        max_errors: Maximum number of errors before aborting (None for no limit)
        error_handler: Optional function to handle errors for each item
        operation_name: Name of the operation for logging and error messages
        logger: Optional logger to use
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @collect_errors(max_errors=10, operation_name="data_processing")
        def process_data_batch(items):
            results = []
            for item in items:
                # Process each item
                results.append(processed_item)
            return results
        
        results, errors = process_data_batch(items)
        if errors:
            print(errors.format())
        ```
    """
    def decorator(func: Callable[..., List[T]]) -> Callable[..., Tuple[List[T], ErrorCollection]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[List[T], ErrorCollection]:
            # Initialize the error collection
            errors = ErrorCollection()
            
            # Get a logger
            log = logger or logging.getLogger('codehem.collect_errors')
            
            try:
                # Call the original function
                results = func(*args, **kwargs)
                
                # If results is not a list, wrap it in a list
                if not isinstance(results, list):
                    results = [results]
                
                # Return the results and an empty error collection
                return results, errors
                
            except Exception as e:
                # If the whole function fails, add the error to the collection
                errors.add(e, args[0] if args else None, operation_name or func.__name__)
                
                # Call the error handler if provided
                if error_handler:
                    try:
                        error_handler(e, args[0] if args else None)
                    except Exception as handler_error:
                        log.warning(
                            f"Error in error handler: "
                            f"{type(handler_error).__name__}: {str(handler_error)}"
                        )
                
                # Return an empty list of results and the error collection
                return [], errors
        
        return wrapper
    
    return decorator


def handle_partial_failures(error_collection: ErrorCollection) -> None:
    """
    Process an error collection and take appropriate actions.
    
    This function provides a centralized way to handle errors from batch operations,
    such as logging, reporting, or raising exceptions.
    
    Args:
        error_collection: The collection of errors to handle
        
    Example:
        ```python
        results, errors = batch_process(items, process_item)
        if errors:
            handle_partial_failures(errors)
        ```
    """
    # Get a logger
    logger = logging.getLogger('codehem.partial_failures')
    
    # Check if there are any errors
    if not error_collection:
        return
    
    # Log the errors
    logger.warning(
        f"Batch operation completed with {len(error_collection)} errors:\n"
        f"{error_collection.format()}"
    )
    
    # Here you could also:
    # - Send notifications
    # - Record metrics
    # - Trigger retry mechanisms
    # - etc.


class ErrorStatistics:
    """
    Utility for analyzing error patterns in batch operations.
    
    This class provides methods for generating statistics about errors
    to help diagnose systematic issues.
    """
    
    @staticmethod
    def analyze_collection(error_collection: ErrorCollection) -> Dict[str, Any]:
        """
        Analyze an error collection to identify patterns.
        
        Args:
            error_collection: The collection of errors to analyze
            
        Returns:
            A dictionary with error statistics
        """
        if not error_collection:
            return {"total_errors": 0}
        
        # Get all errors
        errors = error_collection.get_errors()
        
        # Count errors by type
        error_types = {}
        for entry in errors:
            error = entry['error']
            error_type = type(error).__name__
            
            if error_type in error_types:
                error_types[error_type] += 1
            else:
                error_types[error_type] = 1
        
        # Calculate time range
        timestamps = [entry['timestamp'] for entry in errors]
        time_range = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        # Group errors by operation
        operations = {}
        for entry in errors:
            op = entry.get('operation', 'unknown')
            
            if op in operations:
                operations[op] += 1
            else:
                operations[op] = 1
        
        # Return the statistics
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "operations": operations,
            "time_range": time_range,
            "first_error": errors[0] if errors else None,
            "last_error": errors[-1] if errors else None
        }
    
    @staticmethod
    def format_statistics(statistics: Dict[str, Any]) -> str:
        """
        Format error statistics as a human-readable string.
        
        Args:
            statistics: The statistics dictionary from analyze_collection
            
        Returns:
            A formatted string with error statistics
        """
        lines = [f"Error Statistics: {statistics['total_errors']} total errors"]
        
        # Add error types
        if "error_types" in statistics and statistics["error_types"]:
            lines.append("\nError Types:")
            for error_type, count in sorted(
                statistics["error_types"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        # Add operations
        if "operations" in statistics and statistics["operations"]:
            lines.append("\nOperations:")
            for op, count in sorted(
                statistics["operations"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / statistics["total_errors"]) * 100
                lines.append(f"  {op}: {count} ({percentage:.1f}%)")
        
        # Add time information
        if "time_range" in statistics and statistics["time_range"] > 0:
            lines.append(f"\nTime Range: {statistics['time_range']:.2f} seconds")
        
        # Add first and last error
        if "first_error" in statistics and statistics["first_error"]:
            first_error = statistics["first_error"]["error"]
            lines.append(f"\nFirst Error: {type(first_error).__name__}: {str(first_error)}")
        
        if "last_error" in statistics and statistics["last_error"]:
            last_error = statistics["last_error"]["error"]
            lines.append(f"Last Error: {type(last_error).__name__}: {str(last_error)}")
        
        return "\n".join(lines)
