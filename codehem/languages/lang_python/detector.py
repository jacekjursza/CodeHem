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

        # Strong indicators (high scores)
        strong_patterns = [
            "def\\s+\\w+\\s*\\(",  # Function definition
            "class\\s+\\w+\\s*:",  # Class definition
        ]

        # Medium indicators (medium scores)
        medium_patterns = [
            "import\\s+\\w+",  # Import statement
            "from\\s+\\w+\\s+import",  # From import
            ":\\s*\\n",  # Block indicator
            "__\\w+__",  # Dunder methods/attributes
            "@\\w+",  # Decorators
        ]

        # Weak indicators (low scores)
        weak_patterns = [
            "#.*?\\n",  # Comments
            '""".*?"""',  # Docstrings (multiline)
            "'''.*?'''",  # Docstrings (multiline, alt)
        ]

        # Anti-patterns (negative scores)
        anti_patterns = [
            "{\\s*\\n",  # JS/TS block start
            "function\\s+\\w+\\s*\\(",  # JS function
            "var\\s+\\w+\\s*=",  # JS variable
            "let\\s+\\w+\\s*=",  # JS variable
            "const\\s+\\w+\\s*=",  # JS variable
        ]

        score = 0
        max_score = (
            len(strong_patterns) * 20
            + len(medium_patterns) * 10
            + len(weak_patterns) * 5
        )

        # Calculate score
        for pattern in strong_patterns:
            if re.search(pattern, code, re.DOTALL):
                score += 20

        for pattern in medium_patterns:
            if re.search(pattern, code, re.DOTALL):
                score += 10

        for pattern in weak_patterns:
            if re.search(pattern, code, re.DOTALL):
                score += 5

        for pattern in anti_patterns:
            if re.search(pattern, code):
                score -= 15

        # Special case for minimal function definitions
        if re.search("def\\s+\\w+\\s*\\([^)]*\\)\\s*:", code):
            score += 25  # Extra boost for definitive Python construct

        # Normalize score between 0 and 1, with a minimum threshold of 0.3 for minimal code
        confidence = max(0.0, min(1.0, score / max_score))

        # For very small snippets that match Python syntax, set a minimum confidence
        if len(code.strip()) < 50 and score > 0:
            confidence = max(confidence, 0.6)

        return confidence
