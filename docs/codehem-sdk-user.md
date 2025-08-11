# CodeHem Python SDK – User Guide

This guide shows how to use CodeHem as a Python library (installed via pip) to detect language, extract code structure, query elements with XPath-like paths, and apply safe patches.

## Install
- Recommended: Python 3.9+ (works with >=3.7)
- Install: `pip install CodeHem`

## Quick Start
```python
from codehem import CodeHem, CodeElementType

# Load from a file (language inferred from extension)
hem = CodeHem.from_file_path("app.py")
source = CodeHem.load_file("app.py")

# Extract top-level elements (classes, functions, imports)
elements = hem.extract(source)
print([(e.type.value, e.name) for e in elements.elements])

# Find a specific element via XPath-like path
cls = CodeHem.filter(elements, "MyClass")
method = CodeHem.filter(elements, "MyClass.do_work")
```

## XPath Essentials
- Paths refer to the file root implicitly; `FILE.` prefix is optional in most helpers.
- Examples:
  - Class: `MyClass`
  - Method: `MyClass.do_work`
  - Property getter/setter: `MyClass.value[property_getter]`, `MyClass.value[property_setter]`
  - Parts: `MyClass.do_work[def]` (signature+body), `MyClass.do_work[body]`

```python
# Get code text for a selected element (optionally return its hash)
text = hem.get_text_by_xpath(source, "FILE.MyClass.do_work[body]")
text, frag_hash = hem.get_text_by_xpath(source, "MyClass.do_work", return_hash=True)
```

## Safe Patching with Conflict Detection
```python
# Compute current fragment hash (for optimistic concurrency)
original_hash = hem.get_element_hash(source, "FILE.MyClass.do_work")

# New body (minimal example)
new_body = """
    def do_work(self):
        print("updated")
        return 0
"""

# Preview diff without writing
diff = hem.apply_patch(
    source,
    xpath="MyClass.do_work",
    new_code=new_body,
    mode="replace",     # replace | append | prepend
    original_hash=original_hash,
    dry_run=True,
)
print(diff)

# Apply and write back to the file
patched = hem.apply_patch(source, "MyClass.do_work", new_body, original_hash=original_hash)
with open("app.py", "w", encoding="utf-8") as f:
    f.write(patched["code"] if isinstance(patched, dict) else patched)
```

Common errors to catch:
```python
from codehem.core.error_handling import ElementNotFoundError, WriteConflictError
try:
    hem.apply_patch(source, "MyClass.do_work", new_body, original_hash=original_hash)
except ElementNotFoundError:
    print("XPath didn't match any element")
except WriteConflictError as e:
    print("Content changed; recompute hash and retry")
```

## Batch Processing a Directory
```python
from pathlib import Path
from codehem import CodeHem

for path in Path("src").rglob("*.py"):
    code = path.read_text(encoding="utf-8")
    hem = CodeHem.from_file_path(str(path))
    elements = hem.extract(code)
    # Example: list methods per class
    for el in elements.elements:
        if el.type.value == "class":
            methods = [c for c in el.children if c.type.value == "method"]
            print(path.name, el.name, [m.name for m in methods])
```

## Tips & Capabilities
- Languages: `CodeHem.supported_languages()` returns supported codes (e.g., `python`, `typescript`, `javascript`).
- Reuse the same `CodeHem(language)` instance across files for best performance.
- Results are Pydantic models; to JSON use `model_dump()` and exclude tree-sitter internals if present.
- For quick one-offs, try the CLI: `codehem extract file.py --summary`.

## JSON Output Structure
SDK methods return Pydantic models, but you can convert to JSON easily:

```python
payload = {
  "elements": [e.model_dump(exclude={"range": {"node"}}) for e in elements.elements]
}
```

Typical `CodeElement` fields:
- `type`: element kind (`class`, `function`, `method`, `property`, `import`, ...)
- `name`: element identifier (e.g., `Calculator`, `add`)
- `content`: exact source slice for the element (string)
- `range`: `{ start_line, start_column, end_line, end_column }` (1-based lines)
- `parent_name`: parent container (e.g., class name for methods)
- `value_type`: optional type hint (if available)
- `additional_data`: language-specific extras
- `children`: nested `CodeElement`s (e.g., methods under a class)

