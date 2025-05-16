"""
Unit tests for error_utilities module.

This module contains tests for the various error handling utilities in the
error_utilities module, including retry mechanisms, error logging, graceful
degradation patterns, exception conversion, and more.
"""
import logging
import re
import time
import unittest
from typing import List, Optional, Any

from codehem.core.error_handling import (
    CodeHemError, ValidationError, ExtractionError, UnsupportedLanguageError
)
from codehem.core.error_utilities import (
    # Retry mechanisms
    retry, retry_with_backoff, retry_exponential, retry_jittered, can_retry,
    retry_if_exception_type, retry_if_exception_message, retry_if_result_none,
    linear_backoff, exponential_backoff, jittered_backoff,
    
    # Error logging
    ErrorLogFormatter, ErrorLogger, log_error, log_errors,
    
    # Graceful degradation
    CircuitBreaker, CircuitBreakerError, fallback, FeatureFlags, with_feature_flag,
    
    # Exception conversion
    ExceptionMapper, convert_exception, map_exception, catching,
    
    # User-friendly errors
    ErrorSeverity, UserFriendlyError, ErrorFormatter, format_user_friendly_error,
    format_error_message, format_error_for_api, with_friendly_errors,
    
    # Batch error handling
    ErrorCollection, BatchOperationError, batch_process, collect_errors,
    handle_partial_failures, ErrorStatistics
)


class RetryMechanismsTests(unittest.TestCase):
    """Tests for retry mechanism utilities."""
    
    def test_backoff_strategies(self):
        """Test backoff strategy functions."""
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
        
        # Test jittered backoff is within expected range
        wait_time = jittered_backoff(2, 1.0, 2.0, 10.0, 0.1)
        self.assertTrue(1.8 <= wait_time <= 2.2)
    
    def test_basic_retry(self):
        """Test the basic retry decorator."""
        attempts = []
        
        @retry(max_attempts=3)
        def failing_function():
            attempts.append(1)
            raise ValueError("Test error")
        
        # Should raise after 3 attempts
        with self.assertRaises(ValueError):
            failing_function()
        
        self.assertEqual(len(attempts), 3)
    
    def test_retry_with_success(self):
        """Test retry with eventual success."""
        attempts = []
        
        @retry(max_attempts=5)
        def eventually_succeeds():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("Not yet")
            return "Success"
        
        # Should succeed on the 3rd attempt
        result = eventually_succeeds()
        
        self.assertEqual(result, "Success")
        self.assertEqual(len(attempts), 3)
    
    def test_retry_with_backoff(self):
        """Test retry with exponential backoff."""
        attempts = []
        start_time = time.time()
        
        @retry_with_backoff(
            max_attempts=3,
            initial_wait=0.01,  # Small values for fast tests
            factor=2.0
        )
        def failing_function():
            attempts.append(time.time() - start_time)
            raise ValueError("Test error")
        
        # Should raise after 3 attempts
        with self.assertRaises(ValueError):
            failing_function()
        
        self.assertEqual(len(attempts), 3)
        
        # Check that the timing between attempts increases
        self.assertTrue(attempts[1] - attempts[0] < attempts[2] - attempts[1])
    
    def test_conditional_retry(self):
        """Test conditional retry based on exception type."""
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
    
    def test_retry_on_result(self):
        """Test retry based on function result."""
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


