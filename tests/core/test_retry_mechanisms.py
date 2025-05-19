"""
Unit tests for retry mechanisms in error_utilities/retry.py.

This is a focused test module that tests only the retry mechanisms without
depending on the entire application structure.
"""
import unittest
import time
import random
from codehem.core.error_utilities.retry import (
    linear_backoff,
    exponential_backoff,
    jittered_backoff,
    retry_if_exception_type,
    retry_if_exception_message,
    retry_if_result_none,
    can_retry
)


class RetryUtilitiesTests(unittest.TestCase):
    """
    Tests for the retry utility functions in error_utilities/retry.py.
    """
    
    def test_linear_backoff(self):
        """Test the linear_backoff function."""
        self.assertEqual(linear_backoff(1, 1.0, 1.0), 1.0)
        self.assertEqual(linear_backoff(2, 1.0, 1.0), 2.0)
        self.assertEqual(linear_backoff(3, 1.0, 1.0), 3.0)
        self.assertEqual(linear_backoff(2, 2.0, 2.0), 4.0)
    
    def test_exponential_backoff(self):
        """Test the exponential_backoff function."""
        self.assertEqual(exponential_backoff(1, 1.0, 2.0), 1.0)
        self.assertEqual(exponential_backoff(2, 1.0, 2.0), 2.0)
        self.assertEqual(exponential_backoff(3, 1.0, 2.0), 4.0)
        self.assertEqual(exponential_backoff(10, 1.0, 2.0, 10.0), 10.0)  # Capped at max_wait
    
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
    
    def test_can_retry_with_wait_strategy(self):
        """Test the can_retry decorator with wait strategy."""
        # Function that fails and records time between attempts
        attempts = []
        start_time = time.time()
        
        def wait_strategy(attempt, initial_wait, factor, max_wait):
            # Use a very small wait time for the test
            return 0.01 * attempt
        
        @can_retry(
            retry_on_exception=retry_if_exception_type(ValueError),
            max_attempts=3,
            wait_strategy=wait_strategy,
            initial_wait=0.01
        )
        def failing_function():
            attempts.append(time.time() - start_time)
            raise ValueError("Test error")
        
        # Should raise after 3 attempts
        with self.assertRaises(ValueError):
            failing_function()
        
        self.assertEqual(len(attempts), 3)
        
        # Check that there's a delay between attempts
        self.assertTrue(attempts[1] > attempts[0])
        self.assertTrue(attempts[2] > attempts[1])


if __name__ == "__main__":
    unittest.main()
