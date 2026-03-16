# Implementation Notes: Continuous Phase Builder

## CLI Flag Mapping

[DISCOVERY] (acknowledged) The spec references `claude -p -n <session_name>` for named sessions, but the real Claude Code CLI uses `--session-id <uuid>` instead. Implementation uses `--session-id` with `uuidgen`-generated UUIDs. Spec updated: Section 2.3 now uses `--session-id <session_id>`.

[DISCOVERY] (acknowledged) The spec references `--max-turns N` as a pass-through flag, but this flag does not exist in the Claude Code CLI (`claude --help` shows no `--max-turns`). Only `--max-budget-usd` is a real CLI flag. Spec updated: removed `--max-turns` from Section 2.1 and the Pass-Through Flags Forwarded scenario.

## Bash 3 Compatibility

Replaced `declare -A` (associative arrays, bash 4+) with file-based retry counting (`$RUNTIME_DIR/retry_count_<phase>`). macOS ships bash 3.2 at `/bin/bash`, and the shebang `#!/bin/bash` targets it.

## Evaluator Implementation

The LLM evaluator uses `claude --print --model <haiku> --json-schema <schema> < <prompt_file>` to invoke Haiku. The evaluator prompt is written to a temp file and piped via stdin to avoid shell argument length limits. The `--json-schema` flag constrains the response to the action/reason schema.

On evaluator failure, the fallback compares delivery plan MD5 hashes before and after the Builder run. Changed plan → `continue`; unchanged → `stop`.

## Parallel Phase Orchestration

Parallel phases use manually created git worktrees (`git worktree add -b <branch> <dir> HEAD`) rather than Claude Code's built-in `--worktree` flag. This gives the orchestrator full control over branch naming and merge-back sequencing. The orchestrator tells parallel Builders "Do not modify the delivery plan" and updates the plan centrally after merging.

## Stop-on-Error Exit Code

Non-success stop actions (INFEASIBLE, missing fixture, no progress) are tracked in the FAILURES array and cause non-zero exit. Success stops ("all phases complete") exit zero.

## Dependency Validation (Defense in Depth)

Plan validation against the dependency graph happens at two points: (1) at creation time when the Builder runs `/pl-delivery-plan`, the command instructs the Builder to read `dependency_graph.json` for phase assignment and run the phase analyzer before committing; (2) at bootstrap time when `--continuous` creates a plan, the launcher runs the analyzer as a post-bootstrap dry-run (Section 2.15). Both gates use `tools/delivery/phase_analyzer.py`. The creation-time gate prevents cycles from entering the plan; the bootstrap gate catches any that slip through (e.g., if the Builder creates a plan without using `/pl-delivery-plan`).

## Removed: --max-budget-usd Pass-Through

[DISCOVERY] (acknowledged) The `--max-budget-usd` pass-through flag was removed from the spec. Continuous mode runs until completion -- the user can Ctrl+C to stop. Budget exhaustion mid-phase creates a confusing failure mode where the phase stops partway through work.

## Output Streaming with tee and Exit Codes

When using `cmd | tee file`, `$?` reflects tee's exit code, not the Builder's. In continuous mode this is safe because the evaluator (not exit code) drives all orchestration decisions. For additional robustness, `set -o pipefail` or `${PIPESTATUS[0]}` can be used to capture the Builder's actual exit code through the pipe if needed.
