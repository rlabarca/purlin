---
name: propose
description: This skill activates Engineer mode. If another mode is active, confirm switch first
---

**Purlin mode: Engineer**

Purlin agent: This skill activates Engineer mode. If another mode is active, confirm switch first.

---

Given the topic provided as an argument, surface a structured spec change suggestion to PM mode:

1. Search the current spec system for the relevant feature or anchor node.
2. Describe the gap, inconsistency, or improvement you encountered during implementation.
3. Draft a concrete proposal: what should change in the spec (section, scenario, or constraint).
4. Record the proposal as an `[AUTONOMOUS]` or `[DISCOVERY]` entry in the feature's implementation notes with the tag `[SPEC_PROPOSAL]`, including your rationale.
5. Commit the entry so PM mode sees it in the scan results at their next session.

**Anchor node proposals:** When the proposal is for a new anchor node, use tag `[SPEC_PROPOSAL: NEW_ANCHOR]` with the proposed type (`arch_*`, `design_*`, or `policy_*`), a name suggestion, and the proposed invariants.

Do NOT modify the feature spec directly. PM mode owns spec content.

**Do NOT pass the finding as a chat message** (e.g., "Note for PM: ..."). Chat is not a durable channel. The only valid output of `purlin:propose` is a committed `[SPEC_PROPOSAL]` entry in the feature's Implementation Notes.
