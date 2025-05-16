"""
Input validation framework for CodeHem.

This module provides a comprehensive approach for validating function inputs
and raising appropriate validation errors. It includes decorators, validator functions,
and utilities for common validation patterns.
"""
import functools
import inspect
import re
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Tuple, Type, TypeVar, Union, cast

from codehem.core.error_handling import (
    InvalidParameterError,
    InvalidTypeError,
    MissingParameterError, 
    ValidationError
)

# Type variable for function return type
T = TypeVar('T')

# ===== Basic Validator Functions =====

def validate_type(value: Any, expected_type: Union[Type, Tuple[Type, ...]], 
                  param_name: str) -> None:
    """
    Validate that a value is of the expected type.
    
    Args:
        value: The value to check
        expected_type: The expected type(s)
        param_name: The parameter name for error messages
        
    Raises:
        InvalidTypeError: If the value is not of the expected type
    """
    if value is None:
        return
        
    if not isinstance(value, expected_type):
        raise InvalidTypeError(param_name, value, expected_type)


def validate_not_none(value: Any, param_name: str) -> None:
    """
    Validate that a value is not None.
    
    Args:
        value: The value to check
        param_name: The parameter name for error messages
        
    Raises:
        MissingParameterError: If the value is None
    """
    if value is None:
        raise MissingParameterError(param_name)


def validate_not_empty(value: Any, param_name: str) -> None:
    """
    Validate that a value is not empty (string, list, dict, etc).
    
    Args:
        value: The value to check
        param_name: The parameter name for error messages
        
    Raises:
        InvalidParameterError: If the value is empty
    """
    if value is None:
        return
        
    if hasattr(value, '__len__') and len(value) == 0:
        raise InvalidParameterError(
            param_name, value, "non-empty value"
        )


def validate_enum_value(value: Any, enum_class: Type[Enum], param_name: str) -> None:
    """
    Validate that a value is a valid member of an Enum.
    
    Args:
        value: The value to check
        enum_class: The Enum class to check against
        param_name: The parameter name for error messages
        
    Raises:
        InvalidParameterError: If the value is not a valid enum member
    """
    if value is None:
        return
        
    try:
        # Handle both enum values and strings/ints that can be converted to enum values
        if isinstance(value, enum_class):
            return
        enum_class(value)
    except (ValueError, TypeError):
        valid_values = ', '.join(str(item.value) for item in enum_class)
        raise InvalidParameterError(
            param_name, value, f"one of [{valid_values}]"
        )


def validate_one_of(value: Any, valid_values: List[Any], param_name: str) -> None:
    """
    Validate that a value is one of a set of valid values.
    
    Args:
        value: The value to check
        valid_values: List of valid values
        param_name: The parameter name for error messages
        
    Raises:
        InvalidParameterError: If the value is not in the list of valid values
    """
    if value is None:
        return
        
    if value not in valid_values:
        if len(valid_values) <= 10:
            valid_str = ', '.join(str(v) for v in valid_values)
        else:
            valid_str = f"{len(valid_values)} valid options"
        
        raise InvalidParameterError(
            param_name, value, f"one of [{valid_str}]"
        )


def validate_min_length(value: Any, min_length: int, param_name: str) -> None:
    """
    Validate that a value has at least the minimum length.
    
    Args:
        value: The value to check
        min_length: The minimum length required
        param_name: The parameter name for error messages
        
    Raises:
        InvalidParameterError: If the value is shorter than the minimum length
    """
    if value is None:
        return
        
    if hasattr(value, '__len__') and len(value) < min_length:
        raise InvalidParameterError(
            param_name, value, f"minimum length of {min_length}"
        )


def validate_max_length(value: Any, max_length: int, param_name: str) -> None:
    """
    Validate that a value has at most the maximum length.
    
    Args:
        value: The value to check
        max_length: The maximum length allowed
        param_name: The parameter name for error messages
        
    Raises:
        InvalidParameterError: If the value is longer than the maximum length
    """
    if value is None:
        return
        
    if hasattr(value, '__len__') and len(value) > max_length:
        raise InvalidParameterError(
            param_name, value, f"maximum length of {max_length}"
        )


