"""
Helper functions for loading code examples for tests.
"""
from typing import Dict, Any, Optional
from .fixture_loader import FixtureLoader, CodeFixture

class TestHelper:
    """Helper class for test utilities."""
    
    @staticmethod
    def load_example(name: str, category: str = "general", language: str = "python", metadata: Optional[Dict[str, Any]] = None) -> CodeFixture:
        """
        Load a code example from the fixtures directory.
        
        Args:
            name: Name of the example file (without extension)
            category: Category of the example (e.g., "class", "function")
            language: Language of the example (e.g., "python", "typescript")
            metadata: Optional additional metadata
            
        Returns:
            CodeFixture instance with the loaded content
        """
        return FixtureLoader.load_fixture(language, category, name, metadata)