# TOMBSTONE: purlin_smoke

**Retired:** 2026-03-31
**Reason:** Smoke tier management merged into `purlin:regression` as `promote` and `suggest` subcommands. Smoke is a tier of regression testing, not a separate skill.

## Files Deleted

- `skills/smoke/SKILL.md` — the smoke skill definition
- `features/skills_qa/purlin_smoke.md` — the smoke skill spec
- `features/skills_qa/purlin_smoke.impl.md` (if exists)
- `scripts/smoke/smoke.py` — standalone module eliminated; suggestion logic inlined into `scripts/mcp/scan_engine.py` `_scan_smoke_candidates()`. Tier table writes (`add_to_tier_table`) and smoke regression creation (`create_smoke_regression`) are handled by `purlin:regression promote` skill prose against config.json and scenario JSON directly. `check_smoke_gate` was dead code (verify skill Step 2 implements the gate in prose). `order_verification` and `read_tier_table` removed — unused.
- `scripts/smoke/__init__.py` — package scaffolding

## Dependencies Updated

- `scripts/mcp/scan_engine.py` — `smoke_candidates` output unchanged; suggestion logic now self-contained (no cross-module import)
- `skills/verify/SKILL.md` — references smoke gate in Step 2 (unchanged, gate logic is skill prose)
- `skills/status/SKILL.md` — displays smoke_candidates (unchanged, data comes from scan engine)

## Context

The `purlin:smoke` skill had two subcommands: `<feature>` (promote to smoke tier) and `suggest` (recommend candidates). These are now `purlin:regression promote <feature>` and `purlin:regression suggest`. The smoke gate behavior in `purlin:verify` and the smoke ordering in regression execution are unchanged — only the entry point moved. The `scripts/smoke/smoke.py` module was eliminated because its only runtime consumer was `scan_engine.py` (one function), and the remaining functions were either dead code or simple config.json writes that the regression skill handles directly.
