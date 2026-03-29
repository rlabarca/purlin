# Feature: Sub-Agent Pipeline Delivery

> Label: "Tool: Sub-Agent Pipeline Delivery"
> Category: "Install, Update & Scripts"
> Prerequisite: purlin_agent_launcher.md

## 1. Overview

Formalizes cross-mode parallel delivery with dedicated sub-agent definitions for all three modes: `engineer-worker`, `pm-worker`, `qa-worker`, and `verification-runner`. Enables a pipeline execution model where features progress through PM → Engineer → QA stages independently, with features at different stages running in parallel via isolated worktrees. Includes a robust rebase-before-merge protocol, server lifecycle management, enriched PreCompact checkpointing for pipeline state recovery, and autonomous multi-feature delivery via the work plan coordination artifact.

---

## 2. Requirements

### 2.1 Sub-Agent Definitions

Four sub-agent definition files MUST exist in `.claude/agents/`:

#### 2.1.1 `engineer-worker.md`

Parallel feature builder for pipeline delivery. Implements a single feature in an isolated worktree.

*   **Frontmatter:**
    ```yaml
    name: engineer-worker
    description: >
      Parallel feature builder for pipeline delivery. Implements a single feature
      in an isolated worktree. Use when building independent features concurrently.
    tools: Read, Write, Edit, Bash, Glob, Grep
    isolation: worktree
    skills: [purlin:build]
    permissionMode: bypassPermissions
    model: inherit
    maxTurns: 200
    ```
*   **System prompt constraints:**
    - Single-feature focus: implements one feature only per invocation.
    - Steps 0-2 only from `purlin:build`. No Step 3 (verification), no Step 4 (status tags).
    - MUST NOT modify the work plan (`.purlin/work_plan.md`).
    - MUST NOT spawn nested sub-agents (no Agent tool access).
    - Commit with `feat(scope): implement FEATURE_NAME`.
    - Activates Engineer mode in its worktree (PID-scoped mode file).

#### 2.1.2 `pm-worker.md`

Spec authoring sub-agent for pipeline delivery. Writes or refines a single feature spec in an isolated worktree.

*   **Frontmatter:**
    ```yaml
    name: pm-worker
    description: >
      Spec authoring sub-agent for pipeline delivery. Writes or refines a single
      feature spec in an isolated worktree. Use for parallel spec work.
    tools: Read, Write, Edit, Bash, Glob, Grep
    isolation: worktree
    skills: [purlin:spec]
    permissionMode: bypassPermissions
    model: inherit
    maxTurns: 150
    ```
*   **System prompt constraints:**
    - Single-feature focus: writes or refines one feature spec per invocation.
    - Activates PM mode in its worktree (PID-scoped mode file).
    - MUST NOT write code, tests, scripts, or instruction files.
    - MUST NOT modify the work plan (`.purlin/work_plan.md`).
    - MUST NOT spawn nested sub-agents (no Agent tool access).
    - Commit with `spec(scope): define FEATURE_NAME` or `spec(scope): refine FEATURE_NAME`.
    - Returns: spec file path, prerequisite graph updates if dependencies changed.

#### 2.1.3 `qa-worker.md`

Verification sub-agent for pipeline delivery. Verifies a single feature in an isolated worktree.

*   **Frontmatter:**
    ```yaml
    name: qa-worker
    description: >
      Verification sub-agent for pipeline delivery. Verifies a single feature
      in an isolated worktree. Use for parallel QA verification.
    tools: Read, Write, Edit, Bash, Glob, Grep
    isolation: worktree
    skills: [purlin:verify]
    permissionMode: bypassPermissions
    model: inherit
    maxTurns: 150
    ```
