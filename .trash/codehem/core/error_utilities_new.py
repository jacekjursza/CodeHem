"""
Error handling utilities for CodeHem.

This module provides advanced error handling utilities that complement
the core error handling systems defined in error_handling.py and error_context.py.
It includes the following major component groups:

1. Retry Mechanisms - Functions and decorators for automatic retrying of operations
2. Error Logging - Utilities for standardized error logging
3. Graceful Degradation - Tools for handling failures gracefully (circuit breakers, feature flags)
4. Exception Conversion - Utilities for mapping and converting between exception types
5. User-Friendly Errors - Formatting tools for user-facing error messages
6. Batch Error Handling - Components for managing errors during batch operations

These utilities are designed to work together to provide a comprehensive
error handling strategy throughout the CodeHem codebase.
"""
import contextlib
import functools
import logging
import random
import re
import sys
import time
import traceback
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, Tuple, Pattern, cast, Generic

from codehem.core.error_handling import CodeHemError
from codehem.core.error_context import error_context, ErrorContext, format_error_with_context

# Type variables for generic functions
T = TypeVar('T')
R = TypeVar('R')
E = TypeVar('E', bound=Exception)

# Get the default logger for codehem
logger = logging.getLogger('codehem')

# Constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_WAIT = 1.0
DEFAULT_MAX_WAIT = 60.0
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_JITTER = 0.1

#=====================================================================
# SECTION 1: RETRY MECHANISMS
#=====================================================================
"""
This section provides utilities for retrying operations that may fail transiently.
It includes backoff strategies, retry decorators, and predicates for conditional retries.
"""

#---------------------------------------------------------------------
# 1.1 Backoff Strategies
#---------------------------------------------------------------------

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

#---------------------------------------------------------------------
# 1.2 Retry Predicates
#---------------------------------------------------------------------

class RetryPredicate(Generic[T]):
    """
    Base class for predicates that determine when to retry an operation.
    
    Predicates can be based on the exception that occurred or the result
    of the operation.
    """
    
    def __call__(self, result: Optional[T] = None, exception: Optional[Exception] = None) -> bool:
        """
        Determines whether to retry the operation.
        
        Args:
            result: The result returned by the operation (None if it failed)
            exception: The exception raised by the operation (None if it succeeded)
            
        Returns:
            True if the operation should be retried, False otherwise
        """
        raise NotImplementedError("Subclasses must implement __call__")


def retry_if_exception_type(*exception_types: Type[Exception]) -> RetryPredicate[Any]:
    """
    Returns a predicate that retries if the exception is of a specified type.
    
    Args:
        *exception_types: The exception types that should trigger a retry
        
    Returns:
        A retry predicate
        
    Example:
        ```python
        @can_retry(retry_on_exception=retry_if_exception_type(ConnectionError, TimeoutError))
        def fetch_data():
            # Implementation...
        ```
    """
    class RetryOnExceptionType(RetryPredicate[Any]):
        def __call__(self, result: Optional[Any] = None, exception: Optional[Exception] = None) -> bool:
            return exception is not None and isinstance(exception, exception_types)
    
    return RetryOnExceptionType()


