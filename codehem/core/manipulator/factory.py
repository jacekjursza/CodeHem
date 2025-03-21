"""
Factory for creating code manipulators for different languages.
"""
from typing import Optional
from .abstract import AbstractCodeManipulator
from codehem.core.manipulator.lang.python_manipulator import PythonCodeManipulator
from codehem.core.manipulator.lang.typescript_manipulator import TypeScriptCodeManipulator

def get_code_manipulator(language: str) -> Optional[AbstractCodeManipulator]:
    """
    Get a code manipulator for the specified language.
    
    Args:
        language: Language code (e.g., 'python', 'javascript')
        
    Returns:
        A code manipulator for the specified language or None if not supported
    """
    language = language.lower()
    if language == 'python':
        return PythonCodeManipulator()
    elif language in ['javascript', 'typescript']:
        return TypeScriptCodeManipulator()
    return None