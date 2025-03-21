# CodeHem Python Finder Assumptions

This document outlines the assumptions that the Python finder tests make about how the CodeHem library should behave. These assumptions guide the implementation and testing of the Python finder component.

## General Finder Assumptions

1. **Code Elements**: The finder should be able to locate all standard Python code elements:
   - Functions
   - Classes
   - Methods
   - Properties (including property getters and setters)
   - Class attributes/static properties
   - Import sections

2. **Line Ranges**: When a code element is found, the finder returns a tuple of (start_line, end_line) where:
   - Line numbers are 1-indexed (first line is line 1)
   - The range is inclusive (both start_line and end_line are part of the element)
   - A return value of (0, 0) indicates that the element was not found
   
3. **Range Inclusion Parameters**: Finder methods accept an optional `include_extra` parameter:
   - When `include_extra=False` (default), only the core element is included in the range (e.g., starting from the "def" line for functions)
   - When `include_extra=True`, the range includes related elements like decorators
   - This applies consistently across all element types including properties

4. **Nested Structures**: The finder should handle nested code structures:
   - Classes inside classes
   - Methods inside classes
   - Functions inside functions
   - Conditionals and loops within methods/functions

5. **Robustness**: The finder should be resilient to:
   - Varying indentation styles (spaces vs tabs)
   - Comments within code
   - Docstrings
   - Empty lines
   - Partial/incomplete code where possible

## Specific Element Assumptions

### Functions

1. **Function Identification**:
   - A function is identified by its name
   - Function signatures may include type annotations
   - Standalone functions should not be confused with methods

2. **Function Decorators**:
   - By default, the function range starts at the "def" line
   - When `include_extra=True`, decorators above a function are considered part of the function
   - Multiple decorators are included when requested

### Classes

1. **Class Identification**:
   - A class is identified by its name
   - Classes may have inheritance (single or multiple)
   - Class definitions may include decorators

2. **Class Body**:
   - The class body includes all methods, properties, and static attributes
   - Class docstrings are part of the class body

### Methods

1. **Method Identification**:
   - Methods are identified by their class name and method name
   - Methods must be contained within a class
   - Self or cls parameters identify instance or class methods

2. **Method Decorators**:
   - By default, the method range starts at the "def" line
   - When `include_extra=True`, method decorators are included in the range
   - Methods may have multiple decorators

### Properties

1. **Property Identification**:
   - Properties are identified by the @property decorator
   - Property setters are identified by the @name.setter decorator
   - Property getters and setters should be findable separately and together

2. **Property Range**:
   - By default, the property range starts at the "def" line (like other methods)
   - When `include_extra=True`, property ranges include the @property decorator
   - When `include_extra=True`, property setter ranges include the @name.setter decorator
   - Properties follow the same decorator handling logic as other methods and functions

### Import Sections

1. **Import Section Identification**:
   - Import sections are contiguous blocks of import statements
   - Import sections may include multiple import styles (import x, from x import y)
   - Import sections may have blank lines between imports

## Practical Considerations

1. **Performance**:
   - Finding code elements should be reasonably efficient
   - Code parsing should be cached when appropriate

2. **AST Utilization**:
   - The finder should leverage tree-sitter's AST capabilities
   - AST navigation should be preferred over regex where possible
   - Text searching should be a fallback when AST navigation is insufficient

3. **Error Handling**:
   - The finder should not raise exceptions for code that fails to parse
   - When encountering malformed code, the finder should make best efforts to locate elements
   - Clear error conditions should be indicated by return values rather than exceptions