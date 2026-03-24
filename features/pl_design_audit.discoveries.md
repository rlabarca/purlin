# Discovery Sidecar: pl_design_audit

## [BUG] M39: Missing Local Reference severity
- **Status:** RESOLVED
- **Action Required:** Builder
- **Description:** Code produces MEDIUM severity for missing local reference violations. Spec says missing local reference violations should be CRITICAL severity (Section 2.3).
- **Resolution:** Changed priority from MEDIUM to CRITICAL in `tools/critic/critic.py` (`validate_visual_references`). Updated assertions in `tools/test_pl_design_audit.py` and `tools/critic/test_critic.py` to expect CRITICAL.
