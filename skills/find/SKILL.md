---
name: find
description: Search specs and surface sync-aware work discovery
---

Given the topic or concern provided as an argument, search the spec system and report findings. When invoked with no argument, show sync-aware work discovery.

## Work Discovery (no argument)

When invoked as `/find` with no topic argument, surface features needing attention based on sync state and QA status.

1. Read `.purlin/sync_ledger.json` for per-feature sync status.
2. Read scan results (via `purlin_scan`) for lifecycle, test status, regression status, and open discoveries.
3. Classify features into groups:

```
Features needing attention:

  NEW (spec exists, no code):
    - notification_system: spec written 2d ago
    - user_preferences: spec written 1d ago

  SPEC AHEAD (spec updated after code):
    - webhook_delivery: spec updated 3h ago, code 2d ago

  CODE AHEAD (code updated after spec):
    - auth_middleware: code 1d ago, no impl, spec 8d ago

  QA ATTENTION:
    - webhook_delivery: 1 OPEN discovery, regression PASS
    - auth_middleware: regression STALE (code changed since last run)
    - notification_system: no regression scenarios yet

  SYNCED (no action needed):
    - rate_limiting: all in sync, regression PASS, 0 discoveries
```

**Classification rules:**
- **NEW**: Feature has spec (lifecycle TODO), no `last_code_commit` in sync ledger
- **SPEC_AHEAD**: `sync_status: spec_ahead` in ledger, or `spec_modified_after_completion: true`
- **CODE_AHEAD**: `sync_status: code_ahead` in ledger
- **QA_ATTENTION**: Open discoveries, STALE/FAIL regression, or no regression scenarios for a feature with code
- **SYNCED**: `sync_status: synced` or `unknown` with no QA issues

## Topic Search (with argument)

When a topic or concern is provided, search the spec system and report findings.

### Search Protocol

1. **Feature specs:** Grep `features/**/*.md` (exclude `features/_tombstones/`, `features/_digests/`, `features/_design/`, `*.impl.md`, `*.discoveries.md`) for topic keywords. If found, read the matching file and identify the specific section and scenario.
2. **Anchor nodes:** Grep `features/**/arch_*.md`, `features/**/design_*.md`, `features/**/policy_*.md` for the topic. Anchor hits indicate governance-level coverage.
3. **Instruction files:** Grep `instructions/` and `CLAUDE.md` for the topic. Instruction-only hits mean the topic is a process/workflow rule without a feature spec.
4. **Companion files:** Grep `features/**/*.impl.md` for the topic. Companion hits may reveal implementation decisions or deviations related to the topic.

### Report Format

For each search result, report:
- **File** and **section** where the topic appears
- **Coverage type:** feature spec, anchor node, instruction, or companion

### Recommendation

Based on results, recommend one of:
- **Already covered** — feature spec + scenarios exist; no action needed
- **Spec refinement needed** — coverage exists but is incomplete or vague
- **Anchor node update** — the concern crosses features and belongs in an anchor
- **New spec needed** — no coverage found; suggest creating a feature spec via `purlin:spec`
