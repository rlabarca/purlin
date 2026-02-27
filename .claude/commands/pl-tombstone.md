**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-tombstone instead." and stop.

---

Given the feature name provided as an argument:

1. Read `features/<name>.md` to understand what the feature does.
2. Check the dependency graph (`.purlin/cache/dependency_graph.json`) to identify all features that list `<name>` as a prerequisite. Present the impact list to the user.
3. After user confirmation, create `features/tombstones/<name>.md` using the canonical tombstone format (see `instructions/ARCHITECT_BASE.md` Section 7 for the format).
4. Delete `features/<name>.md`.
5. Commit both changes: `git commit -m "retire(<scope>): retire <name> + tombstone for Builder"`.
6. Run `tools/cdd/status.sh` to update the Critic report.
