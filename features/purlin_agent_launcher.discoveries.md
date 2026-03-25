### [BUG] Missing deprecation warning in pl-run-builder.sh (Discovered: 2026-03-24)
- **Scenario:** Deprecation warning on old launcher
- **Observed Behavior:** `pl-run-builder.sh` launches a full Builder agent session without printing any deprecation warning. No mention of `pl-run.sh` as the replacement.
- **Expected Behavior:** The launcher prints a deprecation warning mentioning `pl-run.sh` before starting the agent session (per spec section 2.5).
- **Action Required:** Builder
- **Status:** RESOLVED

### [INTENT_DRIFT] Stale HOW_WE_WORK_BASE.md reference in spec and regression test (Discovered: 2026-03-25)
- **Scenario:** Instruction stack assembly (regression T7, T10)
- **Observed Behavior:** `pl-run.sh` does NOT load `HOW_WE_WORK_BASE.md` — only `PURLIN_BASE.md`. Code aligns with `purlin_instruction_architecture.md` which explicitly says "does NOT concatenate HOW_WE_WORK_BASE.md."
- **Expected Behavior:** `purlin_agent_launcher.md` line 20 says launcher MUST assemble `HOW_WE_WORK_BASE.md` + `PURLIN_BASE.md`. Regression test T7 and T10 enforce this stale expectation.
- **Action Required:** PM (update purlin_agent_launcher spec to remove HOW_WE_WORK_BASE.md from instruction stack requirement) + QA (update regression test script `tests/qa/test_purlin_agent_launcher_regression.sh` T7/T10 — regression scripts are QA-owned)
- **Status:** RESOLVED
