# Terminal Identity -- Implementation Notes

## Known Implementation Gap: Non-Builder Root Launchers (2026-03-18)

The Builder launcher (`pl-run-builder.sh`) correctly implements all three identity integration points. The Architect, QA, and PM launchers (`pl-run-architect.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`) are missing all three.

### Reference Implementation (pl-run-builder.sh)

**1. Source the helper (after CORE_DIR is set, before any logic):**

Lines 12-15: Guarded source of `$CORE_DIR/tools/terminal/identity.sh`.

**2. Set identity (before the `claude` invocation):**

Line 143: `type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder"`

**3. Cleanup in EXIT trap:**

Lines 32-34: The `cleanup()` function includes a guarded `clear_agent_identity` call before temp file removal.

### What Each Launcher Needs

Apply the same three-point pattern to `pl-run-architect.sh`, `pl-run-qa.sh`, and `pl-run-pm.sh`:

1. **Source** -- Add the guarded source block after line 10 (`export PURLIN_PROJECT_ROOT`) and before the `PROMPT_FILE` setup.
2. **Set identity** -- Add a guarded `set_agent_identity "<Role>"` call immediately before the `claude` invocation. Use the correct display name: `Architect`, `QA`, `PM`.
3. **EXIT trap** -- Replace the existing `trap "rm -f '$PROMPT_FILE'" EXIT` with a cleanup function that calls `clear_agent_identity` (guarded) before removing the temp file.

### Display Name Mapping

| Launcher | Display Name |
|----------|-------------|
| `pl-run-architect.sh` | `Architect` |
| `pl-run-qa.sh` | `QA` |
| `pl-run-pm.sh` | `PM` |
| `pl-run-builder.sh` | `Builder` (already implemented) |

### Non-Continuous Mode Behavior Note

For the Architect, QA, and PM launchers (which have no continuous mode), identity is set once before `claude` launches and cleared on exit. There are no phase transitions -- the badge shows the role name for the entire session. This matches the Builder's non-continuous mode behavior.
