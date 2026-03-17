# Feature: Continuous Phase Builder

> Label: "Tool: Continuous Phase Builder"
> Category: "Install, Update & Scripts"
> Prerequisite: features/builder_agent_launcher.md
> Prerequisite: features/phase_analyzer.md
> Prerequisite: features/agent_launchers_common.md

[TODO]

## 1. Overview

An opt-in orchestration mode (`--continuous`) for the Builder launcher (`pl-run-builder.sh`) that automatically progresses through all delivery plan phases without human intervention. Uses the phase analyzer for dependency-aware ordering and parallelization, an LLM evaluator (Haiku) to classify Builder exit states, and system prompt overrides to enable autonomous operation. When `--continuous` is not passed, the launcher behaves identically to today.

---

## 2. Requirements

### 2.1 Flag Parsing

- `pl-run-builder.sh` accepts `--continuous` as an optional flag.
- When `--continuous` is absent, behavior is identical to the current launcher (single interactive session).
- `--continuous` implies `-p` mode (print mode, non-interactive) for each phase invocation.

### 2.2 Phase Analyzer Integration (Re-Analyze Loop)

- The orchestration loop re-runs `tools/delivery/phase_analyzer.py` **before each execution group**, not once at startup. The loop structure is:
  1. Run the phase analyzer on the current delivery plan.
  2. If no PENDING phases remain (empty groups), exit successfully.
  3. Execute the **first** execution group returned by the analyzer.
  4. Evaluate Builder output via the LLM evaluator.
  5. If the evaluator returns `continue`, goto step 1 (re-analyze the potentially modified plan).
- The launcher MUST NOT cache execution groups across iterations. Each iteration sees the freshest state of the delivery plan.
- If the phase analyzer exits with an error (no delivery plan, no dependency graph), the launcher MUST print the error and exit.

### 2.3 Sequential Phase Execution

- For execution groups with a single phase (`parallel: false`), run the Builder in `-p` mode.
- Each phase invocation uses a unique session ID: `continuous-phase-<phase_number>-<uuid>`.
- The Builder is invoked with `claude -p --session-id <session_id>` plus all resolved config flags (model, effort, permissions) and the assembled system prompt.
- The initial message includes phase-specific context: `"Begin Builder session. CONTINUOUS MODE -- proceed immediately with work plan, do not wait for approval."`.
- Builder output is written to log files; the terminal shows the canvas display (see Section 2.16).

### 2.4 Parallel Phase Execution

- For execution groups with multiple phases (`parallel: true`), launch each phase's Builder in a separate git worktree.
- Each parallel Builder is invoked with `claude -p -w <worktree-name>` where the worktree name is `continuous-phase-<phase_number>`.
- Each parallel Builder receives a phase-specific prompt: `"Begin Builder session. CONTINUOUS MODE -- you are assigned to Phase <N> ONLY. Work exclusively on Phase <N> features. Do not wait for approval."`.
- The launcher waits for all parallel Builders in the group to complete before proceeding. The terminal canvas provides progress visibility (see Section 2.16).
- After all parallel Builders complete, merge each worktree branch back to the main branch.
- If any merge produces a conflict, the launcher MUST stop immediately, report the conflicting files, and exit with a message directing the user to resolve manually.
- After successful merges, clean up worktree branches.
- The orchestrator updates the delivery plan centrally after each group completes (not per-Builder).

### 2.5 LLM Evaluator

- After each Builder exit (whether sequential or parallel), pipe the Builder's output to a lightweight LLM evaluator.
- The evaluator is invoked via `claude -p --model <haiku-model> --json-schema <schema>` with Haiku.
- The evaluator receives: the tail of the Builder's output (last 200 lines), the current delivery plan contents (if the file still exists), and classification instructions.
- The evaluator returns structured JSON:

```json
{
  "action": "continue | retry | approve | stop",
  "reason": "Brief explanation"
}
```

- **Decision mapping:**

| Builder Output Signal | Evaluator Action |
|---|---|
| "Phase N of M complete" + delivery plan updated | `continue` |
| "Ready to go?" / "Ready to resume?" (approval prompt) | `approve` |
| Context exhaustion / checkpoint saved mid-phase | `retry` |
| Partial progress (features done but phase incomplete) | `retry` |
| Error requiring human input (INFEASIBLE, missing fixture) | `stop` |
| All phases complete / delivery plan deleted | `stop` (success) |
| No meaningful progress detected | `stop` |

### 2.6 Evaluator Actions

- **`continue`:** Proceed to the next phase or execution group. Start a new session.
- **`approve`:** The Builder paused for approval despite the auto-proceed override. Resume the same session via `claude -r <session-name> -p "Approved. Proceed."`. After the resumed run completes, re-evaluate with the new output.
- **`retry`:** Relaunch the same phase in a new session (fresh context). Maximum 2 consecutive retries per phase. If the retry limit is exceeded, exit with an escalation message.
- **`stop`:** Exit the orchestration loop. Print the reason from the evaluator. If the reason indicates success (all phases complete), exit with zero status. Otherwise, exit with non-zero status.

### 2.7 Approval Bypass (Auto-Proceed Override)

- In continuous mode, the Builder's system prompt receives an appended override:

