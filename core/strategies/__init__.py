"""
Strategy pattern implementation for language-specific operations.
"""
from typing import Dict, Type, Optional
from .language_strategy import LanguageStrategy
from .python_strategy import PythonStrategy
from .typescript_strategy import TypeScriptStrategy

# Registry of language strategies
STRATEGIES: Dict[str, Type[LanguageStrategy]] = {
    "python": PythonStrategy,
    "typescript": TypeScriptStrategy,
    "javascript": TypeScriptStrategy  # JavaScript uses the TypeScript strategy
}

def get_strategy(language: str) -> Optional[LanguageStrategy]:
    """
    Get a language strategy for the specified language.
    
    Args:
        language: Language code (e.g., 'python', 'typescript')
        
    Returns:
        A language strategy for the specified language or None if not supported
    """
    language = language.lower()
    strategy_class = STRATEGIES.get(language)
    
    if strategy_class:
        return strategy_class()
    return None

def get_strategy_for_file(file_path: str) -> Optional[LanguageStrategy]:
    """
    Get a language strategy based on file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        A language strategy for the file or None if not supported
    """
    import os
    file_ext = os.path.splitext(file_path.lower())[1]
    
    for strategy_class in STRATEGIES.values():
        strategy = strategy_class()
        if file_ext in strategy.file_extensions:
            return strategy
            
    return None

def register_strategy(language: str, strategy_class: Type[LanguageStrategy]) -> None:
    """
    Register a new language strategy.
    
    Args:
        language: Language code (e.g., 'ruby', 'go')
        strategy_class: Language strategy class to register
    """
    STRATEGIES[language.lower()] = strategy_class