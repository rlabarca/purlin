# User Testing Discoveries: Context Recovery Hook

### [DISCOVERY] M47: CLAUDE.md installation scenarios absent (Discovered: 2026-03-23)
- **Observed Behavior:** All 7 test cases from spec section 2.6 are missing from test_init.sh; CLAUDE.md installation paths are untested.
- **Expected Behavior:** test_init.sh should include all 7 CLAUDE.md installation scenarios defined in spec section 2.6.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See context_recovery_hook.impl.md for full context.

### [BUG] M48: Refresh path missing git add CLAUDE.md (Discovered: 2026-03-23)
- **Observed Behavior:** The full init path stages CLAUDE.md with `git add`, but the refresh path does not; CLAUDE.md changes from refresh are left unstaged.
- **Expected Behavior:** The refresh path should also run `git add CLAUDE.md` to stage changes, matching the full init behavior.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See context_recovery_hook.impl.md for full context.
