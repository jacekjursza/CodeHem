"""
Factory system for creating language components.
"""

import importlib
import logging
import os
from typing import Dict, List

from codehem import CodeElementType
from codehem.core.registry import registry
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.element_type_template import create_element_type_descriptor

logger = logging.getLogger(__name__)

class LanguageComponentFactory:
    """Factory for creating language-specific component implementations."""

    @staticmethod
    def create_language_descriptors(language_code: str) -> Dict[str, ElementTypeLanguageDescriptor]:
        """Create all standard element type descriptors for a language."""
        descriptors = {}
        for element_type in ['class', 'method', 'function', 'property', 'property_getter', 'property_setter', 'static_property', 'import', 'decorator']:
            try:
                descriptor_attrs = create_element_type_descriptor(language_code, element_type)
                descriptor_class_name = f'{language_code.capitalize()}{element_type.capitalize()}Descriptor'
                descriptor_class = type(descriptor_class_name, (ElementTypeLanguageDescriptor,), descriptor_attrs)
                registry.register_element_type_descriptor(descriptor_class)
                descriptors[element_type] = descriptor_class()
            except Exception as e:
                logger.warning(
                    f"Failed to create descriptor for {language_code}/{element_type}: {e}"
                )
        return descriptors

    @staticmethod
    def generate_language_skeleton(language_code: str, file_extensions: List[str]):
        """Generate skeleton code for a new language implementation."""
        language_dir = f"d:/code/codehem/codehem/languages/lang_{language_code}"
        detector_code = f'''\nimport re\nfrom typing import List\nfrom codehem.core.detector import BaseLanguageDetector\nfrom codehem.core.registry import language_detector\n\n@language_detector\nclass {language_code.capitalize()}LanguageDetector(BaseLanguageDetector):\n    """Language detector for {language_code}."""\n\n    @property\n    def language_code(self) -> str:\n        return \'{language_code}'\n\n    @property\n    def file_extensions(self) -> List[str]:\n        return {file_extensions}\n\n    def detect_confidence(self, code: str) -> float:\n        """Calculate confidence that the code is {language_code}."""\n        if not code.strip():\n            return 0.0\n            \n        # TODO: Add language-specific detection patterns\n        strong_patterns = []\n        medium_patterns = []\n        anti_patterns = []\n        \n        score = 0\n        max_score = len(strong_patterns) * 20 + len(medium_patterns) * 10\n        \n        for pattern in strong_patterns:\n            if re.search(pattern, code, re.DOTALL):\n                score += 20\n                \n        for pattern in medium_patterns:\n            if re.search(pattern, code, re.DOTALL):\n                score += 10\n                \n        for pattern in anti_patterns:\n            if re.search(pattern, code, re.DOTALL):\n                score -= 15\n                \n        # Normalize score between 0 and 1\n        normalized_score = max(0.0, min(1.0, score / max_score))\n        return normalized_score if max_score > 0 else 0.0\n'''
        service_code = f'''\nfrom typing import List, Optional\nfrom codehem import CodeElementType, CodeElementXPathNode\nfrom codehem.core.service import LanguageService\nfrom codehem.core.registry import language_service\nfrom codehem.models.code_element import CodeElementsResult\n\n@language_service\nclass {language_code.capitalize()}LanguageService(LanguageService):\n    """{language_code.capitalize()} language service implementation."""\n    LANGUAGE_CODE = \'{language_code}'\n\n    @property\n    def file_extensions(self) -> List[str]:\n        return {file_extensions}\n\n    @property\n    def supported_element_types(self) -> List[str]:\n        return [\n            CodeElementType.CLASS.value,\n            CodeElementType.FUNCTION.value,\n            CodeElementType.METHOD.value,\n            CodeElementType.IMPORT.value\n            # TODO: Add more supported element types\n        ]\n\n    def detect_element_type(self, code: str) -> str:\n        """\n        Detect the type of code element.\n        Args:\n            code: The code to analyze\n        Returns:\n            Element type string (from CodeElementType)\n        """\n        code = code.strip()\n        \n        # TODO: Add language-specific detection logic\n        \n        return CodeElementType.UNKNOWN.value\n        \n    def get_text_by_xpath_internal(self, code: str, xpath_nodes: List['CodeElementXPathNode']) -> Optional[str]:\n        """\n        Internal method to retrieve text content based on parsed XPath nodes.\n        """\n        # TODO: Implement language-specific XPath lookup\n        return None\n        \n    def extract_language_specific(self, code: str, current_result: CodeElementsResult) -> CodeElementsResult:\n        """Extract language-specific elements."""\n        # TODO: Extract any language-specific elements\n        return current_result\n'''
        formatter_code = f'\nimport re\nfrom typing import Callable, Dict, Optional\nfrom codehem.core.formatting.formatter import BaseFormatter\nfrom codehem.models.enums import CodeElementType\n\nclass {language_code.capitalize()}Formatter(BaseFormatter):\n    """\n    {language_code.capitalize()}-specific implementation of the code formatter.\n    """\n\n    def __init__(self, indent_size: int=2):\n        """Initialize the formatter."""\n        super().__init__(indent_size)\n\n    def _get_element_formatter(self, element_type: str) -> Optional[Callable]:\n        """Get the formatter function for the specified element type."""\n        formatters = {{\n            CodeElementType.CLASS.value: self.format_class,\n            CodeElementType.METHOD.value: self.format_method,\n            CodeElementType.FUNCTION.value: self.format_function,\n            # TODO: Add more formatters\n        }}\n        return formatters.get(element_type)\n\n    def format_class(self, code: str) -> str:\n        """Format a class definition."""\n        return self.dedent(code).strip()\n\n    def format_method(self, code: str) -> str:\n        """Format a method definition."""\n        return self.dedent(code).strip()\n\n    def format_function(self, code: str) -> str:\n        """Format a function definition."""\n        return self.dedent(code).strip()\n        \n    def format_code(self, code: str) -> str:\n        """Format code according to language standards."""\n        code = code.strip()\n        # TODO: Add language-specific formatting logic\n        return code\n'

        manipulator_base_code = f'''\nimport logging\nfrom typing import Optional\nfrom codehem.core.template_manipulator import TemplateManipulator\nfrom codehem.models.enums import CodeElementType\n\nlogger = logging.getLogger(__name__)\n\nclass {language_code.capitalize()}ManipulatorBase(TemplateManipulator):\n    """Base class for {language_code.capitalize()}-specific manipulators."""\n    LANGUAGE_CODE = \'{language_code}'\n    COMMENT_MARKERS = [\'//\', \'/*\']\n    \n    def __init__(self, element_type: CodeElementType=None, formatter=None, extraction_service=None):\n        """Initialize the manipulator with appropriate formatter."""\n        super().__init__(language_code=\'{language_code}\', element_type=element_type, \n                         formatter=formatter, extraction_service=extraction_service)\n'''

        return {
            f"{language_dir}/__init__.py": f'"""\n{language_code.capitalize()} language module for CodeHem.\n"""',
            f"{language_dir}/detector.py": detector_code,
            f"{language_dir}/service.py": service_code,
            f"{language_dir}/formatting/__init__.py": "",
            f"{language_dir}/formatting/{language_code}_formatter.py": formatter_code,
            f"{language_dir}/manipulator/__init__.py": "",
            f"{language_dir}/manipulator/base.py": manipulator_base_code,
            f"{language_dir}/extractors/__init__.py": "",
        }

    @staticmethod
    def initialize_language(
        language_code: str, file_extensions: List[str] = None
    ) -> bool:
        """
        Initialize a new language by generating and registering all necessary components.

        Args:
            language_code: The language code to initialize (e.g., 'typescript')
            file_extensions: List of file extensions for this language

        Returns:
            True if initialization was successful, False otherwise
        """
        # Generate skeleton files
        language_dir = f"d:/code/codehem/codehem/languages/lang_{language_code}"

        try:
            # Create directories if they don't exist
            os.makedirs(f"{language_dir}/formatting", exist_ok=True)
            os.makedirs(f"{language_dir}/manipulator", exist_ok=True)
            os.makedirs(f"{language_dir}/extractors", exist_ok=True)

            # Generate skeleton files
            skeleton_files = LanguageComponentFactory.generate_language_skeleton(
                language_code, file_extensions or [f".{language_code}"]
            )

            # Write files
            for file_path, content in skeleton_files.items():
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(content)

            logger.info(f"Generated skeleton files for {language_code}")

            # Try to load and register the language components
            try:
                # Import the language service module
                service_module = importlib.import_module(
                    f"codehem.languages.lang_{language_code}.service"
                )
                detector_module = importlib.import_module(
                    f"codehem.languages.lang_{language_code}.detector"
                )

                # Create descriptors
                descriptors = LanguageComponentFactory.create_language_descriptors(
                    language_code
                )
                logger.info(
                    f"Created {len(descriptors)} descriptors for {language_code}"
                )

                # Create manipulators
                manipulators = LanguageComponentFactory.create_language_manipulators(
                    language_code
                )
                logger.info(
                    f"Created {len(manipulators)} manipulators for {language_code}"
                )

                return True

            except ImportError as e:
                logger.error(f"Failed to import modules for {language_code}: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize language {language_code}: {e}")
            return False

    @staticmethod
    def create_language_manipulators(language_code: str) -> Dict[str, Any]:
        """Create standard manipulators for a language."""
        manipulators = {}

        # Standard element types that need manipulators
        element_types = ["class", "method", "function", "import", "property"]

        # Base manipulator class name
        base_class_name = f"{language_code.capitalize()}ManipulatorBase"
        base_module_path = f"codehem.languages.lang_{language_code}.manipulator.base"

        try:
            # Import the base manipulator class
            import importlib

            base_module = importlib.import_module(base_module_path)
            base_class = getattr(base_module, base_class_name)

            # Create manipulator for each element type
            for element_type in element_types:
                class_name = f"{language_code.capitalize()}{element_type.capitalize()}Manipulator"

                # Get the appropriate CodeElementType enum value
                element_type_value = getattr(
                    CodeElementType, element_type.upper(), None
                )

                if element_type_value:
                    # Create manipulator class that inherits from base and template
                    template_module_name = (
                        f"codehem.core.manipulators.template_{element_type}_manipulator"
                    )
                    try:
                        template_module = importlib.import_module(template_module_name)
                        template_class_name = (
                            f"Template{element_type.capitalize()}Manipulator"
                        )
                        template_class = getattr(template_module, template_class_name)

                        # Create the new class
                        manipulator_class = type(
                            class_name,
                            (base_class, template_class),
                            {
                                "ELEMENT_TYPE": element_type_value,
                                "LANGUAGE_CODE": language_code,
                            },
                        )

                        # Register the manipulator
                        from codehem.core.registry import registry

                        registry.register_manipulator(manipulator_class)
                        manipulators[element_type] = manipulator_class

                    except (ImportError, AttributeError) as e:
                        logger.warning(
                            f"Could not create {element_type} manipulator for {language_code}: {e}"
                        )

        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not import base manipulator for {language_code}: {e}")

        return manipulators