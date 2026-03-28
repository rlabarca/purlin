# Discovery Sidecar: pl_help

## [BUG] H14: Skill contradicts spec on --help

**Status:** RESOLVED
**Action Required:** None
**Severity:** HIGH

**Description:** The skill file `skills/help/SKILL.md` previously contained a "Do NOT run scripts" directive that contradicted the spec requirement to execute each `pl-*.sh` script with `--help` to retrieve actual help output.

**Resolution:** The skill file was updated (commit `10a5f661`) to include Step 4 ("Discover CLI Scripts") which instructs agents to run `timeout 3 bash "<script>" --help 2>/dev/null` for each discovered script. The current skill file correctly matches the spec requirements in Section 2.4 (Help Output Convention) and Section 2.5 (CLI Script Discovery). All 7 pl_help tests pass, confirming the --help execution behavior is correctly specified.
