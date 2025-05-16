"""
Error context enhancement system for CodeHem.

This module provides utilities for enriching exceptions with contextual information
as they propagate through the call stack. This includes a context manager for adding
execution context to exceptions, utility functions for error handling, and classes
for storing structured error context data.
"""
import contextlib
import functools
import inspect
import logging
import sys
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

from codehem.core.error_handling import CodeHemError

logger = logging.getLogger('codehem')

class ErrorContext:
    """
    Class for storing contextual information about errors.
    
    This class provides a structured way to capture and manage context information
    that helps diagnose issues when exceptions occur.
    """
    
    def __init__(self, 
                 context_name: str, 
                 component: Optional[str] = None, 
                 operation: Optional[str] = None, 
                 **kwargs):
        """
        Initialize a new error context.
        
        Args:
            context_name: A name that identifies this context
            component: The component where this context applies
            operation: The operation being performed within this context
            **kwargs: Additional context data
        """
        self.context_name = context_name
        self.component = component
        self.operation = operation
        self.data = kwargs
        self.parent = None
        self.children = []
        
    def add_data(self, key: str, value: Any) -> 'ErrorContext':
        """
        Add additional data to the context.
        
        Args:
            key: The data key
            value: The data value
            
        Returns:
            Self for method chaining
        """
        self.data[key] = value
        return self
    
    def add_child(self, child: 'ErrorContext') -> None:
        """
        Add a child context to this context.
        
        Args:
            child: The child context to add
        """
        child.parent = self
        self.children.append(child)
    
    def get_root(self) -> 'ErrorContext':
        """
        Get the root context in the context tree.
        
        Returns:
            The root context
        """
        if self.parent is None:
            return self
        return self.parent.get_root()
    
    def get_full_context(self) -> Dict[str, Any]:
        """
        Get the full context data including all parent contexts.
        
        Returns:
            A dictionary containing all context data from this context and its parents
        """
        if self.parent is None:
            return self.data.copy()
        
        # Get parent context first, then update with this context's data
        # This allows child contexts to override parent context values
        full_context = self.parent.get_full_context()
        full_context.update(self.data)
        return full_context
    
    def format_tree(self, indent: int = 0) -> str:
        """
        Format the context tree as a string for debugging.
        
        Args:
            indent: The current indentation level
            
        Returns:
            A formatted string representation of the context tree
        """
        indent_str = "  " * indent
        result = f"{indent_str}Context: {self.context_name}\n"
        
        if self.component:
            result += f"{indent_str}  Component: {self.component}\n"
        if self.operation:
            result += f"{indent_str}  Operation: {self.operation}\n"
        
        if self.data:
            result += f"{indent_str}  Data:\n"
            for key, value in self.data.items():
                result += f"{indent_str}    {key}: {value}\n"
        
        for child in self.children:
            result += child.format_tree(indent + 1)
        
        return result
    
    def __str__(self) -> str:
        """String representation of the context."""
        return self.format_tree()


# Define a context manager for adding execution context to exceptions
@contextlib.contextmanager
def error_context(context_name: str, 
                  component: Optional[str] = None, 
                  operation: Optional[str] = None, 
                  **kwargs):
    """
    Context manager for adding execution context to exceptions.
    
    This context manager creates a new ErrorContext and attaches it to any
    CodeHemError exceptions that are raised within the context. The context
    data helps diagnose where and why the error occurred.
    
    Args:
        context_name: A name that identifies this context
        component: The component where this context applies
        operation: The operation being performed within this context
        **kwargs: Additional context data
        
    Yields:
        None
        
    Example:
        ```python
        with error_context('parsing', component='Python', operation='parse_function', 
                          code=code_snippet):
            parse_result = parser.parse(code_snippet)
        ```
    """
    # Create a context object
    ctx = ErrorContext(context_name, component, operation, **kwargs)
    
    # Get caller frame information for better error reporting
    caller_frame = inspect.currentframe().f_back
    caller_info = inspect.getframeinfo(caller_frame)
    ctx.add_data('file', caller_info.filename)
    ctx.add_data('line', caller_info.lineno)
    ctx.add_data('function', caller_info.function)
    
    try:
        yield
    except CodeHemError as e:
        # Add context to the exception
        for key, value in ctx.data.items():
            e.add_context(key, value)
        
        # Also add component and operation if they exist
        if component:
            e.add_context('component', component)
        if operation:
            e.add_context('operation', operation)
        
        # Re-raise the exception with context
        raise
    except Exception as e:
        # For non-CodeHemError exceptions, wrap them in a CodeHemError
        # with the context information
        message = f"Error in {context_name}: {str(e)}"
        wrapped = CodeHemError(message)
        
        # Add all context data
        for key, value in ctx.data.items():
            wrapped.add_context(key, value)
        
        # Add component and operation if they exist
        if component:
            wrapped.add_context('component', component)
        if operation:
            wrapped.add_context('operation', operation)
        
        # Preserve original exception
        wrapped.__cause__ = e
        
        # Re-raise the wrapped exception
        raise wrapped from e


