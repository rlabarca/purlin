**Purlin command: shared (all roles)**

Given the topic or concern provided as an argument, search the spec system and report:

1. Whether an existing feature spec covers this topic (and which file, section, and scenario).
2. Whether an anchor node (`arch_*`, `design_*`, `policy_*`) governs this concern.
3. Whether the topic is covered only in instruction files (process/workflow) rather than feature specs.
4. A recommendation: does this need a new spec, a spec refinement, an anchor node update, or is it already covered?

Use Glob and Grep to search `features/`, `instructions/`, and `.purlin/` for the topic keywords.