*   **System prompt constraints:**
    - Single-feature focus: verifies one feature per invocation.
    - Activates QA mode in its worktree (PID-scoped mode file).
    - Runs Phase A (automated verification) of `purlin:verify`. Writes discoveries.
    - MUST NOT write code or feature specs.
    - MUST NOT mark `[Complete]` — the orchestrator handles final status after cross-feature checks.
    - MUST NOT modify the work plan (`.purlin/work_plan.md`).
    - MUST NOT spawn nested sub-agents (no Agent tool access).
    - Returns: verification result (PASS/FAIL), discovery list.

#### 2.1.4 `verification-runner.md`

Runs automated tests in background during B2, keeping test output out of main session context.

*   **Frontmatter:**
    ```yaml
    name: verification-runner
    description: >
      Test execution agent. Runs automated tests and reports structured results.
      Use after code changes to verify implementations.
    tools: Read, Write, Bash, Glob, Grep
    disallowedTools: Edit, Agent
    skills: [pl-unit-test]
    model: haiku
    background: true
    maxTurns: 50
    ```
*   **System prompt constraints:**
    - Run the `purlin:unit-test` protocol for specified features. The skill is preloaded with the complete testing protocol (quality rubric, anti-pattern scan, result reporting).
    - Write `tests.json` results. `Write` is allowed only for `tests.json` output.
    - MUST NOT fix code or edit implementation files.

### 2.2 Pipeline Dispatch Protocol

When a work plan exists, the orchestrator MUST use the pipeline dispatch loop to advance features through their stages using cross-mode sub-agents. The dispatch protocol in `purlin:build` determines which features are ready and dispatches them:

1.  Read `.purlin/work_plan.md`, `.purlin/cache/dependency_graph.json`, and scan state.
2.  For each feature in priority order, determine the next action:
    - PM PENDING → dispatch `pm-worker` sub-agent.
    - Engineer PENDING (and dependencies met) → dispatch `engineer-worker` sub-agent.
    - QA PENDING (and Engineer COMPLETE, and verification group B2 passed) → dispatch `qa-worker` sub-agent.
3.  Dispatch to available worktree slots (max concurrent from config, default 3).
4.  Cross-mode parallelism: a `pm-worker`, `engineer-worker`, and `qa-worker` MAY run simultaneously in separate worktrees on different features. This is safe because PM writes specs, Engineer writes code, and QA writes discoveries -- disjoint file sets.
5.  Wait for any sub-agent to complete. Merge the returned branch using the robust merge protocol (Section 2.4).
6.  Update the work plan: advance the feature's stage, update mode column status.
7.  When all features in a verification group complete Engineer stage → run B2/B3 in main session.
8.  Continue until all features reach `complete` or all remaining features are blocked.
9.  If only 1-2 features or tight dependencies: fall back to sequential single-session work.

### 2.3 B2 Verification with verification-runner

During B2 (Test Sub-Phase), Engineer mode SHOULD use the `verification-runner` sub-agent for automated test execution:

*   Spawn `verification-runner` as a background agent for each feature's test suite.
*   The main Engineer session retains MCP access for web tests and Figma checks, running those concurrently.
*   The `verification-runner` writes `tests.json` results that the main session reads after completion.

### 2.4 Robust Merge Protocol

Replace the current `git merge <branch> --no-edit` with abort-on-conflict with a rebase-before-merge strategy:

1.  After all parallel workers complete, process branches in sequence.
2.  For each branch: `git rebase HEAD <branch>`.
3.  On rebase conflict: check if ALL conflicting files are in the safe list.
    *   **Safe files:** `.purlin/work_plan.md`, `.purlin/cache/*`.
    *   Safe: auto-resolve by keeping main's version (`git checkout --ours`), then `git add` and `git rebase --continue`.
    *   Unsafe (any non-safe file in conflict): `git rebase --abort`, fall back to sequential for THIS feature only.
4.  Loop up to 20 rebase iterations for multi-commit branches.
5.  After rebase: fast-forward merge (`git merge <branch> --no-edit`).
6.  On merge conflict: same safe-file auto-resolve logic.
7.  Only sequential fallback for actual code conflicts -- preserves already-merged features.

