# AGENTS.md – Architecture & Orientation

> **Audience**: autonomous agents / LLMs joining the project.
> **Purpose**: understand what this codebase does, how it is laid out, and the architectural principles we protect.
> **Context**: you start each task in a blank VM; local indexes are cheap to rebuild, global knowledge is not – hence this primer.

---

## 1 · Idea in One Sentence

**CodeHem** is a *syntax‑aware, language‑agnostic* engine that lets higher‑level tools query, patch and refactor source code while guaranteeing syntactic validity.  Tree‑sitter provides the AST; plug‑in modules provide language specifics; a small core provides uniform operations.

---

## 2 · Roadmap at a Glance *(May 2025)*

| Sprint | Status         | Focus                                                               |
| ------ | -------------- | ------------------------------------------------------------------- |
| 1      | ✅ done         | API clean‑up, remove prints, unify error handling                   |
| 2      | ✅ done         | AST & XPath cache, lazy loading                                     |
| 3      | 🟢 in‑progress | Plugin architecture (entry‑points), JS alias, cookiecutter template |
| 4      | 🚧 queued      | DRY formatter/manipulator refactor                                  |
| 5      | 🚧 planned     | Patch API (`apply_patch`, `get_element_hash`)                       |
| 6      | 🟢 in-progress | Builder helpers, short XPath, JSON results                          |
| 7      | 🚧 planned     | Workspace index, locks, thread‑safety                               |
| 8      | 🚧 planned     | Docs, CLI polish, first public release 1.0                          |

Anything beyond Sprint 3 is subject to change; check issues before diving into those areas.

---

## 3 · High‑Level Architecture

```
           ┌──────────────┐   query / patch   ┌────────────────┐
 Agent/CLI │  CodeHem API │  ───────────────► │ LanguageService │◄── plugins (entry‑points)
           └─────┬────────┘                   └────────┬───────┘
                 │                                        │
                 │ (delegates)                            │
                 ▼                                        ▼
      ┌────────────────────┐                    ┌──────────────────┐
      │ ExtractionService  │   builds          │ ManipulationSvc   │  writes + diffs
      └────────────────────┘   CodeElements    └──────────────────┘
                 │                                        │
                 └───> tree‑sitter parser & AST  <────────┘
```

* **Core** (`core/`) is 100 % language‑agnostic.
* **LanguageService** (
  `languages/<lang>/service.py`) registers extractors, manipulators, formatter, detector.
* **Plugins** are discovered at runtime via Python entry‑points (`codehem.languages`).

---

## 4 · Repository Layout (top level)

```
repo‑root/
├── core/
│   ├── extraction.py      # AST → CodeElement tree
│   ├── manipulation.py    # patch orchestration, diff helpers
│   ├── workspace.py       # repo‑wide index & cache (Sprint 7)
│   └── utils/             # hashing, locks, logging, misc
├── languages/
│   ├── python/            # PythonLanguageService, formatter, manipulator
│   └── typescript/        # TypeScriptService (alias js)
├── registry.py            # plugin discovery & lazy import
├── cli.py                 # `codehem` entry‑point (Sprint 8 polish)
├── tests/                 # pytest unit & integration suite
└── docs/                  # architecture, guides, diagrams
```

Inside each language folder:

```
languages/<lang>/
├── service.py      # declares NODE_PATTERNS, file extensions, detector regex
├── formatter.py    # derives from BraceFormatter / IndentFormatter
├── manipulator/
│   ├── class_.py   # optional overrides for tricky constructs
│   └── ...
└── tests/          # language‑specific cases
```

---

## 5 · Naming & Module Conventions

| Suffix / Pattern     | Responsibility                                          |
| -------------------- | ------------------------------------------------------- |
| `*LanguageService`   | glue object: holds tree‑sitter grammar, config, helpers |
| `*Formatter`         | whitespace, braces, trailing newline rules              |
| `*Manipulator`       | text insertion/replacement; calls formatter             |
| `NODE_PATTERNS` dict | maps `CodeElementType` → tree‑sitter query              |
| Tests mirror modules | `test_python_formatter.py` ↔ `python/formatter.py`      |

### Coding style

* **Python 3.11**, typed; `ruff + black` enforced by pre‑commit.
* Public methods carry full docstrings; examples use triple‑backticks for doctest‑ready snippets.
* Logging via stdlib `logging`; DEBUG noisy, default WARNING.

### Error hierarchy (core/utils/errors.py)

```
CodeHemError
 ├─ ElementNotFoundError
 ├─ WriteConflictError   # will appear Sprint 7
 └─ UnsupportedLanguageError
```

---

## 6 · Architectural Principles We Protect

1. **Syntax‑aware first** – every modification must go through a parser; regex hacks live only in detectors.
2. **Plugin ≥ Rewrite** – add language logic via entry‑point, not `if lang == 'x'`.
3. **Minimal duplication** – common behaviour moves to abstract base or template; language modules stay thin.
4. **Patch atomicity** – once Patch API lands, writes require hash match & lockfile.
5. **Tests before merge** – CI gate demands ≥ 95 % coverage on `core/`, ≥ 80 % on per‑language code.

---

## 7 · Adding or Modifying Code

* Extend **NODE\_PATTERNS** instead of writing a new extractor when possible.
* Use the **cookiecutter‑template** (`codehem-lang-template`) for new languages; it wires service, formatter, tests.
* Keep commits focused; prefer 1 feature or bugfix per PR – helps future agents do bisects.

---

## 8 · Further Reading

* `docs/Developer‑Guide.md` – in‑depth walkthrough of CodeHem API (once Sprint 8 ships).
* `tests/fixtures/` – curated real‑world code pieces used in regression tests.
* `ROADMAP.md` (tbd) – living document reflecting sprint progress.

---

Welcome to CodeHem!  Skim this file before opening your first module; ten minutes here saves hundreds of tokens later.
