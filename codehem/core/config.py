"""
Configuration management for CodeHem.
"""
from typing import Any


class Configuration:
    """Configuration manager for CodeHem."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Configuration, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the configuration with defaults."""
        self._config = {
            'extraction': {
                'prefer_tree_sitter': True,
                'fallback_to_regex': True,
                'cache_results': False,
                'cache_size': 100
            },
            'formatting': {
                'preserve_indentation': True,
                'preserve_comments': True
            },
            'logging': {
                'level': 'INFO',
                'file': None
            }
        }
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        try:
            return self._config[section][key]
        except KeyError:
            return default
    
    def set(self, section: str, key: str, value: Any):
        """Set a configuration value."""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value

# Initialize configuration
config = Configuration()