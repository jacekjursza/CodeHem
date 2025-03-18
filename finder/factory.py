# patchcommander/core/finder/factory.py

from finder.base import CodeFinder
from finder.lang.python_code_finder import PythonCodeFinder
from finder.lang.typescript_code_finder import TypeScriptCodeFinder


def get_code_finder(language: str) -> CodeFinder:
    if language.lower() == 'python':
        return PythonCodeFinder()
    elif language.lower() in ['typescript', 'javascript']:
        return TypeScriptCodeFinder()
    else:
        raise ValueError(f"Unsupported language: {language}")
