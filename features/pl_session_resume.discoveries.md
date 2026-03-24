# User Testing Discoveries: PL Session Resume

### [BUG] Checkpoint format missing spec fields (Discovered: 2026-03-23)
- **Observed Behavior:** Parallel B1 State (Builder) and Regression Authoring + Last Authored Feature (QA) are in the skill but not the spec.
- **Expected Behavior:** These fields should be documented in spec Section 2.2.2 (Builder checkpoint) and Section 2.2.3 (QA checkpoint).
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (LOW). See pl_session_resume.impl.md for context.
