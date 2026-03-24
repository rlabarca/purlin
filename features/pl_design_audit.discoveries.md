# User Testing Discoveries: PL Design Audit

### [BUG] M39: Missing Local Reference severity (Discovered: 2026-03-23)
- **Observed Behavior:** Code produces MEDIUM severity for missing local reference violations.
- **Expected Behavior:** Spec says missing local reference violations should be CRITICAL severity.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See pl_design_audit.impl.md for full context.
