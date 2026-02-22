**Purlin command owner: Builder**

If you are not operating as the Purlin Builder, respond: "This is a Builder command. Ask your Builder agent to run /pl-propose instead." and stop.

---

Given the topic provided as an argument, surface a structured spec change suggestion to the Architect:

1. Search the current spec system for the relevant feature or anchor node.
2. Describe the gap, inconsistency, or improvement you encountered during implementation.
3. Draft a concrete proposal: what should change in the spec (section, scenario, or constraint).
4. Record the proposal as an `[AUTONOMOUS]` or `[DISCOVERY]` entry in the feature's implementation notes with the tag `[SPEC_PROPOSAL]`, including your rationale.
5. Commit the entry so the Architect sees it in the Critic report at their next session.

Do NOT modify the feature spec directly. The Architect owns spec content.

**Do NOT pass the finding as a chat message** (e.g., "Note for Architect: ..."). Chat is not a durable channel. The only valid output of `/pl-propose` is a committed `[SPEC_PROPOSAL]` entry in the feature's Implementation Notes.
