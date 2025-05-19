"""
Batch error handling utilities for CodeHem.

This module provides utilities for managing errors during batch operations,
allowing operations to continue even when some items fail while collecting
errors for later analysis and reporting.
"""
import functools
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

# Type variables
T = TypeVar('T')

# Get the logger for codehem
logger = logging.getLogger('codehem')


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
            from codehem.core.error_utilities.formatting import format_user_friendly_error
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
