# test_ts2.py
import logging
import sys
import os
from codehem.core.engine.ast_handler import ASTHandler
from codehem.core.engine.languages import get_parser, TS_LANGUAGE  # Używamy get_parser z CodeHem
from codehem.languages.lang_typescript.config import LANGUAGE_CONFIG, TS_PLACEHOLDERS
from codehem.models.enums import CodeElementType     # Import dla typów
TS_LANGUAGE_CODE = LANGUAGE_CONFIG.get('language_code', 'typescript')
# Wydobycie zapytań dla poszczególnych typów
QUERIES_FROM_CONFIG = {
    "IMPORT": TS_PLACEHOLDERS.get(CodeElementType.IMPORT, {}).get('tree_sitter_query'),
    "FUNCTION": TS_PLACEHOLDERS.get(CodeElementType.FUNCTION, {}).get('tree_sitter_query'),
    "INTERFACE": TS_PLACEHOLDERS.get(CodeElementType.INTERFACE, {}).get('tree_sitter_query'),
    "CLASS": TS_PLACEHOLDERS.get(CodeElementType.CLASS, {}).get('tree_sitter_query'),
    "METHOD": TS_PLACEHOLDERS.get(CodeElementType.METHOD, {}).get('tree_sitter_query'),
    "PROPERTY": TS_PLACEHOLDERS.get(CodeElementType.PROPERTY, {}).get('tree_sitter_query'),
    "DECORATOR": TS_PLACEHOLDERS.get(CodeElementType.DECORATOR, {}).get('tree_sitter_query'),
    "GETTER": TS_PLACEHOLDERS.get(CodeElementType.PROPERTY_GETTER, {}).get('tree_sitter_query', TS_PLACEHOLDERS.get(CodeElementType.METHOD, {}).get('tree_sitter_query')), # Getter może używać zapytania metody
    "SETTER": TS_PLACEHOLDERS.get(CodeElementType.PROPERTY_SETTER, {}).get('tree_sitter_query', TS_PLACEHOLDERS.get(CodeElementType.METHOD, {}).get('tree_sitter_query')), # Setter może używać zapytania metody
}
# Usuń None jeśli zapytanie nie istnieje
QUERIES_FROM_CONFIG = {k: v for k, v in QUERIES_FROM_CONFIG.items() if v}
print("--- Successfully loaded queries from config.py ---")
# print(QUERIES_FROM_CONFIG) # Opcjonalnie: odkomentuj, aby zobaczyć załadowane zapytania
CONFIG_LOADED = True


try:
    import rich
    from rich.tree import Tree
    from rich.syntax import Syntax
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from tree_sitter import Language, Parser, Query, Node, QueryError

