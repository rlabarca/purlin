# Feature: /pl-smoke Smoke Test Promotion

> Label: "Agent Skills: QA: /pl-smoke Smoke Test Promotion"
> Category: "Agent Skills: QA"
> Prerequisite: features/purlin_mode_system.md

## 1. Overview

The `/pl-smoke` skill allows QA mode to promote any test (regression, @auto, or @manual) to smoke tier and optionally create a simplified fast-running smoke version. Smoke tests run first in every QA verification pass and block further verification on failure. QA proactively suggests smoke promotion for critical features that lack smoke coverage.

---

## 2. Requirements

### 2.1 Smoke Promotion

- `/pl-smoke <feature>` MUST add the feature to the `## Test Priority Tiers` table in `PURLIN_OVERRIDES.md` (or `PURLIN_OVERRIDES.md` for legacy projects) with tier `smoke`.
- If the tier table does not exist, the skill MUST create it.
- The skill MUST show the user what tests exist for the feature before promoting.

### 2.2 Simplified Smoke Regression

- After promotion, the skill MUST offer to create a simplified smoke regression at `tests/qa/scenarios/<feature>_smoke.json`.
- Smoke regressions MUST test only the critical path (1-3 scenarios max).
- Smoke regressions MUST target < 30 second execution time.
- Smoke regressions MUST include `"tier": "smoke"` and `"smoke_of": "<feature>.json"` fields.

### 2.3 Smoke Suggestion

- `/pl-smoke suggest` MUST analyze the project and identify features that should be smoke tier.
- Candidates: features with 3+ dependents, `arch_*`/`policy_*` anchors, core categories (Install/Update, Coordination), names containing launcher/init/config/status/scan.
- MUST filter out features already classified as smoke.
- MUST present suggestions with rationale and let the user select.

### 2.4 Verification Integration

- The `/pl-verify` smoke gate (Step 2) MUST run smoke regressions (`_smoke.json`) BEFORE smoke QA scenarios.
- The smoke gate MUST read the tier table from BOTH `PURLIN_OVERRIDES.md` and `PURLIN_OVERRIDES.md`.
- The smoke gate MUST also detect `_smoke.json` files with `"tier": "smoke"` even if the feature is not in the tier table.
- A smoke failure MUST block all further verification with a prominent halt message.
- After smoke passes, the verify skill MUST suggest smoke promotion for high-fan-out features lacking smoke classification (once per session).

### 2.5 Smoke Tier Rules

- Smoke tests run FIRST in every QA verification pass.
- A smoke failure blocks standard and full-only verification.
- Every project should have 5-15 smoke features covering the critical path.
- Smoke tests verify "is it broken?" not "is every edge case handled?"

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Promote feature to smoke tier

    Given feature "project_init" exists with passing regression tests
    And it is not in the Test Priority Tiers table
    When /pl-smoke project_init is invoked
    Then "project_init" is added to the tier table with tier "smoke"

#### Scenario: Create tier table when missing

    Given PURLIN_OVERRIDES.md exists but has no Test Priority Tiers section
    When /pl-smoke project_init is invoked
    Then a "## Test Priority Tiers" section is created
    And "project_init" is added with tier "smoke"

#### Scenario: Offer simplified smoke regression

    Given feature "project_init" has 3 regression scenarios
    When /pl-smoke project_init is invoked and user accepts simplification
    Then tests/qa/scenarios/project_init_smoke.json is created
    And it contains 1-3 scenarios (fewer than the full suite)
    And it contains "tier": "smoke"

#### Scenario: Smoke suggestion identifies high-fan-out features

    Given feature "agent_launchers_common" is a prerequisite for 12 features
    And it is not in the tier table
    When /pl-smoke suggest is invoked
    Then "agent_launchers_common" appears in the suggestion list

#### Scenario: Smoke suggestion skips already-classified features

    Given feature "project_init" is already in the tier table as smoke
    When /pl-smoke suggest is invoked
    Then "project_init" does not appear in the suggestion list

#### Scenario: Verify smoke gate runs smoke regressions first

    Given feature "agent_launchers_common" has a _smoke.json regression file
    And feature "agent_launchers_common" also has @auto QA scenarios
    When /pl-verify runs the smoke gate
    Then the _smoke.json regression runs BEFORE the @auto scenarios

#### Scenario: Verify smoke failure blocks further verification

    Given a smoke-tier feature with a failing smoke regression
    When /pl-verify runs the smoke gate
    Then a prominent SMOKE FAILURE message is displayed
    And the user is prompted to stop or continue
    And standard-tier features are NOT verified until the user responds

### Manual Scenarios (Human Verification Required)

#### Scenario: Smoke regression targets fast execution @manual

    Given a smoke regression file was created by /pl-smoke
    When the scenario count is checked
    Then it has 3 or fewer scenarios
    And each scenario is designed for < 30 second execution

#### Scenario: End-to-end smoke promotion and verification @manual

    Given a feature with no smoke classification
    When /pl-smoke promotes it and creates a smoke regression
    And /pl-verify is run on the project
    Then the smoke regression runs in the smoke gate (Step 2)
    And it runs before all standard-tier features

## Regression Guidance
- Verify _smoke.json files are detected even without a tier table entry
- Verify smoke gate reads from both PURLIN_OVERRIDES.md and PURLIN_OVERRIDES.md
- Verify smoke suggestion does not recommend features with no testable scenarios
- Verify smoke failure halt message is visually prominent and blocks progression
