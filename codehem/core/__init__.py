"""
Core components for CodeHem.
"""
from .extraction_service import ExtractionService
from .manipulation_service import ManipulationService

# Import error handling utilities
from .error_handling import (
    CodeHemError, ExtractionError, UnsupportedLanguageError,
    handle_extraction_errors
)

# Import error utilities
from .error_utilities import (
    error_formatter,
    format_user_friendly_error,
    format_error_message,
    format_error_for_api,
    with_friendly_errors,
    ErrorSeverity,
    UserFriendlyError,
    ErrorFormatter,
    linear_backoff,
    exponential_backoff,
    jittered_backoff,
    retry,
    retry_with_backoff,
    ErrorCollection,
    BatchOperationError,
    batch_process,
    collect_errors,
    handle_partial_failures,
    ErrorStatistics
)
