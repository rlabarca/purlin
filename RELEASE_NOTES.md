# Release Notes

## v2.0.0 — Rule-Proof Runtime

Complete redesign. Purlin v2 replaces the v1 system (35 skills, 5 agents, 8 hooks, 8 MCP tools) with a minimal rule-proof runtime.

### What Changed

**Specs:** 3-section format (`## What it does`, `## Rules`, `## Proof`). Specs live in `specs/<category>/<name>.md`. Rules are numbered (`RULE-N`), proofs map to rules (`PROOF-N (RULE-N)`).

**Proofs:** Test runners emit `*.proofs-*.json` files next to specs. Proof markers in tests: `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")` for pytest, `[proof:feature:PROOF-1:RULE-1:tier]` in Jest test titles, `purlin_proof()` for shell.

**Coverage:** `sync_status` MCP tool reads specs and proof files, diffs them, reports coverage with `→` directives that tell the agent exactly what to do.

**Verification:** `purlin:verify` runs all tests, issues receipts for features with 100% rule coverage. `vhash = sha256(sorted RULE IDs + sorted proof IDs/statuses)`.

**Skills:** 12 skills (down from 35). All optional — no skill invocation required to write any file.

**Hard gates:** 2 (down from 8). Invariant write protection + proof coverage for receipts.

**MCP tools:** 2 (`sync_status`, `purlin_config`).

**Hooks:** 2 (`PreToolUse` gate for invariants, `SessionStart` for cleanup).

### Migration from v1

v2 is a clean break. Key differences:

| v1 | v2 |
|----|-----|
| `features/<category>/<name>.md` | `specs/<category>/<name>.md` |
| Scenarios (Given/When/Then) | Rules (RULE-N) + Proofs (PROOF-N) |
| `tests/<feature>/tests.json` | `specs/<category>/<feature>.proofs-<tier>.json` |
| 3 modes (PM, Engineer, QA) | 1 agent, no modes |
| `purlin_scan` + `purlin_status` | `sync_status` |
| Role-based permissions | No permissions (skills are optional) |
| 35 skills | 12 skills |
| Write guard with file classifications | Gate hook for invariants only |

### New in v2

- **Invariants with external sources:** `> Source:` + `> Pinned:` metadata. Git-sourced and Figma-sourced. Auto-sync with `purlin:invariant sync`.
- **Manual proof stamps:** `@manual(email, date, commit_sha)` in spec's `## Proof` section. Staleness detection via `> Scope:` file tracking.
- **Verification receipts:** `*.receipt.json` files with `vhash` and commit SHA. `--audit` mode for CI.
- **Feature-scoped proof overwrite:** Each test run replaces only its feature's entries in the proof file, preserving others.
