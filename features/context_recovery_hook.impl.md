# Implementation Notes: Context Recovery Hook

**[DISCOVERY] [ACKNOWLEDGED]** CLAUDE.md installation scenarios absent from test_init.sh
**Source:** /pl-spec-code-audit --deep (M47)
**Severity:** MEDIUM
**Details:** Spec §2.6 defines 7 test cases for CLAUDE.md behavior (create on fresh init, replace marked block, append to unmarked file, preserve user content, idempotency, staging verification). None exist in `test_init.sh`.
**Suggested fix:** Add test cases to `test_init.sh` covering all 7 CLAUDE.md scenarios.

**[DISCOVERY] [ACKNOWLEDGED]** Refresh path missing git add CLAUDE.md
**Source:** /pl-spec-code-audit --deep (M48)
**Severity:** MEDIUM
**Details:** `tools/init.sh` refresh path calls `install_claude_md()` but does not follow up with `git add CLAUDE.md`. The full init path correctly stages CLAUDE.md at line 856.
**Suggested fix:** Add `git add "$PROJECT_ROOT/CLAUDE.md"` to the refresh path after the `install_claude_md` call.
