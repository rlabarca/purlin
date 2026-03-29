### [BUG] --name CLI arg does not reference ROLE_DISPLAY (Discovered: 2026-03-25)
- **Scenario:** Badge never uses "Purlin:" prefix @auto (regression WTI6)
- **Observed Behavior:** The `--name` argument passed to the `claude` CLI in `pl-run.sh` does not reference the `ROLE_DISPLAY` variable. The session name should match the badge text for consistency between iTerm badge and Claude session name.
- **Expected Behavior:** `--name` argument uses `ROLE_DISPLAY` (or equivalent computed badge text) so the session name matches the iTerm badge (e.g., "purlin | Engineer" or "purlin | QA (W1)").
- **Action Required:** None — `pl-run.sh` shell launcher is retired. Session naming is now handled by `purlin:resume` / `purlin:session-name` inside the session.
- **Status:** RESOLVED — no longer applicable after launcher retirement (2026-03-28).
