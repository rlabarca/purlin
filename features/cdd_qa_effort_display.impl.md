# Implementation Notes: CDD QA Effort Display

### Rendering Location
The QA column displays a single-line status badge per feature row. No sub-line, no tooltip. Detailed effort breakdowns are available via `status.sh --role <role>` (CLI). The `verification_effort` block in `critic.json` provides the data source but is not rendered on the dashboard.

### Design Decision -- 2026-03-23
Spec redesigned from two-line (badge + sub-line) to single-line (badge only). Rationale: agents get status from CLI, not dashboard; multi-line cells cause row height inconsistency; tooltips add UI complexity without agent benefit. The `_qa_badge_html()` function should be simplified to remove the `title=` attribute.

### Data Source
All effort data comes from the Critic's per-feature `critic.json` output. The dashboard reads this at page load and on each 5-second auto-refresh. No separate computation is needed in the frontend.

### Audit Finding -- 2026-03-16

[DISCOVERY] Scenario "Status JSON includes verification_effort" may lack explicit test match — **ACKNOWLEDGED**

**Source:** /pl-spec-code-audit --deep
**Severity:** MEDIUM
**Details:** The automated scenario asserting /status.json includes a verification_effort block could not be conclusively matched to a specific test function. Traceability may be coincidental keyword overlap.
**Suggested fix:** Verify that test_cdd.py or equivalent includes an explicit assertion for the verification_effort key in /status.json response. Add test if missing.
