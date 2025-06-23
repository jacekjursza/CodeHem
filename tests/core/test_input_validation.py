"""
Tests for the input validation framework.
"""
import re
import unittest
from enum import Enum
from typing import Dict, List, Any, Optional

from codehem.core.error_handling import (
    InvalidParameterError,
    InvalidTypeError,
    MissingParameterError,
    ValidationError
)
from codehem.core.input_validation import (
    validate_type,
    validate_not_none,
    validate_not_empty,
    validate_enum_value,
    validate_one_of,
    validate_min_length,
    validate_max_length,
    validate_regex,
    validate_min_value,
    validate_max_value,
    validate_range,
    validate_unique_items,
    validate_dict_schema,
    validate_list_items,
    validate_params,
    validate_return,
    create_validator,
    create_schema_validator,
    string_validator,
    non_empty_string_validator,
    integer_validator,
    positive_integer_validator,
    non_negative_integer_validator,
    float_validator,
    numeric_validator,
    list_validator,
    non_empty_list_validator,
    dict_validator,
    non_empty_dict_validator,
    boolean_validator
)


class SampleEnum(Enum):
    """Test enum for validation tests."""
    ONE = 1
    TWO = 2
    THREE = 3


class BasicValidatorsTest(unittest.TestCase):
    """Tests for basic validator functions."""

    def test_validate_type(self):
        """Test validate_type function."""
        # Valid cases
        validate_type("test", str, "param")
        validate_type(123, int, "param")
        validate_type(123.45, (int, float), "param")
        validate_type(None, str, "param")  # None is valid for any type

        # Invalid cases
        with self.assertRaises(InvalidTypeError):
            validate_type("test", int, "param")
        with self.assertRaises(InvalidTypeError):
            validate_type(123, str, "param")
        
        # Check error message
        try:
            validate_type(123, str, "param")
        except InvalidTypeError as e:
            self.assertIn("param", str(e))
            self.assertIn("int", str(e))
            self.assertIn("str", str(e))

    def test_validate_not_none(self):
        """Test validate_not_none function."""
        # Valid case
        validate_not_none("test", "param")
        validate_not_none(0, "param")
        validate_not_none(False, "param")
        validate_not_none([], "param")

        # Invalid case
        with self.assertRaises(MissingParameterError):
            validate_not_none(None, "param")
        
        # Check error message
        try:
            validate_not_none(None, "param")
        except MissingParameterError as e:
            self.assertIn("param", str(e))

    def test_validate_not_empty(self):
        """Test validate_not_empty function."""
        # Valid cases
        validate_not_empty("test", "param")
        validate_not_empty([1, 2, 3], "param")
        validate_not_empty({"key": "value"}, "param")
        validate_not_empty(None, "param")  # None is not considered empty

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            validate_not_empty("", "param")
        with self.assertRaises(InvalidParameterError):
            validate_not_empty([], "param")
        with self.assertRaises(InvalidParameterError):
            validate_not_empty({}, "param")
        
        # Check error message
        try:
            validate_not_empty("", "param")
        except InvalidParameterError as e:
            self.assertIn("param", str(e))
            self.assertIn("non-empty", str(e).lower())

    def test_validate_enum_value(self):
        """Test validate_enum_value function."""
        # Valid cases
        validate_enum_value(SampleEnum.ONE, SampleEnum, "param")
        validate_enum_value(1, SampleEnum, "param")
        validate_enum_value(None, SampleEnum, "param")

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            validate_enum_value(4, SampleEnum, "param")
        with self.assertRaises(InvalidParameterError):
            validate_enum_value("FOUR", SampleEnum, "param")
        
        # Check error message
        try:
            validate_enum_value(4, SampleEnum, "param")
        except InvalidParameterError as e:
            self.assertIn("param", str(e))
            self.assertIn("1", str(e))
            self.assertIn("2", str(e))
            self.assertIn("3", str(e))

    def test_validate_one_of(self):
        """Test validate_one_of function."""
        # Valid cases
        validate_one_of("a", ["a", "b", "c"], "param")
        validate_one_of(1, [1, 2, 3], "param")
        validate_one_of(None, [1, 2, 3], "param")

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            validate_one_of("d", ["a", "b", "c"], "param")
        with self.assertRaises(InvalidParameterError):
            validate_one_of(4, [1, 2, 3], "param")
        
        # Check error message
        try:
            validate_one_of("d", ["a", "b", "c"], "param")
        except InvalidParameterError as e:
            self.assertIn("param", str(e))
            self.assertIn("a", str(e))
            self.assertIn("b", str(e))
            self.assertIn("c", str(e))

    def test_validate_min_length(self):
        """Test validate_min_length function."""
        # Valid cases
        validate_min_length("test", 3, "param")
        validate_min_length([1, 2, 3], 3, "param")
        validate_min_length(None, 3, "param")

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            validate_min_length("te", 3, "param")
        with self.assertRaises(InvalidParameterError):
            validate_min_length([1, 2], 3, "param")
        
        # Check error message
        try:
            validate_min_length("te", 3, "param")
        except InvalidParameterError as e:
            self.assertIn("param", str(e))
            self.assertIn("3", str(e))

    def test_validate_max_length(self):
        """Test validate_max_length function."""
        # Valid cases
        validate_max_length("test", 5, "param")
        validate_max_length([1, 2, 3], 5, "param")
        validate_max_length(None, 5, "param")

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            validate_max_length("test too long", 5, "param")
        with self.assertRaises(InvalidParameterError):
            validate_max_length([1, 2, 3, 4, 5, 6], 5, "param")
        
        # Check error message
        try:
            validate_max_length("test too long", 5, "param")
        except InvalidParameterError as e:
            self.assertIn("param", str(e))
            self.assertIn("5", str(e))

    def test_validate_regex(self):
        """Test validate_regex function."""
        # Valid cases
        validate_regex("test123", r"^[a-z]+\d+$", "param")
        validate_regex("test123", re.compile(r"^[a-z]+\d+$"), "param")
        validate_regex(None, r"^[a-z]+\d+$", "param")

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            validate_regex("123test", r"^[a-z]+\d+$", "param")
        with self.assertRaises(InvalidTypeError):
            validate_regex(123, r"^[a-z]+\d+$", "param")
        
        # Check error message
        try:
            validate_regex("123test", r"^[a-z]+\d+$", "param")
        except InvalidParameterError as e:
            self.assertIn("param", str(e))
            self.assertIn("pattern", str(e).lower())

    def test_validate_min_value(self):
        """Test validate_min_value function."""
        # Valid cases
        validate_min_value(5, 3, "param")
        validate_min_value(3, 3, "param")
        validate_min_value(None, 3, "param")

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            validate_min_value(2, 3, "param")
        with self.assertRaises(InvalidTypeError):
            validate_min_value("3", 3, "param")
        
        # Check error message
        try:
            validate_min_value(2, 3, "param")
        except InvalidParameterError as e:
            self.assertIn("param", str(e))
            self.assertIn("3", str(e))

    def test_validate_max_value(self):
        """Test validate_max_value function."""
        # Valid cases
        validate_max_value(3, 5, "param")
        validate_max_value(5, 5, "param")
        validate_max_value(None, 5, "param")

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            validate_max_value(6, 5, "param")
        with self.assertRaises(InvalidTypeError):
            validate_max_value("3", 5, "param")
        
        # Check error message
        try:
            validate_max_value(6, 5, "param")
        except InvalidParameterError as e:
            self.assertIn("param", str(e))
            self.assertIn("5", str(e))

    def test_validate_range(self):
        """Test validate_range function."""
        # Valid cases
        validate_range(3, 1, 5, "param")
        validate_range(1, 1, 5, "param")
        validate_range(5, 1, 5, "param")
        validate_range(None, 1, 5, "param")

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            validate_range(0, 1, 5, "param")
        with self.assertRaises(InvalidParameterError):
            validate_range(6, 1, 5, "param")
        with self.assertRaises(InvalidTypeError):
            validate_range("3", 1, 5, "param")

    def test_validate_unique_items(self):
        """Test validate_unique_items function."""
        # Valid cases
        validate_unique_items([1, 2, 3], "param")
        validate_unique_items({"a", "b", "c"}, "param")
        validate_unique_items("abc", "param")
        validate_unique_items(None, "param")

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            validate_unique_items([1, 2, 3, 1], "param")
        with self.assertRaises(InvalidParameterError):
            validate_unique_items("abca", "param")
        
        # Check error message
        try:
            validate_unique_items([1, 2, 3, 1], "param")
        except InvalidParameterError as e:
            self.assertIn("param", str(e))
            self.assertIn("duplicate", str(e).lower())
            self.assertIn("1", str(e))


