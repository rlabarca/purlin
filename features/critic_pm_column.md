# Feature: Critic PM Column

> Label: "Critic PM Column"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/critic_tool.md
> Prerequisite: features/design_artifact_pipeline.md

[TODO]

## 1. Overview

Adds PM as a first-class role in the Critic coordination engine and CDD dashboard. The Critic parses the `> Owner:` metadata tag from feature files to route action items (especially SPEC_DISPUTEs and design-related items) to either PM or Architect. The CDD dashboard displays a PM column alongside Architect, Builder, and QA.

---

## 2. Requirements

### 2.1 Owner Tag Parsing
- The Critic reads `> Owner: PM` or `> Owner: Architect` from the blockquote metadata of each feature file.
- When absent, the default owner is Architect.
- Anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`) are always Architect-owned. The Critic ignores the Owner tag if present on an anchor node.

### 2.2 PM Action Item Routing
The `generate_action_items` function MUST return a `pm` key in its output. The following items route to PM:
- SPEC_DISPUTEs on features with `> Owner: PM` route to PM.
- SPEC_DISPUTEs referencing Visual Specification screens route to PM, regardless of Owner tag.
- `stale_design_description` items route to PM (moved from Architect).
- `unprocessed_artifact` items route to PM (moved from Architect).
- `missing_design_reference` items route to PM (moved from Architect).
- DESIGN_CONFLICT warnings route to PM.

### 2.3 Architect Action Items (Unchanged)
The following items remain with Architect and MUST NOT be routed to PM:
- All spec gate items.
- All INFEASIBLE items.
- Builder decision items (DEVIATION/DISCOVERY).
- SPEC_DISPUTEs on Architect-owned features (no Owner tag or `> Owner: Architect`) that do not reference Visual Specification screens.
- Untracked file items.

### 2.4 PM Role Status
The `compute_role_status` function MUST return a `pm` key for each feature:
- `DONE` -- No PM action items for this feature.
- `TODO` -- Pending PM work (visual spec gaps, stale designs, disputes on PM-owned features).
- `N/A` -- Feature has no Visual Specification section, no Figma references, and is not `> Owner: PM`.

### 2.5 CDD Dashboard Updates
- `_role_table_html()` adds a PM column.
- `get_feature_role_status()` reads `pm` from `critic.json`.
- JavaScript `roles` arrays include `'pm'`.
- Agent config save endpoint accepts `pm` key.
- Feature status API includes `pm` field.

### 2.6 Report Generator
- The aggregate report generator (`CRITIC_REPORT.md`) MUST iterate over `('Architect', 'Builder', 'QA', 'PM')` for the role-specific action items section.
- PM action items are listed under a `### PM` subsection.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: SPEC_DISPUTE on PM-owned feature routes to PM

    Given a feature file with `> Owner: PM` metadata
    And the feature has an OPEN SPEC_DISPUTE in its discovery sidecar
    When the Critic generates action items
    Then the SPEC_DISPUTE appears in the `pm` action items
    And does not appear in the `architect` action items

#### Scenario: SPEC_DISPUTE on Architect-owned feature routes to Architect

    Given a feature file with `> Owner: Architect` metadata
    And the feature has an OPEN SPEC_DISPUTE in its discovery sidecar
    When the Critic generates action items
    Then the SPEC_DISPUTE appears in the `architect` action items
    And does not appear in the `pm` action items

#### Scenario: SPEC_DISPUTE on feature with no Owner tag defaults to Architect

    Given a feature file with no `> Owner:` metadata
    And the feature has an OPEN SPEC_DISPUTE in its discovery sidecar
    When the Critic generates action items
    Then the SPEC_DISPUTE appears in the `architect` action items
    And does not appear in the `pm` action items

#### Scenario: Visual SPEC_DISPUTE on Architect-owned feature routes to PM

    Given a feature file with `> Owner: Architect` metadata
    And the feature has a Visual Specification section
    And the feature has an OPEN SPEC_DISPUTE referencing a Visual Specification screen
    When the Critic generates action items
    Then the SPEC_DISPUTE appears in the `pm` action items
    And does not appear in the `architect` action items

#### Scenario: Stale design description routes to PM

    Given a feature with a Visual Specification screen
    And the referenced artifact file is newer than the Processed date
    When the Critic runs the visual specification audit
    Then a `stale_design_description` action item is generated for the `pm` role
    And no `stale_design_description` item is generated for the `architect` role

#### Scenario: Unprocessed artifact routes to PM

    Given a feature with a Visual Specification screen
    And the screen has a Reference but no Description
    When the Critic runs the visual specification audit
    Then an `unprocessed_artifact` action item is generated for the `pm` role
    And no `unprocessed_artifact` item is generated for the `architect` role

#### Scenario: Feature with no visual spec and not PM-owned reports PM N/A

    Given a feature file with no `> Owner: PM` metadata
    And the feature has no Visual Specification section
    And the feature has no Figma references
    When the Critic computes role status
    Then `pm` role status is `N/A`

#### Scenario: PM-owned feature with no PM items reports PM DONE

    Given a feature file with `> Owner: PM` metadata
    And there are no PM action items for the feature
    When the Critic computes role status
    Then `pm` role status is `DONE`

#### Scenario: PM-owned feature with pending items reports PM TODO

    Given a feature file with `> Owner: PM` metadata
    And there is an OPEN SPEC_DISPUTE routed to PM
    When the Critic computes role status
    Then `pm` role status is `TODO`

#### Scenario: Aggregate report includes PM section

    Given one or more features have PM action items
    When the Critic generates the aggregate report
    Then `CRITIC_REPORT.md` contains a `### PM` subsection under Action Items by Role
    And PM action items are listed within that subsection

#### Scenario: CDD dashboard shows PM column

    Given the CDD dashboard is running
    And `critic.json` files contain `pm` role status
    When the dashboard renders the feature status table
    Then a PM column is displayed alongside Architect, Builder, and QA columns
    And each feature row shows the PM status value

### Manual Scenarios (Human Verification Required)

None.
