# Implementation Notes: Context Recovery After Compaction

## Implementation Decisions

**[CLARIFICATION]** The `generate_launcher()` function in `tools/init.sh` already did not contain any agent_role file write logic. Only the four standalone launcher scripts (`pl-run-*.sh`) in the repository root had the `echo "$AGENT_ROLE" > .purlin/runtime/agent_role"` line. The `mkdir -p .purlin/runtime` was preserved since the runtime directory is used by other components. (Severity: INFO)

**[CLARIFICATION]** The `install_claude_md()` function uses Python for the marker-replacement case (where content between `<!-- purlin:start -->` and `<!-- purlin:end -->` must be replaced while preserving surrounding content). The create and append cases use shell `printf` for simplicity. (Severity: INFO)

**[CLARIFICATION]** Test results for this feature are produced by `tools/test_init.sh` using counter snapshots (CRH_PASS_BEFORE/CRH_FAIL_BEFORE) to isolate the 26 context_recovery_hook-specific assertions from the broader project_init test suite. Both `tests/context_recovery_hook/tests.json` and `tests/project_init/tests.json` are written by the same test runner. (Severity: INFO)

## Test Quality Audit

- **Deletion test:** All tests would fail if implementation were deleted (compact hook tests check for matcher presence in settings.json; CLAUDE.md tests check for file existence and marker content; launcher tests grep for agent_role references).
- **Anti-pattern scan:** No AP-1 (tautology), AP-2 (echo-check), AP-3 (mock-only), AP-4 (existence-only), or AP-5 (snapshot) violations. Tests verify behavioral outcomes (marker replacement preserves user content, idempotency on re-run, staging area inclusion).
- **Value assertion check:** All assertions check specific values (matcher names, marker text, file content, git staging status), not just existence.
