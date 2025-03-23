"""
Registry for language services.
"""
from typing import Dict, List, Type, Optional
from ..engine.base_language_service import BaseLanguageService

# Registry of language services
_language_services: Dict[str, Type[BaseLanguageService]] = {}

def register_language_service(language_code: str, service_class: Type[BaseLanguageService]) -> None:
    """
    Register a language service.
    
    Args:
        language_code: Language code (e.g., 'python', 'typescript')
        service_class: Language service class
    """
    _language_services[language_code.lower()] = service_class

def get_language_service(language_code: str) -> Optional[BaseLanguageService]:
    """
    Get a language service by language code.
    
    Args:
        language_code: Language code (e.g., 'python', 'typescript')
        
    Returns:
        Language service instance or None if not found
    """
    service_class = _language_services.get(language_code.lower())
    if service_class:
        return service_class()
    return None

def get_language_service_for_file(file_path: str) -> Optional[BaseLanguageService]:
    """
    Get a language service based on file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Language service instance or None if not supported
    """
    import os
    ext = os.path.splitext(file_path.lower())[1]
    
    for service_class in _language_services.values():
        service = service_class()
        if ext in service.file_extensions:
            return service
    
    return None

def get_language_service_for_code(code: str) -> Optional[BaseLanguageService]:
    """
    Get a language service based on code content.
    
    Args:
        code: Source code as string
        
    Returns:
        Language service instance or None if not supported
    """
    candidates = []
    
    for service_class in _language_services.values():
        service = service_class()
        if service.can_handle(code):
            confidence = service.get_confidence_score(code)
            candidates.append((service, confidence))
    
    if not candidates:
        return None
        
    # Sort by confidence score (highest first)
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    return candidates[0][0]

def get_supported_languages() -> List[str]:
    """
    Get a list of supported language codes.
    
    Returns:
        List of supported language codes
    """
    return list(_language_services.keys())