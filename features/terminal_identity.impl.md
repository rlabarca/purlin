# Terminal Identity -- Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


## Resolved: Terminal Identity via Skills (2026-03-18)

Terminal identity is now set by the `purlin:resume` and `purlin:mode` skills running inside a Claude Code session. The retired shell launchers (`pl-run.sh` and role-specific variants) have been replaced by the plugin skill model.

### Current Identity Flow

1. **`purlin:resume`** -- Sets terminal identity for the initial mode (default: Engineer) during session entry.
2. **`purlin:mode`** -- Updates terminal identity when switching modes (Engineer, PM, QA) mid-session.
3. **Session exit** -- Identity is cleared via the SessionEnd hook.

### Display Name Mapping

| Mode | Display Name |
|------|-------------|
| PM | `PM` |
| QA | `QA` |
| Engineer | `Engineer` |

### Non-Continuous Mode Behavior Note

Identity is set once at session start and updated on mode switches. The badge shows the active role name for the duration of that mode. There are no phase transitions -- the badge reflects whichever mode is currently active.

### Warp Terminal Workaround

- [IMPL] Export `WARP_DISABLE_AUTO_TITLE=true` when Warp is detected, immediately after sourcing `identity.sh`. Prevents Warp's shell integration `precmd` hook from auto-resetting the tab title after each command completion, which was causing mode-switch identity updates to flash briefly then revert. Guard: `_PURLIN_ENV_WARP` (set at identity.sh source-time). ref: warp-dev/Warp#8330. (Originally implemented in the retired `pl-run.sh` launcher; now handled by the `purlin:resume` skill.)
