"""
TypeScript language detector implementation.
"""
import re
from typing import List
from codehem.core.detector import BaseLanguageDetector
from codehem.core.registry import language_detector

@language_detector
class TypeScriptLanguageDetector(BaseLanguageDetector):
    """TypeScript-specific language detector."""

    @property
    def language_code(self) -> str:
        return 'typescript'

    @property
    def file_extensions(self) -> List[str]:
        return ['.ts', '.tsx']

    def detect_confidence(self, code: str) -> float:
        """Calculate confidence that the code is TypeScript."""
        if not code.strip():
            return 0.0
        
        # TypeScript specific patterns
        strong_patterns = [
            r'interface\s+\w+\s*{',
            r'type\s+\w+\s*=',
            r'\w+\s*:\s*[A-Z]\w+',
            r'import\s+{\s*[^}]+\s*}\s+from',
            r'export\s+(default\s+)?(class|interface|type|function)',
            r'<\w+>\s*\(',
            r':\s*[A-Z]\w+\[\]'
        ]
        
        medium_patterns = [
            r'const\s+\w+',
            r'let\s+\w+',
            r'function\s+\w+',
            r'=>\s*{',
            r'class\s+\w+',
            r'\/\/\s*.*?',
            r'\/\*[\s\S]*?\*\/'
        ]
        
        anti_patterns = [
            r'def\s+\w+\s*\(',
            r':\s*\n',
            r'import\s+\w+$',
            r'from\s+\w+\s+import'
        ]
        
        score = 0
        max_score = len(strong_patterns) * 20 + len(medium_patterns) * 10
        
        for pattern in strong_patterns:
            if re.search(pattern, code, re.MULTILINE):
                score += 20
                
        for pattern in medium_patterns:
            if re.search(pattern, code, re.MULTILINE):
                score += 10
                
        for pattern in anti_patterns:
            if re.search(pattern, code, re.MULTILINE):
                score -= 15
                
        normalized_score = max(0.0, min(1.0, score / max_score))
        
        # Boost for TS-specific keywords
        if re.search(r'\binterface\b|\bnamespace\b|\btype\b|\bReadonly\b|\bPartial\b|\bPick\b', code):
            normalized_score = min(1.0, normalized_score + 0.2)
            
        return normalized_score