# Language-Specific Post-Processors

## Overview

CodeHem now includes a powerful post-processing system that transforms raw extraction data into structured code elements with proper relationships. This system is an essential part of the code extraction pipeline and provides language-specific handling for features like:

- Decorators
- Property getters and setters
- Type annotations
- Class inheritance and interface implementation
- And more

Post-processors ensure that the extracted code elements accurately represent the relationships and semantic meaning of the source code, regardless of the programming language used.

## Supported Languages

The following languages are supported by the post-processor system:

- **Python**: Complete support for Python-specific features like decorators, property getters/setters, and docstrings
- **TypeScript/JavaScript**: Support for TypeScript-specific features including interfaces, type aliases, enums, and decorators

## Architecture

The post-processor system follows a clean, extensible architecture:

1. **Abstract Base Class**: `LanguagePostProcessor` defines the common interface for all post-processors
2. **Language-Specific Implementations**: `PythonPostProcessor` and `TypeScriptPostProcessor` provide language-specific logic
3. **Factory**: `PostProcessorFactory` dynamically selects the appropriate post-processor based on language

This architecture allows for easy addition of support for new languages in the future.

## Using Post-Processors

Post-processors are integrated seamlessly into the CodeHem API. When you use the `extract` method, the appropriate post-processor is automatically selected and applied:

```python
import codehem

# Create a CodeHem instance
hem = codehem.CodeHem('typescript')

# Extract code elements - post-processor is applied automatically
result = hem.extract(typescript_code)

# Filter for specific elements
class_element = hem.filter(result, 'MyClass')
method_element = hem.filter(result, 'MyClass.myMethod')
```

### Post-Processor Factory

If needed, you can also use the `PostProcessorFactory` directly:

```python
from codehem.core.post_processors.factory import PostProcessorFactory

# Get a list of supported languages
supported_languages = PostProcessorFactory.get_supported_languages()
print(f"Supported languages: {supported_languages}")

# Get a post-processor instance for a specific language
python_processor = PostProcessorFactory.get_post_processor('python')
ts_processor = PostProcessorFactory.get_post_processor('typescript')

# JavaScript is automatically mapped to TypeScript
js_processor = PostProcessorFactory.get_post_processor('javascript')
```

## Extending the System

To add support for a new language, you need to:

1. Create a new post-processor class that inherits from `LanguagePostProcessor`
2. Implement all required methods for the new language
3. Register the post-processor in the factory

For example:

```python
from codehem.core.post_processors.base import LanguagePostProcessor
from codehem.core.post_processors.factory import PostProcessorFactory

class JavaPostProcessor(LanguagePostProcessor):
    def __init__(self):
        super().__init__('java')
    
    # Implement required methods
    def process_imports(self, raw_imports):
        # Java-specific import processing
        pass
    
    def process_functions(self, raw_functions, all_decorators=None):
        # Java-specific function processing
        pass
    
    def process_classes(self, raw_classes, members, static_props, properties=None, all_decorators=None):
        # Java-specific class processing
        pass

# Register the post-processor
PostProcessorFactory.register('java', JavaPostProcessor)
```

## Features by Language

### Python

- Decorator processing for functions, classes, methods, and properties
- Property getter/setter identification and association
- Docstring extraction
- Method parameter processing with type hints
- Return value type processing

### TypeScript/JavaScript

- Interface extraction and inheritance relationships
- Type annotation processing
- Decorator handling
- Method overloading
- Static properties and methods
- Enum and type alias support
- Property optional/readonly flags

## Integration with Existing Code

The post-processor system has been designed to integrate seamlessly with existing CodeHem code. It respects the existing `CodeElement` model structure and enhances it with additional relationships and semantic information.
