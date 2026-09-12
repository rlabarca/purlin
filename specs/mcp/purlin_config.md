# Feature: purlin_config

> Requires: security_no_dangerous_patterns
> Scope: scripts/mcp/purlin_server.py
> Stack: python/stdlib, json
> Description: MCP tool for reading and writing Purlin configuration. Reads the full config or a single key, and writes single keys atomically.

## Rules

- RULE-1: Reads the full config or a single key, and writes single keys via `update_config`

## Proof

- PROOF-1 (RULE-1): Call the tool with action `write`, key `test_key`, value `test_val`; verify it answers with the exact string `Set 'test_key' = "test_val"`; read back with key `test_key` and verify the JSON is exactly `{"test_key": "test_val"}`; read again with no key and verify the full config is exactly `{"test_key": "test_val"}`; then verify action `delete` answers `Unknown action` and leaves the config unchanged, and a `write` with no key answers that a key is required @integration
