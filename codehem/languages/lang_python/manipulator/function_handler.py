"""
Python function manipulator implementation.
"""
import logging
from typing import Optional
from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.core.manipulators.template_function_manipulator import TemplateFunctionManipulator

logger = logging.getLogger(__name__)

@manipulator
class PythonFunctionManipulator(TemplateFunctionManipulator):
    """Manipulator for Python functions."""
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.FUNCTION
    COMMENT_MARKERS = ['#']
    DECORATOR_MARKERS = ['@']
    