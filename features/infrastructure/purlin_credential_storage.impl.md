# Implementation Notes: Credential Storage

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| `credential_status()` returns `{key: configured, description}` | Returns `{key: {configured, description, title}}` — adds `title` field | CLARIFICATION | PENDING |

## Implementation Log

**[IMPL]** Plugin manifest (`plugin.json`) updated with 6 `userConfig` fields. Three sensitive fields (`figma_access_token`, `deploy_token`, `confluence_token`) marked with `"sensitive": true` for OS keychain storage. Three non-sensitive fields (`confluence_email`, `confluence_base_url`, `default_model`) use plugin data directory.

**[IMPL]** Created `scripts/mcp/credentials.py` with three public functions: `get_credential()`, `require_credential()`, `credential_status()`. All read exclusively from `CLAUDE_PLUGIN_OPTION_*` environment variables. No file I/O for secrets.

**[IMPL]** Registered `purlin_credentials` MCP tool in `purlin_server.py` with `status` and `check` actions. Handler never returns credential values — only boolean availability and metadata.

**[IMPL]** Added `.gitignore` patterns (`credentials.json`, `*.credentials`, `*.secret`) per spec section 2.6.

**[IMPL]** Registered `docs/credential-storage-guide.md` in `docs/index.md`.

**[CLARIFICATION]** The `credential_status()` return format includes a `title` field beyond what the spec's type signature shows (`dict[str, bool]`). The actual return is `dict[str, dict]` with `{configured, description, title}` per key. The `title` field is needed by the `check` action's hint message and provides better UX when displaying credential status. The spec's prose in section 2.3 says "Returns the full credential status map (`{key: configured, description}` for each known key)" — the implementation extends this with `title` for consistency with the credential registry.

**[IMPL]** Unit tests written in `scripts/mcp/test_credentials.py` covering all spec scenarios: env var reading, empty string handling, require_credential error format, status reporting, plugin.json/registry sync, and MCP tool handler behavior.
