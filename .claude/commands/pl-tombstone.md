**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-tombstone instead." and stop.

---

Given the feature name provided as an argument:

1. Read `features/<name>.md` to understand what the feature does.
2. Check the dependency graph (`.purlin/cache/dependency_graph.json`) to identify all features that list `<name>` as a prerequisite. Present the impact list to the user.
3. After user confirmation, create `features/tombstones/<name>.md` using the canonical tombstone format below.
4. Delete `features/<name>.md`.
5. Commit both changes: `git commit -m "retire(<scope>): retire <name> + tombstone for Builder"`.
6. Run `tools/cdd/status.sh` to update the Critic report.

**Canonical tombstone format:**

```markdown
# TOMBSTONE: <feature_name>

**Retired:** <YYYY-MM-DD>
**Reason:** <One-line explanation of why this feature was retired.>

## Files to Delete

List each path the Builder should remove. Be specific.

- `<path/to/file.py>` -- entire file
- `<path/to/directory/>` -- entire directory (confirm nothing else depends on it)
- `<path/to/module.py>:ClassName` -- specific class only (if partial deletion)

## Dependencies to Check

List any other features or code that may reference the retired code and will need updating.

- `features/<other_feature>.md` -- references removed API `foo()`
- `tools/<tool>/script.py:line 42` -- imports retired module

## Context

<Brief explanation: what this feature did, why it was retired, and any architectural decisions the Builder should understand before deleting.>
```

**Rules:**
*   Tombstones MUST be created before the feature file is deleted. Never delete a feature file without a tombstone if implementation code exists.
*   If the feature was specced but never implemented (no code exists), a tombstone is unnecessary -- delete the feature file directly and note "not implemented" in the commit message.
*   Tombstone files are NOT feature files. They do not appear in the dependency graph or CDD lifecycle. The Critic detects tombstones and surfaces them as HIGH-priority Builder action items.
*   Once the Builder processes a tombstone and deletes the code, the Builder commits and deletes the tombstone file. The tombstone is transient -- it exists only until the Builder acts.
