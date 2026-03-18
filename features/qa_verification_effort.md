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

The Critic MUST classify each feature's pending verification work into exactly six categories:

| Category | Key | Owner | Definition | Resolution Method |
|----------|-----|-------|------------|-------------------|
| Web:Test | `web_test` | **Builder** | Visual spec items on features with `> Web Test:` metadata | Builder runs `/pl-web-test` during B2 |
| TestOnly | `test_only` | **Builder** | Feature has ONLY automated scenarios (no manual scenarios, no visual spec). Tests pass | Builder marks `[Complete]` directly |
| Skip | `skip` | **Builder** | Regression scope is `cosmetic` -- skip entirely | Builder marks `[Complete]` with cosmetic scope |
| Manual:Interactive | `manual_interactive` | **QA** | Manual scenarios on non-web-test features requiring human interaction | `/pl-verify` with human |
| Manual:Visual | `manual_visual` | **QA** | Visual spec checklist items on non-web-test features | `/pl-verify` with screenshot exchange |
| Manual:Hardware | `manual_hardware` | **QA** | Steps explicitly requiring physical hardware or non-browser environment | Human-in-the-loop only |

A single feature MAY have BOTH auto-verified and manual items. Counts reflect individual scenarios and visual checklist items, not whole features. If a manual scenario CAN be fully verified via browser automation, the Architect SHOULD move it to `### Automated Scenarios` with an `(auto-web)` tag -- at that point it is counted by traceability, not effort classification.

Builder-owned categories (Web:Test, TestOnly, Skip) are computed but NOT shown as QA action items. QA's `verification_effort` summary only counts QA-owned categories.

### 2.2 Classification Rules

*   **Web test detection:** A feature is web-test-eligible if it contains a `> Web Test:` metadata line (or legacy `> AFT Web:` for backward compatibility). The Critic already parses this metadata for other purposes.
*   **Manual scenario count:** The number of `#### Scenario:` headings under `### Manual Scenarios (Human Verification Required)`.
*   **Visual checklist item count:** The number of `- [ ]` items under `## Visual Specification`.
*   **Automated-only detection:** A feature is `test_only` when it has automated scenarios, zero manual scenarios, zero visual spec items, and `tests/<feature>/tests.json` exists with `status: "PASS"`.
*   **Cosmetic detection:** A feature is `skip` when its `regression_scope.change_scope` is `"cosmetic"` AND the cosmetic first-pass guard (policy_critic.md Section 2.8) did not escalate it to `full`.
*   **Web test visual reclassification:** On web-test features, visual spec items are classified as `web_test`. Manual scenarios on web-test features follow the same classification as non-web-test features (`manual_interactive` or `manual_hardware`).
*   **Hardware classification:** Manual scenario steps that reference physical hardware, serial ports, GPIO, USB devices, or non-browser environments are classified as `manual_hardware`. The Critic uses keyword matching on scenario step text: `hardware`, `serial`, `GPIO`, `USB`, `device`, `physical`. If no hardware keywords are found, manual scenarios default to `manual_interactive`.
*   **Scope filtering:** Classification respects regression scoping. A `targeted:` scope reduces the count to only named scenarios/screens. A `cosmetic` scope sets all counts to zero and `skip` to 1. A `dependency-only` scope counts only scenarios in the Critic's computed `regression_scope.scenarios` list.

### 2.3 Output Schema

The Critic MUST include a `verification_effort` block in each feature's `tests/<feature>/critic.json`:

```json
"verification_effort": {
    "web_test": 3,
    "test_only": 0,
    "skip": 0,
    "manual_interactive": 2,
    "manual_visual": 4,
    "manual_hardware": 0,
    "total_auto": 3,
    "total_manual": 6,
    "summary": "6 manual"
}
```

*   `total_auto` = `web_test` + `test_only` + `skip`.
*   `total_manual` = `manual_interactive` + `manual_visual` + `manual_hardware`.
*   `summary` is a human-readable string: `"<total_manual> manual"`. Auto-verified counts are not included in the summary (they are Builder-owned).
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

### Automated Scenarios

#### Scenario: Web-test feature classifies visual items as web_test and manual scenarios normally

    Given a feature has `> Web Test: http://localhost:9086` metadata
    And the feature has 3 manual scenarios and 2 visual checklist items
    When the Critic computes verification_effort for this feature
    Then `web_test` is 2 (visual items only)
    And `manual_interactive` is 3
    And `summary` is "3 manual"

#### Scenario: Non-web-test feature classifies manual scenarios as manual_interactive

    Given a feature does NOT have `> Web Test:` metadata
    And the feature has 4 manual scenarios
    When the Critic computes verification_effort
    Then `manual_interactive` is 4
    And `web_test` is 0
    And `summary` is "4 manual"

#### Scenario: Feature with only automated scenarios classifies as test_only

    Given a feature has 5 automated scenarios and zero manual scenarios
    And the feature has no `## Visual Specification` section
    And `tests/<feature>/tests.json` exists with `status: "PASS"`
    When the Critic computes verification_effort
    Then `test_only` is 1
    And all other category counts are 0
    And `summary` is "builder-verified"

#### Scenario: Web-test feature with mixed manual types and visual items

    Given a web-test feature has 2 interactive manual scenarios and 1 hardware manual scenario
    And the feature has 2 visual checklist items
    When the Critic computes verification_effort
    Then `web_test` is 2 (visual items only)
    And `manual_interactive` is 2
    And `manual_hardware` is 1
    And `summary` is "3 manual"

#### Scenario: Visual spec items classified by web-test eligibility

    Given a non-web-test feature has 6 visual checklist items and no manual scenarios
    When the Critic computes verification_effort
    Then `manual_visual` is 6
    And `web_test` is 0
    And `summary` is "6 manual"

#### Scenario: Cosmetic scope feature classified as skip

    Given a feature has `regression_scope.change_scope` of "cosmetic"
    And the cosmetic first-pass guard did not escalate
    When the Critic computes verification_effort
    Then `skip` is 1
    And all other counts are 0
    And `summary` is "builder-verified"

#### Scenario: Targeted scope reduces counts to named items only

    Given a feature has 5 manual scenarios
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

    Given a feature has zero manual scenarios
    And all automated tests pass
    And the Builder marks `[Complete]` (no `[Verified]`)
    When the Critic computes verification_effort
    Then `qa` status is `"N/A"`
    And `summary` is "builder-verified"

### Manual Scenarios (Human Verification Required)

None.
