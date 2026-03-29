# Active Deviations Protocol

> Referenced by PURLIN_BASE.md spec ownership model and by purlin:build.

## Companion File Format

Companion files (`features/<category_slug>/<name>.impl.md`) use a structured Active Deviations table at the top:

```markdown
# Implementation Notes: [Feature Name]

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| Batch all notifications | Batches in groups of 500 | INFEASIBLE | PENDING |
| (silent on priority) | Defaults to NORMAL | DISCOVERY | PENDING |

## [existing prose sections below]
```

## Decision Hierarchy

When implementing in Engineer mode:

1. Read the spec (PM intent / baseline)
2. Read Active Deviations table (Engineer overrides where they exist)
3. For each requirement:
   - No deviation → follow the spec exactly
   - Deviation with `PENDING` → follow the deviation (provisional)
   - Deviation with `ACCEPTED` → follow the deviation (PM ratified)
   - Deviation with `REJECTED` → follow the spec (PM overruled)

## Three Engineer-to-PM Flows

### Flow 1: INFEASIBLE (blocking)

Engineer hits a wall. Cannot implement as written. Halts work on that requirement, documents why, proposes alternative. Use `purlin:infeasible`.

### Flow 2: Inline Deviation (non-blocking)

Engineer makes decisions during build: interprets ambiguity, chooses different approach, finds uncovered behavior. Build continues. Add row to Active Deviations table with PM status `PENDING`.

### Flow 3: SPEC_PROPOSAL (proactive)

Engineer is not building. They want to suggest a spec change or new feature. Writes a `[SPEC_PROPOSAL]` to companion file. Use `purlin:propose`.

## Engineer Decision Tags

Use these in companion files:

| Tag | Severity | Meaning | PM review? |
|-----|----------|---------|------------|
| `[IMPL]` | NONE | Implemented as specced | No |
| `[CLARIFICATION]` | INFO | Interpreted ambiguous spec language | No |
| `[AUTONOMOUS]` | WARN | Spec was silent; Engineer filled the gap | Yes |
| `[DEVIATION]` | HIGH | Intentionally diverged from spec | Yes |
| `[DISCOVERY]` | HIGH | Found unstated requirement | Yes |
| `[INFEASIBLE]` | CRITICAL | Cannot implement as specced | Yes |

Format: `**[TAG]** <description> (Severity: <level>)` — severity line omitted for `[IMPL]` since severity is NONE.

`[IMPL]` is the low-friction tag for work that matches the spec. It does NOT appear in the Active Deviations table, is NOT surfaced by the scan as a PM action item, and does NOT require PM acknowledgment. Per `features/policy_spec_code_sync.md`, every code commit must have at least an `[IMPL]` entry in the companion file.

Cross-feature discoveries go in the **target feature's** companion file, not the originating feature.

## PM Review

PM reviews unacknowledged entries via `purlin:status` (scan.py surfaces them). For each entry, PM either:
- Marks `[ACKNOWLEDGED]` and accepts the deviation
- Marks `[ACKNOWLEDGED]` and rejects (updates spec to override)
- Requests clarification from Engineer
