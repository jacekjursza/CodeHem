"""
Python language module for CodeHem.
"""
# Ensure standard manipulators are registered via decorators in their respective files
# No explicit initialization function needed here anymore.
from codehem.core.registry import registry
from .service import PythonLanguageService
# Import manipulators to ensure they are discovered by the registry via decorators
from .manipulator.class_handler import PythonClassManipulator
from .manipulator.function_handler import PythonFunctionManipulator
from .manipulator.import_handler import PythonImportManipulator
from .manipulator.method_handler import PythonMethodManipulator
from .manipulator.property_handler import PythonPropertyManipulator

# Import type descriptors to ensure they are discovered
from .type_class import PythonClassHandlerElementType
from .type_decorator import PythonDecoratorHandlerElementType
from .type_function import PythonFunctionHandlerElementType
from .type_import import PythonImportHandlerElementType
from .type_method import PythonMethodHandlerElementType
from .type_property_getter import PythonPropertyGetterHandlerElementType
from .type_property_setter import PythonPropertySetterHandlerElementType
from .type_static_property import PythonStaticPropertyHandlerElementType

# Import detector and formatter
from .detector import PythonLanguageDetector
from .formatting.python_formatter import PythonFormatter

# Note: NODE_CONFIG was removed as it was related to the removed AST manipulator.