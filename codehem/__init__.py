from .models.enums import CodeElementType
from .models.xpath import CodeElementXPathNode
from .models.code_element import CodeElementsResult
from .main import CodeHem
from .core.registry import registry
from .core.post_processors.factory import PostProcessorFactory
from .core.post_processors.base import LanguagePostProcessor
from .core.post_processors.python import PythonPostProcessor
from .languages.lang_typescript.typescript_post_processor import TypeScriptExtractionPostProcessor as TypeScriptPostProcessor

# Initialize all components
registry.initialize_components()

__version__ = '0.1.7.0'  # Updated version to reflect our added post-processors implementation
__all__ = [
    'CodeHem', 
    'CodeElementType', 
    'CodeElementXPathNode', 
    'CodeElementsResult',
    'PostProcessorFactory',
    'LanguagePostProcessor',
    'PythonPostProcessor',
    'TypeScriptPostProcessor'
]
