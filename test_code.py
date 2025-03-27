import rich
from codehem import CodeHem


if __name__ == '__main__':
    hem = CodeHem('python')
    content = hem.load_file('tests/fixtures/python/sample_file2.txt')
    print(content)
    rich.print(hem.extract(content))