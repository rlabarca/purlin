<p align="center">
  <img src="../assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin Documentation

**Rule-Proof Spec-Driven Development**

- Write better code through proof-based specs
- Prove spec / code drift with signed verification
- Enable multi-discipline collaboration with drift detection and anchor specs with external references

## Guides

| Guide | What it covers |
|-------|---------------|
| [The Purlin Lifecycle](lifecycle-guide.md) | Spec format, sync model, PM/Engineer/QA workflows, CI integration |
| [Installation and Quick Start](installation-guide.md) | Quick start, installing Purlin, initializing a project, proof plugin setup |
| [Testing Workflow](testing-workflow-guide.md) | Proof markers, proof quality, custom plugins, tiers, manual proofs |
| [Anchors and External References](anchors-guide.md) | Anchors, external references, FORBIDDEN patterns, cross-cutting constraints |
| [Collaboration](collaboration-guide.md) | External anchors, branch handoff, merge conflicts |
| [Dashboard](dashboard-guide.md) | Visual coverage dashboard — setup, usage, data flow |
| [Regulated Environments](regulated-environments.md) | Integration points for FDA, HIPAA, SOC2 -- what Purlin is and isn't |

## Example Workflows

| Example | What it shows |
|---------|---------------|
| [Figma Web App Example](examples/figma-web-app.md) | Build a weather app from scratch using a Figma design anchor |

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
  _anchors/
    <name>.md              # Cross-cutting constraints (optionally synced from external sources)
```

## Runtime Components

| Component | Path | Purpose |
|-----------|------|---------|
| MCP server | `scripts/mcp/purlin_server.py` | Provides `sync_status` and `purlin_config` tools |
| Proof plugins | `scripts/proof/` | pytest, Jest, and shell proof collectors |

## Skills Reference

See [references/purlin_commands.md](../references/purlin_commands.md) for the full skill reference.

| Resource | What it covers |
|----------|---------------|
| [Spec Quality Guide](../references/spec_quality_guide.md) | How to write good rules, proofs, tiers, anchors, and FORBIDDEN patterns |
| [Audit Criteria](../references/audit_criteria.md) | Three-pass audit -- spec coverage, structural checks, semantic alignment |
| [Drift Criteria](../references/drift_criteria.md) | File classification, drift detection, config field ownership |
| [Generating Specs from Code](spec-from-code-guide.md) | Onboarding existing projects with `purlin:spec-from-code` |

Key skills:

- `purlin:spec` -- create/edit specs
- `purlin:build` -- implement from spec rules
- `purlin:verify` -- run all tests, issue verification receipts
- `purlin:unit-test` -- run tests and emit proof files
- `purlin:audit` -- evaluate proof quality (STRONG/WEAK/HOLLOW)
- `purlin:status` -- show rule coverage via `sync_status`
- `purlin:drift` -- drift detection and change summary
- `purlin:spec-from-code` -- reverse-engineer specs from existing code
- `purlin:find` -- search specs by name
- `purlin:rename` -- rename a feature across specs, proofs, markers, and references
- `purlin:anchor` -- sync cross-cutting constraints from external sources
- `purlin:init` -- initialize and configure a project

## Hard Gate (only 1)

1. **Proof coverage** -- `purlin:verify` won't issue a receipt unless every rule has a passing proof.

Everything else is optional guidance.