class ErrorHandlingTests(unittest.TestCase):
    """Tests for the main error_utilities functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test exception
        self.test_error = ValidationError("Invalid input", parameter="test_param", value=123)
    
    def test_error_logging_formatter(self):
        """Test the ErrorLogFormatter class."""
        formatter = ErrorLogFormatter()
        
        # Test basic formatting
        basic = formatter.format_basic(self.test_error)
        self.assertIn("ValidationError", basic)
        self.assertIn("Invalid input", basic)
        
        # Test context formatting
        with_context = formatter.format_with_context(self.test_error)
        self.assertIn("ValidationError", with_context)
        self.assertIn("Invalid input", with_context)
        self.assertIn("parameter=test_param", with_context)
        self.assertIn("value=123", with_context)
        
        # Test trace formatting (no trace in our test error)
        with_trace = formatter.format_with_trace(self.test_error)
        self.assertIn("ValidationError", with_trace)
    
    def test_circuit_breaker(self):
        """Test the CircuitBreaker class."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        calls = 0
        
        # Function that always fails
        def failing_function():
            nonlocal calls
            calls += 1
            raise ValueError("Test error")
        
        # First call - should fail but circuit stays closed
        with self.assertRaises(ValueError):
            cb.execute(failing_function)
        
        self.assertEqual(cb.state, CircuitBreaker.CLOSED)
        self.assertEqual(calls, 1)
        
        # Second call - should fail and open the circuit
        with self.assertRaises(ValueError):
            cb.execute(failing_function)
        
        self.assertEqual(cb.state, CircuitBreaker.OPEN)
        self.assertEqual(calls, 2)
        
        # Third call - circuit is open, should fail fast
        with self.assertRaises(CircuitBreakerError):
            cb.execute(failing_function)
        
        self.assertEqual(calls, 2)  # No actual call to the function
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Circuit should be half-open now
        self.assertEqual(cb.state, CircuitBreaker.HALF_OPEN)
        
        # Reset the circuit
        cb.reset()
        self.assertEqual(cb.state, CircuitBreaker.CLOSED)
    
    def test_fallback(self):
        """Test the fallback decorator."""
        # Create a primary function that fails
        def primary_function(x):
            raise ValueError("Primary function failed")
        
        # Create a backup function
        def backup_function(x):
            return f"Backup: {x}"
        
        # Apply the fallback decorator
        decorated = fallback(backup_function, exceptions=(ValueError,))(primary_function)
        
        # Call the decorated function
        result = decorated("test")
        
        # Should use the backup function
        self.assertEqual(result, "Backup: test")
    
    def test_feature_flags(self):
        """Test the FeatureFlags class."""
        flags = FeatureFlags()
        
        # Register some flags
        flags.register("feature1", True)
        flags.register("feature2", False)
        
        # Check initial values
        self.assertTrue(flags.is_enabled("feature1"))
        self.assertFalse(flags.is_enabled("feature2"))
        
        # Modify values
        flags.disable("feature1")
        flags.enable("feature2")
        
        # Check modified values
        self.assertFalse(flags.is_enabled("feature1"))
        self.assertTrue(flags.is_enabled("feature2"))
        
        # Reset to defaults
        flags.reset_all()
        
        # Check reset values
        self.assertTrue(flags.is_enabled("feature1"))
        self.assertFalse(flags.is_enabled("feature2"))
    
    def test_exception_conversion(self):
        """Test exception conversion utilities."""
        # Convert a standard exception to a CodeHemError
        std_error = ValueError("Invalid value")
        converted = convert_exception(
            std_error,
            ValidationError,
            "Validation failed",
            parameter="test_param",
            value="invalid"
        )
        
        # Check type and attributes
        self.assertIsInstance(converted, ValidationError)
        self.assertEqual(converted.parameter, "test_param")
        self.assertEqual(converted.value, "invalid")
        self.assertIn("Validation failed", str(converted))
        
        # Check that the original exception is preserved as the cause
        self.assertEqual(converted.__cause__, std_error)
    
    def test_exception_mapper(self):
        """Test the ExceptionMapper class."""
        mapper = ExceptionMapper()
        
        # Register a mapping
        mapper.register(
            ValueError,
            ValidationError,
            "Validation error: {original}",
            {"args": "error_args"}
        )
        
        # Create a test exception
        error = ValueError("Invalid input")
        
        # Convert the exception
        converted = mapper.convert(error)
        
        # Check type and message
        self.assertIsInstance(converted, ValidationError)
        self.assertIn("Validation error", str(converted))
        self.assertIn("Invalid input", str(converted))
    
    def test_user_friendly_error(self):
        """Test the UserFriendlyError class."""
        # Create a user-friendly error
        error = UserFriendlyError(
            message="Something went wrong with your request",
            original_error=self.test_error,
            severity=ErrorSeverity.ERROR,
            suggestions=["Check your input", "Try again later"],
            details="Technical details here",
            code="ERR-001"
        )
        
        # Check string representation
        self.assertEqual(str(error), "Something went wrong with your request")
        
        # Check formatted output
        formatted = error.format(include_details=False)
        self.assertIn("ERROR: Something went wrong with your request", formatted)
        self.assertIn("Code: ERR-001", formatted)
        self.assertIn("Check your input", formatted)
        self.assertIn("Try again later", formatted)
        self.assertNotIn("Technical details", formatted)
        
        # Check with details
        formatted_details = error.format(include_details=True)
        self.assertIn("Technical details", formatted_details)
    
    def test_error_formatter(self):
        """Test the ErrorFormatter class."""
        formatter = ErrorFormatter()
        
        # Format a validation error
        result = formatter.format_exception(self.test_error)
        
        # Check type and contents
        self.assertIsInstance(result, UserFriendlyError)
        self.assertIn("Invalid input", str(result))
        self.assertEqual(result.severity, ErrorSeverity.ERROR)
        self.assertTrue(len(result.suggestions) > 0)
    
    def test_batch_error_handling(self):
        """Test batch error handling utilities."""
        # Create a function that succeeds for even numbers, fails for odd numbers
        def process_item(item: int) -> str:
            if item % 2 == 0:
                return f"Processed {item}"
            else:
                raise ValueError(f"Can't process odd number: {item}")
        
        # Process a batch of items
        items = [1, 2, 3, 4, 5]
        results, errors = batch_process(items, process_item)
        
        # Check results
        self.assertEqual(len(results), 2)  # 2 successful items (2, 4)
        self.assertEqual(results[0], "Processed 2")
        self.assertEqual(results[1], "Processed 4")
        
        # Check errors
        self.assertEqual(errors.count(), 3)  # 3 failed items (1, 3, 5)
        self.assertIsInstance(errors.get_exceptions()[0], ValueError)
    
    def test_error_collection(self):
        """Test the ErrorCollection class."""
        # Create an error collection
        collection = ErrorCollection()
        
        # Add some errors
        collection.add(ValueError("Error 1"), item="item1", operation="test")
        collection.add(TypeError("Error 2"), item="item2", operation="test")
        
        # Check collection properties
        self.assertEqual(collection.count(), 2)
        self.assertFalse(collection.is_empty())
        
        # Check error retrieval
        errors = collection.get_errors()
        self.assertEqual(len(errors), 2)
        self.assertIsInstance(errors[0]['error'], ValueError)
        self.assertIsInstance(errors[1]['error'], TypeError)
        
        # Check string formatting
        formatted = collection.format()
        self.assertIn("Collected 2 errors", formatted)
        self.assertIn("Error 1", formatted)
        self.assertIn("Error 2", formatted)
        
        # Test raising a combined error
        with self.assertRaises(BatchOperationError):
            collection.raise_combined_error()


