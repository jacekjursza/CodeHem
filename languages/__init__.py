"""
Language detection and service management.
"""
from typing import Dict, List, Optional, Any, Type
import os
import re

from languages.registry import registry
from core.error_handling import UnsupportedLanguageError

# Dictionary of registered language services
_language_services = {}

def register_language_service(language_code: str, service_class: Type):
    """Register a language service for a specific language."""
    _language_services[language_code] = service_class()

def get_language_service(language_code: str) -> Optional[Any]:
    """Get language service for the specified language code."""
    return _language_services.get(language_code.lower())

def get_language_service_for_file(file_path: str) -> Optional[Any]:
    """Get language service for the specified file based on its extension."""
    _, ext = os.path.splitext(file_path)
    if not ext:
        return None
        
    # Try to find language by extension
    language_code = registry.get_language_by_extension(ext.lower())
    if language_code:
        return get_language_service(language_code)
    
    return None

def get_language_service_for_code(code: str) -> Optional[Any]:
    """
    Attempt to detect language from code content.
    This is a heuristic approach and not 100% reliable.
    """
    # Try each registered language service
    for language_code, service in _language_services.items():
        # Use detection heuristics
        confidence = _calculate_language_confidence(code, language_code)
        if confidence > 0.7:  # Threshold for confident detection
            return service
    
    # If no confident detection, try to find common patterns
    if re.search(r'def\s+\w+\s*\(', code) and re.search(r':\s*\n', code):
        return get_language_service('python')
    elif re.search(r'function\s+\w+\s*\(', code) and re.search(r'\)\s*{', code):
        if re.search(r':\s*\w+', code):  # Type annotations suggest TypeScript
            return get_language_service('typescript')
        else:
            return get_language_service('javascript')
    
    return None

def get_supported_languages() -> List[str]:
    """Get a list of all supported language codes."""
    return list(_language_services.keys())

def _calculate_language_confidence(code: str, language_code: str) -> float:
    """
    Calculate confidence score for a language detection.
    Returns a value between 0.0 and 1.0.
    """
    if language_code == 'python':
        # Count Python-specific patterns
        patterns = [
            r'def\s+\w+\s*\(',  # Function definitions
            r'class\s+\w+\s*:',  # Class definitions
            r'import\s+\w+',     # Import statements
            r'from\s+\w+\s+import',  # From imports
            r':\s*\n',           # Colon followed by newline
            r'__\w+__'           # Dunder methods
        ]
        score = sum(10 if re.search(pattern, code) else 0 for pattern in patterns)
        
    elif language_code in ('javascript', 'typescript'):
        # Count JS/TS-specific patterns
        patterns = [
            r'function\s+\w+\s*\(',  # Function declarations
            r'const\s+\w+\s*=',      # Const declarations
            r'let\s+\w+\s*=',        # Let declarations
            r'var\s+\w+\s*=',        # Var declarations
            r'import\s+.*from',      # Import statements
            r'export\s+',            # Export statements
            r';\s*\n'                # Semicolons
        ]
        score = sum(10 if re.search(pattern, code) else 0 for pattern in patterns)
        
        # Additional TypeScript patterns
        if language_code == 'typescript':
            ts_patterns = [
                r':\s*\w+',          # Type annotations
                r'interface\s+\w+',   # Interfaces
                r'<\w+>',             # Generic type parameters
            ]
            score += sum(10 if re.search(pattern, code) else 0 for pattern in ts_patterns)
    else:
        # Default for other languages
        score = 0
    
    # Normalize score 
    total_possible = 60 if language_code == 'typescript' else 60
    normalized = min(1.0, score / total_possible)
    
    return normalized