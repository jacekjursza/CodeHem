# Component Interfaces Reference

This document provides a reference for the standard interfaces that language components must implement in the CodeHem library. 

## Core Interfaces

### ICodeParser

Responsible for parsing source code into language-specific syntax trees.

```python
class ICodeParser(ABC):
    @abstractmethod
    def parse(self, code: str) -> Tuple[Any, bytes]:
        """
        Parse source code into a syntax tree.
        
        Args:
            code: Source code as string
            
        Returns:
            Tuple of (syntax_tree, code_bytes) where syntax_tree is the parsed tree
            and code_bytes is the source code as bytes
        """
        pass
    
    @property
    @abstractmethod
    def language_code(self) -> str:
        """Get the language code this parser is for."""
        pass
```

### ISyntaxTreeNavigator

Responsible for navigating and querying syntax trees to find specific elements or patterns.

```python
class ISyntaxTreeNavigator(ABC):
    @abstractmethod
    def find_element(self, tree: Any, code_bytes: bytes, element_type: str, 
                   element_name: Optional[str]=None, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the syntax tree based on type, name, and parent.
        
        Args:
            tree: The syntax tree to search
            code_bytes: The original code as bytes
            element_type: Type of element to find (e.g., 'function', 'class', 'method')
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        pass
    
    @abstractmethod
    def execute_query(self, tree: Any, code_bytes: bytes, query_string: str) -> List[Tuple[Any, str]]:
        """
        Execute a tree-specific query on the syntax tree.
        
        Args:
            tree: The syntax tree to query
            code_bytes: The original code as bytes
            query_string: The query to execute
            
        Returns:
            List of tuples (node, capture_name) matching the query
        """
        pass
    
    @abstractmethod
    def get_node_text(self, node: Any, code_bytes: bytes) -> str:
        """
        Get the text for a node in the syntax tree.
        
        Args:
            node: The node to get text for
            code_bytes: The original code as bytes
            
        Returns:
            The text of the node
        """
        pass
    
    @abstractmethod
    def get_node_range(self, node: Any) -> Tuple[int, int]:
        """
        Get the line range for a node in the syntax tree.
        
        Args:
            node: The node to get range for
            
        Returns:
            Tuple of (start_line, end_line)
        """
        pass
```

### IElementExtractor

Responsible for extracting specific code elements from syntax trees or raw code.

```python
class IElementExtractor(ABC):
    @abstractmethod
    def extract_functions(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract functions from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of function data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_classes(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract classes from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of class data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_methods(self, tree: Any, code_bytes: bytes, 
                      class_name: Optional[str]=None) -> List[Dict]:
        """
        Extract methods from the provided syntax tree, optionally filtering by class.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            class_name: Optional class name to filter by
            
        Returns:
            List of method data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_all(self, tree: Any, code_bytes: bytes) -> Dict[str, List[Dict]]:
        """
        Extract all supported code elements from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            Dictionary of element type to list of element data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_imports(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract imports from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of import data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_properties(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract properties from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of property data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_static_properties(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract static properties from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of static property data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_decorators(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract decorators from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of decorator data dictionaries
        """
        pass
```

### IPostProcessor

Responsible for transforming raw extraction dictionaries into structured CodeElement objects.

```python
class IPostProcessor(ABC):
    @abstractmethod
    def process_imports(self, raw_imports: List[Dict]) -> List['CodeElement']:
        """
        Process raw import data into CodeElement objects.
        
        Args:
            raw_imports: List of raw import dictionaries
            
        Returns:
            List of CodeElement objects representing imports
        """
        pass
    
    @abstractmethod
    def process_functions(self, raw_functions: List[Dict], 
                        all_decorators: Optional[List[Dict]]=None) -> List['CodeElement']:
        """
        Process raw function data into CodeElement objects.
        
        Args:
            raw_functions: List of raw function dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing functions
        """
        pass
    
    @abstractmethod
    def process_classes(self, raw_classes: List[Dict], members: List[Dict], 
                      static_props: List[Dict], properties: Optional[List[Dict]]=None,
                      all_decorators: Optional[List[Dict]]=None) -> List['CodeElement']:
        """
        Process raw class data into CodeElement objects.
        
        Args:
            raw_classes: List of raw class dictionaries
            members: List of raw member dictionaries (methods, getters, setters)
            static_props: List of raw static property dictionaries
            properties: Optional list of raw property dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing classes with their members
        """
        pass
    
    @abstractmethod
    def process_all(self, raw_elements: Dict[str, List[Dict]]) -> 'CodeElementsResult':
        """
        Process all raw element data into a CodeElementsResult.
        
        Args:
            raw_elements: Dictionary of element type to list of raw element dictionaries
            
        Returns:
            CodeElementsResult containing processed elements
        """
        pass
```

