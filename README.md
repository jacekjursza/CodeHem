# CodeHem

> **Syntax‑aware, language‑agnostic refactoring engine designed for AI agents and LLM workflows.**

CodeHem lets tools and autonomous agents **query**, **patch** and **refactor** codebases using minimal context. It understands the Abstract Syntax Tree (AST) of each supported language and guarantees that generated changes stay syntactically valid.

---

## Why CodeHem?

| Traditional script                  | **CodeHem**                                                        |
| ----------------------------------- | ------------------------------------------------------------------ |
| Greps text & hopes for the best     | Parses real AST with [tree‑sitter](https://tree-sitter.github.io/) |
| Prints whole file to change 3 lines | Generates **minimal diffs / JSON patches**                         |
| Tightly coupled to one language     | **Plugin architecture** – drop‑in support for new languages        |
| Risky concurrent writes             | Atomic, hash‑guarded `apply_patch()` with file‑locks               |

---

## 🔑 Key Features

* **Uniform XPath‑like queries** – `"MyClass.reset[method]"` works the same in Python & TypeScript.
* **Patch API** – `apply_patch()` replaces / prepends / appends code and returns a JSON diff.
* **Builder helpers** – generate methods, classes or functions from structured data instead of raw strings.
* **Workspace indexing** – load a repo once, then search elements in O(1).
* **LRU cache & lazy loading** – lightning‑fast repeated calls, perfect for iterative agent loops.
* **Thread‑safe writes** – file‑level locks + hash check → no silent clobbering.
* **Plugin system via entry‑points** – ship a new language as `pip install codehem‑lang‑java`.
* **CLI tooling** – detect language, preview diffs, apply patches from the shell.

---

## Supported Languages

| Language                                    | Notes                |
| ------------------------------------------- | -------------------- |
| **Python**                                  | full support         |
| **JavaScript** / **TypeScript** (incl. TSX) | JS reuses TS runtime |
| *(More coming via plugins – e.g. Java, Go)* |                      |

---

## Installation

```bash
pip install codehem        # or pipx install codehem
```

Optional plugins install automatically:

```bash
pip install codehem‑lang‑java   # hypothetical future plugin
```

---

## Quick‑start (Python <‑> agent)

```python
from codehem import CodeHem

code = """
class Example:
    def greet(self):
        print("Hello")
"""

hem = CodeHem("python")

# 1. Query element & its hash
xpath = "Example.greet[method]"
fragment, frag_hash = hem.get_text_by_xpath(code, xpath, return_hash=True)

# 2. LLM edits `fragment`… then sends back only the new body
new_body = [
    "print(\"Hello, World!\")",
    "return 'done'"
]

result = hem.apply_patch(
    xpath=xpath,
    new_code="\n".join(new_body),
    mode="replace",
    original_hash=frag_hash,
    return_format="json"
)
print(result)
```

Output (truncated):

```json
{ "status": "ok", "lines_added": 2, "lines_removed": 1 }
```

The **full file never left runtime memory** – ideal for token‑budgeted agents.

### Workspace example
```python
ws = CodeHem.open_workspace("/path/to/repo")
file, xp = ws.find(name="calculate", kind="function")
ws.apply_patch(file, xp, "def calculate(x):\n    return x * 2\n")
```

### Builder helpers

Generate new functions or classes from structured data:

```python
result = hem.new_function(
    code,
    name="run",
    args=["config"],
    body=["print(config)", "return True"],
    return_format="json",
)
``` 

---

## CLI highlights

```bash
# Detect language & list top‑level elements
codehem detect src/example.py

# Apply patch file to a given XPath (dry‑run)
codehem patch --file fix.diff --xpath "MyClass.calc[method]" --dry-run
```

Run `codehem --help` for the full CLI.

See [docs/QuickStart-LLM](docs/QuickStart-LLM.md) for a JSON-driven workflow.

---

## Extending with a new language

Create a plugin package declaring an entry‑point:

```toml
[project.entry-points."codehem.languages"]
java = "codehem_lang_java:JavaLanguageService"
```

Provide:

* `JavaLanguageService` (specifies file extensions, patterns)
* formatter & manipulators (often subclass `BraceFormatter` / `AbstractBlockManipulator`)

Start with the **cookiecutter template**:

```
pipx cookiecutter gh:codehem/codehem-lang-template
```

Full guide: [docs/Developer‑Guide](docs/Developer-Guide.md).

---

## Contributing

Bugs, ideas, PRs – all welcome!  Run the test‑suite with `pytest -xv`.

---

## License

CodeHem is distributed under the MIT License. See `LICENSE` for details.
