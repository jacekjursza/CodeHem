"""
Test file for exploring tree-sitter Python grammar and queries.
"""
import tree_sitter_python
from tree_sitter import Language, Parser, Query
import json
import re

from codehem.core2.engine.languages import get_parser

# Initialize tree-sitter
PY_LANGUAGE = Language(tree_sitter_python.language())
parser = get_parser("python")

# Test code with different Python structures
TEST_CODE = """
import os
from typing import List, Dict, Optional

@class_decorator
class MyClass:
    static_prop = "Hello, World!"
    
    def __init__(self, name):
        self.name = name
    
    @my_decorator
    def greet(self):
        print(f"Hello, my name is {self.name}!!!")
        
    @property
    def name_upper(self) -> str:
        return self.name.upper()
        
    @name_upper.setter
    def name_upper(self, value):
        self.name = value.lower()

def standalone_function(param: str) -> str:
    return param.upper()
"""

# Convert code to bytes for tree-sitter
code_bytes = TEST_CODE.encode('utf8')

# Parse the code
tree = parser.parse(code_bytes)
root_node = tree.root_node

def get_node_text(node, code_bytes):
    """Get the text content of a node."""
    return code_bytes[node.start_byte:node.end_byte].decode('utf8')

def print_node(node, code_bytes, indent=0, max_depth=20, name=None):
    """Print a node and its children with indentation, up to max_depth."""
    if indent > max_depth:
        print(f"{' ' * indent}... (max depth reached)")
        return
    
    prefix = f"{name}: " if name else ""
    print(f"{' ' * indent}{prefix}{node.type}")
    
    # Check for named children
    for i in range(node.named_child_count):
        child = node.named_child(i)
        field_name = None
        
        # Try to determine if this child corresponds to a field
        for field in ["name", "decorator", "decorators", "definition", "body"]:
            field_child = node.child_by_field_name(field)
            if field_child and field_child.id == child.id:
                field_name = field
                break
        
        print_node(child, code_bytes, indent + 2, max_depth, field_name)

def execute_query(query_string, root_node, code_bytes):
    """Execute a tree-sitter query and return results."""
    try:
        query = Query(PY_LANGUAGE, query_string)
        captures = query.captures(root_node, code_bytes)
        results = []
        for node, name in captures:
            node_text = get_node_text(node, code_bytes)
            text_preview = node_text.replace('\n', '\\n')
            if len(text_preview) > 50:
                text_preview = text_preview[:25] + "..." + text_preview[-25:]
            results.append((name, node.type, text_preview))
        return results
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return []

# First, examine the structure of the decorated method (greet)
print("\n\n")
print("=" * 80)
print("EXAMINING DECORATED METHOD STRUCTURE:")
print("=" * 80)

# Find the decorated definition for 'greet'
decorated_def = None
for i in range(root_node.named_child_count):
    child = root_node.named_child(i)
    if child.type == "decorated_definition":
        # Check if this contains the 'greet' method
        for j in range(child.named_child_count):
            sub_child = child.named_child(j)
            if sub_child.type == "function_definition":
                name_node = sub_child.child_by_field_name("name")
                if name_node and get_node_text(name_node, code_bytes) == "greet":
                    decorated_def = child
                    break
        if decorated_def:
            break

if decorated_def:
    print("Found decorated definition for 'greet'. Structure:")
    print_node(decorated_def, code_bytes)
    
    print("\nField names available:")
    for field_name in ["decorator", "decorators", "definition", "body", "name"]:
        field_value = decorated_def.child_by_field_name(field_name)
        if field_value:
            print(f"  {field_name}: {field_value.type}")
        else:
            print(f"  {field_name}: None")
else:
    print("Couldn't find decorated definition for 'greet'")

# Now let's test some queries
print("\n\n")
print("=" * 80)
print("TESTING QUERIES FOR DECORATED METHODS:")
print("=" * 80)

test_queries = [
    {
        "name": "Query 1: Basic function definition",
        "query": """
        (function_definition
            name: (identifier) @function_name)
        """
    },
    {
        "name": "Query 2: Decorated function",
        "query": """
        (decorated_definition
            (decorator)
            (function_definition
                name: (identifier) @method_name))
        """
    },
    {
        "name": "Query 3: Specific decorated method",
        "query": """
        (decorated_definition
            (decorator)
            (function_definition
                name: (identifier) @method_name
                (#eq? @method_name "greet")))
        """
    },
    {
        "name": "Query 4: Class with specific method",
        "query": """
        (class_definition
            name: (identifier) @class_name
            body: (block
                (decorated_definition
                    (function_definition
                        name: (identifier) @method_name
                        (#eq? @method_name "greet")))))
        """
    },
    {
        "name": "Query 5: Property getter",
        "query": """
        (decorated_definition
            (decorator
                name: (identifier) @decorator_name)
            (function_definition
                name: (identifier) @method_name))
        """
    }
]

for test in test_queries:
    print(f"\n{test['name']}")
    print(f"Query pattern:\n{test['query']}")
    results = execute_query(test['query'], root_node, code_bytes)
    if results:
        print("Results:")
        for name, node_type, text in results:
            print(f"  {name} ({node_type}): {text}")
    else:
        print("No results found.")

# Now create an improved template based on our findings
print("\n\n")
print("=" * 80)
print("RECOMMENDED TEMPLATES:")
print("=" * 80)

improved_templates = {
    "class": """
    (class_definition
        name: (identifier) @class_name (#eq? @class_name "{class_name}"))
    """,
    
    "method": """
    (function_definition
        name: (identifier) @method_name (#eq? @method_name "{method_name}"))
    """,
    
    "decorated_method": """
    (decorated_definition
        (decorator)
        (function_definition
            name: (identifier) @method_name (#eq? @method_name "{method_name}")))
    """,
    
    "property_getter": """
    (decorated_definition
        (decorator
            name: (identifier) @decorator_name (#eq? @decorator_name "property"))
        (function_definition
            name: (identifier) @property_name (#eq? @property_name "{property_name}")))
    """
}

for template_name, template in improved_templates.items():
    print(f"\n{template_name}:")
    print(template)

# Test the improved templates
print("\n\n")
print("=" * 80)
print("TESTING IMPROVED TEMPLATES:")
print("=" * 80)

test_values = {
    "class": {"class_name": "MyClass"},
    "method": {"method_name": "greet"},
    "decorated_method": {"method_name": "greet"},
    "property_getter": {"property_name": "name_upper"}
}

for template_name, values in test_values.items():
    template = improved_templates[template_name]
    formatted_query = template.format(**values)
    
    print(f"\nTemplate: {template_name}")
    print(f"Formatted query:\n{formatted_query}")
    
    results = execute_query(formatted_query, root_node, code_bytes)
    if results:
        print("Results:")
        for name, node_type, text in results:
            print(f"  {name} ({node_type}): {text}")
    else:
        print("No results found.")

print("\nExecution complete. Use these findings to update the template queries in CodeHem.")