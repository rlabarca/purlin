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

## ANSI Cursor Control for Heartbeat

The in-place heartbeat uses `\033[<N>A` (cursor up N lines) followed by `\033[J` (clear from cursor to end of screen) to overwrite the previous heartbeat block. The heartbeat function tracks the previous output line count so it knows how many lines to move up. On the first print, no cursor-up is emitted. When stderr is not a TTY (`! [ -t 2 ]`), skip all ANSI sequences and fall back to single-line append-only output.

## Activity Extraction from Log Files

Current Builder activity is extracted by tailing the last ~20 lines of each phase's log file and pattern-matching for common operations. Priority order: file write operations map to `editing <file>`, test invocations map to `running tests on <feature>`, shell commands map to `running <command>`, and the default fallback is `working...`. Output is truncated to ~50 characters. Use simple `grep -oE` patterns -- exact parsing is not critical since this is a progress hint, not a guarantee.

## Graceful Stop via SIGINT Trap

The launcher traps SIGINT with `trap graceful_stop INT`. The handler sets `STOP_REQUESTED=true`, then sends `SIGTERM` to tracked PIDs: `WT_PIDS` array for parallel builders, `BUILDER_PID` for sequential. After kills, falls through to the existing summary block. Immediately after the first handler fires, reset the trap to default (`trap - INT`) so a second Ctrl+C invokes the standard bash behavior (immediate termination) without running the handler again.

## Per-Phase Tracking for Exit Summary

Two approaches are viable: (1) a tracking file per phase at `$RUNTIME_DIR/phase_<N>_meta` recording start time, status, and feature list, which the summary reads at exit; or (2) in-memory bash arrays accumulated during the loop. Option (1) is more robust against mid-run crashes (the files survive even if the script is killed). The feature list per phase is extracted from the delivery plan at the start of each phase execution.
