# Import and re-export key components for convenient API access
from .ast_handler import ASTHandler
from .manipulator import get_code_manipulator
from .finder import get_code_finder
from .languages import get_language_for_file
from .models import CodeElement, CodeElementsResult, CodeRange, CodeElementType, MetaElementType
from .strategies import get_strategy, get_strategy_for_file
from .services.extraction_service import ExtractionService