# User Testing Discoveries: PL Update Purlin

### [BUG] M16: Skill file missing PURLIN_PROJECT_ROOT (Discovered: 2026-03-23)
- **Observed Behavior:** The skill file has no reference to PURLIN_PROJECT_ROOT.
- **Expected Behavior:** Spec section 2.13 requires PURLIN_PROJECT_ROOT to be referenced in the skill file for correct path resolution.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Added a "Path Resolution" section to `.claude/commands/pl-update-purlin.md` that instructs the agent to use `PURLIN_PROJECT_ROOT` env var as the primary project root detection mechanism, with directory-climbing as fallback. Added 4 tests to `tests/pl_update_purlin/test_command.py` verifying presence and placement.
- **Source:** Spec-code audit (deep mode). See pl_update_purlin.impl.md for full context.
