# Discovery Sidecar: pl_design_audit

## [BUG] M39: Missing Local Reference severity
- **Status:** RESOLVED
- **Action Required:** Engineer
- **Description:** Code produces MEDIUM severity for missing local reference violations. Spec says missing local reference violations should be CRITICAL severity (Section 2.3).
- **Resolution:** Changed priority from MEDIUM to CRITICAL in `scripts/critic/critic.py` (`validate_visual_references`). Updated assertions in `scripts/test_pl_design_audit.py` and `scripts/critic/test_critic.py` to expect CRITICAL.
