"""
Retry mechanism utilities for handling transient failures.

This module provides functions and decorators for implementing various
retry strategies, including linear, exponential, and jittered backoff.
"""
import functools
import logging
import random
import time
import re
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar, Union


# Type variables
T = TypeVar('T')
R = TypeVar('R')
P = TypeVar('P', bound=Callable[[Exception], bool])
ResultPredicate = Callable[[Any], bool]
ExceptionPredicate = Callable[[Exception], bool]

# Constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_WAIT = 1.0
DEFAULT_MAX_WAIT = 60.0
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_JITTER = 0.1

# Get the logger for codehem
logger = logging.getLogger('codehem')


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
    factor: float = DEFAULT_BACKOFF_FACTOR, 
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
    factor: float = DEFAULT_BACKOFF_FACTOR, 
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
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if logger:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {str(e)}"
                        )

                    attempt += 1

                    if attempt <= max_attempts and logger:
                        logger.info(
                            f"Retrying {func.__name__} (attempt {attempt}/{max_attempts})..."
                        )
            
            # If we get here, all attempts failed
            if logger:
                logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            
            # Re-raise the last exception
            raise last_exception
        
        return wrapper
    
    return decorator


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
    
    return decorator


def retry_if_exception_type(*exception_types: Type[Exception]) -> ExceptionPredicate:
    """
    Create a predicate to retry on specific exception types.
    
    This function creates a predicate for use with the can_retry decorator to
    determine if a retry should occur based on the type of exception raised.
    
    Args:
        *exception_types: One or more exception types to match
        
    Returns:
        A predicate function that returns True if the exception is of specified types
        
    Example:
        ```python
        @can_retry(retry_on_exception=retry_if_exception_type(ValueError, TypeError))
        def parse_data(data):
            # Implementation...
        ```
    """
    def _predicate(exception: Exception) -> bool:
        return isinstance(exception, exception_types)
    
    return _predicate


def retry_if_exception_message(pattern: str) -> ExceptionPredicate:
    """
    Create a predicate to retry if the exception message matches a pattern.
    
    This function creates a predicate for use with the can_retry decorator to
    determine if a retry should occur based on the content of the exception message.
    
    Args:
        pattern: Regular expression pattern to match in the exception message
        
    Returns:
        A predicate function that returns True if the exception message matches the pattern
        
    Example:
        ```python
        @can_retry(retry_on_exception=retry_if_exception_message(r"Network.*unavailable"))
        def connect_to_service():
            # Implementation...
        ```
    """
    compiled_pattern = re.compile(pattern, re.IGNORECASE)
    
    def _predicate(exception: Exception) -> bool:
        return bool(compiled_pattern.search(str(exception)))
    
    return _predicate


def retry_if_result_none(result: Any) -> bool:
    """
    Predicate to retry if the function result is None.
    
    This function creates a predicate for use with the can_retry decorator to
    determine if a retry should occur based on the function's return value.
    
    Args:
        result: The result to evaluate
        
    Returns:
        True if the result is None, False otherwise
        
    Example:
        ```python
        @can_retry(retry_on_result=retry_if_result_none, max_attempts=3)
        def get_resource():
            # Implementation that might return None
        ```
    """
    return result is None


