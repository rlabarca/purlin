<p align="center">
  <img src="../assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin Documentation

**Rule-Proof Spec-Driven Development**

- Write better code through proof-based specs
- Prove spec / code drift with signed verification
- Enable multi-discipline collaboration with smart changelogs and remote invariant specs that cannot be adjusted during development

## Guides

| Guide | What it covers |
|-------|---------------|
| [The Purlin Lifecycle](lifecycle-guide.md) | Spec format, sync model, PM/Engineer/QA workflows, CI integration |
| [Installation](installation-guide.md) | Installing Purlin, initializing a project, proof plugin setup |
| [Testing Workflow](testing-workflow-guide.md) | Proof markers, proof quality, custom plugins, tiers, manual proofs |
| [Invariants](invariants-guide.md) | Read-only external constraints in `specs/_invariants/` |
| [Worktrees](worktree-guide.md) | Running parallel agents in isolated git worktrees |

## Example Workflows

| Example | What it shows |
|---------|---------------|
| [Figma Web App Example](examples/figma-web-app.md) | Build a weather app from scratch using a Figma design invariant |

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

See [references/purlin_commands.md](../references/purlin_commands.md) for the full 13-skill reference.

| Skill | Guide |
|-------|-------|
| `purlin:spec-from-code` | [Generating Specs from Code](spec-from-code-guide.md) — onboarding existing projects |

Key skills:

- `purlin:spec` — create/edit specs
- `purlin:build` — implement from spec rules
- `purlin:verify` — run all tests, issue verification receipts
- `purlin:status` — show rule coverage via `sync_status`
- `purlin:changelog` — PM-readable summary of what changed
- `purlin:spec-from-code` — reverse-engineer specs from existing code
- `purlin:init` — initialize a new project

## Hard Gates (only 2)

1. **Invariant protection** — `specs/_invariants/i_*` files are read-only. Use `purlin:invariant sync` to update.
2. **Proof coverage** — `purlin:verify` won't issue a receipt unless every rule has a passing proof.

Everything else is optional guidance.