class ErrorStatisticsTests(unittest.TestCase):
    """Tests for error statistics utilities."""
    
    def test_analyze_collection(self):
        """Test error pattern analysis."""
        # Create an error collection
        collection = ErrorCollection()
        
        # Add some errors
        collection.add(ValueError("Error 1"), item="item1", operation="op1")
        collection.add(ValueError("Error 2"), item="item2", operation="op1")
        collection.add(TypeError("Error 3"), item="item3", operation="op2")
        
        # Analyze the collection
        stats = ErrorStatistics.analyze_collection(collection)
        
        # Check statistics
        self.assertEqual(stats["total_errors"], 3)
        self.assertEqual(stats["error_types"]["ValueError"], 2)
        self.assertEqual(stats["error_types"]["TypeError"], 1)
        self.assertEqual(stats["operations"]["op1"], 2)
        self.assertEqual(stats["operations"]["op2"], 1)
        
        # Check string formatting
        formatted = ErrorStatistics.format_statistics(stats)
        self.assertIn("Error Statistics: 3 total errors", formatted)
        self.assertIn("ValueError: 2", formatted)
        self.assertIn("TypeError: 1", formatted)


class DecoratorsTests(unittest.TestCase):
    """Tests for error handling decorators."""
    
    def test_log_errors_decorator(self):
        """Test the log_errors decorator."""
        logs = []
        
        # Mock logger handler that captures log records
        class MockHandler(logging.Handler):
            def emit(self, record):
                logs.append(record.getMessage())
        
        # Set up logging with our mock handler
        logger = logging.getLogger('codehem')
        handler = MockHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        # Create a function that raises an exception
        @log_errors
        def function_that_fails():
            raise ValueError("Test error")
        
        # Call the function and catch the exception
        with self.assertRaises(ValueError):
            function_that_fails()
        
        # Check that the error was logged
        self.assertTrue(any("Error in function_that_fails" in log for log in logs))
    
    def test_catching_decorator(self):
        """Test the catching decorator."""
        # Create a function that raises different exceptions
        @catching(ValueError, TypeError, reraise_as=ValidationError)
        def function_with_exceptions(error_type: str):
            if error_type == "value":
                raise ValueError("Value error")
            elif error_type == "type":
                raise TypeError("Type error")
            else:
                raise KeyError("Key error")
        
        # ValueError should be converted to ValidationError
        with self.assertRaises(ValidationError):
            function_with_exceptions("value")
        
        # TypeError should be converted to ValidationError
        with self.assertRaises(ValidationError):
            function_with_exceptions("type")
        
        # KeyError should not be converted
        with self.assertRaises(KeyError):
            function_with_exceptions("key")
    
    def test_with_friendly_errors_decorator(self):
        """Test the with_friendly_errors decorator."""
        # Create a function that raises an exception
        @with_friendly_errors
        def function_that_fails():
            raise ValueError("Something bad happened")
        
        # Call the function and catch the exception
        with self.assertRaises(RuntimeError) as context:
            function_that_fails()
        
        # Check that the exception message is user-friendly
        error_msg = str(context.exception)
        self.assertIn("ERROR", error_msg)
        self.assertIn("Something bad happened", error_msg)


