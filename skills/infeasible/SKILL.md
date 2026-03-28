---
name: infeasible
description: This skill activates Engineer mode. If another mode is active, confirm switch first
---

**Purlin mode: Engineer**

Purlin agent: This skill activates Engineer mode. If another mode is active, confirm switch first.

---

## Path Resolution

> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`.
> **Commit format:** See `${CLAUDE_PLUGIN_ROOT}/references/commit_conventions.md`.
> **Companion files:** See `${CLAUDE_PLUGIN_ROOT}/references/active_deviations.md` for deviation format and PM review protocol.

---

Given the feature name provided as an argument:

1. Read `features/<name>.md` to confirm the feature and its current state.
2. Record an `[INFEASIBLE]` entry in the feature's implementation notes (companion file `features/<name>.impl.md` if it exists, otherwise the `## Implementation Notes` section) with a detailed rationale: what constraint or contradiction makes it unimplementable as specified.
3. Commit the implementation note: `git commit -m "feat(<scope>): [INFEASIBLE] <name> — <brief reason>"`.
4. Run `${CLAUDE_PLUGIN_ROOT}/scripts/cdd/scan.sh` to refresh project state and surface the INFEASIBLE entry as a PM action item visible in scan results.
5. Do NOT implement any code for this feature. PM mode must revise the spec before work can resume.
