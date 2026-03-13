# Feature: Critic Role Status & Routing

> Label: "Critic: Role Status & Routing"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/critic_tool.md
> Prerequisite: features/design_artifact_pipeline.md

[TODO]

## 1. Overview

Defines the unified role status computation model and action item routing rules for all four agent roles (PM, Architect, Builder, QA). This feature is the single source of truth for how the Critic maps gate results, user testing findings, and lifecycle state into per-role status values and actionable work items. Previously, Architect/Builder/QA routing was embedded in `critic_tool.md` and PM routing was patched via a separate feature; this feature consolidates all four roles into one coherent model.

---

## 2. Requirements

### 2.1 Role Enumeration
The Critic recognizes four agent roles: **PM**, **Architect**, **Builder**, **QA**. All role-keyed output structures (action items, role status, aggregate report sections) MUST include all four roles.

### 2.2 Owner Tag Parsing
- The Critic reads `> Owner: PM` or `> Owner: Architect` from the blockquote metadata of each feature file.
- When absent, the default owner is Architect.
- Anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`) are always Architect-owned. The Critic ignores the Owner tag if present on an anchor node.

### 2.3 Common Role Status Values

| Role | Possible Values |
|------|----------------|
| **Architect** | `DONE`, `TODO` |
| **Builder** | `DONE`, `TODO`, `FAIL`, `INFEASIBLE`, `BLOCKED` |
| **QA** | `CLEAN`, `TODO`, `FAIL`, `DISPUTED`, `N/A` |
| **PM** | `DONE`, `TODO`, `N/A` |

### 2.4 Role Status Computation

**Architect Status:**
*   `TODO`: Any HIGH or CRITICAL priority Architect action items exist (Spec Gate FAIL, open SPEC_DISPUTE on Architect-owned feature, INFEASIBLE tag, open DISCOVERY/INTENT_DRIFT, unacknowledged DEVIATION).
*   `DONE`: No HIGH or CRITICAL Architect action items.

**Builder Status:**
*   `DONE`: structural_completeness PASS, no open BUGs, no FAIL-level traceability issues, AND feature is NOT in TODO lifecycle state.
*   `TODO`: Feature is in TODO lifecycle state (spec modified after last status commit), OR has other Builder action items.
*   `FAIL`: tests.json exists with status FAIL.
*   `INFEASIBLE`: `[INFEASIBLE]` tag present in Implementation Notes.
*   `BLOCKED`: Active SPEC_DISPUTE exists for this feature (scenarios suspended).

Builder Precedence (highest wins): INFEASIBLE > BLOCKED > FAIL > TODO > DONE.

**QA Status:**
*   `FAIL`: Has OPEN BUGs in discovery sidecar. (Lifecycle-independent.)
*   `DISPUTED`: Has OPEN SPEC_DISPUTEs in discovery sidecar (no BUGs). (Lifecycle-independent.)
*   `TODO`: Any of: (a) Feature in TESTING lifecycle state with at least one manual scenario; (b) Has SPEC_UPDATED items AND feature is in TESTING lifecycle state.
*   `CLEAN`: `tests/<feature>/tests.json` exists with `status: "PASS"`, AND no FAIL/DISPUTED/TODO conditions matched.
*   `N/A`: No FAIL/DISPUTED/TODO/CLEAN conditions matched.

QA Precedence (highest wins): FAIL > DISPUTED > TODO > CLEAN > N/A.

**PM Status:**
*   `DONE`: No PM action items for this feature.
*   `TODO`: Pending PM work (visual spec gaps, stale designs, disputes on PM-owned features).
*   `N/A`: Feature has no Visual Specification section, no Figma references, and is not `> Owner: PM`.

### 2.5 Action Item Routing

The Critic generates imperative action items for each role based on analysis results. The following table defines the complete routing rules for all four roles:

**Architect action items:**

| Source | Priority | Example |
|--------|----------|---------|
| Spec Gate FAIL (missing sections, broken prereqs) | HIGH | "Fix spec gap: section_completeness -- missing Requirements" |
| OPEN DISCOVERY/INTENT_DRIFT in User Testing | HIGH | "Update spec for cdd_status_monitor: [discovery title]" |
| OPEN SPEC_DISPUTE on Architect-owned features (no Owner tag or `> Owner: Architect`) that do not reference Visual Specification screens | HIGH | "Review disputed scenario in critic_tool: [dispute title]" |
| `[INFEASIBLE]` tag in Implementation Notes | CRITICAL | "Revise infeasible spec for submodule_sync: [rationale]" |
| Unacknowledged `[DEVIATION]`/`[DISCOVERY]` tags | HIGH | "Acknowledge Builder decision in critic_tool: [tag title]" |
| Spec Gate WARN (no manual scenarios, empty impl notes) | LOW | "Improve spec: scenario_classification -- only Automated" |
| Untracked files detected | MEDIUM | "Triage untracked file: tests/critic_tool/critic.json" |

**Builder action items:**

| Source | Priority | Example |
|--------|----------|---------|
| Feature in TODO lifecycle state | HIGH | "Implement spec changes for critic_tool: N new scenario(s)" |
| New scenario with weak traceability match | HIGH | "New scenario 'X' has no dedicated test" |
| Structural completeness FAIL | HIGH | "Fix structural completeness for X: [detail]" |
| Structural completeness WARN (tests.json with FAIL) | HIGH | "Fix failing tests for X" |
| Traceability gaps (unmatched scenarios) | MEDIUM | "Write tests for: Zero-Queue Verification" |
| OPEN BUGs in User Testing | HIGH | "Fix bug in critic_tool: [bug title]" |
| Cross-validation warnings (invalid targeted scope names) | MEDIUM | "Fix scope declaration for X: [detail]" |

**QA action items:**

| Source | Priority | Example |
|--------|----------|---------|
| Features in TESTING status with manual scenarios | HIGH | "Verify cdd_status_monitor: 3 manual scenario(s)" |
| SPEC_UPDATED discoveries (feature in TESTING lifecycle) | MEDIUM | "Re-verify critic_tool: [item title]" |

**PM action items:**

| Source | Priority | Example |
|--------|----------|---------|
| SPEC_DISPUTEs on features with `> Owner: PM` | HIGH | "Review disputed scenario in X: [dispute title]" |
| SPEC_DISPUTEs referencing Visual Specification screens (regardless of Owner tag) | HIGH | "Review visual dispute in X: [dispute title]" |
| `stale_design_description` items | LOW | "Re-process stale design for X: [screen]" |
| `unprocessed_artifact` items | HIGH | "Process design artifact for X: [screen]" |
| `missing_design_reference` items | MEDIUM | "Fix missing design reference for X: [screen]" |
| DESIGN_CONFLICT warnings | MEDIUM | "Resolve design conflict in X: [detail]" |

### 2.6 Architect-Retained Items
The following items remain with Architect and MUST NOT be routed to PM:
- All spec gate items.
- All INFEASIBLE items.
- Builder decision items (DEVIATION/DISCOVERY).
- SPEC_DISPUTEs on Architect-owned features (no Owner tag or `> Owner: Architect`) that do not reference Visual Specification screens.
- Untracked file items.

### 2.7 Canonical JSON Schema for Role Keys
The per-feature `critic.json` MUST include all four roles in both `action_items` and `role_status`:

```json
{
    "action_items": {
        "architect": [],
        "builder": [],
        "qa": [],
        "pm": []
    },
    "role_status": {
        "architect": "DONE | TODO",
        "builder": "DONE | TODO | FAIL | INFEASIBLE | BLOCKED",
        "qa": "CLEAN | TODO | FAIL | DISPUTED | N/A",
        "pm": "DONE | TODO | N/A"
    }
}
```

### 2.8 Aggregate Report Role Iteration
The aggregate report generator (`CRITIC_REPORT.md`) MUST iterate over `('Architect', 'Builder', 'QA', 'PM')` for the role-specific action items section. PM action items are listed under a `### PM` subsection.

