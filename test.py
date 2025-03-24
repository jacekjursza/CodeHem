import rich

from codehem.languages import registrations

from codehem.main import CodeHem2

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