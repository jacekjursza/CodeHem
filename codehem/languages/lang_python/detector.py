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
            "def\\s+\\w+\\s*\\([^)]*\\)\\s*:",  # Complete function signature with colon
        ]

        # Medium indicators (medium scores)
        medium_patterns = [
            "import\\s+\\w+",  # Import statement
            "from\\s+\\w+\\s+import",  # From import
            ":\\s*\\n",  # Block indicator
            "__\\w+__",  # Dunder methods/attributes
            "@\\w+",  # Decorators
            "pass\\b",  # Pass statement - very Python-specific
        ]

        # Weak indicators (low scores)
        weak_patterns = [
            "#.*?\\n",  # Comments
            '""".*?"""',  # Docstrings (multiline)
            "'''.*?'''",  # Docstrings (multiline, alt)
            "\\bif\\s+.+?:",  # If statements
            "\\bfor\\s+.+?:",  # For loops
            "\\bwhile\\s+.+?:",  # While loops
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

        # For minimal function definitions with pass (like 'def foo(): pass')
        if re.search("def\\s+\\w+\\s*\\([^)]*\\)\\s*:\\s*pass", code):
            score += 40  # Very strong boost for definitive minimal Python construct

        # Normalize score between 0 and 1, with a floor of 0.3 for minimal code
        normalized_score = max(0.0, min(1.0, score / max_score))

        # For very small snippets that match Python patterns, set a minimum confidence
        if len(code.strip()) < 50 and score > 0:
            return max(normalized_score, 0.7)  # Higher threshold for small snippets

        return normalized_score
