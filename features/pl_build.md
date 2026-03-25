# Feature: Build

> Label: "Agent Skills: Engineer: /pl-build Build"
> Category: "Agent Skills: Engineer"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The primary Builder skill that orchestrates the entire implementation workflow. Reads the Critic report to identify the highest-priority Builder action item (or accepts a named feature as argument), then executes a multi-step implementation protocol: pre-flight checks, planning, implementation with knowledge colocation, local verification via `/pl-unit-test`, and status tag commits. Supports delivery plan integration with execution group dispatch for parallel multi-feature builds.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the Builder role.
- Non-Builder agents MUST receive a redirect message.

### 2.2 Path Resolution

- The command MUST resolve `tools_root` from `.purlin/config.json` (default: `"tools"`).
- Project root MUST be resolved via `PURLIN_PROJECT_ROOT` env var first, then directory-climbing fallback.

### 2.3 Scope Selection

- If an argument is provided, implement the named feature from `features/<arg>.md`.
- If no argument is provided, read `CRITIC_REPORT.md` or run `status.sh --role builder` to identify the highest-priority Builder action item.
- Tombstones in `features/tombstones/` MUST be processed before regular feature work.
- If a delivery plan exists at `.purlin/delivery_plan.md`, scope work to the current phase only.

### 2.4 Execution Group Dispatch

- When a delivery plan has PENDING phases with 2+ independent features (no mutual dependencies in `dependency_graph.json`), the Builder MUST spawn `builder-worker` sub-agents for parallel execution in isolated worktrees.
- Independent features build in parallel; dependent features use the sequential per-feature loop.
- Merge uses the Robust Merge Protocol: rebase sequentially, auto-resolve conflicts in safe files (delivery plan, Critic report, cache), abort and fall back to sequential for unsafe conflicts.

### 2.5 Per-Feature Implementation Protocol

- **Step 0 (Pre-Flight):** Re-verification detection (skip re-implementation when tests pass and scenarios unchanged), anchor review, visual design source loading, web test readiness check, companion file reading, prerequisite stability check, new scenario detection.
- **Step 1 (Plan):** State the feature being implemented and outline the plan referencing companion file notes.
- **Step 2 (Implement):** Write code and tests. Record discoveries in companion files using Builder Decision Tags (`[CLARIFICATION]`, `[AUTONOMOUS]`, `[DEVIATION]`, `[DISCOVERY]`, `[INFEASIBLE]`). Commit implementation work.
- **Step 3 (Verify):** Invoke `/pl-unit-test` for the complete testing protocol. For features with `> Web Test:` metadata, run `/pl-web-test`.
- **Step 4 (Status Tag):** Determine tag (`[Complete]` for zero manual scenarios, `[Ready for Verification]` for features with manual scenarios). Declare scope (`full`, `targeted`, `cosmetic`, `dependency-only`). Commit as a SEPARATE commit from implementation. Run `status.sh` to confirm state.

### 2.6 Bright-Line Rules

- Status tag MUST be a separate commit from implementation work.
- `tests.json` MUST be produced by an actual test runner, never hand-written.
- `[Verified]` tag is QA-only; Builder MUST NOT include it.
- Chat is not a communication channel; use `/pl-propose` for findings.
- Re-verification, not re-implementation, when Critic shows `lifecycle_reset` with passing tests and no scenario diff.
- Design alignment verification MUST pass (zero BUG/DRIFT) before status tag for features with `> Web Test:` metadata.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Builder invocation

    Given a non-Builder agent session
    When the agent invokes /pl-build
    Then the command responds with a redirect message to use the Builder agent
    And no implementation work is performed

#### Scenario: Named feature argument scopes to specific feature

    Given a Builder agent session
    When /pl-build is invoked with argument "my_feature"
    Then the Builder reads features/my_feature.md
    And implementation targets only that feature

#### Scenario: No-argument mode selects highest-priority action item

    Given a Builder agent session with no argument
    And CRITIC_REPORT.md lists feature_a as highest-priority Builder action
    When /pl-build is invoked
    Then the Builder selects feature_a for implementation

#### Scenario: Tombstones processed before regular features

    Given features/tombstones/old_feature.md exists
    And features/new_feature.md is in TODO state
    When /pl-build is invoked without arguments
    Then old_feature tombstone is processed before new_feature implementation begins

#### Scenario: Delivery plan scopes to current phase

    Given .purlin/delivery_plan.md exists with Phase 1 IN_PROGRESS containing feature_a
    And Phase 2 PENDING contains feature_b
    When /pl-build is invoked
    Then only feature_a is implemented
    And feature_b is not started

#### Scenario: Status tag is a separate commit

    Given the Builder completes implementation of a feature
    When the status tag commit is created
    Then the status tag commit is separate from the implementation commit
    And the implementation commit does not contain lifecycle tags

#### Scenario: Re-verification skips re-implementation

    Given a feature with has_passing_tests true and no scenario diff
    When /pl-build processes the feature
    Then existing tests are run without re-implementing code
    And the feature is re-tagged upon test passage

### QA Scenarios

None.