```
CONTINUOUS PHASE MODE ACTIVE: You are running in non-interactive print mode.
There is no human user present. You MUST:
- NEVER ask "Ready to go?" or "Ready to resume?" or wait for approval.
- NEVER ask for user input or confirmation of any kind.
- Proceed immediately with your work plan.
- Complete the current delivery plan phase autonomously, then halt as normal.
This override takes precedence over any instruction to "wait for approval"
or "ask the user."
```

- This is the primary bypass mechanism. The evaluator's `approve` action is the fallback.

### 2.8 Server Permission Override

- In continuous mode, the Builder's system prompt receives an additional appended override:

```
CONTINUOUS PHASE MODE ACTIVE: You have permission to start, stop, and restart
server processes as needed for local verification. You MUST clean up (stop) any
started servers before halting at phase completion. Use dynamic ports where
possible to avoid conflicts.
```

- This override is only injected when `--continuous` is active. It does not modify `BUILDER_BASE.md`.

### 2.9 Logging

- Each phase's full Builder output is written to `.purlin/runtime/continuous_build_phase_<N>.log`.
- For parallel phases, log files include the worktree context: `.purlin/runtime/continuous_build_phase_<N>_worktree.log`.
- Evaluator decisions are logged to stderr with timestamps.
- At exit, the launcher prints a rich exit summary with per-phase details (see Section 2.16 exit summary format) and then runs a post-run status refresh (see Section 2.16 post-run status refresh).
- Log files are always written identically regardless of whether output is also streamed to the terminal (see Section 2.16). The evaluator reads from log files, not terminal output.

### 2.10 Error Handling

- No delivery plan at launch: run bootstrap session (see Section 2.15). If bootstrap fails, print error and exit non-zero.
- Phase analyzer failure: print error, exit non-zero.
- Evaluator invocation failure (Haiku unavailable, malformed JSON): fall back to delivery plan hash check. If the delivery plan file changed since the last phase, treat as `continue`. If unchanged and Builder exited, treat as `stop`.
- Merge conflict during parallel merge: stop immediately, report conflicting files, exit non-zero.
- Orphaned worktrees on error: clean up any worktrees created during the current run.
- Retry limit exceeded: exit with message identifying the stuck phase and suggesting manual intervention.

### 2.12 Dynamic Delivery Plan Handling

- The Builder MAY amend the delivery plan during any phase (adding QA fix phases, splitting large phases, removing unnecessary phases). The orchestrator treats the delivery plan as a **live document**.
- After each group completes and the evaluator returns `continue`, the loop re-runs the phase analyzer on the (potentially modified) delivery plan. New PENDING phases, reordered phases, and removed phases are all picked up automatically.
- Phase numbers in the delivery plan are not assumed to be contiguous or sequential. The analyzer operates on whatever PENDING phase numbers exist at analysis time.
- The orchestrator tracks completed phases by number across re-analyses. If the Builder adds Phase 7 during Phase 3, and the evaluator returns `continue`, the next re-analysis will include Phase 7 as PENDING and include it in the execution order.
- Total phase count may increase or decrease during execution. The exit summary reports the final count, not the initial count.
- The orchestrator MUST NOT cache or remember previous analysis results. Each re-analysis is independent.

### 2.13 Parallel Phase Plan Amendments

- During parallel execution, multiple Builders run in separate worktrees. If they all modify the delivery plan Markdown independently, the worktree merge will likely conflict.
- **Parallel Builders MUST NOT modify the delivery plan directly.** Instead, if a parallel Builder needs to amend the plan (add a QA fix phase, split remaining work), it writes a structured JSON amendment request to `.purlin/runtime/plan_amendment_phase_<N>.json` where `<N>` is the phase number it was assigned.
- The system prompt override for parallel phases must include: `"You are running in a parallel worktree. Do NOT modify the delivery plan directly. If you need to add, split, or remove phases, write a plan amendment request to .purlin/runtime/plan_amendment_phase_<N>.json instead."`
- **Amendment request format:**

```json
{
  "requesting_phase": 3,
  "amendments": [
    {
      "action": "add",
      "phase_number": 7,
      "label": "QA fixes for Phase 3",
      "features": ["feature_a.md", "feature_b.md"],
      "reason": "B2 test failures require dedicated fix phase"
    }
  ]
}
```

- After all parallel Builders complete and code merges succeed, the orchestrator reads all `plan_amendment_phase_*.json` files, applies them to the delivery plan on the main branch, and deletes the amendment files.
- **Sequential Builders** (non-parallel) can still modify the delivery plan directly as they do today -- only parallel Builders use the amendment request mechanism.

### 2.14 Evaluator: Plan Amendment Detection

- The evaluator decision table includes additional signals for plan amendments:

| Builder Output Signal | Evaluator Action |
|---|---|
| Builder amended the delivery plan (new/split/modified phases) + phase complete | `continue` |
| Builder output mentions plan amendment but current phase not complete | `retry` |

- The evaluator prompt must instruct Haiku to check whether the delivery plan was modified by comparing phase counts or looking for amendment markers in Builder output.

### 2.15 Bootstrap Session

