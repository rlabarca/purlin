# SFC Taxonomy — Purlin Framework

## Anchors

1. **schema_spec_format** — 3-section spec file format (What it does, Rules, Proof), ID conventions, metadata
   - Governs: `specs/**/*.md`
2. **schema_proof_file** — Proof JSON structure: tier, proofs array, per-entry fields
   - Governs: `specs/**/*.proofs-*.json`
3. **schema_receipt** — Verification receipt format: vhash, commit, timestamp, rules/proofs
   - Governs: `specs/**/*.receipt.json`

## Categories

### mcp
MCP server, tools, and config engine.

| Feature | File Name | Description | Anchors |
|---------|-----------|-------------|---------|
| sync-status | sync-status.md | Scans specs + proofs, produces coverage report with directives | schema_spec_format, schema_proof_file |
| changelog | changelog.md | Git-based diff summary with file classification and spec change detection | schema_spec_format |
| config-engine | config-engine.md | Two-file config resolution (local > shared), copy-on-first-access | — |
| mcp-server | mcp-server.md | JSON-RPC 2.0 stdio transport, tool dispatch, manifest loading | — |

### proof
Test framework proof plugins.

| Feature | File Name | Description | Anchors |
|---------|-----------|-------------|---------|
| proof-pytest | proof-pytest.md | Collects @pytest.mark.proof markers, emits feature-scoped JSON | schema_proof_file |
| proof-jest | proof-jest.md | Parses [proof:...] from test names, emits feature-scoped JSON | schema_proof_file |
| proof-shell | proof-shell.md | Bash functions for proof registration + finish, emits JSON | schema_proof_file |

### hooks
Claude Code hook scripts.

| Feature | File Name | Description | Anchors |
|---------|-----------|-------------|---------|
| gate-hook | gate-hook.md | Blocks writes to specs/_invariants/i_* unless bypass lock exists | — |
| session-start | session-start.md | Clears stale runtime locks on session startup | — |
