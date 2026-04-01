# Purlin v2 Documentation

Purlin is a spec-driven development plugin for Claude Code. Specs define rules, tests prove them, `sync_status` shows coverage.

## Guides

| Guide | What it covers |
|-------|---------------|
| [Installation](installation-guide.md) | Installing Purlin, initializing a project, proof plugin setup |
| [Spec–Code Sync](spec-code-sync-guide.md) | The rule-proof model: specs, rules, proofs, and `sync_status` |
| [Testing Workflow](testing-workflow-guide.md) | Proof markers, proof files, and the verify workflow |
| [Invariants](invariants-guide.md) | Read-only external constraints in `specs/_invariants/` |
| [Worktrees](worktree-guide.md) | Running parallel agents in isolated git worktrees |

## Architecture at a Glance

```
.purlin/
  config.json              # Team defaults (committed)
  config.local.json        # Per-user overrides (gitignored)
  plugins/                 # Proof plugin (scaffolded by purlin:init)
specs/
  <category>/
    <feature>.md           # Spec (3-section format)
    <feature>.proofs-*.json  # Proof files (emitted by test runners)
    <feature>.receipt.json   # Verification receipts
  _invariants/
    i_<name>.md            # Read-only external constraints
```

## Runtime Components

| Component | Path | Purpose |
|-----------|------|---------|
| MCP server | `scripts/mcp/purlin_server.py` | Provides `sync_status` and `purlin_config` tools |
| Gate hook | `scripts/gate.sh` | Blocks writes to invariant files |
| Proof plugins | `scripts/proof/` | pytest, Jest, and shell proof collectors |
| Session start | `scripts/session-start.sh` | Clears stale runtime files |

## Skills Reference

See `references/purlin_commands.md` for the full 12-skill reference. Key skills:

- `purlin:spec` — create/edit specs
- `purlin:build` — implement from spec rules
- `purlin:verify` — run all tests, issue verification receipts
- `purlin:status` — show rule coverage via `sync_status`
- `purlin:init` — initialize a new project

## Hard Gates (only 2)

1. **Invariant protection** — `specs/_invariants/i_*` files are read-only. Use `purlin:invariant sync` to update.
2. **Proof coverage** — `purlin:verify` won't issue a receipt unless every rule has a passing proof.

Everything else is optional guidance.