- When `--continuous` is active and no delivery plan exists at `.purlin/cache/delivery_plan.md`, the launcher runs a bootstrap Builder session before entering the orchestration loop.
- The bootstrap session uses `-p` mode with a bootstrap-specific system prompt override (distinct from the continuous phase override in 2.7 and the server override in 2.8).
- The bootstrap override instructs the Builder to: execute the standard startup protocol including scope assessment; if phasing is warranted, create the delivery plan via `/pl-delivery-plan` without user approval and halt immediately (do not begin Phase 1); if phasing is not warranted, complete the work directly and halt.
- **Conservative sizing bias:** The bootstrap override explicitly instructs the Builder to prefer more phases over fewer, smaller phases over larger, and to maximize parallelization opportunities. The goal is to keep each phase's context footprint small enough for reliable autonomous completion. When in doubt, split.
- Outcome detection uses file-existence checking, not output parsing:
  - Plan file exists after bootstrap -> approval checkpoint, then continuous loop (Section 2.2).
  - No plan file + exit code 0 -> Builder completed all work directly (phasing not warranted). Launcher exits successfully with summary.
  - No plan file + exit code non-zero -> bootstrap failed. Launcher exits with error directing the user to run an interactive session.
- **Plan validation:** After bootstrap creates the plan and before the approval prompt, the launcher runs the phase analyzer as a dry-run validation. If the analyzer detects dependency cycles or structural errors, the launcher prints the error, notes that the plan has been committed for manual editing, and exits 0. The user fixes the plan and re-runs `--continuous` (which will skip bootstrap since the plan now exists).
- **Approval checkpoint:** When bootstrap creates a valid delivery plan, the canvas clears the spinner and renders a colored console table summarizing the plan. The table is rendered into the canvas area on stderr. Format:

```
=== Delivery Plan (N phases) ===

  #   Label                        Features                                Complexity   Exec Group
  --- ---------------------------- --------------------------------------- ------------ -------------------
  1   Foundation Anchors           policy_critic, design_visual_standards  LOW+LOW      0 (sequential)
  2   Policy Chain                 policy_release, policy_branch_collab    LOW+LOW      1 (parallel w/ 3)
  ...

Parallel groups: 2 (Phases 2+3, Phases 4+5+6)
Review at .purlin/cache/delivery_plan.md
================================
Proceed? [Y/n]
```

  - Fixed-width columns with space alignment, no Markdown pipes.
  - ANSI bold cyan (`\033[1;36m`) on header row, green (`\033[32m`) on separator lines.
  - Phase labels from delivery plan headings, features/complexity/exec group from the analyzer.
  - Cell content wraps or truncates (with `...`) to fit terminal width (`tput cols`, default 80).
  - TTY fallback: plain uncolored text when stderr is not a TTY.
  - If the user declines (or hits Ctrl-C), the launcher exits 0 with the plan committed to git -- the user can edit the plan and re-run `--continuous`. If the user approves, the launcher enters the continuous orchestration loop.
- The bootstrap log is written to `.purlin/runtime/continuous_build_bootstrap.log`.
- Bootstrap output is written to log files only; the terminal shows the canvas spinner (see Section 2.16).
- The bootstrap session does NOT receive the continuous phase override (Section 2.7) or server permission override (Section 2.8). It receives only the bootstrap-specific override.
- Bootstrap override text:

```
BOOTSTRAP MODE ACTIVE: You are running in non-interactive print mode to
initialize a delivery plan for continuous execution. There is no human user
present. You MUST:
- Execute your full startup protocol (Sections 2.0-2.3) including scope
  assessment.
- If scope assessment determines phasing IS warranted: create the delivery
  plan using /pl-delivery-plan WITHOUT asking for user approval. Auto-accept
  the phased delivery option. After committing the delivery plan, HALT
  IMMEDIATELY. Do not begin Phase 1.
- If scope assessment determines phasing is NOT warranted: proceed directly
  with implementation. Complete all work autonomously.
- NEVER ask "Ready to go?" or wait for any approval.
- SIZING BIAS: Prefer MORE phases over fewer. Prefer SMALLER phases over
  larger. Maximize parallelization -- group independent features into
  separate phases that can run concurrently. Each phase must be completable
  within a single session without context exhaustion. When in doubt, split.
This override takes precedence over any instruction to "wait for approval"
or "ask the user."
```

### 2.16 Terminal Canvas

All continuous mode status output renders into an **in-place terminal canvas** on stderr. The canvas is a block of lines below the command that is continuously cleared and rewritten via ANSI cursor control. Only the final exit summary is permanent output.

- **Canvas mechanics:** Each update uses cursor-up (`\033[<N>A`) + clear-to-end (`\033[J`) to overwrite the previous canvas content. The canvas tracks its own line count for accurate cursor positioning. On the first render, no cursor-up is emitted. All canvas output goes to stderr exclusively.

- **Builder output routing:** In continuous mode, ALL Builder output (bootstrap, sequential, and parallel) goes to log files only. No Builder output streams to the terminal. The terminal is exclusively owned by the canvas. This eliminates stdout/stderr interleaving problems.

- **Canvas refresh rate:** The canvas render loop runs at ~100ms for spinner frame animation. Heavier updates (log file size, activity extraction) run on 15-second intervals to avoid excessive I/O.

- **Color palette:**
  - Spinner: cyan (`\033[36m`)
  - Headers/titles: bold cyan (`\033[1;36m`)
  - Running/active: yellow (`\033[33m`)
  - Done/complete: green (`\033[32m`)
  - Error/warning/0K: red (`\033[31m`)
  - Elapsed time/metadata: dim (`\033[2m`)
  - Phase labels: bold white (`\033[1;37m`)
  - Reset: `\033[0m`

- **Spinner characters:** Braille animation sequence: `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`. Cycles at the canvas refresh rate (~100ms).

