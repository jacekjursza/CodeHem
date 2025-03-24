import re
from typing import Optional, Tuple
from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler
from codehem.languages.registry import handler

@handler
class PythonClassHandler(LanguageHandler):
    """Handler for Python class elements."""
    language_code = 'python'
    element_type = CodeElementType.CLASS
    tree_sitter_query = '\n    (class_definition\n      name: (identifier) @class_name\n      body: (block) @body) @class_def\n    '
    regexp_pattern = 'class\\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\\s*\\([^)]*\\))?\\s*:(.*?)(?=\\n(?:class|def|\\Z))'
    custom_extract = False

    def find_element(self, code: str, name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find a class in the code.
        
        Args:
            code: Source code
            name: Name of the class to find
            parent_name: Unused for classes
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        pattern = 'class\\s+' + re.escape(name) + '(?:\\s*\\([^)]*\\))?\\s*:'
        match = re.search(pattern, code)
        if not match:
            return (0, 0)
        start_line = code[:match.start()].count('\n') + 1
        remaining_code = code[match.end():]
        next_def = re.search('(?:^|\\n)class|(?:^|\\n)def', remaining_code)
        if next_def:
            end_offset = next_def.start()
            end_line = start_line + remaining_code[:end_offset].count('\n')
        else:
            end_line = start_line + remaining_code.count('\n')
        return (start_line, end_line)

    def upsert_element(self, original_code: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add or replace a class in the code.
        
        Args:
            original_code: Original source code
            name: Name of the class to add/replace
            new_code: New class content
            parent_name: Unused for classes
            
        Returns:
            Modified code
        """
        position = self.find_element(original_code, name, None)
        if position[0] > 0:
            lines = original_code.splitlines(True)
            result = ''.join(lines[:position[0] - 1])
            result += new_code
            if not new_code.endswith('\n'):
                result += '\n'
            result += ''.join(lines[position[1]:])
            return result
        else:
            if original_code and (not original_code.endswith('\n')):
                original_code += '\n'
            return original_code + '\n' + new_code + '\n'

    def format_element(self, content: str, indent_level: int=0) -> str:
        """
        Format a Python class.
        
        Args:
            content: Class content to format
            indent_level: Level of indentation to apply
            
        Returns:
            Formatted class
        """
        indent = '    ' * indent_level
        lines = content.splitlines()
        result = []
        for line in lines:
            if line.strip():
                result.append(indent + line.lstrip())
            else:
                result.append(line)
        return '\n'.join(result)