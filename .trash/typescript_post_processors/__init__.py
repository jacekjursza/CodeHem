"""
TypeScript/JavaScript-specific post-processor package.

This package contains post-processor implementations for TypeScript/JavaScript code,
responsible for transforming raw extraction data into structured CodeElement objects
with proper relationships.
"""

from .post_processor import TypeScriptPostProcessor

__all__ = ["TypeScriptPostProcessor"]