# Type variable for function return type
T = TypeVar('T')

def with_error_context(context_name: str, 
                       component: Optional[str] = None, 
                       operation: Optional[str] = None, 
                       **kwargs) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add error context to a function.
    
    This decorator wraps a function with the error_context context manager,
    automatically adding context information to any exceptions raised within
    the function.
    
    Args:
        context_name: A name that identifies this context
        component: The component where this context applies
        operation: The operation being performed within this context
        **kwargs: Additional context data
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @with_error_context('extraction', component='Python', operation='extract_class')
        def extract_class(code):
            # Implementation...
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwds) -> T:
            # If operation was not specified, use the function name
            op = operation if operation else func.__name__
            
            # Wrap the function call with error_context
            with error_context(context_name, component, op, **kwargs):
                return func(*args, **kwds)
        return wrapper
    return decorator


def wrap_exception(e: Exception, 
                   context_name: str, 
                   component: Optional[str] = None, 
                   operation: Optional[str] = None, 
                   **kwargs) -> CodeHemError:
    """
    Wrap a non-CodeHemError exception in a CodeHemError with context.
    
    Args:
        e: The exception to wrap
        context_name: A name that identifies this context
        component: The component where this context applies
        operation: The operation being performed within this context
        **kwargs: Additional context data
        
    Returns:
        A new CodeHemError with the original exception as its cause
    """
    message = f"Error in {context_name}: {str(e)}"
    wrapped = CodeHemError(message)
    
    # Add all context data
    for key, value in kwargs.items():
        wrapped.add_context(key, value)
    
    # Add component and operation if they exist
    if component:
        wrapped.add_context('component', component)
    if operation:
        wrapped.add_context('operation', operation)
    
    # Preserve original exception
    wrapped.__cause__ = e
    
    return wrapped


def rethrow_as(exception_type: Type[CodeHemError], 
               e: Exception, 
               message: Optional[str] = None, 
               **kwargs) -> None:
    """
    Re-throw an exception as a different exception type.
    
    This function wraps an exception in a new exception of the specified type
    and raises it, preserving the original exception as the cause.
    
    Args:
        exception_type: The type of exception to raise
        e: The original exception
        message: Optional message for the new exception
        **kwargs: Additional context data
        
    Raises:
        The specified exception type
    """
    if message is None:
        message = str(e)
    
    new_exception = exception_type(message, **kwargs)
    
    # If the original exception was a CodeHemError, copy its context
    if isinstance(e, CodeHemError) and hasattr(e, 'context'):
        for key, value in e.context.items():
            new_exception.add_context(key, value)
    
    # Add any new context
    for key, value in kwargs.items():
        new_exception.add_context(key, value)
    
    # Preserve original exception
    new_exception.__cause__ = e
    
    raise new_exception from e


def format_error_with_context(e: Exception) -> str:
    """
    Format an exception with its context for logging or display.
    
    Args:
        e: The exception to format
        
    Returns:
        A formatted string representation of the exception with context
    """
    if not isinstance(e, CodeHemError) or not hasattr(e, 'context'):
        return str(e)
    
    error_type = type(e).__name__
    message = str(e)
    
    # Format the exception context
    context_lines = []
    for key, value in e.context.items():
        context_lines.append(f"  {key}: {value}")
    
    # Format the exception chain
    cause_lines = []
    cause = e.__cause__
    while cause is not None:
        cause_type = type(cause).__name__
        cause_lines.append(f"  Caused by {cause_type}: {str(cause)}")
        cause = cause.__cause__
    
    # Combine all parts
    parts = [f"{error_type}: {message}"]
    
    if context_lines:
        parts.append("Context:")
        parts.extend(context_lines)
    
    if cause_lines:
        parts.append("Causes:")
        parts.extend(cause_lines)
    
    return "\n".join(parts)
