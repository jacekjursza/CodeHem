# CodeHem API Index

This document provides a concise reference of all public methods and models in the CodeHem library.

## Core Classes and Methods

### CodeHem (main.py)

Main entry point for the library.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `language_code: str` | `None` | Initializes a CodeHem instance for a specific language |
| `from_file_path` | `file_path: str` | `CodeHem` | Factory method to create an instance based on file extension |
| `from_raw_code` | `code_or_path: str, check_for_file: bool=True` | `CodeHem` | Factory method to auto-detect language from code |
| `load_file` | `file_path: str` | `str` | Static method to load content from a file |
| `extract` | `code: str` | `CodeElementsResult` | Extract code elements from source code |
| `filter` | `elements: CodeElementsResult, xpath: str=''` | `Optional[CodeElement]` | Filter code elements by XPath-like expression |
| `get_content_type` | `content: str` | `str` | Determine the type of content (module, class, function, etc.) |
| `analyze_file` | `file_path: str` | `None` | Static method to analyze a file and print statistics |

### CodeFinder (finder/base.py)

Abstract base class for finding code elements.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `can_handle` | `code: str` | `bool` | Check if this finder can handle the given code |
| `find_function` | `code: str, function_name: str` | `Tuple[int, int]` | Find a function and return its line range |
| `find_class` | `code: str, class_name: str` | `Tuple[int, int]` | Find a class and return its line range |
| `find_method` | `code: str, class_name: str, method_name: str` | `Tuple[int, int]` | Find a method in a class and return its line range |
| `find_property` | `code: str, class_name: str, property_name: str` | `Tuple[int, int]` | Find a property in a class and return its line range |
| `find_property_setter` | `code: str, class_name: str, property_name: str` | `Tuple[int, int]` | Find a property setter in a class |
| `find_property_and_setter` | `code: str, class_name: str, property_name: str` | `Tuple[int, int]` | Find both a property and its setter |
| `find_imports_section` | `code: str` | `Tuple[int, int]` | Find the imports section in a file |
| `find_properties_section` | `code: str, class_name: str` | `Tuple[int, int]` | Find the properties section in a class |
| `get_classes_from_code` | `code: str` | `List[Tuple[str, Node]]` | Get all classes from code |
| `get_methods_from_code` | `code: str` | `List[Tuple[str, Node]]` | Get all methods from code |
| `get_methods_from_class` | `code: str, class_name: str` | `List[Tuple[str, Node]]` | Get all methods from a class |
| `has_class_method_indicator` | `method_node: Node, code_bytes: bytes` | `bool` | Check if a method has class method indicators |
| `get_decorators` | `code: str, name: str, class_name: Optional[str]=None` | `List[str]` | Get decorators for a function/method |
| `get_class_decorators` | `code: str, class_name: str` | `List[str]` | Get decorators for a class |
| `is_correct_syntax` | `plain_text: str` | `bool` | Check if text has correct syntax for this language |
| `find_class_for_method` | `method_name: str, code: str` | `Optional[str]` | Find the class containing a method |
| `content_looks_like_class_definition` | `content: str` | `bool` | Check if content looks like a class definition |

### CodeManipulator (manipulator/abstract.py)

Abstract interface for code manipulators.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `replace_function` | `original_code: str, function_name: str, new_function: str` | `str` | Replace a function with new content |
| `replace_class` | `original_code: str, class_name: str, new_class_content: str` | `str` | Replace a class with new content |
| `replace_method` | `original_code: str, class_name: str, method_name: str, new_method: str` | `str` | Replace a method in a class |
| `replace_property` | `original_code: str, class_name: str, property_name: str, new_property: str` | `str` | Replace a property in a class |
| `add_method_to_class` | `original_code: str, class_name: str, method_code: str` | `str` | Add a new method to a class |
| `remove_method_from_class` | `original_code: str, class_name: str, method_name: str` | `str` | Remove a method from a class |
| `replace_properties_section` | `original_code: str, class_name: str, new_properties: str` | `str` | Replace the properties section in a class |
| `replace_imports_section` | `original_code: str, new_imports: str` | `str` | Replace the imports section |
| `replace_entire_file` | `original_code: str, new_content: str` | `str` | Replace entire file content |
| `replace_lines` | `original_code: str, start_line: int, end_line: int, new_lines: str` | `str` | Replace specific lines in the code |
| `replace_lines_range` | `original_code: str, start_line: int, end_line: int, new_content: str, preserve_formatting: bool=False` | `str` | Replace a range of lines |
| `fix_special_characters` | `content: str, xpath: str` | `Tuple[str, str]` | Fix special characters in content and XPath |
| `fix_class_method_xpath` | `content: str, xpath: str, file_path: str=None` | `Tuple[str, Dict]` | Fix XPath for class methods |

