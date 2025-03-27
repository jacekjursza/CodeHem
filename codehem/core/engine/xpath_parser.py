"""
XPath parser for CodeHem.
Provides functionality to parse and work with XPath-like expressions for code elements.
"""
import re
import logging
from typing import List, Optional, Tuple, Set

from codehem import CodeElementType

from ... import CodeElementXPathNode

logger = logging.getLogger(__name__)

class XPathParser:
    """
    Parser for XPath-like expressions used to locate code elements.
    Supports expressions like:
    - FILE.MyClass.my_method
    - MyClass.my_property[property_getter]
    - my_function
    - [import]
    - MyClass[interface]
    """
    
    # Constants for XPath components
    ROOT_ELEMENT = "FILE"
    
    # Cache valid type names once
    _VALID_TYPES = {t.value for t in CodeElementType}

    @staticmethod
    def parse(xpath: str) -> List[CodeElementXPathNode]:
        """
        Parse an XPath expression into a list of CodeElementXPathNode objects.

        Args:
        xpath: XPath-like expression (e.g., 'FILE.MyClass.my_method')

        Returns:
        List of CodeElementXPathNode objects representing the path
        """
        if not xpath:
            return []
        if xpath.startswith(f'{XPathParser.ROOT_ELEMENT}.'):
            parts = [XPathParser.ROOT_ELEMENT] + xpath[len(XPathParser.ROOT_ELEMENT) + 1:].split('.')
        else:
            parts = xpath.split('.')
        result = []
        for part in parts:
            if not part:
                continue
            if part == XPathParser.ROOT_ELEMENT:
                result.append(CodeElementXPathNode(type=CodeElementType.FILE.value))
                continue
            type_match = re.match('^(?:([^[\\]]+))?(?:\\[([^[\\]]+)\\])?$', part)
            if not type_match:
                logger.warning(f'Invalid XPath part: {part}')
                continue
            name, type_str = type_match.groups()

            # Special case for 'all' to avoid warning
            if type_str and type_str != 'all' and type_str not in XPathParser._VALID_TYPES:
                logger.warning(f'Invalid element type in XPath: {type_str}')

            node = CodeElementXPathNode(name=name, type=type_str)
            if node.is_valid:
                result.append(node)
        XPathParser._infer_types(result)
        return result
    

    @staticmethod
    def _infer_types(nodes: List[CodeElementXPathNode]) -> None:
        """
        Infer element types based on position and other nodes in the path.

        Args:
        nodes: List of CodeElementXPathNode objects
        """
        if not nodes:
            return

        # Define types that can contain members (like methods, properties)
        class_like_types = {
            CodeElementType.CLASS.value,
            CodeElementType.INTERFACE.value
        }

        # Infer types for nodes without explicit type
        for i, node in enumerate(nodes):
            if node.type:
                continue  # Type already specified

            # Infer based on position and name characteristics
            if i == 0:
                # First element could be a class or function (if it's the only element)
                if len(nodes) == 1:
                    # Heuristic: capitalized names are likely classes
                    if node.name and node.name[0].isupper():
                        node.type = CodeElementType.CLASS.value
                    else:
                        node.type = CodeElementType.FUNCTION.value
                else:
                    # First element in a longer path is usually a class
                    node.type = CodeElementType.CLASS.value
            elif i == 1 and nodes[0].type in class_like_types:
                # Second element in a class or interface is usually a method 
                # (unless it has a 'property' suffix or prefix)
                if node.name and ('property' in node.name.lower() or node.name.startswith('get_') or node.name.startswith('set_')):
                    node.type = CodeElementType.PROPERTY.value
                else:
                    node.type = CodeElementType.METHOD.value
    
    @staticmethod
    def to_string(nodes: List[CodeElementXPathNode]) -> str:
        """
        Convert a list of nodes back to an XPath string.
        
        Args:
            nodes: List of CodeElementXPathNode objects
            
        Returns:
            XPath string
        """
        if not nodes:
            return ""
            
        return ".".join(str(node) for node in nodes)
    
    @staticmethod
    def get_element_info(xpath: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract element name, parent name, and type from an XPath.
        
        Args:
            xpath: XPath-like expression
            
        Returns:
            Tuple of (element_name, parent_name, element_type)
        """
        nodes = XPathParser.parse(xpath)
        
        if not nodes:
            return None, None, None
            
        # Get the last node as the target element
        target = nodes[-1]
        element_name = target.name
        element_type = target.type
        
        # Get parent name from second-to-last node
        parent_name = None
        if len(nodes) > 1:
            parent = nodes[-2]
            parent_name = parent.name
        
        return element_name, parent_name, element_type