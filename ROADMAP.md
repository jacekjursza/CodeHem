# Roadmap → CodeHem 1.0 (**context: AI agents**)

> CI/testing environment already exists
> no production users → API can change without migrations

---

## Sprint 1 — Stabilization and clear API

### Tasks

* Remove all `print()` statements; keep only logs (`logger.debug`/`info`).
* Simplify `get_language_service` – drop the Python special case for a unified path.
* Standardize missing results

  * `find_by_xpath` returns `None` (not `(0,0)`).
  * `get_text_by_xpath` already returns `None` – keep as is.
* Default log level `WARNING`; CLI flag `--debug` switches to `DEBUG`.
* Regression tests for the above.

### Rationale

Without a clean, predictable API later features (cache, patch API) would introduce chaos.

---

## Sprint 2 — Cache + Lazy Loading + Profiling

### Tasks

* LRU-cache the AST and extraction result (`maxsize=128`, key = sha1(code)).
* Cache `(code_hash, xpath)` in `find_by_xpath`.
* Replace extractor lists/dicts with `@cached_property`; instances created on first use.
* Profile cold / warm run (10k LOC file) – goal ≥ 3× speed‑up on second run.

### Rationale

Agents will repeatedly query the same files – no cache wastes tokens and CPU.

---

## Sprint 3 — Plug‑in architecture for languages

### Tasks

* Provide entry-points `codehem.languages` + loader `importlib.metadata.entry_points`.
* Alias `'javascript'` → `TypeScriptLanguageService`.
* Add a simple `JavaScriptLanguageDetector` (regexes for `function`, `=>`, `export`, `var/let/const`).
* Create cookie-cutter `codehem-lang-template` (service, formatter, tests).

### Rationale

A necessary step so that future plug‑ins (e.g. Java, Go) can be installed separately and work without changes to the core.

---

## Sprint 4 — DRY: formatter + manipulator

### Tasks

* Create `IndentFormatter` (indent‑based languages) and `BraceFormatter` (brace‑based).

  * Move common helpers (`_fix_spacing`, `apply_indentation`) to the base class.
* Create `AbstractBlockManipulator` with universal insertion logic; Python/TS only provide the block token (`:` vs `{`).
* Descriptor-as-data

  * JSON/TOML configuration with node patterns instead of duplicating extractor classes.

### Rationale

Minimize duplication before adding more languages; reduce the editing surface for AI patches.

---

## Sprint 5 — Patch API (v1) — “minimal-diff”

### Tasks

* `get_element_hash(xpath)` – sha256 of the selected fragment.
* `apply_patch(xpath, new_code, mode="replace|prepend|append", original_hash=None, dry_run=False)`

  * if `original_hash` doesn’t match current → `ConflictError`.
  * `dry_run=True` returns a unified diff (string) without writing.
* Return result in JSON:

  ```json
  { "status":"ok", "lines_added":7, "lines_removed":2, "new_hash":"..." }
  ```
* Tests: replace + append + conflict.

### Rationale

An LLM needs to exchange **only** the changed fragment, not the whole file; the conflict hash provides safety with concurrent agents.

---

## Sprint 6 — Patch API (v2) + Builder helpers

### Tasks

* **Builder**

  * `hem.new_method(parent="MyClass", name="reset", args=["self"], body=["..."], decorators=[])`.
  * `hem.new_class(...)`, `hem.new_function(...)` – return code and insert immediately.
* `short_xpath(element)` – return the shortest unique path (token savings).
* Parameter `return_format="json|text"` in every public function.
* Include docs examples “how an agent should form JSON”.

### Rationale

Minimize LLM prompts – the agent sends clean JSON and CodeHem produces syntactically correct code.

---

## Sprint 7 — Workspace & thread-safe writes

### Status: ✅ completed

### Tasks

* `workspace = CodeHem.open_workspace(repo_root)`

  * index files → language → elements (cached).
  * `workspace.find(name="calculate", kind="method")` returns `(file, xpath)`.
* Lock file on write (per file) + `on_conflict` callback lets the AI decide.
* Smoke test 20 threads × 100 patches (thread safety).
* Stress test on 200k LOC file (timeout < 5 s warm).

### Rationale

Agents may operate in parallel; the workspace shortens searches and the lock ensures atomicity.

---

## Sprint 8 — Documentation + CLI + Release 1.0

### Status: ✅ completed

### Tasks

* **Developer Guide** – description of plugins, builder, patch API; PlantUML diagrams; hosted via GitHub Pages.
* **User Guide / Quick-Start for LLMs** – JSON → patch → diff → commit.
* CLI polish

  * `codehem detect file.py` → language + short stats
  * `codehem patch --xpath "My.f.x" --file update.txt`
* Version `1.0.0` on PyPI.

### Rationale

Without good documentation even the best API won’t reach users (including agents). Release 1.0 = leaving beta.

---

## Next directions (post‑1.0)

* **Vector-search of elements** (AST embeddings + names) – semantic find.
* **LSIF/LSP streaming** – real‑time refactoring in editors.
* **VS Code extension** – CodeHem-driven quick-fix & rename.

*Ship it — AI-ready, diff-first, zero-noise!*
