# Implementation Notes: Intelligent Purlin Update Agent Skill

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (see prose) | MCP manifest diff reporting incomplete in command file — Acknowledged | DISCOVERY | PENDING |
| (see prose) | [ACKNOWLEDGED]** Skill file missing PURLIN_PROJECT_ROOT reference | DISCOVERY | PENDING |

*   **[CLARIFICATION]** Auto-fix iteration 1: restored `--preflight-only` flag to `tools/init.sh`. The flag was removed per a `project_init` discovery but `pl_update_purlin` spec §2.6 requires it for prerequisite checking after submodule advance. Added `PREFLIGHT_ONLY` variable, CLI case branch, and early exit after preflight checks.
*   **Agent Skill Architecture:** This feature is implemented as a Claude Code slash command (`.claude/commands/pl-update-purlin.md`), not as a shell script or Python tool. The command file is a prompt that instructs the agent to perform the update workflow interactively. Tests verify command file structure, referenced infrastructure, and behavioral invariants.
*   **Test Approach:** `tests/pl_update_purlin/test_command.py` validates the command file contains required references for each automated scenario (structural change detection keywords, merge strategy labels, stale artifact names, infrastructure file existence, etc.). This follows the same pattern as other agent skill tests (e.g., `tests/pl_session_resume/test_command.py`).
*   **[CLARIFICATION]** The "Structural Change Migration Plan" scenario describes agent behavior (detecting renamed section headers in instruction files and scanning override files for stale references). Tests verify the command file contains the necessary structural change detection instructions, section header comparison references, override file scanning instructions, and migration plan generation format. (Severity: INFO)

### Audit Finding -- 2026-03-19

[DISCOVERY] MCP manifest diff reporting incomplete in command file — Acknowledged

**Source:** /pl-spec-code-audit --deep (item #22)
**Severity:** MEDIUM
**Details:** The spec (Section 2.3, Scenario "MCP Manifest Diff") requires the update command to detect changes to `.claude/mcp.json` and report added/removed/modified MCP server entries. The command file references MCP manifest diffing but the test coverage does not verify the diff output format (added/removed/modified server names). The structural test checks for keyword presence but not behavioral completeness.
**Suggested fix:** Add a test assertion that verifies the command file contains instructions for reporting specific MCP server changes (server name, change type). Alternatively, if the current keyword check is deemed sufficient for an agent skill, document this as an intentional test-depth tradeoff in the companion file.

**[DISCOVERY] [ACKNOWLEDGED]** Skill file missing PURLIN_PROJECT_ROOT reference
**Source:** /pl-spec-code-audit --deep (M16)
**Severity:** MEDIUM
**Details:** Spec §2.13 requires the skill to use `PURLIN_PROJECT_ROOT` (env var) for project root detection with directory-climbing as fallback. The skill file (`.claude/commands/pl-update-purlin.md`) contains no mention of either mechanism.
**Suggested fix:** Add a Path Resolution section to the skill file referencing `PURLIN_PROJECT_ROOT` and climbing fallback, matching the pattern in `pl-resume.md`.
