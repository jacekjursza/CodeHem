"""
Register language services.
This module should be imported last to avoid circular imports.
"""
from .registry import register_language_service
from .python.service import PythonLanguageService

# Register Python language service
register_language_service('python', PythonLanguageService)