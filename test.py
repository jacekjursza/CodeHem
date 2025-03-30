import logging

import rich

from codehem import CodeHem
from tests.helpers.code_examples import TestHelper

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger('tree_sitter').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

code = '''
from pydantic import BaseModel, Field
from django.models import Model

class MyClass:
    static_property: str = "Hello, World!"

    def __init__(self, name: str):
        self.name = name

    @property
    def new_property(self) -> str:
        return f"Hello, {self.name}!"
    
    @new_property.setter
    def new_property(self, value: str) -> None:
        self.name = value

    @greetdecorator
    def greet(self) -> str:
        return f"Hello, {self.name}!"

    @mydecorator
    def other(self, x: int, y: str) -> str:
        return f"This is other: {x} {y}."


class MyClass2:
    def test(self) -> str:
        return "Hello, World!"

'''

new_version = '''
def greet(self) -> str:
    print("Hello, World!")
    return f"@Hello, {self.name}!!!!!!!!!!!!"
'''

new_method = '''
def new_method(self) -> str:
    print("Hello, World!")
    return f"THIS IS NEW METHOD!!!!!!!!!!!!"
'''

def test_services():
    ch = CodeHem('python')
    for (key, extr) in ch.language_service.extractors.items():
        print(key)
        rich.print(extr.__class__.__name__)
        print('---------')
    print('---------')

def test_extractors():
    """Test the extraction functionality."""
    print('Testing extractors...')
    hem = CodeHem('python')

    r = hem.extract(code)
    result = hem.get_text_by_xpath(code, "FILE.MyClass.documented_method[property_getter]")

    result = hem.upsert_element(code, 'method', 'greet', new_version, parent_name='MyClass')
    result = hem.upsert_element(
        result, "method", "new_method", new_method, parent_name="MyClass"
    )
    print("----- input -----")
    rich.print(result)
    print("----- parsed -----")
    rich.print(r)

    print("----- get_text tests:::: -----")

    versions = [
        "FILE.MyClass.new_property[property_getter]",
        "FILE.MyClass.new_property[property_setter]",
        "FILE.MyClass.new_property[property_getter][body]",
        "FILE.MyClass.new_property",
        "FILE.MyClass.new_property[def]",
        "FILE.MyClass.new_property[all]",
    ]

    for xpath in versions:
        print(f"----- XPATH: {xpath} -----")
        txt_result = hem.get_text_by_xpath(code, xpath)
        print(f"----- XPATH: {xpath} result: -----")
        print(txt_result)
        input("")

    rich.print(r)

print("----- test services-----")
# test_services()
test_extractors()