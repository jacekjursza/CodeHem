"""
Post-processors for CodeHem component architecture.

This package contains post-processor components that transform raw extraction data
into structured CodeElement objects with proper relationships.
"""

from codehem.core.post_processors.factory import PostProcessorFactory

__all__ = [
    'PostProcessorFactory',
]
