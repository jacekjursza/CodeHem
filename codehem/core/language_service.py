# MODIFIED FILE: Corrected storage key for extractor instances in __init__
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Type, Union, TYPE_CHECKING
from codehem.core.extractors.base import BaseExtractor
from codehem.core.formatting.formatter import BaseFormatter
from codehem.core.manipulators.manipulator_base import ManipulatorBase
from codehem.models.enums import CodeElementType
from codehem.models.xpath import CodeElementXPathNode
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
# Import registry and creation function
from codehem.core.registry import registry
from codehem.models.element_type_template import create_element_type_descriptor # Function to create descriptor attributes
# Use TYPE_CHECKING to avoid runtime circular imports if needed later
if TYPE_CHECKING:
    from codehem.core.extraction_service import ExtractionService
    from codehem.models.code_element import CodeElementsResult # Keep for hints

logger = logging.getLogger(__name__)

class LanguageService(ABC):
    """
    Base class for language-specific services.
    Defines the interface for language-specific operations and combines finder, formatter, and manipulator.
    """
    LANGUAGE_CODE: str # Must be defined by subclasses
    _instances: Dict[str, 'LanguageService'] = {}

    # Singleton pattern remains the same
    def __new__(cls, *args, **kwargs):
        language_code = getattr(cls, 'LANGUAGE_CODE', None)
        if not language_code:
            try:
                 language_code = kwargs.get('language_code', args[0] if args else None)
                 if not language_code: raise ValueError("LANGUAGE_CODE missing")
            except:
                 raise ValueError(f'{cls.__name__} must define LANGUAGE_CODE or receive it during instantiation.')

        lang_code_lower = language_code.lower()
        if lang_code_lower not in cls._instances:
            logger.debug(f'[__new__] Creating new singleton instance for {lang_code_lower}')
            cls._instances[lang_code_lower] = super().__new__(cls)
        else:
            logger.debug(f'[__new__] Reusing existing instance for {lang_code_lower}')
        return cls._instances[lang_code_lower]

    def __init__(self, formatter_class: Optional[Type[BaseFormatter]] = None, **kwargs):
        """
        Initialize the language service.
        Creates language-specific descriptor and extractor instances.

        Args:
            formatter_class: Optional formatter class for this language.
                             If None, uses BaseFormatter.
            **kwargs: Catches potential arguments from old __new__ or direct calls.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

        current_language_code = self.language_code # Read via property

        logger.info(f"Initializing LanguageService for '{current_language_code}'...")

        self.element_type_descriptors: Dict[str, ElementTypeLanguageDescriptor] = {}
        self.extractors: Dict[str, BaseExtractor] = {} # Stores INSTANCES
        self.manipulators: Dict[str, ManipulatorBase] = {} # Stores INSTANCES

        self.formatter = formatter_class() if formatter_class else BaseFormatter()
        logger.debug(f"Using formatter: {self.formatter.__class__.__name__}")

        self._extraction_service_instance: Optional['ExtractionService'] = None

        logger.debug("Creating language-specific element type descriptors...")
        supported_types = self._get_supported_element_types_enum()
        for element_type in supported_types:
            descriptor_attrs = create_element_type_descriptor(current_language_code, element_type)
            if descriptor_attrs:
                try:
                    descriptor_instance = ElementTypeLanguageDescriptor(**descriptor_attrs)
                    self.element_type_descriptors[element_type.value.lower()] = descriptor_instance
                    logger.debug(f"  Created descriptor instance for {element_type.value}")
                except Exception as e:
                     logger.error(f"  Failed to instantiate ElementTypeLanguageDescriptor for {element_type.value}: {e}", exc_info=True)
            else:
                # Log during init is better than during discovery/import time
                logger.warning(f"  Could not generate descriptor attributes for {current_language_code}/{element_type.value}")

        logger.debug("Creating language-specific extractor instances...")
        all_extractor_classes = registry.all_extractors
        for element_type in supported_types:
            element_type_key = element_type.value.lower()
            descriptor_instance = self.element_type_descriptors.get(element_type_key)
            if not descriptor_instance:
                logger.warning(f"  Skipping extractor for {element_type_key} - descriptor not found/created.")
                continue

            # Key format used to REGISTER extractor classes
            extractor_key = f'{current_language_code}/{element_type_key}'
            extractor_cls = all_extractor_classes.get(extractor_key)

            if not extractor_cls:
                 fallback_key = f'__all__/{element_type_key}'
                 extractor_cls = all_extractor_classes.get(fallback_key)
                 if extractor_cls:
                      logger.debug(f"  Using fallback extractor class {extractor_cls.__name__} for {element_type_key}")

            if extractor_cls:
                try:
                    extractor_instance = extractor_cls(language_code=current_language_code, language_type_descriptor=descriptor_instance)
                    # *** CHANGE START: Use the correct key for storage ***
                    self.extractors[extractor_key] = extractor_instance # Store instance keyed by 'lang/type'
                    # *** CHANGE END ***
                    logger.debug(f"  Created extractor instance: {extractor_instance.__class__.__name__} for key '{extractor_key}'")
                except Exception as e:
                     logger.error(f"  Failed to instantiate extractor {extractor_cls.__name__} for {element_type_key}: {e}", exc_info=True)
            else:
                logger.warning(f"  No extractor class found in registry for {element_type_key} or fallback __all__/{element_type_key}")

        logger.debug("Creating language-specific manipulator instances...")
        all_manipulator_classes = registry.all_manipulators
        for element_type in supported_types:
            element_type_key = element_type.value.lower()
            # Key format used to REGISTER manipulator classes
            manipulator_map_key = f'{current_language_code}_{element_type_key}'
            manipulator_cls = all_manipulator_classes.get(manipulator_map_key)

            if manipulator_cls:
                try:
                    manipulator_instance = manipulator_cls(
                        language_code=current_language_code,
                        element_type=element_type,
                        formatter=self.formatter
                    )
                    # Store manipulator instance keyed by just the element type value
                    self.manipulators[element_type_key] = manipulator_instance
                    logger.debug(f"  Created manipulator instance: {manipulator_instance.__class__.__name__} for {element_type_key}")
                except Exception as e:
                    logger.error(f"  Failed to instantiate manipulator {manipulator_cls.__name__} for {element_type_key}: {e}", exc_info=True)
            else:
                logger.debug(f"  No manipulator class found in registry for key {manipulator_map_key}")

        logger.info(f"LanguageService for '{current_language_code}' initialization complete. Loaded {len(self.element_type_descriptors)} descriptors, {len(self.extractors)} extractors, {len(self.manipulators)} manipulators.")

    @property
    def extraction_service(self) -> 'ExtractionService':
        """Gets or creates the ExtractionService instance for this language."""
        # Import locally to help avoid cycles if called during complex init sequences
        from codehem.core.extraction_service import ExtractionService
        if self._extraction_service_instance is None:
             try:
                 # Pass self (the LanguageService instance) to ExtractionService if needed,
                 # but current ExtractionService init doesn't require it.
                 self._extraction_service_instance = ExtractionService(self.language_code)
             except Exception as e:
                 logger.error(f"Failed to create ExtractionService instance for {self.language_code} on demand: {e}", exc_info=True)
                 raise
        return self._extraction_service_instance

    def _get_supported_element_types_enum(self) -> List[CodeElementType]:
        """Helper to get CodeElementType enums for supported types."""
        supported_enums = []
        type_names = []
        # Check if the abstract property is implemented
        if hasattr(self, 'supported_element_types') and callable(getattr(self, 'supported_element_types', None)):
             try:
                 # Call the property getter
                 type_names = self.supported_element_types
                 if type_names is None: type_names = [] # Ensure iterable
             except Exception as e:
                 logger.error(f"Error accessing supported_element_types property in {self.__class__.__name__}: {e}", exc_info=True)
                 type_names = [] # Fallback
        else:
            logger.warning(f"Property 'supported_element_types' not found or not callable on {self.__class__.__name__}. Defaulting.")
            type_names = []

        # Convert names to enums
        for type_name in type_names:
             if not isinstance(type_name, str): continue
             try:
                  # Match case-insensitively
                  enum_member = CodeElementType(type_name.lower())
                  supported_enums.append(enum_member)
             except ValueError:
                  logger.warning(f"Unsupported element type string '{type_name}' listed in {self.__class__.__name__}.supported_element_types")

        # Fallback if property was missing or returned no valid types
        if not supported_enums:
             logger.warning(f"{self.__class__.__name__} did not provide valid supported_element_types. Defaulting to all CodeElementType members.")
             supported_enums = list(CodeElementType)

        # Ensure FILE is not included
        supported_enums = [et for et in supported_enums if et != CodeElementType.FILE]
        logger.debug(f"Supported element types for {self.language_code}: {[e.value for e in supported_enums]}")
        return supported_enums

    @property
    def language_code(self) -> str:
        if not hasattr(self.__class__, 'LANGUAGE_CODE') or not self.__class__.LANGUAGE_CODE:
             raise AttributeError(f"Class {self.__class__.__name__} is missing required LANGUAGE_CODE attribute.")
        return self.__class__.LANGUAGE_CODE.lower()

    def get_element_descriptor(self, element_type: Union[str, CodeElementType]) -> Optional[ElementTypeLanguageDescriptor]:
        """Get a descriptor instance by element type value (string)."""
        type_str = element_type.value if isinstance(element_type, CodeElementType) else str(element_type)
        return self.element_type_descriptors.get(type_str.lower())

    def get_manipulator(self, element_type: Union[str, CodeElementType]) -> Optional[ManipulatorBase]:
        """Get a manipulator instance by element type value (string)."""
        type_str = element_type.value if isinstance(element_type, CodeElementType) else str(element_type)
        manipulator = self.manipulators.get(type_str.lower())
        if not manipulator:
            logger.debug(f"No manipulator instance found for '{type_str}' in {self.language_code}. Available: {list(self.manipulators.keys())}")
        return manipulator

    def get_extractor(self, element_type: Union[str, CodeElementType]) -> Optional[BaseExtractor]:
        """Get an extractor instance by element type value (string)."""
        type_str = element_type.value if isinstance(element_type, CodeElementType) else str(element_type)
        # *** CHANGE START: Use the correct key format used during storage ***
        extractor_key = f'{self.language_code}/{type_str.lower()}'
        # *** CHANGE END ***
        extractor = self.extractors.get(extractor_key)
        if not extractor:
             logger.debug(f"No extractor instance found for key '{extractor_key}'. Available keys: {list(self.extractors.keys())}")
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
        logger.debug(f'LanguageService: Starting extraction for {self.language_code}')
        try:
             extractor = self.extraction_service # Use property access
        except Exception as e:
             logger.error(f"LanguageService: Cannot extract, failed to get ExtractionService for {self.language_code}: {e}", exc_info=True)
             from codehem.models.code_element import CodeElementsResult
             return CodeElementsResult(elements=[]) # Return empty result

        result = extractor.extract_all(code)
        result = self.extract_language_specific(code, result)
        logger.debug(f'LanguageService: Completed extraction with {len(result.elements)} top-level elements')
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