### LanguageStrategy (strategies/language_strategy.py)

Abstract strategy for language-specific operations.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `language_code` | - | `str` | Get the language code (property) |
| `file_extensions` | - | `List[str]` | Get file extensions for this language (property) |
| `is_class_definition` | `line: str` | `bool` | Check if a line is a class definition |
| `is_function_definition` | `line: str` | `bool` | Check if a line is a function definition |
| `is_method_definition` | `line: str` | `bool` | Check if a line is a method definition |
| `extract_method_name` | `method_line: str` | `Optional[str]` | Extract method name from a line |
| `extract_class_name` | `class_line: str` | `Optional[str]` | Extract class name from a line |
| `extract_function_name` | `function_line: str` | `Optional[str]` | Extract function name from a line |
| `fix_special_characters` | `content: str, xpath: str` | `Tuple[str, str]` | Fix special characters in content and XPath |
| `adjust_indentation` | `code: str, indent_level: int` | `str` | Adjust code indentation |
| `get_default_indentation` | - | `str` | Get default indentation for this language |
| `is_method_of_class` | `method_node: Node, class_name: str, code_bytes: bytes` | `bool` | Check if method belongs to a class |
| `get_content_type` | `content: str` | `str` | Determine content type |
| `determine_element_type` | `decorators: List[str], is_method: bool=False` | `str` | Determine element type from decorators |

### ASTHandler (core/ast_handler.py)

Handles Abstract Syntax Tree operations using tree-sitter.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `language: str` | `None` | Initialize handler for a language |
| `parse` | `code: str` | `Tuple[Node, bytes]` | Parse source code into AST |
| `get_node_text` | `node: Node, code_bytes: bytes` | `str` | Get text content of a node |
| `get_node_range` | `node: Node` | `Tuple[int, int]` | Get line range of a node |
| `execute_query` | `query_string: str, root: Node, code_bytes: bytes` | `List[Tuple[Node, str]]` | Execute a tree-sitter query |
| `find_parent_of_type` | `node: Node, parent_type: str` | `Optional[Node]` | Find nearest parent of specified type |
| `find_child_by_field_name` | `node: Node, field_name: str` | `Optional[Node]` | Find child by field name |
| `find_first_child_of_type` | `node: Node, child_type: str` | `Optional[Node]` | Find first child of specified type |
| `is_node_of_type` | `node: Node, node_type: str` | `bool` | Check if node is of specified type |
| `get_indentation` | `line: str` | `str` | Extract whitespace indentation from line |
| `apply_indentation` | `content: str, base_indent: str` | `str` | Apply consistent indentation |
| `find_by_query` | `code: str, query_string: str` | `List[Dict[str, Any]]` | Find nodes matching a query |

## Models

### CodeElement (core/models.py)

Represents a single code element (class, method, function, etc.).

| Field | Type | Description |
|-------|------|-------------|
| `type` | `CodeElementType` | Type of the code element (enum) |
| `name` | `str` | Name of the element |
| `content` | `str` | Full content of the element |
| `range` | `Optional[CodeRange]` | Line range in source file |
| `parent_name` | `Optional[str]` | Name of parent element (class name for methods) |
| `value_type` | `Optional[str]` | Type information (for properties, parameters) |
| `additional_data` | `Dict[str, Any]` | Additional element-specific data |
| `children` | `List[CodeElement]` | Child elements |

