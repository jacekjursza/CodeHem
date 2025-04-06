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
    # Another simple assignment within expression statement
    MY_OTHER_VAR = 789

def my_func():
    pass
"""

# --- Queries to Debug ---

# Import query (from last attempt - separate captures)
import_query_str = """
(import_statement) @import_simple
(import_from_statement) @import_from
"""

# Static property query - ONLY capturing the class body block
static_prop_query_str = """
(class_definition
  body: (block) @class_block
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
        # The query now captures the block node with @class_block
        logger.info(f"Static Property Query Results (captures @class_block): {len(static_prop_results)}")

        if not static_prop_results:
             print("  (No class blocks found)")

        for block_node, capture_name in static_prop_results: # Should only capture @class_block
            if capture_name == 'class_block':
                print(
                    f"\n  Processing children of @class_block (Node Type: {block_node.type})"
                )
                print(
                    f"  Block Line Range: {block_node.start_point[0] + 1} - {block_node.end_point[0] + 1}"
                )
                print("-" * 15)

                # Iterate through direct children of the captured block node
                # Iterate through direct children of the captured block node
                for child_node in block_node.named_children:
                    print(f"    Child Node Type: {child_node.type}")
                    print(
                        f"    Child Node Text: {ast_handler.get_node_text(child_node, code_bytes).strip()}"
                    )

                    prop_name_text = "N/A"
                    prop_value_text = "N/A"
                    prop_type_text = "N/A"  # Domyślnie N/A
                    assignment_node = None  # The core assignment node

                    # Determine the actual assignment node
                    if child_node.type == "assignment":
                        assignment_node = child_node
                    elif (
                        child_node.type == "expression_statement"
                        and child_node.named_child_count == 1
                    ):
                        inner_node = child_node.named_child(0)
                        # Important: Check if the inner node is specifically 'assignment'
                        if inner_node.type == "assignment":
                            assignment_node = inner_node
                            print(
                                f"      (Assignment found within expression_statement)"
                            )
                        # If inner node is typed_assignment (less likely at class level based on logs, but good to check)
                        elif inner_node.type == "typed_assignment":
                            assignment_node = inner_node
                            print(
                                f"      (Typed_assignment found within expression_statement - less common case)"
                            )

                    # If we found a relevant assignment node, extract details
                    if assignment_node:
                        # --- REVISED LOGIC ---
                        left_node = assignment_node.child_by_field_name("left")
                        right_node = assignment_node.child_by_field_name(
                            "right"
                        )  # Value for class var assignment
                        type_node = assignment_node.child_by_field_name(
                            "type"
                        )  # Check for optional type field *on the assignment node*

                        # Extract Name
                        if left_node and left_node.type == "identifier":
                            prop_name_text = ast_handler.get_node_text(
                                left_node, code_bytes
                            )

                        # Extract Value (should be 'right' field for class-level assignment)
                        if right_node:
                            prop_value_text = ast_handler.get_node_text(
                                right_node, code_bytes
                            )
                        else:
                            # Sometimes value might be in 'value' field if it's unexpectedly parsed as typed_assignment? Less likely.
                            value_node_alt = assignment_node.child_by_field_name(
                                "value"
                            )
                            if value_node_alt:
                                prop_value_text = ast_handler.get_node_text(
                                    value_node_alt, code_bytes
                                )
                            else:
                                prop_value_text = "N/A (right field not found)"

                        # Extract Type ONLY if type_node was found directly on the assignment node
                        if type_node:
                            prop_type_text = ast_handler.get_node_text(
                                type_node, code_bytes
                            )
                            # prop_type_text will remain 'N/A' if type_node is None
                        # --- END REVISED LOGIC ---

                        print(f"      -> Identified as Static Property Candidate")
                        print(f"        Prop Name: {prop_name_text}")
                        print(f"        Prop Value: {prop_value_text}")
                        print(
                            f"        Prop Type: {prop_type_text}"
                        )  # <-- Powinno być 'int' dla MY_TYPED_VAR
                    else:
                        # Log nodes that are direct children but not assignments we process
                        print(f"      -> Node type '{child_node.type}' skipped.")
                    print("-" * 8) # Separator for children

    except QueryError as qe:
        logger.error(f"Static Property Query FAILED with QueryError: {qe}")
        # Print the specific error details from QueryError if available
        # Make sure QueryError object has these attributes if you access them
        if hasattr(qe, 'error_type'): print(f"  Error Type: {qe.error_type}")
        if hasattr(qe, 'offset'): print(f"  Offset: {qe.offset}")
        if hasattr(qe, 'row'): print(f"  Row: {qe.row}")
        if hasattr(qe, 'column'): print(f"  Column: {qe.column}")
    except Exception as e:
        logger.error(f"Static Property Query FAILED with unexpected error: {e}", exc_info=True)

except Exception as e:
    logger.error(f"Script failed during setup: {e}", exc_info=True)