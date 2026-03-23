## Implementation Notes

**[CLARIFICATION]** The spec says watch mode polls at "1-second intervals" — implemented with `sleep 1` in the loop. On macOS without coreutils `timeout`, the fallback uses background process + polling kill with `pkill -P` to kill child processes. (Severity: INFO)

**[CLARIFICATION]** The enriched `tests.json` format (Section 2.3) is documented and tested as a JSON schema convention — test harnesses that support `--write-results` are expected to produce these fields. No changes to existing harnesses were required for the format definition itself. (Severity: INFO)

**[AUTONOMOUS]** The QA skills (`pl-regression-author.md`, `pl-regression-run.md`, `pl-regression-evaluate.md`) are structured as protocol documents rather than executable code, consistent with other slash commands in `.claude/commands/`. Each guides the QA agent through a single focused workflow. The former unified `pl-regression.md` was retired per spec Section 2.2.4. (Severity: WARN)

**[DISCOVERY] [ACKNOWLEDGED]** Architect-owned files referenced the retired `/pl-regression` skill name. All 8 references updated in commit 7880f97: QA_BASE.md (5), qa_commands.md (2), test_fixture_repo.md (1). (Severity: HIGH)

**[CLARIFICATION]** The harness runner (`tools/test_support/harness_runner.py`) handles `agent_behavior` scenarios by invoking `claude --print` with the scenario's role and prompt. In test environments, a fake `claude` script is placed on PATH to simulate output. The runner evaluates regex assertions against captured output and writes enriched `regression.json`. Output path separation: regression results go to `regression.json`, Builder-owned unit test results go to `tests.json`. (Severity: INFO)

**[CLARIFICATION]** The `web_test` harness type uses Python's `urllib.request` for basic HTTP checks. Full web test delegation (Playwright, browser automation) is handled by the consuming project's web test infrastructure; the harness runner provides the dispatch and assertion pipeline. (Severity: INFO)

**[CLARIFICATION]** Web test server lifecycle (Section 2.8.1): the harness runner manages CDD server start/stop for `web_test` scenarios. For no-fixture scenarios, it checks `.purlin/runtime/cdd.port` and reuses a responsive server or starts a new one via `tools/cdd/start.sh`. For fixture scenarios, it starts a separate server with `PURLIN_PROJECT_ROOT` pointed at the fixture directory (the spec says `--project-root <fixture_dir>` on start.sh, but start.sh doesn't have that flag — instead we set the env var, which start.sh already uses for root detection). Cleanup uses try/finally to ensure servers started by the harness are always stopped. (Severity: INFO)

**[CLARIFICATION]** The meta-runner (`tools/test_support/run_regression.sh`) uses `find` with `-print0` and `sort -z` for null-safe scenario file discovery, ensuring correct handling of filenames with special characters. (Severity: INFO)

### Test Quality Audit
- Rubric: 6/6 PASS
- Tests: 40 total, 40 passed
- AP scan: clean
- Date: 2026-03-23

