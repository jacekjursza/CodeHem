# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Testing
- `pytest -xv` - Run all tests with verbose output and stop on first failure
- `pytest tests/python/` - Run Python-specific tests
- `pytest tests/typescript/` - Run TypeScript-specific tests
- `pytest -k "test_name"` - Run specific test by name
- `pytest --cov=codehem` - Run tests with coverage report

### Development
- `python -m codehem detect <file>` - Detect language and show element statistics for a file
- `python -m codehem patch --file <patch> --xpath "<xpath>" --dry-run` - Preview patches before applying
- `pip install -e .` - Install package in development mode
- `pip install -e .[dev]` - Install with development dependencies

### CLI Usage
- `codehem detect src/example.py` - Language detection with element count
- `codehem patch --xpath "MyClass.method[method]" --file fix.diff --dry-run` - Patch preview

## Core Architecture

### Main Components

**CodeHem (`codehem/main.py`)** - Primary API entry point that orchestrates language services, extraction, and manipulation. Provides `extract()`, `apply_patch()`, and builder methods like `new_function()`, `new_class()`.

**Language Services (`codehem/languages/`)** - Plugin architecture with language-specific implementations:
- `lang_python/` - Python AST handling with tree-sitter
- `lang_typescript/` - TypeScript/JavaScript support  
- `lang_javascript/` - JavaScript alias to TypeScript service

**Core Services (`codehem/core/`):**
- `extraction_service.py` - Extracts code elements using XPath-like queries
- `manipulation_service.py` - Applies patches and modifications
- `workspace.py` - Repository-level indexing and element search
- `registry.py` - Component registration and initialization

**Engine (`codehem/core/engine/`):**
- `ast_handler.py` - Tree-sitter AST operations
- `xpath_parser.py` - XPath-like query parsing
- `languages.py` - Language detection and mapping

**Core Components (`codehem/core/`):**
- `extractors/` - Base extractor classes (`BaseExtractor`, `TemplateExtractor`) and common templates
- `formatting/` - Base formatters (`BaseFormatter`, `BraceFormatter`, `IndentFormatter`)
- `manipulators/` - Base manipulator classes and common manipulation logic
- `components/` - Abstract interfaces (`ICodeParser`, `ISyntaxTreeNavigator`, `IElementExtractor`)
- `post_processors/` - Base post-processor interface and factory

### Key Patterns

**XPath Queries** - Use `"ClassName.method_name[method]"` syntax to target specific code elements. The system supports queries across Python and TypeScript with uniform syntax.

**Patch API** - All modifications go through `apply_patch(xpath, new_code, mode, original_hash)` which:
- Validates hash to prevent conflicts
- Returns JSON with line statistics  
- Supports `replace`, `append`, `prepend` modes
- Thread-safe with file locking

**Plugin System** - Languages register via entry-points as `codehem.languages`. Each plugin provides:
- Language service (file detection, AST parsing)
- Formatter (indentation, spacing)  
- Extractors (element identification)
- Manipulators (code modification)

### Component Structure

Each language plugin follows this structure:
```
lang_<language>/
├── service.py          # Main language service
├── detector.py         # File type detection  
├── components/         # Language-specific implementations of core interfaces
├── extractors/         # Language-specific element extractors
├── formatting/         # Language-specific formatters extending base classes
├── manipulator/        # Language-specific code modification handlers
├── post_processors/    # Language-specific post-processing logic
└── node_patterns.json  # AST pattern definitions
```

**Error Handling (`codehem/core/error_utilities/`)** - Comprehensive error management with retry mechanisms, user-friendly formatting, and batch processing capabilities.

### Workspace Operations

The `Workspace` class provides repository-level operations:
- `Workspace.open(repo_root)` - Index all supported files
- `workspace.find(name="function_name", kind="function")` - Search indexed elements
- `workspace.apply_patch(file, xpath, new_code)` - Apply changes with conflict detection

Use workspace for large codebases to avoid re-parsing files repeatedly.

### Testing Structure

- `tests/common/` - Cross-language integration tests
- `tests/python/` - Python-specific functionality  
- `tests/typescript/` - TypeScript/JavaScript tests
- `tests/fixtures/` - Test data organized by language
- `tests/helpers/` - Shared test utilities

When adding new features, follow the existing test patterns and add fixtures for both supported languages where applicable.