# JSON Interaction Examples

These snippets show how an agent can interact with CodeHem using JSON payloads.

## Patch API

```json
{
  "xpath": "Example.greet[method]",
  "new_code": "print('hi')",
  "original_hash": "...",
  "mode": "replace",
  "return_format": "json"
}
```

The response will include line statistics and the updated code when `return_format` is `json`.
