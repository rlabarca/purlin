# Feature: purlin:smoke Smoke Test Promotion

> Label: "Agent Skills: QA: purlin:smoke Smoke Test Promotion"
> Category: "Agent Skills: QA"
> Prerequisite: purlin_sync_system.md

## 1. Overview

The `purlin:smoke` skill allows QA mode to promote any test (regression, @auto, or @manual) to smoke tier and optionally create a simplified fast-running smoke version. Smoke tests run first in every QA verification pass and block further verification on failure.

**QA is the smoke test design authority.** QA decides which features are critical path, what constitutes a meaningful smoke check, and when to promote or demote a feature's tier. PM may suggest candidates, but the classification decision belongs to QA — they have the verification experience to judge what actually breaks and what matters.

---

## 2. Requirements

### 2.1 Smoke Promotion

- `purlin:smoke <feature>` MUST add the feature to the `## Test Priority Tiers` table in `PURLIN_OVERRIDES.md` (or `PURLIN_OVERRIDES.md` for legacy projects) with tier `smoke`.
- If the tier table does not exist, the skill MUST create it.
- The skill MUST show the user what tests exist for the feature before promoting.

### 2.2 Simplified Smoke Regression

- After promotion, the skill MUST offer to create a simplified smoke regression at `tests/qa/scenarios/<feature>_smoke.json`.
- Smoke regressions MUST test only the critical path (1-3 scenarios max).
- Smoke regressions MUST target < 30 second execution time.
- Smoke regressions MUST include `"tier": "smoke"` and `"smoke_of": "<feature>.json"` fields.

### 2.3 Smoke Suggestion

- `purlin:smoke suggest` MUST analyze the project and identify features that should be smoke tier.
- Candidates: features with 3+ dependents, `arch_*`/`policy_*` anchors, core categories (Install/Update, Coordination), names containing launcher/init/config/status/scan.
- MUST filter out features already classified as smoke.
- MUST present suggestions with rationale and let the user select.

### 2.4 Verification Integration

- The `purlin:verify` smoke gate (Step 2) MUST run smoke regressions (`_smoke.json`) BEFORE smoke QA scenarios.
- The smoke gate MUST read the tier table from BOTH `PURLIN_OVERRIDES.md` and `PURLIN_OVERRIDES.md`.
- The smoke gate MUST also detect `_smoke.json` files with `"tier": "smoke"` even if the feature is not in the tier table.
- A smoke failure MUST block all further verification with a prominent halt message.
- After smoke passes, the verify skill MUST suggest smoke promotion for high-fan-out features lacking smoke classification (once per session).

### 2.6 First-Time Smoke Orientation

When a project has **5+ completed features** but **zero smoke-tier classifications** (no entries in the tier table and no `_smoke.json` files), display a one-time orientation block during `purlin:verify` or `purlin:complete`:

```
━━━ Smoke Testing ━━━
This project has N completed features but no smoke tests.
Smoke tests run first and block verification on failure —
they protect your critical path.

  purlin:smoke suggest     — find candidates
  purlin:smoke <feature>   — promote a feature

Recommended: purlin:smoke suggest
━━━━━━━━━━━━━━━━━━━━━━━━
```

**One-time rule:** Display only when zero smoke classifications exist. Once any feature is promoted to smoke, never show it again.

**Placement:** After Phase A summary in `purlin:verify`, or after marking `[Complete]` via `purlin:complete` when the threshold is first reached.

### 2.7 Scan-Level Smoke Candidate Signal

The scan engine (`tools/cdd/scan.sh`) MUST surface unclassified smoke candidates in its output so that `purlin:status` can display them without requiring QA to run `purlin:smoke suggest` manually.

**Detection logic** (runs as part of every `scan.sh` invocation — no separate command or manual trigger needed):
1. Read the dependency graph from `.purlin/cache/dependency_graph.json`.
2. Count dependents per feature (how many features list it as a prerequisite).
3. Read the tier table to find existing smoke classifications.
4. A feature is a **smoke candidate** if ALL of:
   - It has 3+ dependents (high fan-out)
   - It is NOT already classified as smoke in the tier table
   - It has a `[Complete]` lifecycle status (not TODO or TESTING)

**Scan output field:** Add `smoke_candidates` to the scan JSON output:
```json
{
  "smoke_candidates": [
    {"feature": "agent_launchers_common", "dependents": 4, "reason": "high fan-out, core category"}
  ]
}
```

