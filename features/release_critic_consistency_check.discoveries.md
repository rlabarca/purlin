# Discovery Sidecar: release_critic_consistency_check

## [BUG] H13: Phase 2 README update not automated

- **Severity:** HIGH
- **Status:** RESOLVED
- **Action Required:** Engineer
- **Description:** Only Phase 1 detection exists; Phase 2 README update automation is absent. The `critic_consistency_check.py` script lacked any check for the `## The Critic` section in README.md.
- **Resolution:** Added `check_readme_critic_section()` function implementing Phase 2 verification: checks for presence of `## The Critic` heading, verifies ordering relative to `## The Agents` and `## Setup & Configuration`. Phase 2 runs only when Phase 1 has zero CRITICAL findings, matching the spec (Section 2.3). Added 3 test cases covering missing section, correct section, and Phase 2 skip on Phase 1 CRITICAL.

## [BUG] M45: Routing rule severity wrong

- **Severity:** MEDIUM
- **Status:** RESOLVED
- **Action Required:** Engineer
- **Description:** Code emits WARNING for routing rule inconsistencies, but the spec (Section 2.2 item 2, Scenario 3) says routing rule inconsistencies are CRITICAL findings.
- **Resolution:** Changed severity from `"WARNING"` to `"CRITICAL"` in `check_routing_consistency()`. Updated the routing test assertion to expect CRITICAL. Reworked the WARNING-level test to use Phase 2 README ordering warnings instead of routing inconsistency (since routing is now CRITICAL).