class ComplexValidatorsTest(unittest.TestCase):
    """Tests for complex validator functions."""

    def test_validate_dict_schema(self):
        """Test validate_dict_schema function."""
        schema = {
            "name": {"type": str, "required": True, "not_empty": True},
            "age": {"type": int, "min_value": 0, "max_value": 120},
            "tags": {"type": list, "required": False, "item_validator": {"type": str}}
        }

        # Valid cases
        validate_dict_schema({"name": "John", "age": 30, "tags": ["a", "b"]}, schema, "param")
        validate_dict_schema({"name": "John", "age": 30}, schema, "param")
        validate_dict_schema({"name": "John", "tags": ["a", "b"]}, schema, "param")
        validate_dict_schema({"name": "John"}, schema, "param")
        validate_dict_schema(None, schema, "param")

        # Invalid cases
        with self.assertRaises(MissingParameterError):
            validate_dict_schema({}, schema, "param")
        with self.assertRaises(MissingParameterError):
            validate_dict_schema({"age": 30}, schema, "param")
        with self.assertRaises(InvalidParameterError):
            validate_dict_schema({"name": ""}, schema, "param")
        with self.assertRaises(InvalidParameterError):
            validate_dict_schema({"name": "John", "age": -1}, schema, "param")
        with self.assertRaises(InvalidParameterError):
            validate_dict_schema({"name": "John", "age": 121}, schema, "param")
        with self.assertRaises(InvalidTypeError):
            validate_dict_schema({"name": "John", "tags": "not a list"}, schema, "param")
        with self.assertRaises(InvalidTypeError):
            validate_dict_schema({"name": "John", "tags": [1, 2, 3]}, schema, "param")

    def test_validate_list_items(self):
        """Test validate_list_items function."""
        item_validator = {
            "type": str,
            "not_empty": True,
            "min_length": 2,
            "max_length": 5
        }

        # Valid cases
        validate_list_items(["ab", "abc", "abcd", "abcde"], item_validator, "param")
        validate_list_items([], item_validator, "param")
        validate_list_items(None, item_validator, "param")

        # Invalid cases
        with self.assertRaises(InvalidTypeError):
            validate_list_items("not a list", item_validator, "param")
        with self.assertRaises(InvalidTypeError):
            validate_list_items([1, 2, 3], item_validator, "param")
        with self.assertRaises(InvalidParameterError):
            validate_list_items(["", "ab", "abc"], item_validator, "param")
        with self.assertRaises(InvalidParameterError):
            validate_list_items(["a", "ab", "abc"], item_validator, "param")
        with self.assertRaises(InvalidParameterError):
            validate_list_items(["ab", "abcdef"], item_validator, "param")


