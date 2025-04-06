import logging
import sys
from codehem.core.engine.languages import get_parser, LANGUAGES
from codehem.core.engine.ast_handler import ASTHandler
from tree_sitter import QueryError # Import specific error type

# Configure basic logging to see potential errors from ASTHandler
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("debug_import")

# Minimal code snippet
test_code = """
import os
import sys
from typing import List, Dict

class MySimpleClass:
    MY_VAR = 123 # Simple assignment
    MY_TYPED_VAR: int = 456 # Typed assignment

def my_func():
    pass
"""

# --- Queries to Debug ---

# Import query (from last attempt - separate captures)
import_query_str = """
(import_statement) @import_simple
(import_from_statement) @import_from
"""

# Static property query (from last attempt - simplified direct children)
static_prop_query_str = """
(class_definition
  body: (block >
    (assignment left: (identifier) @prop_name right: (_) @prop_value) @static_prop_assign
  )
)

(class_definition
  body: (block >
    (typed_assignment left: (identifier) @prop_name type: (_) @prop_type value: (_) @prop_value) @static_prop_assign_typed
  )
)
"""

# --- Execution ---

try:
    logger.info("Initializing Python parser and ASTHandler...")
    parser = get_parser('python')
    language = LANGUAGES.get('python')
    if not parser or not language:
        logger.error("Could not get parser or language for Python.")
        sys.exit(1)
    ast_handler = ASTHandler('python', parser, language)
    logger.info("Parsing test code...")
    root_node, code_bytes = ast_handler.parse(test_code)
    logger.info("Code parsed successfully.")

    # --- Test Import Query ---
    logger.info("\n--- Testing Import Query ---")
    logger.debug(f"Query:\n{import_query_str}")
    try:
        import_results = ast_handler.execute_query(import_query_str, root_node, code_bytes)
        logger.info(f"Import Query Results ({len(import_results)}):")
        if not import_results:
             print("  (No matches found)")
        for node, capture_name in import_results:
            print(f"  Capture: @{capture_name}")
            print(f"    Node Type: {node.type}")
            print(f"    Node Text: {ast_handler.get_node_text(node, code_bytes).strip()}")
            print(f"    Line Range: {node.start_point[0]+1} - {node.end_point[0]+1}")
            print("-" * 10)
    except QueryError as qe:
        logger.error(f"Import Query FAILED with QueryError: {qe}")
    except Exception as e:
        logger.error(f"Import Query FAILED with unexpected error: {e}", exc_info=True)

    # --- Test Static Property Query ---
    logger.info("\n--- Testing Static Property Query ---")
    logger.debug(f"Query:\n{static_prop_query_str}")
    try:
        static_prop_results = ast_handler.execute_query(static_prop_query_str, root_node, code_bytes)
        logger.info(f"Static Property Query Results ({len(static_prop_results)}):")
        if not static_prop_results:
             print("  (No matches found)")
        for node, capture_name in static_prop_results:
            # Try to extract specific parts based on capture names within the matched node
            prop_name_node = ast_handler.find_child_by_field_name(node, 'prop_name') # Assuming these captures exist inside the matched node
            prop_value_node = ast_handler.find_child_by_field_name(node, 'prop_value')
            prop_type_node = ast_handler.find_child_by_field_name(node, 'prop_type')

            print(f"  Capture: @{capture_name}")
            print(f"    Node Type: {node.type}")
            print(f"    Node Text: {ast_handler.get_node_text(node, code_bytes).strip()}")
            print(f"    Prop Name: {ast_handler.get_node_text(prop_name_node, code_bytes) if prop_name_node else 'N/A'}")
            print(f"    Prop Value: {ast_handler.get_node_text(prop_value_node, code_bytes) if prop_value_node else 'N/A'}")
            print(f"    Prop Type: {ast_handler.get_node_text(prop_type_node, code_bytes) if prop_type_node else 'N/A'}")
            print(f"    Line Range: {node.start_point[0]+1} - {node.end_point[0]+1}")
            print("-" * 10)
    except QueryError as qe:
        logger.error(f"Static Property Query FAILED with QueryError: {qe}")
        # Print the specific error details from QueryError if available
        print(f"  Error Type: {qe.error_type}")
        print(f"  Offset: {qe.offset}")
        print(f"  Row: {qe.row}")
        print(f"  Column: {qe.column}")
    except Exception as e:
        logger.error(f"Static Property Query FAILED with unexpected error: {e}", exc_info=True)

except Exception as e:
    logger.error(f"Script failed during setup: {e}", exc_info=True)