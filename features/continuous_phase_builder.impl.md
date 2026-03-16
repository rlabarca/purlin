# Implementation Notes: Continuous Phase Builder

## CLI Flag Mapping

[DISCOVERY] The spec references `claude -p -n <session_name>` for named sessions, but the real Claude Code CLI uses `--session-id <uuid>` instead. Implementation uses `--session-id` with `uuidgen`-generated UUIDs. The spec should be updated to reflect the actual CLI flag.

[DISCOVERY] The spec references `--max-turns N` as a pass-through flag, but this flag does not exist in the Claude Code CLI (`claude --help` shows no `--max-turns`). The flag is accepted and forwarded but will cause a CLI error if used. Only `--max-budget-usd` is a real CLI flag.

## Bash 3 Compatibility

Replaced `declare -A` (associative arrays, bash 4+) with file-based retry counting (`$RUNTIME_DIR/retry_count_<phase>`). macOS ships bash 3.2 at `/bin/bash`, and the shebang `#!/bin/bash` targets it.

## Evaluator Implementation

The LLM evaluator uses `claude --print --model <haiku> --json-schema <schema> < <prompt_file>` to invoke Haiku. The evaluator prompt is written to a temp file and piped via stdin to avoid shell argument length limits. The `--json-schema` flag constrains the response to the action/reason schema.

On evaluator failure, the fallback compares delivery plan MD5 hashes before and after the Builder run. Changed plan → `continue`; unchanged → `stop`.

## Parallel Phase Orchestration

Parallel phases use manually created git worktrees (`git worktree add -b <branch> <dir> HEAD`) rather than Claude Code's built-in `--worktree` flag. This gives the orchestrator full control over branch naming and merge-back sequencing. The orchestrator tells parallel Builders "Do not modify the delivery plan" and updates the plan centrally after merging.

## Stop-on-Error Exit Code

Non-success stop actions (INFEASIBLE, missing fixture, no progress) are tracked in the FAILURES array and cause non-zero exit. Success stops ("all phases complete") exit zero.