class DecoratorValidatorsTest(unittest.TestCase):
    """Tests for decorator-based validators."""

    def test_validate_params_decorator(self):
        """Test validate_params decorator."""
        
        @validate_params(
            name={"type": str, "not_empty": True},
            age={"type": int, "min_value": 0, "max_value": 120, "optional": True},
            tags={"type": list, "item_validator": {"type": str}, "optional": True}
        )
        def process_person(name, age=None, tags=None):
            return {"name": name, "age": age, "tags": tags}

        # Valid cases
        self.assertEqual(
            process_person("John", 30, ["a", "b"]),
            {"name": "John", "age": 30, "tags": ["a", "b"]}
        )
        self.assertEqual(
            process_person("John"),
            {"name": "John", "age": None, "tags": None}
        )
        self.assertEqual(
            process_person("John", tags=["a", "b"]),
            {"name": "John", "age": None, "tags": ["a", "b"]}
        )

        # Invalid cases
        with self.assertRaises(InvalidParameterError):
            process_person("")
        with self.assertRaises(InvalidTypeError):
            process_person(123)
        with self.assertRaises(InvalidTypeError):
            process_person("John", "30")
        with self.assertRaises(InvalidParameterError):
            process_person("John", -1)
        with self.assertRaises(InvalidParameterError):
            process_person("John", 121)
        with self.assertRaises(InvalidTypeError):
            process_person("John", 30, "not a list")
        with self.assertRaises(InvalidTypeError):
            process_person("John", 30, [1, 2, 3])

    def test_validate_return_decorator(self):
        """Test validate_return decorator."""
        
        @validate_return({"type": dict, "schema": {
            "name": {"type": str, "not_empty": True},
            "age": {"type": int, "min_value": 0, "max_value": 120, "optional": True}
        }})
        def get_person(valid=True):
            if valid:
                return {"name": "John", "age": 30}
            else:
                return {"name": "", "age": 30}

        # Valid case
        self.assertEqual(get_person(), {"name": "John", "age": 30})

        # Invalid case
        with self.assertRaises(InvalidParameterError):
            get_person(False)