- **Bootstrap phase canvas:** While the bootstrap Builder runs, the canvas shows a single in-place line with an animated spinner and elapsed time:

```
⠹ Starting bootstrap session... 45s
```

  Spinner cycles through braille characters at ~100ms. Elapsed time updates every second. The line overwrites itself in place. Once bootstrap completes, the canvas clears and transitions to the plan approval table (Section 2.15) or exit state.

- **Approval checkpoint canvas:** When bootstrap creates a valid plan, the canvas clears the spinner and renders the colored console table (see Section 2.15 approval checkpoint for format). The table replaces the spinner content in the canvas area.

- **Inter-phase canvas:** Between phases (evaluator running, re-analysis), the canvas shows a spinner line:

```
⠼ Evaluating phase 2 output... 3s
```

  or

```
⠧ Re-analyzing delivery plan... 1s
```

- **Sequential phase canvas:** During sequential phase execution, the canvas shows a single-phase version of the heartbeat display with spinner, elapsed time, log file size, and current activity:

```
⠹ Phase 2 -- Policy Chain   running  2m 15s   45K  editing policy_release.md
```

  Activity is extracted from the log file tail (same extraction logic as parallel heartbeat). Updated on 15-second intervals.

- **Parallel phase canvas:** During parallel execution, the canvas shows the multi-line heartbeat display:

```
[19:34:58] Parallel group (3 phases):
             Phase 2 -- Non-Critical Anchors A   running  2m 15s   45K  editing arch_automated_feedback_tests.md
             Phase 3 -- Non-Critical Anchor B    running  2m 15s   23K  running aft-web on design_modal_standards.md
             Phase 5 -- Core Coordination        done     1m 42s   67K
```

  - One phase per line, indented from the timestamp header.
  - Phase labels extracted from delivery plan headings (`## Phase N -- Label`).
  - Per-phase elapsed time, frozen at exit for completed phases.
  - Per-phase log file size (e.g., `45K`).
  - Current activity for running phases, extracted from log file tail: file operations show `editing <file>`, test runs show `running tests on <feature>`, commands show `running <command>`, default shows `working...`. Activity text truncated to ~50 characters.
  - Status colors: yellow for running, green for done, red for done with 0K log size (diagnostic warning).
  - The canvas overwrites in place on each 15-second refresh. Spinner frames update at ~100ms between heavier refreshes.

- **Canvas lifecycle:** The canvas render loop (background subshell) is started at the beginning of each phase and terminated when the phase or group completes. For parallel groups, the canvas runs for the duration of the group (started when the group begins, terminated before merge). The canvas PID is tracked alongside Builder PIDs for cleanup.

- **Graceful stop (Ctrl+C):**
  - The launcher traps `SIGINT` to perform a graceful shutdown.
  - On first `SIGINT`: set a stop flag, send `SIGTERM` to any running Builder processes (parallel worktree PIDs or sequential Builder PID), terminate the canvas render loop, wait for processes to exit, clear the canvas, print the exit summary (see below), clean up worktrees, exit non-zero.
  - The stop is immediate -- it does not wait for the current phase to finish. Builder processes are terminated, not allowed to complete.
  - A second `SIGINT` during shutdown forces immediate exit. After the first `SIGINT` handler fires, the trap is reset to default (`trap - INT`) so standard bash behavior applies on the second signal.

- **Exit summary:** The canvas is cleared one final time. The exit summary prints as **permanent output** (not in-place -- it stays on screen). This is the only output that persists after the command exits. Format:

```
=== Continuous Build Summary ===
Status: completed | stopped (user interrupt) | failed (<reason>)
Duration: 12m 45s
Phases: 4/6 completed

  Phase 1 -- Critical Path Anchors      COMPLETE      3m 12s   features: policy_critic.md, design_visual_standards.md
  Phase 2 -- Non-Critical Anchors A     COMPLETE      2m 45s   features: design_artifact_pipeline.md, arch_automated_feedback_tests.md
  Phase 3 -- Non-Critical Anchor B      COMPLETE      1m 58s   features: design_modal_standards.md
  Phase 4 -- Policy Chain               INTERRUPTED            features: policy_release.md, policy_branch_collab.md
  Phase 5 -- Core Coordination          PENDING                features: impl_notes_companion.md
  Phase 6 -- Session Resume             PENDING                features: pl_session_resume.md

Retries: 1 (Phase 2)
Parallel groups: 1
Log files: .purlin/runtime/continuous_build_phase_*.log
================================
```

  - Per-phase status: `COMPLETE`, `INTERRUPTED` (was running when stopped), `SKIPPED` (evaluator said stop), `PENDING` (never started).
  - Per-phase duration for completed and interrupted phases.
  - Per-phase feature list from the delivery plan.
  - Retries called out by phase number.
  - Log file location reminder.
  - Exit summary uses the same color palette: bold cyan header/footer, green for COMPLETE, yellow for INTERRUPTED, red for SKIPPED/failed, dim for durations.

- **Post-run status refresh:** After printing the exit summary, the launcher runs `tools/cdd/status.sh` to regenerate the Critic report and update all `critic.json` files. This ensures the CDD dashboard reflects completed work (Builder TODOs clear to DONE for completed phases). Runs on every exit path: success, failure, and graceful stop. Does NOT run on second-SIGINT forced exit. The status refresh output is also permanent (not canvas).

