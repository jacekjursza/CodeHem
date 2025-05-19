from .models.enums import CodeElementType
from .models.xpath import CodeElementXPathNode
from .models.code_element import CodeElementsResult
from .main import CodeHem
from .core.workspace import Workspace
from .core.registry import registry
from .core.post_processors.factory import PostProcessorFactory

# Initialize all components
registry.initialize_components()

__version__ = "1.0.0"
__all__ = [
    "CodeHem",
    "CodeElementType",
    "CodeElementXPathNode",
    "CodeElementsResult",
    "PostProcessorFactory",
    "Workspace",
]
