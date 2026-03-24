# Implementation Notes: Critic Consistency Check & README Update

This step is positioned immediately after `doc_consistency_framework` in Purlin's release config. The broader instruction-file consistency check runs first; this step then focuses narrowly on the Critic subsystem.

Phase 2 (README update) runs only after Phase 1 produces zero CRITICAL findings. A clean audit is a prerequisite for README publication.

### Audit Finding -- 2026-03-23

**[DISCOVERY] [ACKNOWLEDGED]** Phase 2 (README update) not automated
**Source:** /pl-spec-code-audit --deep (H13)
**Severity:** HIGH
**Details:** The "Clean audit -- README updated" scenario is tagged auto-test-only but Phase 2 (write/update `## The Critic` section in README.md and commit) has no code. `critic_consistency_check.py` implements only Phase 1 (detection). The test only verifies Phase 1 JSON output. Phase 2 is entirely agent-side behavior with no automated coverage.
**Suggested fix:** Either add Phase 2 automation to `critic_consistency_check.py` (generate README section text) or reclassify the scenario as @manual since it requires agent judgment for README prose.
**[DISCOVERY] [ACKNOWLEDGED]** Routing rule severity should be CRITICAL not WARNING
**Source:** /pl-spec-code-audit --deep (M45)
**Severity:** MEDIUM
**Details:** Spec §3 scenario says routing inconsistencies are CRITICAL and halt the release. Code at `critic_consistency_check.py:128-136` emits WARNING. Test asserts WARNING (matches code, contradicts spec).
**Suggested fix:** Change the severity from WARNING to CRITICAL in `check_routing_consistency()`. Update the test assertion to match.
