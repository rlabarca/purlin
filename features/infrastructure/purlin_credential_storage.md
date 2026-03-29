# Feature: Credential Storage

> Label: "Infrastructure: Credential Storage"
> Category: "Infrastructure"
> Owner: PM

## 1. Overview

Purlin needs a secure, cross-platform mechanism for storing sensitive credentials (Figma tokens, deploy keys, Confluence API tokens, etc.) that:

- Never stores secrets in plaintext project files
- Works on macOS, Windows, and Linux without platform-specific code
- Leverages Claude Code's native `userConfig` plugin system
- Makes credentials available to the MCP server and hooks at runtime via environment variables

Claude Code's plugin `userConfig` system provides exactly this. Fields marked `"sensitive": true` are stored in the OS keychain (macOS Keychain, Windows Credential Manager) or an encrypted credentials file (Linux). Non-sensitive fields are stored in `~/.claude/plugins/data/<plugin>/`. All `userConfig` values are injected as `CLAUDE_PLUGIN_OPTION_<KEY>` environment variables into MCP server processes.

### 1.1 Design Principles

1. **Zero custom storage.** Purlin does not implement its own credential vault. Claude Code is the credential store.
2. **Env-var contract.** The MCP server reads credentials exclusively from `CLAUDE_PLUGIN_OPTION_*` environment variables. No file I/O for secrets.
3. **Graceful degradation.** Missing credentials are not errors — features that need them report what's missing and how to configure it.
4. **No plaintext fallback.** Credentials must never be written to `.purlin/`, `config.local.json`, or any project-local file.

---

## 2. Requirements

### 2.1 Plugin Manifest (`plugin.json` `userConfig`)

The `userConfig` section of `.claude-plugin/plugin.json` declares all credential fields. Each sensitive field MUST include `"sensitive": true`.

**Required fields:**

| Key | Type | Sensitive | Required | Description |
|-----|------|-----------|----------|-------------|
| `figma_access_token` | string | true | false | Figma personal access token |
| `deploy_token` | string | true | false | Deployment authentication token |
| `confluence_token` | string | true | false | Atlassian Confluence API token |
| `confluence_email` | string | false | false | Atlassian account email for Confluence |
| `confluence_base_url` | string | false | false | Confluence instance URL (e.g., `https://team.atlassian.net`) |
| `default_model` | string | false | false | Default Claude model for Purlin sessions |

Additional credential fields may be added following this pattern. The `sensitive` flag determines storage location (keychain vs plugin data dir).

### 2.2 MCP Server Credential Access

The MCP server (`scripts/mcp/purlin_server.py`) accesses credentials via a helper module (`scripts/mcp/credentials.py`).

**`credentials.py` interface:**

```python
def get_credential(key: str) -> str | None:
    """Read a credential from CLAUDE_PLUGIN_OPTION_<key> env var.

    Returns None if the credential is not configured.
    """

def require_credential(key: str, feature_name: str) -> str:
    """Read a credential, raising a descriptive error if missing.

    The error message tells the user how to configure the credential.
    """

def credential_status() -> dict[str, bool]:
    """Return a dict of {key: is_configured} for all known credential keys."""
```

The module maintains a registry of known credential keys and their descriptions, used by `credential_status()` and error messages.

### 2.3 `purlin_credentials` MCP Tool

A new MCP tool exposed by the server that lets the agent check credential availability without exposing values.

**Tool definition:**

| Field | Value |
|-------|-------|
| Name | `purlin_credentials` |
| Description | Check which credentials are configured for this Purlin project. |

**Input schema:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | enum: `status`, `check` | No (default: `status`) | Action to perform |
| `key` | string | No | Specific credential key to check (for `check` action) |

**Behavior:**

- **`status`**: Returns the full credential status map (`{key: configured, description}` for each known key). Never returns credential values.
- **`check`**: Returns whether a specific credential is configured, with its description and configuration instructions if missing.

**Security constraint:** The tool MUST NOT return credential values. Only boolean availability and metadata.

### 2.4 Credential Configuration UX

When a feature requires a credential that isn't configured, the agent prints:

```
Missing credential: <key>
  <description>

To configure, set it in your Claude Code plugin settings:
  Claude Code → Settings → Plugins → Purlin → <field title>

Or set the environment variable directly:
  export CLAUDE_PLUGIN_OPTION_<key>="<value>"
```

The env var fallback ensures credentials work even when the plugin `userConfig` UI isn't available (e.g., CLI-only sessions, CI environments).

### 2.5 Migration: Remove Plaintext Credential Files

Any existing plaintext credential files (e.g., `.purlin/runtime/confluence/credentials.json`) must be:

1. Documented as deprecated in a code comment
2. Not read by new code paths — the `CLAUDE_PLUGIN_OPTION_*` env vars are the sole source
3. Listed in `.gitignore` if not already

Existing code that reads these files should be updated to use `credentials.get_credential()` instead.

### 2.6 `.gitignore` Enforcement

The project `.gitignore` (or `.purlin/.gitignore`) MUST include patterns that prevent credential files from being committed:

