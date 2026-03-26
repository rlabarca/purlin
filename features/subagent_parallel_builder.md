# Feature: Sub-Agent Parallel Engineer

> Label: "Tool: Sub-Agent Parallel Engineer"
> Category: "Install, Update & Scripts"
> Prerequisite: features/purlin_agent_launcher.md

## 1. Overview

Formalizes parallel feature building with dedicated sub-agent definitions, replaces ad-hoc Agent tool calls with structured `engineer-worker` and `verification-runner` sub-agents, and consolidates duplicated implementation knowledge from `PURLIN_BASE.md` into skills that sub-agents can preload. Adds a robust rebase-before-merge protocol for parallel branches, server lifecycle management with port tracking. Deprecates `--continuous` mode in favor of interactive multi-phase auto-progression.

---

## 2. Requirements

### 2.1 Sub-Agent Definitions

Two sub-agent definition files MUST be created in `.claude/agents/`:

#### 2.1.1 `engineer-worker.md`

Replaces ad-hoc Agent tool calls for intra-phase parallel feature building.

*   **Frontmatter:**
    ```yaml
    name: engineer-worker
    description: >
      Parallel feature builder for intra-phase work. Implements a single feature
      in an isolated worktree. Use when building independent features concurrently.
    tools: Read, Write, Edit, Bash, Glob, Grep
    isolation: worktree
    skills: [pl-build]
    permissionMode: bypassPermissions
    model: inherit
    maxTurns: 200
    ```
*   **System prompt constraints:**
    - Single-feature focus: implements one feature only per invocation.
    - Steps 0-2 only from `/pl-build`. No Step 3 (verification), no Step 4 (status tags).
    - MUST NOT modify the delivery plan (`.purlin/delivery_plan.md`).
    - MUST NOT spawn nested sub-agents (no Agent tool access).
    - Commit with `feat(scope): implement FEATURE_NAME`.
    - Branch naming: `worktree-phase<N>-<feature_stem>` (encodes phase for orphan attribution).

#### 2.1.2 `verification-runner.md`

Runs automated tests in background during B2, keeping test output out of main Engineer context.

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
    - Run the `/pl-unit-test` protocol for specified features. The skill is preloaded with the complete testing protocol (quality rubric, anti-pattern scan, result reporting).
    - Write `tests.json` results. `Write` is allowed only for `tests.json` output.
    - MUST NOT fix code or edit implementation files.

### 2.2 Parallel B1 Protocol

When a delivery plan exists, Engineer mode MUST use `engineer-worker` sub-agents for parallel feature building. The execution group dispatch protocol in `/pl-build` determines which features are independent:

1.  Read `.purlin/cache/dependency_graph.json` and the delivery plan.
2.  Compute execution groups: group PENDING phases with no cross-dependencies.
3.  For the current execution group, collect all features across member phases and check pairwise independence.
4.  If independent features exist (2+):
    - Announce: "Features X and Y are independent -- building in parallel."
    - Spawn one `engineer-worker` sub-agent per feature.
    - Each sub-agent runs Steps 0-2 only.
    - Merge returned branches using the robust merge protocol (Section 2.4).
    - After all groups complete, proceed to B2.
5.  If no independent features exist, or only 1 feature: use the sequential per-feature loop.

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
    *   **Safe files:** `.purlin/delivery_plan.md`, `/pl-status`, `.purlin/cache/*`.
    *   Safe: auto-resolve by keeping main's version (`git checkout --ours`), then `git add` and `git rebase --continue`.
    *   Unsafe (any non-safe file in conflict): `git rebase --abort`, fall back to sequential for THIS feature only.
4.  Loop up to 20 rebase iterations for multi-commit branches.
5.  After rebase: fast-forward merge (`git merge <branch> --no-edit`).
6.  On merge conflict: same safe-file auto-resolve logic.
7.  Only sequential fallback for actual code conflicts -- preserves already-merged features.

**Source reference:** `try_auto_resolve_conflicts()` at `pl-run.sh:734`, rebase loop at lines 2084-2126.

### 2.5 Instruction Consolidation

**Goal:** Implementation knowledge lives in skills (preloadable by sub-agents). Base instructions contain only session orchestration.

#### 2.5.1 Move Remaining Bright-Line Rules into `/pl-build`

*   `PURLIN_BASE.md` Section 5 currently contains ~15 bright-line rules. Testing rules already reference `/pl-unit-test`.
*   Move all remaining non-testing bright-line rules (web test verification, phase halt, cross-cutting triage, regression handoff) into `/pl-build`.
*   `PURLIN_BASE.md` Section 5 becomes:
    ```
    ## 5. Per-Feature Implementation Protocol
    Invoke `/pl-build` for the complete per-feature protocol including all bright-line rules.
    Testing protocol: `/pl-unit-test` (invoked by `/pl-build` Step 3).
    ```