def validate_regex(value: str, pattern: Union[str, Pattern], param_name: str) -> None:
    """
    Validate that a string matches a regular expression pattern.
    
    Args:
        value: The string to check
        pattern: The regex pattern to match against
        param_name: The parameter name for error messages
        
    Raises:
        InvalidParameterError: If the string doesn't match the pattern
    """
    if value is None:
        return
        
    if not isinstance(value, str):
        raise InvalidTypeError(param_name, value, str)
        
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
        
    if not pattern.match(value):
        raise InvalidParameterError(
            param_name, value, f"string matching pattern '{pattern.pattern}'"
        )


def validate_min_value(value: Union[int, float], min_value: Union[int, float], 
                      param_name: str) -> None:
    """
    Validate that a numeric value is at least the minimum value.
    
    Args:
        value: The number to check
        min_value: The minimum value allowed
        param_name: The parameter name for error messages
        
    Raises:
        InvalidParameterError: If the value is less than the minimum value
    """
    if value is None:
        return
        
    if not isinstance(value, (int, float)):
        raise InvalidTypeError(param_name, value, (int, float))
        
    if value < min_value:
        raise InvalidParameterError(
            param_name, value, f"minimum value of {min_value}"
        )


def validate_max_value(value: Union[int, float], max_value: Union[int, float], 
                      param_name: str) -> None:
    """
    Validate that a numeric value is at most the maximum value.
    
    Args:
        value: The number to check
        max_value: The maximum value allowed
        param_name: The parameter name for error messages
        
    Raises:
        InvalidParameterError: If the value is greater than the maximum value
    """
    if value is None:
        return
        
    if not isinstance(value, (int, float)):
        raise InvalidTypeError(param_name, value, (int, float))
        
    if value > max_value:
        raise InvalidParameterError(
            param_name, value, f"maximum value of {max_value}"
        )


def validate_range(value: Union[int, float], min_value: Union[int, float], 
                  max_value: Union[int, float], param_name: str) -> None:
    """
    Validate that a numeric value is within a specified range.
    
    Args:
        value: The number to check
        min_value: The minimum value allowed (inclusive)
        max_value: The maximum value allowed (inclusive)
        param_name: The parameter name for error messages
        
    Raises:
        InvalidParameterError: If the value is outside the allowed range
    """
    if value is None:
        return
        
    validate_min_value(value, min_value, param_name)
    validate_max_value(value, max_value, param_name)


def validate_unique_items(value: Any, param_name: str) -> None:
    """
    Validate that a collection contains unique items.
    
    Args:
        value: The collection to check
        param_name: The parameter name for error messages
        
    Raises:
        InvalidParameterError: If the collection contains duplicate items
    """
    if value is None:
        return
        
    if not hasattr(value, '__iter__'):
        raise InvalidTypeError(param_name, value, "iterable")
        
    seen = set()
    duplicates = []
    
    for item in value:
        if item in seen and item not in duplicates:
            duplicates.append(item)
        else:
            try:
                seen.add(item)
            except TypeError:
                # If the item is unhashable, we can't efficiently check uniqueness
                # For now, we'll skip this check
                return
    
    if duplicates:
        if len(duplicates) == 1:
            raise InvalidParameterError(
                param_name, value, f"collection without duplicate item: {duplicates[0]}"
            )
        else:
            dup_str = ', '.join(str(d) for d in duplicates[:3])
            if len(duplicates) > 3:
                dup_str += f", ... ({len(duplicates) - 3} more)"
            raise InvalidParameterError(
                param_name, value, f"collection without duplicates: {dup_str}"
            )


# ===== Complex Validator Functions =====

