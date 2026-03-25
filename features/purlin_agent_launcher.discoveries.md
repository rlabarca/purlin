### [BUG] Missing deprecation warning in pl-run-builder.sh (Discovered: 2026-03-24)
- **Scenario:** Deprecation warning on old launcher
- **Observed Behavior:** `pl-run-builder.sh` launches a full Builder agent session without printing any deprecation warning. No mention of `pl-run.sh` as the replacement.
- **Expected Behavior:** The launcher prints a deprecation warning mentioning `pl-run.sh` before starting the agent session (per spec section 2.5).
- **Action Required:** Builder
- **Status:** OPEN
