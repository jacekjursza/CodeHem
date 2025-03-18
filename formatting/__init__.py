"""
Code formatting module for standardizing code output across languages.
"""
from .formatter import CodeFormatter
from .python_formatter import PythonFormatter
from .typescript_formatter import TypeScriptFormatter

def get_formatter(language: str) -> CodeFormatter:
    """
    Get a formatter for the specified language.
    
    Args:
        language: Language code (e.g., 'python', 'typescript')
        
    Returns:
        A formatter for the specified language
    """
    language = language.lower()
    
    if language == 'python':
        return PythonFormatter()
    elif language in ['typescript', 'javascript']:
        return TypeScriptFormatter()
    else:
        # Default to a basic formatter for unsupported languages
        return CodeFormatter()