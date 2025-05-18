"""
TypeScript components initialization.

This module registers all TypeScript-specific components with the registry.
"""

import logging

from codehem.core.registry import registry
from .parser import TypeScriptCodeParser
from .navigator import TypeScriptSyntaxTreeNavigator
from .extractor import TypeScriptElementExtractor
from .post_processor import TypeScriptPostProcessor
from .orchestrator import TypeScriptExtractionOrchestrator

# Since 'register_component' method doesn't exist in Registry yet
# we will skip registration for now, to allow imports to proceed

"""
# Uncomment when component registration is implemented properly
# TODO: Implement proper component registration once the new architecture is fully in place
registry.register_component('typescript', 'code_parser', TypeScriptCodeParser)
registry.register_component('typescript', 'syntax_tree_navigator', TypeScriptSyntaxTreeNavigator)
registry.register_component('typescript', 'element_extractor', TypeScriptElementExtractor)
registry.register_component('typescript', 'post_processor', TypeScriptPostProcessor)
registry.register_component('typescript', 'extraction_orchestrator', TypeScriptExtractionOrchestrator)
"""

# For now, just log that these components are available
logger = logging.getLogger(__name__)
logger.info("TypeScript components are available but not registered with registry yet.")
