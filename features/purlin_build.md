# Feature: Build

> Label: "Agent Skills: Engineer: purlin:build Build"
> Category: "Agent Skills: Engineer"

[TODO]

## 1. Overview

The primary Engineer skill that orchestrates the entire implementation workflow. Uses `purlin:status` to identify the highest-priority Engineer work item (or accepts a named feature as argument), then executes a multi-step implementation protocol: tombstone processing, pre-flight checks, planning, implementation with knowledge colocation, local verification via `purlin:unit-test`, and status tag commits. Supports delivery plan integration with execution group dispatch for parallel multi-feature builds.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by Engineer mode role.
- Non-Engineer agents MUST receive a redirect message.

### 2.2 Path Resolution

- Path resolution per `references/path_resolution.md`.

### 2.3 Scope Selection

- If an argument is provided, implement the named feature from `features/<arg>.md`.
- If no argument is provided, run `purlin:status` to identify the highest-priority Engineer work item.
- Tombstones in `features/_tombstones/` MUST be processed before regular feature work (see Section 2.4).
- If a delivery plan exists at `.purlin/delivery_plan.md`, scope work to the current phase only.

### 2.3.1 Missing Spec Redirect

When a feature name is provided but `features/<arg>.md` does not exist, the skill MUST NOT proceed with implementation. Instead:

1. Inform the user: "No spec exists for `<name>`. In Purlin, specs come before code."
2. Offer to switch: "Switch to PM mode to create the spec? (`purlin:spec <name>`)"
3. If the user confirms, switch to PM mode and invoke `purlin:spec <name>`.
4. If the user declines, stop. Do not implement without a spec.

This creates the natural first-feature workflow: user tries `purlin:build my-feature` → gets redirected to PM mode → writes the spec → returns to Engineer mode → builds from the spec.

### 2.4 Tombstone Processing Protocol

When `features/_tombstones/` contains tombstone files, process ALL of them before any regular feature work:

1. **Read the tombstone:** Parse `features/_tombstones/<name>.md` for the "Files to Delete" and "Dependencies to Check" sections.
2. **Delete listed files:** Remove every file and directory listed in "Files to Delete":
   - Implementation code files
   - `tests/<name>/` directory (unit tests, tests.json, regression.json)
   - `tests/qa/scenarios/<name>.json` (QA regression scenario)
   - `tests/qa/test_<name>_regression.sh` (QA regression runner)
   - Any other paths listed in the tombstone
3. **Check dependencies:** For each entry in "Dependencies to Check", verify the referencing code/spec still works without the deleted feature. Fix import errors, remove dead references, update prerequisite lists.
4. **Delete the tombstone and its artifacts:** Remove the tombstone file itself and any companion artifacts that were moved alongside it:
   - `features/_tombstones/<name>.md` (the tombstone)
   - `features/_tombstones/<name>.impl.md` (if exists)
   - `features/_tombstones/<name>.discoveries.md` (if exists)
5. **Regenerate dependency graph:** Run the MCP `purlin_graph` tool to update `.purlin/cache/dependency_graph.json`.
6. **Commit:** `git commit -m "chore: process tombstone <name> — delete retired code and tests"`
7. **Repeat** for each remaining tombstone.

### 2.5 Execution Group Dispatch

- When a delivery plan has PENDING phases with 2+ independent features (no mutual dependencies in `dependency_graph.json`), Engineer mode MUST spawn `engineer-worker` sub-agents for parallel execution in isolated worktrees.
- Independent features build in parallel; dependent features use the sequential per-feature loop.
- Merge uses the Robust Merge Protocol: rebase sequentially, auto-resolve conflicts in safe files (delivery plan, cache), abort and fall back to sequential for unsafe conflicts.

### 2.6 Per-Feature Implementation Protocol

- **Step 0 (Pre-Flight):** Re-verification detection (skip re-implementation when tests pass and scenarios unchanged), anchor review, visual design source loading, web test readiness check, companion file reading, prerequisite stability check, new scenario detection, invariant preflight (see 2.6.1).
- **Step 1 (Plan):** State the feature being implemented and outline the plan referencing companion file notes.
- **Step 2 (Implement):** Write code and tests. Record discoveries in companion files using Engineer Decision Tags (`[CLARIFICATION]`, `[AUTONOMOUS]`, `[DEVIATION]`, `[DISCOVERY]`, `[INFEASIBLE]`). Companion entries SHOULD reference specific invariant constraint IDs when code addresses them (e.g., `per i_arch_api_standards.md INV-2`). Invariant deviations escalate as "invariant conflict" rather than "spec deviation" since invariants are immutable and externally-sourced. Commit implementation work.
- **Step 3 (Verify):** Invoke `purlin:unit-test` for the complete testing protocol. For features with `> Web Test:` metadata, run `purlin:web-test`.
- **Step 4 (Status Tag):** Pre-check: run a Spec & Plan Alignment Audit — re-read the feature spec and walk each requirement and scenario verifying implementation coverage; log unimplemented requirements as `[DISCOVERY]`, missing scenario coverage blocks until addressed or `[DEVIATION]`-tagged, undocumented deviations require companion file entries. When a design plan was used, re-read the plan section and verify each deliverable exists. Gate blocks on undocumented gaps, not on deviations themselves. Then determine tag (`[Complete]` for zero manual scenarios, `[Ready for Verification]` for features with manual scenarios). Declare scope (`full`, `targeted`, `cosmetic`, `dependency-only`). Commit as a SEPARATE commit from implementation. Run `scan.sh` to confirm state.

