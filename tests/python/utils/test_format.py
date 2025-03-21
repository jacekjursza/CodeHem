from core.utils.format_utils import normalize_indentation, format_python_class_content, format_python_method_content, process_lines
from tests.helpers.code_examples import TestHelper

def test_normalize_indentation_default():
    example = TestHelper.load_example('indentation_default.py', category='format')
    result = normalize_indentation(example.metadata['original'])
    assert result == example.metadata['expected']

def test_normalize_indentation_mixed():
    example = TestHelper.load_example('indentation_mixed.py', category='format')
    result = normalize_indentation(example.metadata['original'])
    assert result == example.metadata['expected']

def test_normalize_indentation_empty_lines():
    example = TestHelper.load_example('indentation_empty_lines.py', category='format')
    result = normalize_indentation(example.metadata['original'])
    assert result == example.metadata['expected']

def test_normalize_indentation_custom():
    example = TestHelper.load_example('indentation_default.py', category='format')
    custom_expected = "def function():\n  if True:\n    print(\"Hello\")\n    "
    result = normalize_indentation(example.metadata['original'], '  ')
    assert result == custom_expected

def test_normalize_indentation_no_indent():
    example = TestHelper.load_example('indentation_no_indent.py', category='format')
    result = normalize_indentation(example.metadata['original'])
    assert result == example.metadata['expected']

def test_format_python_class_simple():
    example = TestHelper.load_example('python_class_simple.py', category='format')
    result = format_python_class_content(example.metadata['original'])
    assert result == example.metadata['expected']

def test_format_python_class_with_decorator():
    example = TestHelper.load_example('python_class_with_decorator.py', category='format')
    result = format_python_class_content(example.metadata['original'])
    assert result == example.metadata['expected']

def test_format_python_method_simple():
    example = TestHelper.load_example('python_method_simple.py', category='format')
    result = format_python_method_content(example.metadata['original'].strip())
    assert result == example.metadata['expected'].strip()

def test_format_python_method_with_decorator():
    example = TestHelper.load_example('python_method_with_decorator.py', category='format')
    result = format_python_method_content(example.metadata['original'].strip())
    assert result == example.metadata['expected'].strip()

def test_process_lines_simple():
    example = TestHelper.load_example('process_lines_example.py', category='format')
    original_lines = example.metadata['original_lines']
    new_lines = example.metadata['new_lines']
    start_idx = example.metadata['start_idx']
    end_idx = example.metadata['end_idx']
    expected_lines = example.metadata['expected_lines']
    
    result = process_lines(original_lines, start_idx, end_idx, new_lines)
    assert result == expected_lines

def test_process_lines_at_beginning():
    original = ['line 1', 'line 2', 'line 3']
    new_lines = ['new line 1']
    expected = ['new line 1', 'line 2', 'line 3']
    assert process_lines(original, 0, 0, new_lines) == expected

def test_process_lines_at_end():
    original = ['line 1', 'line 2', 'line 3']
    new_lines = ['new line 3']
    expected = ['line 1', 'line 2', 'new line 3']
    assert process_lines(original, 2, 2, new_lines) == expected

def test_process_lines_empty_original():
    original = []
    new_lines = ['new line']
    assert process_lines(original, 0, 0, new_lines) == new_lines

def test_process_lines_out_of_bounds():
    original = ['line 1', 'line 2', 'line 3']
    new_lines = ['new line']
    assert process_lines(original, -1, -1, new_lines) == ['new line', 'line 1', 'line 2', 'line 3']
    assert process_lines(original, 10, 20, new_lines) == ['line 1', 'line 2', 'line 3', 'new line']