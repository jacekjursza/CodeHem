import logging
import sys

import rich

from codehem import CodeHem
from codehem.core.registry import registry

# Set up more detailed logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(levelname)s:%(name)s:%(message)s')

# Set specific modules to higher log level to reduce noise
logging.getLogger('tree_sitter').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

def test_registry():
    """Test the registry system for components."""
    logger.info("Testing registry system...")
    
    # Check language detectors
    logger.info("Registered Language Detectors:")
    for code, detector in registry.language_detectors.items():
        logger.info(f"  {code}: {detector.__class__.__name__}")
    
    # Check language services
    logger.info("Registered Language Services:")
    for code, service in registry.language_services.items():
        logger.info(f"  {code}: {service.__class__.__name__}")
    
    # Check extractors
    logger.info("Registered Extractors:")
    for code, extractor in registry.extractors.items():
        logger.info(f"  {code}: {extractor.__name__}")
    
    # Check handlers
    logger.info("Registered Handlers:")
    for lang, handlers in registry.handlers.items():
        logger.info(f"  {lang}:")
        for element_type, handler in handlers.items():
            logger.info(f"    {element_type}: {handler.__class__.__name__}")
    
    logger.info("")

def test_extractors():
    """Test the extraction functionality."""
    print("Testing extractors...")
    
    # Sample Python code
    code = """
from pydantic import BaseModel, Field

class MyClass:
    static_property: str = "Hello, World!"
    
    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        return f"Hello, {self.name}!"
    
    @mydecorator
    def other(self, x: int, y: str) -> str:
        return f"This is other: {x} {y}"."

def my_function(x: int) -> int:
    return x + 1
"""
    
    # Create CodeHem instance for Python
    hem = CodeHem('python')
    
    # Extract elements
    elements = hem.extract(code)
    
    # Print the result
    print("----------------------------------")
    rich.print(elements)
    print("----------------------------------")

if __name__ == "__main__":
    test_registry()
    test_extractors()