def retry_if_exception_message(pattern: Union[str, Pattern]) -> RetryPredicate[Any]:
    """
    Returns a predicate that retries if the exception message matches a pattern.
    
    Args:
        pattern: A string or compiled regex pattern to match against the exception message
        
    Returns:
        A retry predicate
        
    Example:
        ```python
        @can_retry(retry_on_exception=retry_if_exception_message("connection reset"))
        def fetch_data():
            # Implementation...
        ```
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern, re.IGNORECASE)
    
    class RetryOnExceptionMessage(RetryPredicate[Any]):
        def __call__(self, result: Optional[Any] = None, exception: Optional[Exception] = None) -> bool:
            return (exception is not None and 
                    hasattr(exception, '__str__') and 
                    bool(pattern.search(str(exception))))
    
    return RetryOnExceptionMessage()


def retry_if_result_none() -> RetryPredicate[Any]:
    """
    Returns a predicate that retries if the operation returns None.
    
    This is useful for operations that return None to indicate a temporary failure.
    
    Returns:
        A retry predicate
        
    Example:
        ```python
        @can_retry(retry_on_result=retry_if_result_none())
        def fetch_data():
            # Implementation that might return None on failure
        ```
    """
    class RetryOnNoneResult(RetryPredicate[Any]):
        def __call__(self, result: Optional[Any] = None, exception: Optional[Exception] = None) -> bool:
            return exception is None and result is None
    
    return RetryOnNoneResult()

#---------------------------------------------------------------------
# 1.3 Retry Decorators
#---------------------------------------------------------------------

def retry(
    max_attempts: int = DEFAULT_MAX_RETRIES, 
    exceptions: Tuple[Type[Exception], ...] = (Exception,), 
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
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
            
            log = logger or logging.getLogger(f'codehem.retry.{func.__name__}')
            
            while attempt <= max_attempts:
                try:
                    with error_context("retry", 
                                      operation=func.__name__, 
                                      attempt=attempt, 
                                      max_attempts=max_attempts):
                        return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if log:
                        log.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {str(e)}"
                        )
                    
                    attempt += 1
                    
                    # If this was the last attempt, don't log about retrying
                    if attempt <= max_attempts:
                        if log:
                            log.info(f"Retrying {func.__name__} (attempt {attempt}/{max_attempts})...")
            
            # If we get here, all attempts failed
            if log:
                log.error(f"All {max_attempts} attempts failed for {func.__name__}")
            
            # Re-raise the last exception
            raise last_exception
        
        return wrapper
    
    return decorator


def retry_with_backoff(
    max_attempts: int = DEFAULT_MAX_RETRIES, 
    exceptions: Tuple[Type[Exception], ...] = (Exception,), 
    backoff_strategy: Callable[[int, float, float, float], float] = exponential_backoff,
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
            
            log = logger or logging.getLogger(f'codehem.retry.{func.__name__}')
            
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
                        
                        if log:
                            log.warning(
                                f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                                f"Retrying in {wait_time:.2f} seconds."
                            )
                        
                        # Wait before the next attempt
                        time.sleep(wait_time)
                    else:
                        # This was the last attempt
                        if log:
                            log.error(f"All {max_attempts} attempts failed for {func.__name__}")
                    
                    attempt += 1
            
            # If we get here, all attempts failed
            # Re-raise the last exception
            raise last_exception
        
        return wrapper
    
    return decorator


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
    
    This is a convenience wrapper around retry_with_backoff that uses
    exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        exceptions: Tuple of exception classes that should trigger a retry
        initial_wait: Initial wait time in seconds (default: 1.0)
        factor: Multiplication factor for exponential growth (default: 2.0)
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
        jitter=0.0,  # No jitter for pure exponential
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
    
    This is a convenience wrapper around retry_with_backoff that uses
    jittered exponential backoff to avoid the thundering herd problem.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        exceptions: Tuple of exception classes that should trigger a retry
        initial_wait: Initial wait time in seconds (default: 1.0)
        factor: Multiplication factor for exponential growth (default: 2.0)
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


def can_retry(
    max_attempts: int = DEFAULT_MAX_RETRIES,
    retry_on_exception: Optional[RetryPredicate[Any]] = None,
    retry_on_result: Optional[RetryPredicate[Any]] = None,
    backoff_strategy: Callable[[int, float, float, float], float] = exponential_backoff,
    initial_wait: float = DEFAULT_INITIAL_WAIT,
    factor: float = DEFAULT_BACKOFF_FACTOR,
    max_wait: float = DEFAULT_MAX_WAIT,
    jitter: float = DEFAULT_JITTER,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Advanced decorator for conditional retrying based on predicates.
    
    This decorator allows for conditional retrying based on the exception
    type, exception message, or function result.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        retry_on_exception: Predicate for retrying based on exception
        retry_on_result: Predicate for retrying based on result
        backoff_strategy: Function to calculate wait time between retries
        initial_wait: Initial wait time in seconds (default: 1.0)
        factor: Multiplication factor for exponential growth (default: 2.0)
        max_wait: Maximum wait time in seconds (default: 60.0)
        jitter: Maximum fraction to randomly adjust wait time by (default: 0.1)
        logger: Logger instance for logging retries
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @can_retry(
            retry_on_exception=retry_if_exception_type(ConnectionError),
            retry_on_result=retry_if_result_none()
        )
        def fetch_data():
            # Implementation...
        ```
    """
    # If no predicates are provided, use a default that retries on any exception
    if retry_on_exception is None and retry_on_result is None:
        retry_on_exception = retry_if_exception_type(Exception)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 1
            last_exception: Optional[Exception] = None
            last_result: Optional[T] = None
            should_retry = False
            
            log = logger or logging.getLogger(f'codehem.can_retry.{func.__name__}')
            
            while attempt <= max_attempts:
                try:
                    with error_context("retry", 
                                      operation=func.__name__, 
                                      attempt=attempt, 
                                      max_attempts=max_attempts):
                        last_result = func(*args, **kwargs)
                    
                    # Check if we should retry based on the result
                    if retry_on_result and retry_on_result(result=last_result, exception=None):
                        should_retry = True
                        if log:
                            log.info(
                                f"Retry condition met for result from {func.__name__} "
                                f"(attempt {attempt}/{max_attempts})"
                            )
                    else:
                        # No retry needed, return the result
                        return last_result
                        
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry based on the exception
                    if retry_on_exception and retry_on_exception(result=None, exception=e):
                        should_retry = True
                        if log:
                            log.warning(
                                f"Retry condition met for exception from {func.__name__}: {str(e)} "
                                f"(attempt {attempt}/{max_attempts})"
                            )
                    else:
                        # No retry for this exception, re-raise
                        raise
                
                # If we should retry and not at max attempts yet
                if should_retry and attempt < max_attempts:
                    # Calculate wait time
                    if backoff_strategy == linear_backoff:
                        wait_time = backoff_strategy(attempt, initial_wait, factor)
                    elif backoff_strategy == jittered_backoff:
                        wait_time = backoff_strategy(attempt, initial_wait, factor, max_wait, jitter)
                    else:  # exponential_backoff or custom
                        wait_time = backoff_strategy(attempt, initial_wait, factor, max_wait)
                    
                    if log:
                        log.info(f"Retrying {func.__name__} in {wait_time:.2f} seconds")
                    
                    # Wait before the next attempt
                    time.sleep(wait_time)
                    
                    # Reset for next attempt
                    should_retry = False
                    attempt += 1
                    continue
                elif should_retry:
                    # We've reached max attempts
                    if log:
                        log.error(f"All {max_attempts} attempts failed for {func.__name__}")
                    
                    # If there was an exception on the last attempt, raise it
                    if last_exception:
                        raise last_exception
                    
                    # Otherwise, return the last result
                    return last_result
                else:
                    # We didn't meet retry conditions, raise the exception
                    if last_exception:
                        raise last_exception
                    
                    # Or return the result
                    return last_result
            
            # If we get here, all attempts failed
            if last_exception:
                raise last_exception
            
            # Otherwise, return the last result
            return last_result
        
        return wrapper
    
    return decorator
