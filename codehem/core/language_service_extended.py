"""
Extended language service with orchestration support.

This module extends the LanguageService class to support the new component-based
architecture, adding orchestrator management.
"""

import logging
from typing import Dict, Optional, TYPE_CHECKING

from codehem.core.language_service import LanguageService
from codehem.core.components.interfaces import IExtractionOrchestrator

if TYPE_CHECKING:
    from codehem.models.code_element import CodeElementsResult

logger = logging.getLogger(__name__)

class ExtendedLanguageService(LanguageService):
    """
    Extended language service with orchestrator support.
    
    This class extends the base LanguageService to support the new component-based
    architecture, adding orchestrator management.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the extended language service."""
        super().__init__(*args, **kwargs)
        self._orchestrator_instance: Optional[IExtractionOrchestrator] = None
    
    def get_orchestrator(self) -> Optional[IExtractionOrchestrator]:
        """
        Get the extraction orchestrator for this language.
        
        Returns:
            The extraction orchestrator or None if not available
        """
        if self._orchestrator_instance is None:
            # Attempt to create orchestrator instance based on language
            orchestrator_class = self._get_orchestrator_class()
            if orchestrator_class:
                try:
                    # Get post processor for this language
                    post_processor = self._get_post_processor()
                    if post_processor:
                        self._orchestrator_instance = orchestrator_class(post_processor)
                        logger.debug(f"Created orchestrator instance: {self._orchestrator_instance.__class__.__name__} for {self.language_code}")
                    else:
                        logger.error(f"Cannot create orchestrator for {self.language_code} - no post processor available")
                except Exception as e:
                    logger.error(f"Failed to instantiate orchestrator {orchestrator_class.__name__} for {self.language_code}: {e}", exc_info=True)
            else:
                logger.warning(f"No orchestrator class found for language {self.language_code}")
        
        return self._orchestrator_instance
    
    def _get_orchestrator_class(self):
        """Get the orchestrator class for this language."""
        # Import here to avoid circular imports
        if self.language_code == 'python':
            from codehem.core.components.python.orchestrator import PythonExtractionOrchestrator
            return PythonExtractionOrchestrator
        elif self.language_code == 'typescript':
            # Add TypeScript orchestrator import when available
            # from codehem.core.components.typescript.orchestrator import TypeScriptExtractionOrchestrator
            # return TypeScriptExtractionOrchestrator
            logger.warning(f"TypeScript orchestrator not yet implemented")
            return None
        else:
            logger.warning(f"No orchestrator class known for language {self.language_code}")
            return None
    
    def _get_post_processor(self):
        """Get the post processor for this language."""
        # Use existing post processor from language config
        lang_config = self._get_language_config()
        if not lang_config:
            return None
        
        post_processor_class = lang_config.get('post_processor_class')
        if not post_processor_class:
            return None
        
        try:
            post_processor = post_processor_class()
            logger.debug(f"Created post processor instance: {post_processor.__class__.__name__} for {self.language_code}")
            return post_processor
        except Exception as e:
            logger.error(f"Failed to instantiate post processor {post_processor_class.__name__} for {self.language_code}: {e}", exc_info=True)
            return None
    
    def _get_language_config(self) -> Optional[Dict]:
        """Get the language configuration from registry."""
        from codehem.core.registry import registry
        return registry.get_language_config(self.language_code)
