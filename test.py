import logging
import rich
from codehem import CodeHem
from tests.helpers.code_examples import TestHelper

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger('tree_sitter').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

code = '''
import os
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class ExampleClass:
    # Class constant
    CONSTANT = 42
    other_property: int = 0 # Translated from 'inny_property'

    def __init__(self, value: int = 0):
        self._value = value

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, new_value: int) -> None:
        self._value = new_value

    def calculate(self, multiplier: int) -> int:
        return self._value * multiplier

def standalone_function(param: str) -> str:
    return param.upper()

'''
new_version = '''
def greet(self) -> str:
    print("Hello, World!")
    return f"@Hello, {self.name}!!!!!!!!!!!!"
'''
new_method = '''
def new_method(self) -> str:
    """ A new method to add to a class."""
    
    print("Hello, World!")
    
    return f"THIS IS+ 11111 NEW METHOD!!!!!!!!!!!!@"
'''

def test_services():
    ch = CodeHem('python')
    for key, extr in ch.language_service.extractors.items():
        print(key)
        rich.print(extr.__class__.__name__)
        print('---------')
    print('---------')

def test_extractors():
    """Test the extraction functionality."""
    print('Testing extractors...')
    hem = CodeHem('python')
    r = hem.extract(code)
    result = hem.get_text_by_xpath(code, 'FILE.MyClass.documented_method[property_getter]') # Assuming MyClass maps to ExampleClass here based on context
    result = hem.upsert_element(code, 'method', 'greet', new_version, parent_name='ExampleClass')
    result = hem.upsert_element(result, 'method', 'new_method', new_method, parent_name='ExampleClass')
    print('----- input -----')
    rich.print(result)


print('----- test services-----')
test_extractors()