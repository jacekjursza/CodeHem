"""
Error handling utilities for CodeHem.
"""
import logging
import traceback
from typing import Optional, Type, Any, Callable

logger = logging.getLogger('codehem')

class CodeHemError(Exception):
    """Base class for all CodeHem exceptions."""
    pass

class ExtractionError(CodeHemError):
    """Exception raised for errors during code extraction."""
    pass

class UnsupportedLanguageError(CodeHemError):
    """Exception raised when an operation is attempted with an unsupported language."""
    pass

def handle_extraction_errors(func: Callable) -> Callable:
    """
    Decorator to handle extraction errors gracefully.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ExtractionError as e:
            logger.error(f"Extraction error: {str(e)}")
            # Return empty result instead of raising exception
            return []
        except UnsupportedLanguageError as e:
            logger.error(f"Unsupported language: {str(e)}")
            # Return empty result instead of raising exception
            return []
        except AttributeError as e:
            logger.error(f"! Could not find extractor for {func.__name__} / {args[0].language_code}")
            print(f"{e}")
            # Return empty result instead of raising exception
            return []
        except Exception as e:
            logger.exception(f"Unexpected error during extraction: {str(e)}")
            # Re-raise other exceptions
            raise
    
    return wrapper