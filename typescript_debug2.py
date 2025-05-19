# test_ts2.py
import logging
import sys
from codehem.core.engine.ast_handler import ASTHandler
from codehem.core.engine.languages import (
    get_parser,
    TS_LANGUAGE,
)  # Using get_parser from CodeHem
from codehem.languages.lang_typescript.config import LANGUAGE_CONFIG, TS_PLACEHOLDERS
from codehem.models.enums import CodeElementType  # Import for types
from tree_sitter import Language, Query, Node, QueryError

TS_LANGUAGE_CODE = LANGUAGE_CONFIG.get("language_code", "typescript")
# Extract queries for each element type
QUERIES_FROM_CONFIG = {
    "IMPORT": TS_PLACEHOLDERS.get(CodeElementType.IMPORT, {}).get("tree_sitter_query"),
    "FUNCTION": TS_PLACEHOLDERS.get(CodeElementType.FUNCTION, {}).get(
        "tree_sitter_query"
    ),
    "INTERFACE": TS_PLACEHOLDERS.get(CodeElementType.INTERFACE, {}).get(
        "tree_sitter_query"
    ),
    "CLASS": TS_PLACEHOLDERS.get(CodeElementType.CLASS, {}).get("tree_sitter_query"),
    "METHOD": TS_PLACEHOLDERS.get(CodeElementType.METHOD, {}).get("tree_sitter_query"),
    "PROPERTY": TS_PLACEHOLDERS.get(CodeElementType.PROPERTY, {}).get(
        "tree_sitter_query"
    ),
    "DECORATOR": TS_PLACEHOLDERS.get(CodeElementType.DECORATOR, {}).get(
        "tree_sitter_query"
    ),
    "GETTER": TS_PLACEHOLDERS.get(CodeElementType.PROPERTY_GETTER, {}).get(
        "tree_sitter_query",
        TS_PLACEHOLDERS.get(CodeElementType.METHOD, {}).get("tree_sitter_query"),
    ),  # Getter may use the method query
    "SETTER": TS_PLACEHOLDERS.get(CodeElementType.PROPERTY_SETTER, {}).get(
        "tree_sitter_query",
        TS_PLACEHOLDERS.get(CodeElementType.METHOD, {}).get("tree_sitter_query"),
    ),  # Setter may use the method query
}
# Remove None entries if a query does not exist
QUERIES_FROM_CONFIG = {k: v for k, v in QUERIES_FROM_CONFIG.items() if v}
print("--- Successfully loaded queries from config.py ---")
# print(QUERIES_FROM_CONFIG)  # Optional: uncomment to display loaded queries
CONFIG_LOADED = True


try:
    import rich
    from rich.tree import Tree
    from rich.syntax import Syntax

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# Ten sam kod testowy co poprzednio
ts_code = """
import { Component, OnInit } from '@angular/core';
import { UserService } from './user-service';
import * as React from 'react'; // Namespace import test
import DefaultExport from 'some-module'; // Default import test

// Interface Definition
interface UserProfile {
    id: number;
    name: string;
    email?: string; // Optional property
}

/**
 * Represents the User Component.
 */
@Component({ selector: 'app-user' })
export class UserComponent implements OnInit {
    // Properties (Fields)
    userId: number = 0; // Property (field)
    private profile: UserProfile | null = null;
    readonly creationDate: Date = new Date();

    // Static property
    static componentType: string = 'UserInterface';

    // Constructor Method
    constructor(private userService: UserService) {
        console.log("UserComponent constructor called.");
    }

    // Standard Method (Lifecycle Hook)
    ngOnInit(): void {
        this.loadProfile(this.userId);
        console.log(`Component initialized for user ${this.userId}`);
    }

    // Async Method Definition
    @AnotherDecorator() // Additional decorator for testing
    async loadProfile(id: number): Promise<void> {
        // logger.debug(`Attempting to load profile for ID: ${id}`); // Python logger won't work here easily
        console.log(`Attempting to load profile for ID: ${id}`);
        try {
            // Fake await for testing structure
            // this.profile = await this.userService.getUser(id);
            this.profile = { id: id, name: 'Test User' }; // Simulate loading
            await new Promise(resolve => setTimeout(resolve, 10)); // Simulate async
            console.log('Profile loaded:', this.profile);
        } catch (error) {
            console.error('Failed to load profile', error);
            // logger.error(`Error in loadProfile: ${error}`, exc_info=True);
        }
    }

    // Getter Property
    get displayName(): string {
        return this.profile?.name ?? 'Guest';
    }

    // Setter Property
    set userIdentifier(value: number) {
         if (value > 0) {
             this.userId = value;
             // this.loadProfile(value); // Example calling another method
             console.log(`Set userId to ${value}, would call loadProfile`);
         } else {
             console.warn("Attempted to set invalid userIdentifier:", value);
         }
    }

    // Another simple method
    public clearProfile(): void {
        this.profile = null;
    }
}

// Standalone Arrow Function
const helperFunction = (input: string): string => {
    if (!input) return "Default";
    return `Helper processed: ${input.toUpperCase()}`;
};

// Standard Standalone Function
function anotherHelper(count: number = 1): void {
    for(let i = 0; i < count; i++) {
        console.log(`Another helper called (iteration ${i+1})`);
    }
}

// Example Enum
export enum Status {
    Pending,
    Active,
    Inactive
}

// Example Type Alias
type UserID = number | string;
"""

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logging.getLogger("tree_sitter").setLevel(
    logging.WARNING
)  # Reduce tree_sitter verbosity
logger = logging.getLogger("ts_ast_debugger")
logger.setLevel(logging.DEBUG)