**Source reference:** The `try_auto_resolve_conflicts()` logic and rebase loop are implemented in the plugin's merge protocol handler.

### 2.5 Instruction Consolidation

**Goal:** Implementation knowledge lives in skills (preloadable by sub-agents). Base instructions contain only session orchestration.

#### 2.5.1 Move Remaining Bright-Line Rules into `purlin:build`

*   `PURLIN_BASE.md` Section 5 currently contains ~15 bright-line rules. Testing rules already reference `purlin:unit-test`.
*   Move all remaining non-testing bright-line rules (web test verification, phase halt, cross-cutting triage, regression handoff) into `purlin:build`.
*   `PURLIN_BASE.md` Section 5 becomes:
    ```
    ## 5. Per-Feature Implementation Protocol
    Invoke `purlin:build` for the complete per-feature protocol including all bright-line rules.
    Testing protocol: `purlin:unit-test` (invoked by `purlin:build` Step 3).
    ```
*   This completes the extraction pattern that `purlin:unit-test` already started.

#### 2.5.2 Delete Section 7 (Agentic Team Orchestration)

*   Two vague lines with no actionable content. Sub-agent patterns are now defined by the sub-agent definitions themselves.

#### 2.5.3 Extract Server Lifecycle into `purlin:server`

*   `PURLIN_BASE.md` Section 8 server rules move to a new `purlin:server` skill (`.claude/commandspurlin:server.md`).
*   `PURLIN_BASE.md` Section 8 retains only non-server build/environment rules.

#### 2.5.4 Resulting `PURLIN_BASE.md` Structure

```
1. Executive Summary (role identity)
2. Startup Protocol (scan, work discovery, plan proposal)
3. Feature Status Lifecycle
4. Tombstone Processing
5. Per-Feature Implementation Protocol (pointer to purlin:build)
6. Shutdown Protocol
7. [deleted]
8. Build & Environment Protocols (non-server rules only)
9. Command Authorization
```

### 2.6 Server Lifecycle Skill

A new skill at `.claude/commandspurlin:server.md` with the following capabilities:

#### 2.6.1 Port Management

*   Before starting a dev server: check if default port is in use (`lsof -i :<port>`).
*   If occupied: select alternate port (default + 100, e.g., 3000 -> 3100).
*   Announce to user: "Starting dev server on port XXXX".

#### 2.6.2 State Tracking

*   Write server PID and port to `.purlin/runtime/dev_server.json`:
    ```json
    {"pid": N, "port": N, "command": "...", "started_at": "..."}
    ```
*   This file is gitignored (runtime artifact).
*   Makes server state discoverable by other tools and the user.

#### 2.6.3 Cleanup Guarantee

*   Register cleanup in session: server MUST be stopped when verification completes.
*   On session end: check `.purlin/runtime/dev_server.json`, kill tracked PID if still running.
*   On session start: check for stale `dev_server.json`, warn user if process is still running from a previous session.

#### 2.6.4 User Visibility

*   Print server state on start: `Dev server running: http://localhost:3100 (PID 12345)`.
*   Print on stop: `Dev server stopped (port 3100)`.
*   If server fails to start: clear error with port and command.

#### 2.6.5 Unchanged Rules

*   NEVER manage persistent/production servers.
*   NEVER use kill/pkill on processes not started in current session.
*   Use `> Web Start:` command from feature spec when available.

### 2.7 Pipeline Auto-Progression

When `auto_start: true` in Purlin agent config:

*   The orchestrator works through the entire feature list across all modes without pausing at verification checkpoints.
*   Only stops for major plan amendments (new features added, dependencies restructured) or unresolvable blockers.
*   When `auto_start: false` (default), the orchestrator pauses at verification checkpoints (after B2 completes for each verification group) for user review before continuing.
*   The orchestrator runs all features through the complete PM → Engineer → QA pipeline in a single session.

### 2.8 Continuous Mode Deprecation