### IExtractionOrchestrator

Responsible for coordinating the extraction process across multiple components.

```python
class IExtractionOrchestrator(ABC):
    @abstractmethod
    def extract_all(self, code: str) -> 'CodeElementsResult':
        """
        Extract all code elements from the provided code.
        
        Args:
            code: Source code as string
            
        Returns:
            CodeElementsResult containing extracted elements
        """
        pass
    
    @abstractmethod
    def find_element(self, code: str, element_type: str, 
                   element_name: Optional[str]=None, 
                   parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the code based on type, name, and parent.
        
        Args:
            code: Source code as string
            element_type: Type of element to find (e.g., 'function', 'class', 'method')
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        pass
```

## Extended Interfaces

### IManipulator

Responsible for modifying source code by adding, removing, or replacing specific code elements.

```python
class IManipulator(ABC):
    @abstractmethod
    def add_element(self, original_code: str, new_element: str, 
                  parent_name: Optional[str]=None) -> str:
        """
        Add a new element to the code.
        
        Args:
            original_code: The original source code
            new_element: The code for the new element to add
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            The modified source code with the new element added
        """
        pass
    
    @abstractmethod
    def find_element(self, code: str, element_name: str, 
                   parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the code by name and optional parent.
        
        Args:
            code: The source code to search
            element_name: Name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        pass
    
    @abstractmethod
    def replace_element(self, original_code: str, element_name: str, 
                       new_element: str, parent_name: Optional[str]=None) -> str:
        """
        Replace an existing element with a new implementation.
        
        Args:
            original_code: The original source code
            element_name: Name of the element to replace
            new_element: The new code for the element
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            The modified source code with the element replaced
        """
        pass
    
    @abstractmethod
    def remove_element(self, original_code: str, element_name: str, 
                      parent_name: Optional[str]=None) -> str:
        """
        Remove an element from the code.
        
        Args:
            original_code: The original source code
            element_name: Name of the element to remove
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            The modified source code with the element removed
        """
        pass
    
    @abstractmethod
    def format_element(self, element_code: str, indent_level: int=0) -> str:
        """
        Format an element's code using the appropriate formatter and indentation.
        
        Args:
            element_code: The code of the element to format
            indent_level: The indentation level to apply
            
        Returns:
            The formatted element code
        """
        pass
```

### IFormatter

Responsible for formatting code elements according to language-specific style guidelines.

```python
class IFormatter(ABC):
    @abstractmethod
    def format_code(self, code: str) -> str:
        """
        Format general code according to language-specific rules.
        
        Args:
            code: The code to format
            
        Returns:
            The formatted code
        """
        pass
    
    @abstractmethod
    def format_element(self, element_type: str, code: str) -> str:
        """
        Format a specific code element based on its type.
        
        Args:
            element_type: The type of the element (e.g., 'class', 'method', 'function')
            code: The code to format
            
        Returns:
            The formatted code
        """
        pass
    
    @abstractmethod
    def apply_indentation(self, code: str, base_indent: str) -> str:
        """
        Apply a base indentation level to all lines in the code.
        
        Args:
            code: The code to indent
            base_indent: The base indentation to apply (e.g., '    ', '\t')
            
        Returns:
            The indented code
        """
        pass
    
    @abstractmethod
    def get_indentation(self, line: str) -> str:
        """
        Extract the indentation from a line of code.
        
        Args:
            line: The line to extract indentation from
            
        Returns:
            The indentation string
        """
        pass
    
    @abstractmethod
    def normalize_indentation(self, code: str, target_indent: str='') -> str:
        """
        Normalize indentation by reducing all lines to a common baseline,
        then applying the target indentation.
        
        Args:
            code: The code to normalize
            target_indent: The target indentation to apply
            
        Returns:
            The code with normalized indentation
        """
        pass
```

