# Quick‑Start for LLMs

This short guide shows the typical workflow for autonomous agents.

1. **Detect the language** of a file:

   ```bash
   codehem detect path/to/file.py
   ```

2. **Query and patch** using JSON:

   ```json
   { "xpath": "Example.greet[method]", "new_code": "print('hi')" }
   ```

   Send this payload to `CodeHem.apply_patch` and apply the result.

3. **Preview diffs from the CLI** before writing:

   ```bash
   codehem patch path/to/file.py --xpath "Example.greet[method]" --file update.txt --dry-run
   ```

4. **Commit** the updated file when the patch succeeds.
