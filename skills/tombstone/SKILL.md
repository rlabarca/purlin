---
name: tombstone
description: This skill activates Engineer mode. If another mode is active, confirm switch first
---

**Purlin mode: Engineer**

Purlin agent: This skill activates Engineer mode. If another mode is active, confirm switch first.

---

## Path Resolution

> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`.
> **Commit format:** See `${CLAUDE_PLUGIN_ROOT}/references/commit_conventions.md`.
> **Output standards:** See `${CLAUDE_PLUGIN_ROOT}/references/output_standards.md`.

---

Given the feature name provided as an argument:

1. Resolve the feature file via `features/**/<name>.md` and read it to understand what the feature does.
2. Check the dependency graph (`.purlin/cache/dependency_graph.json`) to identify all features that list `<name>` as a prerequisite. Present the impact list to the user.
3. **Auto-discover all artifacts** for this feature (searching the same category subfolder as the spec):
   - Companion file: `features/<category_slug>/<name>.impl.md`
   - Discovery sidecar: `features/<category_slug>/<name>.discoveries.md`
   - Test directory: `tests/<name>/`
   - Regression results: `tests/<name>/regression.json`
   - QA regression scenario: `tests/qa/scenarios/<name>.json`
   - QA regression runner: `tests/qa/test_<name>_regression.sh`
4. After user confirmation, create the tombstone content at `features/_tombstones/<name>.md` using the canonical format below. The "Files to Delete" section MUST include all discovered test artifacts from step 3.
5. **Move feature and companion artifacts to tombstones:**
   - `git mv features/<category_slug>/<name>.md features/_tombstones/<name>.md` (overwrites tombstone content — write tombstone content into the file AFTER the move, or write it first then move the spec to replace)
   - `git mv features/<category_slug>/<name>.impl.md features/_tombstones/<name>.impl.md` (if exists)
   - `git mv features/<category_slug>/<name>.discoveries.md features/_tombstones/<name>.discoveries.md` (if exists)
6. Commit all changes: `git commit -m "retire(<scope>): tombstone <name>"`.
7. Run the MCP `purlin_scan` tool (with `only: "features"`, `tombstones: true`) to verify tombstone state.

**Canonical tombstone format:**

```markdown
# TOMBSTONE: <feature_name>

**Retired:** <YYYY-MM-DD>
**Reason:** <One-line explanation of why this feature was retired.>

## Files to Delete

- `tests/<name>/` -- test directory (if exists)
- `tests/qa/scenarios/<name>.json` -- QA regression scenario (if exists)
- `tests/qa/test_<name>_regression.sh` -- QA regression runner (if exists)
- `<path/to/implementation.py>` -- implementation code
- `<path/to/other_file>` -- other related files

## Dependencies to Check

List any other features or code that may reference the retired code and will need updating.

- `features/<other_feature>.md` -- references removed API `foo()`
- `tools/<tool>/script.py:line 42` -- imports retired module

## Context

<Brief explanation: what this feature did, why it was retired, and any architectural decisions the Engineer should understand before deleting.>
```

**Rules:**
*   Tombstones MUST be created before the feature file is moved. Never move a feature file without a tombstone if implementation code exists.
*   If the feature was specced but never implemented (no code exists), a tombstone is unnecessary — delete the feature file directly and note "not implemented" in the commit message. Still move companions/discoveries to tombstones if they exist.
*   Tombstone files are NOT feature files. They do not appear in the dependency graph or CDD lifecycle. The scan detects tombstones and surfaces them as HIGH-priority Engineer action items via `purlin:status`.
*   Once the Engineer processes a tombstone (deletes the listed code and test files), the Engineer also deletes the tombstone file itself and any companion artifacts in `features/_tombstones/`. The tombstone is transient — it exists only until the Engineer acts.