# --- Helper Functions ---


def load_ts_language_dynamic() -> Language | None:
    """Attempt to load the language from an installed package."""
    try:
        import tree_sitter_typescript

        logger.info(
            "Trying to load language from installed package 'tree_sitter_typescript'..."
        )
        # Check for the TSX or TS parser
        if hasattr(tree_sitter_typescript, "language_tsx"):
            logger.debug("Found language_tsx(), using it...")
            return tree_sitter_typescript.language_tsx()
        elif hasattr(tree_sitter_typescript, "language_typescript"):
            logger.debug("Found language_typescript(), using it...")
            return tree_sitter_typescript.language_typescript()
        else:
            logger.error(
                "Installed package 'tree_sitter_typescript' lacks language_tsx and language_typescript functions."
            )
            return None
    except ImportError:
        logger.error(
            "Package 'tree_sitter_typescript' not found. Ensure it is installed (`pip install tree-sitter-typescript`)."
        )
        return None
    except Exception as e:
        logger.error(f"Error while loading language from package: {e}", exc_info=True)
        return None


def traverse_and_print_ast(
    node: Node, indent_level: int = 0, field_name: str | None = None
):
    """Recursively print the AST structure (without rich)."""
    indent = "  " * indent_level
    field_str = f"field={field_name}: " if field_name else ""
    try:
        # Safely decode and truncate text
        text_snippet = node.text.decode("utf8", errors="replace").split("\n")[0]
        text_snippet = (
            text_snippet[:60] + "..." if len(text_snippet) > 60 else text_snippet
        )
    except Exception:
        text_snippet = "[Text decode error]"
    print(
        f"{indent}{field_str}{node.type} [{node.start_point} - {node.end_point}] '{text_snippet}'"
    )
    for i in range(node.child_count):
        child = node.child(i)
        child_field_name = node.field_name_for_child(i)
        traverse_and_print_ast(child, indent_level + 1, child_field_name)


def build_rich_ast_tree(node: Node, field_name: str | None = None) -> Tree:
    """Build an AST tree for the rich library."""
    if not HAS_RICH:
        return None  # Return None if rich is unavailable

    field_str = f"[dim]field=[/dim][i]{field_name}[/i]: " if field_name else ""
    try:
        # Safely decode and truncate text
        text_snippet = node.text.decode("utf8", errors="replace").split("\n")[0]
        text_snippet = (
            text_snippet[:60] + "..." if len(text_snippet) > 60 else text_snippet
        )
    except Exception:
        text_snippet = "[Text decode error]"

    # Adding node ID information may help with debugging
    node_info = f"[dim](id={node.id})[/dim]"
    label = f"{field_str}[bold blue]{node.type}[/bold blue] {node_info} [dim][{node.start_point} - {node.end_point}] '{text_snippet}'[/dim]"
    tree = Tree(label)

    for i in range(node.child_count):
        child = node.child(i)
        child_field_name = node.field_name_for_child(i)
        child_tree = build_rich_ast_tree(child, child_field_name)
        if child_tree:  # Ensure rich is available
            tree.add(child_tree)
    return tree


