---
name: complete
description: Gate feature completion on all quality requirements
---

**Writes:** status tag commits

Given the feature name provided as an argument, gate completion on all requirements:

## Completion Gates

1.  **TESTING state:** Confirm the feature is in TESTING state (run `purlin_scan` with `only: "features"` if needed).
2.  **All scenarios verified:** Confirm all manual scenarios have been verified (PASS) in the current session or a prior session.
3.  **Zero open discoveries:** Confirm there are zero OPEN or SPEC_UPDATED discoveries in the feature's `.discoveries.md` sidecar (resolve via `features/**/<name>.discoveries.md`). If the file is absent or empty, the gate passes.
4.  **Regression gate:** Check `regression_status` from scan results. If FAIL or STALE, do NOT mark complete. FAIL means tests are broken; STALE means source changed since results were generated. Both require `purlin:regression` to resolve.
5.  **Constraint gate:** Call `purlin_constraints` for the feature. For each anchor and invariant returned, extract `## FORBIDDEN Patterns` and grep the feature's code files. If any violations exist, do NOT mark complete — "FORBIDDEN pattern violation from <constraint_file>: <pattern> found in <file>:<line>. Fix before completion."
6.  **Companion file gate:** Check the feature's `.impl.md` companion (resolve via `features/**/<name>.impl.md`) for unacknowledged `[DEVIATION]`, `[DISCOVERY]`, or `[INFEASIBLE]` entries (no `[ACKNOWLEDGED]` tag). If any exist, do NOT mark complete — "N unacknowledged companion file entries exist. PM must review before completion." This prevents completing features where the Engineer made undocumented deviations PM hasn't seen.
7.  **Delivery plan check:** Check `.purlin/delivery_plan.md`. If the feature appears in any PENDING phase, do NOT mark complete -- inform the user: "Feature X is deferred until all phases are delivered (appears in Phase N)."
8.  **[Verified] tag required:** QA completions MUST include the `[Verified]` tag. This distinguishes QA completions from Engineer auto-completions and is checked by scan results.

## Execution

If all gates pass:

```
git commit --allow-empty -m "status(<scope>): [Complete features/<name>.md] [Verified]"
```

Run `purlin_scan` (with `only: "features"`) to confirm the feature transitions to COMPLETE.

## Gate Failures

If any gate fails, report which gate(s) failed and what is needed:
*   Not in TESTING -> "Feature must be in TESTING state. Current state: <state>."
*   Open discoveries -> "N OPEN discoveries remain: <titles>. These must be resolved before completion."
*   Regression FAIL -> "Regression tests failing (<passed>/<total>). Run `purlin:regression` to re-run and evaluate, or ask Engineer to fix the underlying issue."
*   Regression STALE -> "Regression results are stale (source changed since last run). Run `purlin:regression` to update results before completing."
*   FORBIDDEN violation -> "FORBIDDEN pattern violation from <constraint_file>. Fix the code or escalate as invariant conflict before completion."
*   Unacknowledged deviations -> "N unacknowledged companion entries. PM must review (purlin:status shows them) before completion."
*   Delivery plan -> "Feature appears in PENDING Phase N. Complete when all phases are delivered."
