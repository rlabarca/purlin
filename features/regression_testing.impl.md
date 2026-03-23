## Implementation Notes

**[CLARIFICATION]** The spec says watch mode polls at "1-second intervals" — implemented with `sleep 1` in the loop. On macOS without coreutils `timeout`, the fallback uses background process + polling kill with `pkill -P` to kill child processes. (Severity: INFO)

**[CLARIFICATION]** The enriched `tests.json` format (Section 2.3) is documented and tested as a JSON schema convention — test harnesses that support `--write-results` are expected to produce these fields. No changes to existing harnesses were required for the format definition itself. (Severity: INFO)

**[AUTONOMOUS]** The QA skills (`pl-regression-author.md`, `pl-regression-run.md`, `pl-regression-evaluate.md`) are structured as protocol documents rather than executable code, consistent with other slash commands in `.claude/commands/`. Each guides the QA agent through a single focused workflow. The former unified `pl-regression.md` was retired per spec Section 2.2.4. (Severity: WARN)

**[DISCOVERY] [ACKNOWLEDGED]** Architect-owned files referenced the retired `/pl-regression` skill name. All 8 references updated in commit 7880f97: QA_BASE.md (5), qa_commands.md (2), test_fixture_repo.md (1). (Severity: HIGH)

**[CLARIFICATION]** The harness runner (`tools/test_support/harness_runner.py`) handles `agent_behavior` scenarios by invoking `claude --print` with the scenario's role and prompt. In test environments, a fake `claude` script is placed on PATH to simulate output. The runner evaluates regex assertions against captured output and writes enriched `tests.json`. (Severity: INFO)

**[CLARIFICATION]** The `web_test` harness type uses Python's `urllib.request` for basic HTTP checks. Full web test delegation (Playwright, browser automation) is handled by the consuming project's web test infrastructure; the harness runner provides the dispatch and assertion pipeline. (Severity: INFO)

**[CLARIFICATION]** The meta-runner (`tools/test_support/run_regression.sh`) uses `find` with `-print0` and `sort -z` for null-safe scenario file discovery, ensuring correct handling of filenames with special characters. (Severity: INFO)

