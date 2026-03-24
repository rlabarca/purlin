# User Testing Discoveries: PL Help

### [BUG] H14: Skill contradicts spec on --help (Discovered: 2026-03-23)
- **Observed Behavior:** Skill says "Do NOT run scripts" when processing --help requests.
- **Expected Behavior:** Spec requires executing each script with --help to retrieve actual help output.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See pl_help.impl.md for full context.