# Ten sam kod testowy co poprzednio
ts_code = """
import { Component, OnInit } from '@angular/core';
import { UserService } from './user-service';
import * as React from 'react'; // Test importu namespace
import DefaultExport from 'some-module'; // Test importu domyślnego

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
    @AnotherDecorator() // Dodatkowy dekorator dla testu
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

# --- Konfiguracja Logowania ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logging.getLogger('tree_sitter').setLevel(logging.WARNING) # Zmniejszamy gadatliwość tree_sitter
logger = logging.getLogger('ts_ast_debugger')
logger.setLevel(logging.DEBUG)

# --- Funkcje Pomocnicze ---

def load_ts_language_dynamic() -> Language | None:
    """Próbuje załadować język z zainstalowanego pakietu."""
    try:
        import tree_sitter_typescript
        logger.info("Próba załadowania języka z zainstalowanego pakietu 'tree_sitter_typescript'...")
        # Sprawdzamy dostępność parsera TSX lub TS
        if hasattr(tree_sitter_typescript, 'language_tsx'):
            logger.debug('Znaleziono language_tsx(), używam...')
            return tree_sitter_typescript.language_tsx()
        elif hasattr(tree_sitter_typescript, 'language_typescript'):
            logger.debug('Znaleziono language_typescript(), używam...')
            return tree_sitter_typescript.language_typescript()
        else:
            logger.error("Zainstalowany pakiet 'tree_sitter_typescript' nie posiada funkcji language_tsx ani language_typescript.")
            return None
    except ImportError:
        logger.error("Nie znaleziono pakietu 'tree_sitter_typescript'. Upewnij się, że jest zainstalowany (`pip install tree-sitter-typescript`).")
        return None
    except Exception as e:
        logger.error(f'Błąd podczas ładowania języka z pakietu: {e}', exc_info=True)
        return None

def traverse_and_print_ast(node: Node, indent_level: int = 0, field_name: str | None = None):
    """Rekurencyjnie drukuje strukturę AST (wersja bez rich)."""
    indent = '  ' * indent_level
    field_str = f'field={field_name}: ' if field_name else ''
    try:
        # Bezpieczne dekodowanie i skracanie tekstu
        text_snippet = node.text.decode('utf8', errors='replace').split('\n')[0]
        text_snippet = text_snippet[:60] + '...' if len(text_snippet) > 60 else text_snippet
    except Exception:
        text_snippet = '[Błąd dekodowania tekstu]'
    print(f"{indent}{field_str}{node.type} [{node.start_point} - {node.end_point}] '{text_snippet}'")
    for i in range(node.child_count):
        child = node.child(i)
        child_field_name = node.field_name_for_child(i)
        traverse_and_print_ast(child, indent_level + 1, child_field_name)

def build_rich_ast_tree(node: Node, field_name: str | None = None) -> Tree:
    """Buduje drzewo AST dla biblioteki rich."""
    if not HAS_RICH: return None # Zwracamy None jeśli rich nie jest dostępny

    field_str = f'[dim]field=[/dim][i]{field_name}[/i]: ' if field_name else ''
    try:
        # Bezpieczne dekodowanie i skracanie tekstu
        text_snippet = node.text.decode('utf8', errors='replace').split('\n')[0]
        text_snippet = text_snippet[:60] + '...' if len(text_snippet) > 60 else text_snippet
    except Exception:
        text_snippet = '[Błąd dekodowania tekstu]'

    # Dodanie informacji o ID węzła może być pomocne w debugowaniu
    node_info = f"[dim](id={node.id})[/dim]"
    label = f"{field_str}[bold blue]{node.type}[/bold blue] {node_info} [dim][{node.start_point} - {node.end_point}] '{text_snippet}'[/dim]"
    tree = Tree(label)

    for i in range(node.child_count):
        child = node.child(i)
        child_field_name = node.field_name_for_child(i)
        child_tree = build_rich_ast_tree(child, child_field_name)
        if child_tree: # Upewniamy się, że rich jest dostępny
             tree.add(child_tree)
    return tree

# --- Główna Logika Skryptu ---
if __name__ == '__main__':
    logger.info('--- Debugger AST TypeScript ---')

    # --- Ładowanie Języka ---
    ts_lang = TS_LANGUAGE
    if not ts_lang:
        logger.critical('Nie udało się załadować języka TypeScript. Przerywam.')
        sys.exit(1)
    logger.info('Język TypeScript załadowany pomyślnie.')

    # --- Parsowanie Kodu ---
    try:
        parser = get_parser('typescript') # Używamy parsera z CodeHem
        if not parser:
             logger.critical("Nie udało się uzyskać parsera TypeScript z CodeHem. Przerywam.")
             sys.exit(1)
        logger.info('Parsowanie kodu TypeScript...')
        code_bytes = ts_code.encode('utf8')
        tree = parser.parse(code_bytes)
        root_node = tree.root_node
        logger.info('Kod sparsowany.')
        if root_node.has_error:
            logger.warning('Wykryto błędy składni w kodzie! Struktura AST może być niekompletna lub nieprawidłowa.')

    except Exception as e:
        logger.critical(f'Krytyczny błąd podczas parsowania: {e}', exc_info=True)
        sys.exit(1)

    # --- Drukowanie Drzewa AST ---
    print('\n--- Struktura Drzewa Składni Abstrakcyjnej (AST) ---')
    if HAS_RICH:
        rich_tree = build_rich_ast_tree(root_node)
        if rich_tree:
            rich.print(rich_tree)
        else:
            logger.warning("Biblioteka 'rich' nie jest zainstalowana. Drukowanie AST w trybie tekstowym.")
            traverse_and_print_ast(root_node)
    else:
        traverse_and_print_ast(root_node)
    print('--- Koniec Struktury AST ---')

    # --- Testowanie Zapytań ---
    print('\n--- Testowanie Zapytań Tree-sitter (z config.py jeśli załadowano) ---')
    all_queries_valid = True
    if not QUERIES_FROM_CONFIG:
         logger.warning("Brak zapytań do przetestowania (nie załadowano z configu ani nie zdefiniowano zastępczych).")
    else:
        for name, query_string in QUERIES_FROM_CONFIG.items():
            print(f'\n--- Zapytanie: {name} ---')
            if not query_string:
                print("  (Zapytanie puste lub nie załadowano)")
                continue

            if HAS_RICH:
                rich.print(Syntax(query_string, "scheme", theme="default", line_numbers=False))
            else:
                print(f'``` S-expression\n{query_string.strip()}\n```')

            is_valid = True
            try:
                query = Query(ts_lang, query_string) # Używamy załadowanego języka ts_lang
                # Używamy ASTHandler z CodeHem do przetwarzania wyników
                ast_handler = ASTHandler('typescript', parser, ts_lang)

                captures_raw = query.captures(root_node)
                captures = ast_handler.process_captures(captures_raw)

                print(f'Znaleziono {len(captures)} przechwyceń (captures):')
                if not captures:
                    print('  (Brak dopasowań)')
                else:
                    # Grupujemy wyniki po nazwie przechwycenia
                    captures_by_name = {}
                    for node, capture_name in captures:
                        if capture_name not in captures_by_name:
                            captures_by_name[capture_name] = []
                        captures_by_name[capture_name].append(node)

                    for capture_name, nodes in captures_by_name.items():
                        print(f'  Przechwycenie: @{capture_name} ({len(nodes)}x)')
                        for i, node in enumerate(nodes[:5]): # Drukuj tylko kilka pierwszych dla zwięzłości
                            try:
                                node_text = node.text.decode('utf8', errors='replace').split('\n')[0][:60]
                            except Exception:
                                node_text = "[Błąd dekodowania]"
                            print(f"    {i + 1}. Typ: {node.type}, Zakres: [{node.start_point} - {node.end_point}], Tekst: '{node_text}... summarised'")
                        if len(nodes) > 5:
                            print(f"    ... (i {len(nodes) - 5} więcej)")

            except QueryError as qe:
                logger.error(f"Zapytanie '{name}' ZAWODZI z błędem QueryError: {qe}")
                # Drukowanie szczegółów błędu QueryError
                if hasattr(qe, 'message'): print(f'  Komunikat błędu: {qe.message}')
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

    # --- Podsumowanie ---
    print(f"\n--- Podsumowanie Testów Zapytań {('(Wszystkie OK!)' if all_queries_valid else '(WYSTĄPIŁY BŁĘDY!)')} ---")
    print('\n--- Skrypt Debugowania Zakończony ---')