import logging
import sys
import rich
from codehem import CodeHem
from codehem.core.registry import registry
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger('tree_sitter').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

code = '''
from pydantic import BaseModel, Field

class MyClass:
    static_property: str = "Hello, World!"

    def __init__(self, name: str):
        self.name = name

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
    return f"Hello, {self.name}!!!!!!!!!!!!"
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
    
    result = hem.upsert_element(code, 'method', 'greet', new_version, parent_name='MyClass')
    rich.print(result)

if __name__ == '__main__':
    test_services()
    test_extractors()