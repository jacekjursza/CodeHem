# Create this file as d:\code\CodeHem\test_ts2.py
import logging
import sys
import os

from codehem.core.engine.ast_handler import ASTHandler
from codehem.core.engine.languages import get_parser, TS_LANGUAGE

# Use rich for potentially better AST printing, optional
try:
    import rich
    from rich.tree import Tree
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from tree_sitter import Language, Parser, Query, Node, QueryError

# --- Konfiguracja ---

# Sample TypeScript Code (skopiowany z test_ts.py)
# Upewnij się, że ten kod jest DOKŁADNIE taki sam jak ten, który powoduje problemy
ts_code = """
import { Component, OnInit } from '@angular/core';
import { UserService } from './user-service';

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
    userId: number = 0;
    private profile: UserProfile | null = null;
    readonly creationDate: Date = new Date();

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

// Example of potentially problematic code (e.g., for testing robustness)
// let x = { a: 1, b: }; // Syntax error
"""

# Zapytania do przetestowania (skopiuj/wklej/popraw te z lang_typescript/config.py)
# Użyj tego słownika do eksperymentowania z zapytaniami
queries_to_test = {
    "IMPORT_ORIGINAL_FAILING": """
(import_statement) @import_simple
(import_from_statement) @import_from """, # Oryginalne błędne zapytanie
    "IMPORT_ATTEMPT_1": """
(import_statement) @import_statement
(export_statement declaration: (import_statement)) @exported_import
    """, # Prostsze zapytanie - może wystarczy?
     "FUNCTION_ORIGINAL_FAILING": """
(function_definition name: (identifier) @function_name) @function_def
(decorated_definition definition: (function_definition name: (identifier) @function_name)) @decorated_function_def """, # Oryginalne błędne
    "FUNCTION_ATTEMPT_1": """
(function_declaration name: (identifier) @func_decl_name) @func_decl
(export_statement declaration: (function_declaration name: (identifier) @exported_func_decl_name)) @exported_func_decl
(lexical_declaration (variable_declarator name: (identifier) @arrow_func_name value: (arrow_function))) @arrow_func_lexical
(export_statement declaration: (lexical_declaration (variable_declarator name: (identifier) @exported_arrow_func_name value: (arrow_function)))) @exported_arrow_func_lexical
    """, # Zapytanie bazujące na typach z dokumentacji TS
    "CLASS_WORKING": """
(class_declaration name: (type_identifier) @class_name body: (class_body) @body) @class_def
(export_statement declaration: (class_declaration name: (type_identifier) @class_name body: (class_body) @body)) @class_def_exported
    """, # Prawdopodobnie działające
    "INTERFACE_WORKING": """
(interface_declaration name: (type_identifier) @interface_name body: (object_type) @interface_body) @interface_def
(export_statement declaration: (interface_declaration name: (type_identifier) @interface_name body: (object_type) @interface_body)) @interface_def_exported
    """, # Prawdopodobnie działające
     "METHOD_ATTEMPT_1": """
(method_definition name: (property_identifier) @method_name) @method_def
(method_definition name: (constructor)) @constructor_def
(method_definition kind: (get) name: (property_identifier) @getter_name) @getter_def
(method_definition kind: (set) name: (property_identifier) @setter_name) @setter_def
     """, # Zapytanie bazujące na typach z dokumentacji TS
     "PROPERTY_ATTEMPT_1": """
(public_field_definition name: (property_identifier) @prop_name) @prop_def
     """, # Uproszczone zapytanie dla pola publicznego (może wymagać rozszerzenia)
     "DECORATOR_ATTEMPT_1": """
(decorator) @decorator_node
     """,
}

# --- Konfiguracja Logowania ---
# Zwiększ poziom logowania dla tree_sitter, aby zobaczyć więcej informacji
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logging.getLogger('tree_sitter').setLevel(logging.DEBUG) # Debug dla samego tree-sitter
logger = logging.getLogger('ts_ast_debugger')
logger.setLevel(logging.DEBUG) # Debug dla naszego skryptu

# --- Funkcje Pomocnicze ---

def load_ts_language_dynamic() -> Language | None:
    """Próbuje załadować język z zainstalowanego pakietu."""
    try:
        import tree_sitter_typescript
        logger.info("Próba załadowania języka z zainstalowanego pakietu 'tree_sitter_typescript'...")
        # Gramatyka TSX jest często bardziej kompletna i kompatybilna wstecz
        if hasattr(tree_sitter_typescript, 'language_tsx'):
             logger.debug("Znaleziono language_tsx(), używam...")
             return tree_sitter_typescript.language_tsx()
        elif hasattr(tree_sitter_typescript, 'language_typescript'):
             logger.debug("Znaleziono language_typescript(), używam...")
             return tree_sitter_typescript.language_typescript()
        else:
             logger.error("Zainstalowany pakiet 'tree_sitter_typescript' nie posiada funkcji language_tsx ani language_typescript.")
             return None
    except ImportError:
        logger.error("Nie znaleziono pakietu 'tree_sitter_typescript'. Upewnij się, że jest zainstalowany (`pip install tree-sitter-typescript`).")
        return None
    except Exception as e:
        logger.error(f"Błąd podczas ładowania języka z pakietu: {e}", exc_info=True)
        return None

