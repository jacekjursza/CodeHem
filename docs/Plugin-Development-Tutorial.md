# Plugin Development Tutorial: Creating Language Support for CodeHem

This tutorial guides you through creating a new language plugin for CodeHem, using Java as an example. By the end, you'll have a fully functional language plugin that can extract and manipulate Java code.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Setting Up the Plugin Structure](#setting-up-the-plugin-structure)
4. [Core Components Implementation](#core-components-implementation)
5. [Testing Your Plugin](#testing-your-plugin)
6. [Publishing and Distribution](#publishing-and-distribution)
7. [Advanced Features](#advanced-features)

## Overview

### What You'll Build

A complete Java language plugin for CodeHem that supports:
- Class and interface extraction
- Method and constructor detection
- Field and property extraction
- Import statement handling
- Code manipulation and formatting

### Architecture Understanding

CodeHem uses a component-based architecture where each language plugin provides:

1. **Language Service** - Main entry point and file detection
2. **Parser** - Converts source code to AST using tree-sitter
3. **Navigator** - Executes queries on the AST
4. **Extractor** - Identifies and extracts code elements
5. **Post-Processor** - Transforms raw data to structured CodeElement objects
6. **Formatter** - Handles code formatting and style

## Prerequisites

### Required Dependencies

```bash
# Install CodeHem development dependencies
pip install codehem[dev]

# Install tree-sitter Java parser
pip install tree-sitter-java

# Install cookiecutter for project templating
pip install cookiecutter
```

### Knowledge Requirements

- Basic understanding of Python and Java
- Familiarity with tree-sitter concepts
- Basic knowledge of Abstract Syntax Trees (AST)

## Setting Up the Plugin Structure

### Step 1: Create Project from Template

```bash
# Use the official CodeHem plugin template
cookiecutter gh:codehem/codehem-lang-template

# Answer the prompts:
# language_name: Java
# language_slug: java
# author_name: Your Name
# author_email: your.email@example.com
```

This creates a project structure:

```
codehem_lang_java/
├── codehem_lang_java/
│   ├── __init__.py
│   ├── service.py
│   ├── detector.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   ├── navigator.py
│   │   ├── extractor.py
│   │   └── post_processor.py
│   ├── formatting/
│   │   ├── __init__.py
│   │   └── formatter.py
│   └── node_patterns.json
├── tests/
│   ├── __init__.py
│   ├── test_java_basic.py
│   └── fixtures/
├── setup.py
└── README.md
```

### Step 2: Configure Entry Points

Edit `setup.py` to register your plugin:

```python
from setuptools import setup, find_packages

setup(
    name="codehem-lang-java",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "codehem>=1.0.0",
        "tree-sitter-java>=0.20.0",
    ],
    entry_points={
        "codehem.languages": [
            "java = codehem_lang_java:JavaLanguageService",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Java language support for CodeHem",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8+",
    ],
)
```

## Core Components Implementation

### Step 1: Language Service

The language service is the main entry point that registers your plugin with CodeHem.

```python
# codehem_lang_java/service.py

import logging
from typing import Dict, Any, Optional

from codehem.core.registry import language_service
from codehem.core.components.interfaces import ILanguageService
from codehem.core.engine.languages import get_parser

from .components.parser import JavaCodeParser
from .components.navigator import JavaSyntaxTreeNavigator
from .components.extractor import JavaElementExtractor
from .components.post_processor import JavaPostProcessor
from .formatting.formatter import JavaFormatter

logger = logging.getLogger(__name__)


@language_service("java")
class JavaLanguageService(ILanguageService):
    """Java language service for CodeHem."""
    
    def __init__(self):
        """Initialize the Java language service."""
        self.language_name = "java"
        self.file_extensions = ['.java']
        self._components = None
    
    def detect_language(self, file_path: str, content: str = None) -> bool:
        """
        Detect if the given file/content is Java.
        
        Args:
            file_path: Path to the file
            content: Optional file content for content-based detection
            
        Returns:
            True if the file is detected as Java
        """
        # File extension check
        if file_path.lower().endswith('.java'):
            return True
        
        # Content-based detection if extension check fails
        if content:
            java_indicators = [
                'public class',
                'public interface',
                'import java.',
                'package ',
                'public static void main'
            ]
            return any(indicator in content for indicator in java_indicators)
        
        return False
    
    def get_components(self) -> Dict[str, Any]:
        """
        Get all language-specific components.
        
        Returns:
            Dictionary of component instances
        """
        if self._components is None:
            # Create navigator first (needed by other components)
            navigator = JavaSyntaxTreeNavigator()
            
            self._components = {
                'parser': JavaCodeParser(),
                'navigator': navigator,
                'extractor': JavaElementExtractor(navigator),
                'post_processor': JavaPostProcessor(),
                'formatter': JavaFormatter(),
            }
        
        return self._components
    
    def get_file_extensions(self) -> list:
        """Get supported file extensions."""
        return self.file_extensions
```

### Step 2: Parser Component

The parser converts Java source code into an AST using tree-sitter.

```python
# codehem_lang_java/components/parser.py

import logging
from typing import Any

import tree_sitter_java
from tree_sitter import Language, Parser

from codehem.core.components.interfaces import ICodeParser
from codehem.core.components.base_implementations import BaseCodeParser

logger = logging.getLogger(__name__)

# Initialize Java language
JAVA_LANGUAGE = Language(tree_sitter_java.language())


class JavaCodeParser(BaseCodeParser):
    """Java implementation of the ICodeParser interface."""
    
    def __init__(self):
        """Initialize the Java code parser."""
        super().__init__('java')
        self.language = JAVA_LANGUAGE
        self._parser = None
    
    def parse(self, code: str) -> Any:
        """
        Parse Java code into an AST.
        
        Args:
            code: Java source code to parse
            
        Returns:
            Tree-sitter AST tree
        """
        try:
            if self._parser is None:
                self._parser = Parser()
                self._parser.set_language(self.language)
            
            # Convert code to bytes (tree-sitter requirement)
            code_bytes = code.encode('utf-8')
            
            # Parse the code
            tree = self._parser.parse(code_bytes)
            
            logger.debug(f"Successfully parsed Java code ({len(code_bytes)} bytes)")
            return tree
            
        except Exception as e:
            logger.error(f"Error parsing Java code: {e}", exc_info=True)
            raise
    
    def get_language(self):
        """Get the tree-sitter language object."""
        return self.language
```

### Step 3: Navigator Component

The navigator executes tree-sitter queries to find specific AST nodes.

```python
# codehem_lang_java/components/navigator.py

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from codehem.core.components.interfaces import ISyntaxTreeNavigator
from codehem.core.components.base_implementations import BaseSyntaxTreeNavigator

logger = logging.getLogger(__name__)


class JavaSyntaxTreeNavigator(BaseSyntaxTreeNavigator):
    """Java implementation of the ISyntaxTreeNavigator interface."""
    
    def __init__(self):
        """Initialize the Java syntax tree navigator."""
        super().__init__('java')
        # Import here to avoid circular imports
        import tree_sitter_java
        from tree_sitter import Language
        self.language = Language(tree_sitter_java.language())
    
    def execute_query(self, tree: Any, code_bytes: bytes, query_string: str) -> List[Dict[str, Any]]:
        """
        Execute a tree-sitter query on the Java syntax tree.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            query_string: The tree-sitter query string
            
        Returns:
            List of dictionaries mapping capture names to nodes
        """
        logger.debug(f"Executing Java query: {query_string[:100]}...")
        
        try:
            # Create tree-sitter query
            query = self.language.query(query_string)
            
            # Execute query
            if hasattr(tree, 'root_node'):
                captures = query.captures(tree.root_node)
            else:
                captures = query.captures(tree)
            
            # Process captures into structured format
            result = []
            if captures:
                # Group captures by match
                max_nodes = max(len(nodes) for nodes in captures.values()) if captures else 0
                
                if max_nodes > 1 and len(captures) > 1:
                    # Multiple captures with multiple nodes - pair them correctly
                    sorted_captures = {}
                    for capture_name, nodes in captures.items():
                        sorted_captures[capture_name] = sorted(nodes, key=lambda n: n.start_point)
                    
                    for i in range(max_nodes):
                        match_dict = {}
                        for capture_name, nodes in sorted_captures.items():
                            if i < len(nodes):
                                match_dict[capture_name] = nodes[i]
                        
                        if match_dict:
                            result.append(match_dict)
                else:
                    # Simple case - create one match per capture group
                    match_dict = {}
                    for capture_name, nodes in captures.items():
                        if nodes:
                            match_dict[capture_name] = nodes[0]
                    
                    if match_dict:
                        result.append(match_dict)
            
            logger.debug(f"Found {len(result)} matches")
            return result
            
        except Exception as e:
            logger.error(f"Error executing Java query: {e}", exc_info=True)
            return []
    
    def find_element(
        self, 
        tree: Any, 
        code_bytes: bytes, 
        element_type: str, 
        element_name: Optional[str] = None, 
        parent_name: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Find a specific element in the Java syntax tree.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            element_type: Type of element to find (class, method, field, etc.)
            element_name: Optional name of the element
            parent_name: Optional name of the parent element
            
        Returns:
            Tuple of (start_line, end_line) for the found element
        """
        logger.debug(f"Finding Java element: type={element_type}, name={element_name}, parent={parent_name}")
        
        query_string = self._build_query_for_element_type(element_type, element_name, parent_name)
        
        try:
            matches = self.execute_query(tree, code_bytes, query_string)
            
            for match in matches:
                # Find the target node based on element type
                target_node = None
                
                if element_type.lower() == 'class':
                    target_node = match.get('class_decl')
                elif element_type.lower() == 'interface':
                    target_node = match.get('interface_decl')
                elif element_type.lower() == 'method':
                    target_node = match.get('method_decl')
                elif element_type.lower() == 'field':
                    target_node = match.get('field_decl')
                elif element_type.lower() == 'constructor':
                    target_node = match.get('constructor_decl')
                
                if target_node:
                    start_line, end_line = self.get_node_range(target_node)
                    logger.debug(f"Found Java element at lines {start_line}-{end_line}")
                    return start_line, end_line
            
            logger.warning(f"No matching Java element found: type={element_type}, name={element_name}")
            return 0, 0
            
        except Exception as e:
            logger.error(f"Error finding Java element: {e}", exc_info=True)
            return 0, 0
    
    def _build_query_for_element_type(
        self, 
        element_type: str, 
        element_name: Optional[str] = None, 
        parent_name: Optional[str] = None
    ) -> str:
        """Build a tree-sitter query for finding Java elements."""
        
        if element_type.lower() == 'class':
            if element_name:
                return f"""
                (class_declaration
                  name: (identifier) @class_name
                  (#eq? @class_name "{element_name}")
                  body: (class_body) @body) @class_decl
                """
            else:
                return """
                (class_declaration
                  name: (identifier) @class_name
                  body: (class_body) @body) @class_decl
                """
        
        elif element_type.lower() == 'interface':
            if element_name:
                return f"""
                (interface_declaration
                  name: (identifier) @interface_name
                  (#eq? @interface_name "{element_name}")
                  body: (interface_body) @body) @interface_decl
                """
            else:
                return """
                (interface_declaration
                  name: (identifier) @interface_name
                  body: (interface_body) @body) @interface_decl
                """
        
        elif element_type.lower() == 'method':
            base_query = """
            (class_declaration
              name: (identifier) @class_name
              body: (class_body
                (method_declaration
                  name: (identifier) @method_name
                  parameters: (formal_parameters) @params
                  body: (block) @body) @method_decl))
            """
            
            conditions = []
            if parent_name:
                conditions.append(f'(#eq? @class_name "{parent_name}")')
            if element_name:
                conditions.append(f'(#eq? @method_name "{element_name}")')
            
            if conditions:
                # Insert conditions after the method_name capture
                lines = base_query.strip().split('\n')
                method_name_line = None
                for i, line in enumerate(lines):
                    if '@method_name' in line:
                        method_name_line = i
                        break
                
                if method_name_line:
                    for condition in conditions:
                        lines.insert(method_name_line + 1, f'                  {condition}')
                
                return '\n'.join(lines)
            
            return base_query
        
        elif element_type.lower() == 'field':
            if parent_name and element_name:
                return f"""
                (class_declaration
                  name: (identifier) @class_name
                  (#eq? @class_name "{parent_name}")
                  body: (class_body
                    (field_declaration
                      declarator: (variable_declarator
                        name: (identifier) @field_name
                        (#eq? @field_name "{element_name}")) @field_decl)))
                """
            else:
                return """
                (class_declaration
                  name: (identifier) @class_name
                  body: (class_body
                    (field_declaration
                      declarator: (variable_declarator
                        name: (identifier) @field_name) @field_decl)))
                """
        
        # Default fallback
        return f"({element_type}_declaration) @{element_type}_decl"
```

### Step 4: Extractor Component

The extractor identifies and extracts different types of code elements.

```python
# codehem_lang_java/components/extractor.py

import logging
from typing import Any, Dict, List

from codehem.core.components.interfaces import IElementExtractor, ISyntaxTreeNavigator
from codehem.core.components.base_implementations import BaseElementExtractor
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)


class JavaElementExtractor(BaseElementExtractor):
    """Java implementation of the IElementExtractor interface."""
    
    def __init__(self, navigator: ISyntaxTreeNavigator):
        """Initialize the Java element extractor."""
        super().__init__('java', navigator)
    
    def extract_classes(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """Extract Java class declarations."""
        logger.debug("Extracting Java classes")
        
        query_str = """
        (class_declaration
          name: (identifier) @class_name
          body: (class_body) @body) @class_decl
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            classes = []
            
            for match in result:
                if 'class_name' in match and 'class_decl' in match:
                    class_name = self.navigator.get_node_text(match['class_name'], code_bytes).decode('utf-8')
                    class_node = match['class_decl']
                    
                    class_range = self.navigator.get_node_range(class_node)
                    
                    class_data = {
                        'name': class_name,
                        'type': CodeElementType.CLASS.value,
                        'range': {
                            'start': {'line': class_range[0], 'column': 0},
                            'end': {'line': class_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(class_node, code_bytes).decode('utf-8'),
                    }
                    
                    classes.append(class_data)
            
            logger.debug(f"Extracted {len(classes)} Java classes")
            return classes
            
        except Exception as e:
            logger.error(f"Error extracting Java classes: {e}", exc_info=True)
            return []
    
    def extract_interfaces(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """Extract Java interface declarations."""
        logger.debug("Extracting Java interfaces")
        
        query_str = """
        (interface_declaration
          name: (identifier) @interface_name
          body: (interface_body) @body) @interface_decl
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            interfaces = []
            
            for match in result:
                if 'interface_name' in match and 'interface_decl' in match:
                    interface_name = self.navigator.get_node_text(match['interface_name'], code_bytes).decode('utf-8')
                    interface_node = match['interface_decl']
                    
                    interface_range = self.navigator.get_node_range(interface_node)
                    
                    interface_data = {
                        'name': interface_name,
                        'type': CodeElementType.INTERFACE.value,
                        'range': {
                            'start': {'line': interface_range[0], 'column': 0},
                            'end': {'line': interface_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(interface_node, code_bytes).decode('utf-8'),
                    }
                    
                    interfaces.append(interface_data)
            
            logger.debug(f"Extracted {len(interfaces)} Java interfaces")
            return interfaces
            
        except Exception as e:
            logger.error(f"Error extracting Java interfaces: {e}", exc_info=True)
            return []
    
    def extract_methods(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """Extract Java method declarations."""
        logger.debug("Extracting Java methods")
        
        query_str = """
        (class_declaration
          name: (identifier) @class_name
          body: (class_body
            (method_declaration
              name: (identifier) @method_name
              parameters: (formal_parameters) @params
              body: (block) @method_body) @method_decl))
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            methods = []
            
            for match in result:
                if all(key in match for key in ['class_name', 'method_name', 'method_decl']):
                    class_name = self.navigator.get_node_text(match['class_name'], code_bytes).decode('utf-8')
                    method_name = self.navigator.get_node_text(match['method_name'], code_bytes).decode('utf-8')
                    method_node = match['method_decl']
                    
                    method_range = self.navigator.get_node_range(method_node)
                    
                    # Extract parameters if available
                    parameters = []
                    if 'params' in match:
                        params_text = self.navigator.get_node_text(match['params'], code_bytes).decode('utf-8')
                        # Simple parameter extraction - can be enhanced
                        parameters = [p.strip() for p in params_text.strip('()').split(',') if p.strip()]
                    
                    method_data = {
                        'name': method_name,
                        'type': CodeElementType.METHOD.value,
                        'parent': class_name,
                        'range': {
                            'start': {'line': method_range[0], 'column': 0},
                            'end': {'line': method_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(method_node, code_bytes).decode('utf-8'),
                        'parameters': parameters,
                    }
                    
                    methods.append(method_data)
            
            logger.debug(f"Extracted {len(methods)} Java methods")
            return methods
            
        except Exception as e:
            logger.error(f"Error extracting Java methods: {e}", exc_info=True)
            return []
    
    def extract_functions(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """Extract Java functions (static methods outside classes)."""
        # Java doesn't have standalone functions, so return empty list
        # or implement extraction of static methods if needed
        return []
    
    def extract_imports(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """Extract Java import statements."""
        logger.debug("Extracting Java imports")
        
        query_str = """
        (import_declaration) @import
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            imports = []
            
            for match in result:
                if 'import' in match:
                    import_node = match['import']
                    import_range = self.navigator.get_node_range(import_node)
                    
                    import_data = {
                        'type': CodeElementType.IMPORT.value,
                        'range': {
                            'start': {'line': import_range[0], 'column': 0},
                            'end': {'line': import_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(import_node, code_bytes).decode('utf-8'),
                    }
                    
                    imports.append(import_data)
            
            logger.debug(f"Extracted {len(imports)} Java imports")
            return imports
            
        except Exception as e:
            logger.error(f"Error extracting Java imports: {e}", exc_info=True)
            return []
```

### Step 5: Post-Processor Component

The post-processor transforms raw extraction data into structured CodeElement objects.

```python
# codehem_lang_java/components/post_processor.py

import logging
from typing import Any, Dict, List, Optional

from codehem.core.components.interfaces import IPostProcessor
from codehem.core.post_processors.base import LanguagePostProcessor
from codehem.models.code_element import CodeElement, CodeElementsResult
from codehem.models.enums import CodeElementType
from codehem.models.range import CodeRange
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class JavaPostProcessor(LanguagePostProcessor):
    """Java implementation of the IPostProcessor interface."""
    
    def __init__(self):
        """Initialize the Java post-processor."""
        super().__init__('java')
    
    def process(self, raw_data: Dict[str, List[Dict]]) -> CodeElementsResult:
        """
        Process raw extraction data into structured CodeElement objects.
        
        Args:
            raw_data: Dictionary containing lists of raw element data
            
        Returns:
            CodeElementsResult with structured CodeElement objects
        """
        logger.debug("Processing raw Java extraction data")
        
        try:
            # Process each element type
            classes = self.process_classes(raw_data.get('classes', []))
            interfaces = self.process_interfaces(raw_data.get('interfaces', []))
            methods = self.process_methods(raw_data.get('methods', []))
            imports = self.process_imports(raw_data.get('imports', []))
            
            # Create result object
            result = CodeElementsResult(
                classes=classes,
                interfaces=interfaces,
                functions=[],  # Java doesn't have standalone functions
                methods=methods,
                imports=imports,
                properties=[],  # Can be added later if needed
                static_properties=[]  # Can be added later if needed
            )
            
            logger.debug(f"Processed Java data: {len(classes)} classes, {len(interfaces)} interfaces, {len(methods)} methods, {len(imports)} imports")
            return result
            
        except Exception as e:
            logger.error(f"Error processing Java data: {e}", exc_info=True)
            return CodeElementsResult(
                classes=[], interfaces=[], functions=[], methods=[], 
                imports=[], properties=[], static_properties=[]
            )
    
    def process_classes(self, raw_classes: List[Dict]) -> List[CodeElement]:
        """Process raw class data into CodeElement objects."""
        classes = []
        
        for class_data in raw_classes:
            try:
                if not isinstance(class_data, dict) or 'range' not in class_data:
                    continue
                
                range_data = class_data['range']
                code_range = CodeRange(
                    start_line=range_data['start']['line'],
                    start_column=range_data['start'].get('column', 0),
                    end_line=range_data['end']['line'],
                    end_column=range_data['end'].get('column', 0),
                )
                
                class_element = CodeElement(
                    name=class_data.get('name', 'UnknownClass'),
                    type=CodeElementType.CLASS,
                    range=code_range,
                    content=class_data.get('content', ''),
                    parent=class_data.get('parent'),
                    methods=[],  # Will be populated later
                    properties=[],
                    static_properties=[]
                )
                
                classes.append(class_element)
                
            except (ValidationError, KeyError, Exception) as e:
                logger.warning(f"Skipping invalid class data: {e}")
                continue
        
        return classes
    
    def process_interfaces(self, raw_interfaces: List[Dict]) -> List[CodeElement]:
        """Process raw interface data into CodeElement objects."""
        interfaces = []
        
        for interface_data in raw_interfaces:
            try:
                if not isinstance(interface_data, dict) or 'range' not in interface_data:
                    continue
                
                range_data = interface_data['range']
                code_range = CodeRange(
                    start_line=range_data['start']['line'],
                    start_column=range_data['start'].get('column', 0),
                    end_line=range_data['end']['line'],
                    end_column=range_data['end'].get('column', 0),
                )
                
                interface_element = CodeElement(
                    name=interface_data.get('name', 'UnknownInterface'),
                    type=CodeElementType.INTERFACE,
                    range=code_range,
                    content=interface_data.get('content', ''),
                    parent=interface_data.get('parent'),
                    methods=[],
                    properties=[],
                    static_properties=[]
                )
                
                interfaces.append(interface_element)
                
            except (ValidationError, KeyError, Exception) as e:
                logger.warning(f"Skipping invalid interface data: {e}")
                continue
        
        return interfaces
    
    def process_methods(self, raw_methods: List[Dict]) -> List[CodeElement]:
        """Process raw method data into CodeElement objects."""
        methods = []
        
        for method_data in raw_methods:
            try:
                if not isinstance(method_data, dict) or 'range' not in method_data:
                    continue
                
                range_data = method_data['range']
                code_range = CodeRange(
                    start_line=range_data['start']['line'],
                    start_column=range_data['start'].get('column', 0),
                    end_line=range_data['end']['line'],
                    end_column=range_data['end'].get('column', 0),
                )
                
                method_element = CodeElement(
                    name=method_data.get('name', 'unknownMethod'),
                    type=CodeElementType.METHOD,
                    range=code_range,
                    content=method_data.get('content', ''),
                    parent=method_data.get('parent'),
                    parameters=method_data.get('parameters', []),
                    methods=[],
                    properties=[],
                    static_properties=[]
                )
                
                methods.append(method_element)
                
            except (ValidationError, KeyError, Exception) as e:
                logger.warning(f"Skipping invalid method data: {e}")
                continue
        
        return methods
    
    def process_imports(self, raw_imports: List[Dict]) -> List[CodeElement]:
        """Process raw import data into CodeElement objects."""
        if not raw_imports:
            return []
        
        # Combine all imports into a single element
        try:
            # Sort imports by line number
            valid_imports = [imp for imp in raw_imports if isinstance(imp, dict) and 'range' in imp]
            if not valid_imports:
                return []
            
            valid_imports.sort(key=lambda x: x['range']['start']['line'])
            
            # Get combined range
            first_import = valid_imports[0]
            last_import = valid_imports[-1]
            
            combined_range = CodeRange(
                start_line=first_import['range']['start']['line'],
                start_column=first_import['range']['start'].get('column', 0),
                end_line=last_import['range']['end']['line'],
                end_column=last_import['range']['end'].get('column', 0),
            )
            
            # Combine content
            combined_content = '\n'.join(imp.get('content', '') for imp in valid_imports)
            
            import_element = CodeElement(
                name='imports',
                type=CodeElementType.IMPORT,
                range=combined_range,
                content=combined_content,
                parent=None,
                methods=[],
                properties=[],
                static_properties=[]
            )
            
            return [import_element]
            
        except Exception as e:
            logger.error(f"Error processing Java imports: {e}", exc_info=True)
            return []
```

### Step 6: Formatter Component

The formatter handles Java-specific code formatting.

```python
# codehem_lang_java/formatting/formatter.py

import logging
from typing import List, Optional

from codehem.core.formatting.formatter import BraceFormatter

logger = logging.getLogger(__name__)


class JavaFormatter(BraceFormatter):
    """Java-specific code formatter."""
    
    def __init__(self):
        """Initialize the Java formatter."""
        super().__init__(
            indent_size=4,
            use_tabs=False,
            brace_style="k&r",  # or "allman" for Allman style
            line_ending="\n"
        )
    
    def format_class(self, class_name: str, content: str, modifiers: Optional[List[str]] = None) -> str:
        """
        Format a Java class declaration.
        
        Args:
            class_name: Name of the class
            content: Class body content
            modifiers: Optional list of modifiers (public, abstract, etc.)
            
        Returns:
            Formatted class declaration
        """
        modifiers_str = ' '.join(modifiers) if modifiers else 'public'
        
        # Format class header
        header = f"{modifiers_str} class {class_name}"
        
        # Format body with proper indentation
        if content.strip():
            indented_content = self.apply_indentation(content, 1)
            return f"{header} {{\n{indented_content}\n}}"
        else:
            return f"{header} {{\n}}"
    
    def format_interface(self, interface_name: str, content: str, modifiers: Optional[List[str]] = None) -> str:
        """
        Format a Java interface declaration.
        
        Args:
            interface_name: Name of the interface
            content: Interface body content
            modifiers: Optional list of modifiers
            
        Returns:
            Formatted interface declaration
        """
        modifiers_str = ' '.join(modifiers) if modifiers else 'public'
        
        header = f"{modifiers_str} interface {interface_name}"
        
        if content.strip():
            indented_content = self.apply_indentation(content, 1)
            return f"{header} {{\n{indented_content}\n}}"
        else:
            return f"{header} {{\n}}"
    
    def format_method(
        self, 
        method_name: str, 
        parameters: List[str], 
        body: str, 
        return_type: str = "void",
        modifiers: Optional[List[str]] = None
    ) -> str:
        """
        Format a Java method declaration.
        
        Args:
            method_name: Name of the method
            parameters: List of parameter declarations
            body: Method body content
            return_type: Return type of the method
            modifiers: Optional list of modifiers (public, static, etc.)
            
        Returns:
            Formatted method declaration
        """
        modifiers_str = ' '.join(modifiers) if modifiers else 'public'
        params_str = ', '.join(parameters)
        
        # Format method signature
        signature = f"{modifiers_str} {return_type} {method_name}({params_str})"
        
        # Format body
        if body.strip():
            indented_body = self.apply_indentation(body, 1)
            return f"{signature} {{\n{indented_body}\n}}"
        else:
            return f"{signature} {{\n}}"
    
    def format_field(
        self, 
        field_name: str, 
        field_type: str, 
        initial_value: Optional[str] = None,
        modifiers: Optional[List[str]] = None
    ) -> str:
        """
        Format a Java field declaration.
        
        Args:
            field_name: Name of the field
            field_type: Type of the field
            initial_value: Optional initial value
            modifiers: Optional list of modifiers (private, static, final, etc.)
            
        Returns:
            Formatted field declaration
        """
        modifiers_str = ' '.join(modifiers) if modifiers else 'private'
        
        declaration = f"{modifiers_str} {field_type} {field_name}"
        
        if initial_value:
            declaration += f" = {initial_value}"
        
        return f"{declaration};"
    
    def format_import(self, import_path: str, is_static: bool = False) -> str:
        """
        Format a Java import statement.
        
        Args:
            import_path: The import path (e.g., java.util.List)
            is_static: Whether this is a static import
            
        Returns:
            Formatted import statement
        """
        if is_static:
            return f"import static {import_path};"
        else:
            return f"import {import_path};"
```

## Testing Your Plugin

### Step 1: Create Test Fixtures

Create test files in `tests/fixtures/java/`:

```java
// tests/fixtures/java/simple_class.java
public class Calculator {
    private int result;
    
    public Calculator() {
        this.result = 0;
    }
    
    public int add(int a, int b) {
        return a + b;
    }
    
    public int getResult() {
        return result;
    }
}
```

### Step 2: Write Tests

```python
# tests/test_java_extraction.py

import pytest
from codehem import CodeHem


class TestJavaExtraction:
    def setup_method(self):
        """Set up test fixtures."""
        self.hem = CodeHem("java")
    
    def test_extract_java_class(self):
        """Test extracting a simple Java class."""
        code = """
        public class Calculator {
            private int result;
            
            public int add(int a, int b) {
                return a + b;
            }
        }
        """
        
        result = self.hem.extract(code)
        
        # Verify class extraction
        assert len(result.classes) == 1
        assert result.classes[0].name == "Calculator"
        
        # Verify method extraction
        assert len(result.methods) == 1
        assert result.methods[0].name == "add"
        assert result.methods[0].parent == "Calculator"
    
    def test_extract_java_interface(self):
        """Test extracting a Java interface."""
        code = """
        public interface Drawable {
            void draw();
            void setColor(String color);
        }
        """
        
        result = self.hem.extract(code)
        
        assert len(result.interfaces) == 1
        assert result.interfaces[0].name == "Drawable"
    
    def test_extract_java_imports(self):
        """Test extracting Java imports."""
        code = """
        import java.util.List;
        import java.util.ArrayList;
        
        public class Example {
            private List<String> items = new ArrayList<>();
        }
        """
        
        result = self.hem.extract(code)
        
        assert len(result.imports) == 1
        assert "java.util.List" in result.imports[0].content
        assert "java.util.ArrayList" in result.imports[0].content


class TestJavaManipulation:
    def setup_method(self):
        """Set up test fixtures."""
        self.hem = CodeHem("java")
    
    def test_apply_patch_to_method(self):
        """Test applying a patch to a Java method."""
        code = """
        public class Calculator {
            public int add(int a, int b) {
                return a + b;
            }
        }
        """
        
        xpath = "Calculator.add[method]"
        new_code = """public int add(int a, int b) {
            int result = a + b;
            System.out.println("Result: " + result);
            return result;
        }"""
        
        result = self.hem.apply_patch(
            code=code,
            xpath=xpath,
            new_code=new_code,
            mode="replace",
            return_format="json"
        )
        
        assert result["status"] == "ok"
        assert "System.out.println" in result["modified_code"]
```

### Step 3: Run Tests

```bash
# Install your plugin in development mode
pip install -e .

# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_java_extraction.py -v

# Run with coverage
pytest tests/ --cov=codehem_lang_java --cov-report=html
```

## Publishing and Distribution

### Step 1: Package Configuration

Ensure your `setup.py` is properly configured:

```python
setup(
    name="codehem-lang-java",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "codehem>=1.0.0",
        "tree-sitter-java>=0.20.0",
    ],
    entry_points={
        "codehem.languages": [
            "java = codehem_lang_java:JavaLanguageService",
        ],
    },
    # ... other metadata
)
```

### Step 2: Build and Publish

```bash
# Build the package
python setup.py sdist bdist_wheel

# Upload to PyPI (test first)
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

### Step 3: Installation

Users can now install your plugin:

```bash
pip install codehem-lang-java
```

CodeHem will automatically discover and load your plugin.

## Advanced Features

### Custom AST Node Patterns

Define custom patterns in `node_patterns.json`:

```json
{
  "class_patterns": [
    "(class_declaration name: (identifier) @class_name)",
    "(enum_declaration name: (identifier) @enum_name)"
  ],
  "method_patterns": [
    "(method_declaration name: (identifier) @method_name)",
    "(constructor_declaration name: (identifier) @constructor_name)"
  ]
}
```

### Error Handling and Retry Logic

Implement robust error handling:

```python
from codehem.core.error_utilities.retry import retry_exponential

class JavaElementExtractor(BaseElementExtractor):
    @retry_exponential(max_attempts=3)
    def extract_classes(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        # Implementation with retry logic
        pass
```

### Performance Optimization

Implement caching for expensive operations:

```python
from functools import lru_cache

class JavaSyntaxTreeNavigator(BaseSyntaxTreeNavigator):
    @lru_cache(maxsize=128)
    def execute_query(self, tree_hash: str, query_string: str) -> List[Dict]:
        # Cached query execution
        pass
```

## Conclusion

You now have a complete Java language plugin for CodeHem! This tutorial covered:

1. Setting up the plugin structure
2. Implementing all core components
3. Adding proper formatting support
4. Writing comprehensive tests
5. Publishing for distribution

Your plugin supports:
- ✅ Class and interface extraction
- ✅ Method and constructor detection
- ✅ Import statement handling
- ✅ Code manipulation and patching
- ✅ Java-specific formatting

Next steps could include:
- Adding support for annotations
- Implementing field extraction
- Adding enum support
- Enhancing error handling
- Performance optimization

The same patterns can be applied to create plugins for other languages like Go, Rust, C++, or any language supported by tree-sitter.