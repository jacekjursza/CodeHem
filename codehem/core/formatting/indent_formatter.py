from .formatter import BaseFormatter

class IndentFormatter(BaseFormatter):
    """Formatter for indentation-based languages."""

    def apply_indentation(self, code: str, base_indent: str) -> str:
        dedented = self.dedent(code)
        return super().apply_indentation(dedented, base_indent)

    def format_code(self, code: str) -> str:
        code = code.strip()
        code = self._fix_spacing(code)
        return code
