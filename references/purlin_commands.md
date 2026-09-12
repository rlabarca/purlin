# Purlin Commands

> 12 skills, no permission system. The only mode is `purlin:audit`, and it derives that from what exists rather than asking.

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
  purlin:test [feature]         Run tests, emit proof files, report coverage
  purlin:test --all             Run all tiers, including the remote path
  purlin:test --local           Skip the remote path; report platform-scoped proofs as awaiting
  purlin:test --platform <id>   Target one platform: run it here, or dispatch just its runner
  purlin:verify                 Run ALL tests, issue verification receipts
  purlin:verify --recheck         Clean-room re-execution, compare vhash to receipts
  purlin:verify --manual <f> <P>  Stamp a manual proof

  Quality
  ──────
  purlin:audit [feature]        Evaluate proof quality — mode derived from state
  purlin:audit --design         Proof Design only: PROVABLE/LOOSE/UNPROVABLE
                                (specs only — no tests needed)
  purlin:audit --integrity      Proof Integrity only: STRONG/WEAK/HOLLOW
  purlin:audit --criteria <f>   Use a specific criteria file

  Reporting
  ──────
  purlin:status                 Show rule coverage via sync_status (with → directives)
  purlin:drift [pm|eng|qa] [--since N]
                                Detect spec drift, summarize changes since last verify

  Project
  ──────
  purlin:init                   Initialize project (.purlin/, specs/, proof plugin)
  purlin:init --update          Bring the project up to the installed plugin
  purlin:init --update --check  Report pending migrations; write nothing
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
| `purlin:test` | Run tests, emit proofs | `*.proofs-*.json` next to specs |
| `purlin:audit` | Evaluate proof quality (both gauges) | Audit and design caches |
| `purlin:status` | Show coverage + directives | Nothing (read-only) |
| `purlin:drift` | Drift detection since last verify | Nothing (read-only) |
| `purlin:init` | Initialize project | `.purlin/`, `specs/`, proof plugin |
| `purlin:init --update` | Migrate the project to the installed plugin | Specs, proof filenames, markers, plugin copies, config |
| `purlin:anchor` | Sync external constraints | `specs/_anchors/*.md` |
| `purlin:find` | Search specs | Nothing (read-only) |
| `purlin:rename` | Rename feature | Specs, proofs, markers, references |
| `purlin:spec-from-code` | Generate specs from code | `specs/<category>/<name>.md` |

## Pending migrations

When `sync_status` opens with a pending-migrations advisory, stop before doing the skill's work,
print the advisory and its directive, and ask whether to run `purlin:init --update` now.
`purlin:verify` does not issue receipts while a `legacy-*` migration is pending, because the
legacy alias makes coverage a guess; that is a warning and a refusal to claim, not a gate.

Skills that display `sync_status` output (`purlin:status`, `purlin:test`, `purlin:build`,
`purlin:verify`, `purlin:drift`) see the advisory by construction. The skills that do not call
`sync_status` call it first when they would write specs or proofs, for the same reason: a spec
written against a legacy alias is written against a reading the next release drops.

The advisory names one migration per line with its count and the files it counted, and ends with
`→ Run: purlin:init --update`. `purlin:init --update --check` prints the same list as JSON and
writes nothing, which is what a CI preflight runs.
