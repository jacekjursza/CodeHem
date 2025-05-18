# Content of codehem\core\language_service.py
import logging
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Dict, List, Optional, Tuple, Type, Union, TYPE_CHECKING
from codehem.core.extractors.base import BaseExtractor
from codehem.core.formatting.formatter import BaseFormatter
from codehem.core.manipulators.manipulator_base import ManipulatorBase
from codehem.models.enums import CodeElementType
from codehem.models.xpath import CodeElementXPathNode
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import registry
if TYPE_CHECKING:
    from codehem.core.extraction_service import ExtractionService
    from codehem.models.code_element import CodeElementsResult

logger = logging.getLogger(__name__)

class LanguageService(ABC):
    """
    Base class for language-specific services.
    Defines the interface for language-specific operations and combines finder, formatter, and manipulator.
    """
    LANGUAGE_CODE: str
    _instances: Dict[str, 'LanguageService'] = {}

    def __new__(cls, *args, **kwargs):
        language_code = getattr(cls, 'LANGUAGE_CODE', None)
        if not language_code:
            language_code = kwargs.get('language_code', args[0] if args else None)
            if not language_code:
                 raise ValueError(f'{cls.__name__} must define LANGUAGE_CODE or receive it during instantiation.')

        lang_code_lower = language_code.lower()
        if lang_code_lower not in cls._instances:
            logger.debug(f'[__new__] Creating new singleton instance for {lang_code_lower}')
            cls._instances[lang_code_lower] = super().__new__(cls)
        else:
            logger.debug(f'[__new__] Reusing existing instance for {lang_code_lower}')
        return cls._instances[lang_code_lower]

    def __init__(self, formatter_class: Optional[Type[BaseFormatter]]=None, **kwargs):
        """
        Initialize the language service.
        Retrieves registered descriptor instances, initializes their patterns,
        and creates language-specific extractor and manipulator instances.

        Args:
            formatter_class: Optional formatter class for this language. If None, uses BaseFormatter.
            **kwargs: Catches potential arguments.
        """
        if hasattr(self, '_initialized') and self._initialized:
            # logger.debug(f"LanguageService for '{self.language_code}' already initialized. Skipping.") # Reduce noise
            return
        self._initialized = True

        current_language_code = self.language_code
        logger.info(f"Initializing LanguageService for '{current_language_code}'...")

        self.formatter = formatter_class() if formatter_class else BaseFormatter()
        logger.debug(f'Using formatter: {self.formatter.__class__.__name__}')
        self._extraction_service_instance: Optional['ExtractionService'] = None
        logger.debug('LanguageService initialization deferred. Components will be created lazily.')

    # Lazy-initialized component containers

    @cached_property
    def element_type_descriptors(self) -> Dict[str, ElementTypeLanguageDescriptor]:
        """Initialize and cache descriptor instances for this language."""
        current_language_code = self.language_code
        descriptors: Dict[str, ElementTypeLanguageDescriptor] = {}
        supported_types = self._get_supported_element_types_enum()
        all_descriptor_instances_for_lang = registry.all_descriptors.get(current_language_code, {})

        for element_type in supported_types:
            element_type_key = element_type.value.lower()
            descriptor_instance = all_descriptor_instances_for_lang.get(element_type_key)

            if not descriptor_instance:
                logger.debug(f"  No descriptor instance registered for element type: {element_type_key}")
                continue
            if not isinstance(descriptor_instance, ElementTypeLanguageDescriptor):
                logger.error(
                    f"  Registered item for {element_type_key} is not a valid ElementTypeLanguageDescriptor instance: {type(descriptor_instance)}"
                )
                continue

            if descriptor_instance.language_code is None:
                descriptor_instance.language_code = current_language_code
            if descriptor_instance.element_type is None:
                descriptor_instance.element_type = element_type

            if not descriptor_instance._patterns_initialized:
                logger.debug(
                    f"  Attempting pattern initialization for {descriptor_instance.__class__.__name__} ({element_type_key})..."
                )
                if descriptor_instance.initialize_patterns():
                    logger.debug(
                        f"  Pattern initialization method returned True for {descriptor_instance.__class__.__name__}."
                    )
                else:
                    logger.warning(
                        f"  Pattern initialization method returned False for descriptor {descriptor_instance.__class__.__name__} ({element_type_key}). Extractor might not work."
                    )

            descriptors[element_type_key] = descriptor_instance
        return descriptors

    @cached_property
    def extractors(self) -> Dict[str, BaseExtractor]:
        """Instantiate extractor objects lazily."""
        current_language_code = self.language_code
        extractors: Dict[str, BaseExtractor] = {}
        all_extractor_classes = registry.all_extractors

        for element_type, descriptor_instance in self.element_type_descriptors.items():
            if not descriptor_instance._patterns_initialized:
                logger.warning(
                    f"  Skipping extractor for {element_type} - descriptor patterns failed to initialize or flag not set."
                )
                continue

            extractor_key = f"{current_language_code}/{element_type}"
            extractor_cls = all_extractor_classes.get(extractor_key)
            if not extractor_cls:
                fallback_key = f"__all__/{element_type}"
                extractor_cls = all_extractor_classes.get(fallback_key)
                if extractor_cls:
                    logger.debug(f"  Using fallback extractor class {extractor_cls.__name__} for {element_type}")

            if extractor_cls:
                try:
                    extractor_instance = extractor_cls(
                        language_code=current_language_code,
                        language_type_descriptor=descriptor_instance,
                    )
                    extractors[extractor_key] = extractor_instance
                except Exception as e:
                    logger.error(
                        f"  Failed to instantiate extractor {extractor_cls.__name__} for {element_type}: {e}",
                        exc_info=True,
                    )
            else:
                if not all_extractor_classes.get(f"__all__/{element_type}"):
                    logger.warning(
                        f"  No specific or fallback extractor class found in registry for {element_type}"
                    )
        return extractors

    @cached_property
    def manipulators(self) -> Dict[str, ManipulatorBase]:
        """Instantiate manipulator objects lazily."""
        current_language_code = self.language_code
        manipulators: Dict[str, ManipulatorBase] = {}
        all_manipulator_classes = registry.all_manipulators

        for element_type in self._get_supported_element_types_enum():
            element_type_key = element_type.value.lower()
            manipulator_map_key = f"{current_language_code}_{element_type_key}"
            manipulator_cls = all_manipulator_classes.get(manipulator_map_key)
            if manipulator_cls:
                try:
                    manipulator_instance = manipulator_cls(
                        language_code=current_language_code,
                        element_type=element_type,
                        formatter=self.formatter,
                    )
                    manipulators[element_type_key] = manipulator_instance
                except Exception as e:
                    logger.error(
                        f"  Failed to instantiate manipulator {manipulator_cls.__name__} for {element_type_key}: {e}",
                        exc_info=True,
                    )
            else:
                logger.debug(f"  No manipulator class found in registry for key {manipulator_map_key}")
        return manipulators

    @property
    def extraction_service(self) -> 'ExtractionService':
        """Gets or creates the ExtractionService instance for this language."""
        from codehem.core.extraction_service import ExtractionService
        if self._extraction_service_instance is None:
            try:
                self._extraction_service_instance = ExtractionService(self.language_code)
            except Exception as e:
                logger.error(f'Failed to create ExtractionService instance for {self.language_code} on demand: {e}', exc_info=True)
                raise
        return self._extraction_service_instance

    def _get_supported_element_types_enum(self) -> List[CodeElementType]:
        """Helper to get CodeElementType enums for supported types."""
        supported_enums = []
        type_names = []
        supported_prop = getattr(self, 'supported_element_types', None)
        if callable(supported_prop):
             try:
                  type_names = supported_prop()
                  if type_names is None: type_names = []
             except Exception as e:
                  logger.error(f'Error accessing supported_element_types property in {self.__class__.__name__}: {e}', exc_info=True)
                  type_names = []
        elif isinstance(supported_prop, list):
             type_names = supported_prop
        else:
             logger.warning(f"Property 'supported_element_types' on {self.__class__.__name__} is missing or has unexpected type {type(supported_prop)}. Defaulting.")
             type_names = []

        for type_name in type_names:
            if not isinstance(type_name, str):
                logger.warning(f"Non-string value '{type_name}' found in supported_element_types for {self.__class__.__name__}")
                continue
            try:
                enum_member = CodeElementType(type_name.lower())
                supported_enums.append(enum_member)
            except ValueError:
                logger.warning(f"Unsupported element type string '{type_name}' listed in {self.__class__.__name__}.supported_element_types")

        if not supported_enums:
            logger.warning(f'{self.__class__.__name__} did not provide valid supported_element_types. Defaulting to all CodeElementType members.')
            supported_enums = list(CodeElementType)

        supported_enums = [et for et in supported_enums if et != CodeElementType.FILE]
        logger.debug(f'Final supported element types for {self.language_code} service init: {[e.value for e in supported_enums]}')
        return supported_enums

    @property
    def language_code(self) -> str:
        if not hasattr(self.__class__, 'LANGUAGE_CODE') or not self.__class__.LANGUAGE_CODE:
            raise AttributeError(f'Class {self.__class__.__name__} is missing required LANGUAGE_CODE attribute.')
        return self.__class__.LANGUAGE_CODE.lower()

    def get_element_descriptor(self, element_type: Union[str, CodeElementType]) -> Optional[ElementTypeLanguageDescriptor]:
        """Get a fully initialized descriptor instance by element type value (string)."""
        type_str = element_type.value if isinstance(element_type, CodeElementType) else str(element_type)
        descriptor = self.element_type_descriptors.get(type_str.lower())
        if descriptor and not descriptor._patterns_initialized:
             logger.error(f"Returning descriptor for {type_str} but its patterns are uninitialized. Check LanguageService init logs.")
        elif not descriptor:
             logger.debug(f"No descriptor found for element type '{type_str}' in language '{self.language_code}'. Available: {list(self.element_type_descriptors.keys())}")
        return descriptor

    def get_manipulator(self, element_type: Union[str, CodeElementType]) -> Optional[ManipulatorBase]:
        """Get a manipulator instance by element type value (string)."""
        type_str = element_type.value if isinstance(element_type, CodeElementType) else str(element_type)
        manipulator = self.manipulators.get(type_str.lower())
        if not manipulator:
            logger.debug(f"No manipulator instance found for '{type_str}' in {self.language_code}. Available: {list(self.manipulators.keys())}")
        return manipulator

    def get_extractor(self, element_type: Union[str, CodeElementType]) -> Optional[BaseExtractor]:
        """Get an extractor instance by element type value (string), trying language-specific first, then fallback."""
        type_str = element_type.value if isinstance(element_type, CodeElementType) else str(element_type)
        extractor_key = f'{self.language_code}/{type_str.lower()}'
        extractor = self.extractors.get(extractor_key)

        if not extractor:
            fallback_key = f'__all__/{type_str.lower()}'
            extractor = self.extractors.get(fallback_key)
            if extractor:
                 logger.debug(f"Using fallback extractor {extractor.__class__.__name__} for type '{type_str}'.")
            else:
                 logger.debug(f"No specific ('{extractor_key}') or fallback ('{fallback_key}') extractor instance found. Available keys: {list(self.extractors.keys())}")
        return extractor

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Get file extensions supported by this language."""
        pass

    @property
    @abstractmethod
    def supported_element_types(self) -> List[str]:
        """Get element type *string values* supported by this language."""
        pass

    @abstractmethod
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of element in the code.
        Args:
            code: The code to analyze
        Returns:
            Element type string (value from CodeElementType)
        """
        pass

    def extract(self, code: str) -> 'CodeElementsResult':
        """Extract code elements from source code using the service's extraction_service."""
        logger.debug(f'LanguageService ({self.language_code}): Starting extraction via self.extraction_service')
        try:
            extractor = self.extraction_service
        except Exception as e:
            logger.error(f'LanguageService ({self.language_code}): Cannot extract, failed to get ExtractionService: {e}', exc_info=True)
            from codehem.models.code_element import CodeElementsResult # Local import
            return CodeElementsResult(elements=[]) # Return empty result

        result = extractor.extract_all(code)
        result = self.extract_language_specific(code, result)
        logger.debug(f'LanguageService ({self.language_code}): Completed extraction via self.extraction_service. Found {len(result.elements)} top-level elements.')
        return result

    def extract_language_specific(self, code: str, current_result: 'CodeElementsResult') -> 'CodeElementsResult':
        """Optional hook for language-specific post-extraction adjustments."""
        return current_result

    @abstractmethod
    def get_text_by_xpath_internal(self, code: str, xpath_nodes: List['CodeElementXPathNode']) -> Optional[str]:
        """
        Internal method to retrieve text content based on parsed XPath nodes.
        To be implemented by language-specific services.
        """
        logger.error(f'get_text_by_xpath_internal not implemented in LanguageService subclass for {self.language_code}')
        return None