```
credentials.json
*.credentials
*.secret
```

---

## 3. Scenarios

### Unit Tests

#### Scenario: get_credential returns value when env var is set

    Given CLAUDE_PLUGIN_OPTION_figma_access_token is set to "test-token"
    When get_credential("figma_access_token") is called
    Then it returns "test-token"

#### Scenario: get_credential returns None when env var is missing

    Given CLAUDE_PLUGIN_OPTION_deploy_token is not set
    When get_credential("deploy_token") is called
    Then it returns None

#### Scenario: get_credential returns None for empty string

    Given CLAUDE_PLUGIN_OPTION_deploy_token is set to ""
    When get_credential("deploy_token") is called
    Then it returns None

#### Scenario: require_credential returns value when configured

    Given CLAUDE_PLUGIN_OPTION_figma_access_token is set to "test-token"
    When require_credential("figma_access_token", "Figma ingest") is called
    Then it returns "test-token"

#### Scenario: require_credential raises ValueError when missing

    Given CLAUDE_PLUGIN_OPTION_confluence_token is not set
    When require_credential("confluence_token", "Confluence sync") is called
    Then a ValueError is raised
    And the error message includes "confluence_token"
    And the error message includes "Confluence sync"
    And the error message includes "CLAUDE_PLUGIN_OPTION_confluence_token"

#### Scenario: credential_status reports all known keys

    Given the credential registry has 6 known keys
    When credential_status() is called
    Then it returns a dict with 6 entries
    And each entry has "configured", "description", and "title" keys

#### Scenario: credential_status reflects env var state

    Given CLAUDE_PLUGIN_OPTION_figma_access_token is set to "token"
    And CLAUDE_PLUGIN_OPTION_deploy_token is not set
    When credential_status() is called
    Then figma_access_token entry has configured: true
    And deploy_token entry has configured: false

#### Scenario: credential registry matches plugin.json userConfig

    Given the _CREDENTIAL_REGISTRY in credentials.py
    And the userConfig in plugin.json
    When the keys are compared
    Then every userConfig key exists in the registry
    And every registry key exists in userConfig

#### Scenario: purlin_credentials tool status action

    Given the MCP server is running
    When handle_purlin_credentials is called with action "status"
    Then it returns credential_status() output
    And no credential values are present

#### Scenario: purlin_credentials tool check action for missing key

    Given deploy_token is not configured
    When handle_purlin_credentials is called with action "check" and key "deploy_token"
    Then it returns configured: false
    And it includes a hint with configuration instructions

#### Scenario: purlin_credentials tool check action for unknown key

    When handle_purlin_credentials is called with action "check" and key "nonexistent"
    Then it returns an error: "Unknown credential key: nonexistent"

#### Scenario: purlin_credentials tool check requires key parameter

    When handle_purlin_credentials is called with action "check" and no key
    Then it returns an error: "key is required for check action"

### QA Scenarios

#### Scenario: Credential available via userConfig

    Given the user has configured figma_access_token in Claude Code plugin settings
    When the MCP server starts
    Then CLAUDE_PLUGIN_OPTION_figma_access_token is set in the server's environment
    And get_credential("figma_access_token") returns the token value

#### Scenario: Credential missing — graceful degradation

    Given the user has NOT configured deploy_token
    When the agent invokes purlin_credentials with action "check" and key "deploy_token"
    Then the tool returns configured: false with configuration instructions
    And no error is raised

#### Scenario: Environment variable fallback

    Given the user has set CLAUDE_PLUGIN_OPTION_figma_access_token as a shell env var
    But has NOT configured it via Claude Code plugin settings UI
    When get_credential("figma_access_token") is called
    Then it returns the env var value (the env var is the same regardless of source)

#### Scenario: Cross-platform storage

    Given the user is on Windows
    When they configure a sensitive credential via Claude Code plugin settings
    Then the value is stored in Windows Credential Manager (handled by Claude Code)
    And CLAUDE_PLUGIN_OPTION_<key> is injected into the MCP server process

#### Scenario: No credential values in tool output

    Given figma_access_token is configured with value "secret-token-abc"
    When the agent invokes purlin_credentials with action "status"
    Then the response contains configured: true for figma_access_token
    And the string "secret-token-abc" does NOT appear in the response

---

## 4. Acceptance Criteria

1. `plugin.json` declares all credential fields with correct `sensitive` flags
2. `credentials.py` module provides `get_credential`, `require_credential`, and `credential_status`
3. `purlin_credentials` MCP tool returns credential availability without exposing values
4. No credential values are written to any file under `.purlin/` or the project directory
5. Missing credentials produce actionable error messages with configuration instructions
6. Works identically on macOS, Windows, and Linux (no platform-specific code in Purlin)

---

## 5. Out of Scope

- Credential rotation or expiry management (Claude Code handles token lifecycle)
- OAuth flow implementation (use Claude Code's MCP OAuth support for services that need it)
- Encrypting credentials at rest (delegated to Claude Code / OS keychain)
- UI for credential management beyond Claude Code's plugin settings
