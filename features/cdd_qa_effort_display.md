# Feature: CDD QA Effort Display

> Label: "CDD: QA Effort Breakdown"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/qa_verification_effort.md
> Prerequisite: features/design_visual_standards.md
> Web Testable: http://localhost:9086

[TODO]

## 1. Overview

The CDD Dashboard's QA column currently shows coarse status values (TODO, CLEAN, FAIL, DISPUTED, N/A). When QA is TODO, there is no indication of how much work is needed or what kind -- a feature with 8 manual hardware-in-the-loop scenarios looks identical to one with 2 web-verifiable checks. This feature enriches the QA column with an effort breakdown derived from the Critic's `verification_effort` block.

---

## 2. Requirements

### 2.1 QA Column Enrichment

*   When a feature's QA status is `TODO`, the dashboard table cell MUST display the effort breakdown inline: `TODO (Na/Mm)` where `N` is `total_auto` and `M` is `total_manual` from the feature's `verification_effort` block.
*   Examples: `TODO (3a/6m)`, `TODO (0a/2m)`, `TODO (5a/0m)`.
*   When both `total_auto` and `total_manual` are zero (e.g., `summary` is `"awaiting builder"`), display only `TODO` with no parenthetical.
*   Non-TODO QA statuses (CLEAN, FAIL, DISPUTED, N/A) are unchanged.

### 2.2 Effort Tooltip

*   When the user hovers over a QA cell showing the effort breakdown, a tooltip MUST display the full category breakdown:
    *   `Auto: N web, N test-only, N skip`
    *   `Manual: N interactive, N visual, N hardware`
*   Categories with zero count MAY be omitted from the tooltip for brevity.

### 2.3 Data Source

*   The dashboard reads `verification_effort` from the per-feature `critic.json` files, alongside the existing `role_status` data.
*   The `/status.json` API endpoint MUST include the `verification_effort` block for each feature.
*   No additional Critic invocation is required; the data is pre-computed.

### 2.4 Theme Compatibility

*   The effort breakdown text MUST be legible in both light and dark themes.
*   The parenthetical `(Na/Mm)` uses a muted color (lower contrast than the status badge) to avoid visual clutter.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: QA TODO cell shows effort breakdown

    Given a feature has QA status "TODO"
    And its `verification_effort` has `total_auto: 3` and `total_manual: 6`
    When the CDD dashboard renders the Status view
    Then the QA cell displays "TODO (3a/6m)"

#### Scenario: QA TODO with zero effort shows plain TODO

    Given a feature has QA status "TODO"
    And its `verification_effort.summary` is "awaiting builder"
    When the CDD dashboard renders the Status view
    Then the QA cell displays "TODO" with no parenthetical

#### Scenario: Non-TODO QA status is unchanged

    Given a feature has QA status "CLEAN"
    When the CDD dashboard renders the Status view
    Then the QA cell displays "CLEAN" with no effort breakdown

#### Scenario: Status JSON includes verification_effort

    Given the Critic has run and produced `critic.json` files with `verification_effort`
    When a client requests `/status.json`
    Then each feature object includes the `verification_effort` block

### Manual Scenarios (Human Verification Required)

#### Scenario: Effort tooltip displays full breakdown

    Given a feature's QA cell shows "TODO (3a/6m)"
    When the user hovers over the QA cell
    Then a tooltip displays: "Auto: 3 web" and "Manual: 2 interactive, 4 visual"
    And zero-count categories are omitted

#### Scenario: Effort breakdown is legible in dark theme

    Given the CDD dashboard is in dark theme
    When a QA cell shows "TODO (5a/2m)"
    Then the parenthetical text is visible and uses a muted color distinct from the badge

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: QA Effort Column
- **Reference:** N/A
- **Processed:** N/A
- **Description:** QA column cells showing TODO status display an inline effort breakdown `(Na/Mm)` in muted text after the status badge. Non-TODO statuses are unchanged.
- [ ] Effort breakdown `(Na/Mm)` is visible next to TODO badge
- [ ] Muted color for parenthetical distinguishes it from the badge
- [ ] Tooltip appears on hover with full category breakdown
- [ ] Both light and dark themes render breakdown legibly

