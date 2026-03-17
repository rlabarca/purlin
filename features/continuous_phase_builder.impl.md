# Implementation Notes: Continuous Phase Builder

## Traceability Overrides

- traceability_override: "Bootstrap Failure" -> test_bootstrap_failure

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

Stop-action exit status is determined by the evaluator's `success` boolean field, not keyword matching on the reason string. When `success: true`, the phase is recorded COMPLETE and the launcher exits zero. When `success: false`, the phase is recorded SKIPPED, added to the FAILURES array, and exits non-zero. The earlier keyword-grep approach (`grep -qi "success\|complete\|all phases"`) was replaced because Haiku's reason phrasing varied enough to cause false negatives (e.g., "the agent has finished its work" doesn't match those keywords).

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

Current Builder activity is extracted by tailing the last ~20 lines of each phase's log file and pattern-matching for common operations. Priority chain: (1) file operations -> `editing <file>`, (2) test/command runs -> `running <command>`, (3) log tail fallback -> last non-empty line from `tail -5`, stripped of ANSI escape codes via `sed`. The `"working..."` string is used ONLY when the log file does not exist or is empty. Output is truncated to ~50 characters. Use simple `grep -oE` patterns -- exact parsing is not critical since this is a progress hint, not a guarantee.

## Graceful Stop via SIGINT Trap

The launcher traps SIGINT with `trap graceful_stop INT`. The handler sets `STOP_REQUESTED=true`, then sends `SIGTERM` to tracked PIDs: `WT_PIDS` array for parallel builders, `BUILDER_PID` for sequential. The canvas render loop is also terminated (`kill $CANVAS_PID 2>/dev/null`). After kills, the handler clears the canvas one final time (`canvas_clear`), then falls through to the existing summary block. Immediately after the first handler fires, reset the trap to default (`trap - INT`) so a second Ctrl+C invokes the standard bash behavior (immediate termination) without running the handler again.

## Per-Phase Tracking for Exit Summary

Two approaches are viable: (1) a tracking file per phase at `$RUNTIME_DIR/phase_<N>_meta` recording start time, status, and feature list, which the summary reads at exit; or (2) in-memory bash arrays accumulated during the loop. Option (1) is more robust against mid-run crashes (the files survive even if the script is killed). The feature list per phase is extracted from the delivery plan at the start of each phase execution.

## Stacked Approval Table Layout (2026-03-16)

Added stacked single-column layout for terminal widths below 60 columns (Section 2.15 minimum width floor). When `cols < STACKED_THRESHOLD (60)`, `render_approval_table()` renders each phase as labeled fields (`Label:`, `Features:`, `Exec Group:`) on separate lines instead of proportional columns. Lines are truncated to terminal width. The threshold check is in the embedded Python block; if a SIGWINCH resize crosses the 60-column boundary, the layout mode switches on re-render.

## Builder Output Routing Change (Canvas Migration)

[DISCOVERY] (acknowledged) Previous spec had sequential and bootstrap Builder output streamed to the terminal via `tee`. The terminal canvas model replaces this: ALL Builder output in continuous mode goes to log files only (`> "$LOG_FILE" 2>&1`). The terminal is exclusively owned by the canvas. This eliminates stdout/stderr interleaving issues and simplifies exit code handling (no `PIPESTATUS` needed since there is no pipe). The evaluator reads from log files as before -- no change to evaluator behavior.

## Line Buffering: script stdin isolation

The macOS `script -q /dev/null` fallback in `run_line_buffered()` uses `</dev/null` to prevent `script` from consuming parent stdin. Without this, `script` connects its stdin to the pseudo-TTY and steals input meant for later `read` commands (e.g., the approval checkpoint prompt). All continuous mode Builders are non-interactive (`-p` mode) so they never need stdin.

## Line Buffering: script output routing (2026-03-17)

macOS `script` tees output to BOTH its file argument AND stdout. The file argument MUST be `/dev/null` (not `/dev/stdout`). Using `/dev/stdout` causes every line to appear twice in the log file because both the transcript and stdout resolve to the same fd when stdout is redirected (`> "$LOG_FILE"`). With `/dev/null`, the transcript copy is discarded and only the stdout copy reaches the log redirect — clean, no duplication.

The functional test verifies: (a) content appears in the log file during execution (incremental, not buffered until exit), (b) all subprocess output is present after completion, (c) no line duplication.

## Stream-JSON Output Format (2026-03-17)

All `claude --print` invocations in continuous mode use `--verbose --output-format stream-json` to produce NDJSON (newline-delimited JSON) output. The `--verbose` flag is required by the Claude CLI when combining `--print` with `--output-format stream-json` (added as a CLI requirement circa 2026-03). Without these flags, `--print` in text mode only emits the assistant's final text responses — tool calls, file reads, edits, and intermediate reasoning are silent. With `--verbose --output-format stream-json`, every message, tool_use, tool_result, and result event is emitted as a JSON line, giving the log files real content for activity monitoring and evaluator analysis.

The `extract_activity` function's filename regex (`grep -oE '[a-zA-Z0-9_.-]+\.(md|py|sh|...)'`) still matches file paths embedded in JSON values like `"file_path":"foo.py"`, so activity extraction works without changes.

## Stale IN_PROGRESS Recovery

The `reset_stale_in_progress()` function runs both at startup (before the main orchestration loop) and during graceful stop (inside the `graceful_stop` SIGINT handler). At startup, it catches orphans from a previous interrupted run. During graceful stop, it resets phases that were marked IN_PROGRESS during the current run but not completed before the interrupt.

## Evaluator Timeout (Section 2.5)

The 30-second evaluator timeout uses a platform-aware fallback chain: `timeout 30` (Linux/GNU), `gtimeout 30` (macOS with coreutils), or a background-process-with-kill pattern as final fallback. macOS does not ship `timeout` by default; the background fallback polls with 1-second sleeps and sends SIGTERM after 30 iterations, returning exit code 124 (same as GNU timeout).

## Runtime Artifact Cleanup (Section 2.11)

The startup purge (`purge_stale_runtime_artifacts`) runs at the very beginning of continuous mode, BEFORE the bootstrap check. This is earlier than the spec's "after bootstrap, before the first phase" placement to avoid deleting the current run's bootstrap log. The functional effect is the same: stale artifacts from a previous run are purged before any current-run work begins.

Exit cleanup runs after the exit summary and status refresh, deleting transient artifacts (phase_*_meta, canvas_frozen_*, retry_count_*, plan_amendment_phase_*.json, approval_table_lines, canvas_state) while preserving log files for user inspection.

## grep -c Exit Code Fix

`grep -c` returns exit code 1 when the count is 0 (no matches). Using `|| echo 0` would append a second "0" line, causing bash `[` integer comparison to fail with "integer expression expected". Fixed by using `${var:-0}` default expansion instead.

## Per-Phase Status Update During Parallel Execution (Section 2.4)

Replaced the simple `wait $pid` loop (which blocked until ALL builders completed, then batch-updated all phases) with a polling monitor that detects individual builder exits via `kill -0`. As soon as a builder exits with code 0, the orchestrator immediately calls `update_plan_phase_status` and commits the delivery plan update on the main branch. This keeps CDD metrics accurate in real time (e.g., "1 DONE | 1 RUNNING" instead of "0 DONE | 2 RUNNING").

Also fixed `update_plan_phase_status()` to use phase-aware Completion Commit targeting: the function now finds the specific phase heading first, then updates the next `**Completion Commit:** --` line after it. The previous `count=1` approach would always update the first occurrence in the file, which could target the wrong phase when phases complete out of order during parallel execution.

## Configurable Evaluator Model & Success Boolean (2026-03-17)

The evaluator model is now resolved from `continuous_evaluator_model` in config (`.purlin/config.local.json` first, then `.purlin/config.json`). Defaults to Haiku if absent. The same model is used for both the evaluator and the work digest (per spec: "Same model and timeout as the evaluator").

The evaluator JSON schema now includes a `success` boolean field. The stop-action handler uses `EVAL_SUCCESS` variable (parsed from the evaluator's `success` field) instead of the previous `grep -qi "success\|complete\|all phases"` keyword matching on the reason string. The evaluator fallback (hash check) always returns `success: false` since it can't determine completion status.

The output format from `run_evaluator` changed from `action|reason` to `action|success|reason` (pipe-delimited). Both sequential and parallel eval output parsing updated to extract the middle field.

## [DISCOVERY] (acknowledged) JSON Leaking to Terminal During Parallel Execution (2026-03-17)

**Problem:** During the first `--continuous` run with parallel phases (1, 2, 3), raw NDJSON output from the `--verbose --output-format stream-json` builders leaked to the terminal, flooding it with JSON instead of showing the canvas. The parallel group completed successfully (all 3 phases merged) but the evaluator then hung for 646+ seconds (pre-timeout-fix) and the orchestrator never advanced to phase 4.

**Root cause:** macOS `script -q /dev/null` creates a pseudo-TTY whose master can leak output to the controlling terminal (`/dev/tty`), bypassing stdout redirects. This occurs specifically in `( ... ) &` parallel subshells where multiple `script` processes run concurrently.

**Fix:** Two-part approach:
1. Refactored `run_line_buffered` → `run_to_log` with log file as first parameter. The function handles all redirect logic internally (stdbuf path: `> logfile 2>&1`; script path: `> logfile 2>&1`; fallback: `> logfile 2>&1`). Append mode via `--append` flag.
2. Added output containment at the parallel call site: `( ... ) > /dev/null 2>&1 &`. The outer redirect catches any PTY master leakage that bypasses the inner redirect inside `run_to_log`. Sequential and bootstrap invocations don't need containment (no concurrent PTY interaction).
