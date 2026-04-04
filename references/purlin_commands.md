# Purlin Commands

> 12 skills, no modes, no permission system.

```
Purlin — Spec-Driven Development
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Authoring
  ──────
  purlin:spec <name>            Scaffold or edit a feature spec (3-section format)
  purlin:spec-from-code [dir]   Reverse-engineer specs from existing code
  purlin:find [name]            Search specs by name, show coverage

  Building
  ──────
  purlin:build [name]           Inject spec rules into context, then implement
  purlin:unit-test [feature]    Run tests, emit proof files, report coverage
  purlin:verify                 Run ALL tests, issue verification receipts
  purlin:verify --audit         Clean-room re-execution, compare vhash to receipts
  purlin:verify --manual <f> <P>  Stamp a manual proof

  Quality
  ──────
  purlin:audit [feature]        Evaluate proof quality (STRONG/WEAK/HOLLOW)
  purlin:audit --criteria <f>   Use a specific criteria file

  Reporting
  ──────
  purlin:status                 Show rule coverage via sync_status (with → directives)
  purlin:drift [pm|eng|qa] [--since N]
                                Detect spec drift, summarize changes since last verify

  Project
  ──────
  purlin:init                   Initialize project (.purlin/, specs/, proof plugin)
  purlin:init --add-plugin <src> Install a proof plugin from a file path or git URL
  purlin:init --list-plugins    List installed proof plugins
  purlin:rename <old> <new>     Rename feature across all Purlin artifacts
  purlin:anchor <cmd>           Sync read-only constraints from external sources
  purlin:init --sync-audit-criteria
                                Sync external audit criteria to latest version

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Quick Reference

| Skill | Purpose | Writes |
|-------|---------|--------|
| `purlin:spec` | Create/edit specs | `specs/<category>/<name>.md` |
| `purlin:build` | Implement from spec rules | Code files + test files |
| `purlin:verify` | Run all tests, issue receipts | `*.receipt.json` next to specs |
| `purlin:unit-test` | Run tests, emit proofs | `*.proofs-*.json` next to specs |
| `purlin:audit` | Evaluate proof quality | Nothing (read-only) |
| `purlin:status` | Show coverage + directives | Nothing (read-only) |
| `purlin:drift` | Drift detection since last verify | Nothing (read-only) |
| `purlin:init` | Initialize project | `.purlin/`, `specs/`, proof plugin |
| `purlin:anchor` | Sync external constraints | `specs/_anchors/*.md` |
| `purlin:find` | Search specs | Nothing (read-only) |
| `purlin:rename` | Rename feature | Specs, proofs, markers, references |
| `purlin:spec-from-code` | Generate specs from code | `specs/<category>/<name>.md` |
