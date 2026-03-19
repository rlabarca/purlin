## Implementation Notes

**[CLARIFICATION]** The spec says watch mode polls at "1-second intervals" — implemented with `sleep 1` in the loop. On macOS without coreutils `timeout`, the fallback uses background process + polling kill with `pkill -P` to kill child processes. (Severity: INFO)

**[CLARIFICATION]** The enriched `tests.json` format (Section 2.3) is documented and tested as a JSON schema convention — test harnesses that support `--write-results` are expected to produce these fields. No changes to existing harnesses were required for the format definition itself. (Severity: INFO)

**[AUTONOMOUS]** The QA skill (`pl-regression.md`) is structured as a protocol document rather than executable code, consistent with other slash commands in `.claude/commands/`. It guides the QA agent through discovery, selection, command composition, and result processing. (Severity: WARN)

