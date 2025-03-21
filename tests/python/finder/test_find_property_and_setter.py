import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_property_and_setter_together(python_finder):
    """Test finding both property getter and setter when they're adjacent."""
    example = TestHelper.load_example("property_and_setter_together.py", category="property")
    
    (start_line, end_line) = python_finder.find_property_and_setter(
        example.content,
        example.class_name,
        example.property_name,
        include_extra=example.include_extra
    )
    
    assert start_line == example.expected_start_line, f'Expected combined start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected combined end at line {example.expected_end_line}, got {end_line}'

def test_find_property_and_setter_separated(python_finder):
    """Test finding both property getter and setter when they're not adjacent."""
    example = TestHelper.load_example("property_and_setter_separated.py", category="property")
    
    (start_line, end_line) = python_finder.find_property_and_setter(
        example.content,
        example.class_name,
        example.property_name,
        include_extra=example.include_extra
    )
    
    assert start_line == example.expected_start_line, f'Expected combined start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected combined end at line {example.expected_end_line}, got {end_line}'

def test_find_property_and_setter_only_getter(python_finder):
    """Test finding property and setter when only the getter exists."""
    example = TestHelper.load_example("property_only_getter.py", category="property")
    
    (start_line, end_line) = python_finder.find_property_and_setter(
        example.content,
        example.class_name,
        example.property_name,
        include_extra=example.include_extra
    )
    
    assert start_line == example.expected_start_line, f'Expected getter start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected getter end at line {example.expected_end_line}, got {end_line}'

def test_find_property_and_setter_only_setter(python_finder):
    """Test finding property and setter when only the setter exists."""
    example = TestHelper.load_example("property_only_setter.py", category="property")
    
    (start_line, end_line) = python_finder.find_property_and_setter(
        example.content,
        example.class_name,
        example.property_name,
        include_extra=example.include_extra
    )
    
    assert start_line == example.expected_start_line, f'Expected setter start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected setter end at line {example.expected_end_line}, got {end_line}'

def test_find_property_and_setter_missing(python_finder):
    """Test finding property and setter when neither exists."""
    example = TestHelper.load_example("property_and_setter_missing.py", category="property")
    
    (start_line, end_line) = python_finder.find_property_and_setter(
        example.content,
        example.class_name,
        example.property_name
    )
    
    assert start_line == 0 and end_line == 0, 'Expected no lines when property does not exist'