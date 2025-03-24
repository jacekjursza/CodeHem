import re
from typing import Optional, Tuple
from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler

class JavaScriptClassHandler(LanguageHandler):
    """Handler for JavaScript class elements."""
    language_code = 'javascript'
    element_type = CodeElementType.CLASS
    tree_sitter_query = """
    (class_declaration
      name: (identifier) @class_name
      body: (class_body) @body) @class_def
    """
    regexp_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+extends\s+[a-zA-Z_][a-zA-Z0-9_.]*)?s*{(.*?)(?=\n})'
    custom_extract = False

    def find_element(self, code: str, name: str, parent_name: Optional[str] = None) -> Tuple[int, int]:
        """
        Find a class in the code.
        
        Args:
            code: Source code
            name: Name of the class to find
            parent_name: Unused for classes
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        pattern = r'class\s+' + re.escape(name) + r'(?:\s+extends\s+[a-zA-Z_][a-zA-Z0-9_.]*)?s*{'
        match = re.search(pattern, code)
        if not match:
            return (0, 0)
            
        # Get start line
        start_line = code[:match.start()].count('\n') + 1
        
        # Find the matching closing brace
        class_start = match.end()
        
        # Find the matching closing brace by counting braces
        brace_level = 1
        end_pos = class_start
        
        for i in range(class_start, len(code)):
            if code[i] == '{':
                brace_level += 1
            elif code[i] == '}':
                brace_level -= 1
                if brace_level == 0:
                    end_pos = i + 1
                    break
        
        if end_pos <= class_start:
            return (0, 0)
            
        end_line = code[:end_pos].count('\n') + 1
        return (start_line, end_line)
    
    def upsert_element(self, original_code: str, name: str, new_code: str, 
                       parent_name: Optional[str] = None) -> str:
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
        # Find class position
        position = self.find_element(original_code, name, None)
        
        if position[0] > 0:
            # Class exists, replace it
            lines = original_code.splitlines(True)
            result = ''.join(lines[:position[0]-1])
            result += new_code
            if not new_code.endswith('\n'):
                result += '\n'
            result += ''.join(lines[position[1]:])
            return result
        else:
            # Class doesn't exist, add it
            if original_code and not original_code.endswith('\n'):
                original_code += '\n'
                
            return original_code + '\n' + new_code + '\n'
    
    def format_element(self, content: str, indent_level: int = 0) -> str:
        """
        Format a JavaScript class.
        
        Args:
            content: Class content to format
            indent_level: Level of indentation to apply
            
        Returns:
            Formatted class
        """
        indent = '  ' * indent_level  # JavaScript typically uses 2 spaces
        lines = content.splitlines()
        result = []
        
        for line in lines:
            if line.strip():
                result.append(indent + line.lstrip())
            else:
                result.append(line)
                
        return '\n'.join(result)