### ILanguageService

Responsible for providing a unified interface to all language-specific functionality.

```python
class ILanguageService(ABC):
    @abstractmethod
    def get_parser(self) -> ICodeParser:
        """
        Get the language-specific parser.
        
        Returns:
            The parser component for this language
        """
        pass
    
    @abstractmethod
    def get_navigator(self) -> ISyntaxTreeNavigator:
        """
        Get the language-specific syntax tree navigator.
        
        Returns:
            The navigator component for this language
        """
        pass
    
    @abstractmethod
    def get_extractor(self) -> IElementExtractor:
        """
        Get the language-specific element extractor.
        
        Returns:
            The extractor component for this language
        """
        pass
    
    @abstractmethod
    def get_post_processor(self) -> IPostProcessor:
        """
        Get the language-specific post-processor.
        
        Returns:
            The post-processor component for this language
        """
        pass
    
    @abstractmethod
    def get_orchestrator(self) -> IExtractionOrchestrator:
        """
        Get the language-specific extraction orchestrator.
        
        Returns:
            The orchestrator component for this language
        """
        pass
    
    @abstractmethod
    def get_manipulator(self, element_type: Union[str, CodeElementType]) -> IManipulator:
        """
        Get the language-specific manipulator for a given element type.
        
        Args:
            element_type: The type of element to get a manipulator for
            
        Returns:
            The manipulator component for this language and element type
        """
        pass
    
    @abstractmethod
    def get_formatter(self) -> IFormatter:
        """
        Get the language-specific formatter.
        
        Returns:
            The formatter component for this language
        """
        pass
    
    @abstractmethod
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of the primary element in a code snippet.
        
        Args:
            code: The code snippet to analyze
            
        Returns:
            The detected element type
        """
        pass
    
    @abstractmethod
    def extract(self, code: str) -> 'CodeElementsResult':
        """
        Extract all code elements from the provided code.
        
        Args:
            code: The source code to extract from
            
        Returns:
            A CodeElementsResult containing all extracted elements
        """
        pass
    
    @abstractmethod
    def find_element(self, code: str, element_type: str, 
                   element_name: Optional[str]=None, 
                   parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the code based on type, name, and parent.
        
        Args:
            code: The source code to search
            element_type: The type of element to find
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        pass
    
    @abstractmethod
    def get_text_by_xpath(self, code: str, xpath: str) -> str:
        """
        Get the text of an element identified by an XPath expression.
        
        Args:
            code: The source code to search
            xpath: The XPath expression identifying the element
            
        Returns:
            The text of the element
        """
        pass
    
    @property
    @abstractmethod
    def language_code(self) -> str:
        """
        Get the language code for this service.
        
        Returns:
            The language code (e.g., 'python', 'typescript')
        """
        pass
    
    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """
        Get the file extensions associated with this language.
        
        Returns:
            List of file extensions (e.g., ['.py'], ['.ts', '.tsx'])
        """
        pass
    
    @property
    @abstractmethod
    def supported_element_types(self) -> List[str]:
        """
        Get the element types supported by this language.
        
        Returns:
            List of supported element type strings
        """
        pass
```

### ILanguageDetector

Responsible for detecting the programming language of a code snippet.

```python
class ILanguageDetector(ABC):
    @abstractmethod
    def detect_confidence(self, code: str) -> float:
        """
        Calculate a confidence score for the code being in this language.
        
        Args:
            code: The code snippet to analyze
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass
```

## Base Implementations

For each of these interfaces, the library provides base implementations that handle common functionality:

- `BaseCodeParser` - Base implementation of `ICodeParser`
- `BaseSyntaxTreeNavigator` - Base implementation of `ISyntaxTreeNavigator`
- `BaseElementExtractor` - Base implementation of `IElementExtractor`
- `BaseExtractionOrchestrator` - Base implementation of `IExtractionOrchestrator`
- `BaseFormatter` - Base implementation of `IFormatter`
- `BaseManipulator` - Base implementation of `IManipulator`

These base implementations should be extended by language-specific implementations to provide the required functionality.
