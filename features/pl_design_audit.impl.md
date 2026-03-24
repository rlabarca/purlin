# Implementation Notes: /pl-design-audit

**[DISCOVERY]** Missing Local Reference severity mismatch
**Source:** /pl-spec-code-audit --deep (M39)
**Severity:** MEDIUM
**Details:** Spec Section 2.3 says missing local files are reported as CRITICAL. Code in `validate_visual_references()` (critic.py) reports them as MEDIUM priority. The test asserts MEDIUM (matching code, contradicting spec).
**Suggested fix:** Change the priority in `validate_visual_references()` from MEDIUM to CRITICAL for missing local references. Update the test assertion to match.
