"""
XPath parser for CodeHem.
Provides functionality to parse and work with XPath-like expressions for code elements.
"""
import re
import logging
from typing import List, Optional, Tuple, Set, TYPE_CHECKING
import sys # For printing errors

# Keep direct model imports to prevent circular dependency
from codehem.models.enums import CodeElementType
from codehem.models.xpath import CodeElementXPathNode

logger = logging.getLogger(__name__)

class XPathParser:
    """
    Parser for XPath-like expressions used to locate code elements.
    """
    ROOT_ELEMENT = 'FILE'
    _VALID_TYPES = {t.value for t in CodeElementType}
    _VALID_PARTS = {'body', 'def', 'decorators', 'comments', 'doc', 'signature', 'all'}

    # Keep helper, but it's not used by parse() by default
    @staticmethod
    def _ensure_file_prefix(xpath: str) -> str:
        """Static helper to ensure XPath starts with FILE."""
        root_prefix = XPathParser.ROOT_ELEMENT + '.'
        if not xpath.startswith(root_prefix) and (not xpath.startswith('[')):
            xpath = root_prefix + xpath
        return xpath

    @staticmethod
    def _infer_types(nodes: List[CodeElementXPathNode]) -> None:
        """
        Infer element types based on position and other nodes in the path.
        Skips inferring type if it is already set. Does not infer `part`.
        (Logic adjusted slightly based on whether FILE node is present)
        """
        if not nodes:
            return

        class_like_types = {CodeElementType.CLASS.value, CodeElementType.INTERFACE.value}
        file_node_present = nodes[0].type == CodeElementType.FILE.value
        start_index = 1 if file_node_present else 0
        num_meaningful_nodes = len(nodes) - start_index

        if num_meaningful_nodes <= 0:
             return

        for i in range(start_index, len(nodes)):
            node = nodes[i]
            rel_index = i - start_index

            if node.type:
                continue

            if rel_index == 0: # First meaningful element
                if num_meaningful_nodes == 1: # Only one element specified
                    # Don't infer type for single elements - let ElementFilter handle matching
                    # This allows "IUser" to match both classes and interfaces
                    pass  # Leave node.type as None
                else: # First element in a longer path
                    # For multi-element paths, still assume first element is class-like
                    if node.name and node.name[0].isupper():
                        node.type = CodeElementType.CLASS.value # Could be class or interface
                    else:
                        node.type = CodeElementType.FUNCTION.value # Default assumption
            elif rel_index > 0: # Nested element
                parent_node = nodes[i-1] # The actual previous node in list
                if parent_node.type in class_like_types:
                    node.type = CodeElementType.METHOD.value # Default assumption
        # logger.debug(f"Inferred types for XPath nodes: {[str(n) for n in nodes]}") # Keep logging if needed

    @staticmethod
    def to_string(nodes: List[CodeElementXPathNode]) -> str:
        """
        Convert a list of nodes back to an XPath string.
        (Reverted to simpler logic respecting original FILE presence)
        """
        if not nodes:
            return ''

        parts = []
        has_file_prefix = nodes[0].type == CodeElementType.FILE.value
        start_index = 1 if has_file_prefix else 0

        if has_file_prefix:
            parts.append(XPathParser.ROOT_ELEMENT)

        for i in range(start_index, len(nodes)):
            node = nodes[i]
            part_str = ''
            if node.name:
                part_str = node.name
            if node.type:
                part_str += f'[{node.type}]'
            if node.part:
                part_str += f'[{node.part}]'

            if part_str: # Append only if node contributed something
                parts.append(part_str)
            # If node was invalid but not FILE, maybe log? For now, just skip.

        # Join parts with '.' , handling the case where only FILE was present
        if len(parts) == 1 and has_file_prefix:
            return parts[0] # Just "FILE"
        elif has_file_prefix:
            return parts[0] + '.' + '.'.join(parts[1:])
        else:
            return '.'.join(parts)

    @staticmethod
    def get_element_info(xpath: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract element name, parent name, and inferred/explicit type from an XPath.
        Parses the original XPath without forcing FILE prefix.
        """
        nodes = XPathParser.parse(xpath) # Parse the original string

        if not nodes:
            return (None, None, None)

        # Handle simple cases first
        if len(nodes) == 1:
             node = nodes[0]
             # If it's FILE node, parent is None, type is FILE
             if node.type == CodeElementType.FILE.value:
                  return (None, None, CodeElementType.FILE.value)
             # Otherwise, it's a top-level element (like Class or function)
             else:
                  return (node.name, None, node.type)

        # More than one node
        target_node = nodes[-1]
        parent_node = nodes[-2]

        element_name = target_node.name
        element_type = target_node.type

        # Parent name is the name of the second-to-last node, unless it's FILE
        parent_name = None
        if parent_node.type != CodeElementType.FILE.value:
             parent_name = parent_node.name

        # logger.debug(f"get_element_info for '{xpath}': name='{element_name}', parent='{parent_name}', type='{element_type}'") # Keep if needed
        return (element_name, parent_name, element_type)

    @staticmethod
    def parse(xpath: str) -> List[CodeElementXPathNode]:
        """
        Parse an XPath expression into a list of CodeElementXPathNode objects.
        Does NOT force FILE prefix. Infers types.
        """
        if not xpath:
            return []

        parts = xpath.split('.')
        result: List[CodeElementXPathNode] = []
        is_first_part = True

        for part in parts:
            if not part:
                logger.warning(f"Skipping empty part found in XPath '{xpath}'.")
                continue

            # Check if the first part is the FILE root element
            if is_first_part and part == XPathParser.ROOT_ELEMENT:
                result.append(CodeElementXPathNode(type=CodeElementType.FILE.value))
                is_first_part = False # Only the very first part can be FILE
                continue

            is_first_part = False # Subsequent parts cannot be FILE node

            # Regex to parse name and up to two bracketed qualifiers [type] or [part]
            match = re.match(r'^(?P<name>[^\[\]]+)?(?:\[(?P<qual1>[^\[\]]+)\])?(?:\[(?P<qual2>[^\[\]]+)\])?$', part)

            if not match:
                logger.warning(f"Invalid XPath part format: '{part}' in '{xpath}'. Skipping.")
                continue

            name = match.group('name')
            qual1 = match.group('qual1')
            qual2 = match.group('qual2')

            # Create node first, might be nameless (e.g., "[import]")
            node = CodeElementXPathNode(name=name)
            found_type = None
            found_part = None

            def assign_qualifier(item: Optional[str]):
                nonlocal found_type, found_part
                if not item: return
                item_lower = item.lower()
                is_type = item_lower in XPathParser._VALID_TYPES
                is_part = item_lower in XPathParser._VALID_PARTS
                if is_type and found_type is None: found_type = item_lower
                elif is_part and found_part is None: found_part = item_lower
                elif is_type and found_type is not None: logger.warning(f"Duplicate type qualifier: '[{item}]' in part '{part}'. Ignoring.")
                elif is_part and found_part is not None: logger.warning(f"Duplicate part qualifier: '[{item}]' in part '{part}'. Ignoring.")
                elif not is_type and not is_part: logger.warning(f"Unknown XPath qualifier: '[{item}]' in part '{part}'. Ignoring qualifier.")

            assign_qualifier(qual1)
            assign_qualifier(qual2)

            node.type = found_type
            node.part = found_part

            if node.is_valid:
                result.append(node)
            elif not node.name and not node.type and not node.part:
                 logger.warning(f"Skipping completely empty node parsed from part '{part}'.")

        # Infer types after parsing all parts
        XPathParser._infer_types(result)

        return result