class UtilityFunctionsTest(unittest.TestCase):
    """Tests for utility functions."""

    def test_create_validator(self):
        """Test create_validator function."""
        # Create a custom validator for positive integers
        positive_int_validator = create_validator(
            lambda v, p: validate_type(v, int, p),
            lambda v, p: validate_min_value(v, 1, p)
        )

        # Valid case
        positive_int_validator(5, "param")

        # Invalid cases
        with self.assertRaises(InvalidTypeError):
            positive_int_validator("5", "param")
        with self.assertRaises(InvalidParameterError):
            positive_int_validator(0, "param")

    def test_create_schema_validator(self):
        """Test create_schema_validator function."""
        # Create a schema validator for a person
        person_schema = {
            "name": {"type": str, "not_empty": True},
            "age": {"type": int, "min_value": 0, "max_value": 120, "optional": True}
        }
        person_validator = create_schema_validator(person_schema)

        # Valid cases
        person_validator({"name": "John", "age": 30}, "person")
        person_validator({"name": "John"}, "person")

        # Invalid cases
        with self.assertRaises(MissingParameterError):
            person_validator({}, "person")
        with self.assertRaises(InvalidParameterError):
            person_validator({"name": ""}, "person")


class PrebuiltValidatorsTest(unittest.TestCase):
    """Tests for prebuilt validators."""

    def test_string_validators(self):
        """Test string validators."""
        # string_validator
        string_validator("test", "param")
        with self.assertRaises(InvalidTypeError):
            string_validator(123, "param")

        # non_empty_string_validator
        non_empty_string_validator("test", "param")
        with self.assertRaises(InvalidParameterError):
            non_empty_string_validator("", "param")

    def test_numeric_validators(self):
        """Test numeric validators."""
        # integer_validator
        integer_validator(123, "param")
        with self.assertRaises(InvalidTypeError):
            integer_validator(123.45, "param")

        # positive_integer_validator
        positive_integer_validator(5, "param")
        with self.assertRaises(InvalidParameterError):
            positive_integer_validator(0, "param")

        # non_negative_integer_validator
        non_negative_integer_validator(0, "param")
        with self.assertRaises(InvalidParameterError):
            non_negative_integer_validator(-1, "param")

        # float_validator
        float_validator(123.45, "param")
        with self.assertRaises(InvalidTypeError):
            float_validator(123, "param")

        # numeric_validator
        numeric_validator(123, "param")
        numeric_validator(123.45, "param")
        with self.assertRaises(InvalidTypeError):
            numeric_validator("123", "param")

    def test_collection_validators(self):
        """Test collection validators."""
        # list_validator
        list_validator([1, 2, 3], "param")
        with self.assertRaises(InvalidTypeError):
            list_validator((1, 2, 3), "param")

        # non_empty_list_validator
        non_empty_list_validator([1, 2, 3], "param")
        with self.assertRaises(InvalidParameterError):
            non_empty_list_validator([], "param")

        # dict_validator
        dict_validator({"key": "value"}, "param")
        with self.assertRaises(InvalidTypeError):
            dict_validator([1, 2, 3], "param")

        # non_empty_dict_validator
        non_empty_dict_validator({"key": "value"}, "param")
        with self.assertRaises(InvalidParameterError):
            non_empty_dict_validator({}, "param")

    def test_boolean_validator(self):
        """Test boolean validator."""
        boolean_validator(True, "param")
        boolean_validator(False, "param")
        with self.assertRaises(InvalidTypeError):
            boolean_validator(1, "param")
        with self.assertRaises(InvalidTypeError):
            boolean_validator("true", "param")


