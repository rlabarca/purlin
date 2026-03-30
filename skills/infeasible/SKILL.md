---
name: infeasible
description: Mark a feature as infeasible with detailed rationale
---

Given the feature name provided as an argument:

1. Resolve the feature file via `features/**/<name>.md` and read it to confirm the feature exists and its current state. If no match is found, stop with: "Feature spec `<name>.md` not found. Check feature name and try again."
2. Record an `[INFEASIBLE]` entry in the feature's companion file (`.impl.md` in the same folder as the spec, creating it if it doesn't exist) with a detailed rationale: what constraint or contradiction makes it unimplementable as specified.
3. Commit the implementation note: `git commit -m "feat(<scope>): [INFEASIBLE] <name> — <brief reason>"`.
4. Run `purlin_scan` to refresh project state and surface the INFEASIBLE entry as a PM action item visible in scan results.
5. Do NOT implement any code for this feature. PM must revise the spec (via `purlin:spec`) before work can resume.
