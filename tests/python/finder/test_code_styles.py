import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_with_mixed_indentation(python_finder):
    """Test finding elements in code with mixed indentation styles."""
    example = TestHelper.load_example("mixed_indentation.py", category="code_style")
    
    (spaces_start, spaces_end) = python_finder.find_method(example.content, "MixedIndentClass", "spaces_method")
    assert spaces_start == example.metadata['spaces_method_start'], \
        f'Expected spaces_method start at line {example.metadata["spaces_method_start"]}, got {spaces_start}'
    
    (tabs_start, tabs_end) = python_finder.find_method(example.content, "MixedIndentClass", "tabs_method")
    assert tabs_start == example.metadata['tabs_method_start'], \
        f'Expected tabs_method start at line {example.metadata["tabs_method_start"]}, got {tabs_start}'

def test_find_with_comments(python_finder):
    """Test finding elements in code with various comments."""
    example = TestHelper.load_example("commented_code.py", category="code_style")
    
    (class_start, class_end) = python_finder.find_class(example.content, "CommentedClass")
    assert class_start == example.metadata['class_start'], \
        f'Expected class start at line {example.metadata["class_start"]}, got {class_start}'
    
    (method_start, method_end) = python_finder.find_method(example.content, "CommentedClass", "commented_method")
    assert method_start == example.metadata['method_start'], \
        f'Expected method start at line {example.metadata["method_start"]}, got {method_start}'
    
    (prop_start, prop_end) = python_finder.find_properties_section(example.content, "CommentedClass")
    assert prop_start == example.metadata['prop_start'], \
        f'Expected properties section start at line {example.metadata["prop_start"]}, got {prop_start}'

def test_find_with_docstrings(python_finder):
    """Test finding elements in code with docstrings."""
    example = TestHelper.load_example("docstring_code.py", category="code_style")
    
    (class_start, class_end) = python_finder.find_class(example.content, "DocstringClass")
    assert class_start == example.metadata['class_start'], \
        f'Expected class start at line {example.metadata["class_start"]}, got {class_start}'
    
    (method_start, method_end) = python_finder.find_method(example.content, "DocstringClass", "docstring_method")
    assert method_start == example.metadata['method_start'], \
        f'Expected method start at line {example.metadata["method_start"]}, got {method_start}'

def test_find_with_blank_lines(python_finder):
    """Test finding elements in code with various blank line patterns."""
    example = TestHelper.load_example("blank_lines_code.py", category="code_style")
    
    (class_start, class_end) = python_finder.find_class(example.content, "BlankLinesClass")
    assert class_start == example.metadata['class_start'], \
        f'Expected class start at line {example.metadata["class_start"]}, got {class_start}'
    
    (method1_start, method1_end) = python_finder.find_method(example.content, "BlankLinesClass", "method_with_blanks")
    assert method1_start == example.metadata['method1_start'], \
        f'Expected method_with_blanks start at line {example.metadata["method1_start"]}, got {method1_start}'
    
    (method2_start, method2_end) = python_finder.find_method(example.content, "BlankLinesClass", "another_method")
    assert method2_start == example.metadata['method2_start'], \
        f'Expected another_method start at line {example.metadata["method2_start"]}, got {method2_start}'