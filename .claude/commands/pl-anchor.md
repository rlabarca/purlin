**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-anchor instead." and stop.

---

Read `instructions/references/feature_format.md` for heading format rules and Critic parser requirements before creating or editing an anchor node.

Given the topic provided as an argument, create or update an anchor node file in `features/`:

1. Determine the correct prefix: `arch_` for technical constraints, `design_` for visual/UX standards, `policy_` for governance rules.
2. If updating: read the existing anchor node, identify the constraint to add or revise, apply the change, and identify all dependent features whose status will be reset.
3. If creating: scaffold a new anchor node with sections for Constraints, Patterns, and Invariants relevant to the domain.
4. After editing, commit the change and run `tools/cdd/status.sh`. The status run will reset all dependent features to TODO and surface them as Builder action items.
