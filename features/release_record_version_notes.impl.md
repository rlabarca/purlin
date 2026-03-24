# Implementation Notes: Record Version & Release Notes

This step is positioned last in Purlin's release checklist. Recording version notes after all verification steps ensures the notes reflect the actual final state of the release.

The `## Releases` section is a running log. New entries are prepended (most recent at top). The Architect does not delete or modify previous entries.

## Bug Fix: Prepend Order in agent_instructions (2026-03-24)

**[CLARIFICATION]** The `agent_instructions` field in `tools/release/global_steps.json` for `purlin.record_version_notes` step 6 originally said "Insert a new entry into README.md" without specifying prepend order. The spec (Section 2.5) requires: "New entries are prepended at the top of the `## Releases` section (most recent first)." Fixed step 6 to say "Prepend a new entry at the top of the '## Releases' section in README.md (most recent first)." (Severity: INFO)

**[DISCOVERY] [ACKNOWLEDGED]** The inline copy of agent_instructions in `features/release_checklist_core.md` Section 2.7 originally used the old "Insert" wording. That file is Architect-owned. The Architect has since updated it to "Prepend" — both the authoritative source (`tools/release/global_steps.json`) and the inline spec copy are now consistent. (Severity: HIGH — resolved)
