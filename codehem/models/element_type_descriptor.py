# Content of codehem\models\element_type_descriptor.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Mapping # Added Mapping
import logging
import json # Added for pretty printing dicts

from codehem.models.enums import CodeElementType
# Removed: from codehem.core.registry import registry # Keep removed
from codehem.models.element_type_template import create_element_type_descriptor

logger = logging.getLogger(__name__)

@dataclass
class ElementTypeLanguageDescriptor:
    """
    Abstract base class for language handlers.
    Provides patterns (tree_sitter_query and regexp_pattern) for element finding,
    but does not implement the search logic itself. The actual element finding
    is implemented in higher-level components (extractors, finders) that use
    these patterns.
    When custom_extract=True, the handler implements its own extraction logic
    in the extract() method.

    Patterns are initialized lazily via initialize_patterns().
    """
    # Fields that identify the descriptor - set by subclass attributes typically
    language_code: Optional[str] = field(default=None, init=False)
    element_type: Optional[CodeElementType] = field(default=None, init=False)

    # Pattern fields - initialized as None, populated by initialize_patterns()
    tree_sitter_query: Optional[str] = field(default=None, init=False)
    regexp_pattern: Optional[str] = field(default=None, init=False)
    custom_extract: bool = field(default=False, init=False) # Default, can be overridden by subclass or template

    # Internal state
    _patterns_initialized: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        """
        Ensures language_code and element_type are set from the class attributes
        if they weren't provided via __init__.
        Does NOT initialize patterns here.
        """
        cls = self.__class__
        # Prefer _LANGUAGE and _TYPE if defined (new convention)
        if self.language_code is None and hasattr(cls, '_LANGUAGE'):
            self.language_code = cls._LANGUAGE
        # Fallback to older direct class attribute (less preferred)
        elif self.language_code is None and hasattr(cls, 'language_code') and isinstance(cls.language_code, str):
             self.language_code = cls.language_code

        if self.element_type is None and hasattr(cls, '_TYPE'):
            self.element_type = cls._TYPE
        elif self.element_type is None and hasattr(cls, 'element_type') and isinstance(cls.element_type, CodeElementType):
            self.element_type = cls.element_type

        # Ensure custom_extract gets its default if defined on the class
        # This allows subclasses to define custom_extract = True directly
        class_custom_extract = getattr(cls, 'custom_extract', False)
        if isinstance(class_custom_extract, bool):
             self.custom_extract = class_custom_extract

        if not self.language_code or not self.element_type:
             # This might happen temporarily during registration before LanguageService.__init__ sets them
             pass # logger.warning(f"Descriptor class {cls.__name__} instance created without language_code or element_type fully set yet.")

    def initialize_patterns(self) -> bool:
        """
        Initializes the tree_sitter_query and regexp_pattern based on language config.
        This should be called after the registry has loaded all language configs.
        Returns True if patterns were successfully initialized (or already were), False otherwise.
        """
        if self._patterns_initialized:
            # logger.debug(f"Patterns already initialized for {self.language_code}/{getattr(self.element_type, 'value', 'N/A')}") # Reduce noise
            return True
        if not self.language_code or not self.element_type:
            logger.error(f"Cannot initialize patterns for {self.__class__.__name__}: language_code or element_type is missing.")
            return False

        # --- Local import to avoid circular dependency at module level ---
        from codehem.core.registry import registry
        # --- End Local import ---

        # --- Added Detailed Logging ---
        logger.debug(f"Attempting pattern initialization for {self.language_code}/{self.element_type.value} in {self.__class__.__name__}")

        # 1. Get the language config dictionary from the registry
        lang_config = registry.get_language_config(self.language_code)
        if not lang_config:
             logger.error(f"  [{self.language_code}/{self.element_type.value}] Could not retrieve language configuration from registry.")
             return False
        logger.debug(f"  [{self.language_code}/{self.element_type.value}] Successfully retrieved lang_config.")

        # 2. Extract the placeholder map for this language
        all_language_placeholders = lang_config.get('template_placeholders', {})
        if not isinstance(all_language_placeholders, Mapping):
             logger.error(f"  [{self.language_code}/{self.element_type.value}] Invalid 'template_placeholders' format in config: Expected dict, got {type(all_language_placeholders)}.")
             return False
        if not all_language_placeholders:
             logger.warning(f"  [{self.language_code}/{self.element_type.value}] Retrieved 'template_placeholders' dictionary is empty.")
        else:
             # Log first few keys to verify content without being too verbose
             logged_keys = list(all_language_placeholders.keys())[:5]
             logger.debug(f"  [{self.language_code}/{self.element_type.value}] Retrieved {len(all_language_placeholders)} language placeholders. Sample keys: {logged_keys}")

        # 3. Call the modified factory function, passing the placeholders
        descriptor_attrs = create_element_type_descriptor(
             self.language_code,
             self.element_type,
             all_language_placeholders # Pass the fetched placeholders
        )

        # 4. Assign the formatted patterns to self
        if descriptor_attrs:
            self.tree_sitter_query = descriptor_attrs.get('tree_sitter_query')
            self.regexp_pattern = descriptor_attrs.get('regexp_pattern')
            template_custom_extract = descriptor_attrs.get('custom_extract')
            if isinstance(template_custom_extract, bool):
                 self.custom_extract = template_custom_extract

            self._patterns_initialized = True
            # Log success status clearly
            ts_status = 'Yes' if self.tree_sitter_query else 'No'
            rx_status = 'Yes' if self.regexp_pattern else 'No'
            logger.info(f"  Patterns initialized SUCCESSFULLY for {self.language_code}/{self.element_type.value}. TS: {ts_status}, RX: {rx_status}, Custom: {self.custom_extract}")
            return True
        else:
            # Log failure clearly
            logger.error(f"  Pattern initialization FAILED for {self.language_code}/{self.element_type.value} (create_element_type_descriptor returned None). Patterns remain uninitialized.")
            # Keep _patterns_initialized as False
            return False

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Custom extraction logic for language handlers with custom_extract=True.
        Base implementation returns empty list.
        Args:
            code: The source code to extract from
            context: Optional context information for the extraction

        Returns:
            List of extracted elements as dictionaries
        """
        if not self.custom_extract:
             logger.warning(f"extract() called on non-custom descriptor {self.__class__.__name__}")
        return []

    @property
    def lang_code(self) -> Optional[str]:
        return self.language_code

    @property
    def el_type(self) -> Optional[CodeElementType]:
        return self.element_type