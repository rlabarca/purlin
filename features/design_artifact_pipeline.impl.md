# Implementation Notes: Design Artifact Pipeline

## Review: Spec Revision f383f70 (2026-03-16)

Two additions to the anchor:

1. **Token Map validation mandate** (Section "Token Map Format"): "Token mappings MUST validate against the declared design anchor's token definitions. Invalid mappings are flagged by the Critic as PM action items."

2. **Cross-reference to canonical tokens** (Section "Design Anchor Declaration"): Points to `features/design_visual_standards.md` Section 2.2 for the canonical token definitions that Token Maps validate against.

### [DISCOVERY: Critic token validation is presence-only]

The Critic (`tools/critic/critic.py`, `validate_visual_references()`) currently checks only whether a Token Map **exists** (non-empty) for each screen reference. It does NOT parse token content or validate individual mappings against the design anchor's token definitions.

The new spec language says "Invalid mappings are flagged by the Critic as PM action items" — this implies content-level validation that does not yet exist. The Critic feature (`features/critic_tool.md` or `features/critic_role_status.md`) would need to be updated to implement this constraint.

**Impact:** LOW — no existing consumer projects rely on content-level Token Map validation yet. The presence check still catches the most common error (missing Token Map entirely). Content validation is an enhancement for the Critic feature.

**Architect Acknowledgment (2026-03-19):** Acknowledged. The current presence-only validation is acceptable for now. Content-level Token Map validation (parsing individual mappings and validating against the design anchor's token definitions) is a future Critic enhancement. The spec language in `design_artifact_pipeline.md` ("Invalid mappings are flagged by the Critic as PM action items") describes the target state, not the current state. No spec change needed -- the spec is aspirational and the Builder will implement content validation when the Critic feature is next updated.
