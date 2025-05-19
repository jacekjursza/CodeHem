# Input Validation Framework

This module provides a comprehensive approach for validating function inputs and raising appropriate validation errors in the CodeHem library.

## Overview

The input validation framework is designed to:

1. Provide a consistent way to validate function inputs throughout the codebase
2. Offer both simple validators and complex schema validation for nested structures
3. Generate helpful error messages that make debugging easier
4. Integrate with the CodeHem error context system for detailed error reporting
5. Support both decorator-based and direct validation approaches

## Key Components

- Basic validators for common types and constraints
- Complex validators for dictionaries and lists using schemas
- Decorator-based validation for function parameters and return values
- Prebuilt validators for common use cases
- Utility functions for creating custom validators

## Documentation

For detailed documentation on how to use the input validation framework, see:
- [Input Validation Framework Documentation](../../docs/input_validation.md)
- [Example Implementation](../../examples/input_validation_example.py)

## Usage

```python
from codehem.core.input_validation import validate_params, validate_type, validate_not_empty

# Using the decorator approach
@validate_params(
    code={"type": str, "not_empty": True},
    element_type={"type": str, "one_of": ["class", "method", "function"]},
    element_name={"type": str, "optional": True}
)
def find_element(code, element_type, element_name=None):
    # Implementation...

# Using direct validation
def parse_xpath(xpath):
    validate_type(xpath, str, "xpath")
    validate_not_empty(xpath, "xpath")
    # Implementation...
```

## Integration with Error Context

The validation framework integrates with CodeHem's error context system to provide comprehensive error reports:

```python
from codehem.core.error_context import with_error_context
from codehem.core.input_validation import validate_params

@with_error_context('extraction', component='Python')
@validate_params(code={"type": str, "not_empty": True})
def extract_class(code):
    # Implementation...
```
