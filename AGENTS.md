# Repository Guidelines

## Overview
CodeHem is a syntax‑aware, multi‑language engine for structure‑aware queries, extraction, and safe patching of source code. It uses tree‑sitter for parsing and language plugins for specifics; the core guarantees consistent operations and element‑boundary correctness.

- Detects language; extracts classes/functions/methods to JSON for tooling.
- Finds elements via XPath‑like paths; returns text/ranges; computes hashes.
- Applies patches (replace/append/prepend) with dry‑run diffs and hash conflict checks.
- Languages: Python, TypeScript, JavaScript; extend via `codehem/languages/<lang>/`.
- CLI examples:
  - `python -m codehem.cli detect path/to/file.py`
  - `python -m codehem.cli extract path/to/file.ts --raw-json`
  - `python -m codehem.cli patch app.py --xpath "MyClass.do_work" --file new_body.txt --mode replace --dry-run`

## Project Structure & Module Organization
- Package root: `codehem/`.
- Core: `codehem/core/` (extraction_service, manipulation_service, registry, workspace, utils).
- Languages: `codehem/languages/<lang>/` (e.g., `lang_python/`, `lang_typescript/`) with `service.py`, detectors, type handlers.
- Models: `codehem/models/` (element types, ranges, XPath helpers).
- CLI & entry: `codehem/cli.py`, `codehem/main.py`.
- Tests & Docs: `tests/` (unit/integration), `docs/` (guides, diagrams).

## Build, Test, and Development Commands
- CLI help: `python -m codehem.cli --help` or `python codehem/cli.py --help`.
- Run tests: `pytest -q` | target a file: `pytest tests/test_patch_api.py -q`.
- Lint: `ruff check .` | autofix: `ruff check . --fix`.
- Format: `black .`.
- Pre‑commit (if configured): `pre-commit run -a`.

## Coding Style & Naming Conventions
- Python 3.11, type‑annotated, 4‑space indent.
- Tools: `ruff` + `black`; public methods include doctest‑ready examples.
- Logging: stdlib `logging` (DEBUG noisy, default WARNING).
- Naming: `*LanguageService`, `*PostProcessor`, `*Detector`; `NODE_PATTERNS` maps element types → queries.
- Tests mirror modules (e.g., `tests/python/` ↔ `codehem/languages/lang_python/`).

## Testing Guidelines
- Framework: `pytest`; keep tests focused and deterministic.
- Coverage targets: `codehem/core/` ≥ 95%, language code ≥ 80%.
- Locations: `tests/core/`, `tests/python/`, `tests/typescript/`; fixtures in `tests/fixtures/`.

## Commit & Pull Request Guidelines
- Commits: one topic per commit; imperative mood (“core: cache XPath lookups”); keep diffs minimal.
- PRs: clear description (what/why), linked issues, updated tests/docs, and screenshots for CLI UX changes.
- Quality gate: lint, format, and tests must pass; maintain coverage thresholds.

## Architecture & Agent Tips
- Syntax‑aware first: route edits through extraction/manipulation plus formatters; avoid regex beyond detectors.
- Plugin ≥ rewrite: extend via `codehem/languages/<lang>/` and entry‑points.
- Prefer evolving `NODE_PATTERNS` before new extractors; keep language modules thin.
- For new languages, start from `codehem-lang-template` and mirror structure above.

## Key References
- `docs/Developer-Guide.md`: API walkthrough and usage patterns.
- `docs/Plugin-Development-Tutorial.md`: create/extend a language service.
- `docs/component_interfaces.md`: contracts for services and components.
- `docs/input_validation.md` and `codehem/core/input_validation.py`: validation rules.
- `docs/Troubleshooting-Guide.md`: common failures and fixes.
- `docs/architecture.puml`: system diagram; `docs/roadmap.md`: planned work.
- `codehem/core/README.md`: core responsibilities and modules.
