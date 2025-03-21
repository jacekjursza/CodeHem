# CodeHem

CodeHem is a language-agnostic library designed for sophisticated querying and manipulation of source code. 
It provides a high-level interface to effortlessly navigate, analyze, and modify code elements such as functions, 
classes, methods, and properties across multiple programming languages, including Python, JavaScript, and TypeScript.

## Key Features

- **Advanced Code Querying**: Easily locate functions, classes, methods, properties, imports, and more within your source code, using a uniform, intuitive API.
- **Powerful Code Manipulation**: Replace, add, or remove functions, methods, classes, properties, or entire code sections with minimal effort.
- **Syntax-aware Operations**: Ensures accurate manipulation preserving syntax integrity through the `tree-sitter` parser.
- **Language Detection**: Automatically identifies the programming language based on file extensions or code analysis.
- **Extensible Architecture**: Easily add support for new programming languages through the strategy pattern.

## Supported Languages

- Python
- JavaScript / TypeScript (including TSX)

## Project Structure

```
CodeHem/
├── ast_handler.py            # Unified interface for AST operations
├── caching/                  # Performance optimization through caching
│   ├── __init__.py
│   └── cache_manager.py
│
├── finder/                   # Code element location
│   ├── base.py               # Abstract base class for querying code elements
│   ├── factory.py            # Factory for creating code finders
│   └── lang/
│       ├── python_code_finder.py
│       └── typescript_code_finder.py
│
├── formatting/               # Code formatting system
│   ├── __init__.py
│   ├── formatter.py          # Base formatter class
│   ├── python_formatter.py   # Python-specific formatter
│   └── typescript_formatter.py # TypeScript-specific formatter
│
├── language_handler.py       # High-level language handling interface (LangHem)
├── languages.py              # Language definitions and parsers
│
├── manipulator/              # Code manipulation
│   ├── abstract.py           # Abstract interface for code manipulators
│   ├── base.py               # Base implementation
│   ├── factory.py            # Factory for manipulators
│   └── lang/
│       ├── python_manipulator.py
│       └── typescript_manipulator.py
│
├── query_builder.py          # Unified query construction
│
├── strategies/               # Strategy pattern for language-specific operations
│   ├── __init__.py
│   ├── language_strategy.py  # Abstract strategy interface
│   ├── python_strategy.py    # Python-specific strategy
│   └── typescript_strategy.py # TypeScript-specific strategy
│
├── templates/                # Templates for adding new languages
│   └── new_language_template.py
│
└── utils/
    └── logs.py               # Logging utilities
## Installation

Ensure Python 3.7 or later is installed, then:

```

Dependencies include `tree-sitter` and language-specific parsers.

## Usage Example

### Querying Code


# Create a handler for Python code
handler = LangHem('python')

code = '''
class Example:
    def greet(self):
        print("Hello")
'''

# Find method location
start, end = handler.finder.find_method(code, 'Example', 'greet')
print(f'Method found from line {start} to {end}')
```

### Manipulating Code


handler = LangHem('python')

original_code = '''
def greet():
    print("Hello")
'''

new_function = '''
def greet():
    print("Hello, World!")
'''

modified_code = handler.manipulator.replace_function(original_code, 'greet', new_function)
```


## Contributing

We warmly welcome contributions, whether it's through reporting issues, suggesting enhancements, or submitting pull requests. Feel free to participate!

## License

This project is licensed under the MIT license. See `LICENSE` for details.