- **TTY fallback:** When stderr is not a TTY (`! [ -t 2 ]`), no canvas is rendered. Instead, print minimal milestone lines: `"Bootstrap started"`, `"Bootstrap complete"`, `"Phase N started"`, `"Phase N complete"`, etc. No spinner, no color, no ANSI. One line per event, append-only.

- **Log file integrity:** Log files are always written identically regardless of canvas state. The evaluator reads from log files, not terminal output.

- **Non-continuous mode:** Without `--continuous`, no canvas is rendered. Behavior is unchanged from the current interactive launcher.

### 2.11 Default Behavior Preservation

- Without `--continuous`, `pl-run-builder.sh` MUST behave identically to its current implementation.
- The `--continuous` flag is entirely additive. No existing flags or behaviors change.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Continuous Flag Accepted
    Given pl-run-builder.sh is invoked with --continuous
    And a delivery plan exists with PENDING phases
    When the launcher starts
    Then it runs the phase analyzer to determine execution groups
    And it enters the continuous orchestration loop

#### Scenario: Default Behavior Without Continuous Flag
    Given pl-run-builder.sh is invoked without --continuous
    When the launcher starts
    Then it behaves identically to the current interactive launcher
    And no phase analyzer or evaluator is invoked

#### Scenario: Sequential Phase Completion
    Given --continuous is active
    And the phase analyzer returns 3 sequential groups
    When the Builder completes Phase 1 and the evaluator returns "continue"
    Then the launcher starts a new session for Phase 2
    And after Phase 2 the evaluator returns "continue"
    And the launcher starts a new session for Phase 3
    And after Phase 3 the evaluator returns "stop" with success reason
    Then the launcher exits with zero status

#### Scenario: Parallel Phase Execution
    Given --continuous is active
    And the phase analyzer returns a group with Phases 3 and 5 marked parallel
    When the launcher reaches that group
    Then it launches a Builder in a worktree for Phase 3
    And it launches a Builder in a worktree for Phase 5 concurrently
    And it waits for both to complete
    And it merges both worktree branches back to the main branch

#### Scenario: Parallel Phase Merge Conflict
    Given --continuous is active with parallel Phases 3 and 5
    When both Builders complete and the merge produces a conflict
    Then the launcher stops immediately
    And reports the conflicting files to stderr
    And exits with non-zero status

#### Scenario: Evaluator Returns Approve
    Given --continuous is active
    And the Builder outputs "Ready to go, or would you like to adjust the plan?"
    When the evaluator classifies the output
    Then it returns action "approve"
    And the launcher resumes the same session with "Approved. Proceed."
    And the evaluator runs again on the new output

#### Scenario: Evaluator Returns Retry
    Given --continuous is active
    And the Builder exits due to context exhaustion mid-phase
    When the evaluator classifies the output
    Then it returns action "retry"
    And the launcher starts a new session for the same phase

#### Scenario: Retry Limit Exceeded
    Given --continuous is active
    And the same phase has been retried 2 consecutive times
    When the evaluator returns "retry" a third time
    Then the launcher exits with an escalation message
    And identifies the stuck phase

#### Scenario: Evaluator Returns Stop on Error
    Given --continuous is active
    And the Builder outputs an INFEASIBLE escalation
    When the evaluator classifies the output
    Then it returns action "stop" with the error reason
    And the launcher exits with non-zero status

#### Scenario: All Phases Complete
    Given --continuous is active
    And the Builder deletes the delivery plan after the final phase
    When the evaluator classifies the output
    Then it returns action "stop" with a success reason
    And the launcher exits with zero status
    And the summary reports all phases completed successfully

#### Scenario: Bootstrap Creates Delivery Plan
    Given pl-run-builder.sh is invoked with --continuous
    And no delivery plan exists at .purlin/cache/delivery_plan.md
    When the launcher starts the bootstrap session
    And the bootstrap Builder creates a delivery plan and exits
    Then the launcher prints a plan summary (phase count, parallel groups)
    And prompts the user to approve the plan
    And the bootstrap log is written to .purlin/runtime/continuous_build_bootstrap.log

#### Scenario: Bootstrap Plan Approved
    Given the bootstrap session created a delivery plan
    When the user approves the plan at the approval checkpoint
    Then the launcher enters the continuous orchestration loop

#### Scenario: Bootstrap Plan Declined
    Given the bootstrap session created a delivery plan
    When the user declines at the approval checkpoint
    Then the launcher exits with zero status
    And the delivery plan remains committed to git for user editing

#### Scenario: Bootstrap Completes Work Directly
    Given pl-run-builder.sh is invoked with --continuous
    And no delivery plan exists at .purlin/cache/delivery_plan.md
    And the scope assessment determines phasing is not warranted
    When the bootstrap Builder completes all work and exits with zero status
    Then the launcher detects no delivery plan was created
    And exits successfully with a summary noting direct completion

#### Scenario: Bootstrap Failure
    Given pl-run-builder.sh is invoked with --continuous
    And no delivery plan exists at .purlin/cache/delivery_plan.md
    When the bootstrap Builder exits with non-zero status
    And no delivery plan was created
    Then the launcher prints an error directing the user to run an interactive session
    And exits with non-zero status

#### Scenario: Bootstrap Uses Distinct System Prompt Override
    Given pl-run-builder.sh is invoked with --continuous
    And no delivery plan exists
    When the bootstrap session is launched
    Then the Builder's system prompt includes the bootstrap override text
    And it does NOT include the continuous phase override (Section 2.7)
    And it does NOT include the server permission override (Section 2.8)

