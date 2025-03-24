from abc import ABC, abstractmethod
from typing import List


class BaseLanguageDetector(ABC):
    """Base class for language detection."""

    @property
    @abstractmethod
    def language_code(self) -> str:
        """Get the language code this detector is for."""
        pass

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Get file extensions associated with this language."""
        pass

    @abstractmethod
    def detect_confidence(self, code: str) -> float:
        """
        Calculate confidence level that the code is written in this language.

        Args:
            code: Source code to analyze

        Returns:
            Confidence score (0.0 to 1.0)
        """
        pass
