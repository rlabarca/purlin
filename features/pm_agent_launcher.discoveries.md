# User Testing Discoveries: PM Agent Launcher

### [BUG] M51: PM non-bypass allowedTools missing Write and Edit (Discovered: 2026-03-23)
- **Observed Behavior:** PM agent's non-bypass allowedTools list does not include Write and Edit tools.
- **Expected Behavior:** Spec includes Write and Edit in the PM non-bypass allowedTools list.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See pm_agent_launcher.impl.md for full context.
