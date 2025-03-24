"""
Simplified test script for tree-sitter Python grammar.
"""
import tree_sitter_python
from tree_sitter import Language, Parser
import sys

from codehem.core.engine.languages import get_parser

# Initialize tree-sitter

PY_LANGUAGE = Language(tree_sitter_python.language())
parser = get_parser("python")

# Simple test code with a decorated method
TEST_CODE = """
@class_decorator
class MyClass:
    
    @method_decorator
    def greet(self):
        print("Hello")
        
    @property
    def name(self):
        return self._name
"""

# Parse the code
code_bytes = TEST_CODE.encode('utf8')
tree = parser.parse(code_bytes)
root_node = tree.root_node

def get_node_text(node):
    """Get the text content of a node."""
    return code_bytes[node.start_byte:node.end_byte].decode('utf8')

def print_node(node, indent=0):
    """Print a node with its type, text and children."""
    text = get_node_text(node)
    if len(text) > 50:
        text = text[:25] + "..." + text[-25:]
    text = text.replace('\n', '\\n')
    
    print(f"{' ' * indent}{node.type}: '{text}'")
    
    # Print any available field names
    for i in range(node.child_count):
        child = node.child(i)
        child_info = f"{child.type}"
        
        # Try to identify fields
        field_name = None
        if node.type == "class_definition" and child.type == "identifier":
            field_name = "name"
        elif node.type == "function_definition" and child.type == "identifier":
            field_name = "name"
        elif node.type == "decorator" and child.type == "identifier":
            field_name = "name"
        
        if field_name:
            print(f"{' ' * (indent+2)}Field '{field_name}': {child.type}: '{get_node_text(child)}'")
        
        # Recursively print child nodes
        print_node(child, indent + 4)

print("=" * 80)
print("AST STRUCTURE ANALYSIS")
print("=" * 80)
print_node(root_node)

print("\n" + "=" * 80)
print("LOOKING FOR DECORATED DEFINITIONS")
print("=" * 80)

# Manually search for decorated methods
for i in range(root_node.child_count):
    node = root_node.child(i)
    if node.type == "decorated_definition":
        print(f"Found decorated_definition: '{get_node_text(node)}'")
        # Print children
        print("Children:")
        for j in range(node.child_count):
            child = node.child(j)
            print(f"  {child.type}: '{get_node_text(child)}'")

# Test simple function definition query manually
print("\n" + "=" * 80)
print("TESTING SIMPLE QUERY")
print("=" * 80)

from tree_sitter import Query

# Create a simple query to find function definitions
query_string = "(function_definition) @function"
try:
    query = Query(PY_LANGUAGE, query_string)
    captures = []
    
    def capture_callback(match, node, capture_name):
        text = get_node_text(node)
        if len(text) > 50:
            text = text[:25] + "..." + text[-25:]
        captures.append((node, capture_name, text))
    
    query.captures(root_node, capture_callback)
    
    print(f"Query results for '{query_string}':")
    for node, name, text in captures:
        print(f"  {name}: {node.type}: '{text}'")
except Exception as e:
    print(f"Error executing query: {str(e)}")

print("\nSimple test complete.")