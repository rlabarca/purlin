# Implementation Notes: /pl-release-step

**[DISCOVERY] [ACKNOWLEDGED]** manage_step.py has zero unit tests
**Source:** /pl-spec-code-audit --deep (M52)
**Severity:** MEDIUM
**Details:** `tools/release/manage_step.py` implements the CLI tool behind `/pl-release-step` (create, modify, delete release steps). All 11 spec scenarios are tested only via structural checks of the skill file text. The CLI tool's actual behavior (validation, JSON writes, error messages) has no direct test coverage.
**Suggested fix:** Create `tools/release/test_manage_step.py` with unit tests covering: reserved prefix rejection, duplicate detection, atomic writes, modify field updates, delete both-files warning, and valid JSON output.