def validate_dict_schema(value: Dict[Any, Any], schema: Dict[str, Dict[str, Any]], 
                         param_name: str) -> None:
    """
    Validate a dictionary against a schema.
    
    The schema is a dictionary where each key is a field name and each value is a
    dictionary of validation rules for that field.
    
    Example schema:
    ```
    {
        "name": {"type": str, "required": True, "not_empty": True},
        "age": {"type": int, "min_value": 0, "max_value": 120},
        "tags": {"type": list, "required": False, "item_validator": {"type": str}}
    }
    ```
    
    Args:
        value: The dictionary to validate
        schema: The schema to validate against
        param_name: The parameter name for error messages
        
    Raises:
        ValidationError: If the dictionary doesn't match the schema
    """
    if value is None:
        return
        
    if not isinstance(value, dict):
        raise InvalidTypeError(param_name, value, dict)
    
    # Check for required fields
    for field_name, field_schema in schema.items():
        if field_schema.get('required', False) and field_name not in value:
            raise MissingParameterError(f"{param_name}.{field_name}")
    
    # Validate each field in the dictionary
    for field_name, field_value in value.items():
        if field_name not in schema:
            # If allow_unknown_fields is False, raise an error for unknown fields
            if schema.get('__allow_unknown_fields', True) is False:
                raise InvalidParameterError(
                    param_name, field_name, f"known field in schema: {', '.join(schema.keys())}"
                )
            continue
        
        field_schema = schema[field_name]
        field_param_name = f"{param_name}.{field_name}"
        
        # Type check
        if 'type' in field_schema:
            validate_type(field_value, field_schema['type'], field_param_name)
        
        # Skip further validation if None and not required
        if field_value is None and not field_schema.get('required', False):
            continue
        
        # Not empty check
        if field_schema.get('not_empty', False):
            validate_not_empty(field_value, field_param_name)
        
        # Min/max length checks
        if 'min_length' in field_schema:
            validate_min_length(field_value, field_schema['min_length'], field_param_name)
        
        if 'max_length' in field_schema:
            validate_max_length(field_value, field_schema['max_length'], field_param_name)
        
        # Regex pattern check
        if 'pattern' in field_schema:
            validate_regex(field_value, field_schema['pattern'], field_param_name)
        
        # Min/max value checks
        if 'min_value' in field_schema:
            validate_min_value(field_value, field_schema['min_value'], field_param_name)
        
        if 'max_value' in field_schema:
            validate_max_value(field_value, field_schema['max_value'], field_param_name)
        
        # One of check
        if 'one_of' in field_schema:
            validate_one_of(field_value, field_schema['one_of'], field_param_name)
        
        # Enum check
        if 'enum' in field_schema:
            validate_enum_value(field_value, field_schema['enum'], field_param_name)
        
        # Unique items check
        if field_schema.get('unique_items', False):
            validate_unique_items(field_value, field_param_name)
        
        # Item validator for lists/collections
        if 'item_validator' in field_schema and hasattr(field_value, '__iter__'):
            item_schema = field_schema['item_validator']
            for i, item in enumerate(field_value):
                item_param_name = f"{field_param_name}[{i}]"
                
                # Type check for items
                if 'type' in item_schema:
                    validate_type(item, item_schema['type'], item_param_name)
                
                # Other validators for items
                if 'not_empty' in item_schema and item_schema['not_empty']:
                    validate_not_empty(item, item_param_name)
                
                if 'pattern' in item_schema:
                    validate_regex(item, item_schema['pattern'], item_param_name)
                
                if 'min_value' in item_schema:
                    validate_min_value(item, item_schema['min_value'], item_param_name)
                
                if 'max_value' in item_schema:
                    validate_max_value(item, item_schema['max_value'], item_param_name)
                
                if 'one_of' in item_schema:
                    validate_one_of(item, item_schema['one_of'], item_param_name)
                
                if 'enum' in item_schema:
                    validate_enum_value(item, item_schema['enum'], item_param_name)
        
        # Nested schema for dictionaries
        if 'schema' in field_schema and isinstance(field_value, dict):
            validate_dict_schema(field_value, field_schema['schema'], field_param_name)
        
        # Custom validator
        if 'custom_validator' in field_schema and callable(field_schema['custom_validator']):
            try:
                field_schema['custom_validator'](field_value, field_param_name)
            except ValidationError:
                # Pass through validation errors
                raise
            except Exception as e:
                # Wrap other exceptions in a ValidationError
                raise ValidationError(
                    f"Custom validation failed for {field_param_name}: {str(e)}",
                    parameter=field_param_name,
                    value=field_value
                ) from e