**`purlin:status` display:** When smoke candidates exist, show them in the QA section:
```
Smoke candidates (unclassified):
  agent_launchers_common — 4 dependents
```

No action is required — this is informational. QA sees it naturally and can promote via `purlin:smoke` when ready.

### 2.5 Smoke Tier Rules

- Smoke tests run FIRST in every QA verification pass.
- A smoke failure blocks standard and full-only verification.
- Every project should have 5-15 smoke features covering the critical path.
- Smoke tests verify "is it broken?" not "is every edge case handled?"

---

## 3. Scenarios

### Unit Tests

#### Scenario: Promote feature to smoke tier

    Given feature "project_init" exists with passing regression tests
    And it is not in the Test Priority Tiers table
    When purlin:smoke project_init is invoked
    Then "project_init" is added to the tier table with tier "smoke"

#### Scenario: Create tier table when missing

    Given PURLIN_OVERRIDES.md exists but has no Test Priority Tiers section
    When purlin:smoke project_init is invoked
    Then a "## Test Priority Tiers" section is created
    And "project_init" is added with tier "smoke"

#### Scenario: Offer simplified smoke regression

    Given feature "project_init" has 3 regression scenarios
    When purlin:smoke project_init is invoked and user accepts simplification
    Then tests/qa/scenarios/project_init_smoke.json is created
    And it contains 1-3 scenarios (fewer than the full suite)
    And it contains "tier": "smoke"

#### Scenario: Smoke suggestion identifies high-fan-out features

    Given feature "agent_launchers_common" is a prerequisite for 12 features
    And it is not in the tier table
    When purlin:smoke suggest is invoked
    Then "agent_launchers_common" appears in the suggestion list

#### Scenario: Scan surfaces smoke candidates in output

    Given feature "agent_launchers_common" has 4 dependents
    And it is not in the tier table as smoke
    And it has [Complete] lifecycle status
    When the scan engine runs
    Then smoke_candidates includes "agent_launchers_common" with dependents 4

#### Scenario: Scan excludes already-classified features from candidates

    Given feature "project_init" is in the tier table as smoke
    And it has 3 dependents
    When the scan engine runs
    Then smoke_candidates does not include "project_init"

#### Scenario: Smoke suggestion skips already-classified features

    Given feature "project_init" is already in the tier table as smoke
    When purlin:smoke suggest is invoked
    Then "project_init" does not appear in the suggestion list

#### Scenario: Verify smoke gate runs smoke regressions first

    Given feature "agent_launchers_common" has a _smoke.json regression file
    And feature "agent_launchers_common" also has @auto QA scenarios
    When purlin:verify runs the smoke gate
    Then the _smoke.json regression runs BEFORE the @auto scenarios

#### Scenario: First-time orientation shown when no smoke features exist

    Given a project has 5 completed features
    And zero features are classified as smoke tier
    When purlin:verify runs
    Then a smoke testing orientation block is displayed
    And it suggests purlin:smoke suggest as the next step

#### Scenario: Orientation not shown after first smoke promotion

    Given a project has 5 completed features
    And one feature is classified as smoke tier
    When purlin:verify runs
    Then no smoke orientation block is displayed

#### Scenario: Verify smoke failure blocks further verification

    Given a smoke-tier feature with a failing smoke regression
    When purlin:verify runs the smoke gate
    Then a prominent SMOKE FAILURE message is displayed
    And the user is prompted to stop or continue
    And standard-tier features are NOT verified until the user responds

### QA Scenarios

#### Scenario: Smoke regression targets fast execution @manual

    Given a smoke regression file was created by purlin:smoke
    When the scenario count is checked
    Then it has 3 or fewer scenarios
    And each scenario is designed for < 30 second execution

#### Scenario: End-to-end smoke promotion and verification @manual

    Given a feature with no smoke classification
    When purlin:smoke promotes it and creates a smoke regression
    And purlin:verify is run on the project
    Then the smoke regression runs in the smoke gate (Step 2)
    And it runs before all standard-tier features

## Regression Guidance
- Verify _smoke.json files are detected even without a tier table entry
- Verify smoke gate reads from both PURLIN_OVERRIDES.md and PURLIN_OVERRIDES.md
- Verify smoke suggestion does not recommend features with no testable scenarios
- Verify smoke failure halt message is visually prominent and blocks progression
