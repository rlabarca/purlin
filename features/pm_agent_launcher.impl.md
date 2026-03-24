# Implementation Notes: PM Agent Launcher

*   **Tool Allowlist:** The PM launcher restricts tools to: `Bash(git *)`, `Bash(bash *)`, `Bash(python3 *)`, `Read`, `Write`, `Edit`, `Glob`, `Grep`. This is broader than the original QA-style read-only set because the PM writes to feature files (Visual Specification sections) and design artifact directories.
*   **Figma MCP:** The PM is the primary Figma write agent. Figma MCP tools are available through the standard MCP server configuration, not through `--allowedTools`. The launcher does not need to explicitly allow MCP tools.
*   **Test Harness:** `tools/test_per_role_launchers.sh` (shared across all four launcher features).

**[DISCOVERY]** PM non-bypass allowedTools missing Write and Edit
**Source:** /pl-spec-code-audit --deep (M51)
**Severity:** MEDIUM
**Details:** When `bypass_permissions=false` is configured for the PM, the launcher's `--allowedTools` list includes Read, Glob, Grep, and Bash but omits Write and Edit. The spec §2.1 includes Write and Edit since the PM writes to feature files and design artifacts.
**Suggested fix:** Add `"Write"` and `"Edit"` to the PM launcher's non-bypass `--allowedTools` list in `pl-run-pm.sh`.