def validate_list_items(value: List[Any], item_validator: Dict[str, Any], 
                       param_name: str) -> None:
    """
    Validate each item in a list against a set of validation rules.
    
    Args:
        value: The list to validate
        item_validator: Dictionary of validation rules for each item
        param_name: The parameter name for error messages
        
    Raises:
        ValidationError: If any item fails validation
    """
    if value is None:
        return
        
    if not isinstance(value, (list, tuple)):
        raise InvalidTypeError(param_name, value, (list, tuple))
    
    for i, item in enumerate(value):
        item_param_name = f"{param_name}[{i}]"
        
        # Type check
        if 'type' in item_validator:
            validate_type(item, item_validator['type'], item_param_name)
        
        # Not empty check
        if item_validator.get('not_empty', False):
            validate_not_empty(item, item_param_name)
        
        # Min/max length checks
        if 'min_length' in item_validator:
            validate_min_length(item, item_validator['min_length'], item_param_name)
        
        if 'max_length' in item_validator:
            validate_max_length(item, item_validator['max_length'], item_param_name)
        
        # Regex pattern check
        if 'pattern' in item_validator:
            validate_regex(item, item_validator['pattern'], item_param_name)
        
        # Min/max value checks
        if 'min_value' in item_validator:
            validate_min_value(item, item_validator['min_value'], item_param_name)
        
        if 'max_value' in item_validator:
            validate_max_value(item, item_validator['max_value'], item_param_name)
        
        # One of check
        if 'one_of' in item_validator:
            validate_one_of(item, item_validator['one_of'], item_param_name)
        
        # Enum check
        if 'enum' in item_validator:
            validate_enum_value(item, item_validator['enum'], item_param_name)
        
        # Nested schema for dictionaries
        if 'schema' in item_validator and isinstance(item, dict):
            validate_dict_schema(item, item_validator['schema'], item_param_name)
        
        # Custom validator
        if 'custom_validator' in item_validator and callable(item_validator['custom_validator']):
            try:
                item_validator['custom_validator'](item, item_param_name)
            except ValidationError:
                # Pass through validation errors
                raise
            except Exception as e:
                # Wrap other exceptions in a ValidationError
                raise ValidationError(
                    f"Custom validation failed for {item_param_name}: {str(e)}",
                    parameter=item_param_name,
                    value=item
                ) from e


# ===== Decorator-based Validation =====

