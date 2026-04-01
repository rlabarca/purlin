# Taxonomy (Phase 2)

## Anchors

1. **schema_spec_format** — 3-section spec format (What it does, Rules, Proof) + metadata (Requires, Scope, Stack). Governs all spec files.
2. **schema_proof_file** — Proof JSON file format (.proofs-{tier}.json), feature-scoped overwrite contract. Governs proof plugins, sync-status, verify.
3. **schema_receipt** — Verification receipt format (.receipt.json), vhash = SHA256(sorted rule IDs + proof IDs/statuses). Governs verify, sync-status.
4. **security_no_dangerous_patterns** — No eval/exec, no shell=True, no hardcoded secrets. Grep-based negative assertions. Governs all scripts/, dev/.

## Categories

### mcp (4 features)
- **mcp-server** (`specs/mcp/mcp-server.md`) — JSON-RPC MCP transport, tool dispatch, spec scanning. Scope: scripts/mcp/purlin_server.py, scripts/mcp/manifest.json. Requires: schema_spec_format, schema_proof_file.
- **sync-status** (`specs/mcp/sync-status.md`) — Coverage computation, proof aggregation, directives. Scope: scripts/mcp/purlin_server.py. Requires: schema_spec_format, schema_proof_file.
- **config-engine** (`specs/mcp/config-engine.md`) — Two-file config resolution, copy-on-first-access. Scope: scripts/mcp/config_engine.py.
- **changelog** (`specs/mcp/changelog.md`) — Git-based structured changelog with spec cross-references. Scope: scripts/mcp/purlin_server.py.

### proof (1 consolidated feature)
- **proof-plugins** (`specs/proof/proof-plugins.md`) — Shared proof collection across pytest/jest/shell: marker parsing, feature-scoped JSON emission, overwrite strategy. Per-implementation rules for marker syntax. Scope: scripts/proof/pytest_purlin.py, scripts/proof/jest_purlin.js, scripts/proof/shell_purlin.sh. Requires: schema_proof_file.

### hooks (2 features)
- **gate-hook** (`specs/hooks/gate-hook.md`) — Pre-write hook blocking writes to specs/_invariants/i_* unless bypass lock exists. Scope: scripts/gate.sh, hooks/hooks.json.
- **session-start** (`specs/hooks/session-start.md`) — Session startup hook clearing stale runtime locks. Scope: scripts/session-start.sh, hooks/hooks.json.
