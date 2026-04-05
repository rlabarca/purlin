# Feature: e2e_manual_staleness

> Scope: scripts/mcp/purlin_server.py
> Stack: shell/bash, python3 (sync_status, _check_manual_staleness)
> Description: End-to-end test of the manual proof staleness lifecycle. Exercises stamping a manual proof with email/date/commit SHA, detecting staleness when scope files change after the stamp, and re-stamping to clear the stale state.

## Rules

- RULE-1: A stamped @manual proof shows as PASS in sync_status when no scope files have changed since the stamp's commit SHA
- RULE-2: A stamped @manual proof shows as MANUAL PROOF STALE when scope files have commits newer than the stamp's commit SHA
- RULE-3: Re-stamping with the current HEAD commit SHA clears the stale state and shows PASS again

## Proof

- PROOF-1 (RULE-1): Create spec with @manual stamp at current HEAD; commit; run sync_status; verify PASS with verified date @e2e
- PROOF-2 (RULE-2): Edit scope file and commit; run sync_status; verify MANUAL PROOF STALE and re-verify directive @e2e
- PROOF-3 (RULE-3): Update @manual stamp with new HEAD SHA; commit; run sync_status; verify PASS again @e2e