#### Scenario: Bootstrap Plan Validated Before Approval
    Given the bootstrap session created a delivery plan
    When the launcher runs the phase analyzer as a dry-run validation
    And the analyzer detects no dependency cycles or errors
    Then the launcher prints the plan summary
    And prompts the user for approval

#### Scenario: Bootstrap Plan Has Dependency Cycle
    Given the bootstrap session created a delivery plan
    When the launcher runs the phase analyzer as a dry-run validation
    And the analyzer detects a dependency cycle
    Then the launcher prints the cycle error with the involved phases
    And notes that the plan has been committed for manual editing
    And exits with zero status without entering the continuous loop

#### Scenario: Bootstrap Prefers Conservative Phase Sizing
    Given pl-run-builder.sh is invoked with --continuous
    And no delivery plan exists
    When the bootstrap session creates a delivery plan
    Then the plan prefers more smaller phases over fewer larger ones
    And independent features are placed in separate phases for parallel execution
    And each phase is sized to complete within a single session's context budget

#### Scenario: Evaluator Failure Fallback
    Given --continuous is active
    And the evaluator invocation fails (Haiku unavailable)
    When the launcher detects the evaluator failure
    Then it falls back to checking whether the delivery plan file changed
    And continues if the delivery plan was modified, stops if unchanged

#### Scenario: System Prompt Overrides Injected
    Given --continuous is active
    When the Builder's system prompt is assembled
    Then it includes the auto-proceed override text
    And it includes the server permission override text
    And these overrides appear after the standard BUILDER_BASE.md content

#### Scenario: Phase-Specific Builder Assignment
    Given --continuous is active with parallel phases
    When a Builder is launched for Phase 3
    Then its initial message specifies "you are assigned to Phase 3 ONLY"
    And the Builder works exclusively on Phase 3 features

#### Scenario: Logging Per Phase
    Given --continuous is active
    When Phase 2 completes
    Then the full Builder output is written to .purlin/runtime/continuous_build_phase_2.log

#### Scenario: Exit Summary Lists Per-Phase Details
    Given --continuous is active
    And 4 phases complete across 3 execution groups with 1 parallel group
    When the orchestration loop exits
    Then the summary includes an overall status line (completed, stopped, or failed)
    And the summary includes total wall-clock duration
    And the summary includes a completed/total phase count
    And the summary lists each phase with its label, status (COMPLETE/INTERRUPTED/SKIPPED/PENDING), duration, and feature list
    And the summary lists retries by phase number
    And the summary includes the log file location pattern

#### Scenario: Worktree Cleanup on Error
    Given --continuous is active with parallel phases running in worktrees
    When an error occurs during the parallel group
    Then all worktrees created for that group are cleaned up
    And no orphaned worktree directories remain

#### Scenario: Delivery Plan Updated Centrally
    Given --continuous is active with parallel phases
    When all Builders in a parallel group complete
    Then the orchestrator updates the delivery plan to mark completed phases
    And individual Builders do not modify the delivery plan during parallel execution

#### Scenario: Builder Adds QA Fix Phase Mid-Execution
    Given --continuous is active with Phases 1, 2, 3 PENDING
    And the Builder completes Phase 1 and adds Phase 4 (QA fixes) to the delivery plan
    When the evaluator returns "continue"
    Then the launcher re-runs the phase analyzer
    And the analyzer returns groups that include the new Phase 4
    And the loop proceeds with the next group from the fresh analysis

#### Scenario: Builder Splits Phase Into Two
    Given --continuous is active with Phases 1, 2 PENDING
    And the Builder completes Phase 1 and splits Phase 2 into Phase 2a and Phase 2b
    When the evaluator returns "continue"
    Then the launcher re-runs the phase analyzer
    And the analyzer processes Phases 2a and 2b as distinct PENDING phases
    And both are included in subsequent execution groups

#### Scenario: Builder Removes Remaining Phases
    Given --continuous is active with Phases 1, 2, 3 PENDING
    And the Builder completes Phase 1 and removes Phases 2 and 3 (scope collapsed)
    When the evaluator returns "continue"
    Then the launcher re-runs the phase analyzer
    And the analyzer returns empty groups (no PENDING phases)
    And the launcher exits successfully

#### Scenario: New Phase Has Dependencies on Completed Work
    Given --continuous is active
    And the Builder completed Phase 1 and added Phase 4 which depends on Phase 1 features
    When the evaluator returns "continue" and the analyzer runs
    Then Phase 4 is included in the execution groups
    And its dependency on Phase 1 (already COMPLETE) does not block it

#### Scenario: New Phase Creates New Dependency Chain
    Given --continuous is active with Phase 2 PENDING
    And the Builder completed Phase 1 and added Phase 5 which Phase 2 depends on
    When the evaluator returns "continue" and the analyzer runs
    Then Phase 5 is ordered before Phase 2 in the execution groups
    And the analyzer detects and respects the new dependency

#### Scenario: Parallel Group Invalidated by Plan Amendment
    Given --continuous is active
    And the initial analysis grouped Phases 3 and 5 as parallel
    And during Phase 2, the Builder adds Phase 6 which Phase 5 depends on
    When Phase 2 completes and the analyzer re-runs
    Then Phase 6 is ordered before Phase 5
    And Phase 5 is no longer grouped with Phase 3 (dependency changed)

