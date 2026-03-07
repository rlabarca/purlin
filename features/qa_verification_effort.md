# Feature: QA Verification Effort Classification

> Label: "Critic: QA Effort Classification"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The Critic computes a per-feature **verification effort** classification that breaks down QA work into auto-resolvable and human-required categories. This replaces the coarse TODO/CLEAN/FAIL status with a granular effort signal, enabling the QA agent to prioritize and auto-execute low-friction verification items before engaging the human tester.

---

## 2. Requirements

### 2.1 Verification Effort Taxonomy

The Critic MUST classify each feature's pending QA work into exactly six categories:

| Category | Key | Definition | Resolution Method |
|----------|-----|------------|-------------------|
| Auto:Web | `auto_web` | Manual scenarios + visual spec items on features with `> Web Testable:` metadata | Agent runs `/pl-web-verify` autonomously |
| Auto:TestOnly | `auto_test_only` | Feature has ONLY automated scenarios (no manual scenarios, no visual spec). QA confirms tests pass | Agent reads `tests.json`, ACKs pass status |
| Auto:Skip | `auto_skip` | Regression scope is `cosmetic` -- skip entirely | Agent skips and logs |
| Manual:Interactive | `manual_interactive` | Manual scenarios on non-web-testable features requiring human interaction | `/pl-verify` with human |
| Manual:Visual | `manual_visual` | Visual spec checklist items on non-web-testable features | `/pl-verify` with screenshot exchange |
| Manual:Hardware | `manual_hardware` | Steps explicitly requiring physical hardware or non-browser environment | Human-in-the-loop only |

A single feature MAY have BOTH auto and manual items (e.g., some scenarios are web-testable but one was marked INCONCLUSIVE in a prior run). Counts reflect individual scenarios and visual checklist items, not whole features.

### 2.2 Classification Rules

*   **Web-testable detection:** A feature is web-testable if it contains a `> Web Testable:` metadata line. The Critic already parses this metadata for other purposes.
*   **Manual scenario count:** The number of `#### Scenario:` headings under `### Manual Scenarios (Human Verification Required)`.
*   **Visual checklist item count:** The number of `- [ ]` items under `## Visual Specification`.
*   **Automated-only detection:** A feature is `auto_test_only` when it has automated scenarios, zero manual scenarios, zero visual spec items, and `tests/<feature>/tests.json` exists with `status: "PASS"`.
*   **Cosmetic detection:** A feature is `auto_skip` when its `regression_scope.change_scope` is `"cosmetic"` AND the cosmetic first-pass guard (policy_critic.md Section 2.8) did not escalate it to `full`.
*   **Hardware classification:** Manual scenario steps that reference physical hardware, serial ports, GPIO, USB devices, or non-browser environments are classified as `manual_hardware`. The Critic uses keyword matching on scenario step text: `hardware`, `serial`, `GPIO`, `USB`, `device`, `physical`. If no hardware keywords are found, manual scenarios on non-web features default to `manual_interactive`.
*   **Scope filtering:** Classification respects regression scoping. A `targeted:` scope reduces the count to only named scenarios/screens. A `cosmetic` scope sets all counts to zero and `auto_skip` to 1. A `dependency-only` scope counts only scenarios in the Critic's computed `regression_scope.scenarios` list.

### 2.3 Output Schema

The Critic MUST include a `verification_effort` block in each feature's `tests/<feature>/critic.json`:

```json
"verification_effort": {
    "auto_web": 3,
    "auto_test_only": 0,
    "auto_skip": 0,
    "manual_interactive": 2,
    "manual_visual": 4,
    "manual_hardware": 0,
    "total_auto": 3,
    "total_manual": 6,
    "summary": "3 auto, 6 manual"
}
```

*   `total_auto` = `auto_web` + `auto_test_only` + `auto_skip`.
*   `total_manual` = `manual_interactive` + `manual_visual` + `manual_hardware`.
*   `summary` is a human-readable string: `"<total_auto> auto, <total_manual> manual"`.
*   When all counts are zero (no QA work pending), `summary` is `"no QA items"`.

### 2.4 Computation Timing

The `verification_effort` block MUST be computed during the same Critic pass that computes `role_status` and `regression_scope`. It uses data already parsed by `compute_role_status()` -- scenario counts, visual spec detection, `> Web Testable:` metadata, and regression scope. No additional file reads are required.

### 2.5 Lifecycle Gating

The `verification_effort` block is only meaningful for features in TESTING lifecycle state (QA role status is TODO). For features in other states:
*   **COMPLETE (qa: CLEAN):** All counts are zero, summary is `"no QA items"`.
*   **Not yet implemented (qa: N/A):** All counts are zero, summary is `"no QA items"`.
*   **Builder not done (builder: TODO/FAIL):** All counts are zero, summary is `"awaiting builder"`.

### 2.6 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/qa_verification_effort/varied-effort-types` | Project with features having auto-only, manual, and mixed QA classifications |

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Web-testable feature classifies manual scenarios as auto_web

    Given a feature has `> Web Testable: http://localhost:9086` metadata
    And the feature has 3 manual scenarios and 2 visual checklist items
    When the Critic computes verification_effort for this feature
    Then `auto_web` is 5 (3 scenarios + 2 visual items)
    And `manual_interactive` is 0
    And `manual_visual` is 0
    And `summary` is "5 auto, 0 manual"

#### Scenario: Non-web feature classifies manual scenarios as manual_interactive

    Given a feature does NOT have `> Web Testable:` metadata
    And the feature has 4 manual scenarios
    When the Critic computes verification_effort
    Then `manual_interactive` is 4
    And `auto_web` is 0
    And `summary` is "0 auto, 4 manual"

#### Scenario: Feature with only automated scenarios classifies as auto_test_only

    Given a feature has 5 automated scenarios and zero manual scenarios
    And the feature has no `## Visual Specification` section
    And `tests/<feature>/tests.json` exists with `status: "PASS"`
    When the Critic computes verification_effort
    Then `auto_test_only` is 1
    And all other category counts are 0
    And `summary` is "1 auto, 0 manual"

#### Scenario: Mixed feature splits counts correctly

    Given a web-testable feature has 3 manual scenarios
    And 1 scenario was previously marked INCONCLUSIVE by `/pl-web-verify`
    And the feature has 2 visual checklist items
    When the Critic computes verification_effort
    Then `auto_web` is 4 (2 remaining web scenarios + 2 visual items)
    And `manual_interactive` is 1 (the INCONCLUSIVE scenario)
    And `summary` is "4 auto, 1 manual"

#### Scenario: Visual spec items classified by web-testability

    Given a non-web-testable feature has 6 visual checklist items and no manual scenarios
    When the Critic computes verification_effort
    Then `manual_visual` is 6
    And `auto_web` is 0
    And `summary` is "0 auto, 6 manual"

#### Scenario: Cosmetic scope feature classified as auto_skip

    Given a feature has `regression_scope.change_scope` of "cosmetic"
    And the cosmetic first-pass guard did not escalate
    When the Critic computes verification_effort
    Then `auto_skip` is 1
    And all other counts are 0
    And `summary` is "1 auto, 0 manual"

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

### Manual Scenarios (Human Verification Required)

None.