class IntegrationTest(unittest.TestCase):
    """Integration tests for the validation framework."""

    def test_real_world_example(self):
        """Test a real-world example of using the validation framework."""
        # Define a complex validation for a CodeHem-like function
        @validate_params(
            code={"type": str, "not_empty": True},
            element_type={"type": str, "one_of": ["class", "method", "function", "property"]},
            element_name={"type": str, "optional": True},
            parent_name={"type": str, "optional": True},
            options={"type": dict, "optional": True, "schema": {
                "include_decorators": {"type": bool, "optional": True},
                "include_docs": {"type": bool, "optional": True},
                "max_depth": {"type": int, "min_value": 1, "max_value": 10, "optional": True}
            }}
        )
        def find_element(code, element_type, element_name=None, parent_name=None, options=None):
            # This is just a mock implementation
            return {
                "code": code,
                "element_type": element_type,
                "element_name": element_name,
                "parent_name": parent_name,
                "options": options
            }

        # Valid calls
        self.assertEqual(
            find_element("code sample", "class", "MyClass"),
            {
                "code": "code sample",
                "element_type": "class",
                "element_name": "MyClass",
                "parent_name": None,
                "options": None
            }
        )
        
        self.assertEqual(
            find_element("code sample", "method", "my_method", "MyClass", 
                        {"include_decorators": True, "max_depth": 5}),
            {
                "code": "code sample",
                "element_type": "method",
                "element_name": "my_method",
                "parent_name": "MyClass",
                "options": {"include_decorators": True, "max_depth": 5}
            }
        )

        # Invalid calls
        with self.assertRaises(InvalidParameterError):
            find_element("", "class", "MyClass")  # Empty code
        
        with self.assertRaises(InvalidParameterError):
            find_element("code sample", "unknown_type", "MyClass")  # Invalid element type
        
        with self.assertRaises(InvalidParameterError):
            find_element("code sample", "class", "MyClass", options={
                "max_depth": 0  # Invalid option value
            })
        
        with self.assertRaises(InvalidParameterError):
            find_element("code sample", "class", "MyClass", options={
                "unknown_option": True,  # Unknown field is allowed by default
                "__allow_unknown_fields": False  # Disallow unknown fields
            })


if __name__ == "__main__":
    unittest.main()
