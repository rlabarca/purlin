# User Testing Discoveries: Release Step: Purlin Agent Instruction Audit

### [BUG] Agent does not halt or escalate on base-layer errors (Discovered: 2026-03-18)
- **Scenario:** Audit blocked by unresolvable base-layer conflict (Manual Scenario, Section 2.3)
- **Observed Behavior:** AFT agent interaction test (`instruction-audit-base-error` scenario) shows the agent correctly identifies a stale path in `BUILDER_BASE.md` (`tools/legacy_build_engine/`) but does NOT halt or signal escalation. It proceeds toward "fix and commit" behavior instead.
- **Expected Behavior:** Per Section 2.3 and the Manual Scenario: "The Architect halts the step and documents the base-layer conflict, And uses /pl-edit-base (Purlin repo) or reports to the framework maintainer (consumer project), And the release does not proceed until the conflict is resolved."
- **Root Cause:** The `agent_instructions` field in `tools/release/global_steps.json` for step `purlin.instruction_audit` reads: "Fix any inconsistencies and commit." It does not distinguish between override-fixable issues and base-layer errors that cannot be corrected via override. The agent follows the instructions literally and tries to fix everything.
- **Action Required:** Architect
- **Status:** OPEN
