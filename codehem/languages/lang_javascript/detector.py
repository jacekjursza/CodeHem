import re
from typing import List
from codehem.core.detector import BaseLanguageDetector
from codehem.core.registry import language_detector

@language_detector
class JavaScriptLanguageDetector(BaseLanguageDetector):
    """Simple heuristic detector for JavaScript code."""

    @property
    def language_code(self) -> str:
        return "javascript"

    @property
    def file_extensions(self) -> List[str]:
        return [".js", ".jsx"]

    def detect_confidence(self, code: str) -> float:
        if not code.strip():
            return 0.0
        patterns = [r"function\b", r"=>", r"\bexport\b", r"\b(var|let|const)\b"]
        matches = sum(bool(re.search(p, code)) for p in patterns)
        return min(1.0, matches / len(patterns))