Example (trimmed):
```json
{
  "elements": [
    { "type": "function", "name": "util", "range": {"start_line": 1, "end_line": 3} },
    { "type": "class", "name": "Calculator", "range": {"start_line": 5, "end_line": 20},
      "children": [
        { "type": "method", "name": "add", "parent_name": "Calculator",
          "range": {"start_line": 7, "end_line": 9} },
        { "type": "property_getter", "name": "value", "parent_name": "Calculator" }
      ]
    }
  ]
}
```

CLI `extract` (recursive) emits either NDJSON (one object per line) or an aggregate object:
```json
{ "files": [
  { "path": "src/app.py", "summary": {"classes": 1, "functions": 2, "methods": 3} },
  { "path": "src/util.ts", "elements": [ { "type": "function", "name": "fmt" } ] }
]}
```

## Troubleshooting
- Unsupported files raise `ValueError` on language detection (`from_file_path` / `from_raw_code`).
- If an XPath does not match, `get_text_by_xpath` returns `None`; `apply_patch` raises `ElementNotFoundError`.
- Hash mismatches in `apply_patch` raise `WriteConflictError` when the fragment changed since hashing.

## FAQ

- Performance tips:
  - Reuse a `CodeHem("python")` or `CodeHem("typescript")` instance across multiple files to amortize parser setup.
  - For large trees, prefer the CLI `extract --recursive --summary` to pre-compute counts and shortlist targets.
  - Suppress verbose logs by default; enable debug only for diagnostics.
  - When scanning a repository programmatically, consider `CodeHem.open_workspace(root)` to index once and query many times.

- Common XPath patterns (TypeScript/JavaScript):
  - Class method: `MyClass.compute` or `MyClass.compute[method]`
  - Getter/setter (may normalize as `method`): `MyClass.value[property_getter]`, `MyClass.value[property_setter]`
  - Interface: `IUser[interface]`
  - Type alias: `Result[type_alias]`
  - Enum: `Status[enum]`

## TypeScript/JavaScript Example (via Python SDK)

```python
from codehem import CodeHem

code_ts = """
export interface IUser { id: string; name: string }
export class Greeter {
  greet(name: string) { return `Hello, ${name}` }
}
export function fmt(x: number): string { return `${x}` }
"""

hem = CodeHem("typescript")  # also handles JavaScript
elements = hem.extract(code_ts)

classes = [e for e in elements.elements if e.type.value == "class"]
funcs = [e for e in elements.elements if e.type.value == "function"]
interfaces = [e for e in elements.elements if e.type.value == "interface"]
print([c.name for c in classes], [f.name for f in funcs], [i.name for i in interfaces])

# XPath examples
print(hem.get_text_by_xpath(code_ts, "Greeter.greet[body]"))
```

## Minimal JSON Schema (informal)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://codehem.dev/schemas/elements.json",
  "title": "CodeHem Elements Payload",
  "type": "object",
  "properties": {
    "elements": {
      "type": "array",
      "items": { "$ref": "#/$defs/CodeElement" }
    },
    "files": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "path": { "type": "string" },
          "elements": { "type": "array", "items": { "$ref": "#/$defs/CodeElement" } },
          "summary": {
            "type": "object",
            "properties": {
              "classes": { "type": "integer" },
              "functions": { "type": "integer" },
              "methods": { "type": "integer" }
            },
            "additionalProperties": false
          }
        },
        "required": ["path"],
        "additionalProperties": true
      }
    }
  },
  "$defs": {
    "Range": {
      "type": "object",
      "properties": {
        "start_line": { "type": "integer" },
        "start_column": { "type": ["integer", "null"] },
        "end_line": { "type": "integer" },
        "end_column": { "type": ["integer", "null"] }
      },
      "additionalProperties": true
    },
    "CodeElement": {
      "type": "object",
      "properties": {
        "type": { "type": "string" },
        "name": { "type": "string" },
        "content": { "type": "string" },
        "range": { "$ref": "#/$defs/Range" },
        "parent_name": { "type": ["string", "null"] },
        "value_type": { "type": ["string", "null"] },
        "additional_data": { "type": "object" },
        "children": { "type": "array", "items": { "$ref": "#/$defs/CodeElement" } }
      },
      "required": ["type", "name"],
      "additionalProperties": true
    }
  },
  "additionalProperties": true
}
```
