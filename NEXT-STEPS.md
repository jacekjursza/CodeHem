# Next Steps after Failed Test Run

The automated test suite was executed with `pytest`. Several tests failed due to
issues in the Python and TypeScript extraction logic.

## Summary of Failures

- `tests/common/test_codehem2.py` – property getter/setter and XPath retrieval
  returned `None` because the internal tree-sitter queries could not be parsed.
- `tests/python/test_element_extraction.py` – property and import extraction
  failed; returned `None` or empty results.
- `tests/python/test_xpath_results.py` – multiple tests raised `TypeError` when
  operating on `None` results.
- `tests/typescript/test_element_extraction.py` – interface and imports
  extraction failed, leaving no matching elements.
- Integration tests in `tests/test_full_integration.py` also failed due to the
  above extraction issues.

`pytest` reported 16 failing tests in total:

```
$ pytest -q
...FFF.................................................................. [ 49%]
..............................F...F............FFFF.FF..FF......F...F.F. [ 99%]
.                                                                        [100%]
16 failed, 129 passed
```

## Likely Cause

Errors in the test output indicate `tree_sitter.QueryError: Invalid syntax at
row 1, column 0` for several queries. This suggests that query strings used for
extracting Python static properties and TypeScript elements are malformed or
incompatible with the currently bundled tree-sitter grammars.

## Suggested Solutions

1. **Review tree-sitter query strings** in
   `codehem/languages/lang_python/components/extractor.py` and
   `codehem/core/engine/ast_handler.py`. Ensure node names used in queries match
   those provided by the `tree-sitter-python` and `tree-sitter-typescript`
   grammars.
2. **Verify query syntax** by loading the grammar and executing minimal queries
   in an interactive environment. A leading newline or incorrect nesting may
   trigger the `Invalid syntax` errors.
3. **Check grammar versions**. The installed `tree-sitter` Python packages might
   expose different node names or structures compared to the queries in the
   repository. Align the queries or upgrade/downgrade the grammar packages.
4. **Run the failing tests individually** once the query issues are fixed to
   confirm that property getter/setter extraction and TypeScript import handling
   behave correctly.
