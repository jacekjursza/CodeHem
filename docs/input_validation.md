# Input Validation Framework

The Input Validation Framework in CodeHem provides a comprehensive approach for validating function inputs and raising appropriate validation errors. This document explains how to use the framework and provides examples for common validation patterns.

## Basic Usage

### Using Decorators for Function Parameter Validation

The `@validate_params` decorator is the simplest way to add validation to your functions:

```python
from codehem.core.input_validation import validate_params
from codehem.models.enums import CodeElementType

@validate_params(
    code={"type": str, "not_empty": True},
    element_type={"type": str, "one_of": CodeElementType.values()},
    element_name={"type": str, "optional": True}
)
def find_element(code, element_type, element_name=None):
    # Implementation...
```

### Using Decorators for Return Value Validation

The `@validate_return` decorator can be used to validate function return values:

```python
from codehem.core.input_validation import validate_return

@validate_return({"type": dict, "schema": {
    "name": {"type": str},
    "path": {"type": str, "not_empty": True},
    "elements": {"type": list}
}})
def extract_elements(code):
    # Implementation...
```

### Direct Validation

You can also perform validation directly within your functions:

```python
from codehem.core.input_validation import (
    validate_type,
    validate_not_empty,
    validate_one_of
)

def my_function(code, element_type):
    # Validate inputs
    validate_type(code, str, "code")
    validate_not_empty(code, "code")
    validate_type(element_type, str, "element_type")
    validate_one_of(element_type, ["class", "method", "function"], "element_type")
    
    # Actual implementation
    # ...
```

## Available Validators

### Basic Validators

| Validator | Description |
|-----------|-------------|
| `validate_type(value, expected_type, param_name)` | Validates that a value is of the expected type |
| `validate_not_none(value, param_name)` | Validates that a value is not None |
| `validate_not_empty(value, param_name)` | Validates that a value is not empty (string, list, dict, etc.) |
| `validate_enum_value(value, enum_class, param_name)` | Validates that a value is a valid member of an Enum |
| `validate_one_of(value, valid_values, param_name)` | Validates that a value is one of a set of valid values |
| `validate_min_length(value, min_length, param_name)` | Validates that a value has at least the minimum length |
| `validate_max_length(value, max_length, param_name)` | Validates that a value has at most the maximum length |
| `validate_regex(value, pattern, param_name)` | Validates that a string matches a regular expression pattern |
| `validate_min_value(value, min_value, param_name)` | Validates that a numeric value is at least the minimum value |
| `validate_max_value(value, max_value, param_name)` | Validates that a numeric value is at most the maximum value |
| `validate_range(value, min_value, max_value, param_name)` | Validates that a numeric value is within a specified range |
| `validate_unique_items(value, param_name)` | Validates that a collection contains unique items |

### Complex Validators

| Validator | Description |
|-----------|-------------|
| `validate_dict_schema(value, schema, param_name)` | Validates a dictionary against a schema |
| `validate_list_items(value, item_validator, param_name)` | Validates each item in a list against a set of validation rules |

### Decorator Validators

| Validator | Description |
|-----------|-------------|
| `@validate_params(**param_validators)` | Decorator to validate function parameters according to specified rules |
| `@validate_return(validator)` | Decorator to validate a function's return value |

### Utility Functions

| Function | Description |
|----------|-------------|
| `create_validator(*validators)` | Creates a composite validator from multiple validator functions |
| `create_schema_validator(schema)` | Creates a validator function for a specific schema |

### Prebuilt Validators

| Validator | Description |
|-----------|-------------|
| `string_validator` | Validates that a value is a string |
| `non_empty_string_validator` | Validates that a value is a non-empty string |
| `integer_validator` | Validates that a value is an integer |
| `positive_integer_validator` | Validates that a value is a positive integer (> 0) |
| `non_negative_integer_validator` | Validates that a value is a non-negative integer (>= 0) |
| `float_validator` | Validates that a value is a float |
| `numeric_validator` | Validates that a value is a numeric (int or float) |
| `list_validator` | Validates that a value is a list |
| `non_empty_list_validator` | Validates that a value is a non-empty list |
| `dict_validator` | Validates that a value is a dict |
| `non_empty_dict_validator` | Validates that a value is a non-empty dict |
| `boolean_validator` | Validates that a value is a boolean |

## Schema Validation

The framework provides a powerful mechanism for validating complex data structures using schemas.

