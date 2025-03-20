# CodeHem Documentation

## Overview

CodeHem is a language-agnostic library designed for sophisticated querying and manipulation of source code across multiple programming languages. It provides a high-level interface to effortlessly navigate, analyze, and modify code elements such as functions, classes, methods, and properties. The name "CodeHem" suggests code-hemming - the process of altering or adjusting code.

## Core Capabilities

- **Advanced Code Querying**: Locate functions, classes, methods, properties, imports, etc. within source code
- **Powerful Code Manipulation**: Replace, add, or remove functions, methods, classes, properties, or whole code sections
- **Syntax-aware Operations**: Preserve syntax integrity using tree-sitter parsing
- **Language Detection**: Automatically identify programming languages from file extensions or code analysis
- **Multi-language Support**: Works with Python, JavaScript, TypeScript (including TSX)

## Architecture

CodeHem follows a layered architecture with clear separation of concerns:

```
[CodeHem Main Interface]
        │
        ├── [Finder Layer] ── Language-specific Finders (Python, TypeScript)
        │
        ├── [Manipulator Layer] ── Language-specific Manipulators (Python, TypeScript)
        │
        ├── [Strategy Layer] ── Language Strategies (Python, TypeScript)
        │
        └── [Tree-sitter Integration] ── AST Handling
```

### Project Structure

```
CodeHem/
├── finder/            # Finding code elements
│   ├── base.py        # Abstract base class for code finders
│   ├── factory.py     # Factory for creating code finders
│   └── lang/          # Language-specific implementations
│       ├── python_code_finder.py
│       └── typescript_code_finder.py
│
├── manipulator/       # Manipulating code
│   ├── abstract.py    # Abstract interface 
│   ├── base.py        # Base implementation
│   ├── factory.py     # Factory for manipulators
│   └── lang/          # Language-specific implementations
│       ├── python_manipulator.py
│       └── typescript_manipulator.py
│
├── core/              # Core components
│   ├── ast_handler.py # AST handling via tree-sitter
│   ├── models.py      # Pydantic models for code elements
│   ├── languages.py   # Language definitions and parsers
│   ├── formatting/    # Code formatting utilities
│   ├── services/      # Service layer components
│   ├── strategies/    # Language-specific strategies
│   ├── caching/       # Performance optimization
│   └── utils/         # Utility functions
│
├── main.py            # Main class (CodeHem) integrating all components
└── cli.py             # Command-line interface
```

## Key Components

### 1. CodeHem (main.py)

The central class that serves as the main entry point to the library.

```python
class CodeHem:
    def __init__(self, language_code: str):
        # Initializes appropriate finders, manipulators, etc. for the specified language
        
    @classmethod
    def from_file_path(cls, file_path: str) -> 'CodeHem':
        # Creates a CodeHem instance by detecting language from file path
        
    @classmethod
    def from_raw_code(cls, code_or_path: str, check_for_file: bool=True) -> 'CodeHem':
        # Creates a CodeHem instance from raw code with language auto-detection
        
    def extract(self, code: str) -> 'CodeElementsResult':
        # Extracts code elements from source code as structured data
        
    @staticmethod
    def filter(elements: CodeElementsResult, xpath: str='') -> Optional[CodeElement]:
        # Filters code elements based on XPath-like expression
```

### 2. Finders

Responsible for locating code elements within source code. Abstract base class:

```python
class CodeFinder(ABC):
    @abstractmethod
    def find_function(self, code: str, function_name: str) -> Tuple[int, int]:
        # Returns (start_line, end_line) of function

    @abstractmethod
    def find_class(self, code: str, class_name: str) -> Tuple[int, int]:
        # Returns (start_line, end_line) of class
        
    @abstractmethod
    def find_method(self, code: str, class_name: str, method_name: str) -> Tuple[int, int]:
        # Returns (start_line, end_line) of method

    # ... more finding methods
```

### 3. Manipulators

Responsible for modifying code elements. Abstract base class:

```python
class AbstractCodeManipulator(ABC):
    @abstractmethod
    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        # Replaces a function definition with new content
    
    @abstractmethod
    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        # Replaces a class definition with new content
        
    @abstractmethod
    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        # Replaces a method in a class with new content

    # ... more manipulation methods
```

### 4. Language Strategies

Language-specific strategies for code analysis and formatting:

```python
class LanguageStrategy(ABC):
    @property
    @abstractmethod
    def language_code(self) -> str:
        # Return language code (e.g., 'python', 'typescript')
        
    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        # Return file extensions (e.g., ['.py'], ['.ts', '.tsx'])
        
    @abstractmethod
    def is_class_definition(self, line: str) -> bool:
        # Check if a line is a class definition
        
    # ... more language-specific methods
```

### 5. AST Handler

Provides a unified interface for tree-sitter operations:

```python
class ASTHandler:
    def __init__(self, language: str):
        # Initialize handler for a specific language
        
    def parse(self, code: str) -> Tuple[Node, bytes]:
        # Parse source code into an AST
        
    def execute_query(self, query_string: str, root: Node, code_bytes: bytes) -> List[Tuple[Node, str]]:
        # Execute a tree-sitter query on an AST
        
    # ... more AST handling methods
```

### 6. Models

Pydantic models for representing code elements:

```python
class CodeElement(BaseModel):
    type: CodeElementType
    name: str
    content: str
    range: Optional[CodeRange] = None
    parent_name: Optional[str] = None
    value_type: Optional[str] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)
    children: List['CodeElement'] = Field(default_factory=list)
    
    # Properties for easy access to element characteristics
```

## Core Workflows

### 1. Language Detection Workflow

