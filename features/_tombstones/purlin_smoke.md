# TOMBSTONE: purlin_smoke

**Retired:** 2026-03-31
**Reason:** Smoke tier management merged into `purlin:regression` as `promote` and `suggest` subcommands. Smoke is a tier of regression testing, not a separate skill.

## Files to Delete

- `skills/smoke/SKILL.md` — the smoke skill definition
- `features/skills_qa/purlin_smoke.md` — the smoke skill spec
- `features/skills_qa/purlin_smoke.impl.md` (if exists)

## Dependencies to Check

- `skills/verify/SKILL.md` — references smoke gate in Step 2 (smoke gate logic unchanged, just the skill reference updates)
- `skills/status/SKILL.md` — displays smoke_candidates (unchanged, data comes from scan engine)
- `scripts/smoke/smoke.py` — implementation stays, called by regression skill now
- `scripts/mcp/scan_engine.py` — smoke_candidates output unchanged

## Context

The `purlin:smoke` skill had two subcommands: `<feature>` (promote to smoke tier) and `suggest` (recommend candidates). These are now `purlin:regression promote <feature>` and `purlin:regression suggest`. The smoke gate behavior in `purlin:verify` and the smoke ordering in regression execution are unchanged — only the entry point moved.
