# Feature: CDD QA Effort Display

> Label: "CDD: QA Effort Breakdown"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/qa_verification_effort.md
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/test_fixture_repo.md
> Web Test: http://localhost:9086
> Web Start: /pl-cdd

[TODO]

## 1. Overview

The CDD Dashboard's QA column shows status values (TODO, AUTO, CLEAN, FAIL, DISPUTED, N/A). `AUTO` is a real Critic status (not a display hack) indicating all QA work is automatable. The display uses a two-line layout: the primary status badge on the first line, and a compact effort summary on a second sub-line (10px, `var(--purlin-dim)`) showing the auto/manual breakdown. No tooltip. Both are derived from the Critic's `verification_effort` block.

---

## 2. Requirements

### 2.1 QA Column — AUTO Status

*   `AUTO` is a real Critic-computed QA status (see `critic_role_status.md` Section 2.4). The CDD dashboard reads it directly from `role_status.qa` in `critic.json` -- no display-side derivation.
*   Non-AUTO QA statuses (TODO, CLEAN, FAIL, DISPUTED, N/A) are unchanged.
*   **AUTO color:** The `AUTO` badge MUST use `var(--purlin-status-auto)` -- green in both light and dark themes -- to signal a positive state (no human work needed), visually distinct from the yellow `TODO` badge.

### 2.1.1 No Aggregate QA Queue Summary

*   The Active section MUST NOT display an aggregate QA queue summary (e.g., "QA Queue: N auto-resolvable, N manual across N features"). Per-feature effort is communicated exclusively through per-cell AUTO/TODO badges and their hover tooltips. No aggregate text is rendered in the section body or heading.

### 2.2 Two-Line Effort Display

*   When a feature's QA status is `TODO` or `AUTO`, the QA cell MUST display a second sub-line below the status badge showing the effort summary from `verification_effort.summary`.
*   **Sub-line styling:** 10px font size, `var(--purlin-dim)` color. Compact and unobtrusive.
*   **Examples:** `AUTO` on line 1, `3 auto` on line 2. Or `TODO` on line 1, `2 auto, 4 manual` on line 2.
*   When the summary is `"awaiting builder"` or `"no QA items"`, no sub-line is shown.
*   Non-TODO/AUTO QA statuses do not show a sub-line.
*   **No tooltip.** The sub-line replaces the previous tooltip approach.

### 2.3 Data Source

*   The dashboard reads `verification_effort` from the per-feature `critic.json` files, alongside the existing `role_status` data.
*   The `/status.json` API endpoint MUST include the `verification_effort` block for each feature.
*   No additional Critic invocation is required; the data is pre-computed.

### 2.4 Theme Compatibility

*   `TODO` continues to use `var(--purlin-status-todo)`.
*   `AUTO` uses `var(--purlin-status-auto)` in both themes.
*   The tooltip MUST be legible in both light and dark themes.

### 2.5 Web-Verify Fixture Tags

The following fixture tags provide deterministic project states for web-verify testing:

| Tag | State Description |
|-----|-------------------|
| `main/cdd_qa_effort_display/auto-and-todo` | Features with AUTO vs TODO QA states for verifying green vs yellow distinction and hover tooltips |

---

## 3. Scenarios

### Unit Tests

#### Scenario: AUTO status displays with green badge

    Given a feature has QA status "AUTO" in critic.json
    When the CDD dashboard renders the Status view
    Then the QA cell displays "AUTO"
    And the AUTO text uses `var(--purlin-status-auto)` color (green)

#### Scenario: TODO status with effort shows sub-line

    Given a feature has QA status "TODO"
    And its `verification_effort.summary` is "2 auto, 4 manual"
    When the CDD dashboard renders the Status view
    Then the QA cell displays "TODO" on line 1
    And "2 auto, 4 manual" on a sub-line (10px, `var(--purlin-dim)`)

#### Scenario: AUTO status with effort shows sub-line

    Given a feature has QA status "AUTO"
    And its `verification_effort.summary` is "3 auto"
    When the CDD dashboard renders the Status view
    Then the QA cell displays "AUTO" on line 1
    And "3 auto" on a sub-line

#### Scenario: QA TODO with zero effort shows plain TODO

    Given a feature has QA status "TODO"
    And its `verification_effort.summary` is "awaiting builder"
    When the CDD dashboard renders the Status view
    Then the QA cell displays "TODO" with no sub-line

#### Scenario: Non-TODO/AUTO QA status has no sub-line

    Given a feature has QA status "CLEAN"
    When the CDD dashboard renders the Status view
    Then the QA cell displays "CLEAN" with no sub-line

#### Scenario: Status JSON includes verification_effort

    Given the Critic has run and produced `critic.json` files with `verification_effort`
    When a client requests `/status.json`
    Then each feature object includes the `verification_effort` block

#### Scenario: AUTO badge is visually distinct from TODO (auto-web)

    Given the CDD dashboard is rendered
    And one feature has QA status AUTO and another has TODO
    When both are visible in the Status view
    Then AUTO uses a green color (`var(--purlin-status-auto)`) distinct from TODO's yellow (`var(--purlin-status-todo)`)
    And the color difference is clear in both light and dark themes

### QA Scenarios

None.

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: QA Effort Column
- **Reference:** N/A
- **Processed:** N/A
- **Description:** QA column cells show TODO (yellow) or AUTO (orange) status. Hovering over TODO or AUTO reveals a tooltip with the full effort breakdown. Non-TODO statuses are unchanged.
- [ ] AUTO badge uses `var(--purlin-status-auto)` (green), visually distinct from TODO's yellow
- [ ] TODO badge continues to use `var(--purlin-status-todo)` (yellow)
- [ ] Sub-line below TODO/AUTO shows effort summary (10px, `var(--purlin-dim)`)
- [ ] Both light and dark themes render AUTO (green) and TODO (yellow) with clearly distinct colors

