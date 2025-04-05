"""
Python language module for CodeHem.
"""

NODE_CONFIG = {
    'function': {
        'name_field': 'name',
        'parameters_field': 'parameters',
        'body_field': 'body',
        'decorators_field': 'decorators',
        'parent_class_type': 'class_definition',
    },
    'method': {
        'name_field': 'name',
        'parameters_field': 'parameters',
        'body_field': 'body',
        'decorators_field': 'decorators',
        'parent_class_type': 'class_definition',
    },
    'class': {
        'name_field': 'name',
        'body_field': 'body',
        'decorators_field': 'decorators',
        'parent_class_type': None,
    },
    'decorator': {
        'name_field': 'name',
    },
    'property_getter': {
        'name_field': 'name',
        'body_field': 'body',
        'decorators_field': 'decorators',
        'parent_class_type': 'class_definition',
    },
    'property_setter': {
        'name_field': 'name',
        'body_field': 'body',
        'decorators_field': 'decorators',
        'parent_class_type': 'class_definition',
    },
    'static_method': {
        'name_field': 'name',
        'parameters_field': 'parameters',
        'body_field': 'body',
        'decorators_field': 'decorators',
        'parent_class_type': 'class_definition',
    },
    'import': {
        'name_field': 'name',  # or 'module' depending on AST
    },
}
from codehem.core.registry import registry
from .service import PythonLanguageService
from .manipulator.method_handler import PythonMethodManipulator
from .python_ast_manipulator import PythonASTManipulator
from codehem.models.enums import CodeElementType
import logging

def initialize_python_language():
    """
    Initialize and register Python language manipulators and services.
    This function clears existing 'python_' manipulators and registers patched versions.
    Call this explicitly before using Python language features or running tests.
    """
    # Clear all existing python manipulators
    keys_to_remove = [k for k in list(registry.all_manipulators.keys()) if k.startswith('python_')]
    for k in keys_to_remove:
        registry.all_manipulators.pop(k, None)
    logging.debug(f"Cleared {len(keys_to_remove)} existing python manipulators.")

    # Register AST manipulators for function, class, import
    for element_type_enum in [
        CodeElementType.FUNCTION,
        CodeElementType.CLASS,
        CodeElementType.IMPORT,
    ]:
        element_type_name = element_type_enum.value.lower()
        Wrapper = type(
            f"Python{element_type_name.capitalize()}ASTManipulator",
            (PythonASTManipulator,),
            {
                'LANGUAGE_CODE': 'python',
                'ELEMENT_TYPE': element_type_enum
            }
        )
        registry.register_manipulator(Wrapper)
        logging.debug(f"Registered ASTManipulator: Python{element_type_name.capitalize()}ASTManipulator for element_type: {element_type_enum}")

    # Register PythonASTManipulator for other element types
    for element_type_enum in [
        CodeElementType.METHOD,
        CodeElementType.PROPERTY_GETTER,
        CodeElementType.PROPERTY_SETTER,
        CodeElementType.STATIC_PROPERTY,
    ]:
        element_type_name = element_type_enum.value.lower()
        Wrapper = type(
            f"Python{element_type_name.capitalize()}ASTManipulator",
            (PythonASTManipulator,),
            {
                'LANGUAGE_CODE': 'python',
                'ELEMENT_TYPE': element_type_enum
            }
        )
        registry.register_manipulator(Wrapper)
        logging.debug(f"Registered ASTManipulator: Python{element_type_name.capitalize()}ASTManipulator for element_type: {element_type_enum}")

    # Register the Python language service (if needed elsewhere)
    # This import ensures the service is available
    logging.debug("Python language initialization complete.")
