import os
import pathlib
import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class CodeExample:
    """Representation of code example with metadata for tests."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def class_name(self) -> Optional[str]:
        """Get the class name from metadata."""
        return self.metadata.get("class_name")
    
    @property
    def method_name(self) -> Optional[str]:
        """Get the method name from metadata."""
        return self.metadata.get("method_name")
    
    @property
    def property_name(self) -> Optional[str]:
        """Get the property name from metadata."""
        return self.metadata.get("property_name")
    
    @property
    def function_name(self) -> Optional[str]:
        """Get the function name from metadata."""
        return self.metadata.get("function_name")
    
    @property
    def expected_start_line(self) -> Optional[int]:
        """Get the expected start line from metadata."""
        return self.metadata.get("start_line")
    
    @property
    def expected_end_line(self) -> Optional[int]:
        """Get the expected end line from metadata."""
        return self.metadata.get("end_line")
    
    @property
    def include_extra(self) -> bool:
        """Get if extra elements should be included."""
        return self.metadata.get("include_extra", False)

class TestHelper:
    """Helper for loading and managing code examples."""
    
    @staticmethod
    def fixtures_path() -> pathlib.Path:
        """Return the path to the fixtures directory."""
        # Find the tests directory
        current_file = pathlib.Path(__file__).resolve()
        test_dir = current_file.parent.parent  # helpers directory is within tests
        
        return test_dir / "fixtures"
    
    @staticmethod
    def ensure_fixtures_directory(language="python", category=None) -> pathlib.Path:
        """
        Ensure the fixtures directory exists.
        
        Args:
            language: Programming language (python, typescript, etc.)
            category: Example category (property, class, function)
            
        Returns:
            Path to the created directory
        """
        fixtures_path = TestHelper.fixtures_path()
        
        # Building path to the example directory
        example_dir = fixtures_path / language
        if category:
            example_dir = example_dir / category
        
        # Create directories if they don't exist
        example_dir.mkdir(parents=True, exist_ok=True)
        
        return example_dir

    @staticmethod
    def load_example(filename, language='python', category=None) -> CodeExample:
        """
        Load a code example from file.

        Args:
        filename: Example file name
        language: Programming language (python, typescript, etc.)
        category: Example category (property, class, function)

        Returns:
        CodeExample object
        """
        fixtures_path = TestHelper.fixtures_path()
        example_path = fixtures_path / language
        if category:
            example_path = example_path / category
        example_path = example_path / filename
        if not example_path.exists():
            raise FileNotFoundError(f'Example file not found: {example_path}')
        with open(example_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try loading metadata from both possible paths
        metadata = {}

        # Construct both possible metadata paths
        metadata_path_with_py = example_path.parent / f"{example_path.name}.metadata.json"
        metadata_path_without_py = example_path.with_suffix('.metadata.json')

        # Try both paths
        for path in [metadata_path_with_py, metadata_path_without_py]:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    break  # Successfully loaded metadata, no need to try the next path
                except Exception as e:
                    print(f"Error loading metadata from {path}: {e}")

        return CodeExample(content=content, metadata=metadata)
    
    @staticmethod
    def create_example(content, **metadata) -> CodeExample:
        """Create a code example with content and metadata."""
        return CodeExample(content=content, metadata=metadata)
    
    @staticmethod
    def save_example(example, filename, language="python", category=None) -> None:
        """
        Save a code example to file.
        
        Args:
            example: CodeExample to save
            filename: Target filename
            language: Programming language
            category: Example category
        """
        example_dir = TestHelper.ensure_fixtures_directory(language, category)
        
        # Save code
        example_path = example_dir / filename
        with open(example_path, "w", encoding="utf-8") as f:
            f.write(example.content)
        
        # Save metadata if present
        if example.metadata:
            metadata_path = example_path.with_suffix(".metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(example.metadata, f, indent=2)
    
    @staticmethod
    def list_examples(language="python", category=None) -> list:
        """
        List all available examples.
        
        Args:
            language: Programming language
            category: Optional category filter
            
        Returns:
            List of example filenames
        """
        fixtures_path = TestHelper.fixtures_path()
        
        # Building path to the examples directory
        examples_dir = fixtures_path / language
        if category:
            examples_dir = examples_dir / category
        
        if not examples_dir.exists():
            return []
        
        # List all .py files (excluding metadata files)
        return [f.name for f in examples_dir.glob("*.py") if not f.name.endswith(".metadata.py")]