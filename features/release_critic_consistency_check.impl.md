# Implementation Notes: Critic Consistency Check & README Update

This step is positioned immediately after `doc_consistency_framework` in Purlin's release config. The broader instruction-file consistency check runs first; this step then focuses narrowly on the Critic subsystem.

Phase 2 (README update) runs only after Phase 1 produces zero CRITICAL findings. A clean audit is a prerequisite for README publication.

**[DISCOVERY] [ACKNOWLEDGED]** Routing rule severity should be CRITICAL not WARNING
**Source:** /pl-spec-code-audit --deep (M45)
**Severity:** MEDIUM
**Details:** Spec §3 scenario says routing inconsistencies are CRITICAL and halt the release. Code at `critic_consistency_check.py:128-136` emits WARNING. Test asserts WARNING (matches code, contradicts spec).
**Suggested fix:** Change the severity from WARNING to CRITICAL in `check_routing_consistency()`. Update the test assertion to match.