*   The `--continuous` flag and shell launcher `pl-run.sh` are retired. Sessions are started via `claude` with the Purlin plugin auto-activating. Pipeline auto-progression is handled by the `auto_start: true` config setting within the interactive session (see Section 2.7).
*   `features/continuous_phase_builder.md` gets a tombstone for code removal (see `features/_tombstones/continuous_phase_builder.md`).
*   Deprecated config keys: `continuous_evaluator_model`, `max_remediation_attempts`.
*   Deprecated runtime artifacts: `.purlin/runtime/continuous_build_phase_*.log`, phase status JSON, evaluator state files.

### 2.9 Context Recovery

#### 2.9.1 Orphaned Sub-Agent Branches

On `purlin:resume`, the orchestrator MUST check for orphaned worktree branches matching the pattern `purlin-*`:
*   If found: attempt to merge them using the robust merge protocol (Section 2.4), then continue.
*   If not found: the sub-agents either completed and merged, or never started. The work plan + scan state tells the orchestrator what remains.

#### 2.9.2 Enriched PreCompact Checkpoint

The PreCompact hook (`pre-compact-checkpoint.sh`) MUST save enriched pipeline state by reading disk artifacts:
*   **Mode:** Read from `.purlin/runtime/current_mode_*` (PID-scoped mode file).
*   **Work plan summary:** Read first 20 lines of `.purlin/work_plan.md` (pipeline status table).
*   **Recent commits:** `git log --oneline -5` for context.
*   **Active worktrees:** Count from `git worktree list`.

This gives `purlin:resume` enough to reconstruct pipeline state without a full scan.

#### 2.9.3 Pipeline Continuity

On resume, the orchestrator:
1.  Reads work plan -- identifies each feature's current stage and per-mode status.
2.  Reads scan results -- identifies which features have progressed since the checkpoint.
3.  Checks for orphaned worktree branches -- merges if found.
4.  Updates work plan with any state changes discovered during recovery.
5.  Re-enters the pipeline dispatch loop (Section 2.2) from the current state.
6.  Continues dispatching features through their remaining stages (if `auto_start: true`).

### 2.10 Distribution to Consumer Projects

#### 2.10.1 Init Changes

*   Add `copy_agent_files()` function to `tools/init.sh` (same pattern as `copy_command_files()`).
*   Source: `<submodule>/.claude/agents/`.
*   Destination: `<project_root>/.claude/agents/`.
*   Same skip logic: preserve locally modified versions (timestamp comparison).
*   Called during both full init and refresh modes.

#### 2.10.2 Update Changes

*   `purlin:update` extends conflict detection to also scan `.claude/agents/` for local modifications vs upstream changes.
*   Same resolution options: "Accept upstream", "Keep current", "Smart merge".

### 2.11 Lifecycle Metadata Hash Exemption

The lifecycle content hash MUST exclude blockquote metadata lines (`> Key: Value` at the top of feature files) when determining whether a feature spec has changed. Only body content (Overview, Requirements, Scenarios, Visual Specification) contributes to the hash. This uses an explicit allow-list of known metadata keys (`Label`, `Category`, `Prerequisite`, `Owner`, `Web Test`, `Web Start`, `AFT Web`, `AFT Start`, `Test Fixtures`, `Figma Status`, `Regression Coverage`). Unknown blockquote keys are preserved in the hash (conservative).

### 2.12 Sync Invariants

*   `purlin:build` preloading by `engineer-worker` auto-syncs all conventions (bright-line rules, commit formats, decision tags) to sub-agents.
*   `purlin:unit-test` preloading by `verification-runner` auto-syncs the testing protocol.
*   When a convention changes in the skill file, sub-agents inherit the change on next invocation with zero manual propagation.

### 2.13 Pipeline Dispatch Bright-Line Rule

Pipeline dispatch MUST appear as a named bright-line rule in `purlin:build`,
not only as a standalone section. The rule text:

> **Pipeline dispatch is mandatory when a work plan exists.** When `.purlin/work_plan.md`
> exists and contains 2+ features, the orchestrator MUST use the pipeline dispatch loop
> (Section 2.5 of `purlin:build`). MUST read `dependency_graph.json`, determine feature
> independence, and dispatch cross-mode sub-agents (`pm-worker`, `engineer-worker`,
> `qa-worker`) for features ready at different pipeline stages. Sequential processing
> of independent features without checking the work plan is a protocol violation.


---

## 3. Scenarios

### Unit Tests

#### Scenario: Pipeline dispatches cross-mode sub-agents in parallel

    Given a work plan with feature A at stage "engineer" and feature B at stage "qa"
    And features A and B have no cross-dependencies
    When the pipeline dispatch loop runs
    Then it spawns an engineer-worker for feature A in an isolated worktree
    And a qa-worker for feature B in another isolated worktree
    And both sub-agents run simultaneously

#### Scenario: PM-worker writes spec in isolated worktree

    Given a work plan with feature C at stage "pm" with PM PENDING
    When the pipeline dispatch loop dispatches a pm-worker for feature C
    Then the pm-worker activates PM mode in its worktree
    And writes the feature spec
    And commits with "spec(scope): define FEATURE_NAME"
    And does NOT write code or tests

#### Scenario: QA-worker verifies feature in isolated worktree

    Given a work plan with feature D at stage "qa" with QA PENDING
    When the pipeline dispatch loop dispatches a qa-worker for feature D
    Then the qa-worker activates QA mode in its worktree
    And runs Phase A automated verification
    And writes discoveries
    And does NOT mark [Complete] (orchestrator handles that)

#### Scenario: Engineer-worker runs Steps 0-2 only

    Given an engineer-worker sub-agent is spawned for feature A
    When the sub-agent completes its work
    Then it has run Steps 0-2 (pre-flight, plan, implement)
    And it has NOT run Step 3 (verification) or Step 4 (status tags)
    And it has NOT modified the work plan

#### Scenario: Sub-agents cannot spawn nested sub-agents

    Given any sub-agent (engineer-worker, pm-worker, or qa-worker) is running
    When the sub-agent's tool list is inspected
    Then the Agent tool is not available
    And the sub-agent cannot launch nested sub-agents

#### Scenario: Sub-agent hits maxTurns safety limit

    Given a sub-agent is running
    When it reaches its maxTurns limit
    Then the sub-agent stops execution
    And the main session handles the incomplete feature sequentially

#### Scenario: verification-runner runs tests in background during B2

    Given the orchestrator has completed B1 for all features in a verification group
    When the orchestrator enters B2
    Then it spawns verification-runner sub-agents in the background
    And each verification-runner runs purlin:unit-test for its assigned feature
    And the main session runs web tests concurrently with MCP access

#### Scenario: verification-runner cannot edit files

    Given a verification-runner sub-agent is running
    When the sub-agent's disallowed tools are inspected
    Then Edit and Agent are disallowed
    And Write is allowed only for tests.json output

#### Scenario: Three modes run simultaneously in separate worktrees

    Given a work plan with 5 features at different stages
    And max_concurrent_worktrees is 3
    When the pipeline dispatch loop runs
    Then up to 3 worktrees run simultaneously
    And each worktree has a different mode (PM, Engineer, or QA)
    And mode-guard enforces write boundaries per-worktree via PID-scoped mode files

#### Scenario: Safe file conflicts auto-resolve during merge

    Given two sub-agent branches both modified .purlin/work_plan.md
    When the robust merge protocol runs rebase-before-merge
    Then the conflict on .purlin/work_plan.md is auto-resolved by keeping main's version
    And the merge completes successfully

#### Scenario: Unsafe conflict falls back to sequential for that feature only

    Given engineer-worker branch A modified src/app.py
    And the main branch also modified src/app.py
    When the robust merge protocol encounters the conflict
    Then it aborts the rebase for branch A
    And falls back to sequential building for feature A only
    And already-merged features from other branches are preserved

