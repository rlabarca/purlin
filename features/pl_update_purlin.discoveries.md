# User Testing Discoveries: PL Update Purlin

### [BUG] M16: Skill file missing PURLIN_PROJECT_ROOT (Discovered: 2026-03-23)
- **Observed Behavior:** The skill file has no reference to PURLIN_PROJECT_ROOT.
- **Expected Behavior:** Spec section 2.13 requires PURLIN_PROJECT_ROOT to be referenced in the skill file for correct path resolution.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Added a "Path Resolution" section to `.claude/commands/pl-update-purlin.md` that instructs the agent to use `PURLIN_PROJECT_ROOT` env var as the primary project root detection mechanism, with directory-climbing as fallback. Added 4 tests to `tests/pl_update_purlin/test_command.py` verifying presence and placement.
- **Source:** Spec-code audit (deep mode). See pl_update_purlin.impl.md for full context.

### [BUG] Code uses "categories" where spec says "dimensions" for go-deeper grouping (Discovered: 2026-03-23)
- **Observed Behavior:** Code and tests use "categories" terminology for go-deeper grouping.
- **Expected Behavior:** Spec uses "dimensions" terminology. Code and tests should align to spec terminology "dimensions".
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See pl_update_purlin.impl.md for context.

### [BUG] Skill file missing stale artifact decline and skip behaviors (Discovered: 2026-03-23)
- **Observed Behavior:** Skill file does not implement decline or skip behaviors for stale artifacts.
- **Expected Behavior:** Spec Section 2.10 requires: print "Stale files preserved." on decline, skip step entirely if none found. Both absent from skill file.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See pl_update_purlin.impl.md for context.
