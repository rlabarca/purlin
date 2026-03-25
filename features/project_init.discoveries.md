# User Testing Discoveries: Project Init

### [BUG] --preflight-only flag should be removed from init.sh (Discovered: 2026-03-23)
- **Observed Behavior:** Code has undocumented --preflight-only flag at lines 17, 105-108.
- **Expected Behavior:** Spec does not include a --preflight-only flag. The flag should be removed.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See project_init.impl.md for context.