### 2.6.1 Invariant Preflight (Step 0)

During pre-flight, the build collects and enforces invariant constraints:

1. **Collect global invariants:** Read `dependency_graph.json` → `global_invariants` list. Read each `i_*` file to extract constraints.
2. **Collect scoped invariants:** Read scoped `i_*` files from the feature's transitive `> Prerequisite:` chain.
3. **FORBIDDEN pre-scan:** Extract `## FORBIDDEN Patterns` from each collected invariant. Grep feature code files for pattern violations. If any match: **block the build** with an actionable message (invariant ID, pattern, file:line location, fix suggestion). The agent MUST NOT proceed to Step 1 until all FORBIDDEN violations are resolved.
4. **Behavioral awareness reminders:** Surface non-FORBIDDEN invariant statements as non-blocking awareness context for the engineer.
5. **Figma brief staleness:** For design invariants, check the Figma invariant pointer's `> Version:` against brief.json version. Warn if stale.

### 2.7 Bright-Line Rules

- Status tag MUST be a separate commit from implementation work.
- `tests.json` MUST be produced by an actual test runner, never hand-written.
- `[Verified]` tag is QA-only; Engineer MUST NOT include it.
- Chat is not a communication channel; use `purlin:propose` for findings.
- Re-verification, not re-implementation, when scan shows `spec_modified_after_completion` with passing tests and no scenario diff.
- Design alignment verification MUST pass (zero BUG/DRIFT) before status tag for features with `> Web Test:` metadata.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Engineer invocation

    Given a non-Engineer agent session
    When the agent invokes purlin:build
    Then the command responds with a redirect message to use Engineer mode agent
    And no implementation work is performed

#### Scenario: Named feature argument scopes to specific feature

    Given an Engineer agent session
    When purlin:build is invoked with argument "my_feature"
    Then Engineer mode reads features/my_feature.md
    And implementation targets only that feature

#### Scenario: Missing spec redirects to PM mode

    Given an Engineer agent session
    When purlin:build is invoked with argument "new_feature"
    And features/new_feature.md does not exist
    Then the agent informs the user no spec exists
    And offers to switch to PM mode to create it
    And does not proceed with implementation

#### Scenario: No-argument mode selects highest-priority action item

    Given an Engineer agent session with no argument
    And purlin:status lists feature_a as highest-priority Engineer work item
    When purlin:build is invoked
    Then Engineer mode selects feature_a for implementation

#### Scenario: Tombstones processed before regular features

    Given features/_tombstones/old_feature.md exists
    And features/new_feature.md is in TODO state
    When purlin:build is invoked without arguments
    Then old_feature tombstone is processed before new_feature implementation begins

#### Scenario: Tombstone processing deletes all listed artifacts

    Given features/_tombstones/old_feature.md lists tests/old_feature/ and src/old.py
    And features/_tombstones/old_feature.impl.md exists
    When purlin:build processes the tombstone
    Then tests/old_feature/ is deleted
    And src/old.py is deleted
    And features/_tombstones/old_feature.md is deleted
    And features/_tombstones/old_feature.impl.md is deleted
    And the dependency graph is regenerated

#### Scenario: Delivery plan scopes to current phase

    Given .purlin/delivery_plan.md exists with Phase 1 IN_PROGRESS containing feature_a
    And Phase 2 PENDING contains feature_b
    When purlin:build is invoked
    Then only feature_a is implemented
    And feature_b is not started

#### Scenario: Status tag is a separate commit

    Given Engineer mode completes implementation of a feature
    When the status tag commit is created
    Then the status tag commit is separate from the implementation commit
    And the implementation commit does not contain lifecycle tags

#### Scenario: Re-verification skips re-implementation

    Given a feature with has_passing_tests true and no scenario diff
    When purlin:build processes the feature
    Then existing tests are run without re-implementing code
    And the feature is re-tagged upon test passage

#### Scenario: FORBIDDEN invariant pattern blocks build

    Given a global invariant i_arch_api_standards.md contains a FORBIDDEN pattern "eval("
    And the feature code contains a call to eval(
    When purlin:build runs Step 0 invariant preflight
    Then the build is blocked with an actionable message citing the invariant ID and file:line
    And the agent does not proceed to Step 1

#### Scenario: Invariant behavioral reminders are non-blocking

    Given a scoped invariant prerequisite contains behavioral constraints but no FORBIDDEN patterns
    When purlin:build runs Step 0 invariant preflight
    Then the constraints are surfaced as awareness reminders
    And the build proceeds to Step 1

#### Scenario: Spec & plan alignment audit catches undocumented gaps

    Given Engineer mode completes implementation of a feature
    And the spec contains a requirement with no corresponding implementation
    And no [DEVIATION] or [DISCOVERY] tag exists in the companion file
    When purlin:build runs Step 4 pre-check
    Then the audit blocks status tag commit until the gap is documented

### QA Scenarios

None.
