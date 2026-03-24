# User Testing Discoveries: CDD QA Effort Display

### [BUG] M38: verification_effort test traceability (Discovered: 2026-03-23)
- **Observed Behavior:** No explicit test exists for the /status.json `verification_effort` field.
- **Expected Behavior:** A dedicated test should verify that the `verification_effort` field is correctly populated in the /status.json response.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Added `TestApiStatusJsonVerificationEffort` class in `tools/cdd/test_cdd.py` with three end-to-end tests exercising `generate_api_status_json()`: (1) verification_effort is included when present in critic.json, (2) verification_effort is omitted when absent, (3) auto-resolvable features carry the effort data through the API.
- **Source:** Spec-code audit (deep mode). See cdd_qa_effort_display.impl.md for full context.