*   This completes the extraction pattern that `/pl-unit-test` already started.

#### 2.5.2 Delete Section 7 (Agentic Team Orchestration)

*   Two vague lines with no actionable content. Sub-agent patterns are now defined by the sub-agent definitions themselves.

#### 2.5.3 Extract Server Lifecycle into `/pl-server`

*   `PURLIN_BASE.md` Section 8 server rules move to a new `/pl-server` skill (`.claude/commands/pl-server.md`).
*   `PURLIN_BASE.md` Section 8 retains only non-server build/environment rules.

#### 2.5.4 Resulting `PURLIN_BASE.md` Structure

```
1. Executive Summary (role identity)
2. Startup Protocol (scan, work discovery, plan proposal)
3. Feature Status Lifecycle
4. Tombstone Processing
5. Per-Feature Implementation Protocol (pointer to /pl-build)
6. Shutdown Protocol
7. [deleted]
8. Build & Environment Protocols (non-server rules only)
9. Command Authorization
```

### 2.6 Server Lifecycle Skill

A new skill at `.claude/commands/pl-server.md` with the following capabilities:

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

### 2.7 Multi-Phase Auto-Progression

When `auto_start: true` in Engineer mode's config:

*   After completing a delivery plan phase, Engineer mode auto-advances to the next PENDING phase instead of halting.
*   The phase halt rule in `/pl-build` Step 4.E becomes conditional: halt only when `auto_start: false` (current default behavior).
*   When `auto_start: true`, Engineer mode marks the phase COMPLETE, then immediately begins the next phase within the same session.
*   Engineer mode runs all phases end-to-end without bash orchestration.

### 2.8 Continuous Mode Deprecation

*   `--continuous` flag in `pl-run.sh` prints a deprecation warning and exits.
*   Warning message: "The --continuous flag is deprecated. Set `auto_start: true` in agent config and relaunch the interactive Engineer."
*   `features/continuous_phase_builder.md` gets a tombstone for code removal (see `features/tombstones/continuous_phase_builder.md`).
*   Deprecated config keys: `continuous_evaluator_model`, `max_remediation_attempts`.
*   Deprecated runtime artifacts: `.purlin/runtime/continuous_build_phase_*.log`, phase status JSON, evaluator state files.

### 2.9 Context Recovery

#### 2.9.1 Orphaned Sub-Agent Branches

On `/pl-resume`, Engineer mode MUST check for orphaned worktree branches matching the pattern `worktree-*`:
*   If found: attempt to merge them using the robust merge protocol (Section 2.4), then continue.
*   If not found: the sub-agents either completed and merged, or never started. The delivery plan + scan state tells Engineer mode what remains.

#### 2.9.2 Checkpoint Format Extension

Add to Engineer mode Context section of the checkpoint:
```markdown
**Parallel B1 State:** <"idle" | "spawned N sub-agents for features [A, B]" | "merging N branches">
**Execution Group:** <"N/A" | "Group K: Phases [X, Y] -- N features">
```

#### 2.9.3 Auto-Progression Continuity

On resume, Engineer mode:
1.  Reads delivery plan -- identifies current phase (IN_PROGRESS) and remaining phases (PENDING).
2.  Reads scan results -- identifies which features in the current phase are done vs TODO.
3.  Checks for orphaned worktree branches -- merges if found.
4.  Continues with remaining features in the current phase.
5.  Auto-progresses to next phases (if `auto_start: true`).

### 2.10 Distribution to Consumer Projects

#### 2.10.1 Init Changes

*   Add `copy_agent_files()` function to `tools/init.sh` (same pattern as `copy_command_files()`).
*   Source: `<submodule>/.claude/agents/`.
*   Destination: `<project_root>/.claude/agents/`.
*   Same skip logic: preserve locally modified versions (timestamp comparison).
*   Called during both full init and refresh modes.

#### 2.10.2 Update Changes

*   `/pl-update-purlin` extends conflict detection to also scan `.claude/agents/` for local modifications vs upstream changes.
*   Same resolution options: "Accept upstream", "Keep current", "Smart merge".

### 2.11 Lifecycle Metadata Hash Exemption

The lifecycle content hash MUST exclude blockquote metadata lines (`> Key: Value` at the top of feature files) when determining whether a feature spec has changed. Only body content (Overview, Requirements, Scenarios, Visual Specification) contributes to the hash. This uses an explicit allow-list of known metadata keys (`Label`, `Category`, `Prerequisite`, `Owner`, `Web Test`, `Web Start`, `AFT Web`, `AFT Start`, `Test Fixtures`, `Figma Status`, `Regression Coverage`). Unknown blockquote keys are preserved in the hash (conservative).

