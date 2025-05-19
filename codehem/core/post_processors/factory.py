"""
Post-processor factory module.

This module provides a factory for creating language-specific post-processors.
The factory determines the appropriate post-processor based on the language identifier.
"""

import logging
from typing import Dict, Type, Any, Optional, TYPE_CHECKING

# Import base class for runtime type checking
from codehem.core.post_processors.base import LanguagePostProcessor

# Only import specific post-processors when needed 
# to avoid circular imports
if TYPE_CHECKING:
    from codehem.core.post_processors.python import PythonPostProcessor
    from codehem.languages.lang_typescript.typescript_post_processor import TypeScriptExtractionPostProcessor as TypeScriptPostProcessor

logger = logging.getLogger(__name__)


class PostProcessorFactory:
    """
    Factory for creating language-specific post-processors.
    
    This factory dynamically selects and instantiates the appropriate post-processor
    based on the provided language identifier.
    """
    
    _registry: Dict[str, str] = {}  # Maps language code to post-processor class path
    
    @classmethod
    def register(cls, language_code: str, processor_class_path: str) -> None:
        """
        Register a post-processor class path for a specific language.
        
        Args:
            language_code: The language identifier (e.g., 'python', 'typescript')
            processor_class_path: The import path of the post-processor class (e.g., 'codehem.core.post_processors.python.PythonPostProcessor')
        """
        if not language_code:
            logger.error("Cannot register post-processor with empty language code")
            return
            
        cls._registry[language_code.lower()] = processor_class_path
        logger.debug(f"Registered post-processor path '{processor_class_path}' for language '{language_code}'")
    
    @classmethod
    def get_post_processor(cls, language_code: str) -> Any:
        """
        Get a post-processor instance for the specified language.
        
        Args:
            language_code: The language identifier
            
        Returns:
            An instance of the appropriate language-specific post-processor
            
        Raises:
            ValueError: If no post-processor is registered for the specified language
        """
        if not language_code:
            error_msg = "Cannot get post-processor for empty language code"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        normalized_code = language_code.lower()
        
        # Handle JavaScript as TypeScript
        if normalized_code == "javascript":
            normalized_code = "typescript"
            logger.debug("Using TypeScript post-processor for JavaScript")
        
        processor_class_path = cls._registry.get(normalized_code)
        if not processor_class_path:
            error_msg = f"No post-processor registered for language '{language_code}'"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Dynamically import the post-processor class
        try:
            # Split into module path and class name
            module_path, class_name = processor_class_path.rsplit('.', 1)
            
            # Import the module
            module = __import__(module_path, fromlist=[class_name])
            
            # Get the class
            processor_class = getattr(module, class_name)
            
            # Check if it's a subclass of LanguagePostProcessor
            if not issubclass(processor_class, LanguagePostProcessor):
                error_msg = f"Post-processor class '{processor_class.__name__}' is not a subclass of LanguagePostProcessor"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            logger.debug(f"Creating post-processor instance for language '{language_code}'")
            return processor_class()
            
        except (ImportError, AttributeError) as e:
            error_msg = f"Failed to import post-processor class '{processor_class_path}': {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """
        Get a list of supported language codes.
        
        Returns:
            List of language codes for which post-processors are registered
        """
        return list(cls._registry.keys())


# Register built-in post-processors - use string paths to avoid direct imports
PostProcessorFactory.register("python", "codehem.core.post_processors.python.post_processor.PythonPostProcessor")
PostProcessorFactory.register("typescript", "codehem.languages.lang_typescript.typescript_post_processor.TypeScriptExtractionPostProcessor")
