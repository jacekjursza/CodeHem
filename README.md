# CodeHem

CodeHem is a language-agnostic library designed for sophisticated querying and manipulation of source code. 
It provides a high-level interface to effortlessly navigate, analyze, and modify code elements such as functions, 
classes, methods, and properties across multiple programming languages, including Python, JavaScript, and TypeScript.

## Key Features

- **Advanced Code Querying**: Easily locate functions, classes, methods, properties, imports, and more within your source code, using a uniform, intuitive API.
- **Powerful Code Manipulation**: Replace, add, or remove functions, methods, classes, properties, or entire code sections with minimal effort.
- **Syntax-aware Operations**: Ensures accurate manipulation preserving syntax integrity through the `tree-sitter` parser.
- **Language Detection**: Automatically identifies the programming language based on file extensions or code analysis.

## Supported Languages

- Python
- JavaScript / TypeScript (including TSX)

## Project Structure

```
CodeHem/
├── finder/
│   ├── base.py                   # Abstract base class for querying code elements
│   ├── factory.py               # Factory for creating code finders
│   └── lang/
│       ├── python_code_finder.py
│       └── typescript_code_finder.py
│
├── manipulator/
│   ├── abstract.py               # Abstract interface for code manipulators
│   ├── base.py                   # Base implementation
│   ├── factory.py                # Factory for manipulators
│   └── lang/
│       ├── python_manipulator.py
│       └── typescript_manipulator.py
│
├── language_handler.py           # High-level language handling interface (LangHem)
├── languages.py                  # Language definitions and parsers
└── utils/
    └── logs.py                   # Logging utilities
```

## Installation

Ensure Python 3.7 or later is installed, then:

```bash
pip install -r requirements.txt
```

Dependencies include `tree-sitter` and language-specific parsers.

## Usage Example

### Querying Code

```python
from finder.factory import get_code_finder

finder = get_code_finder('python')
code = '''
class Example:
    def greet(self):
        print("Hello")
'''

# Find method location
start, end = finder.find_method(code, 'ExampleClass', 'my_method')
print(f'Method found from line {start} to {end_line}')
```

### Manipulating Code

```python
from manipulator.factory import get_code_manipulator

manipulator = get_code_manipulator('python')

original_code = '''
def greet():
    print("Hello")
'''

new_function = '''
def greet():
    print("Hello, World!")
'''

modified_code = manipulator.replace_function(original_code, 'greet', new_function)
```

## Contributing

We warmly welcome contributions, whether it's through reporting issues, suggesting enhancements, or submitting pull requests. Feel free to participate!

## License

This project is licensed under the MIT license. See `LICENSE` for details.