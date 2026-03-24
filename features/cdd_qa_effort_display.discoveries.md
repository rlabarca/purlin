# User Testing Discoveries: CDD QA Effort Display

### [BUG] M38: verification_effort test traceability (Discovered: 2026-03-23)
- **Observed Behavior:** No explicit test exists for the /status.json `verification_effort` field.
- **Expected Behavior:** A dedicated test should verify that the `verification_effort` field is correctly populated in the /status.json response.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See cdd_qa_effort_display.impl.md for full context.
