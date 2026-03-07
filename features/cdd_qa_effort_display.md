# Feature: CDD QA Effort Display

> Label: "CDD: QA Effort Breakdown"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/qa_verification_effort.md
> Prerequisite: features/design_visual_standards.md
> Web Testable: http://localhost:9086
> Web Port File: .purlin/runtime/cdd.port
> Web Start: /pl-cdd

[TODO]

## 1. Overview

The CDD Dashboard's QA column currently shows coarse status values (TODO, CLEAN, FAIL, DISPUTED, N/A). When QA is TODO, there is no indication of how much work is needed or what kind. This feature adds two enhancements: (1) features that are completely auto-resolvable (zero manual items) display `AUTO` in orange instead of `TODO` in yellow, giving an at-a-glance signal that no human verification is needed; (2) hovering over any `TODO` or `AUTO` badge reveals a tooltip with the full effort breakdown (auto vs manual categories). Both are derived from the Critic's `verification_effort` block.

---

## 2. Requirements

### 2.1 QA Column — AUTO Status

*   When a feature's QA status is `TODO` and its verification effort is **completely auto-resolvable** (`total_manual == 0` and `total_auto > 0`), the QA cell MUST display `AUTO` instead of `TODO`.
*   When a feature's QA status is `TODO` and it has any manual items (`total_manual > 0`), the QA cell displays `TODO` (unchanged).
*   When both `total_auto` and `total_manual` are zero (e.g., `summary` is `"awaiting builder"`), display `TODO` (unchanged).
*   Non-TODO QA statuses (CLEAN, FAIL, DISPUTED, N/A) are unchanged.
*   **AUTO color:** The `AUTO` badge MUST use `var(--purlin-status-auto)` — green in both light and dark themes — to signal a positive state (no human work needed), visually distinct from the yellow `TODO` badge.

### 2.1.1 No Aggregate QA Queue Summary

*   The Active section MUST NOT display an aggregate QA queue summary (e.g., "QA Queue: N auto-resolvable, N manual across N features"). Per-feature effort is communicated exclusively through per-cell AUTO/TODO badges and their hover tooltips. No aggregate text is rendered in the section body or heading.

### 2.2 Effort Tooltip

*   When the user hovers over a QA cell showing `TODO` or `AUTO`, a tooltip MUST display the full effort breakdown:
    *   `Auto: N web, N test-only, N skip`
    *   `Manual: N interactive, N visual, N hardware`
*   Categories with zero count MAY be omitted from the tooltip for brevity.
*   When both totals are zero (awaiting builder), no tooltip is shown.

### 2.3 Data Source

*   The dashboard reads `verification_effort` from the per-feature `critic.json` files, alongside the existing `role_status` data.
*   The `/status.json` API endpoint MUST include the `verification_effort` block for each feature.
*   No additional Critic invocation is required; the data is pre-computed.

### 2.4 Theme Compatibility

*   `TODO` continues to use `var(--purlin-status-todo)`.
*   `AUTO` uses `var(--purlin-status-auto)` in both themes.
*   The tooltip MUST be legible in both light and dark themes.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Fully auto-resolvable feature shows AUTO

    Given a feature has QA status "TODO"
    And its `verification_effort` has `total_auto: 5` and `total_manual: 0`
    When the CDD dashboard renders the Status view
    Then the QA cell displays "AUTO"
    And the AUTO text uses `var(--purlin-status-auto)` color

#### Scenario: Mixed effort feature shows TODO

    Given a feature has QA status "TODO"
    And its `verification_effort` has `total_auto: 3` and `total_manual: 6`
    When the CDD dashboard renders the Status view
    Then the QA cell displays "TODO"

#### Scenario: QA TODO with zero effort shows plain TODO

    Given a feature has QA status "TODO"
    And its `verification_effort.summary` is "awaiting builder"
    When the CDD dashboard renders the Status view
    Then the QA cell displays "TODO" with no tooltip

#### Scenario: Non-TODO QA status is unchanged

    Given a feature has QA status "CLEAN"
    When the CDD dashboard renders the Status view
    Then the QA cell displays "CLEAN" with no effort tooltip

#### Scenario: Status JSON includes verification_effort

    Given the Critic has run and produced `critic.json` files with `verification_effort`
    When a client requests `/status.json`
    Then each feature object includes the `verification_effort` block

### Manual Scenarios (Human Verification Required)

#### Scenario: Effort tooltip displays full breakdown on hover

    Given a feature's QA cell shows "TODO" with manual and auto items
    When the user hovers over the TODO text
    Then a tooltip displays the category breakdown (e.g., "Auto: 3 web | Manual: 2 interactive, 4 visual")
    And zero-count categories are omitted

#### Scenario: AUTO badge is visually distinct from TODO

    Given the CDD dashboard is rendered
    And one feature has QA status AUTO and another has TODO
    When both are visible in the Status view
    Then AUTO uses a green color (`var(--purlin-status-auto)`) distinct from TODO's yellow (`var(--purlin-status-todo)`)
    And the color difference is clear in both light and dark themes

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: QA Effort Column
- **Reference:** N/A
- **Processed:** N/A
- **Description:** QA column cells show TODO (yellow) or AUTO (orange) status. Hovering over TODO or AUTO reveals a tooltip with the full effort breakdown. Non-TODO statuses are unchanged.
- [ ] AUTO badge uses `var(--purlin-status-auto)` (green), visually distinct from TODO's yellow
- [ ] TODO badge continues to use `var(--purlin-status-todo)` (yellow)
- [ ] Tooltip appears on hover over TODO or AUTO text with full category breakdown
- [ ] Both light and dark themes render AUTO (green) and TODO (yellow) with clearly distinct colors