### 2.9 SPEC_DISPUTE Visual Detection
Visual SPEC_DISPUTEs are detected by checking the dispute title for: `Visual:` prefix, `visual specification` substring (case-insensitive), or exact screen name matches from the feature's parsed `visual_spec.screen_names`. This heuristic covers the standard naming conventions without requiring structured metadata in discovery entries.

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

#### Scenario: Per-feature critic.json includes all four role keys

    Given the Critic tool completes analysis of a feature
    When the per-feature critic.json is written
    Then action_items contains architect, builder, qa, and pm arrays
    And role_status contains architect, builder, qa, and pm fields

#### Scenario: Architect action item from spec gate FAIL

    Given a feature has spec_gate.status FAIL due to missing Requirements section
    When the Critic generates action items
    Then an Architect action item is created with priority HIGH
    And no PM action item is created for this spec gap

#### Scenario: Builder action item from lifecycle reset

    Given a feature was previously in TESTING or COMPLETE lifecycle state
    And the feature spec is modified (file edit after status commit)
    And the feature lifecycle resets to TODO per feature_status.json
    When the Critic generates action items
    Then a Builder action item is created with priority HIGH
    And role_status.builder is TODO

#### Scenario: QA action item from TESTING status with manual scenarios

    Given a feature is in TESTING state per CDD feature_status.json
    And the feature has 3 manual scenarios
    When the Critic generates action items
    Then a QA action item is created identifying the feature and scenario count

#### Scenario: Anchor node Owner tag ignored

    Given an anchor node file (arch_*.md) with `> Owner: PM` metadata
    When the Critic parses the owner
    Then the owner resolves to Architect (anchor nodes are always Architect-owned)

### Manual Scenarios (Human Verification Required)

None.
