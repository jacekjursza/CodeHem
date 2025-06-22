"""
TypeScript post-processor package.
This is a compatibility wrapper to avoid circular imports.
The actual implementation is in languages.lang_typescript.typescript_post_processor.
"""
# Import the actual implementation from the languages module
from codehem.languages.lang_typescript.typescript_post_processor import TypeScriptExtractionPostProcessor as TypeScriptPostProcessor

__all__ = ['TypeScriptPostProcessor']
