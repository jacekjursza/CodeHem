from typing import List, Optional

import pytest

from codehem import CodeHem
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def codehem():
    return CodeHem('python')

def get_lines(xpath: str) -> Optional[List[str]]:
    hem = CodeHem("python")
    example = TestHelper.load_example('multi_case', category='general')
    code = example.content

    result = hem.get_text_by_xpath(code, xpath)
    if result:
        return result.split('\n')
    return None

def verify_content(str_line: str, expected: str, indent=0):
    assert str_line.strip() == expected.strip()
    assert str_line == f"{' ' * indent * 4}{expected}"



def test_property_getter(codehem):
    """
    Whether the X-PATH in the form FILE.MyClass.new_property[property_getter]
    actually returns the getter from the MyClass along with the decorator
    """
    result = get_lines("FILE.MyClass.new_property[property_getter]")
    verify_content(result[0], "@property", 1)
    verify_content(result[-1], 'return f"Hello, {self.name}!"', 2)

def test_property_setter(codehem):
    """
    Whether the X-PATH in the form "FILE.MyClass.new_property[property_setter]"
    actually returns the setter along with the decorator
    """
    result = get_lines("FILE.MyClass.new_property[property_setter]")
    verify_content(result[0], "@new_property.setter", 1)
    verify_content(result[-1], 'self.name = value', 2)

def test_property_setter_def(codehem):
    """
    Whether the X-PATH in the form "FILE.MyClass.new_property[property_setter][def]"
    actually returns the setter without the decorator, but with the method body and its definition
    """
    result = get_lines("FILE.MyClass.new_property[property_setter][def]")
    verify_content(result[0], "def new_property(self, value: str) -> None:", 1)
    verify_content(result[-1], 'self.name = value', 2)

def test_property_setter_body(codehem):
    """
    Whether the X-PATH in the form "FILE.MyClass.new_property[property_setter][body]"
    actually returns the setter without the decorator and without the function definition, only the function body
    """
    result = get_lines("FILE.MyClass.new_property[property_setter][body]")
    assert len(result) == 1
    verify_content(result[0], 'self.name = value', 2)

def test_not_existing(codehem):
    """
    Whether the X-PATH to a non-existent method returns None
    """
    result = get_lines("FILE.MyClass.new_property_missing[property_setter][body]")
    assert result is None

def test_duplicated_method(codehem):
    """
    Whether the X-PATH to a duplicated method returns the one that was declared last
    """
    result = get_lines("FILE.DocstringClass.duplicated_method")
    verify_content(result[0], "def duplicated_method(self, param1, param2):", 1)
    verify_content(result[-1], 'return "Duplicated 2"', 2)

def test_getter_vs_setter(codehem):
    """
    Whether the X-PATH without a specific getter/setter but pointing to the method name
    prefers the setter over the getter and returns it along with the decorator
    """
    result = get_lines("FILE.MyClass.new_property")
    verify_content(result[0], "@new_property.setter", 1)
    verify_content(result[-1], 'self.name = value', 2)

def test_wrong_class_existing_method(codehem):
    """
    Whether the X-PATH to class A but with a method that exists only in class B returns None
    """
    result = get_lines("FILE.MyClass.documented_method")
    assert result is None
