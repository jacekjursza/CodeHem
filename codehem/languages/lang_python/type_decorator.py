"""Handler for Python decorator elements."""
import re
from typing import Any, Dict, List, Optional

from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType


@element_type_descriptor
class PythonDecoratorHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler for Python decorator elements."""
    language_code = 'python'
    element_type = CodeElementType.DECORATOR
    tree_sitter_query = '''
    (decorated_definition
      decorator: (decorator name: (identifier) @decorator_name)
      definition: [(function_definition name: (identifier) @func_name)
                  (class_definition name: (identifier) @class_name)])
    '''
    regexp_pattern = '@([a-zA-Z_][a-zA-Z0-9_]*)(?:\\s*\\([^)]*\\))?\\s*\\n\\s*(?:def|class)\\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    custom_extract = True

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """Custom extraction for decorators to properly associate with their targets."""
        results = []
        pattern = re.compile(self.regexp_pattern, re.MULTILINE | re.DOTALL)
        for match in pattern.finditer(code):
            decorator_name = match.group(1)
            target_name = match.group(2)
            content = match.group(0).split('\n')[0]
            start_pos = match.start()
            end_pos = start_pos + len(content)
            lines_before = code[:start_pos].count('\n')
            last_newline = code[:start_pos].rfind('\n')
            start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
            lines_total = code[:end_pos].count('\n')
            last_newline_end = code[:end_pos].rfind('\n')
            end_column = end_pos - last_newline_end - 1 if last_newline_end >= 0 else end_pos
            results.append({'type': 'decorator', 'name': decorator_name, 'content': content, 'parent_name': target_name, 'range': {'start': {'line': lines_before + 1, 'column': start_column}, 'end': {'line': lines_total + 1, 'column': end_column}}})
        return results
