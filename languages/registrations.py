"""
Register language services with the central registry.
"""
from languages import register_language_service
from languages.python_service import PythonLanguageService
from languages.javascript_service import JavaScriptLanguageService
from languages.typescript_service import TypeScriptLanguageService

# Register Python
register_language_service('python', PythonLanguageService)

# Register JavaScript
register_language_service('javascript', JavaScriptLanguageService)

# Register TypeScript
register_language_service('typescript', TypeScriptLanguageService)