def traverse_and_print_ast(node: Node, indent_level: int = 0, field_name: str | None = None):
    """Rekurencyjnie drukuje strukturę AST."""
    indent = "  " * indent_level
    field_str = f"field={field_name}: " if field_name else ""
    try:
        # Pokaż fragment tekstu węzła dla kontekstu
        text_snippet = node.text.decode('utf8').split('\n')[0]
        text_snippet = (text_snippet[:60] + '...') if len(text_snippet) > 60 else text_snippet
    except Exception:
        text_snippet = "[Błąd dekodowania tekstu]"

    print(f"{indent}{field_str}{node.type} [{node.start_point} - {node.end_point}] '{text_snippet}'")

    # Rekurencyjnie przejdź przez dzieci
    for i in range(node.child_count):
        child = node.child(i)
        # Pobierz nazwę pola dla dziecka (jeśli istnieje)
        child_field_name = node.field_name_for_child(i)
        traverse_and_print_ast(child, indent_level + 1, child_field_name)

def build_rich_ast_tree(node: Node, field_name: str | None = None) -> Tree:
    """Buduje drzewo AST dla biblioteki rich."""
    field_str = f"[dim]field=[/dim][i]{field_name}[/i]: " if field_name else ""
    try:
        text_snippet = node.text.decode('utf8').split('\n')[0]
        text_snippet = (text_snippet[:60] + '...') if len(text_snippet) > 60 else text_snippet
    except Exception:
        text_snippet = "[Błąd dekodowania tekstu]"

    label = f"{field_str}[bold blue]{node.type}[/bold blue] [dim][{node.start_point} - {node.end_point}] '{text_snippet}'[/dim]"
    tree = Tree(label)

    for i in range(node.child_count):
        child = node.child(i)
        child_field_name = node.field_name_for_child(i)
        child_tree = build_rich_ast_tree(child, child_field_name)
        tree.add(child_tree)
    return tree

# --- Główna Logika Skryptu ---
if __name__ == "__main__":
    logger.info("--- Debugger AST TypeScript ---")

    # 1. Załaduj Język i Parser
    ts_lang = load_ts_language_dynamic()
    if not ts_lang:
        logger.critical("Nie udało się załadować języka TypeScript. Przerywam.")
        sys.exit(1)
    logger.info("Język TypeScript załadowany pomyślnie.")

    parser = get_parser('typescript')

    # 2. Sparsuj Kod
    logger.info("Parsowanie kodu TypeScript...")
    code_bytes = ts_code.encode('utf8')
    try:
        tree = parser.parse(code_bytes)
        root_node = tree.root_node
        logger.info("Kod sparsowany.")
    except Exception as e:
        logger.critical(f"Krytyczny błąd podczas parsowania: {e}", exc_info=True)
        sys.exit(1)

    # Sprawdź błędy składni
    if root_node.has_error:
        logger.warning("Wykryto błędy składni w kodzie! Struktura AST może być niekompletna lub nieprawidłowa.")
        # Można dodać logikę wyszukiwania węzłów ERROR
        # np. traverse_ast(root_node) i szukanie node.type == 'ERROR'

    # 3. Wyświetl Strukturę AST
    print("\n--- Struktura Drzewa Składni Abstrakcyjnej (AST) ---")
    if HAS_RICH:
        rich_tree = build_rich_ast_tree(root_node)
        rich.print(rich_tree)
    else:
        traverse_and_print_ast(root_node) # Wersja tekstowa, jeśli nie ma rich
    print("--- Koniec Struktury AST ---")


    # 4. Przetestuj Zapytania
    print("\n--- Testowanie Zapytań Tree-sitter ---")
    all_queries_valid = True
    for name, query_string in queries_to_test.items():
        print(f"\n--- Zapytanie: {name} ---")
        print(f"``` S-expression\n{query_string.strip()}\n```")
        is_valid = True
        try:
            query = Query(TS_LANGUAGE, query_string)
            captures = query.captures(root_node)
            captures = ASTHandler.process_captures(captures)
            print(f"Znaleziono {len(captures)} przechwyceń (captures):")
            if not captures:
                print("  (Brak dopasowań)")
            else:
                # Grupuj wyniki wg nazwy przechwycenia dla czytelności
                captures_by_name = {}
                for node, capture_name in captures:
                    if capture_name not in captures_by_name:
                        captures_by_name[capture_name] = []
                    captures_by_name[capture_name].append(node)

                for capture_name, nodes in captures_by_name.items():
                    print(f"  Przechwycenie: @{capture_name} ({len(nodes)}x)")
                    for i, node in enumerate(nodes):
                        node_text = node.text.decode('utf8').split('\n')[0][:60] # Snippet
                        print(f"    {i+1}. Typ: {node.type}, Zakres: [{node.start_point} - {node.end_point}], Tekst: '{node_text}... summarised'")

        except QueryError as qe:
            logger.error(f"Zapytanie '{name}' ZAWODZI z błędem QueryError: {qe}")
            if hasattr(qe, 'message'): print(f"  Komunikat błędu: {qe.message}")
            if hasattr(qe, 'error_type'): print(f'  Typ błędu: {qe.error_type}')
            if hasattr(qe, 'offset'): print(f'  Offset: {qe.offset}')
            if hasattr(qe, 'row'): print(f'  Wiersz: {qe.row}')
            if hasattr(qe, 'column'): print(f'  Kolumna: {qe.column}')
            is_valid = False
            all_queries_valid = False
        except Exception as e:
            logger.error(f"Zapytanie '{name}' ZAWODZI z nieoczekiwanym błędem: {e}", exc_info=True)
            is_valid = False
            all_queries_valid = False
        if is_valid:
             logger.info(f"Zapytanie '{name}' wykonane poprawnie (sprawdź wyniki).")

    print(f"\n--- Podsumowanie Testów Zapytań {'(Wszystkie OK!)' if all_queries_valid else '(WYSTĄPIŁY BŁĘDY!)'} ---")
    print("\n--- Skrypt Debugowania Zakończony ---")