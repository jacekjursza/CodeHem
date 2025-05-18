import rich
from codehem import CodeHem


new_content1 = '''
def calculate(self, multiplier: int) -> int:
    return self._value * multiplier + 33
'''


if __name__ == '__main__':
    hem = CodeHem('python')
    content = hem.load_file('D:\\code\\CodeHem\\tests\\fixtures\\python\\general\\sample_class_with_properties.txt')
    print(content)
    rich.print(hem.extract(content))


    result = hem.upsert_element_by_xpath(content, "ExampleClass.calculate", new_content1)

    print("------------------------")
    print(result)
    print("------------------------")