#### Scenario: Parallel Builders Both Request Plan Amendments
    Given --continuous is active with Phases 3 and 5 running in parallel worktrees
    And Builder for Phase 3 writes a plan amendment request adding Phase 7 (QA fixes)
    And Builder for Phase 5 writes a plan amendment request adding Phase 8 (QA fixes)
    When both Builders complete and worktrees merge
    Then the orchestrator reads all amendment request files from merged worktrees
    And applies both amendments to the delivery plan on the main branch
    And the next re-analysis includes both Phase 7 and Phase 8 as PENDING

#### Scenario: Parallel Builder Amendment Requests Use Structured Files
    Given --continuous is active with parallel Builders
    When a parallel Builder needs to amend the delivery plan
    Then it writes a JSON amendment request to .purlin/runtime/plan_amendment_phase_<N>.json
    And it does NOT modify the delivery plan Markdown directly
    And the orchestrator applies amendments centrally after merge

#### Scenario: Phase Count Changes Reflected in Summary
    Given --continuous is active starting with 3 PENDING phases
    And the Builder adds 2 more phases during execution
    When all phases complete
    Then the exit summary reports 5 total phases completed
    And notes that the plan was amended during execution

#### Scenario: Re-Analysis After Retry
    Given --continuous is active
    And a phase fails and the evaluator returns "retry"
    And during the retry the Builder amends the plan
    When the retry completes and the evaluator returns "continue"
    Then the launcher re-runs the phase analyzer on the amended plan
    And picks up any changes made during the retry

#### Scenario: Builder Removes Some Phases But Not All
    Given --continuous is active with Phases 1, 2, 3, 4 PENDING
    And the Builder completes Phase 1 and removes Phase 3 (scope no longer needed)
    When the evaluator returns "continue"
    Then the launcher re-runs the phase analyzer
    And the analyzer returns groups containing Phases 2 and 4 only
    And Phase 3 does not appear in any execution group

#### Scenario: Non-Contiguous Phase Numbers After Amendment
    Given --continuous is active with Phases 1, 2, 3 PENDING
    And the Builder completes Phase 1 and adds Phase 7 (skipping 4-6)
    When the evaluator returns "continue"
    Then the launcher re-runs the phase analyzer
    And the analyzer processes Phases 2, 3, and 7 as PENDING
    And non-contiguous numbering does not cause an error

#### Scenario: Amendment Files Cleaned Up After Application
    Given --continuous is active with parallel Builders
    And Builder for Phase 3 writes .purlin/runtime/plan_amendment_phase_3.json
    And Builder for Phase 5 writes .purlin/runtime/plan_amendment_phase_5.json
    When both Builders complete and the orchestrator applies the amendments
    Then .purlin/runtime/plan_amendment_phase_3.json is deleted
    And .purlin/runtime/plan_amendment_phase_5.json is deleted
    And the amendments are reflected in the delivery plan Markdown

#### Scenario: Sequential Builder Modifies Delivery Plan Directly
    Given --continuous is active with a sequential (non-parallel) execution group
    And the Builder completes Phase 2 and adds Phase 6 directly in the delivery plan Markdown
    When the evaluator returns "continue"
    Then the launcher re-runs the phase analyzer
    And Phase 6 appears as PENDING in the analysis results
    And no amendment request file was needed for the sequential Builder

#### Scenario: Removed Phase Had Dependents
    Given --continuous is active with Phases 1, 2, 3 PENDING
    And Phase 3 depends on Phase 2
    And the Builder completes Phase 1 and removes Phase 2
    When the evaluator returns "continue"
    Then the launcher re-runs the phase analyzer
    And Phase 3's dependency on the removed Phase 2 is no longer blocking
    And the analyzer includes Phase 3 in the execution groups

#### Scenario: Bootstrap Canvas Shows Spinner During Initialization
    Given pl-run-builder.sh is invoked with --continuous
    And no delivery plan exists at .purlin/cache/delivery_plan.md
    And stderr is a TTY
    When the bootstrap session starts
    Then the canvas shows a single in-place line with an animated braille spinner and elapsed time
    And the spinner cycles through braille characters at ~100ms
    And the elapsed time updates every second
    And the line overwrites itself in place (no new rows appended)
    And Builder output is written only to .purlin/runtime/continuous_build_bootstrap.log (not the terminal)
    And when bootstrap completes the canvas clears and transitions to the plan approval table or exit state

#### Scenario: Approval Checkpoint Renders Console Table
    Given pl-run-builder.sh is invoked with --continuous
    And the bootstrap session created a valid delivery plan
    And stderr is a TTY
    When the canvas transitions to the approval checkpoint
    Then the canvas clears the spinner and renders a fixed-width console table
    And the table has columns for phase number, label, features, complexity, and exec group
    And the header row uses bold cyan ANSI coloring
    And separator lines use green ANSI coloring
    And cell content wraps or truncates with "..." to fit terminal width (tput cols)
    And the table includes a parallel groups summary line
    And the table includes a delivery plan file path reference
    And the table ends with a "Proceed? [Y/n]" prompt

#### Scenario: Sequential Phase Canvas During Execution
    Given --continuous is active
    And the phase analyzer returns a sequential group for Phase 2
    And stderr is a TTY
    When the Builder runs Phase 2
    Then the canvas shows a single-phase display with spinner, elapsed time, log size, and current activity
    And Builder output is written only to .purlin/runtime/continuous_build_phase_2.log (not the terminal)
    And the canvas overwrites in place on each refresh
    And activity is extracted from the log file tail on 15-second intervals

