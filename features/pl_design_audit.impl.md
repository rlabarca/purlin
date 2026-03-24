# Implementation Notes: /pl-design-audit

*   **Helper Functions:** `parse_visual_spec()`, `validate_visual_references()`, `check_figma_staleness()`, `detect_design_conflicts()`, `detect_identity_tokens()` — all in `tools/test_pl_design_audit.py` (shared test helpers) and `tools/critic/critic.py` (production validators).
*   **Skill File:** `.claude/commands/pl-design-audit.md` — shared PM/Architect command.
*   **Test File:** `tools/test_pl_design_audit.py` — 12 test classes covering all unit scenarios.

### Audit Finding -- 2026-03-23

**[DISCOVERY] [ACKNOWLEDGED]** Missing Local Reference severity mismatch
**Source:** /pl-spec-code-audit --deep (M39)
**Severity:** MEDIUM
**Details:** Spec Section 2.3 says missing local files are reported as CRITICAL. Code in `validate_visual_references()` (critic.py) reports them as MEDIUM priority. The test asserts MEDIUM (matching code, contradicting spec).
**Suggested fix:** Change the priority in `validate_visual_references()` from MEDIUM to CRITICAL for missing local references. Update the test assertion to match.