def validate_params(**param_validators: Dict[str, Any]) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to validate function parameters according to specified rules.
    
    Example:
    ```python
    @validate_params(
        code={"type": str, "not_empty": True},
        element_type={"type": str, "one_of": CodeElementType.values()},
        element_name={"type": str, "optional": True}
    )
    def find_element(code, element_type, element_name=None):
        # Implementation...
    ```
    
    Args:
        **param_validators: Parameter names mapped to dictionaries of validation rules
        
    Returns:
        A decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Get the function's signature to check parameter names and defaults
        sig = inspect.signature(func)
        
        # Verify that all parameters in param_validators exist in the function signature
        for param_name in param_validators:
            if param_name not in sig.parameters:
                raise ValueError(
                    f"Parameter '{param_name}' specified in validator does not exist in function {func.__name__}"
                )
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Create a mapping of parameter names to values
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            params = bound_args.arguments
            
            # Validate each parameter
            for param_name, validator in param_validators.items():
                if param_name not in params:
                    continue
                
                value = params[param_name]
                
                # Skip validation if parameter is optional and None
                if validator.get('optional', False) and value is None:
                    continue
                
                # Required parameter check (if not optional and no default)
                param_def = sig.parameters.get(param_name)
                is_required = (not validator.get('optional', False) and 
                              param_def and param_def.default is inspect.Parameter.empty)
                
                if is_required and value is None:
                    raise MissingParameterError(param_name)
                
                # Type check
                if 'type' in validator:
                    validate_type(value, validator['type'], param_name)
                
                # Skip further validation if None
                if value is None:
                    continue
                
                # Not empty check
                if validator.get('not_empty', False):
                    validate_not_empty(value, param_name)
                
                # Min/max length checks
                if 'min_length' in validator:
                    validate_min_length(value, validator['min_length'], param_name)
                
                if 'max_length' in validator:
                    validate_max_length(value, validator['max_length'], param_name)
                
                # Regex pattern check
                if 'pattern' in validator:
                    validate_regex(value, validator['pattern'], param_name)
                
                # Min/max value checks
                if 'min_value' in validator:
                    validate_min_value(value, validator['min_value'], param_name)
                
                if 'max_value' in validator:
                    validate_max_value(value, validator['max_value'], param_name)
                
                # One of check
                if 'one_of' in validator:
                    validate_one_of(value, validator['one_of'], param_name)
                
                # Enum check
                if 'enum' in validator:
                    validate_enum_value(value, validator['enum'], param_name)
                
                # Unique items check
                if validator.get('unique_items', False):
                    validate_unique_items(value, param_name)
                
                # Item validator for lists/collections
                if 'item_validator' in validator and hasattr(value, '__iter__'):
                    validate_list_items(value, validator['item_validator'], param_name)
                
                # Schema validator for dictionaries
                if 'schema' in validator and isinstance(value, dict):
                    validate_dict_schema(value, validator['schema'], param_name)
                
                # Custom validator
                if 'custom_validator' in validator and callable(validator['custom_validator']):
                    try:
                        validator['custom_validator'](value, param_name)
                    except ValidationError:
                        # Pass through validation errors
                        raise
                    except Exception as e:
                        # Wrap other exceptions in a ValidationError
                        raise ValidationError(
                            f"Custom validation failed for {param_name}: {str(e)}",
                            parameter=param_name,
                            value=value
                        ) from e
            
            # Call the original function if all validations pass
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def validate_return(validator: Dict[str, Any]) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to validate a function's return value.
    
    Example:
    ```python
    @validate_return({"type": str, "not_empty": True})
    def get_element_name():
        # Implementation...
    ```
    
    Args:
        validator: Dictionary of validation rules for the return value
        
    Returns:
        A decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            result = func(*args, **kwargs)
            
            # Skip validation if the result is None and optional
            if validator.get('optional', False) and result is None:
                return result
            
            # Type check
            if 'type' in validator:
                validate_type(result, validator['type'], 'return value')
            
            # Skip further validation if None
            if result is None:
                return result
            
            # Not empty check
            if validator.get('not_empty', False):
                validate_not_empty(result, 'return value')
            
            # Min/max length checks
            if 'min_length' in validator:
                validate_min_length(result, validator['min_length'], 'return value')
            
            if 'max_length' in validator:
                validate_max_length(result, validator['max_length'], 'return value')
            
            # Regex pattern check
            if 'pattern' in validator:
                validate_regex(result, validator['pattern'], 'return value')
            
            # Min/max value checks
            if 'min_value' in validator:
                validate_min_value(result, validator['min_value'], 'return value')
            
            if 'max_value' in validator:
                validate_max_value(result, validator['max_value'], 'return value')
            
            # One of check
            if 'one_of' in validator:
                validate_one_of(result, validator['one_of'], 'return value')
            
            # Enum check
            if 'enum' in validator:
                validate_enum_value(result, validator['enum'], 'return value')
            
            # Unique items check
            if validator.get('unique_items', False):
                validate_unique_items(result, 'return value')
            
            # Item validator for lists/collections
            if 'item_validator' in validator and hasattr(result, '__iter__'):
                validate_list_items(result, validator['item_validator'], 'return value')
            
            # Schema validator for dictionaries
            if 'schema' in validator and isinstance(result, dict):
                validate_dict_schema(result, validator['schema'], 'return value')
            
            # Custom validator
            if 'custom_validator' in validator and callable(validator['custom_validator']):
                try:
                    validator['custom_validator'](result, 'return value')
                except ValidationError:
                    # Pass through validation errors
                    raise
                except Exception as e:
                    # Wrap other exceptions in a ValidationError
                    raise ValidationError(
                        f"Custom validation failed for return value: {str(e)}",
                        parameter='return value',
                        value=result
                    ) from e
            
            return result
        
        return wrapper
    
    return decorator


