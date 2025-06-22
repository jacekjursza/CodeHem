# Quick‑Start for LLMs

This guide shows the typical workflow for autonomous agents using CodeHem.

## Installation

```bash
# Install CodeHem
pip install codehem

# Or for CLI usage
pipx install codehem
```

## Basic Workflow

### 1. **Detect the language** of a file:

```bash
codehem detect path/to/file.py
```

### 2. **Query and patch** using JSON:

```json
{ "xpath": "Example.greet[method]", "new_code": "print('hi')" }
```

Send this payload to `CodeHem.apply_patch` and apply the result.

### 3. **Preview diffs from the CLI** before writing:

```bash
codehem patch path/to/file.py --xpath "Example.greet[method]" --file update.txt --dry-run
```

### 4. **Commit** the updated file when the patch succeeds.

## Python API Example

```python
from codehem import CodeHem

# Initialize for specific language
hem = CodeHem("python")

# Extract elements
result = hem.extract(code)

# Apply patch with conflict detection
fragment, hash_val = hem.get_text_by_xpath(code, xpath, return_hash=True)
result = hem.apply_patch(
    xpath=xpath,
    new_code=new_implementation,
    mode="replace",
    original_hash=hash_val,
    return_format="json"
)
```

For more detailed examples, see the [AI Agent Tutorial](AI-Agent-Tutorial.md).
