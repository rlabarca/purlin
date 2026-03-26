# Feature: Status Check

> Label: "Agent Skills: Common: /pl-status Status Check"
> Category: "Agent Skills: Common"

[TODO]

## 1. Overview

A shared skill available to all roles that wraps `scan.sh` to display the current CDD project state. Shows feature counts by lifecycle status (TODO/TESTING/COMPLETE), role-specific action items sorted by priority with explanatory reasons, and open discoveries or tombstones requiring attention. Includes role-filtered shortcut mode and PM-specific uncommitted changes detection.

---

## 2. Requirements

### 2.1 Shared Access

- The command is available to all roles (PM, Engineer, QA, PM).

### 2.2 Core Output

- Run `scan.sh` with focused flags based on current mode (see 2.5 Mode-Scoped Output). Read the JSON output.
- Summarize: feature counts by lifecycle status, work items for the current mode, and relevant discoveries.
- The `regression_status` field in scan.json comes from `tests/<feature>/regression.json` — values: `PASS`, `FAIL`, `STALE`, or `null` (no regression tests).
- Tombstone files (features with `tombstone: true` in scan output) MUST be surfaced as Engineer work items with highest priority — tombstones are processed before regular feature work.

### 2.2.1 Work Item Priority Ranking

Action items MUST be sorted in this order (highest priority first):

1. **Tombstones** — Engineer processes tombstones before any regular work
2. **FAIL** — Test failures or regression failures require immediate attention
3. **TESTING** — Features in verification (QA) or features blocked by spec issues (PM)
4. **TODO** — Features not yet started
5. **Informational** — Smoke candidates, cosmetic notes

### 2.3 Status Value Reference

- Display status meanings per role (PM: DONE/TODO; Engineer: DONE/TODO/FAIL/BLOCKED/INFEASIBLE; QA: CLEAN/TODO/FAIL/DISPUTED/N/A).

### 2.4 QA-Specific: Regression and Smoke Status

- **Regression status:** Features with `regression_status` of STALE or FAIL in scan results MUST appear as QA work items with the reason `"regression STALE"` or `"regression FAIL"` and the hint `"Run /pl-regression to update."`.
- **Smoke candidates:** Read `smoke_candidates` from scan results. If non-empty, display after QA work items as an informational block showing feature name and dependent count. No action required — QA can promote via `/pl-smoke`.

### 2.5 Mode-Scoped Output

When a mode is active, `/pl-status` MUST limit output to that mode's work items only. When no mode is active (open mode), show all work items across all modes (current behavior).

**Scoping rules by active mode:**

- **PM mode:** Show only PM work items (incomplete specs, unacknowledged deviations, SPEC_DISPUTE/INTENT_DRIFT discoveries). Use `scan.sh --only features,discoveries,deviations,git`. Do NOT show Engineer or QA work items.
- **Engineer mode:** Show only Engineer work items (tombstones, test failures, spec_modified_after_completion, TODO features, open BUGs with Engineer action, delivery plan features). Use `scan.sh --only features,discoveries,plan,git --tombstones`. Do NOT show PM or QA work items.
- **QA mode:** Show only QA work items (TESTING features with QA scenarios, regression status, smoke candidates). Use `scan.sh --only features,discoveries,git,smoke`. Do NOT show PM or Engineer work items.
- **Open mode (no mode active):** Show all work items grouped by mode. Use `scan.sh --tombstones` (full scan). Suggest the mode with highest-priority work.

**Always shown regardless of mode:**
- Feature counts by lifecycle (TODO / TESTING / COMPLETE). These are compact and provide essential context.
- Worktree summary (when worktrees exist).

**Never shown in scoped mode:**
- Work items belonging to other modes. The purpose is to reduce noise and let the agent focus on actionable work within its current mode.
- The "suggest which mode" prompt (only shown in open mode).

### 2.6 PM-Specific: Uncommitted Changes Check

- After standard output, if PM role: check for uncommitted changes in PM-owned files.
- Present summary of changes grouped by type (new, modified, deleted).
- Propose commit message and ask user for confirmation.
- Non-PM-owned files are noted but not acted upon.

---

## 3. Scenarios

### Unit Tests

#### Scenario: All roles can invoke the command

    Given any agent role
    When the agent invokes /pl-status
    Then the command executes without a role authorization error

#### Scenario: Output includes feature counts by status

    Given a project with 3 TODO, 2 TESTING, and 5 COMPLETE features
    When /pl-status is invoked
    Then the output shows the correct counts for each status

#### Scenario: PM mode shows only PM work items

    Given an active PM mode session
    And there are unacknowledged deviations AND features with test failures
    When /pl-status is invoked
    Then only PM work items are shown (deviations, incomplete specs, disputes)
    And Engineer work items (test failures) are NOT shown
    And QA work items are NOT shown

#### Scenario: Engineer mode shows only Engineer work items

    Given an active Engineer mode session
    And there are features with test failures AND unacknowledged deviations
    When /pl-status is invoked
    Then only Engineer work items are shown (failures, tombstones, TODO features)
    And PM work items (deviations) are NOT shown
    And QA work items are NOT shown

#### Scenario: QA mode shows only QA work items

    Given an active QA mode session
    And there are TESTING features AND features with test failures
    When /pl-status is invoked
    Then only QA work items are shown (TESTING features, regression status)
    And Engineer work items (test failures) are NOT shown
    And PM work items are NOT shown

#### Scenario: Open mode shows all work items

    Given no mode is active (open mode)
    When /pl-status is invoked
    Then work items for ALL modes are shown (PM, Engineer, QA)
    And a mode suggestion is included

#### Scenario: PM sees uncommitted changes check

    Given a PM agent session
    And features/new_spec.md has uncommitted changes
    When /pl-status completes
    Then the output includes the uncommitted changes summary
    And a commit message is proposed

#### Scenario: QA section shows regression failures with hint

    Given a feature has regression_status "FAIL" in scan results
    When /pl-status is invoked
    Then the QA work items include the feature with reason "regression FAIL"
    And the hint "Run /pl-regression to update" is shown

#### Scenario: Mode-scoped output uses focused scan flags

    Given an active PM mode session
    When /pl-status invokes scan.sh
    Then scan.sh is called with --only features,discoveries,deviations,git
    And tombstones are NOT included in the scan output

#### Scenario: Lifecycle counts shown in all modes

    Given an active Engineer mode session with 3 TODO, 2 TESTING, 5 COMPLETE features
    When /pl-status is invoked
    Then lifecycle counts are shown (TODO: 3, TESTING: 2, COMPLETE: 5)
    And only Engineer work items are shown

#### Scenario: QA section shows smoke candidates

    Given scan results contain smoke_candidates with "hub_feature" (4 dependents)
    When /pl-status is invoked
    Then the output includes "Smoke candidates (unclassified):"
    And "hub_feature — 4 dependents" is shown

### QA Scenarios

None.
