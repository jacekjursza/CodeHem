"""
Language modules for CodeHem.
"""
# Re-export registry functions
from .registry import (
    register_language_service,
    get_language_service,
    get_language_service_for_file,
    get_language_service_for_code,
    get_supported_languages
)

# Import language services
# Note: We don't import and register here to avoid circular imports