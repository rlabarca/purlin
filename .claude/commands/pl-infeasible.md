**Purlin mode: Engineer**

Purlin agent: This skill activates Engineer mode. If another mode is active, confirm switch first.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

Given the feature name provided as an argument:

1. Read `features/<name>.md` to confirm the feature and its current state.
2. Record an `[INFEASIBLE]` entry in the feature's implementation notes (companion file `features/<name>.impl.md` if it exists, otherwise the `## Implementation Notes` section) with a detailed rationale: what constraint or contradiction makes it unimplementable as specified.
3. Commit the implementation note: `git commit -m "feat(<scope>): [INFEASIBLE] <name> — <brief reason>"`.
4. Run `${TOOLS_ROOT}/cdd/scan.sh` to refresh project state and surface the INFEASIBLE entry as a PM action item visible in scan results.
5. Do NOT implement any code for this feature. PM mode must revise the spec before work can resume.
