"""
A standalone validation script for testing retry mechanisms.

This script imports only the retry module and tests it in isolation without
depending on the entire codehem package structure.
"""
import sys
import os
import random
import time

# Add the codehem directory to the path for direct imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import only the retry module directly (avoiding the main package)
from codehem.core.error_utilities.retry import (
    linear_backoff,
    exponential_backoff,
    jittered_backoff,
    retry_if_exception_type,
    retry_if_exception_message,
    retry_if_result_none,
    can_retry
)

# Set a fixed random seed for reproducible results
random.seed(42)

# Test the backoff strategies
print("Testing backoff strategies...")
print(f"linear_backoff(1, 1.0, 1.0) = {linear_backoff(1, 1.0, 1.0)}")  # Expected: 1.0
print(f"linear_backoff(2, 1.0, 1.0) = {linear_backoff(2, 1.0, 1.0)}")  # Expected: 2.0
print(f"linear_backoff(3, 1.0, 1.0) = {linear_backoff(3, 1.0, 1.0)}")  # Expected: 3.0

print(f"exponential_backoff(1, 1.0, 2.0) = {exponential_backoff(1, 1.0, 2.0)}")  # Expected: 1.0
print(f"exponential_backoff(2, 1.0, 2.0) = {exponential_backoff(2, 1.0, 2.0)}")  # Expected: 2.0
print(f"exponential_backoff(3, 1.0, 2.0) = {exponential_backoff(3, 1.0, 2.0)}")  # Expected: 4.0
print(f"exponential_backoff(10, 1.0, 2.0, 10.0) = {exponential_backoff(10, 1.0, 2.0, 10.0)}")  # Expected: 10.0

# Test the jittered backoff
wait_time = jittered_backoff(2, 1.0, 2.0, 10.0, 0.1)
print(f"jittered_backoff(2, 1.0, 2.0, 10.0, 0.1) = {wait_time}")
if 1.8 <= wait_time <= 2.2:
    print("✓ jittered_backoff within expected range")
else:
    print("✗ jittered_backoff outside expected range")

# Test the retry_if_exception_type predicate
print("\nTesting retry_if_exception_type...")
predicate = retry_if_exception_type(ValueError)
print(f"retry_if_exception_type(ValueError) for ValueError = {predicate(ValueError('test'))}")  # Expected: True
print(f"retry_if_exception_type(ValueError) for TypeError = {predicate(TypeError('test'))}")  # Expected: False

predicate = retry_if_exception_type(ValueError, TypeError)
print(f"retry_if_exception_type(ValueError, TypeError) for ValueError = {predicate(ValueError('test'))}")  # Expected: True
print(f"retry_if_exception_type(ValueError, TypeError) for TypeError = {predicate(TypeError('test'))}")  # Expected: True
print(f"retry_if_exception_type(ValueError, TypeError) for KeyError = {predicate(KeyError('test'))}")  # Expected: False

# Test the retry_if_exception_message predicate
print("\nTesting retry_if_exception_message...")
predicate = retry_if_exception_message(r"connection.*lost")
print(f"retry_if_exception_message('connection.*lost') for 'The connection was lost' = {predicate(Exception('The connection was lost'))}")  # Expected: True
print(f"retry_if_exception_message('connection.*lost') for 'Invalid input' = {predicate(Exception('Invalid input'))}")  # Expected: False
print(f"retry_if_exception_message('connection.*lost') for 'Connection Lost' (case insensitive) = {predicate(Exception('Connection Lost'))}")  # Expected: True

# Test the retry_if_result_none predicate
print("\nTesting retry_if_result_none...")
print(f"retry_if_result_none(None) = {retry_if_result_none(None)}")  # Expected: True
print(f"retry_if_result_none('') = {retry_if_result_none('')}")  # Expected: False
print(f"retry_if_result_none(0) = {retry_if_result_none(0)}")  # Expected: False
print(f"retry_if_result_none(False) = {retry_if_result_none(False)}")  # Expected: False

# Test the can_retry decorator with exception predicate
print("\nTesting can_retry with exception predicate...")
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

try:
    function_with_different_errors()
except TypeError as e:
    print(f"✓ Correctly raised TypeError: {e}")
    print(f"Number of attempts: {len(attempts)} (expected: 2)")

# Test the can_retry decorator with result predicate
print("\nTesting can_retry with result predicate...")
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

result = returns_none_then_value()
print(f"Result: {result} (expected: Success)")
print(f"Number of attempts: {len(attempts)} (expected: 2)")

# Test the can_retry decorator with wait strategy
print("\nTesting can_retry with wait strategy...")
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

try:
    failing_function()
except ValueError as e:
    print(f"✓ Correctly raised ValueError: {e}")
    print(f"Number of attempts: {len(attempts)} (expected: 3)")
    
    # Check that there's a delay between attempts
    if attempts[1] > attempts[0] and attempts[2] > attempts[1]:
        print("✓ Delay between attempts verified")
    else:
        print("✗ No delay between attempts")

print("\nAll validations complete!")
