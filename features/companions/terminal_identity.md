# Companion: terminal_identity

## Warp Terminal Workaround

- [IMPL] Export `WARP_DISABLE_AUTO_TITLE=true` when Warp is detected, immediately after sourcing `identity.sh`. Prevents Warp's shell integration `precmd` hook from auto-resetting the tab title after each command completion, which was causing mode-switch identity updates to flash briefly then revert. Guard: `_PURLIN_ENV_WARP` (set at identity.sh source-time). ref: warp-dev/Warp#8330. (Originally implemented in the retired `pl-run.sh` launcher; now handled by the `purlin:start` skill.)
