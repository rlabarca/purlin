# Mode-to-Sync Migration: Completed Context

## Status: IMPLEMENTED (v0.8.6)

This document records the design decisions from the mode-to-sync migration. It serves as context for the **Three-Bucket Model** plan (`PLAN-three-bucket-model.md`) which builds on top of this foundation.

## What Was Done

The mode system (Engineer/PM/QA role-based write guards) was replaced with a sync observation system:

- **Modes removed** — No more `purlin_mode()`, mode files, mode switching, or role-based write restrictions
- **Sync tracking added** — `sync-tracker.sh` (FileChanged hook) observes all writes, groups by feature
- **Sync ledger added** — `sync-ledger-update.sh` records per-feature sync status on commit
- **Write guard simplified** — Only blocks INVARIANT and UNKNOWN files (no role checks)
- **All skills unlocked** — Any user can invoke any skill (build, spec, verify, etc.)

## Key Design Decisions

### Why modes were removed
Modes enforced who could write what (Engineer→CODE, PM→SPEC, QA→QA). But this created friction for single users playing all roles, and didn't actually keep specs and code in sync — it just prevented writes.

### Why sync tracking replaced it
The real goal was always spec-code alignment, not access control. Sync tracking observes what changed and surfaces drift:
- `code_ahead` = code changed without spec update
- `spec_ahead` = spec changed without code
- `synced` = both updated together

### What the sync system tracks
- **Session state** (`.purlin/runtime/sync_state.json`) — ephemeral, per-session writes
- **Ledger** (`.purlin/sync_ledger.json`) — persistent, per-commit history
- **Merged view** — `get_sync_summary()` combines both for status

### How files map to features
- `features/<cat>/<stem>.md` → spec for `<stem>` (deterministic)
- `features/<cat>/<stem>.impl.md` → impl for `<stem>` (deterministic)
- `tests/<stem>/` → code for `<stem>` (convention)
- `skills/<name>/` → code for `purlin_<name>` (convention)
- Everything else → unclassified (no feature mapping)
- Commit scope fallback: `feat(stem):` → code for `<stem>` (ledger only)

### What remained unchanged
- INVARIANT protection (source-of-truth, not role-based)
- Companion files (.impl.md) as documentation artifacts
- File classification (CODE, SPEC, QA, INVARIANT, UNKNOWN)
- Worktree isolation (independent sync state per worktree)
- Parallel workers (branch isolation, not mode isolation)

## Relationship to Three-Bucket Model

The mode-to-sync migration removed role-based gating but left file writes completely open — any agent can edit any file without going through a skill. The **Three-Bucket Model** (`PLAN-three-bucket-model.md`) addresses this by:

1. **Adding skill-based write gating** — the write guard blocks writes unless a skill's `active_skill` marker is present
2. **Simplifying classification** — three buckets (Spec, Code, Other) instead of five categories
3. **Smart feature resolution** — `purlin:build` finds the right spec for code changes via reverse lookup
4. **Managed exceptions** — `purlin:classify` skill manages paths that are freely editable

The sync tracking infrastructure from this migration (sync_state.json, sync_ledger.json, sync-tracker.sh, sync-ledger-update.sh) remains unchanged and continues to power drift detection.

## User Flows (Reference)

These flows from the original migration remain valid. The three-bucket model adds a skill routing layer on top:

### PM pulls after engineer coded
1. PM runs `/status` → sees `code_ahead` per feature
2. PM runs `/whats-different` → sees changes grouped by SPEC, CODE, IMPL
3. PM reads `.impl.md` entries to understand what was built and why
4. PM updates spec or pushes back on deviations

### Engineer pulls after PM wrote specs
1. Engineer runs `/status` → sees `spec_ahead` or `new` features
2. Engineer runs `/whats-different engineer` → sees spec changes affecting code
3. Engineer invokes `purlin:build` → builds against updated spec

### Single user writes code and spec
1. User invokes `purlin:build` → writes code + impl
2. User invokes `purlin:spec` → updates spec
3. On commit: sync_status = `synced`

### Parallel workers
1. Dispatcher creates worktrees with independent sync tracking
2. Each worker operates in isolation (branch + sync state)
3. On merge back: main session picks up state from git
