# Implementation Notes: /pl-design-audit

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (see prose) | [ACKNOWLEDGED]** Missing Local Reference severity mismatch | DISCOVERY | PENDING |

*   **Helper Functions:** `parse_visual_spec()`, `validate_visual_references()`, `check_figma_staleness()`, `detect_design_conflicts()`, `detect_identity_tokens()` — in `tools/test_pl_design_audit.py` (shared test helpers). Production validators formerly in `tools/critic/critic.py` were deleted with the Critic system.
*   **Skill File:** `.claude/commands/pl-design-audit.md` — shared PM command.
*   **Test File:** `tools/test_pl_design_audit.py` — 12 test classes covering all unit scenarios.

### Audit Finding -- 2026-03-23

**[DISCOVERY] [ACKNOWLEDGED]** Missing Local Reference severity mismatch. **RESOLVED:** The production validator (`critic.py`) was deleted with the Critic system. When re-implementing validation, use CRITICAL severity per spec Section 2.3.
