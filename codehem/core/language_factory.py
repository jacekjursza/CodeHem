"""
Factory system for creating language components.
"""
from typing import Dict, List, Any, Type, Optional
import logging
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.element_type_template import create_element_type_descriptor
from codehem.core.registry import registry, element_type_descriptor

logger = logging.getLogger(__name__)

class LanguageComponentFactory:
    """Factory for creating language-specific component implementations."""
    
    @staticmethod
    def create_language_descriptors(language_code: str) -> Dict[str, ElementTypeLanguageDescriptor]:
        """Create all standard element type descriptors for a language."""
        descriptors = {}
        
        for element_type in [
            "class",
            "method",
            "function",
            "property",
            "property_getter",
            "property_setter",
            "static_property",
            "import",
            "decorator"
        ]:
            try:
                descriptor_attrs = create_element_type_descriptor(language_code, element_type)
                
                # Create descriptor class
                descriptor_class_name = f"{language_code.capitalize()}{element_type.capitalize()}Descriptor"
                descriptor_class = type(
                    descriptor_class_name, 
                    (ElementTypeLanguageDescriptor,), 
                    descriptor_attrs
                )
                
                # Register descriptor
                registry.register_element_type_descriptor(descriptor_class)
                
                # Store in result
                descriptors[element_type] = descriptor_class()
                
            except Exception as e:
                logger.warning(f"Failed to create descriptor for {language_code}/{element_type}: {e}")
                
        return descriptors
    
    @staticmethod
    def generate_language_skeleton(language_code: str, file_extensions: List[str]):
        """Generate skeleton code for a new language implementation."""
        # Create base language directory
        language_dir = f"d:/code/codehem/codehem/languages/lang_{language_code}"
        
        # Create detector class
        detector_code = f"""
import re
from typing import List
from codehem.core.detector import BaseLanguageDetector
from codehem.core.registry import language_detector

@language_detector
class {language_code.capitalize()}LanguageDetector(BaseLanguageDetector):
    \"\"\"Language detector for {language_code}.\"\"\"

    @property
    def language_code(self) -> str:
        return '{language_code}'

    @property
    def file_extensions(self) -> List[str]:
        return {file_extensions}

    def detect_confidence(self, code: str) -> float:
        \"\"\"Calculate confidence that the code is {language_code}.\"\"\"
        if not code.strip():
            return 0.0
            
        # TODO: Add language-specific detection patterns
        patterns = []
        score = 0
        max_score = len(patterns) * 10
        
        for pattern in patterns:
            if re.search(pattern, code, re.DOTALL):
                score += 10
                
        # Normalize score between 0 and 1
        return max(0.0, min(1.0, score / max_score))
"""

        # Create language service class
        service_code = f"""
from typing import List
from codehem import CodeElementType
from codehem.core.service import LanguageService
from codehem.core.registry import language_service

@language_service
class {language_code.capitalize()}LanguageService(LanguageService):
    \"\"\"Language service for {language_code}.\"\"\"
    LANGUAGE_CODE = '{language_code}'

    @property
    def file_extensions(self) -> List[str]:
        return {file_extensions}

    @property
    def supported_element_types(self) -> List[str]:
        return [
            CodeElementType.CLASS.value,
            CodeElementType.FUNCTION.value,
            CodeElementType.METHOD.value,
            CodeElementType.IMPORT.value
            # TODO: Add more supported element types
        ]

    def detect_element_type(self, code: str) -> str:
        \"\"\"
        Detect the type of code element.
        Args:
            code: The code to analyze
        Returns:
            Element type string (from CodeElementType)
        \"\"\"
        code = code.strip()
        
        # TODO: Add language-specific detection logic
        
        return CodeElementType.UNKNOWN.value
"""

        # Create formatter class
        formatter_code = f"""
import re
from typing import Callable, Dict, Optional
from codehem.core.formatting.formatter import BaseFormatter
from codehem.models.enums import CodeElementType

class {language_code.capitalize()}Formatter(BaseFormatter):
    \"\"\"
    {language_code.capitalize()}-specific implementation of the code formatter.
    \"\"\"

    def __init__(self, indent_size: int=2):
        \"\"\"Initialize the formatter.\"\"\"
        super().__init__(indent_size)

    def _get_element_formatter(self, element_type: str) -> Optional[Callable]:
        \"\"\"Get the formatter function for the specified element type.\"\"\"
        formatters = {{
            CodeElementType.CLASS.value: self.format_class,
            CodeElementType.METHOD.value: self.format_method,
            CodeElementType.FUNCTION.value: self.format_function,
            # TODO: Add more formatters
        }}
        return formatters.get(element_type)

    def format_class(self, code: str) -> str:
        \"\"\"Format a class definition.\"\"\"
        # TODO: Implement class formatting
        return self.dedent(code).strip()

    def format_method(self, code: str) -> str:
        \"\"\"Format a method definition.\"\"\"
        # TODO: Implement method formatting
        return self.dedent(code).strip()

    def format_function(self, code: str) -> str:
        \"\"\"Format a function definition.\"\"\"
        # TODO: Implement function formatting
        return self.dedent(code).strip()
"""

        return {
            f"{language_dir}/detector.py": detector_code,
            f"{language_dir}/service.py": service_code,
            f"{language_dir}/formatting/{language_code}_formatter.py": formatter_code
        }