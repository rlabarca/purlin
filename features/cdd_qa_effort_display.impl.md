# Implementation Notes: CDD QA Effort Display

### Rendering Location
The QA effort breakdown renders inline within each feature row on the CDD Dashboard, below the QA status column. It displays the effort classification computed by the Critic's `verification_effort` block in `tests/<feature>/critic.json`.

### Data Source
All effort data comes from the Critic's per-feature `critic.json` output. The dashboard reads this at page load and on each 5-second auto-refresh. No separate computation is needed in the frontend.

### Audit Finding -- 2026-03-16

[DISCOVERY] Scenario "Status JSON includes verification_effort" may lack explicit test match — **ACKNOWLEDGED**

**Source:** /pl-spec-code-audit --deep
**Severity:** MEDIUM
**Details:** The automated scenario asserting /status.json includes a verification_effort block could not be conclusively matched to a specific test function. Traceability may be coincidental keyword overlap.
**Suggested fix:** Verify that test_cdd.py or equivalent includes an explicit assertion for the verification_effort key in /status.json response. Add test if missing.
