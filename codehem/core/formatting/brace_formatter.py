from .formatter import BaseFormatter

class BraceFormatter(BaseFormatter):
    """Formatter for brace-based languages."""

    def apply_indentation(self, code: str, base_indent: str) -> str:
        dedented = self.dedent(code)
        return super().apply_indentation(dedented, base_indent)
