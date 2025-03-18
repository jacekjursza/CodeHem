# Adding Support for a New Language in CodeHem

This guide explains how to add support for a new programming language in CodeHem.

## Overview

CodeHem is designed to be extendable to support multiple programming languages. To add support for a new language, you'll need to implement several components:

1. **Language Strategy**: Defines language-specific operations
2. **Code Finder**: Implements code element location for the language
3. **Code Manipulator**: Implements code manipulation operations
4. **Formatter**: Handles code formatting for the language

## Step 1: Create a Language Strategy

Create a new file in the `strategies` directory for your language. Use the following template:

```python
"""
[Language]-specific implementation of the language strategy.
"""
import re
from typing import Tuple, List, Dict, Any, Optional
from tree_sitter import Node
from .language_strategy import LanguageStrategy

class YourLanguageStrategy(LanguageStrategy):
    """
    [Language]-specific implementation of the language strategy.
    """
    
    @property
    def language_code(self) -> str:
        return "yourlanguage"
    
    @property
    def file_extensions(self) -> List[str]:
        return [".yourlang", ".yl"]
    
    def is_class_definition(self, line: str) -> bool:
        # Implement for your language
        pass
    
    def is_function_definition(self, line: str) -> bool:
        # Implement for your language
        pass
    
    def is_method_definition(self, line: str) -> bool:
        # Implement for your language
        pass
    
    def extract_method_name(self, method_line: str) -> Optional[str]:
        # Implement for your language
        pass
    
    def extract_class_name(self, class_line: str) -> Optional[str]:
        # Implement for your language
        pass
    
    def extract_function_name(self, function_line: str) -> Optional[str]:
        # Implement for your language
        pass
    
    def fix_special_characters(self, content: str, xpath: str) -> Tuple[str, str]:
        # Implement for your language
        pass
    
    def adjust_indentation(self, code: str, indent_level: int) -> str:
        # Implement for your language
        pass
    
    def get_default_indentation(self) -> str:
        # Return default indentation for your language
        pass
    
    def is_method_of_class(self, method_node: Node, class_name: str, code_bytes: bytes) -> bool:
        # Implement for your language
        pass
Register your strategy in `strategies/__init__.py`:


# Add to STRATEGIES dict
STRATEGIES["yourlanguage"] = YourLanguageStrategy
```

## Step 2: Create a Code Finder

Create a new file in the `finder/lang` directory for your language. Use the following template:

```python
from typing import Tuple, List, Optional
from tree_sitter import Query, Node
from finder.base import CodeFinder
from languages import YOUR_LANGUAGE  # Add this to languages.py

class YourLanguageCodeFinder(CodeFinder):
    language = 'yourlanguage'

    def find_function(self, code: str, function_name: str) -> Tuple[int, int]:
        # Implement for your language
        pass

    def find_class(self, code: str, class_name: str) -> Tuple[int, int]:
        # Implement for your language
        pass

    def find_method(self, code: str, class_name: str, method_name: str) -> Tuple[int, int]:
        # Implement for your language
        pass

    def find_property(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        # Implement for your language
        pass

    def find_imports_section(self, code: str) -> Tuple[int, int]:
        # Implement for your language
        pass

    def find_properties_section(self, code: str, class_name: str) -> Tuple[int, int]:
        # Implement for your language
        pass

    def get_classes_from_code(self, code: str) -> List[Tuple[str, Node]]:
        # Implement for your language
        pass

    def get_methods_from_code(self, code: str) -> List[Tuple[str, Node]]:
        # Implement for your language
        pass

    def get_methods_from_class(self, code: str, class_name: str) -> List[Tuple[str, Node]]:
        # Implement for your language
        pass

    def has_class_method_indicator(self, method_node: Node, code_bytes: bytes) -> bool:
        # Implement for your language
        pass

    # Optional overrides for additional functionality
Register your finder in `finder/factory.py`:


# Update get_code_finder function
def get_code_finder(language: str) -> CodeFinder:
    if language.lower() == 'python':
        return PythonCodeFinder()
    elif language.lower() in ['typescript', 'javascript']:
        return TypeScriptCodeFinder()
    elif language.lower() == 'yourlanguage':
        return YourLanguageCodeFinder()
    else:
        raise ValueError(f'Unsupported language: {language}')
```

## Step 3: Create a Code Manipulator

Create a new file in the `manipulator/lang` directory for your language. Use the following template:


class YourLanguageCodeManipulator(BaseCodeManipulator):
    """[Language]-specific code manipulator that handles [Language]'s syntax requirements."""

    def __init__(self):
        super().__init__('yourlanguage')

    # Override methods as needed for language-specific behavior
    def fix_special_characters(self, content: str, xpath: str) -> tuple[str, str]:
        # Implement for your language
        pass

    def fix_class_method_xpath(self, content: str, xpath: str, file_path: str=None) -> tuple[str, dict]:
        # Implement for your language
        pass
Register your manipulator in `manipulator/factory.py`:


# Update get_code_manipulator function
def get_code_manipulator(language: str) -> Optional[AbstractCodeManipulator]:
    language = language.lower()
    if language == 'python':
        return PythonCodeManipulator()
    elif language in ['javascript', 'typescript']:
        return TypeScriptCodeManipulator()
    elif language == 'yourlanguage':
        return YourLanguageCodeManipulator()
    return None
```

## Step 4: Create a Formatter

Create a new file in the `formatting` directory for your language. Use the following template:

```python
"""
[Language]-specific code formatter.
"""
import re
from typing import List, Tuple, Optional
from .formatter import CodeFormatter

class YourLanguageFormatter(CodeFormatter):
    """
    [Language]-specific code formatter.
    Handles [Language]'s indentation rules and common patterns.
    """
    
    def __init__(self, indent_size: int = 4):  # Adjust default as appropriate
        """
        Initialize a [Language] formatter.
        
        Args:
            indent_size: Number of spaces for each indentation level (default: 4)
        """
        super().__init__(indent_size)
    
    def format_code(self, code: str) -> str:
        # Implement for your language
        pass
    
    def format_class(self, class_code: str) -> str:
        # Implement for your language
        pass
    
    def format_method(self, method_code: str) -> str:
        # Implement for your language
        pass
    
    def format_function(self, function_code: str) -> str:
        # Implement for your language
        pass
    
    def _fix_spacing(self, code: str) -> str:
        # Implement for your language
        pass
```

Register your formatter in `formatting/__init__.py`:


# Update get_formatter function
def get_formatter(language: str) -> CodeFormatter:
    language = language.lower()
    
    if language == 'python':
        return PythonFormatter()
    elif language in ['typescript', 'javascript']:
        return TypeScriptFormatter()
    elif language == 'yourlanguage':
        return YourLanguageFormatter()
    else:
        # Default to a basic formatter for unsupported languages
        return CodeFormatter()
```

## Step 5: Update Language Registry

Update `languages.py` to include your language:

1. Add the tree-sitter parser for your language
2. Add your language to the `LANGUAGES` dictionary
3. Update `FILE_EXTENSIONS` to map your language's file extensions

## Testing Your Implementation

Create tests in the `tests/yourlanguage` directory to verify your implementation:

1. Test the language finder
2. Test the language manipulator
3. Test formatting
4. Test the language strategy

## Examples

For examples, refer to the existing implementations for Python and TypeScript.