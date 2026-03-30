### [BUG] Missing deprecation warning in pl-run.sh (Discovered: 2026-03-24)
- **Scenario:** Deprecation warning on old launcher
- **Observed Behavior:** `pl-run.sh` launches a full Engineer agent session without printing any deprecation warning. No mention of `pl-run.sh` as the replacement.
- **Expected Behavior:** The launcher prints a deprecation warning mentioning `pl-run.sh` before starting the agent session (per spec section 2.5).
- **Action Required:** Engineer
- **Status:** RESOLVED

### [INTENT_DRIFT] Stale PURLIN_BASE.md reference in spec and regression test (Discovered: 2026-03-25)
- **Scenario:** Instruction stack assembly (regression T7, T10)
- **Observed Behavior:** `pl-run.sh` does NOT load `PURLIN_BASE.md` — only `PURLIN_BASE.md`. Code aligns with `purlin_instruction_architecture.md` which explicitly says "does NOT concatenate PURLIN_BASE.md."
- **Expected Behavior:** `purlin_resume.md` line 20 says launcher MUST assemble `PURLIN_BASE.md` + `PURLIN_BASE.md`. Regression test T7 and T10 enforce this stale expectation.
- **Action Required:** PM (update purlin_resume spec to remove PURLIN_BASE.md from instruction stack requirement) + QA (update regression test script `tests/qa/test_purlin_resume_regression.sh` T7/T10 — regression scripts are QA-owned)
- **Status:** RESOLVED

### [DISCOVERY] show_help switched from self-parsing to heredoc (Discovered: 2026-03-25)
- **Scenario:** Help output separates sticky and ephemeral flags
- **Observed Behavior:** The `show_help()` function previously used `sed` to self-parse `# desc:` comments from case patterns. The new grouped layout (Saved preferences / Session options / Other) cannot be produced by flat self-parsing, so `show_help()` was rewritten as a `cat <<'HELPTEXT'` heredoc with the exact spec-prescribed layout.
- **Impact:** Help text is no longer dynamically generated from case-statement comments. Adding a new flag requires updating both the case statement and the heredoc.
- **Action Required:** None — spec §2.2.4 explicitly permits this ("implementation mechanism is left to Engineer mode").
- **Status:** ACKNOWLEDGED

### [INTENT_DRIFT] Deprecation warning scenario tests removed legacy launchers (Discovered: 2026-03-25)
- **Scenario:** Deprecation warning on old launcher @auto
- **Observed Behavior:** Scenario and regression tests (T0a-T3) expect `pl-run-builder.sh` to exist and print a deprecation warning. The legacy role-specific launchers (`pl-run-builder.sh`, `pl-run-architect.sh`, etc.) were removed as part of the Purlin unified agent transition. The `project_init` regression (S10) also fails expecting these launchers to be regenerated on refresh. The spec (section 2.5) still requires deprecation wrappers but the system has moved past needing them.
- **Expected Behavior:** Either (a) the spec should be updated to remove the deprecation warning requirement since legacy launchers are fully retired, or (b) init.sh should generate thin wrapper scripts that print a deprecation message and exit.
- **Action Required:** PM (remove spec section 2.6 and deprecation scenario from QA scenarios)
- **Status:** RESOLVED — legacy launchers fully retired per user decision (2026-03-28). No deprecation wrappers needed.

### [BUG] Legacy launcher pl-run-builder.sh does not exist (Discovered: 2026-03-25)
- **Scenario:** Deprecation warning on old launcher @auto
- **Observed Behavior:** `pl-run-builder.sh` does not exist at project root. Regression tests T0a, T1, T2, T3 all fail. The spec (section 2.5) requires that old role-specific launchers exist and print a deprecation warning directing users to `pl-run.sh`. Without the file, the deprecation path is untestable.
- **Expected Behavior:** `pl-run-builder.sh` exists, prints deprecation warning mentioning `pl-run.sh`, and starts the agent session.
- **Action Required:** None — legacy launchers intentionally removed.
- **Status:** RESOLVED — not a bug; legacy launchers are retired. Spec section 2.6 needs PM update to match.

### [BUG] --no-save flag missing from purlin:resume skill (Discovered: 2026-03-28)
- **Scenario:** Help output includes yolo and no-save flags @auto
- **Observed Behavior:** The `skills/resume/SKILL.md` file contains `--yolo` and `--no-yolo` flags but does not contain `--no-save`. Regression assertion for `--no-save` presence fails.
- **Expected Behavior:** Per `features/purlin_resume.md` section 2.2.3, `--no-save` is a meta flag that suppresses persistence for all sticky flags. The skill file should document this flag in its usage section.
- **Action Required:** Engineer (add `--no-save` flag to `skills/resume/SKILL.md` usage section and implementation)
- **Status:** RESOLVED — fixed in auto-fix iteration 2 (2026-03-28)
