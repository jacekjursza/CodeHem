from codehem.core.finder.base import CodeFinder
from codehem.core.finder.lang.python_code_finder import PythonCodeFinder
from codehem.core.finder.lang.typescript_code_finder import TypeScriptCodeFinder

def get_code_finder(language: str) -> CodeFinder:
    if language.lower() == 'python':
        return PythonCodeFinder()
    elif language.lower() in ['typescript', 'javascript', 'tsx']:
        return TypeScriptCodeFinder()
    else:
        raise ValueError(f'Unsupported language: {language}')