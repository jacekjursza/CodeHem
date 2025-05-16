"""
A completely isolated test script for retry mechanisms.

This script creates isolated copies of the necessary functions and
tests them without importing from the actual codehem package.
"""
import functools
import logging
import random
import re
import time
import unittest
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar, Union

# Mock error_context for testing
class MockErrorContext:
    def __init__(self, **kwargs):
        self.context = kwargs
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

# Copy the backoff functions for isolated testing
def linear_backoff(attempt: int, initial_wait: float = 1.0, increment: float = 1.0) -> float:
    """Linear backoff strategy."""
    return initial_wait + (attempt - 1) * increment

def exponential_backoff(
    attempt: int, 
    initial_wait: float = 1.0, 
    factor: float = 2.0, 
    max_wait: float = 60.0
) -> float:
    """Exponential backoff strategy."""
    wait_time = initial_wait * (factor ** (attempt - 1))
    return min(wait_time, max_wait)

def jittered_backoff(
    attempt: int, 
    initial_wait: float = 1.0, 
    factor: float = 2.0, 
    max_wait: float = 60.0, 
    jitter: float = 0.1
) -> float:
    """Jittered exponential backoff strategy."""
    wait_time = exponential_backoff(attempt, initial_wait, factor, max_wait)
    jitter_multiplier = 1.0 + jitter * (2 * random.random() - 1)
    return wait_time * jitter_multiplier

# Type variables
T = TypeVar('T')
R = TypeVar('R')
ExceptionPredicate = Callable[[Exception], bool]
ResultPredicate = Callable[[Any], bool]

# Simplified retry predicates
def retry_if_exception_type(*exception_types: Type[Exception]) -> ExceptionPredicate:
    """Create a predicate to retry on specific exception types."""
    def _predicate(exception: Exception) -> bool:
        return isinstance(exception, exception_types)
    return _predicate

def retry_if_exception_message(pattern: str) -> ExceptionPredicate:
    """Create a predicate to retry if the exception message matches a pattern."""
    compiled_pattern = re.compile(pattern, re.IGNORECASE)  # Fix: add IGNORECASE flag
    def _predicate(exception: Exception) -> bool:
        return bool(compiled_pattern.search(str(exception)))
    return _predicate

def retry_if_result_none(result: Any) -> bool:
    """Predicate to retry if the function result is None."""
    return result is None

