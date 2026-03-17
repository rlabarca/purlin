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

## Terminal Canvas Engine

Central rendering function that owns the cursor position on stderr. The canvas tracks the line count of its last render in a variable (e.g., `CANVAS_LINES`). Each update does:

1. If `CANVAS_LINES > 0`, emit `\033[${CANVAS_LINES}A` (cursor up) + `\033[J` (clear to end of screen).
2. Print the new content lines to stderr.
3. Update `CANVAS_LINES` to the new count.

Spinner state is a global index (`SPINNER_IDX`) into the braille array `(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)`. The canvas render function accepts content lines as arguments and handles all ANSI mechanics. All intermediate status renders into this canvas; only the final exit summary is permanent.

The render loop runs as a background subshell at ~100ms (`sleep 0.1`) for spinner animation. Heavier updates (log size via `wc -c`, activity extraction via `tail | grep`) happen on a 15-second counter within the loop. The render loop PID is stored in `CANVAS_PID` for cleanup.

TTY guard: `[ -t 2 ]` at canvas startup. If false, the render loop is never started. Instead, a simple `canvas_milestone()` function prints single append-only lines without ANSI.

## Bootstrap Progress Canvas

Background subshell running the canvas render loop at ~100ms. Content is a single line: `"${SPINNER[SPINNER_IDX]} Starting bootstrap session... ${elapsed}s"`. Elapsed time derived from `$SECONDS` delta. Killed (`kill $CANVAS_PID`) when bootstrap exits. The bootstrap Builder's output goes to `> "$LOG_FILE" 2>&1` (no tee, no terminal streaming).

## Console Plan Summary Rendering

`printf`-based column alignment for the approval checkpoint table. Terminal width from `tput cols` (default 80). Column widths are computed proportionally from available width. Cell content that exceeds column width is truncated with `...`. ANSI sequences for header colors (`\033[1;36m` bold cyan for header, `\033[32m` green for separators) are applied only when `[ -t 2 ]`. Phase data (label, features, complexity, exec group) is read from the phase analyzer JSON output. The table is rendered via the canvas engine (replaces the spinner content).

## Sequential Phase Canvas

Same canvas engine as the parallel heartbeat but single-phase display. Content is one line: `"${SPINNER[SPINNER_IDX]} Phase N -- Label   running  Xm Ys   SIZE  activity"`. Replaces the previous `tee` streaming approach -- Builder output goes exclusively to the log file (`> "$LOG_FILE" 2>&1`), and the terminal shows only the canvas. Activity extraction and log size checks happen on 15-second intervals within the render loop.

## Inter-Phase Canvas

Between phases, the canvas shows evaluator/re-analysis status. Same render loop, different content: `"${SPINNER[SPINNER_IDX]} Evaluating phase N output... Xs"` or `"${SPINNER[SPINNER_IDX]} Re-analyzing delivery plan... Xs"`. Started before the evaluator invocation, killed after it returns.

## Activity Extraction from Log Files

Current Builder activity is extracted by tailing the last ~20 lines of each phase's log file and pattern-matching for common operations. Priority order: file write operations map to `editing <file>`, test invocations map to `running tests on <feature>`, shell commands map to `running <command>`, and the default fallback is `working...`. Output is truncated to ~50 characters. Use simple `grep -oE` patterns -- exact parsing is not critical since this is a progress hint, not a guarantee.

## Graceful Stop via SIGINT Trap

The launcher traps SIGINT with `trap graceful_stop INT`. The handler sets `STOP_REQUESTED=true`, then sends `SIGTERM` to tracked PIDs: `WT_PIDS` array for parallel builders, `BUILDER_PID` for sequential. The canvas render loop is also terminated (`kill $CANVAS_PID 2>/dev/null`). After kills, the handler clears the canvas one final time (`canvas_clear`), then falls through to the existing summary block. Immediately after the first handler fires, reset the trap to default (`trap - INT`) so a second Ctrl+C invokes the standard bash behavior (immediate termination) without running the handler again.

## Per-Phase Tracking for Exit Summary

Two approaches are viable: (1) a tracking file per phase at `$RUNTIME_DIR/phase_<N>_meta` recording start time, status, and feature list, which the summary reads at exit; or (2) in-memory bash arrays accumulated during the loop. Option (1) is more robust against mid-run crashes (the files survive even if the script is killed). The feature list per phase is extracted from the delivery plan at the start of each phase execution.

## Builder Output Routing Change (Canvas Migration)

[DISCOVERY] (acknowledged) Previous spec had sequential and bootstrap Builder output streamed to the terminal via `tee`. The terminal canvas model replaces this: ALL Builder output in continuous mode goes to log files only (`> "$LOG_FILE" 2>&1`). The terminal is exclusively owned by the canvas. This eliminates stdout/stderr interleaving issues and simplifies exit code handling (no `PIPESTATUS` needed since there is no pipe). The evaluator reads from log files as before -- no change to evaluator behavior.