```
Input: Code or file path
┌───────────────────┐
│ Check if file     │
│ exists and try to │
│ load it          │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Analyze code with │
│ each language    │
│ finder            │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Calculate         │
│ confidence score  │
│ for each match    │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Return CodeHem     │
│ instance with the  │
│ best match        │
└───────────────────┘
```

### 2. Code Extraction Workflow

```
Input: Source code
┌───────────────────┐
│ Parse code with   │
│ tree-sitter       │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Extract imports   │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Extract classes   │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ For each class:   │
│ Extract methods   │
│ and properties    │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Extract standalone│
│ functions         │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Return structured │
│ CodeElementsResult│
└───────────────────┘
```

### 3. Code Manipulation Workflow

```
Input: Original code, target element, new content
┌───────────────────┐
│ Find target       │
│ element in code   │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Format new content│
│ with proper       │
│ indentation       │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Replace target    │
│ element with new  │
│ content           │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Return modified   │
│ code              │
└───────────────────┘
```

## Common Usage Patterns

### 1. Automated Code Modification

CodeHem is ideal for programmatically modifying code across multiple files:

```python
# Create a CodeHem instance for Python
hem = CodeHem('python')

# Load source code
code = hem.load_file('/path/to/file.py')

# Extract code elements
elements = hem.extract(code)

# Modify a specific method
class_element = hem.filter(elements, 'MyClass')
for method in class_element.children:
    if method.name == 'target_method':
        # Create modified method content
        new_method = method.content.replace('old_logic', 'new_logic')
        
        # Apply the change
        modified_code = hem.manipulator.replace_method(code, 'MyClass', 'target_method', new_method)
        
        # Save the modified code
        with open('/path/to/file.py', 'w') as f:
            f.write(modified_code)
```

### 2. Code Analysis

CodeHem can be used to analyze code structure and extract metrics:

```python
# Analyze multiple files
def analyze_project(project_path):
    results = {}
    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                code = CodeHem.load_file(file_path)
                hem = CodeHem.from_raw_code(code)
                elements = hem.extract(code)
                
                # Count classes, methods, etc.
                class_count = len([e for e in elements.elements if e.is_class])
                method_count = sum(len([m for m in c.children if m.is_method]) 
                                  for c in elements.elements if c.is_class)
                
                results[file_path] = {
                    'classes': class_count,
                    'methods': method_count
                }
    return results
```

### 3. Language-Agnostic Processing

CodeHem allows applying the same operations across different languages:

```python
# Process both Python and TypeScript files with the same logic
def process_file(file_path):
    code = CodeHem.load_file(file_path)
    hem = CodeHem.from_file_path(file_path)  # Auto-detects language
    
    # Extract code elements
    elements = hem.extract(code)
    
    # Apply the same analysis regardless of language
    for element in elements.elements:
        if element.is_class:
            print(f"Class: {element.name}")
            for method in [c for c in element.children if c.is_method]:
                print(f"  Method: {method.name}")
```

## Implementation Details

### Tree-sitter Integration

CodeHem uses tree-sitter parsers to build Abstract Syntax Trees (ASTs) for code:

1. Code is parsed into an AST
2. AST queries are used to locate specific elements
3. Node ranges are mapped to line numbers in the original code
4. AST navigation helps understand code structure

### Language-Specific Handling

Each supported language has:

1. A dedicated finder implementation
2. A dedicated manipulator implementation
3. A language strategy defining syntax patterns
4. Custom formatting rules

### Performance Optimization

- **Caching**: Results of parsing and queries are cached
- **Lazy Loading**: Parsers are initialized on demand
- **Query Optimization**: Specialized queries for common operations

## Best Practices

1. Use `CodeHem.from_raw_code()` for automatic language detection
2. Use `extract()` to get a structured view of code
3. Use `filter()` to locate specific elements
4. Use the appropriate manipulator method for the target element
5. Chain operations for complex transformations

## Extending CodeHem

To add support for a new language:

1. Create a language-specific finder
2. Create a language-specific manipulator
3. Create a language strategy
4. Register the new language in the factory classes
5. Add language detection rules

## Limitations

1. Only supports Python, JavaScript, and TypeScript currently
2. Complex language constructs might not be perfectly handled
3. Very large files might encounter performance issues
4. Custom language extensions may require specialized handling

## Examples

### Example 1: Analyzing a Python Class

```python
hem = CodeHem('python')
code = '''
class Example:
    def method1(self):
        return "Hello"
        
    def method2(self, param):
        return f"Hello, {param}"
'''

elements = hem.extract(code)
class_elem = hem.filter(elements, 'Example')

print(f"Class: {class_elem.name}")
for method in [c for c in class_elem.children if c.is_method]:
    print(f"Method: {method.name}")
    params = [p for p in method.children if p.is_parameter]
    if params:
        print(f"  Parameters: {', '.join(p.name for p in params)}")
```

### Example 2: Modifying a TypeScript Method

```python
hem = CodeHem('typescript')
code = '''
class Component {
    private count: number = 0;
    
    increment() {
        this.count++;
    }
    
    getCount(): number {
        return this.count;
    }
}
'''

# Add a new method
new_method = '''
reset() {
    this.count = 0;
}
'''

modified = hem.manipulator.add_method_to_class(code, 'Component', new_method)
print(modified)
```

### Example 3: Converting a Function to Use Async/Await

```python
hem = CodeHem('javascript')
code = '''
function fetchData(url, callback) {
    fetch(url)
        .then(response => response.json())
        .then(data => callback(null, data))
        .catch(error => callback(error));
}
'''

new_function = '''
async function fetchData(url) {
    try {
        const response = await fetch(url);
        const data = await response.json();
        return data;
    } catch (error) {
        throw error;
    }
}
'''

modified = hem.manipulator.replace_function(code, 'fetchData', new_function)
print(modified)
```