### Dictionary Schema Validation

```python
from codehem.core.input_validation import validate_dict_schema

# Define a schema for a configuration dictionary
config_schema = {
    "api_key": {"type": str, "required": True, "not_empty": True},
    "timeout": {"type": int, "min_value": 1, "max_value": 600, "required": False},
    "retries": {"type": int, "min_value": 0, "max_value": 10, "required": False},
    "debug": {"type": bool, "required": False},
    "advanced": {"type": dict, "required": False, "schema": {
        "log_level": {"type": str, "one_of": ["debug", "info", "warning", "error"]},
        "cache_size": {"type": int, "min_value": 1}
    }}
}

# Validate a configuration
def process_config(config):
    validate_dict_schema(config, config_schema, "config")
    # Process the validated configuration
    # ...
```

### List Item Validation

```python
from codehem.core.input_validation import validate_list_items

# Define a validator for list items
tag_validator = {
    "type": str,
    "not_empty": True,
    "min_length": 2,
    "max_length": 50,
    "pattern": r"^[a-zA-Z0-9_-]+$"
}

# Validate a list of tags
def process_tags(tags):
    validate_list_items(tags, tag_validator, "tags")
    # Process the validated tags
    # ...
```

## Custom Validators

You can create custom validators for specific validation logic:

```python
from codehem.core.input_validation import create_validator
from codehem.core.error_handling import InvalidParameterError

# Custom validator for a URL
def validate_url(value, param_name):
    import re
    if value is None:
        return
    if not isinstance(value, str):
        raise InvalidTypeError(param_name, value, str)
    url_pattern = r'^https?://[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}(/.*)?$'
    if not re.match(url_pattern, value):
        raise InvalidParameterError(param_name, value, "valid URL (http:// or https://)")

# Using it in a validator decorator
@validate_params(
    name={"type": str, "not_empty": True},
    website={"type": str, "custom_validator": validate_url, "optional": True}
)
def add_company(name, website=None):
    # Implementation...
```

## Schema Definition Reference

When defining parameter validation using `@validate_params` or schema-based validators, the following options are available:

| Option | Description |
|--------|-------------|
| `type` | Expected type or tuple of types |
| `required` | Whether the parameter is required (default: False) |
| `optional` | Whether the parameter can be None (default: False) |
| `not_empty` | Whether the value cannot be empty (default: False) |
| `min_length` | Minimum length for strings, lists, etc. |
| `max_length` | Maximum length for strings, lists, etc. |
| `pattern` | Regex pattern for string validation |
| `min_value` | Minimum value for numbers |
| `max_value` | Maximum value for numbers |
| `one_of` | List of valid values |
| `enum` | Enum class for validation |
| `unique_items` | Whether collection items must be unique (default: False) |
| `item_validator` | Validator for items in a collection |
| `schema` | Schema for nested dictionary validation |
| `custom_validator` | Custom validation function |
| `__allow_unknown_fields` | Whether to allow fields not in the schema (default: True) |

## Best Practices

### When to Use Validation

- **Public API Functions**: Always validate inputs to public API functions.
- **Critical Internal Functions**: Validate inputs to functions where incorrect inputs could cause data corruption or security issues.
- **Complex Data Structures**: Use schema validation for complex data structures.
- **User-Provided Inputs**: Always validate any data coming from external sources.

### Error Handling

ValidationError exceptions provide useful context for debugging:

```python
try:
    validate_params_function(invalid_param)
except ValidationError as e:
    print(f"Validation error: {e}")
    print(f"Parameter: {e.parameter}")
    print(f"Value: {e.value}")
    print(f"Expected: {e.expected}")
```

### Performance Considerations

- For performance-critical paths, consider doing validation only in public API entry points rather than in every internal function.
- The `@validate_params` decorator adds some overhead, so use it judiciously in performance-critical code.

## Integration with Error Context System

The validation framework integrates with CodeHem's error context system for enhanced error reporting:

```python
from codehem.core.error_context import error_context, with_error_context
from codehem.core.input_validation import validate_params

@with_error_context('extraction', component='Python', operation='extract_class')
@validate_params(
    code={"type": str, "not_empty": True},
    class_name={"type": str, "optional": True}
)
def extract_class(code, class_name=None):
    with error_context('parsing', code=code[:100]):
        # Implementation...
```

In this example, if a validation error occurs, it will include the error context information, providing much more detailed error reports.
