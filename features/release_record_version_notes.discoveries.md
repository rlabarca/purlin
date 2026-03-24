# User Testing Discoveries: Release Record Version Notes

### [BUG] Prepend order missing from agent_instructions (Discovered: 2026-03-23)
- **Observed Behavior:** agent_instructions in global_steps.json says "insert" without specifying prepend.
- **Expected Behavior:** Spec Section 2.5 says entries are prepended (most recent first). agent_instructions should explicitly say "prepend" to match spec.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Updated agent_instructions step 6 in tools/release/global_steps.json from "Insert a new entry into README.md" to "Prepend a new entry at the top of the '## Releases' section in README.md (most recent first)".
- **Source:** Spec-code audit (LOW). See release_record_version_notes.impl.md for context.

### [DISCOVERY] Inline agent_instructions in release_checklist_core.md Section 2.7 still uses old "Insert" wording (Discovered: 2026-03-24)
- **Status:** RESOLVED
- **Resolution:** Updated release_checklist_core.md line 97 to say "Prepend" matching global_steps.json.
- **Action Required:** Architect
- **Description:** The inline copy of purlin.record_version_notes agent_instructions in features/release_checklist_core.md Section 2.7 (line 97) still uses the old wording "Insert a new entry into README.md" rather than the corrected "Prepend" wording. The authoritative source is tools/release/global_steps.json (which is now correct), but the spec's inline copy is stale.
