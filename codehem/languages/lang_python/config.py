"""
Language-specific configuration for Python in CodeHem.
"""
import json
from pathlib import Path
from codehem.models.enums import CodeElementType
from .python_post_processor import PythonExtractionPostProcessor

_patterns_path = Path(__file__).with_name("node_patterns.json")
with _patterns_path.open() as f:
    _raw = json.load(f)
PYTHON_PLACEHOLDERS = {CodeElementType[k]: v for k, v in _raw.items()}

LANGUAGE_CONFIG = {
    'language_code': 'python',
    'post_processor_class': PythonExtractionPostProcessor,
    'template_placeholders': PYTHON_PLACEHOLDERS,
}
