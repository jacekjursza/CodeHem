# Developer Guide

This comprehensive guide explains how to extend CodeHem, use its APIs, and develop language plugins.

## Table of Contents
1. [Core API Reference](#core-api-reference)
2. [Plugin Development](#plugin-development)
3. [Architecture Overview](#architecture-overview)
4. [Testing Guidelines](#testing-guidelines)
5. [Performance Considerations](#performance-considerations)

## Core API Reference

### CodeHem Class

The main entry point for all CodeHem operations.

#### Initialization

```python
from codehem import CodeHem

# Initialize with specific language
hem = CodeHem("python")          # Python support
hem = CodeHem("typescript")      # TypeScript/JavaScript support

# Auto-detect language from code
code = "def example(): pass"
hem = CodeHem.from_raw_code(code)

# From file path (auto-detects language)
hem = CodeHem.from_file("/path/to/file.py")
```

#### Core Methods

##### `extract(code: str) -> CodeElementsResult`

Extracts all code elements from the provided code.

```python
result = hem.extract(code)

# Access extracted elements
for cls in result.classes:
    print(f"Class: {cls.name} at line {cls.range.start_line}")
    for method in cls.methods:
        print(f"  Method: {method.name}")

for func in result.functions:
    print(f"Function: {func.name}")

for import_stmt in result.imports:
    print(f"Import: {import_stmt.name}")
```

##### `get_text_by_xpath(code: str, xpath: str, return_hash: bool = False)`

Retrieves text content for a specific XPath query.

```python
# Simple text retrieval
text = hem.get_text_by_xpath(code, "MyClass.method_name[method]")

# With hash for conflict detection
text, hash_value = hem.get_text_by_xpath(code, xpath, return_hash=True)
```

##### `apply_patch(xpath: str, new_code: str, mode: str, original_hash: str = None, dry_run: bool = False, return_format: str = "text")`

Applies modifications to code at the specified XPath location.

**Parameters:**
- `xpath`: XPath query targeting the element to modify
- `new_code`: The new code content
- `mode`: Modification mode (`"replace"`, `"append"`, `"prepend"`)
- `original_hash`: Hash of the original content for conflict detection
- `dry_run`: If True, returns a preview without applying changes
- `return_format`: Response format (`"text"` or `"json"`)

**Return Values:**

Text format:
```python
modified_code = hem.apply_patch(xpath, new_code, "replace")
```

JSON format:
```python
result = hem.apply_patch(xpath, new_code, "replace", return_format="json")
# Returns: {
#   "status": "ok",
#   "lines_added": 3,
#   "lines_removed": 1,
#   "modified_code": "...",
#   "new_hash": "abc123..."
# }
```

#### Builder Methods

##### `new_function(code: str, name: str, args: List[str], body: List[str], **kwargs)`

Creates a new function and inserts it into the code.

```python
result = hem.new_function(
    code=existing_code,
    name="calculate_sum",
    args=["numbers"],
    body=[
        "total = 0",
        "for num in numbers:",
        "    total += num", 
        "return total"
    ],
    decorators=["@staticmethod"],
    return_format="json"
)
```

##### `new_class(code: str, name: str, methods: List[Dict], **kwargs)`

Creates a new class with specified methods.

```python
result = hem.new_class(
    code=existing_code,
    name="Calculator",
    methods=[
        {
            "name": "__init__",
            "args": ["self"],
            "body": ["pass"]
        },
        {
            "name": "add",
            "args": ["self", "a", "b"],
            "body": ["return a + b"]
        }
    ],
    return_format="json"
)
```

##### `new_method(code: str, parent: str, name: str, args: List[str], body: List[str], **kwargs)`

Adds a new method to an existing class.

```python
result = hem.new_method(
    code=existing_code,
    parent="Calculator",
    name="multiply",
    args=["self", "a", "b"],
    body=["return a * b"],
    decorators=["@property"],
    return_format="json"
)
```

### Workspace Class

For repository-level operations on multiple files.

#### Initialization

```python
from codehem import CodeHem

# Open workspace (indexes all supported files)
workspace = CodeHem.open_workspace("/path/to/repository")
```

#### Methods

##### `find(name: str = None, kind: str = None, file_pattern: str = None) -> List[Tuple[str, str]]`

Searches for elements across the entire workspace.

```python
# Find all methods named 'calculate'
matches = workspace.find(name="calculate", kind="method")
for file_path, xpath in matches:
    print(f"Found in {file_path}: {xpath}")

# Find all classes
classes = workspace.find(kind="class")

# Find in specific files
python_functions = workspace.find(kind="function", file_pattern="*.py")
```

##### `apply_patch(file_path: str, xpath: str, new_code: str, **kwargs)`

Applies a patch to a specific file in the workspace.

```python
result = workspace.apply_patch(
    file_path="src/calculator.py",
    xpath="Calculator.add[method]",
    new_code="def add(self, a, b):\n    return a + b + 1",
    mode="replace",
    return_format="json"
)
```

### XPath Query Syntax

CodeHem uses XPath-like queries to target code elements:

#### Basic Patterns

```python
# Classes
"ClassName[class]"                    # Target class
"MyClass[class]"                      # Specific class named MyClass

# Methods
"ClassName.method_name[method]"       # Method in class
"Calculator.add[method]"              # Specific method

# Functions
"function_name[function]"             # Standalone function
"helper_function[function]"           # Specific function

# Properties
"ClassName.property_name[property]"   # Property in class
"User.name[property]"                # Specific property

# Static properties
"ClassName.CONSTANT[static_property]" # Static/class variable

# Imports (special case)
"imports[imports]"                    # All imports section
```

#### Advanced Patterns

```python
# TypeScript interfaces
"InterfaceName[interface]"           # Interface declaration
"User[interface]"                    # Specific interface

# Type aliases
"TypeName[type_alias]"               # Type alias
"Result[type_alias]"                 # Specific type alias

# Enums
"EnumName[enum]"                     # Enum declaration
"Status[enum]"                       # Specific enum

# Namespaces (TypeScript)
"NamespaceName[namespace]"           # Namespace
"Utils[namespace]"                   # Specific namespace
```

## Plugin Development

### Overview

CodeHem uses a plugin architecture where each language is implemented as a separate plugin. Plugins register via Python entry-points and provide language-specific implementations.

### Plugin Structure

Each language plugin follows this structure:

```
codehem_lang_<language>/
├── __init__.py
├── service.py              # Main language service
├── detector.py             # File type detection
├── components/             # Component implementations
│   ├── __init__.py
│   ├── parser.py          # Code parsing
│   ├── navigator.py       # AST navigation
│   ├── extractor.py       # Element extraction
│   └── post_processor.py  # Post-processing
├── formatting/            # Code formatting
│   ├── __init__.py
│   └── formatter.py
├── manipulator/          # Code manipulation
│   ├── __init__.py
│   └── handlers.py
├── extractors/           # Element extractors
│   ├── __init__.py
│   └── specific_extractors.py
└── node_patterns.json    # AST pattern definitions
```

### Creating a Plugin

#### 1. Use the Cookiecutter Template

```bash
pipx cookiecutter gh:codehem/codehem-lang-template
```

This creates a skeleton plugin with all necessary components.

#### 2. Define Entry Points

In your plugin's `setup.py` or `pyproject.toml`:

```toml
[project.entry-points."codehem.languages"]
java = "codehem_lang_java:JavaLanguageService"
```

#### 3. Implement Core Components

##### Language Service

```python
from codehem.core.registry import language_service
from codehem.core.components.interfaces import ILanguageService

@language_service("java")
class JavaLanguageService(ILanguageService):
    def __init__(self):
        self.file_extensions = ['.java']
        self.language_name = "java"
    
    def detect_language(self, file_path: str, content: str = None) -> bool:
        """Detect if file/content is Java."""
        return file_path.endswith('.java')
    
    def get_parser(self):
        """Return tree-sitter parser for Java."""
        # Implementation specific to Java
        pass
```

##### Component Implementations

Implement the core interfaces:

- `ICodeParser` - Parse code into AST
- `ISyntaxTreeNavigator` - Navigate and query AST
- `IElementExtractor` - Extract code elements
- `IPostProcessor` - Transform raw data to CodeElement objects

##### Formatter

```python
from codehem.core.formatting.formatter import BraceFormatter

class JavaFormatter(BraceFormatter):
    """Java-specific code formatting."""
    
    def __init__(self):
        super().__init__(
            indent_size=4,
            use_tabs=False,
            brace_style="allman"  # or "k&r"
        )
    
    def format_class(self, class_name: str, content: str) -> str:
        """Format Java class declaration."""
        return f"public class {class_name} {{\n{content}\n}}"
```

### Base Classes

CodeHem provides base classes to minimize implementation work:

#### BaseElementExtractor

```python
from codehem.core.components.base_implementations import BaseElementExtractor

class JavaElementExtractor(BaseElementExtractor):
    def __init__(self, navigator):
        super().__init__('java', navigator)
    
    def extract_classes(self, tree, code_bytes):
        """Extract Java class declarations."""
        query = """
        (class_declaration
          name: (identifier) @class_name
          body: (class_body) @body) @class_decl
        """
        return self._extract_with_query(tree, code_bytes, query)
```

#### BraceFormatter vs IndentFormatter

Choose the appropriate base formatter:

```python
# For languages with braces (Java, C++, JavaScript)
from codehem.core.formatting.formatter import BraceFormatter

class JavaFormatter(BraceFormatter):
    pass

# For languages with indentation (Python, YAML)
from codehem.core.formatting.formatter import IndentFormatter

class PythonFormatter(IndentFormatter):
    pass
```

### Testing Plugins

#### Test Structure

```
tests/
├── test_<language>_basic.py
├── test_<language>_extraction.py
├── test_<language>_manipulation.py
└── fixtures/
    └── <language>/
        ├── simple_class.txt
        ├── complex_example.txt
        └── edge_cases.txt
```

#### Test Templates

```python
import pytest
from codehem import CodeHem

class TestJavaExtraction:
    def setup_method(self):
        self.hem = CodeHem("java")
    
    def test_extract_java_class(self):
        code = """
        public class Example {
            private int value;
            
            public int getValue() {
                return value;
            }
        }
        """
        
        result = self.hem.extract(code)
        assert len(result.classes) == 1
        assert result.classes[0].name == "Example"
        assert len(result.classes[0].methods) == 1
```

## Architecture Overview

### Component Relationships

```
CodeHem (Main API)
├── LanguageService (Plugin Entry Point)
├── Components/
│   ├── Parser (AST Creation)
│   ├── Navigator (AST Traversal)
│   ├── Extractor (Element Identification)
│   └── PostProcessor (Data Transformation)
├── Formatter (Code Formatting)
└── Manipulator (Code Modification)
```

### Data Flow

1. **Detection**: Language detector identifies file type
2. **Parsing**: Parser creates AST from source code
3. **Navigation**: Navigator executes tree-sitter queries
4. **Extraction**: Extractor identifies code elements
5. **Post-processing**: PostProcessor transforms to CodeElement objects
6. **Manipulation**: Manipulator applies modifications
7. **Formatting**: Formatter ensures consistent style

### Error Handling

CodeHem provides comprehensive error handling:

```python
from codehem.core.error_handling import CodeHemError, retry_with_backoff

try:
    result = hem.apply_patch(xpath, new_code, mode="replace")
except CodeHemError as e:
    # Handle CodeHem-specific errors
    logger.error(f"CodeHem error: {e}")
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
```

## Testing Guidelines

### Test Categories

1. **Unit Tests** - Test individual components
2. **Integration Tests** - Test component interactions
3. **Language Tests** - Test language-specific functionality
4. **End-to-End Tests** - Test complete workflows

### Running Tests

```bash
# All tests
pytest -xv

# Specific language
pytest tests/python/ -v
pytest tests/typescript/ -v

# With coverage
pytest --cov=codehem --cov-report=html

# Specific test pattern
pytest -k "test_extract" -v
```

### Test Fixtures

Store test code in fixture files:

```
tests/fixtures/python/general/
├── simple_class.txt
├── complex_class.txt
├── multiple_functions.txt
└── edge_cases.txt
```

Load fixtures in tests:

```python
from tests.helpers.fixture_loader import load_fixture

def test_complex_extraction():
    code = load_fixture('python/general/complex_class.txt')
    result = hem.extract(code)
    # Assertions...
```

## Performance Considerations

### Caching Strategy

CodeHem implements multiple caching layers:

1. **AST Cache** - Parsed trees cached by code hash
2. **Query Cache** - Tree-sitter query results cached
3. **Element Cache** - Extracted elements cached

### Memory Management

```python
# For large codebases, use workspace indexing
workspace = CodeHem.open_workspace("/large/repo")

# Avoid repeatedly parsing the same files
hem = CodeHem("python")
for file_path in files:
    if not hem.is_cached(file_path):
        # Only parse if not cached
        hem.extract_from_file(file_path)
```

### Profiling

Profile extraction performance:

```python
import cProfile
from codehem import CodeHem

def profile_extraction():
    hem = CodeHem("python")
    with open("large_file.py") as f:
        code = f.read()
    
    result = hem.extract(code)
    return result

cProfile.run('profile_extraction()', 'extraction_profile.prof')
```

## Diagrams

Architecture and plugin relations are illustrated in `docs/architecture.puml`.
PlantUML renders the diagrams for the GitHub Pages site.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest -xv`
5. Submit a pull request

For plugin development, start with the cookiecutter template and follow the plugin structure guidelines above.
