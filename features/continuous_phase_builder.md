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
- Optional pass-through flags: `--max-turns N` and `--max-budget-usd N`, forwarded to each `claude -p` invocation.

### 2.2 Phase Analyzer Integration

- Before the first phase, run `tools/delivery/phase_analyzer.py` to determine execution groups.
- If the phase analyzer exits with an error (no delivery plan, no dependency graph), the launcher MUST print the error and exit.
- The launcher iterates through execution groups in the order returned by the analyzer.

### 2.3 Sequential Phase Execution

- For execution groups with a single phase (`parallel: false`), run the Builder in `-p` mode.
- Each phase invocation uses a named session: `continuous-phase-<phase_number>-<timestamp>`.
- The Builder is invoked with `claude -p -n <session_name>` plus all resolved config flags (model, effort, permissions) and the assembled system prompt.
- The initial message includes phase-specific context: `"Begin Builder session. CONTINUOUS MODE -- proceed immediately with work plan, do not wait for approval."`.

### 2.4 Parallel Phase Execution

- For execution groups with multiple phases (`parallel: true`), launch each phase's Builder in a separate git worktree.
- Each parallel Builder is invoked with `claude -p -w <worktree-name>` where the worktree name is `continuous-phase-<phase_number>`.
- Each parallel Builder receives a phase-specific prompt: `"Begin Builder session. CONTINUOUS MODE -- you are assigned to Phase <N> ONLY. Work exclusively on Phase <N> features. Do not wait for approval."`.
- The launcher waits for all parallel Builders in the group to complete before proceeding.
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
- At exit, the launcher prints a summary: phases completed, parallel groups used, any failures, retries consumed, total wall-clock duration.

### 2.10 Error Handling

- No delivery plan at launch: print error, exit non-zero.
- Phase analyzer failure: print error, exit non-zero.
- Evaluator invocation failure (Haiku unavailable, malformed JSON): fall back to delivery plan hash check. If the delivery plan file changed since the last phase, treat as `continue`. If unchanged and Builder exited, treat as `stop`.
- Merge conflict during parallel merge: stop immediately, report conflicting files, exit non-zero.
- Orphaned worktrees on error: clean up any worktrees created during the current run.
- Retry limit exceeded: exit with message identifying the stuck phase and suggesting manual intervention.

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

#### Scenario: No Delivery Plan at Launch
    Given pl-run-builder.sh is invoked with --continuous
    And no delivery plan exists at .purlin/cache/delivery_plan.md
    When the launcher starts
    Then it prints an error message about missing delivery plan
    And exits with non-zero status

#### Scenario: Evaluator Failure Fallback
    Given --continuous is active
    And the evaluator invocation fails (Haiku unavailable)
    When the launcher detects the evaluator failure
    Then it falls back to checking whether the delivery plan file changed
    And continues if the delivery plan was modified, stops if unchanged

#### Scenario: Pass-Through Flags Forwarded
    Given pl-run-builder.sh is invoked with --continuous --max-turns 50 --max-budget-usd 10
    When each phase Builder is invoked
    Then --max-turns 50 is passed to the claude -p invocation
    And --max-budget-usd 10 is passed to the claude -p invocation

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

#### Scenario: Exit Summary
    Given --continuous is active
    And 4 phases complete across 3 execution groups with 1 parallel group
    When the orchestration loop exits
    Then the summary reports: 4 phases completed, 3 groups (1 parallel), total duration
    And any retries or failures are listed

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

### Manual Scenarios (Human Verification Required)
None.
