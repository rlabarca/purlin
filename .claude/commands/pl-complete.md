**Purlin command owner: QA**
**Purlin mode: QA**

Legacy agents: If you are not the QA, respond: "This is a QA command. Ask your QA agent to run /pl-complete instead." and stop.
Purlin agent: This skill activates QA mode. If another mode is active, confirm switch first.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

Given the feature name provided as an argument, gate completion on all requirements:

## Completion Gates

1.  **TESTING state:** Confirm the feature is in TESTING state (run `${TOOLS_ROOT}/cdd/scan.sh` if needed).
2.  **All scenarios verified:** Confirm all manual scenarios have been verified (PASS) in the current session or a prior session.
3.  **Zero open discoveries:** Confirm there are zero OPEN or SPEC_UPDATED discoveries in `features/<name>.discoveries.md`. If the file is absent or empty, the gate passes.
4.  **Delivery plan check:** Check `.purlin/delivery_plan.md`. If the feature appears in any PENDING phase, do NOT mark complete -- inform the user: "Feature X is deferred until all phases are delivered (appears in Phase N)."
5.  **[Verified] tag required:** QA completions MUST include the `[Verified]` tag. This distinguishes QA completions from Builder auto-completions and is checked by scan results.

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
*   Delivery plan -> "Feature appears in PENDING Phase N. Complete when all phases are delivered."
