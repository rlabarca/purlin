# Sync Tracking Guide

How Purlin watches what you change and surfaces drift — without blocking you.

---

## Why Sync Tracking Exists

Previous versions of Purlin used a mode system: PM could only write specs, Engineer could only write code, QA could only write test artifacts. This prevented accidental cross-role writes but added friction — you had to switch modes constantly.

Sync tracking replaces that enforcement model. Everyone can write any file type. Purlin watches what changes and tells you when specs and code have drifted apart. It's information, not enforcement.

---

## Two Layers

Sync tracking has two data stores that work together.

### Session Layer (Ephemeral)

**File:** `.purlin/runtime/sync_state.json` (gitignored)

Tracks every file write in the current session. The `sync-tracker.sh` FileChanged hook fires on each write, classifies the file, and maps it to a feature.

Per-feature, it records:
- Which code files were written
- Which test files were written
- Whether the spec was updated
- Whether the companion file (`.impl.md`) was updated

Session state is cleared on every session start. It captures uncommitted, in-progress work.

### Committed Ledger (Persistent)

**File:** `.purlin/sync_ledger.json` (committed to git)

Updated automatically on every commit by `sync-ledger-update.sh`. For each feature touched by the commit, it records:
- Last code commit SHA and timestamp
- Last spec commit SHA and timestamp
- Last companion file commit SHA and timestamp
- Computed `sync_status`

The ledger is the cross-session source of truth. It survives context clears, terminal restarts, and worktree merges.

---

## Sync Status

Each feature gets a sync status based on what changed:

| Code changed | Spec changed | Companion changed | Status |
|---|---|---|---|
| Yes | No | No | `code_ahead` |
| Yes | No | Yes | `synced` |
| Yes | Yes | — | `synced` |
| No | Yes | No | `spec_ahead` |
| — | — | — | `new` |

**`code_ahead`** is the most common drift state. It means code was committed but the companion file wasn't updated. This is advisory — it surfaces as an Engineer action item in `purlin:status`, not a blocker.

**`spec_ahead`** means the spec was updated but no code changes followed. This surfaces as an Engineer action item suggesting the code needs to catch up.

**`synced`** means both sides are up to date — either both changed together, or code changed with a companion file documenting it.

---

## How `purlin:status` Uses Sync Data

Status classification happens server-side in the MCP tool. When you run `purlin:status`:

1. The MCP server runs a full scan internally (features, tests, discoveries, deviations, git state).
2. Reads the committed ledger and overlays session state.
3. Classifies everything into role-based work items (Engineer, QA, PM) with priority sorting.
4. Returns only the classified summary — the raw feature array never enters the conversation.

You can scope by role: `purlin:status pm` returns only PM work items. This is fast and focused.

Features with `code_ahead` sync status appear as engineer advisories with a hint to run `purlin:spec-code-audit`. Features with `spec_ahead` appear as PM items. Per-feature sync details (timestamps, drift direction) are included for actionable entries.

---

## What Gets Tracked (and What Doesn't)

**Tracked:**
- CODE files (`src/`, `scripts/`, `tests/`, `agents/`, `hooks/`, config)
- SPEC files (`features/**/*.md`, excluding `.impl.md` and `.discoveries.md`)
- Companion files (`*.impl.md`)

**Not tracked:**
- INVARIANT files (`features/_invariants/`) — blocked by write guard
- QA artifacts (`.discoveries.md`, regression JSON) — separate lifecycle
- Internal files (`.purlin/`, `.claude/`, `__pycache__/`, lock files)

---

## Only Two Hard Blocks

The write guard blocks exactly two file types:

| Classification | Blocked | What to Do |
|---|---|---|
| **INVARIANT** | Yes | Use `purlin:invariant sync` to update from the external source |
| **UNKNOWN** | Yes | Add a classification rule to CLAUDE.md |

Everything else — CODE, SPEC, QA — is writable by anyone, anytime. The write guard auto-approves these with no prompt.

---

## Worktrees and Parallel Agents

Each worktree has independent sync data:
- **Session state** is per-worktree (`.purlin/runtime/sync_state.json` is gitignored, scoped to the working directory).
- **Ledger** is per-branch (`.purlin/sync_ledger.json` is updated by commits on that branch).

When a worktree merges back to main, the main session picks up the merged ledger entries on the next `purlin:status` call.

Parallel workers on different features produce clean, independent ledger entries. Workers on the same feature would produce merge conflicts — the prerequisite graph prevents this by never scheduling the same feature in parallel.

---

## Reconciling Drift

When `purlin:status` shows features with `code_ahead` status:

| Situation | What to Do |
|---|---|
| One feature behind | Write companion entries manually (`[IMPL]` tag) |
| Multiple features behind | `purlin:spec-code-audit` — bulk reconciliation |
| Spec needs to change | `purlin:propose` — suggest a spec update to PM |
| Code should match spec exactly | Write `[IMPL]` entries confirming alignment |

See the [Spec-Code Sync Guide](spec-code-sync-guide.md) for companion file format, decision tags, and the Active Deviations table.

---

## Quick Reference

| You want to... | What to do |
|---|---|
| Check sync status | `purlin:status` (all roles) or `purlin:status engineer` |
| See what changed since last session | `purlin:whats-different` |
| See what changed, PM-focused | `purlin:whats-different pm` |
| Reconcile companion debt | `purlin:spec-code-audit` |
| Understand why a feature shows `code_ahead` | Read the ledger: code committed without companion file update |
| Clear session state | Starts fresh every session automatically |
