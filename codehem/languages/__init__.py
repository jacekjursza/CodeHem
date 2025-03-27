"""
Language detection and service management.
"""
from typing import List, Optional, Any
import re
import logging
from codehem.core.registry import registry
from codehem.core.service import LanguageService

logger = logging.getLogger(__name__)

def get_language_service(language_code: str) -> Optional[LanguageService]:
    """Get language service for the specified language code."""
    return registry.get_language_service(language_code.lower())

def get_language_service_for_file(file_path: str) -> Optional[LanguageService]:
    """Get language service for the specified file based on its extension."""
    import os
    _, ext = os.path.splitext(file_path)
    if not ext:
        return None
    
    # Try to get language service based on file extension
    for language_code in registry.get_supported_languages():
        service = registry.get_language_service(language_code)
        if service and ext.lower() in service.file_extensions:
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
    # Use all available detectors
    for language_code in registry.get_supported_languages():
        detector = registry.get_language_detector(language_code)
        if detector:
            confidence = detector.detect_confidence(code)
            logger.debug(f"Language detection confidence for {language_code}: {confidence}")
            if confidence > 0:
                results.append((language_code, confidence))
    
    if not results:
        logger.debug("No language detected")
        return None
    
    # Sort by confidence score
    results.sort(key=lambda x: x[1], reverse=True)
    logger.debug(f"Best language match: {results[0][0]} with confidence {results[0][1]}")
    
    # Use the language with the highest confidence if it's above a threshold
    if results[0][1] > 0.5:
        return get_language_service(results[0][0])
    
    # Fallback to basic pattern matching
    if re.search('def\\s+\\w+\\s*\\(', code) and re.search(':\\s*\\n', code):
        return get_language_service('python')
    elif re.search('function\\s+\\w+\\s*\\(', code) or re.search(':\\s*\\w+', code):
        return get_language_service('typescript')
    
    return None

def get_supported_languages() -> List[str]:
    """Get a list of all supported language codes."""
    return registry.get_supported_languages()