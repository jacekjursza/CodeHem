"""
Main entry point for code extraction functionality.
Acts as a facade for the various extraction strategies.
"""
from typing import Dict, List, Optional, Type, Union
import os

from codehem.extractors.base import BaseExtractor
from codehem.extractors.factory import ExtractorFactory
from codehem.languages.registry import registry
from codehem.core.error_handling import handle_extraction_errors
from codehem.core.error_handling import logger

class Extractor:
    """Main extractor class that delegates to specific extractors based on language."""
    
    def __init__(self, language_code: str):
        self.language_code = language_code
        self.factory = ExtractorFactory()
        
    @classmethod
    def from_file_path(cls, file_path: str) -> 'Extractor':
        """Create an extractor for a file based on its extension."""
        _, ext = os.path.splitext(file_path)
        language_code = registry.get_language_by_extension(ext)
        if not language_code:
            raise ValueError(f"Unsupported file extension: {ext}")
        return cls(language_code)
        
    @classmethod
    def from_raw_code(cls, code: str, language_hints: List[str] = None) -> 'Extractor':
        """Create an extractor by attempting to detect the language from code."""
        # Start with hints if provided
        if language_hints:
            for lang in language_hints:
                # Try to create extractors for each type and see if they can extract anything
                temp_extractor = cls(lang)
                if temp_extractor.extract_functions(code) or temp_extractor.extract_classes(code):
                    return temp_extractor
        
        # Try all supported languages
        for lang_code in registry._languages.keys():
            temp_extractor = cls(lang_code)
            if temp_extractor.extract_functions(code) or temp_extractor.extract_classes(code):
                return temp_extractor
                
        # Default to Python if detection fails
        return cls('python')
        
    def get_extractor(self, extractor_type: str, **kwargs) -> BaseExtractor:
        """Get the appropriate extractor for the given type and language."""
        return self.factory.create_extractor(extractor_type, self.language_code)
        
    @handle_extraction_errors
    def extract_functions(self, code: str) -> List[Dict]:
        """Extract functions from the provided code."""
        extractor = self.get_extractor('function', language_code=self.language_code)
        if not extractor:
            logger.warning(f"Could not find extractor for extract_functions / {self.language_code}")
            return []
        return extractor.extract(code, {'language_code': self.language_code})
        
    @handle_extraction_errors
    def extract_classes(self, code: str) -> List[Dict]:
        """Extract classes from the provided code."""
        extractor = self.get_extractor('class', language_code=self.language_code)
        if not extractor:
            logger.warning(f"Could not find extractor for extract_classes / {self.language_code}")
            return []
        return extractor.extract(code, {'language_code': self.language_code})
        
    @handle_extraction_errors
    def extract_methods(self, code: str, class_name: Optional[str]=None) -> List[Dict]:
        """Extract methods from the provided code, optionally filtering by class."""
        extractor = self.get_extractor('method', language_code=self.language_code)
        if not extractor:
            logger.warning(f"Could not find extractor for extract_methods / {self.language_code}")
            return []
        return extractor.extract(code, {'language_code': self.language_code, 'class_name': class_name})
        
    @handle_extraction_errors
    def extract_imports(self, code: str) -> List[Dict]:
        """Extract imports from the provided code."""
        extractor = self.get_extractor('import', language_code=self.language_code)
        if not extractor:
            logger.warning(f"Could not find extractor for extract_imports / {self.language_code}")
            return []
        return extractor.extract(code, {'language_code': self.language_code})
        
    def extract_all(self, code: str) -> Dict[str, List[Dict]]:
        """Extract all code elements from the provided code."""
        return {
            'functions': self.extract_functions(code),
            'classes': self.extract_classes(code),
            'methods': self.extract_methods(code),
            'imports': self.extract_imports(code)
        }
        
    def extract_with_global_context(self, code: str) -> List[Dict]:
        """Extract code elements with global context awareness."""
        global_extractor = self.factory.create_extractor('global', self.language_code)
        return global_extractor.extract(code, {'language_code': self.language_code})