#### Scenario: Parallel Phase Canvas During Execution
    Given --continuous is active
    And the phase analyzer returns a parallel group with Phases 3 and 5
    And stderr is a TTY
    When both parallel Builders are running
    Then the canvas shows a multi-line heartbeat display on stderr
    And the display has a timestamp header line followed by one indented line per phase
    And each phase line includes the phase label from the delivery plan heading
    And each phase line includes the status (running or done), elapsed time, log file size, and current activity
    And running phases show activity extracted from the log file tail (truncated to ~50 chars)
    And status colors are applied: yellow for running, green for done, red for done with 0K log
    And the canvas overwrites in place via ANSI cursor-up and clear-to-end sequences

#### Scenario: All Builder Output Routes to Log Files in Continuous Mode
    Given --continuous is active
    When any Builder runs (bootstrap, sequential, or parallel)
    Then the Builder's stdout and stderr are written exclusively to the phase log file
    And no Builder output is streamed to the terminal
    And the terminal is exclusively owned by the canvas
    And the log file content is complete regardless of terminal rendering

#### Scenario: Inter-Phase Canvas Shows Evaluator Status
    Given --continuous is active
    And a phase has just completed
    And stderr is a TTY
    When the evaluator runs to classify the Builder output
    Then the canvas shows a spinner line with "Evaluating phase N output..." and elapsed time
    And when re-analysis runs the canvas shows "Re-analyzing delivery plan..." with elapsed time
    And the spinner uses the same braille animation as the bootstrap canvas

#### Scenario: Canvas Clears Before Final Summary
    Given --continuous is active
    And the orchestration loop is exiting (success, failure, or graceful stop)
    And stderr is a TTY
    When the exit summary is about to print
    Then the canvas is cleared one final time via ANSI clear sequences
    And the exit summary prints as permanent output (not in-place)
    And the exit summary is the only continuous mode output that persists on screen after exit
    And the exit summary uses colored output: bold cyan header, green for COMPLETE, yellow for INTERRUPTED, red for SKIPPED

#### Scenario: Canvas Falls Back to Milestone Lines When Not a TTY
    Given --continuous is active
    And stderr is not a TTY (e.g., piped to a file)
    When continuous mode phases execute
    Then no canvas is rendered (no ANSI sequences, no spinner, no in-place overwriting)
    And milestone lines are printed instead: "Bootstrap started", "Bootstrap complete", "Phase N started", "Phase N complete"
    And each milestone is a single append-only line without color
    And the approval checkpoint renders as plain uncolored text

#### Scenario: Canvas Render Loop Lifecycle
    Given --continuous is active
    And stderr is a TTY
    When a phase or parallel group begins execution
    Then a background canvas render loop is started
    And the render loop PID is tracked alongside Builder PIDs
    And the render loop is terminated when the phase or group completes (before merge for parallel groups)
    And no orphaned render loop processes remain after phase completion

#### Scenario: Resume Session Log Appended
    Given --continuous is active
    And the evaluator returned "approve" for Phase 2
    And .purlin/runtime/continuous_build_phase_2.log already contains output from the initial run
    When the launcher resumes the session with "Approved. Proceed."
    Then the resumed output is appended to the existing log file
    And the log file contains both the initial and resumed output
    And the canvas shows the phase spinner during the resumed session

#### Scenario: Canvas Shows Current Builder Activity
    Given --continuous is active with a phase running
    And stderr is a TTY
    And the Builder is currently editing a file
    When the canvas performs a 15-second activity refresh
    Then the phase line shows the current activity (e.g., "editing arch_automated_feedback_tests.md")
    And the activity text is truncated to ~50 characters if longer

#### Scenario: Canvas Warns on Empty Log at Phase Completion
    Given --continuous is active
    And a Builder process has exited
    And the phase log file has 0K size
    When the canvas displays the phase status
    Then the phase line shows "done" with a red warning marker
    And the 0K size is displayed to indicate the diagnostic condition

#### Scenario: Graceful Stop on SIGINT
    Given --continuous is active
    And a Builder process is currently running (sequential or parallel)
    When the user sends SIGINT (Ctrl+C)
    Then the launcher sets a stop flag and sends SIGTERM to all running Builder processes
    And the canvas render loop is terminated (if running)
    And the launcher waits for processes to exit
    And the canvas is cleared before the exit summary prints
    And the exit summary is printed with status "stopped (user interrupt)"
    And worktrees are cleaned up
    And the launcher exits with non-zero status

#### Scenario: Second SIGINT Forces Immediate Exit
    Given --continuous is active
    And a graceful stop is in progress (first SIGINT was received)
    When the user sends a second SIGINT
    Then the launcher exits immediately without printing a summary
    And no cleanup is performed

#### Scenario: Post-Run Status Refresh
    Given --continuous is active
    And the orchestration loop has exited (success, failure, or graceful stop)
    And the exit summary has been printed
    When the launcher performs post-run cleanup
    Then it runs tools/cdd/status.sh to regenerate the Critic report
    And the status refresh output is permanent (not canvas)
    And the CDD dashboard reflects the completed work from this run

### Manual Scenarios (Human Verification Required)
None.
