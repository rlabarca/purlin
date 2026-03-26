**Purlin mode: QA**

Purlin agent: This skill activates QA mode. If another mode is active, confirm switch first.

---

## Path Resolution

> See `instructions/references/path_resolution.md`. Produces `TOOLS_ROOT`.
> **Companion files:** See `instructions/references/active_deviations.md` for deviation format and PM review protocol.
> **Test infrastructure:** See `instructions/references/test_infrastructure.md` for result schemas, harness types, status interpretation, and smoke tier rules.
> **Commit format:** See `instructions/references/commit_conventions.md`.

---

Given the feature name provided as an argument, gate completion on all requirements:

## Completion Gates

1.  **TESTING state:** Confirm the feature is in TESTING state (run `${TOOLS_ROOT}/cdd/scan.sh` if needed).
2.  **All scenarios verified:** Confirm all manual scenarios have been verified (PASS) in the current session or a prior session.
3.  **Zero open discoveries:** Confirm there are zero OPEN or SPEC_UPDATED discoveries in `features/<name>.discoveries.md`. If the file is absent or empty, the gate passes.
4.  **Regression gate:** Check `regression_status` from scan results. If FAIL or STALE, do NOT mark complete. FAIL means tests are broken; STALE means source changed since results were generated. Both require `/pl-regression` to resolve.
5.  **Companion file gate:** Check `features/<name>.impl.md` for unacknowledged `[DEVIATION]` or `[DISCOVERY]` entries (no `[ACKNOWLEDGED]` tag). If any exist, do NOT mark complete — "N unacknowledged companion file entries exist. PM must review before completion." This prevents completing features where the Engineer made undocumented deviations PM hasn't seen.
6.  **Delivery plan check:** Check `.purlin/delivery_plan.md`. If the feature appears in any PENDING phase, do NOT mark complete -- inform the user: "Feature X is deferred until all phases are delivered (appears in Phase N)."
7.  **[Verified] tag required:** QA completions MUST include the `[Verified]` tag. This distinguishes QA completions from Engineer auto-completions and is checked by scan results.

## Execution

If all gates pass:

```
git commit --allow-empty -m "status(<scope>): [Complete features/<name>.md] [Verified]"
```

Run `${TOOLS_ROOT}/cdd/scan.sh` to confirm the feature transitions to COMPLETE.

## Gate Failures

If any gate fails, report which gate(s) failed and what is needed:
*   Not in TESTING -> "Feature must be in TESTING state. Current state: <state>."
*   Open discoveries -> "N OPEN discoveries remain: <titles>. These must be resolved before completion."
*   Regression FAIL -> "Regression tests failing (<passed>/<total>). Run `/pl-regression` to re-run and evaluate, or ask Engineer to fix the underlying issue."
*   Regression STALE -> "Regression results are stale (source changed since last run). Run `/pl-regression` to update results before completing."
*   Unacknowledged deviations -> "N unacknowledged companion entries. PM must review (/pl-status shows them) before completion."
*   Delivery plan -> "Feature appears in PENDING Phase N. Complete when all phases are delivered."
