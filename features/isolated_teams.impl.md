## Implementation Notes

See [isolated_teams.md](isolated_teams.md) for the feature specification.

**Bash 3.2 compatibility (macOS):** The launcher script heredoc MUST NOT use bash 4.0+ features. macOS ships `/bin/bash` 3.2.57 which does not support `${var^}` (case modification). The role label capitalization uses a POSIX-compatible `case` statement instead. This also produces semantically correct labels ("QA" instead of "Qa").

**[DISCOVERY] RESOLVED — Missing automated scenarios for Section 2.6 (Per-Team Launcher Scripts)**

Architect added 5 Gherkin scenarios to `## 3. Scenarios` covering: script generation (all three files exist and are executable), `cd`+exec delegation contract, per-role delegation targets, kill cleanup, and idempotency. The `exec`-without-`cd` root cause of the startup print BUG was discovered and resolved in the same pass — Section 2.6 now mandates `cd "$WORKTREE_PATH" && exec`. Builder must update `create_isolation.sh` accordingly and update `TestLauncherScripts` in `test_isolation.py` to assert the `cd` line is present.
