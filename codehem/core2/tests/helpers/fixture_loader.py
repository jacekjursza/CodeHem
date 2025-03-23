"""
Fixture loader for CodeHem tests.
"""
import os
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class CodeFixture:
    """Container for code fixture with metadata."""
    name: str
    category: str
    content: str
    expected_start_line: int = 0
    expected_end_line: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class FixtureLoader:
    """Utility for loading code fixtures from files."""
    
    @staticmethod
    def get_fixtures_dir() -> str:
        """Get the path to the fixtures directory."""
        # Base test directory
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(current_dir, "fixtures")
    
    @staticmethod
    @staticmethod
    def load_fixture(language: str, category: str, name: str, metadata: Optional[Dict[str, Any]]=None) -> CodeFixture:
        """
        Load a code fixture from the fixtures directory.

        Args:
        language: Language directory (e.g., 'python', 'typescript')
        category: Category directory (e.g., 'class', 'function')
        name: Filename without extension (fixture will add .txt extension)
        metadata: Optional metadata to associate with the fixture

        Returns:
        CodeFixture instance with the loaded content
        """
        fixtures_dir = FixtureLoader.get_fixtures_dir()
        fixture_path = os.path.join(fixtures_dir, language, category, f'{name}.txt')
        try:
            with open(fixture_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.splitlines()
            fixture_metadata = {} if metadata is None else metadata.copy()
            expected_start_line = 0
            expected_end_line = 0
            content_lines = []

            for line in lines:
                if line.startswith('## '):
                    parts = line[3:].split(':', 1)
                    if len(parts) == 2:
                        key, value = parts
                        key = key.strip().lower()
                        value = value.strip()
                        if key == 'start_line':
                            expected_start_line = int(value)
                        elif key == 'end_line':
                            expected_end_line = int(value)
                        else:
                            fixture_metadata[key] = value
                else:
                    content_lines.append(line)

            content = '\n'.join(content_lines)
            return CodeFixture(name=name, category=category, content=content, expected_start_line=expected_start_line, expected_end_line=expected_end_line, metadata=fixture_metadata)
        except FileNotFoundError:
            raise ValueError(f'Fixture not found: {fixture_path}')
