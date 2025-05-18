from codehem.core.registry import language_service
from codehem.languages.lang_typescript.service import TypeScriptLanguageService

@language_service
class JavaScriptLanguageService(TypeScriptLanguageService):
    """JavaScript service aliasing the TypeScript implementation."""
    LANGUAGE_CODE = "javascript"
