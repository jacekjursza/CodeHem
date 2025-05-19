# -*- coding: utf-8 -*-
"""
Manual Debugging Script for CodeHem TypeScript Functionality.
"""
import logging
import rich # For pretty printing
from codehem import CodeHem, CodeElementType # Import enums if needed for checks
import traceback

# --- Configuration ---
# Set logging level to DEBUG to see detailed logs from CodeHem components
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
# Optional: Quieten the tree_sitter logger if it's too verbose
# logging.getLogger('tree_sitter').setLevel(logging.INFO)

logger = logging.getLogger("test_ts_manual") # Logger for this script

# --- Sample TypeScript Code ---
# Includes imports, interface, class with decorator, constructor,
# properties, methods (sync/async), getter, setter, and standalone functions.
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
        logger.debug(`Attempting to load profile for ID: ${id}`); // Example of using logger
        try {
            this.profile = await this.userService.getUser(id);
            console.log('Profile loaded:', this.profile);
        } catch (error) {
            console.error('Failed to load profile', error);
            logger.error(`Error in loadProfile: ${error}`, exc_info=True); // Example error logging
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
             this.loadProfile(value); // Example calling another method
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

def run_typescript_debug():
    """Runs the debugging steps for TypeScript."""
    logger.info("--- Initializing CodeHem for TypeScript ---")
    hem = None # Initialize hem to None
    try:
        # Initialize CodeHem specifically for typescript
        hem = CodeHem('typescript')
        logger.info("CodeHem(typescript) instance created successfully.")
    except ValueError as e:
        logger.error(f"Failed to initialize CodeHem for 'typescript'. Is the language service registered? Error: {e}", exc_info=True)
        return # Stop if initialization fails
    except Exception as e:
        logger.error(f"An unexpected error occurred during CodeHem initialization: {e}", exc_info=True)
        return

    # --- 1. Test Full Extraction ---
    logger.info("\n--- STEP 1: Testing Full Extraction (hem.extract) ---")

    extracted_result = hem.extract(ts_code)
    logger.info(f"Extraction complete. Found {len(extracted_result.elements)} top-level elements.")

    print("\nExtracted Elements (using rich.print for readability):")
    rich.print(extracted_result) # Pretty-print the Pydantic model



    logger.info("\n--- Debugging Script Finished ---")

if __name__ == "__main__":
    run_typescript_debug()