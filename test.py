import rich
from codehem.models.enums import CodeElementType
from codehem.main import CodeHem
import logging
import importlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


my_test_code = '''
from pydantic import BaseModel, Field

class MyClass:
    static_property: str = "Hello, World!"
    
    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        return f"Hello, {self.name}!"
    
    @mydecorator
    def other(self) -> str:
        return "This is other."


def my_function(x: int) -> int:
    return x + 1

'''


def test_registry():
    """Test the registry system."""
    from codehem.languages.registry import registry
    logger.info('Registered Language Detectors:')
    for (lang, detector) in registry.language_detectors.items():
        logger.info(f'  {lang}: {detector.__class__.__name__}')
    logger.info('Registered Language Services:')
    for (lang, service) in registry.language_services.items():
        logger.info(f'  {lang}: {service.__class__.__name__}')
    logger.info('Registered Extractors:')
    for (element_type, extractor_class) in registry.extractors.items():
        logger.info(f'  {element_type}: {extractor_class.__name__}')
    logger.info('Registered Handlers:')
    for (lang, handlers) in registry.handlers.items():
        logger.info(f'  {lang}:')
        for (element_type, handler) in handlers.items():
            logger.info(f'    {element_type}: {handler.__class__.__name__}')

def test_extractors():
    """Test extractors on a simple class."""
    ch = CodeHem('python')
    result = ch.extract(my_test_code)
    print('----------------------------------')
    rich.print(result)
    print('----------------------------------')

if __name__ == '__main__':
    logger.info('Testing registry system...')
    try:
        test_registry()
        logger.info('\nTesting extractors...')
        test_extractors()
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)