import re
from typing import List
import logging
from codehem.core.detector import BaseLanguageDetector
from codehem.core.registry import language_detector

logger = logging.getLogger(__name__)

@language_detector
class TypeScriptLanguageDetector(BaseLanguageDetector):
    """TypeScript/JavaScript language detector."""

    @property
    def language_code(self) -> str:
        return 'typescript'

    @property
    def file_extensions(self) -> List[str]:
        # Handles TS, TSX, JS, JSX
        return ['.ts', '.tsx', '.js', '.jsx']

    def detect_confidence(self, code: str) -> float:
        """Calculate confidence that the code is TypeScript or JavaScript."""
        if not code.strip():
            return 0.0

        # Strong indicators for TS/JS
        ts_strong_patterns = [
            r'\b(interface|type)\s+[A-Z]', # TS interfaces/types usually start upper
            r'\b(import|export)\s+.*\s+from\s+["\']', # ES6 modules
            r'@(Component|Injectable|NgModule|Directive|Pipe)\b', # Common Angular decorators
            r'\b(class|constructor)\b',
            r'\b(public|private|protected|readonly)\s+', # TS access modifiers/readonly
            r'\b(let|const)\s+\w+', # Modern JS variable declarations
            r'=>', # Arrow functions
            r'function\s*\(', # Function keyword
        ]
        # Weaker indicators (could appear in other languages but common in JS/TS)
        ts_weak_patterns = [
            r'{\s*\n', # Braces formatting
            r'}\s*;?', # Braces formatting
            r'\.\s*(then|catch|subscribe|map|filter|forEach)\s*\(', # Common method chaining
            r'document\.getElementById', # Browser JS
            r'console\.log', # Common logging
            r'angular\.module', # AngularJS module definition
            r'\$scope|\$http|\$q', # Common AngularJS identifiers
        ]
        # Anti-patterns (more likely in other languages like Python)
        anti_patterns = [
            r'^\s*def\s+\w+\(.*\):', # Python function definition
            r'^\s*class\s+\w+\(.*\):', # Python class definition with inheritance
            r'@property', # Python property decorator
            r'#include', # C/C++
            r'using\s+System', # C#
            r'package\s+\w+', # Java/Go
            r'func\s+\w+\(', # Go
        ]

        score = 0.0
        max_score = len(ts_strong_patterns) * 15.0 + len(ts_weak_patterns) * 5.0

        num_lines = code.count('\n')

        # Check strong patterns
        for pattern in ts_strong_patterns:
            if re.search(pattern, code):
                score += 15
                # logger.debug(f"TS Strong Match: {pattern}")

        # Check weak patterns
        for pattern in ts_weak_patterns:
            if re.search(pattern, code):
                score += 5
                # logger.debug(f"TS Weak Match: {pattern}")

        # Check anti-patterns
        for pattern in anti_patterns:
            if re.search(pattern, code):
                score -= 20 # Penalize heavily for strong indicators of other languages
                # logger.debug(f"TS Anti-Match: {pattern}")

        # Adjust score based on heuristics
        if '=>' in code and '{' in code and '}' in code: # Arrow functions are very JS/TS
             score += 10
        if 'async function' in code or 'await ' in code: # Async/await is strong indicator
             score += 10

        # Normalize score
        normalized_score = 0.0
        if max_score > 0:
             normalized_score = max(0.0, min(1.0, score / max_score))

        # Boost confidence for typical file lengths with some matches
        if 0.1 < normalized_score < 0.7 and num_lines > 10:
             normalized_score += 0.1 # Small boost if some signals exist

        # logger.debug(f"TypeScript detection score: {score}, max: {max_score}, normalized: {normalized_score}")
        return normalized_score