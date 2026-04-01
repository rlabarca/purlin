# Installation Guide

## Prerequisites

- git
- Python 3.8+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

## Install Purlin

```bash
claude plugin install purlin
```

This adds Purlin as a Claude Code plugin. The MCP server, hooks, and skills are available immediately.

## Initialize a Project

```
purlin:init
```

This does 3 things:

1. **Creates `.purlin/`** — config directory with `config.json` (team defaults) and `config.local.json` (per-user overrides, gitignored).
2. **Creates `specs/`** — directory for spec files, with a `_invariants/` subdirectory for read-only external constraints.
3. **Scaffolds proof plugin** — detects your test framework (pytest, Jest, or shell) and installs the appropriate proof collector so tests emit `*.proofs-*.json` files.

### Proof Plugin Setup by Framework

**pytest** — Adds `conftest.py` that imports the proof plugin:
```python
pytest_plugins = [".purlin/plugins/pytest_purlin"]
```

**Jest** — Adds the reporter to `jest.config.js`:
```javascript
reporters: ["default", ".purlin/plugins/jest_purlin.js"]
```

**Shell** — Source the harness in your test scripts:
```bash
source .purlin/plugins/purlin-proof.sh
```

## Config System

Purlin uses a two-file config system:

- **`.purlin/config.json`** — committed, team defaults
- **`.purlin/config.local.json`** — gitignored, per-user overrides

Resolution: `config.local.json` wins if it exists. On first access, `config.json` is copied to `config.local.json` automatically (copy-on-first-access).

Default config:
```json
{
  "version": "0.9.0",
  "test_framework": "auto",
  "spec_dir": "specs"
}
```

Read or update config with `purlin:config` or the `purlin_config` MCP tool.

## What Gets Created

```
your-project/
  .purlin/
    config.json            # Team defaults
    config.local.json      # Per-user (gitignored)
    plugins/               # Proof collector for your test framework
  specs/
    _invariants/           # Read-only external constraints
  .gitignore               # Updated with Purlin entries
```

## Updating Purlin

```bash
claude plugin update purlin
```

This pulls the latest version. Existing specs, proofs, and config are preserved.
