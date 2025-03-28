"""
Base manipulator for TypeScript-specific manipulators.
"""
import logging
import re
from typing import Optional
from codehem.core.template_manipulator import TemplateManipulator
from codehem.core.formatting.formatter import BaseFormatter
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

class TypeScriptManipulatorBase(TemplateManipulator):
    """Base class for TypeScript-specific manipulators."""
    LANGUAGE_CODE = 'typescript'
    COMMENT_MARKERS = ['//']
    DECORATOR_MARKERS = ['@']

    def __init__(self, element_type: CodeElementType=None, formatter: BaseFormatter=None, extraction_service=None):
        """Initialize TypeScript manipulator with appropriate formatter."""
        if formatter is None:
            try:
                from codehem.languages.lang_typescript.formatting.typescript_formatter import TypeScriptFormatter
                formatter = TypeScriptFormatter()
            except Exception as e:
                logger.warning(f'Could not get TypeScriptFormatter: {e}')
                
        super().__init__(language_code='typescript', element_type=element_type, 
                        formatter=formatter, extraction_service=extraction_service)