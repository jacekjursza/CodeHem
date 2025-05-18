# Roadmap → CodeHem 1.0 (**kontekst = Agenci AI**)

> środowisko CI/testy już istnieją
> nie ma użytkowników produkcyjnych → wolno zmieniać API bez migracji

---

## Sprint 1 — Stabilizacja i czytelne API

### Co robimy

* Wyrzucamy wszystkie `print()`; zostają wyłącznie logi (`logger.debug`/`info`).
* Upraszczamy `get_language_service` – kasujemy specjal-case dla Pythona, zostaje jednolita ścieżka.
* Ujednolicamy brak wyniku

  * `find_by_xpath` zwraca `None` (nie `(0,0)`).
  * `get_text_by_xpath` już jest `None` – pozostaje bez zmian.
* Poziom logów domyślnie `WARNING`; w CLI `--debug` przełącza na `DEBUG`.
* Testy regresyjne dla powyższych.

### Powód

Bez czystego, przewidywalnego API późniejsze feature’y (cache, patch-API) będą wprowadzały chaos.

---

## Sprint 2 — Cache + Lazy Loading + Profil

### Co robimy

* LRU-cache AST oraz wyniku ekstrakcji (`maxsize=128`, klucz = sha1(code)).
* Cache `(code_hash, xpath)` w `find_by_xpath`.
* Zamieniamy listy/dict ekstraktorów na `@cached_property`; instancje tworzą się przy pierwszym użyciu.
* Profilujemy cold / warm run (plik 10 k LOC) – cel ≥ 3× przyspieszenie drugiego wywołania.

### Powód

Agenci będą wielokrotnie zadawać zapytania do tych samych plików – brak cache to marnowanie tokenów i CPU.

---

## Sprint 3 — Pluginowa architektura języków

### Co robimy

* Wprowadzamy entry-points `codehem.languages` + loader `importlib.metadata.entry_points`.
* Alias `'javascript'` → `TypeScriptLanguageService`.
* Dodajemy prosty `JavaScriptLanguageDetector` (regexy `function`, `=>`, `export`, `var/let/const`).
* Tworzymy cookie-cutter `codehem-lang-template` (service, formatter, tests).

### Powód

Krok konieczny, by w przyszłości wtyczki (np. Java, Go) mogły być instalowane osobno i obsługiwane przez agentów bez zmian w core.

---

## Sprint 4 — DRY: formatter + manipulator

### Co robimy

* Tworzymy `IndentFormatter` (języki wcięciowe) i `BraceFormatter` (klamrowe).

  * Wspólne helpery (`_fix_spacing`, `apply_indentation`) przenosimy do bazowej klasy.
* Tworzymy `AbstractBlockManipulator` z uniwersalną logiką wstawiania; Python/TS podają tylko token bloku (`:` vs `{`).
* Descriptor-as-data

  * Konfiguracja JSON/TOML z node-patternami zamiast powielania klas ekstraktora.

### Powód

Minimalizujemy duplikację przed wprowadzeniem kolejnych języków; zmniejszamy powierzchnię edycji dla AI-patchy.

---

## Sprint 5 — Patch API (v1) — „minimal-diff”

### Co robimy

* `get_element_hash(xpath)` – sha256 wybranego fragmentu.
* `apply_patch(xpath, new_code, mode="replace|prepend|append", original_hash=None, dry_run=False)`

  * jeżeli `original_hash` nie zgadza się z bieżącym -> ConflictError.
  * `dry_run=True` zwraca unified-diff (string) bez zapisu.
* Zwracamy wynik w JSON:

  ```json
  { "status":"ok", "lines_added":7, "lines_removed":2, "new_hash":"..." }
  ```
* Testy: replace + append + conflict.

### Powód

LLM potrzebuje wymieniać **tylko** zmieniony fragment, nie pełen plik; konflikt-hash daje bezpieczeństwo przy równoległych agentach.

---

## Sprint 6 — Patch API (v2) + Builder helpers

### Co robimy

* **Builder**

  * `hem.new_method(parent="MyClass", name="reset", args=["self"], body=["..."], decorators=[])`.
  * `hem.new_class(...)`, `hem.new_function(...)` – zwracają kod + od razu wstawiają.
* `short_xpath(element)` – zwraca najkrótszą unikalną ścieżkę (oszczędność tokenów).
* Parametr `return_format="json|text"` w każdej publicznej funkcji.
* Dołączyć przykłady w docs „jak agent ma formować JSON”.

### Powód

Minimalizacja promptów LLM – agent przekazuje czysty JSON, CodeHem generuje syntaktycznie poprawny kod.

---

## Sprint 7 — Workspace & thread-safe writes

### Co robimy

* `workspace = CodeHem.open_workspace(repo_root)`

  * indeks plików → język → elementy (na cache).
  * `workspace.find(name="calculate", kind="method")` zwraca `(file, xpath)`.
* Lock-file przy zapisie (per plik) + `on_conflict` callback – pozwala AI podjąć decyzję.
* Smoke-test 20 wątków × 100 patchy (thread safety).
* Stres-test pliku 200 k LOC (timeout < 5 s warm).

### Powód

Agenci mogą działać równolegle; workspace skraca wyszukiwanie, lock zapewnia atomiczność.

---

## Sprint 8 — Dokumentacja + CLI + Release 1.0

### Co robimy

* **Developer Guide** – opis pluginów, buildera, patch API; diagramy PlantUML; hostowane przez GitHub Pages.
* **User Guide / Quick-Start for LLMs** – JSON → patch → diff → commit.
* CLI polish

  * `codehem detect file.py` → język + short-stats
  * `codehem patch --xpath "My.f.x" --file update.txt`
* Wersja `1.0.0` na PyPI.

### Powód

Bez dobrej dokumentacji nawet najlepsze API nie trafi do użytkowników (w tym agentów). Release 1.0 = wyjście z bety.

---

## Kolejne kierunki (po 1.0)

* **Vector-search elementów** (embeddings AST + nazwy) – semantyczne find.
* **LSIF/LSP streaming** – realtime refaktoryzacja w edytorach.
* **VS Code extension** – CodeHem-driven quick-fix & rename.

*Ship it — AI-ready, diff-first, zero-noise!*
