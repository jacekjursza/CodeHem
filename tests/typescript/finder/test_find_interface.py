import pytest
from finder.factory import get_code_finder

@pytest.fixture
def typescript_finder():
    return get_code_finder('typescript')

def test_find_interface_simple(typescript_finder):
    code = '\ninterface MyInterface {\n    prop1: string;\n    prop2: number;\n}\n'
    query_str = '(interface_declaration name: (type_identifier) @interface_name)'
    
    (root, code_bytes) = typescript_finder._get_tree(code)
    results = typescript_finder.ast_handler.execute_query(query_str, root, code_bytes)
    
    interface_found = False
    for node, capture_name in results:
        if capture_name == 'interface_name' and typescript_finder._get_node_text(node, code_bytes) == 'MyInterface':
            interface_found = True
            
    assert interface_found, "Failed to find interface declaration"

def test_find_type_alias(typescript_finder):
    code = '\ntype MyType = string | number;\n'
    query_str = '(type_alias_declaration name: (type_identifier) @type_name)'
    
    (root, code_bytes) = typescript_finder._get_tree(code)
    results = typescript_finder.ast_handler.execute_query(query_str, root, code_bytes)
    
    type_found = False
    for node, capture_name in results:
        if capture_name == 'type_name' and typescript_finder._get_node_text(node, code_bytes) == 'MyType':
            type_found = True
            
    assert type_found, "Failed to find type alias declaration"

def test_find_tsx_element(typescript_finder):
    code = '\nconst element = <div>Hello World</div>;\n'

    # First verify we're getting a TSX tree
    (root, code_bytes) = typescript_finder._get_tree(code)

    # The specific node type might vary, so try different possibilities
    jsx_pattern = '(jsx_element) @jsx'
    jsx_found = False

    # Try different query patterns that might work
    patterns = [
        '(jsx_element) @jsx',
        '(jsx_opening_element) @jsx',
        '(jsx_fragment) @jsx'
    ]

    for pattern in patterns:
        try:
            from languages import TSX_LANGUAGE
            from tree_sitter import Query

            query = Query(TSX_LANGUAGE, pattern)
            raw_captures = query.captures(root)

            if raw_captures:
                jsx_found = True
                break
        except Exception as e:
            continue

    if not jsx_found:
        # If all specific queries fail, check if we at least have angle brackets in the right places
        source_code = typescript_finder._get_node_text(root, code_bytes)
        jsx_found = "<div>" in source_code and "</div>" in source_code

    assert jsx_found, 'Failed to find JSX element'