**Properties:**

| Property | Returns | Description |
|----------|---------|-------------|
| `decorators` | `List[CodeElement]` | Get all decorator metaelements |
| `is_method` | `bool` | Check if element is a method |
| `is_interface` | `bool` | Check if element is an interface |
| `parameters` | `List[CodeElement]` | Get all parameter children |
| `is_property` | `bool` | Check if element is a property |
| `is_function` | `bool` | Check if element is a function |
| `meta_elements` | `List[CodeElement]` | Get all metaelement children |
| `is_return_value` | `bool` | Check if element is a return value |
| `return_value` | `Optional[CodeElement]` | Get return value element |
| `is_parameter` | `bool` | Check if element is a parameter |
| `is_meta_element` | `bool` | Check if element is a meta element |
| `is_class` | `bool` | Check if element is a class |

### CodeElementsResult (core/models.py)

Collection of extracted code elements.

| Field | Type | Description |
|-------|------|-------------|
| `elements` | `List[CodeElement]` | List of code elements |

**Properties:**

| Property | Returns | Description |
|----------|---------|-------------|
| `classes` | `List[CodeElement]` | Get all class elements |
| `properties` | `List[CodeElement]` | Get all property elements |
| `methods` | `List[CodeElement]` | Get all method elements |
| `functions` | `List[CodeElement]` | Get all function elements |

### CodeRange (core/models.py)

Represents a range in source code (line numbers).

| Field | Type | Description |
|-------|------|-------------|
| `start_line` | `int` | Starting line number (1-indexed) |
| `end_line` | `int` | Ending line number (1-indexed) |
| `node` | `Any` | Tree-sitter node reference (optional) |

## Enums

### CodeElementType (core/models.py)

Types of code elements that can be identified and manipulated.

| Value | Description |
|-------|-------------|
| `CLASS` | Class definition |
| `METHOD` | Method within a class |
| `FUNCTION` | Standalone function |
| `PROPERTY` | Property or attribute |
| `IMPORT` | Import statement |
| `MODULE` | Module or file |
| `VARIABLE` | Variable declaration |
| `PARAMETER` | Function/method parameter |
| `RETURN_VALUE` | Return value |
| `META_ELEMENT` | Metadata element |
| `INTERFACE` | Interface definition |

### MetaElementType (core/models.py)

Types of meta-elements that provide information about or modify code elements.

| Value | Description |
|-------|-------------|
| `DECORATOR` | Function/class decorator |
| `ANNOTATION` | Type or metadata annotation |
| `ATTRIBUTE` | Attribute metadata |
| `DOC_COMMENT` | Documentation comment |
| `TYPE_HINT` | Type hint information |
| `PARAMETER` | Parameter metadata |

## Factories

### get_code_finder (finder/factory.py)

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_code_finder` | `language: str` | `CodeFinder` | Get a code finder for specified language |

### get_code_manipulator (manipulator/factory.py)

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_code_manipulator` | `language: str` | `Optional[AbstractCodeManipulator]` | Get a code manipulator for specified language |

### get_strategy (strategies/__init__.py)

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_strategy` | `language: str` | `Optional[LanguageStrategy]` | Get a language strategy for specified language |
| `get_strategy_for_file` | `file_path: str` | `Optional[LanguageStrategy]` | Get a language strategy based on file extension |
| `register_strategy` | `language: str, strategy_class: Type[LanguageStrategy]` | `None` | Register a new language strategy |

## Utility Functions

### format_utils.py

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `normalize_indentation` | `code_text: str, indent: str='    '` | `str` | Normalize indentation in code |
| `format_python_class_content` | `code_text: str` | `str` | Format Python class content |
| `format_python_method_content` | `code_text: str` | `str` | Format Python method content |
| `process_lines` | `original_lines: list, start_idx: int, end_idx: int, new_lines: list` | `list` | Process and replace lines |