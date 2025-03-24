import re
from typing import List

from codehem.core.detector import BaseLanguageDetector
from codehem.core.registry import language_detector


@language_detector
class PythonLanguageDetector(BaseLanguageDetector):
    """Python-specific language detector."""

    @property
    def language_code(self) -> str:
        return 'python'

    @property
    def file_extensions(self) -> List[str]:
        return ['.py']

    def detect_confidence(self, code: str) -> float:
        """Calculate confidence that the code is Python."""
        if not code.strip():
            return 0.0
        patterns = ['def\\s+\\w+\\s*\\(', 'class\\s+\\w+\\s*:', 'import\\s+\\w+', 'from\\s+\\w+\\s+import', ':\\s*\\n', '__\\w+__', '#.*?\\n', '""".*?"""', '@\\w+']
        score = 0
        max_score = len(patterns) * 10
        for pattern in patterns:
            if re.search(pattern, code, re.DOTALL):
                score += 10
        non_python = ['{\\s*\\n', 'function\\s+\\w+\\s*\\(', 'var\\s+\\w+\\s*=', 'let\\s+\\w+\\s*=', 'const\\s+\\w+\\s*=']
        for pattern in non_python:
            if re.search(pattern, code):
                score -= 15
        normalized = max(0.0, min(1.0, score / max_score))
        return normalized