class CollectErrorsDecoratorTests(unittest.TestCase):
    """Tests for the collect_errors decorator."""
    
    def test_collect_errors_decorator(self):
        """Test the collect_errors decorator."""
        # Create a function that processes items with errors
        @collect_errors()
        def process_items(items: List[int]) -> List[str]:
            results = []
            for item in items:
                if item % 2 == 0:
                    results.append(f"Processed {item}")
                else:
                    raise ValueError(f"Can't process odd number: {item}")
            return results
        
        # Process a batch of items
        items = [1, 2, 3, 4, 5]
        results, errors = process_items(items)
        
        # Check results and errors
        self.assertEqual(len(results), 0)  # All processing stopped on first error
        self.assertEqual(errors.count(), 1)  # First error (item 1)
        
        # Test a function that handles errors internally
        @collect_errors()
        def process_items_safely(items: List[int]) -> List[str]:
            results = []
            for item in items:
                try:
                    if item % 2 == 0:
                        results.append(f"Processed {item}")
                    else:
                        raise ValueError(f"Can't process odd number: {item}")
                except ValueError:
                    # Handle the error internally
                    results.append(f"Skipped {item}")
            return results
        
        # Process a batch of items
        results, errors = process_items_safely(items)
        
        # Check results and errors
        self.assertEqual(len(results), 5)  # All items processed
        self.assertEqual(errors.count(), 0)  # No errors captured


if __name__ == "__main__":
    unittest.main()
