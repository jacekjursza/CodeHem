"""
Component architecture for CodeHem.

This package contains the components that make up the refactored architecture
of CodeHem. The components are organized according to the principle of separation
of concerns, with each component responsible for a specific aspect of the
code extraction and manipulation process.
"""

from codehem.core.components.interfaces import (
    ICodeParser, 
    ISyntaxTreeNavigator, 
    IElementExtractor,
    IPostProcessor,
    IExtractionOrchestrator
)

from codehem.core.components.base_implementations import (
    BaseCodeParser,
    BaseSyntaxTreeNavigator,
    BaseElementExtractor,
    BaseExtractionOrchestrator
)


__all__ = [
    'ICodeParser',
    'ISyntaxTreeNavigator',
    'IElementExtractor',
    'IPostProcessor',
    'IExtractionOrchestrator',
    'BaseCodeParser',
    'BaseSyntaxTreeNavigator',
    'BaseElementExtractor',
    'BaseExtractionOrchestrator'
]
