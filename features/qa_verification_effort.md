# Feature: QA Verification Effort Classification

> Label: "Critic: QA Effort Classification"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The Critic computes a per-feature **verification effort** classification that breaks down verification work into Builder-owned auto-verified categories and QA-owned manual categories. Builder-owned categories are computed for status tracking but do not generate QA action items. QA only sees manual items and cross-feature integration work.

---

## 2. Requirements

### 2.1 Verification Effort Taxonomy

The Critic MUST classify each feature's pending verification work into exactly four categories:

| Category | Key | Owner | Definition | Resolution Method |
|----------|-----|-------|------------|-------------------|
| TestOnly | `test_only` | **Builder** | Feature has ONLY Unit Tests (no QA scenarios, no visual spec). Tests pass | Builder marks `[Complete]` directly |
| Skip | `skip` | **Builder** | Regression scope is `cosmetic` -- skip entirely | Builder marks `[Complete]` with cosmetic scope |
| Auto | `auto` | **QA** | QA Scenarios with `@auto` tag, or visual spec items on `> Web Test:` features | QA runs directly (servers, Playwright, etc.) |
| Manual | `manual` | **QA** | QA Scenarios without `@auto` tag, or visual spec items on non-web features | `/pl-verify` with human |

A single feature MAY have BOTH auto and manual items. Counts reflect individual scenarios and visual checklist items, not whole features. When QA determines a manual scenario can be automated, QA adds the `@auto` tag and optionally authors the automation.

Builder-owned categories (TestOnly, Skip) are computed but NOT shown as QA action items. QA's `verification_effort` summary only counts QA-owned categories (auto and manual).

### 2.2 Classification Rules

*   **Web test detection:** A feature is web-test-eligible if it contains a `> Web Test:` metadata line (or legacy `> AFT Web:` for backward compatibility). The Critic already parses this metadata for other purposes.
*   **QA scenario count:** The number of `#### Scenario:` headings under `### QA Scenarios` (or legacy `### Manual Scenarios (Human Verification Required)`).
*   **@auto detection:** A QA scenario heading containing `@auto` as a suffix (e.g., `#### Scenario: Title @auto`) is classified as auto. QA scenarios without the tag are classified as manual.
*   **Visual checklist item count:** The number of `- [ ]` items under `## Visual Specification`.
*   **Test-only detection:** A feature is `test_only` when it has Unit Tests, zero QA scenarios, zero visual spec items, and `tests/<feature>/tests.json` exists with `status: "PASS"`.
*   **Cosmetic detection:** A feature is `skip` when its `regression_scope.change_scope` is `"cosmetic"` AND the cosmetic first-pass guard (policy_critic.md Section 2.8) did not escalate it to `full`.
*   **Visual spec classification:** On web-test features, visual spec items are classified as `auto`. On non-web-test features, visual spec items are classified as `manual`.
*   **Scope filtering:** Classification respects regression scoping. A `targeted:` scope reduces the count to only named scenarios/screens. A `cosmetic` scope sets all counts to zero and `skip` to 1. A `dependency-only` scope counts only scenarios in the Critic's computed `regression_scope.scenarios` list.

### 2.3 Output Schema

The Critic MUST include a `verification_effort` block in each feature's `tests/<feature>/critic.json`:

```json
"verification_effort": {
    "auto": 5,
    "manual": 6,
    "test_only": 0,
    "skip": 0,
    "summary": "6 manual"
}
```

*   `summary` is a human-readable string: `"<manual> manual"` when manual items exist, `"<auto> auto"` when only auto items exist, `"<auto> auto, <manual> manual"` when both exist.
*   When all counts are zero (no QA work pending), `summary` is `"no QA items"`.
*   When a feature is `[Complete]` via Builder (no `[Verified]`), `summary` is `"builder-verified"`.

### 2.4 Computation Timing

The `verification_effort` block MUST be computed during the same Critic pass that computes `role_status` and `regression_scope`. It uses data already parsed by `compute_role_status()` -- scenario counts, visual spec detection, `> Web Test:` metadata, and regression scope. No additional file reads are required.

### 2.5 Lifecycle Gating

The `verification_effort` block is only meaningful for features in TESTING lifecycle state (QA role status is TODO). For features in other states:
*   **COMPLETE (qa: CLEAN):** All counts are zero, summary is `"no QA items"`.
*   **COMPLETE via Builder (qa: N/A, zero manual scenarios):** All counts are zero, summary is `"builder-verified"`.
*   **Not yet implemented (qa: N/A):** All counts are zero, summary is `"no QA items"`.
*   **Builder not done (builder: TODO/FAIL):** All counts are zero, summary is `"awaiting builder"`.

### 2.6 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/qa_verification_effort/varied-effort-types` | Project with features having auto-verified-only, manual, and mixed verification classifications |

---

## 3. Scenarios

### Unit Tests

#### Scenario: Web-test feature classifies visual items as auto and QA scenarios normally

    Given a feature has `> Web Test: http://localhost:9086` metadata
    And the feature has 3 QA scenarios (no @auto tag) and 2 visual checklist items
    When the Critic computes verification_effort for this feature
    Then `auto` is 2 (visual items on web-test feature)
    And `manual` is 3
    And `summary` is "3 manual"

#### Scenario: Non-web-test feature classifies QA scenarios as manual

    Given a feature does NOT have `> Web Test:` metadata
    And the feature has 4 QA scenarios without @auto tag
    When the Critic computes verification_effort
    Then `manual` is 4
    And `auto` is 0
    And `summary` is "4 manual"

#### Scenario: Feature with only Unit Tests classifies as test_only

    Given a feature has 5 Unit Test scenarios and zero QA scenarios
    And the feature has no `## Visual Specification` section
    And `tests/<feature>/tests.json` exists with `status: "PASS"`
    When the Critic computes verification_effort
    Then `test_only` is 1
    And all other category counts are 0
    And `summary` is "builder-verified"

#### Scenario: QA scenarios with @auto tag classified as auto

    Given a feature has 2 QA scenarios with @auto tag and 1 without
    When the Critic computes verification_effort
    Then `auto` is 2
    And `manual` is 1
    And `summary` is "2 auto, 1 manual"

#### Scenario: Visual spec items classified by web-test eligibility

    Given a non-web-test feature has 6 visual checklist items and no QA scenarios
    When the Critic computes verification_effort
    Then `manual` is 6
    And `auto` is 0
    And `summary` is "6 manual"

#### Scenario: Cosmetic scope feature classified as skip

    Given a feature has `regression_scope.change_scope` of "cosmetic"
    And the cosmetic first-pass guard did not escalate
    When the Critic computes verification_effort
    Then `skip` is 1
    And all other counts are 0
    And `summary` is "builder-verified"

#### Scenario: Targeted scope reduces counts to named items only

    Given a feature has 5 QA scenarios
    And `regression_scope.change_scope` is "targeted:Scenario A,Scenario B"
    When the Critic computes verification_effort
    Then only 2 scenarios are counted (the targeted ones)
    And the remaining 3 are excluded from all categories

#### Scenario: Builder-incomplete feature shows awaiting builder

    Given a feature has `role_status.builder` of "TODO"
    When the Critic computes verification_effort
    Then all counts are 0
    And `summary` is "awaiting builder"

#### Scenario: Builder-verified feature produces qa N/A

    Given a feature has zero QA scenarios
    And all Unit Tests pass
    And the Builder marks `[Complete]` (no `[Verified]`)
    When the Critic computes verification_effort
    Then `qa` status is `"N/A"`
    And `summary` is "builder-verified"

### QA Scenarios

None.
