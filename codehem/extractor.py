"""
Main entry point for code extraction functionality.
Acts as a facade for the various extraction strategies.
"""

from typing import Dict, List, Optional, Any
import os
import logging
from codehem.extractors.factory import ExtractorFactory
from codehem.core.error_handling import handle_extraction_errors
from codehem.languages import (
    get_language_service_for_file,
    get_language_service_for_code,
)

logger = logging.getLogger(__name__)

class Extractor:
    """Main extractor class that delegates to specific extractors based on language."""

    def __init__(self, language_code: str):
        self.language_code = language_code
        self.factory = ExtractorFactory()

    @classmethod
    def from_file_path(cls, file_path: str) -> 'Extractor':
        """Create an extractor for a file based on its extension."""
        service = get_language_service_for_file(file_path)
        if not service:
            (_, ext) = os.path.splitext(file_path)
            raise ValueError(f'Unsupported file extension: {ext}')
        return cls(service.language_code)

    @classmethod
    def from_raw_code(cls, code: str, language_hints: List[str]=None) -> 'Extractor':
        """Create an extractor by attempting to detect the language from code."""

        # Try with language hints first
        if language_hints:
            for lang in language_hints:
                temp_extractor = cls(lang)
                if temp_extractor.extract_functions(code) or temp_extractor.extract_classes(code):
                    return temp_extractor
        
        # Auto-detect language
        service = get_language_service_for_code(code)
        if service:
            return cls(service.language_code)
            
        # Fallback to Python if nothing else works
        return cls('python')

    def get_extractor(self, extractor_type: str) -> Optional[Any]:
        """Get the appropriate extractor for the given type and language."""
        return self.factory.create_extractor(extractor_type, self.language_code)

    @handle_extraction_errors
    def extract_functions(self, code: str) -> List[Dict]:
        """Extract functions from the provided code."""
        extractor = self.get_extractor('function')
        if not extractor:
            logger.warning(f'Could not find extractor for extract_functions / {self.language_code}')
            return []
        return extractor.extract(code, {'language_code': self.language_code})

    @handle_extraction_errors
    def extract_classes(self, code: str) -> List[Dict]:
        """Extract classes from the provided code."""
        extractor = self.get_extractor('class')
        if not extractor:
            logger.warning(f'Could not find extractor for extract_classes / {self.language_code}')
            return []
        return extractor.extract(code, {'language_code': self.language_code})

    @handle_extraction_errors
    def extract_methods(self, code: str, class_name: Optional[str]=None) -> List[Dict]:
        """Extract methods from the provided code, optionally filtering by class."""
        extractor = self.get_extractor('method')
        if not extractor:
            logger.warning(f'Could not find extractor for extract_methods / {self.language_code}')
            return []
        return extractor.extract(code, {'language_code': self.language_code, 'class_name': class_name})

    @handle_extraction_errors
    def extract_imports(self, code: str) -> List[Dict]:
        """Extract imports from the provided code."""
        extractor = self.get_extractor('import')
        if not extractor:
            logger.warning(f'Could not find extractor for extract_imports / {self.language_code}')
            return []
        return extractor.extract(code, {'language_code': self.language_code})

    @handle_extraction_errors
    def extract_any(self, code, element_type: str) -> List[Dict]:
        """Extract any code element from the provided code."""
        extractor = self.get_extractor(element_type)
        return extractor.extract(code, {'language_code': self.language_code})

    def extract_all(self, code: str) -> Dict[str, List[Dict]]:
        """Extract all code elements from the provided code."""
        return {
            'functions': self.extract_functions(code), 
            'classes': self.extract_classes(code), 
            'methods': self.extract_methods(code), 
            'imports': self.extract_imports(code)
            # Decorators are now handled as children of their parent elements
        }
