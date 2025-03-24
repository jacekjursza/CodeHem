"""
Register language services with the central registry.
"""
from . import register_language_service
from .python_service import PythonLanguageService
from .javascript_service import JavaScriptLanguageService
from .typescript_service import TypeScriptLanguageService
from .registry import registry

# Register language services
register_language_service('python', PythonLanguageService)
register_language_service('javascript', JavaScriptLanguageService)
register_language_service('typescript', TypeScriptLanguageService)

# Register Python handlers explicitly
from .lang_python.type_class import PythonClassHandler
from .lang_python.type_function import PythonFunctionHandler
from .lang_python.type_method import PythonMethodHandler
from .lang_python.type_import import PythonImportHandler
from .lang_python.type_property_getter import PythonPropertyGetterHandler
from .lang_python.type_property_setter import PythonPropertySetterHandler
from .lang_python.type_static_property import PythonStaticPropertyHandler

registry.register_handler(PythonClassHandler())
registry.register_handler(PythonFunctionHandler())
registry.register_handler(PythonMethodHandler())
registry.register_handler(PythonImportHandler())
registry.register_handler(PythonPropertyGetterHandler())
registry.register_handler(PythonPropertySetterHandler())
registry.register_handler(PythonStaticPropertyHandler())