### 2.12 Sync Invariants

*   `/pl-build` preloading by `engineer-worker` auto-syncs all conventions (bright-line rules, commit formats, decision tags) to sub-agents.
*   `/pl-unit-test` preloading by `verification-runner` auto-syncs the testing protocol.
*   When a convention changes in the skill file, sub-agents inherit the change on next invocation with zero manual propagation.

### 2.13 Execution Group Dispatch Bright-Line Rule

The Execution Group Dispatch MUST appear as a named bright-line rule in `/pl-build`,
not only as a standalone section. The rule text:

> **Execution group dispatch is mandatory for multi-feature groups.** When an execution
> group contains 2+ independent features (across all its member phases), MUST read
> `dependency_graph.json`, check pairwise independence, and spawn `engineer-worker`
> sub-agents for independent features BEFORE beginning Step 0 for any feature.
> Sequential processing of independent features without checking the dependency graph
> is a protocol violation.

Additionally, Step 4.E auto-progression MUST explicitly reference the Execution
Group Dispatch as mandatory when entering a new group with 2+ features.


---

## 3. Scenarios

### Unit Tests

#### Scenario: Parallel features use engineer-worker sub-agent

    Given a delivery plan phase has features A and B
    And the dependency graph shows A and B have no cross-dependencies
    When Engineer mode begins B1 for the phase
    Then Engineer mode spawns one engineer-worker sub-agent per feature
    And each sub-agent runs in an isolated worktree
    And each sub-agent runs Steps 0-2 only

#### Scenario: Engineer-worker runs Steps 0-2 only

    Given a engineer-worker sub-agent is spawned for feature A
    When the sub-agent completes its work
    Then it has run Steps 0-2 (pre-flight, plan, implement)
    And it has NOT run Step 3 (verification) or Step 4 (status tags)
    And it has NOT modified the delivery plan

#### Scenario: Engineer-worker cannot spawn nested sub-agents

    Given a engineer-worker sub-agent is running
    When the sub-agent's tool list is inspected
    Then the Agent tool is not available
    And the sub-agent cannot launch nested sub-agents

#### Scenario: Engineer-worker hits maxTurns safety limit

    Given a engineer-worker sub-agent is running
    When the sub-agent reaches 200 turns
    Then the sub-agent stops execution
    And the main session handles the incomplete feature sequentially

#### Scenario: verification-runner runs tests in background during B2

    Given Engineer mode has completed B1 for all features in a phase
    When Engineer mode enters B2
    Then it spawns verification-runner sub-agents in the background
    And each verification-runner runs /pl-unit-test for its assigned feature
    And the main session runs web tests concurrently with MCP access

#### Scenario: verification-runner cannot edit files

    Given a verification-runner sub-agent is running
    When the sub-agent's disallowed tools are inspected
    Then Edit and Agent are disallowed
    And Write is allowed only for tests.json output

#### Scenario: Main session runs web tests concurrently

    Given verification-runner sub-agents are running in background
    When the main Engineer session begins web test verification
    Then MCP tools (browser_navigate, browser_snapshot) are available in the main session
    And web tests run concurrently with the background test runners

#### Scenario: Safe file conflicts auto-resolve during merge

    Given two engineer-worker branches both modified /pl-status
    When the robust merge protocol runs rebase-before-merge
    Then the conflict on /pl-status is auto-resolved by keeping main's version
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
    And 2 of those commits touch .purlin/delivery_plan.md
    When the robust merge protocol runs rebase
    Then it iterates through each commit's conflicts
    And auto-resolves safe file conflicts at each step
    And the rebase completes within 20 iterations

#### Scenario: Engineer auto-advances to next phase when auto_start is true

    Given auto_start is true in Engineer mode's config
    And a delivery plan has Phase 1 IN_PROGRESS and Phase 2 PENDING
    When Engineer mode completes Phase 1
    Then Phase 1 is marked COMPLETE in the delivery plan
    And Engineer mode immediately begins Phase 2 without halting

#### Scenario: Engineer halts after phase when auto_start is false

    Given auto_start is false in Engineer mode's config
    And a delivery plan has Phase 1 IN_PROGRESS and Phase 2 PENDING
    When Engineer mode completes Phase 1
    Then Phase 1 is marked COMPLETE in the delivery plan
    And Engineer mode halts with a phase completion message
    And Engineer mode does NOT begin Phase 2

#### Scenario: Engineer spawns parallel sub-agents for multi-feature phases

    Given auto_start is true
    And Phase 2 has 3 independent features
    When Engineer mode auto-advances to Phase 2
    Then it spawns engineer-worker sub-agents for the independent features
    And merges results using the robust merge protocol
    And proceeds to B2 verification

