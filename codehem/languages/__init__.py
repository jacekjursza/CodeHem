"""
Language detection and service management.
"""
from typing import List, Optional, Any, Type
import os
import re
from .registry import registry

_language_services = {}

def register_language_service(language_code: str, service_class: Type):
    """Register a language service for a specific language."""
    _language_services[language_code] = service_class()

def get_language_service(language_code: str) -> Optional[Any]:
    """Get language service for the specified language code."""
    return _language_services.get(language_code.lower())

def get_language_service_for_file(file_path: str) -> Optional[Any]:
    """Get language service for the specified file based on its extension."""
    (_, ext) = os.path.splitext(file_path)
    if not ext:
        return None
    language_code = registry.get_language_by_extension(ext.lower())
    if language_code:
        return get_language_service(language_code)
    return None

def get_language_service_for_code(code: str) -> Optional[Any]:
    """
    Attempt to detect language from code content.
    This is a heuristic approach and not 100% reliable.
    """
    for (language_code, service) in _language_services.items():
        confidence = _calculate_language_confidence(code, language_code)
        if confidence > 0.7:
            return service
    if re.search('def\\s+\\w+\\s*\\(', code) and re.search(':\\s*\\n', code):
        return get_language_service('python')
    elif re.search('function\\s+\\w+\\s*\\(', code) and re.search('\\)\\s*{', code):
        if re.search(':\\s*\\w+', code):
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
        patterns = ['def\\s+\\w+\\s*\\(', 'class\\s+\\w+\\s*:', 'import\\s+\\w+', 'from\\s+\\w+\\s+import', ':\\s*\\n', '__\\w+__']
        score = sum((10 if re.search(pattern, code) else 0 for pattern in patterns))
    elif language_code in ('javascript', 'typescript'):
        patterns = ['function\\s+\\w+\\s*\\(', 'const\\s+\\w+\\s*=', 'let\\s+\\w+\\s*=', 'var\\s+\\w+\\s*=', 'import\\s+.*from', 'export\\s+', ';\\s*\\n']
        score = sum((10 if re.search(pattern, code) else 0 for pattern in patterns))
        if language_code == 'typescript':
            ts_patterns = [':\\s*\\w+', 'interface\\s+\\w+', '<\\w+>']
            score += sum((10 if re.search(pattern, code) else 0 for pattern in ts_patterns))
    else:
        score = 0
    total_possible = 60 if language_code == 'typescript' else 60
    normalized = min(1.0, score / total_possible)
    return normalized