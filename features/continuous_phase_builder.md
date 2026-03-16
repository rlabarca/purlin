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
- Optional pass-through flag: `--max-budget-usd N`, forwarded to each `claude -p` invocation.

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
- **Approval checkpoint:** When bootstrap creates a valid delivery plan, the launcher prints a summary to stdout (phase count, features per phase, identified parallel groups) and prompts the user: `"Delivery plan created (N phases). Review at .purlin/cache/delivery_plan.md. Proceed? [Y/n]"`. If the user declines (or hits Ctrl-C), the launcher exits 0 with the plan committed to git -- the user can edit the plan and re-run `--continuous`. If the user approves, the launcher enters the continuous orchestration loop.
- The bootstrap log is written to `.purlin/runtime/continuous_build_bootstrap.log`.
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

#### Scenario: Pass-Through Flags Forwarded
    Given pl-run-builder.sh is invoked with --continuous --max-budget-usd 10
    When each phase Builder is invoked
    Then --max-budget-usd 10 is passed to the claude -p invocation

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

### Manual Scenarios (Human Verification Required)
None.