# ===== Convenience Functions =====

def create_validator(*validators: Callable) -> Callable[[Any, str], None]:
    """
    Create a composite validator from multiple validator functions.
    
    Example:
    ```python
    string_validator = create_validator(
        lambda v, p: validate_type(v, str, p),
        lambda v, p: validate_not_empty(v, p),
        lambda v, p: validate_max_length(v, 100, p)
    )
    ```
    
    Args:
        *validators: A sequence of validator functions, each taking a value and parameter name
        
    Returns:
        A function that applies all the validators in sequence
    """
    def validator(value: Any, param_name: str) -> None:
        for v in validators:
            v(value, param_name)
    
    return validator


def create_schema_validator(schema: Dict[str, Any]) -> Callable[[Dict[str, Any], str], None]:
    """
    Create a validator function for a specific schema.
    
    Example:
    ```python
    config_validator = create_schema_validator({
        "api_key": {"type": str, "required": True, "not_empty": True},
        "timeout": {"type": int, "min_value": 1, "max_value": 600, "required": False},
        "debug": {"type": bool, "required": False}
    })
    ```
    
    Args:
        schema: The schema to validate against
        
    Returns:
        A function that validates a dictionary against the schema
    """
    def validator(value: Dict[str, Any], param_name: str) -> None:
        validate_dict_schema(value, schema, param_name)
    
    return validator


# ===== Prebuilt Validators =====

# String validators
string_validator = create_validator(
    lambda v, p: validate_type(v, str, p)
)

non_empty_string_validator = create_validator(
    lambda v, p: validate_type(v, str, p),
    lambda v, p: validate_not_empty(v, p)
)

# Numeric validators
integer_validator = create_validator(
    lambda v, p: validate_type(v, int, p)
)

positive_integer_validator = create_validator(
    lambda v, p: validate_type(v, int, p),
    lambda v, p: validate_min_value(v, 1, p)
)

non_negative_integer_validator = create_validator(
    lambda v, p: validate_type(v, int, p),
    lambda v, p: validate_min_value(v, 0, p)
)

float_validator = create_validator(
    lambda v, p: validate_type(v, float, p)
)

numeric_validator = create_validator(
    lambda v, p: validate_type(v, (int, float), p)
)

# Collection validators
list_validator = create_validator(
    lambda v, p: validate_type(v, list, p)
)

non_empty_list_validator = create_validator(
    lambda v, p: validate_type(v, list, p),
    lambda v, p: validate_not_empty(v, p)
)

dict_validator = create_validator(
    lambda v, p: validate_type(v, dict, p)
)

non_empty_dict_validator = create_validator(
    lambda v, p: validate_type(v, dict, p),
    lambda v, p: validate_not_empty(v, p)
)

# Boolean validator
boolean_validator = create_validator(
    lambda v, p: validate_type(v, bool, p)
)