def can_retry(
    max_attempts: int = DEFAULT_MAX_RETRIES,
    retry_on_exception: Optional[ExceptionPredicate] = None,
    retry_on_result: Optional[ResultPredicate] = None,
    wait_strategy: Callable = None,
    initial_wait: float = DEFAULT_INITIAL_WAIT,
    factor: float = DEFAULT_BACKOFF_FACTOR,
    max_wait: float = DEFAULT_MAX_WAIT,
    jitter: float = DEFAULT_JITTER,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """
    Decorator with configurable retry conditions for exceptions and results.
    
    This advanced retry decorator allows for flexible retry logic based on
    both the exceptions raised and the results returned by the function.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        retry_on_exception: Predicate determining if an exception should trigger a retry
        retry_on_result: Predicate determining if a result should trigger a retry
        wait_strategy: Function to calculate wait time between retries
        initial_wait: Initial wait time in seconds (default: 1.0)
        factor: Multiplication factor for backoff strategies that use it (default: 2.0)
        max_wait: Maximum wait time in seconds (default: 60.0)
        jitter: Maximum fraction to randomly adjust wait time by (default: 0.1)
        logger: Logger instance for logging retries
        
    Returns:
        A decorator function
        
    Example:
        ```python
        @can_retry(
            retry_on_exception=retry_if_exception_type(ConnectionError),
            retry_on_result=retry_if_result_none,
            max_attempts=5
        )
        def fetch_resource():
            # Implementation...
        ```
    """
    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            attempt = 1
            last_exception = None
            
            while attempt <= max_attempts:
                try:
                    result = func(*args, **kwargs)
                    
                    # Check if we should retry based on the result
                    if retry_on_result and retry_on_result(result):
                        if logger:
                            logger.info(
                                f"Result from {func.__name__} triggered a retry "
                                f"(attempt {attempt}/{max_attempts})"
                            )
                        
                        # Wait if not the first attempt
                        if attempt > 1 and wait_strategy:
                            wait_time = _calculate_wait_time(
                                wait_strategy, attempt, initial_wait, factor, max_wait, jitter
                            )
                            if logger:
                                logger.info(f"Waiting {wait_time:.2f} seconds before retry...")
                            time.sleep(wait_time)
                        
                        attempt += 1
                        continue
                    
                    # If we get here, the result is acceptable
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry based on the exception
                    should_retry = False
                    if retry_on_exception:
                        should_retry = retry_on_exception(e)
                    
                    if should_retry and attempt < max_attempts:
                        if logger:
                            logger.warning(
                                f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {str(e)}"
                            )
                        
                        # Wait before the next attempt
                        if wait_strategy:
                            wait_time = _calculate_wait_time(
                                wait_strategy, attempt, initial_wait, factor, max_wait, jitter
                            )
                            if logger:
                                logger.info(f"Waiting {wait_time:.2f} seconds before retry...")
                            time.sleep(wait_time)
                        
                        attempt += 1
                    else:
                        # Either we shouldn't retry or this was the last attempt
                        if logger and should_retry:
                            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
                        
                        # Re-raise the exception
                        raise
            
            # If we get here due to retry_on_result, we've exhausted retries
            if last_exception:
                raise last_exception
            
            # If we get here due to retry_on_result, return the last result
            return result
        
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
    exponential backoff by default.
    
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
        @retry_exponential(max_attempts=5, factor=3.0)
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
        jitter=0.0,  # No jitter for pure exponential backoff
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
    jittered backoff by default, which adds randomness to avoid thundering herd.
    
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
        @retry_jittered(max_attempts=5, jitter=0.2)
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


# Private helper functions

def _calculate_wait_time(
    wait_strategy: Callable,
    attempt: int,
    initial_wait: float,
    factor: float,
    max_wait: float,
    jitter: float
) -> float:
    """
    Calculate the wait time based on the strategy and parameters.
    
    Args:
        wait_strategy: Function to calculate wait time
        attempt: The current attempt number
        initial_wait: Initial wait time in seconds
        factor: Multiplication factor
        max_wait: Maximum wait time in seconds
        jitter: Maximum fraction to randomly adjust wait time by
        
    Returns:
        The calculated wait time in seconds
    """
    if wait_strategy == linear_backoff:
        return wait_strategy(attempt, initial_wait, factor)
    elif wait_strategy == jittered_backoff:
        return wait_strategy(attempt, initial_wait, factor, max_wait, jitter)
    elif wait_strategy == exponential_backoff:
        return wait_strategy(attempt, initial_wait, factor, max_wait)
    else:
        # For custom strategies, try different argument patterns
        try:
            return wait_strategy(attempt, initial_wait, factor, max_wait)
        except TypeError:
            try:
                return wait_strategy(attempt, initial_wait, factor)
            except TypeError:
                return wait_strategy(attempt)
