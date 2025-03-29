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
    - MyClass.greet[body]
    """
    ROOT_ELEMENT = 'FILE'
    _VALID_TYPES = {t.value for t in CodeElementType}
    _VALID_PARTS = {'body', 'def', 'decorators', 'comments', 'doc', 'signature', 'all'}

    @staticmethod
    def _infer_types(nodes: List[CodeElementXPathNode]) -> None:
        """
        Infer element types based on position and other nodes in the path.
        Skips inferring type if it is already set. Does not infer `part`.
        """
        if not nodes:
            return
        class_like_types = {CodeElementType.CLASS.value, CodeElementType.INTERFACE.value}
        for i, node in enumerate(nodes):
            if node.type:
                continue
            if i == 0:
                if len(nodes) == 1:
                    if node.name and node.name[0].isupper():
                        node.type = CodeElementType.CLASS.value
                    else:
                        node.type = CodeElementType.FUNCTION.value
                else:
                    node.type = CodeElementType.CLASS.value
            elif i == 1 and nodes[0].type in class_like_types:
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
        result = []
        for node in nodes:
            part = ""
            if node.name:
                part = node.name
            if node.type:
                part += f"[{node.type}]"
            if node.part:
                part += f"[{node.part}]"
            result.append(part)
        return ".".join(result)

    @staticmethod
    def get_element_info(
        xpath: str,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
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

    @staticmethod
    def parse(xpath: str) -> List[CodeElementXPathNode]:
        """
        Parse an XPath expression into a list of CodeElementXPathNode objects.
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
            type_match = re.match(r'^(?P<name>[^\[\]]+)?(?:\[(?P<first>[^\[\]]+)\])?(?:\[(?P<second>[^\[\]]+)\])?$', part)
            if not type_match:
                print(f'Invalid XPath part: {part}')
                continue
            name = type_match.group('name')
            first = type_match.group('first')
            second = type_match.group('second')
            node = CodeElementXPathNode(name=name)

            def assign_qualifier(item: Optional[str]):
                if not item:
                    return
                if item in XPathParser._VALID_TYPES:
                    node.type = item
                elif item in XPathParser._VALID_PARTS:
                    node.part = item
                else:
                    print(f'Unknown XPath qualifier: [{item}]')

            assign_qualifier(first)
            assign_qualifier(second)

            if node.is_valid:
                result.append(node)
        XPathParser._infer_types(result)
        return result
