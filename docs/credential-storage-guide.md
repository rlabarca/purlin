# How Credential Storage Works in Purlin

How Purlin stores and accesses sensitive credentials like API tokens and deploy keys.

---

## How It Works

Purlin does not implement its own credential vault. It uses Claude Code's native plugin `userConfig` system, which stores sensitive values in your operating system's secure storage:

| Platform | Storage |
|----------|---------|
| macOS | Keychain |
| Windows | Credential Manager |
| Linux | Encrypted credentials file (`~/.claude/.credentials.json`, mode 0600) |

When the MCP server starts, Claude Code injects all configured credentials as environment variables (`CLAUDE_PLUGIN_OPTION_<key>`). Purlin reads them from there. No credential values are ever written to project files.

---

## Available Credential Fields

| Key | What It's For | Sensitive |
|-----|--------------|-----------|
| `figma_access_token` | Figma personal access token for design system integration | Yes |
| `deploy_token` | Deployment authentication token | Yes |
| `confluence_token` | Atlassian Confluence API token | Yes |
| `confluence_email` | Atlassian account email for Confluence | No |
| `confluence_base_url` | Confluence instance URL | No |
| `default_model` | Default Claude model for Purlin sessions | No |

**Sensitive** fields are stored in the OS keychain. Non-sensitive fields are stored in `~/.claude/plugins/data/purlin-inline/`.

---

## Configuring Credentials

### Option 1: Claude Code Plugin Settings (Recommended)

Open Claude Code settings and navigate to:

```
Settings → Plugins → Purlin
```

Fill in the fields you need. Sensitive values are stored in your OS keychain automatically.

### Option 2: Environment Variables

Set the variable before starting Claude Code:

```bash
export CLAUDE_PLUGIN_OPTION_figma_access_token="your-token-here"
claude
```

Or add it to your shell profile (`~/.zshrc`, `~/.bashrc`, etc.) for persistence:

```bash
echo 'export CLAUDE_PLUGIN_OPTION_figma_access_token="your-token-here"' >> ~/.zshrc
```

On Windows (PowerShell):

```powershell
$env:CLAUDE_PLUGIN_OPTION_figma_access_token = "your-token-here"
claude
```

Or set it permanently:

```powershell
[Environment]::SetEnvironmentVariable("CLAUDE_PLUGIN_OPTION_figma_access_token", "your-token-here", "User")
```

The env var approach is useful for CI environments or when the plugin settings UI isn't available.

---

## Checking Credential Status

The agent can check which credentials are configured using the `purlin_credentials` MCP tool. This never reveals credential values — only whether each one is set.

The agent calls this automatically when a feature requires a credential. If one is missing, you'll see:

```
Missing credential: figma_access_token
  Figma personal access token for design system integration

To configure, set it in your Claude Code plugin settings:
  Claude Code → Settings → Plugins → Purlin → Figma Access Token

Or set the environment variable directly:
  export CLAUDE_PLUGIN_OPTION_figma_access_token="<value>"
```

---

## For Purlin Developers

### Reading Credentials in MCP Tools

Import from `credentials.py`:

```python
from credentials import get_credential, require_credential, credential_status

# Returns None if not configured
token = get_credential("figma_access_token")

# Raises ValueError with configuration instructions if missing
token = require_credential("figma_access_token", "Figma design ingest")

# Returns {key: {configured, description, title}} for all known keys
status = credential_status()
```

### Adding a New Credential Field

1. Add the field to `.claude-plugin/plugin.json` under `userConfig`:
   ```json
   "my_new_token": {
     "title": "My New Token",
     "description": "Token for the new integration",
     "type": "string",
     "sensitive": true,
     "required": false
   }
   ```

2. Register the key in `scripts/mcp/credentials.py` in `_CREDENTIAL_REGISTRY`:
   ```python
   "my_new_token": (
       "Token for the new integration",
       "My New Token",
   ),
   ```

3. Use `get_credential("my_new_token")` or `require_credential("my_new_token", "feature name")` in your code.

### Security Rules

- Never return credential values from MCP tools — only boolean availability
- Never write credentials to files under `.purlin/` or the project directory
- Never log credential values (even to stderr)
- Use `require_credential` for hard dependencies; use `get_credential` when the credential is optional
