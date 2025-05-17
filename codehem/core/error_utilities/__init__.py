"""
Error handling utilities for CodeHem.

This package provides advanced error handling utilities that complement
the basic error handling system, including retry mechanisms, standardized
error logging, batch processing with error collection, user-friendly error
formatting, and more.
"""
# Import and re-export error severity constants
from .formatting import ErrorSeverity, UserFriendlyError, ErrorFormatter
from .formatting import format_user_friendly_error, format_error_message, format_error_for_api
from .formatting import with_friendly_errors

# Import and re-export retry mechanisms
from .retry import (
    linear_backoff,
    exponential_backoff,
    jittered_backoff,
    retry,
    retry_with_backoff,
    retry_exponential,
    retry_jittered,
    can_retry,
    retry_if_exception_type,
    retry_if_exception_message,
    retry_if_result_none,
)

# Import logging and graceful utilities
from .helpers import (
    ErrorLogFormatter,
    ErrorLogger,
    log_error,
    log_errors,
    CircuitBreaker,
    CircuitBreakerError,
    fallback,
    FeatureFlags,
    with_feature_flag,
    ExceptionMapper,
    convert_exception,
    map_exception,
    catching,
)

# Import and re-export batch processing utilities
from .batch import ErrorCollection, BatchOperationError
from .batch import batch_process, collect_errors, handle_partial_failures
from .batch import ErrorStatistics

# Create the default error formatter instance
error_formatter = ErrorFormatter()
