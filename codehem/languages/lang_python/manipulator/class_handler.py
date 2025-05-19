"""
Python class manipulator implementation.
"""
import logging
from typing import Optional
from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.core.manipulators.template_class_manipulator import TemplateClassManipulator

logger = logging.getLogger(__name__)

@manipulator
class PythonClassManipulator(TemplateClassManipulator):
    """Manipulator for Python classes."""
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.CLASS
    COMMENT_MARKERS = ['#']
    DECORATOR_MARKERS = ['@']
    