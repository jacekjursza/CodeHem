# Standard Directory Structure for Language Components

This document outlines the standardized directory structure for language-specific components in the CodeHem library. Each supported language should follow this structure to ensure consistency and maintainability.

## Overview Structure

```
/codehem/languages/lang_<language>/
├── __init__.py                     # Initialization and component exports
├── components/                     # Directory with components implementing interfaces
│   ├── __init__.py                 # Initialization and component registration
│   ├── parser.py                   # ICodeParser implementation
│   ├── navigator.py                # ISyntaxTreeNavigator implementation
│   ├── extractor.py                # IElementExtractor implementation
│   ├── orchestrator.py             # IExtractionOrchestrator implementation
│   ├── post_processor.py           # IPostProcessor implementation
│   └── formatter.py                # IFormatter implementation
├── config.py                       # Language-specific configuration
├── detector.py                     # Language detection implementation
├── service.py                      # Language service implementation
├── extractors/                     # Element-type specific extractors
│   ├── __init__.py
│   └── [element_type]_extractor.py
├── manipulator/                    # Code manipulators
│   ├── __init__.py
│   ├── base.py                     # Base manipulator class
│   └── [element_type]_handler.py  
├── formatting/                     # Code formatting (legacy, will be moved to components)
│   ├── __init__.py
│   └── formatter.py
└── type_[element_type].py          # Element type descriptors
```

## Components Description

### Core Components (`components/` directory)

These components implement the core interfaces defined in `codehem/core/components/interfaces.py` and `codehem/core/components/extended_interfaces.py`:

1. **Parser (`parser.py`)**: Implements `ICodeParser`.
   - Responsible for parsing source code into syntax trees using tree-sitter.
   - Each language has its own parser implementation.

2. **Navigator (`navigator.py`)**: Implements `ISyntaxTreeNavigator`.
   - Provides methods for navigating and querying syntax trees.
   - Handles language-specific tree-sitter queries.

3. **Extractor (`extractor.py`)**: Implements `IElementExtractor`.
   - Extracts various code elements from syntax trees.
   - Coordinates with element-type specific extractors in the `extractors/` directory.

4. **Orchestrator (`orchestrator.py`)**: Implements `IExtractionOrchestrator`.
   - Coordinates the entire extraction process.
   - Uses the parser, navigator, and extractor to extract code elements.
   - Passes raw extraction results to the post-processor.

5. **Post-processor (`post_processor.py`)**: Implements `IPostProcessor`.
   - Transforms raw extraction results into structured `CodeElement` objects.
   - Handles parent-child relationships between elements.

6. **Formatter (`formatter.py`)**: Implements `IFormatter`.
   - Handles code formatting and indentation for various element types.
   - Provides methods for normalizing indentation and applying indentation.

### Language Service (`service.py`)

The language service acts as a facade for all language-specific components, providing a unified interface for:

- Extracting code elements
- Finding elements by type, name, and parent
- Getting text by XPath expression
- Detecting element types
- Accessing all language-specific components

### Configuration (`config.py`)

Contains language-specific configuration:

- Element type descriptors registration
- Language detection patterns
- File extensions
- Other language-specific settings

### Detector (`detector.py`)

Implements the language detector interface:

- Uses patterns, keywords, and heuristics to determine if code is written in the language
- Returns a confidence score for detection

### Element Type Descriptors (`type_*.py`)

Separate files for each element type (class, function, method, etc.):

- Define patterns for tree-sitter queries
- Define patterns for regex matching
- Configure custom extraction logic if needed

### Manipulators (`manipulator/` directory)

Implement code manipulation operations:

- Adding new elements
- Removing elements
- Replacing elements
- Formatting elements

### Extractors (`extractors/` directory)

Specialized extractors for specific element types:

- Class extractor
- Function extractor
- Method extractor
- Property extractor
- Import extractor
- Etc.

## Registration Pattern

All language components should be registered with the global registry in their respective `__init__.py` files using decorators:

```python
@registry.register_component('parser', 'python', PythonCodeParser)
@registry.register_component('navigator', 'python', PythonSyntaxTreeNavigator)
@registry.register_component('extractor', 'python', PythonElementExtractor)
@registry.register_component('post_processor', 'python', PythonPostProcessor)
@registry.register_component('orchestrator', 'python', PythonExtractionOrchestrator)
@registry.register_component('formatter', 'python', PythonFormatter)
@registry.register_component('detector', 'python', PythonLanguageDetector)
@registry.register_component('service', 'python', PythonLanguageService)
```

Or direct registry calls:

```python
registry.register_component('parser', 'python', PythonCodeParser)
registry.register_component('navigator', 'python', PythonSyntaxTreeNavigator)
# etc.
```

## Implementation Guidelines

1. Each language must implement all core interfaces to ensure consistent behavior.
2. Language-specific components should be placed in their respective directories.
3. Class names should include the language name as a prefix (e.g., `PythonCodeParser`).
4. Components should handle language-specific edge cases and quirks.
5. Error handling should use the `handle_extraction_errors` decorator when appropriate.
6. Logging should be used consistently throughout the components.
7. Code should be well-documented with clear docstrings.
