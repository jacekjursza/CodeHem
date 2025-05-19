"""Base manipulator for TypeScript/JavaScript."""

from codehem.core.manipulators.abstract_block_manipulator import (
    AbstractBlockManipulator,
)
from codehem.core.formatting.brace_formatter import BraceFormatter
from codehem.core.registry import registry
from codehem.models.enums import CodeElementType


class TypeScriptManipulatorBase(AbstractBlockManipulator):
    """Base class for TypeScript-specific manipulators."""

    LANGUAGE_CODE = "typescript"
    COMMENT_MARKERS = ["//"]
    DECORATOR_MARKERS = ["@"]
    BLOCK_START_TOKEN = "{"

    def __init__(
        self,
        element_type: CodeElementType | None = None,
        formatter: BraceFormatter | None = None,
        extraction_service=None,
    ) -> None:
        if formatter is None:
            try:
                lang_service = registry.get_language_service("typescript")
                if lang_service and hasattr(lang_service, "formatter"):
                    formatter = lang_service.formatter
                else:
                    formatter = BraceFormatter()
            except Exception:
                formatter = BraceFormatter()
        super().__init__(
            language_code="typescript",
            element_type=element_type,
            formatter=formatter,
            extraction_service=extraction_service,
        )