#### Scenario: Engineer runs all phases in a single session without bash orchestration

    Given auto_start is true
    And a delivery plan has 4 phases
    When Engineer mode completes all 4 phases
    Then all phases are marked COMPLETE
    And the delivery plan is deleted
    And no external bash orchestrator was involved

#### Scenario: --continuous flag prints deprecation warning and exits

    Given pl-run.sh exists
    When the user invokes pl-run.sh --continuous
    Then a deprecation warning is printed
    And the warning includes: "Set auto_start: true in agent config and relaunch the interactive Engineer"
    And the script exits without launching an Engineer session

#### Scenario: Bright-line rules exist only in /pl-build skill

    Given PURLIN_BASE.md Section 5 is read
    Then it contains only a pointer to /pl-build
    And it does not contain web test verification rules
    And it does not contain phase halt rules
    And it does not contain cross-cutting triage rules

#### Scenario: PURLIN_BASE.md Section 5 contains only skill invocation pointer

    Given PURLIN_BASE.md is read
    When Section 5 is inspected
    Then it contains "Invoke /pl-build" text
    And it contains "Testing protocol: /pl-unit-test" text
    And the section is fewer than 10 lines

#### Scenario: Sub-agent preloading /pl-build gets all bright-line rules

    Given a engineer-worker sub-agent has skills: [pl-build]
    When the sub-agent's preloaded context is inspected
    Then the /pl-build skill content includes all bright-line rules
    And the sub-agent has the complete per-feature protocol

#### Scenario: Dev server starts on alternate port when default occupied

    Given port 3000 is already in use
    When the /pl-server skill starts a dev server
    Then it detects port 3000 is occupied
    And starts the server on port 3100 instead
    And prints: "Dev server running: http://localhost:3100 (PID XXXXX)"

#### Scenario: Server PID and port tracked in dev_server.json

    Given a dev server is started via /pl-server
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
    And .claude/agents/verification-runner.md
    When the user runs tools/init.sh (full init)
    Then .claude/agents/engineer-worker.md is copied to the project root
    And .claude/agents/verification-runner.md is copied to the project root

#### Scenario: pl-update-purlin refreshes agent files with conflict detection

    Given the submodule has updated .claude/agents/engineer-worker.md
    And the consumer's copy has not been locally modified
    When /pl-update-purlin runs
    Then engineer-worker.md is updated to the new version

#### Scenario: Locally modified agent files preserved during update

    Given the consumer has locally modified .claude/agents/engineer-worker.md
    And the submodule has also updated engineer-worker.md
    When /pl-update-purlin runs
    Then init.sh preserves the local version (newer timestamp)
    And the conflict resolution step offers merge options

#### Scenario: Resume after clear during multi-phase auto-progression

    Given Engineer mode was auto-progressing through Phase 4 of 6
    And context was cleared via /clear
    When /pl-resume restores the session
    Then the delivery plan shows phases 1-3 COMPLETE, phase 4 IN_PROGRESS
    And /pl-status identifies remaining TODO features in phase 4
    And Engineer mode continues from the current phase

#### Scenario: Resume with orphaned sub-agent branches

    Given Engineer mode spawned 2 engineer-worker sub-agents
    And context was cleared while sub-agents were running
    When /pl-resume restores the session
    Then Engineer mode detects orphaned worktree branches
    And merges them using the robust merge protocol
    And continues with remaining work

#### Scenario: Resume after all sub-agents completed before clear

    Given 2 engineer-worker sub-agents completed and merged
    And context was cleared after merge but before B2 verification
    When /pl-resume restores the session
    Then the checkpoint shows parallel B1 completed
    And Engineer mode proceeds directly to B2 verification

#### Scenario: Metadata-only spec edit does not reset lifecycle

    Given terminal_identity.md is in COMPLETE state
    And its only change is removing a > Prerequisite: line
    When the scan status computation runs
    Then terminal_identity.md remains in COMPLETE state
    And no Engineer action item is generated for it

#### Scenario: Execution group dispatch bright-line rule exists in /pl-build

    Given /pl-build is read
    When the Bright-Line Rules section is inspected
    Then it contains a rule about execution group dispatch being mandatory
    And the rule requires reading dependency_graph.json before Step 0
    And the rule labels sequential processing of independent features as a protocol violation

### QA Scenarios

#### @manual Scenario: Sub-agent parallel build end-to-end

    Given a delivery plan phase has 3 independent features
    When Engineer mode executes the phase with parallel sub-agents
    Then a human verifies all 3 features are correctly implemented
    And the merge produced no regressions
    And the scan status shows expected states

#### @manual Scenario: Robust merge handles real-world conflicts

    Given two sub-agents modified overlapping non-safe files
    When the merge protocol falls back to sequential
    Then a human verifies the sequential rebuild produces correct results
    And no work from the successful parallel merge is lost
