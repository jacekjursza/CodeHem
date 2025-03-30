# codehem/languages/lang_python/type_decorator.py
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
    # Ten query jest używany głównie do *znalezienia* dekoratorów,
    # a TemplateMethodExtractor zajmuje się ich *ekstrakcją* w kontekście metody/funkcji/klasy
    tree_sitter_query = """
    (decorator) @decorator_node
    """
    # Regex może być przydatny jako fallback, ale na razie wyłączamy custom_extract
    regexp_pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*(?:\s*\.\s*[a-zA-Z_][a-zA-Z0-9_]*)*)(?:\([^)]*\))?'
    # --- ZMIANA ---
    # Wyłączamy custom_extract, polegamy na ekstrakcji w TemplateMethodExtractor
    custom_extract = False

    # --- ZMIANA ---
    # Metoda extract staje się nieużywana przy custom_extract = False,
    # ale zostawiamy ją zakomentowaną lub usuwamy.
    # def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
    #     """Custom extraction for decorators to properly associate with their targets."""
    #     # Ta logika jest teraz prawdopodobnie obsługiwana lepiej przez TreeSitter
    #     # w TemplateMethodExtractor._extract_all_decorators
    #     logger.warning("PythonDecoratorHandlerElementType.extract jest wyłączona (custom_extract=False)")
    #     return []
    #     # Stara logika oparta na regex:
    #     # results = []
    #     # pattern = re.compile(self.regexp_pattern, re.MULTILINE | re.DOTALL)
    #     # # Poprawiony regex do asocjacji z następną linią def/class
    #     # assoc_pattern = re.compile(self.regexp_pattern + r'\s*\n\s*(?:def|class)\s+([a-zA-Z_][a-zA-Z0-9_]*)', re.MULTILINE | re.DOTALL)
    #     # for match in assoc_pattern.finditer(code):
    #     #     decorator_name = match.group(1)
    #     #     target_name = match.group(2) # Nazwa funkcji/klasy
    #     #     content = match.group(0).split('\n')[0] # Tylko linia z @...
    #     #     start_pos = match.start()
    #     #     # ... reszta logiki obliczania zakresu ...
    #     #     results.append({
    #     #         'type': 'decorator',
    #     #         'name': decorator_name,
    #     #         'content': content,
    #     #         'parent_name': target_name, # Asocjacja z celem
    #     #         'range': { ... }
    #     #     })
    #     # return results