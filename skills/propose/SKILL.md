---
name: propose
description: Surface structured spec change proposals from implementation experience
---

## Active Skill Marker

Before any file writes, set the active skill marker:

```bash
mkdir -p .purlin/runtime && echo "propose" > .purlin/runtime/active_skill
```

After all writes are complete (final commit), clear it:

```bash
rm -f .purlin/runtime/active_skill
```

---

Given the topic provided as an argument, surface a structured spec change suggestion for PM review:

1. Search the current spec system for the relevant feature or anchor node.
2. Describe the gap, inconsistency, or improvement you encountered during implementation.
3. Draft a concrete proposal: what should change in the spec (section, scenario, or constraint).
4. **Constraint check:** Call `purlin_constraints` for the feature. If the proposal would conflict with a FORBIDDEN pattern or contradict an invariant statement, flag it in the proposal entry: `[CONSTRAINT WARNING: conflicts with <constraint_file> INV-N]`. This helps PM evaluate whether the proposal requires an invariant exception or escalation to the external source owner.
5. Record the proposal as an `[AUTONOMOUS]` or `[DISCOVERY]` entry in the feature's implementation notes with the tag `[SPEC_PROPOSAL]`, including your rationale.
5. Commit the entry so PM sees it in the scan results at the next spec session.

**Anchor node proposals:** When the proposal is for a new anchor node, use tag `[SPEC_PROPOSAL: NEW_ANCHOR]` with the proposed type (`arch_*`, `design_*`, `policy_*`, `ops_*`, or `prodbrief_*`), a name suggestion, and the proposed invariants.

Do NOT modify the feature spec directly. PM owns spec content.

**Do NOT pass the finding as a chat message** (e.g., "Note for PM: ..."). Chat is not a durable channel. The only valid output of `purlin:propose` is a committed `[SPEC_PROPOSAL]` entry in the feature's Implementation Notes.
