"""
Language detection and service management.
"""
from typing import List, Optional, Any
import re

from codehem.core.registry import registry
from codehem.core.service import LanguageService


def get_language_service(language_code: str) -> Optional[LanguageService]:
    """Get language service for the specified language code."""
    return registry.get_language_service(language_code.lower())

def get_language_service_for_file(file_path: str) -> Optional[LanguageService]:
    """Get language service for the specified file based on its extension."""
    import os
    (_, ext) = os.path.splitext(file_path)
    if not ext:
        return None
    for service in registry.language_services.values():
        if ext.lower() in service.file_extensions:
            return service
    return None

def get_language_service_for_code(code: str) -> Optional[LanguageService]:
    """
    Attempt to detect language from code content.
    This is a heuristic approach and not 100% reliable.
    """
    if not code.strip():
        return None
    results = []
    for detector in registry.language_detectors.values():
        confidence = detector.detect_confidence(code)
        if confidence > 0:
            results.append((detector.language_code, confidence))
    if not results:
        return None
    results.sort(key=lambda x: x[1], reverse=True)
    if results[0][1] > 0.5:
        return get_language_service(results[0][0])
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
    return registry.get_supported_languages()