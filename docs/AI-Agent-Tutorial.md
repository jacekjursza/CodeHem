# AI Agent Tutorial: Automated Code Refactoring with CodeHem

This comprehensive tutorial shows AI agents how to use CodeHem for syntax-aware code modifications with minimal context and maximum safety.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Step-by-Step Workflow](#step-by-step-workflow)
4. [Advanced Patterns](#advanced-patterns)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)

## Quick Start

### Installation
```bash
pip install codehem
```

### Basic Usage
```python
from codehem import CodeHem

# Initialize for specific language
hem = CodeHem("python")  # or "typescript", "javascript"

# Or auto-detect from code
code = """
class Calculator:
    def add(self, a, b):
        return a + b
"""
hem = CodeHem.from_raw_code(code)
```

## Core Concepts

### 1. XPath-like Queries
CodeHem uses XPath-like syntax to target specific code elements:

```python
# Target patterns:
"ClassName[class]"                    # Class
"ClassName.method_name[method]"       # Method in class
"function_name[function]"             # Standalone function
"ClassName.property_name[property]"   # Property in class
```

### 2. Hash-based Conflict Detection
Each code fragment has a hash to prevent conflicts:

```python
fragment, hash_value = hem.get_text_by_xpath(code, xpath, return_hash=True)
# Use hash_value when applying patches to ensure no conflicts
```

### 3. Atomic Patch Operations
All modifications are atomic and return structured results:

```python
result = hem.apply_patch(
    xpath="Calculator.add[method]",
    new_code="def add(self, a, b):\n    return a + b + 1",
    mode="replace",
    original_hash=hash_value,
    return_format="json"
)
# Returns: {"status": "ok", "lines_added": 1, "lines_removed": 1}
```

## Step-by-Step Workflow

### Step 1: Language Detection and Element Discovery

```python
from codehem import CodeHem

# Code to analyze
code = """
class DataProcessor:
    def __init__(self, config):
        self.config = config
    
    def process(self, data):
        # TODO: implement processing logic
        pass
    
    def validate(self, data):
        return len(data) > 0

def helper_function(x, y):
    return x * y
"""

# Auto-detect language and extract elements
hem = CodeHem.from_raw_code(code)
elements = hem.extract(code)

# Print discovered elements
for element in elements.classes:
    print(f"Class: {element.name}")
    for method in element.methods:
        print(f"  Method: {method.name}")

for func in elements.functions:
    print(f"Function: {func.name}")
```

### Step 2: Targeted Code Queries

```python
# Get specific element with hash for conflict detection
xpath = "DataProcessor.process[method]"
fragment, fragment_hash = hem.get_text_by_xpath(code, xpath, return_hash=True)

print(f"Current method:\n{fragment}")
print(f"Hash: {fragment_hash}")
```

### Step 3: Safe Code Modification

```python
# Generate new implementation
new_implementation = """def process(self, data):
    if not self.validate(data):
        raise ValueError("Invalid data")
    
    # Process each item
    results = []
    for item in data:
        processed = helper_function(item, self.config.multiplier)
        results.append(processed)
    
    return results"""

# Apply patch with conflict detection
result = hem.apply_patch(
    xpath=xpath,
    new_code=new_implementation,
    mode="replace",
    original_hash=fragment_hash,
    return_format="json"
)

if result["status"] == "ok":
    print(f"✅ Successfully modified method")
    print(f"Lines added: {result['lines_added']}")
    print(f"Lines removed: {result['lines_removed']}")
else:
    print(f"❌ Modification failed: {result.get('error', 'Unknown error')}")
```

### Step 4: Builder Helpers for New Code

```python
# Add new method using builder helper
result = hem.new_method(
    code,
    parent="DataProcessor",
    name="cleanup",
    args=["self"],
    body=[
        "self.config = None",
        "print('Cleanup completed')"
    ],
    decorators=[],
    return_format="json"
)

# Add new function
result = hem.new_function(
    code,
    name="utility_function",
    args=["param1", "param2"],
    body=[
        "result = param1 + param2",
        "return result * 2"
    ],
    return_format="json"
)
```

## Advanced Patterns

### 1. Workspace Operations for Large Codebases

```python
from codehem import CodeHem

# Open workspace for repository-level operations
workspace = CodeHem.open_workspace("/path/to/repo")

# Find elements across all files
matches = workspace.find(name="calculate", kind="method")
for file_path, xpath in matches:
    print(f"Found 'calculate' method in {file_path} at {xpath}")

# Apply patches to workspace
for file_path, xpath in matches:
    workspace.apply_patch(file_path, xpath, new_implementation)
```

### 2. TypeScript/JavaScript Support

```python
# TypeScript code
ts_code = """
interface User {
    id: number;
    name: string;
}

class UserService {
    async fetchUser(id: number): Promise<User | null> {
        const response = await fetch(`/api/users/${id}`);
        return response.ok ? response.json() : null;
    }
    
    private validateUser(user: User): boolean {
        return user.id > 0 && user.name.length > 0;
    }
}
"""

# Use TypeScript CodeHem instance
hem = CodeHem("typescript")
elements = hem.extract(ts_code)

# Modify TypeScript interface
new_interface = """interface User {
    id: number;
    name: string;
    email: string;
    createdAt: Date;
}"""

result = hem.apply_patch(
    xpath="User[interface]",
    new_code=new_interface,
    mode="replace",
    return_format="json"
)
```

### 3. Batch Operations with Error Recovery

```python
def safe_batch_modify(hem, code, modifications):
    """Apply multiple modifications with rollback on failure."""
    results = []
    current_code = code
    
    for xpath, new_code, mode in modifications:
        try:
            # Get current hash
            _, current_hash = hem.get_text_by_xpath(current_code, xpath, return_hash=True)
            
            # Apply modification
            result = hem.apply_patch(
                xpath=xpath,
                new_code=new_code,
                mode=mode,
                original_hash=current_hash,
                return_format="json"
            )
            
            if result["status"] == "ok":
                current_code = result["modified_code"]
                results.append(("success", xpath, result))
            else:
                results.append(("failed", xpath, result))
                break  # Stop on first failure
                
        except Exception as e:
            results.append(("error", xpath, str(e)))
            break
    
    return current_code, results

# Example usage
modifications = [
    ("Calculator.add[method]", "def add(self, a, b):\n    return a + b", "replace"),
    ("Calculator.subtract[method]", "def subtract(self, a, b):\n    return a - b", "replace"),
]

final_code, results = safe_batch_modify(hem, code, modifications)
```

## Error Handling

### Common Error Patterns

```python
from codehem.core.error_handling import CodeHemError

try:
    result = hem.apply_patch(xpath, new_code, mode="replace")
except CodeHemError as e:
    if "ConflictError" in str(e):
        # Code was modified by another process
        print("Conflict detected - refetch current code")
    elif "XPathError" in str(e):
        # Invalid XPath query
        print("Invalid XPath - check element exists")
    else:
        print(f"CodeHem error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Dry Run for Safety

```python
# Preview changes without applying them
result = hem.apply_patch(
    xpath=xpath,
    new_code=new_code,
    mode="replace",
    dry_run=True
)

print("Proposed changes:")
print(result["diff"])

# Apply only if changes look correct
if input("Apply changes? (y/n): ").lower() == 'y':
    final_result = hem.apply_patch(
        xpath=xpath,
        new_code=new_code,
        mode="replace",
        original_hash=fragment_hash
    )
```

## Best Practices

### 1. Always Use Hash Verification
```python
# ✅ Good - prevents conflicts
fragment, hash_val = hem.get_text_by_xpath(code, xpath, return_hash=True)
result = hem.apply_patch(xpath, new_code, mode="replace", original_hash=hash_val)

# ❌ Bad - risk of conflicts
result = hem.apply_patch(xpath, new_code, mode="replace")
```

### 2. Prefer Minimal Changes
```python
# ✅ Good - modify only the method body
xpath = "Calculator.add[method]"
new_body = "return a + b + 1"  # Just the changed logic

# ❌ Bad - unnecessary context
new_complete_method = """def add(self, a, b):
    return a + b + 1"""
```

### 3. Use Appropriate Modes
```python
# For replacing existing code
hem.apply_patch(xpath, new_code, mode="replace")

# For adding new methods/functions
hem.apply_patch(xpath, new_code, mode="append")

# For adding imports or setup code
hem.apply_patch(xpath, new_code, mode="prepend")
```

### 4. Structure JSON Responses
```python
# Always request JSON format for programmatic use
result = hem.apply_patch(
    xpath=xpath,
    new_code=new_code,
    mode="replace",
    return_format="json"  # Gets structured data
)

# Check status before proceeding
if result["status"] == "ok":
    # Process successful result
    lines_changed = result["lines_added"] + result["lines_removed"]
    print(f"Modified {lines_changed} lines")
else:
    # Handle error
    print(f"Error: {result.get('error')}")
```

### 5. Use Workspace for Large Projects
```python
# For single files
hem = CodeHem("python")
result = hem.extract(code)

# For entire repositories
workspace = CodeHem.open_workspace("/path/to/repo")
matches = workspace.find(name="target_function", kind="function")
```

## Integration Examples

### CI/CD Pipeline Integration
```python
import os
from codehem import CodeHem

def automated_refactor(repo_path, pattern, replacement):
    """Automated refactoring for CI/CD."""
    workspace = CodeHem.open_workspace(repo_path)
    
    # Find all matching patterns
    matches = workspace.find(name=pattern, kind="method")
    
    modified_files = []
    for file_path, xpath in matches:
        try:
            result = workspace.apply_patch(file_path, xpath, replacement)
            if result["status"] == "ok":
                modified_files.append(file_path)
        except Exception as e:
            print(f"Failed to modify {file_path}: {e}")
    
    return modified_files

# Usage in CI
if __name__ == "__main__":
    repo = os.environ.get("CI_PROJECT_DIR", ".")
    modified = automated_refactor(repo, "deprecated_method", "new_method_impl")
    print(f"Modified {len(modified)} files")
```

This tutorial provides AI agents with the knowledge needed to safely and effectively use CodeHem for automated code refactoring. The hash-based conflict detection and atomic operations ensure reliability even in concurrent environments.