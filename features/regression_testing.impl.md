## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


**[CLARIFICATION]** The spec says watch mode polls at "1-second intervals" — implemented with `sleep 1` in the loop. On macOS without coreutils `timeout`, the fallback uses background process + polling kill with `pkill -P` to kill child processes. (Severity: INFO)

**[CLARIFICATION]** The enriched `tests.json` format (Section 2.3) is documented and tested as a JSON schema convention — test harnesses that support `--write-results` are expected to produce these fields. No changes to existing harnesses were required for the format definition itself. (Severity: INFO)

**[AUTONOMOUS]** The QA skill (`pl-regression.md`) is structured as a protocol document rather than executable code, consistent with other slash commands in `.claude/commands/`. It guides the QA agent through discovery, selection, command composition, and result processing. (Severity: WARN)

**[CLARIFICATION]** The harness runner (`tools/test_support/harness_runner.py`) handles `agent_behavior` scenarios by invoking `claude --print` with the scenario's role and prompt. In test environments, a fake `claude` script is placed on PATH to simulate output. The runner evaluates regex assertions against captured output and writes enriched `tests.json`. (Severity: INFO)

**[CLARIFICATION]** The `web_test` harness type uses Python's `urllib.request` for basic HTTP checks. Full web test delegation (Playwright, browser automation) is handled by the consuming project's web test infrastructure; the harness runner provides the dispatch and assertion pipeline. (Severity: INFO)

**[CLARIFICATION]** The meta-runner (`tools/test_support/run_regression.sh`) uses `find` with `-print0` and `sort -z` for null-safe scenario file discovery, ensuring correct handling of filenames with special characters. (Severity: INFO)

**[CLARIFICATION]** M33 fix: stderr capture uses a temp file (`mktemp`) rather than process substitution to ensure portability across all three timeout dispatch paths (gtimeout, GNU timeout, macOS fallback). The excerpt is truncated to 1000 bytes via `head -c 1000`. The `stderr_excerpt` field is only included in the result JSON when non-empty, keeping the result clean for successful harnesses. Stderr is re-echoed to the terminal via `cat "$stderr_tmpfile" >&2` so it remains visible to the user. (Severity: INFO)

**[CLARIFICATION]** M35 fix: The completion gate logic is tested as a pure function (`_evaluate_completion_gate`) that mirrors the gate semantics described in the spec -- FAIL status blocks completion, PASS allows it, and absence of regression results does not gate. Status table rendering tests verify the format matches the meta-runner's summary output pattern. (Severity: INFO)

