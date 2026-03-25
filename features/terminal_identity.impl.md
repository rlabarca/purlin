# Terminal Identity -- Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


## Resolved: Non-Engineer Root Launchers (2026-03-18)

All four root launchers now implement the three-point identity integration pattern. The gap in PM, QA, and PM launchers was resolved by adding sourcing, set_agent_identity, and cleanup to each.

### Reference Implementation (pl-run.sh)

**1. Source the helper (after CORE_DIR is set, before any logic):**

Lines 12-15: Guarded source of `$CORE_DIR/tools/terminal/identity.sh`.

**2. Set identity (before the `claude` invocation):**

Line 143: `type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Engineer"`

**3. Cleanup in EXIT trap:**

Lines 32-34: The `cleanup()` function includes a guarded `clear_agent_identity` call before temp file removal.

### What Each Launcher Needs

Apply the same three-point pattern to `pl-run.sh`, `pl-run.sh`, and `pl-run.sh`:

1. **Source** -- Add the guarded source block after line 10 (`export PURLIN_PROJECT_ROOT`) and before the `PROMPT_FILE` setup.
2. **Set identity** -- Add a guarded `set_agent_identity "<Role>"` call immediately before the `claude` invocation. Use the correct display name: `PM`, `QA`, `PM`.
3. **EXIT trap** -- Replace the existing `trap "rm -f '$PROMPT_FILE'" EXIT` with a cleanup function that calls `clear_agent_identity` (guarded) before removing the temp file.

### Display Name Mapping

| Launcher | Display Name |
|----------|-------------|
| `pl-run.sh` | `PM` |
| `pl-run.sh` | `QA` |
| `pl-run.sh` | `PM` |
| `pl-run.sh` | `Engineer` (already implemented) |

### Non-Continuous Mode Behavior Note

For PM mode, QA, and PM launchers (which have no continuous mode), identity is set once before `claude` launches and cleared on exit. There are no phase transitions -- the badge shows the role name for the entire session. This matches Engineer mode's non-continuous mode behavior.