#### Scenario: Rebase-before-merge reduces conflicts from parallel branches

    Given three engineer-worker branches completed
    And branches B and C both added lines to the same config file (safe file)
    When the robust merge protocol processes branches sequentially
    Then branch B is rebased onto HEAD and merged
    And branch C is rebased onto the new HEAD (which includes B)
    And the merge succeeds without conflict

#### Scenario: Multi-commit rebase with iterative safe-file resolution

    Given a engineer-worker branch has 5 commits
    And 2 of those commits touch .purlin/work_plan.md
    When the robust merge protocol runs rebase
    Then it iterates through each commit's conflicts
    And auto-resolves safe file conflicts at each step
    And the rebase completes within 20 iterations

#### Scenario: Orchestrator continues through pipeline when auto_start is true

    Given auto_start is true in Purlin agent config
    And a work plan has features at different pipeline stages
    When the orchestrator completes a verification group's B2
    Then it immediately continues dispatching remaining features
    And does not pause for user review

#### Scenario: Orchestrator pauses at verification checkpoint when auto_start is false

    Given auto_start is false in Purlin agent config
    And a verification group's B2 completes
    When the orchestrator reaches the verification checkpoint
    Then it pauses for user review
    And resumes dispatching when the user continues

#### Scenario: Pipeline dispatches cross-mode agents for multi-feature work

    Given auto_start is true
    And a work plan has 5 features at different stages
    When the pipeline dispatch loop runs
    Then it dispatches up to 3 concurrent sub-agents across PM, Engineer, and QA modes
    And merges results using the robust merge protocol
    And advances features through their stages

#### Scenario: Pipeline completes all features in a single session

    Given auto_start is true
    And a work plan has 4 features
    When the orchestrator completes all features through the full pipeline
    Then all features reach stage "complete"
    And the work plan is deleted
    And no external orchestration was involved

#### Scenario: Pipeline auto-start replaces continuous mode

    Given the user wants autonomous multi-feature delivery
    When the user sets auto_start: true in agent config
    And starts a session via claude (plugin auto-activates)
    Then purlin:resume reads the auto_start setting from resolved config
    And the orchestrator runs the pipeline dispatch loop without halting

#### Scenario: Bright-line rules exist only in purlin:build skill

    Given PURLIN_BASE.md Section 5 is read
    Then it contains only a pointer to purlin:build
    And it does not contain web test verification rules
    And it does not contain phase halt rules
    And it does not contain cross-cutting triage rules

#### Scenario: PURLIN_BASE.md Section 5 contains only skill invocation pointer

    Given PURLIN_BASE.md is read
    When Section 5 is inspected
    Then it contains "Invoke purlin:build" text
    And it contains "Testing protocol: purlin:unit-test" text
    And the section is fewer than 10 lines

#### Scenario: Sub-agent preloading purlin:build gets all bright-line rules

    Given a engineer-worker sub-agent has skills: [purlin:build]
    When the sub-agent's preloaded context is inspected
    Then the purlin:build skill content includes all bright-line rules
    And the sub-agent has the complete per-feature protocol

#### Scenario: Dev server starts on alternate port when default occupied

    Given port 3000 is already in use
    When the purlin:server skill starts a dev server
    Then it detects port 3000 is occupied
    And starts the server on port 3100 instead
    And prints: "Dev server running: http://localhost:3100 (PID XXXXX)"

#### Scenario: Server PID and port tracked in dev_server.json

    Given a dev server is started via purlin:server
    When the server starts successfully
    Then .purlin/runtime/dev_server.json is created
    And it contains pid, port, command, and started_at fields

#### Scenario: Server stopped when verification completes

    Given a dev server is running with PID tracked in dev_server.json
    When verification completes for the feature
    Then the server process is stopped
    And dev_server.json is removed
    And "Dev server stopped (port XXXX)" is printed