# --- Main Script Logic ---
if __name__ == "__main__":
    logger.info("--- Debugger AST TypeScript ---")

    # --- Loading Language ---
    ts_lang = TS_LANGUAGE
    if not ts_lang:
        logger.critical("Failed to load the TypeScript language. Aborting.")
        sys.exit(1)
    logger.info("TypeScript language loaded successfully.")

    # --- Parsing Code ---
    try:
        parser = get_parser("typescript")  # Using CodeHem's parser
        if not parser:
            logger.critical(
                "Failed to obtain the TypeScript parser from CodeHem. Aborting."
            )
            sys.exit(1)
        logger.info("Parsing TypeScript code...")
        code_bytes = ts_code.encode("utf8")
        tree = parser.parse(code_bytes)
        root_node = tree.root_node
        logger.info("Code parsed.")
        if root_node.has_error:
            logger.warning(
                "Syntax errors detected! The AST structure may be incomplete or invalid."
            )

    except Exception as e:
        logger.critical(f"Critical error while parsing: {e}", exc_info=True)
        sys.exit(1)

    # --- Printing the AST Tree ---
    print("\n--- Abstract Syntax Tree (AST) structure ---")
    if HAS_RICH:
        rich_tree = build_rich_ast_tree(root_node)
        if rich_tree:
            rich.print(rich_tree)
        else:
            logger.warning(
                "The 'rich' library is not installed. Printing AST in text mode."
            )
            traverse_and_print_ast(root_node)
    else:
        traverse_and_print_ast(root_node)
    print("--- End of AST structure ---")

    # --- Testing Queries ---
    print("\n--- Testing Tree-sitter queries (from config.py if loaded) ---")
    all_queries_valid = True
    if not QUERIES_FROM_CONFIG:
        logger.warning("No queries to test (none loaded from config or placeholders).")
    else:
        for name, query_string in QUERIES_FROM_CONFIG.items():
            print(f"\n--- Query: {name} ---")
            if not query_string:
                print("  (Query empty or not loaded)")
                continue

            if HAS_RICH:
                rich.print(
                    Syntax(query_string, "scheme", theme="default", line_numbers=False)
                )
            else:
                print(f"``` S-expression\n{query_string.strip()}\n```")

            is_valid = True
            try:
                query = Query(ts_lang, query_string)  # Using the loaded ts_lang
                # Use ASTHandler from CodeHem to process results
                ast_handler = ASTHandler("typescript", parser, ts_lang)

                captures_raw = query.captures(root_node)
                captures = ast_handler.process_captures(captures_raw)

                print(f"Found {len(captures)} captures:")
                if not captures:
                    print("  (No matches)")
                else:
                    # Group results by capture name
                    captures_by_name = {}
                    for node, capture_name in captures:
                        if capture_name not in captures_by_name:
                            captures_by_name[capture_name] = []
                        captures_by_name[capture_name].append(node)

                    for capture_name, nodes in captures_by_name.items():
                        print(f"  Capture: @{capture_name} ({len(nodes)}x)")
                        for i, node in enumerate(
                            nodes[:5]
                        ):  # Print only a few for brevity
                            try:
                                node_text = node.text.decode(
                                    "utf8", errors="replace"
                                ).split("\n")[0][:60]
                            except Exception:
                                node_text = "[Decode error]"
                            print(
                                f"    {i + 1}. Type: {node.type}, Range: [{node.start_point} - {node.end_point}], Text: '{node_text}... summarised'"
                            )
                        if len(nodes) > 5:
                            print(f"    ... (and {len(nodes) - 5} more)")

            except QueryError as qe:
                logger.error(f"Query '{name}' FAILED with QueryError: {qe}")
                # Print QueryError details
                if hasattr(qe, "message"):
                    print(f"  Error message: {qe.message}")
                if hasattr(qe, "error_type"):
                    print(f"  Error type: {qe.error_type}")
                if hasattr(qe, "offset"):
                    print(f"  Offset: {qe.offset}")
                if hasattr(qe, "row"):
                    print(f"  Row: {qe.row}")
                if hasattr(qe, "column"):
                    print(f"  Column: {qe.column}")
                is_valid = False
                all_queries_valid = False
            except Exception as e:
                logger.error(
                    f"Query '{name}' FAILED with unexpected error: {e}", exc_info=True
                )
                is_valid = False
                all_queries_valid = False

            if is_valid:
                logger.info(f"Query '{name}' executed successfully (check results).")

    # --- Summary ---
    print(
        f"\n--- Query Tests Summary {('(ALL OK!)' if all_queries_valid else '(ERRORS OCCURRED!)')} ---"
    )
    print("\n--- Debug script finished ---")
