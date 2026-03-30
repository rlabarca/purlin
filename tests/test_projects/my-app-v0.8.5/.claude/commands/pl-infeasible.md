**Purlin command owner: Builder**

If you are not operating as the Purlin Builder, respond: "This is a Builder command. Ask your Builder agent to run /pl-infeasible instead." and stop.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

Given the feature name provided as an argument:

1. Read `features/<name>.md` to confirm the feature and its current state.
2. Record an `[INFEASIBLE]` entry in the feature's implementation notes (companion file `features/<name>.impl.md` if it exists, otherwise the `## Implementation Notes` section) with a detailed rationale: what constraint or contradiction makes it unimplementable as specified.
3. Commit the implementation note: `git commit -m "feat(<scope>): [INFEASIBLE] <name> — <brief reason>"`.
4. Run `${TOOLS_ROOT}/cdd/status.sh` to surface the INFEASIBLE entry as a CRITICAL-priority Architect action item in the Critic report.
5. Do NOT implement any code for this feature. The Architect must revise the spec before work can resume.