#### Scenario: Stale server detected on session start with user warning

    Given .purlin/runtime/dev_server.json exists from a previous session
    And the tracked PID is still running
    When a new Engineer session starts
    Then Engineer mode warns: "Stale dev server detected from previous session (port XXXX, PID YYYY)"
    And asks the user whether to kill it

#### Scenario: User sees server start and stop messages

    Given a feature requires web test verification
    When the dev server is started
    Then the user sees: "Dev server running: http://localhost:XXXX (PID YYYY)"
    When the dev server is stopped
    Then the user sees: "Dev server stopped (port XXXX)"

#### Scenario: init.sh copies .claude/agents/ to consumer project

    Given Purlin is a submodule with .claude/agents/engineer-worker.md
    And .claude/agents/pm-worker.md and .claude/agents/qa-worker.md
    And .claude/agents/verification-runner.md
    When the user runs tools/init.sh (full init)
    Then all four agent files are copied to the project root

#### Scenario: pl-update-purlin refreshes agent files with conflict detection

    Given the submodule has updated .claude/agents/engineer-worker.md
    And the consumer's copy has not been locally modified
    When purlin:update runs
    Then engineer-worker.md is updated to the new version

#### Scenario: Locally modified agent files preserved during update

    Given the consumer has locally modified .claude/agents/engineer-worker.md
    And the submodule has also updated engineer-worker.md
    When purlin:update runs
    Then init.sh preserves the local version (newer timestamp)
    And the conflict resolution step offers merge options

#### Scenario: Resume after clear during pipeline delivery

    Given the orchestrator was dispatching features through the pipeline
    And context was cleared via /clear
    When purlin:resume restores the session
    Then the work plan shows each feature's current stage and per-mode status
    And the enriched checkpoint provides mode, recent commits, and active worktrees
    And the orchestrator re-enters the pipeline dispatch loop

#### Scenario: Resume with orphaned sub-agent branches

    Given the orchestrator spawned cross-mode sub-agents
    And context was cleared while sub-agents were running
    When purlin:resume restores the session
    Then the orchestrator detects orphaned worktree branches
    And merges them using the robust merge protocol
    And updates the work plan with merged results
    And continues dispatching remaining work

#### Scenario: Resume after sub-agents completed before clear

    Given sub-agents completed and merged for features in a verification group
    And context was cleared after merge but before B2
    When purlin:resume restores the session
    Then the work plan shows all group features at Engineer COMPLETE
    And the orchestrator proceeds directly to B2 verification

#### Scenario: Enriched PreCompact checkpoint captures pipeline state

    Given the orchestrator is mid-pipeline with 3 active worktrees
    When PreCompact fires before context compaction
    Then the checkpoint includes current mode from runtime file
    And the first 20 lines of the work plan (pipeline status table)
    And the last 5 git commits
    And the count of active worktrees

#### Scenario: Metadata-only spec edit does not reset lifecycle

    Given terminal_identity.md is in COMPLETE state
    And its only change is removing a > Prerequisite: line
    When the scan status computation runs
    Then terminal_identity.md remains in COMPLETE state
    And no Engineer action item is generated for it

#### Scenario: Pipeline dispatch bright-line rule exists in purlin:build

    Given purlin:build is read
    When the Bright-Line Rules section is inspected
    Then it contains a rule about pipeline dispatch being mandatory when a work plan exists
    And the rule requires reading dependency_graph.json and dispatching cross-mode sub-agents
    And the rule labels sequential processing of independent features as a protocol violation

### QA Scenarios

#### @manual Scenario: Cross-mode pipeline delivery end-to-end

    Given a work plan with 4 features at different pipeline stages
    When the orchestrator runs the pipeline with cross-mode sub-agents
    Then a human verifies all features are correctly implemented and verified
    And cross-mode merges produced no regressions
    And the work plan accurately reflects final state

#### @manual Scenario: Robust merge handles real-world conflicts

    Given two sub-agents modified overlapping non-safe files
    When the merge protocol falls back to sequential
    Then a human verifies the sequential rebuild produces correct results
    And no work from the successful parallel merge is lost
