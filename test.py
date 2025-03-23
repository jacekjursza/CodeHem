import rich

from codehem import CodeHem
from codehem.core2.codehem2 import CodeHem2

my_test_code = '''
class MyClass:
    static_prop = "Hello, World!"
    
    def __init__(self, name):
        self.name = name
    
    @my_decorator
    def greet(self):
        print(f"Hello, my name is {self.name}!!!")
        
'''



ch = CodeHem2('python')

result = ch.extract(my_test_code)

print('----------------------------------')
rich.print(result)
print('----------------------------------')