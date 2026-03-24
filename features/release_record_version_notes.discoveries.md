# User Testing Discoveries: Release Record Version Notes

### [BUG] Prepend order missing from agent_instructions (Discovered: 2026-03-23)
- **Observed Behavior:** agent_instructions in global_steps.json says "insert" without specifying prepend.
- **Expected Behavior:** Spec Section 2.5 says entries are prepended (most recent first). agent_instructions should explicitly say "prepend" to match spec.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (LOW). See release_record_version_notes.impl.md for context.