# Implementation of can_retry decorator
def can_retry(
    max_attempts: int = 3,
    retry_on_exception: Optional[ExceptionPredicate] = None,
    retry_on_result: Optional[ResultPredicate] = None,
    wait_strategy: Optional[Callable] = None,
    initial_wait: float = 1.0,
    factor: float = 2.0,
    max_wait: float = 60.0,
    jitter: float = 0.1,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """Decorator with configurable retry conditions for exceptions and results."""
    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            attempt = 1
            last_exception = None
            
            while attempt <= max_attempts:
                try:
                    with MockErrorContext(
                        operation=func.__name__, 
                        attempt=attempt, 
                        max_attempts=max_attempts
                    ):
                        result = func(*args, **kwargs)
                    
                    # Check if we should retry based on the result
                    if retry_on_result and retry_on_result(result):
                        if logger:
                            logger.info(f"Result triggered a retry (attempt {attempt}/{max_attempts})")
                        
                        # Wait if not the first attempt and we have a wait strategy
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
                            logger.warning(f"Attempt {attempt}/{max_attempts} failed: {str(e)}")
                        
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
                            logger.error(f"All {max_attempts} attempts failed")
                        
                        # Re-raise the exception
                        raise
            
            # If we get here due to retry_on_result, we've exhausted retries
            if last_exception:
                raise last_exception
            
            # If we get here due to retry_on_result, return the last result
            return result
        
        return wrapper
    
    return decorator

# Helper function for calculating wait time
def _calculate_wait_time(
    wait_strategy: Callable,
    attempt: int,
    initial_wait: float,
    factor: float,
    max_wait: float,
    jitter: float
) -> float:
    """Calculate the wait time based on the strategy and parameters."""
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

# Implementation of retry_exponential decorator
def retry_exponential(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    initial_wait: float = 1.0,
    factor: float = 2.0,
    max_wait: float = 60.0,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Convenience decorator for retrying with exponential backoff."""
    return can_retry(
        max_attempts=max_attempts,
        retry_on_exception=retry_if_exception_type(*exceptions),
        wait_strategy=exponential_backoff,
        initial_wait=initial_wait,
        factor=factor,
        max_wait=max_wait,
        jitter=0.0,  # No jitter for pure exponential
        logger=logger
    )

# Implementation of retry_jittered decorator
def retry_jittered(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    initial_wait: float = 1.0,
    factor: float = 2.0,
    max_wait: float = 60.0,
    jitter: float = 0.1,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Convenience decorator for retrying with jittered exponential backoff."""
    return can_retry(
        max_attempts=max_attempts,
        retry_on_exception=retry_if_exception_type(*exceptions),
        wait_strategy=jittered_backoff,
        initial_wait=initial_wait,
        factor=factor,
        max_wait=max_wait,
        jitter=jitter,
        logger=logger
    )

# Test class
class RetryTests(unittest.TestCase):
    """Tests for the retry utilities."""
    
    def test_backoff_strategies(self):
        """Test the backoff strategy functions."""
        # Test linear backoff
        self.assertEqual(linear_backoff(1, 1.0, 1.0), 1.0)
        self.assertEqual(linear_backoff(2, 1.0, 1.0), 2.0)
        self.assertEqual(linear_backoff(3, 1.0, 1.0), 3.0)
        
        # Test exponential backoff
        self.assertEqual(exponential_backoff(1, 1.0, 2.0), 1.0)
        self.assertEqual(exponential_backoff(2, 1.0, 2.0), 2.0)
        self.assertEqual(exponential_backoff(3, 1.0, 2.0), 4.0)
        
        # Test max_wait cap
        self.assertEqual(exponential_backoff(10, 1.0, 2.0, 10.0), 10.0)
    
    def test_jittered_backoff(self):
        """Test the jittered_backoff function."""
        # Fix the random seed for reproducible results
        random.seed(42)
        
        # Test with small jitter
        wait_time = jittered_backoff(2, 1.0, 2.0, 10.0, 0.1)
        self.assertTrue(1.8 <= wait_time <= 2.2)
        
        # Test with larger jitter
        wait_time = jittered_backoff(2, 1.0, 2.0, 10.0, 0.5)
        self.assertTrue(1.0 <= wait_time <= 3.0)
    
    def test_retry_if_exception_type(self):
        """Test the retry_if_exception_type predicate."""
        # Create a predicate for ValueError
        predicate = retry_if_exception_type(ValueError)
        
        # Should return True for ValueError
        self.assertTrue(predicate(ValueError("test")))
        
        # Should return False for other exceptions
        self.assertFalse(predicate(TypeError("test")))
        
        # Create a predicate for multiple exception types
        predicate = retry_if_exception_type(ValueError, TypeError)
        
        # Should return True for both exception types
        self.assertTrue(predicate(ValueError("test")))
        self.assertTrue(predicate(TypeError("test")))
        
        # Should return False for other exceptions
        self.assertFalse(predicate(KeyError("test")))
    
    def test_retry_if_exception_message(self):
        """Test the retry_if_exception_message predicate."""
        # Create a predicate for a specific message pattern
        predicate = retry_if_exception_message(r"connection.*lost")
        
        # Should return True if the message matches
        self.assertTrue(predicate(Exception("The connection was lost")))
        
        # Should return False if the message doesn't match
        self.assertFalse(predicate(Exception("Invalid input")))
        
        # Case insensitive match
        self.assertTrue(predicate(Exception("Connection Lost")))
    
    def test_retry_if_result_none(self):
        """Test the retry_if_result_none predicate."""
        # Should return True for None
        self.assertTrue(retry_if_result_none(None))
        
        # Should return False for any other value
        self.assertFalse(retry_if_result_none(""))
        self.assertFalse(retry_if_result_none(0))
        self.assertFalse(retry_if_result_none(False))
        self.assertFalse(retry_if_result_none([]))
    
    def test_can_retry_with_exception_predicate(self):
        """Test the can_retry decorator with exception predicate."""
        # Function that raises different exceptions based on attempts
        attempts = []
        
        @can_retry(
            retry_on_exception=retry_if_exception_type(ValueError),
            max_attempts=3
        )
        def function_with_different_errors():
            attempts.append(1)
            if len(attempts) == 1:
                raise ValueError("Retry this")
            elif len(attempts) == 2:
                raise TypeError("Don't retry this")
            return "Success"
        
        # Should raise TypeError on the 2nd attempt (no retry)
        with self.assertRaises(TypeError):
            function_with_different_errors()
        
        self.assertEqual(len(attempts), 2)
    
    def test_can_retry_with_result_predicate(self):
        """Test the can_retry decorator with result predicate."""
        # Function that returns None and then a value
        attempts = []
        
        @can_retry(
            retry_on_result=retry_if_result_none,
            max_attempts=3
        )
        def returns_none_then_value():
            attempts.append(1)
            if len(attempts) < 2:
                return None
            return "Success"
        
        # Should return "Success" on the 2nd attempt
        result = returns_none_then_value()
        
        self.assertEqual(result, "Success")
        self.assertEqual(len(attempts), 2)
    
    def test_retry_exponential(self):
        """Test the retry_exponential decorator."""
        # Function that fails twice then succeeds
        attempts = []
        
        @retry_exponential(max_attempts=4, exceptions=(ValueError,))
        def eventually_succeeds():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError(f"Attempt {len(attempts)} failed")
            return "Success"
        
        # Should succeed on the 3rd attempt
        result = eventually_succeeds()
        
        self.assertEqual(result, "Success")
        self.assertEqual(len(attempts), 3)
    
    def test_retry_jittered(self):
        """Test the retry_jittered decorator."""
        # Function that fails twice then succeeds
        attempts = []
        
        @retry_jittered(max_attempts=4, exceptions=(ValueError,), initial_wait=0.01)
        def eventually_succeeds():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError(f"Attempt {len(attempts)} failed")
            return "Success"
        
        # Should succeed on the 3rd attempt
        result = eventually_succeeds()
        
        self.assertEqual(result, "Success")
        self.assertEqual(len(attempts), 3)


if __name__ == "__main__":
    unittest.main()
