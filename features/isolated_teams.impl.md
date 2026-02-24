## Implementation Notes

See [isolated_teams.md](isolated_teams.md) for the feature specification.

**Bash 3.2 compatibility (macOS):** The launcher script heredoc MUST NOT use bash 4.0+ features. macOS ships `/bin/bash` 3.2.57 which does not support `${var^}` (case modification). The role label capitalization uses a POSIX-compatible `case` statement instead. This also produces semantically correct labels ("QA" instead of "Qa").

**[DISCOVERY] [SPEC_PROPOSAL] Missing automated scenarios for Section 2.6 (Per-Team Launcher Scripts)** (Severity: HIGH)

Section 2.6 specifies detailed requirements for launcher script generation (three scripts created, exec contract, CWD preservation, cleanup on kill, idempotency) but the Automated Scenarios section has zero coverage for any of them. The `${ROLE^}` bash 3.2 incompatibility bug went undetected because no scenario verified launcher script creation. Builder has added 4 tests to cover the gap (`TestLauncherScripts` in `test_isolation.py`), but the spec needs matching Gherkin scenarios to formalize the contract.

Proposed scenarios for Architect to add:

1. **create_isolation Generates All Three Launcher Scripts** — after successful creation, `run_<name>_architect.sh`, `run_<name>_builder.sh`, `run_<name>_qa.sh` exist in `$PROJECT_ROOT/`, are non-empty, and are executable.
2. **Launcher Scripts Delegate to Worktree Launchers** — each generated script contains `exec "$WORKTREE_PATH/run_<role>.sh" "$@"` targeting the correct worktree path.
3. **kill_isolation Removes All Launcher Scripts** — after kill, all three launcher scripts are deleted from `$PROJECT_ROOT/`.
4. **Launcher Scripts Are Not Regenerated on Idempotent Create** — when the worktree already exists, the idempotent exit path does not overwrite existing launcher scripts.
