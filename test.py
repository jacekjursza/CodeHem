import logging

import rich

from codehem import CodeHem

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger('tree_sitter').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

code = '''
from pydantic import BaseModel, Field

class MyClass:
    static_property: str = "Hello, World!"

    def __init__(self, name: str):
        self.name = name

    @greetdecorator
    def greet(self) -> str:
        return f"Hello, {self.name}!"

    @mydecorator
    def other(self, x: int, y: str) -> str:
        return f"This is other: {x} {y}."

def my_function(x: int) -> int:
    return x + 1
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
    # for (key, extr) in ch.language_service.extractors.items():
    #     print(key)
    #     rich.print(extr.__class__.__name__)
    #     print('---------')
    # print('---------')

def test_extractors():
    """Test the extraction functionality."""
    print('Testing extractors...')
    hem = CodeHem('python')
    elements = hem.extract(code)
    print('----------------------------------')
    rich.print(elements)
    print('----------------------------------')
    
    # Print imports separately to verify they're being extracted
    print('Imports found:')
    for element in elements.elements:
        if element.type.value == 'import':
            rich.print(element)
    print('----------------------------------')

    result = hem.get_text_by_xpath(code, "MyClass.greet")

    # result = hem.upsert_element(code, 'method', 'greet', new_version, parent_name='MyClass')
    # result = hem.upsert_element(result, 'method', 'new_method', new_method, parent_name='MyClass')
    rich.print(result)



print("----- test services-----")
test_services()
test_extractors()