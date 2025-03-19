from core.utils.format_utils import (
    normalize_indentation,
    format_python_class_content,
    format_python_method_content,
    process_lines
)

# Tests for normalize_indentation
def test_normalize_indentation_default():
    code = """
def function():
    if True:
        print("Hello")
    """
    expected = """
def function():
    if True:
        print("Hello")
    """
    assert normalize_indentation(code) == expected


def test_normalize_indentation_mixed():
    code = """
def function():
  if True:
    print("Hello")
      print("Indented more")
    """
    expected = """
def function():
    if True:
        print("Hello")
            print("Indented more")
    """
    assert normalize_indentation(code) == expected


def test_normalize_indentation_empty_lines():
    code = """
def function():

    if True:
        print("Hello")

    """
    expected = """
def function():

    if True:
        print("Hello")

    """
    assert normalize_indentation(code) == expected


def test_normalize_indentation_custom():
    code = """
def function():
    if True:
        print("Hello")
    """
    expected = """
def function():
  if True:
    print("Hello")
    """
    assert normalize_indentation(code, "  ") == expected


def test_normalize_indentation_no_indent():
    code = """
no indentation
at all
in this code
    """
    assert normalize_indentation(code) == code


# Tests for format_python_class_content
def test_format_python_class_simple():
    code = """
class MyClass:
    def method(self):
        print("Hello")
    """
    expected = """
class MyClass:
    def method(self):
        print("Hello")
    """
    assert format_python_class_content(code) == expected


def test_format_python_class_with_decorator():
    code = """
@decorator
class MyClass:
    def method(self):
        print("Hello")
    """
    expected = """
@decorator
class MyClass:
    def method(self):
        print("Hello")
    """
    assert format_python_class_content(code) == expected


def test_format_python_class_nested():
    code = """
class MyClass:
    def method(self):
        if True:
            print("Hello")
    """
    expected = """
class MyClass:
    def method(self):
        if True:
            print("Hello")
    """
    assert format_python_class_content(code) == expected


def test_format_python_class_inheritance():
    code = """
class MyClass(BaseClass):
    def method(self):
        print("Hello")
    """
    expected = """
class MyClass(BaseClass):
    def method(self):
        print("Hello")
    """
    assert format_python_class_content(code) == expected


def test_format_python_class_properties():
    code = """
class MyClass:
    x = 1
    y = 2

    def method(self):
        print("Hello")
    """
    expected = """
class MyClass:
    x = 1
    y = 2

    def method(self):
        print("Hello")
    """
    assert format_python_class_content(code) == expected


# Tests for format_python_method_content
def test_format_python_method_simple():
    code = """
def method(self):
    print("Hello")
    """
    expected = """
    def method(self):
        print("Hello")
    """
    assert format_python_method_content(code.strip()) == expected.strip()


def test_format_python_method_with_decorator():
    code = """
@decorator
def method(self):
    print("Hello")
    """
    expected = """
    @decorator
    def method(self):
        print("Hello")
    """
    assert format_python_method_content(code.strip()) == expected.strip()


def test_format_python_method_nested():
    code = """
def method(self):
    if True:
        print("Hello")
    """
    expected = """
    def method(self):
        if True:
            print("Hello")
    """
    assert format_python_method_content(code.strip()) == expected.strip()


def test_format_python_method_docstring():
        code = """
    def method(self):
        \"""Documentation.\"""
        print("Hello")
        """
        result = format_python_method_content(code.strip())
        assert "def method(self):" in result
        assert '"""Documentation."""' in result
        assert "print(\"Hello\")" in result


def test_format_python_method_complex_nesting():
    code = """
def method(self):
    if True:
        for item in items:
            if item:
                print(item)
    """
    expected = """
    def method(self):
        if True:
            for item in items:
                if item:
                    print(item)
    """
    assert format_python_method_content(code.strip()) == expected.strip()


# Tests for process_lines
def test_process_lines_simple():
    original = ["line 1", "line 2", "line 3", "line 4", "line 5"]
    new_lines = ["new line 2", "new line 3"]
    expected = ["line 1", "new line 2", "new line 3", "line 4", "line 5"]
    assert process_lines(original, 1, 2, new_lines) == expected


def test_process_lines_at_beginning():
    original = ["line 1", "line 2", "line 3"]
    new_lines = ["new line 1"]
    expected = ["new line 1", "line 2", "line 3"]
    assert process_lines(original, 0, 0, new_lines) == expected


def test_process_lines_at_end():
    original = ["line 1", "line 2", "line 3"]
    new_lines = ["new line 3"]
    expected = ["line 1", "line 2", "new line 3"]
    assert process_lines(original, 2, 2, new_lines) == expected


def test_process_lines_empty_original():
    original = []
    new_lines = ["new line"]
    assert process_lines(original, 0, 0, new_lines) == new_lines


def test_process_lines_out_of_bounds():
    original = ["line 1", "line 2", "line 3"]
    new_lines = ["new line"]
    # Should not change if indices are out of bounds
    assert process_lines(original, -1, -1, new_lines) == ["new line", "line 1", "line 2", "line 3"]
    assert process_lines(original, 10, 20, new_lines) == ["line 1", "line 2", "line 3", "new line"]