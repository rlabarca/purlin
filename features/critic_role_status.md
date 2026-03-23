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
| **QA** | `CLEAN`, `TODO`, `AUTO`, `FAIL`, `DISPUTED`, `N/A` |
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
*   `BLOCKED`: OPEN SPEC_DISPUTE exists for this feature (scenarios suspended). Only OPEN-status disputes trigger BLOCKED; disputes in SPEC_UPDATED, RESOLVED, or PRUNED status do not.

Builder Precedence (highest wins): INFEASIBLE > BLOCKED > FAIL > TODO > DONE.

**QA Status:**
*   `FAIL`: Has OPEN BUGs in discovery sidecar. (Lifecycle-independent.)
*   `DISPUTED`: Has OPEN SPEC_DISPUTEs in discovery sidecar (no BUGs). (Lifecycle-independent.)
*   `TODO`: Any of: (a) Feature in TESTING lifecycle state with at least one manual QA item (QA scenario without `@auto` tag); (b) Has SPEC_UPDATED items AND feature is in TESTING lifecycle state. Mixed auto+manual = TODO.
*   `AUTO`: Feature in TESTING lifecycle state with QA scenarios, ALL of which are `@auto`-tagged. Zero manual QA items. Visual spec items are Builder-verified and do NOT contribute to QA status.
*   `CLEAN`: `tests/<feature>/tests.json` exists with `status: "PASS"`, AND no FAIL/DISPUTED/TODO/AUTO conditions matched.
*   `N/A`: No FAIL/DISPUTED/TODO/AUTO/CLEAN conditions matched.

QA Precedence (highest wins): FAIL > DISPUTED > TODO > AUTO > CLEAN > N/A.

**PM Status:**
*   `DONE`: No PM action items for this feature.
*   `TODO`: Pending PM work (visual spec gaps, stale designs, disputes on PM-owned features, disputes triaged to PM via `Action Required: PM`).
*   `N/A`: Feature has no Visual Specification section, no Figma references, and is not `> Owner: PM`.

### 2.5 Action Item Routing

The Critic generates imperative action items for each role based on analysis results. The following table defines the complete routing rules for all four roles:

**Architect action items:**

| Source | Priority | Example |
|--------|----------|---------|
| Spec Gate FAIL (missing sections, broken prereqs) | HIGH | "Fix spec gap: section_completeness -- missing Requirements" |
| OPEN DISCOVERY/INTENT_DRIFT in User Testing | HIGH | "Update spec for cdd_status_monitor: [discovery title]" |
| OPEN SPEC_DISPUTE on Architect-owned features (no Owner tag or `> Owner: Architect`) that do not reference Visual Specification screens and do not have `Action Required: PM` set | HIGH | "Review disputed scenario in critic_tool: [dispute title]" |
| SPEC_DISPUTEs with explicit `Action Required: Architect` (override, e.g. on PM-owned features) | HIGH | "Review disputed scenario in X: [dispute title]" |
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
| OPEN SPEC_DISPUTE (dispute routes to PM or Architect) | LOW | "Scenario suspended pending SPEC_DISPUTE resolution by PM for X" |

The SPEC_DISPUTE informational item satisfies the role_status/action_item consistency rule: QA=DISPUTED must have at least one QA action item. The item is LOW priority because QA has no actionable work -- the resolution is owned by PM or Architect.

**PM action items:**

| Source | Priority | Example |
|--------|----------|---------|
| SPEC_DISPUTEs on features with `> Owner: PM` | HIGH | "Review disputed scenario in X: [dispute title]" |
| SPEC_DISPUTEs referencing Visual Specification screens (regardless of Owner tag) | HIGH | "Review visual dispute in X: [dispute title]" |
| SPEC_DISPUTEs with explicit `Action Required: PM` (Architect triage) | HIGH | "Review disputed scenario in X: [dispute title]" |
| `stale_design_description` items | LOW | "Re-process stale design for X: [screen]" |
| `unprocessed_artifact` items | HIGH | "Process design artifact for X: [screen]" |
| `missing_design_reference` items | MEDIUM | "Fix missing design reference for X: [screen]" |
| DESIGN_CONFLICT warnings (from `/pl-design-audit`, not Critic-generated) | MEDIUM | "Resolve design conflict in X: [detail]" |

### 2.6 Architect-Retained Items
The following items remain with Architect and MUST NOT be routed to PM:
- All spec gate items.
- All INFEASIBLE items.
- Builder decision items (DEVIATION/DISCOVERY).
- SPEC_DISPUTEs on Architect-owned features (no Owner tag or `> Owner: Architect`) that do not reference Visual Specification screens and do not have `Action Required: PM` set.
- Untracked file items.

### 2.6.1 SPEC_DISPUTE Resolution Handoff
When PM or Architect resolves a SPEC_DISPUTE, the resolution cascade to Builder works as follows:

*   **Resolution with spec edit** (typical): PM/Architect updates the Visual Specification or scenario in the feature file. This edit resets the feature to TODO lifecycle, signaling the Builder via the standard lifecycle reset mechanism. The discovery transitions from OPEN to SPEC_UPDATED.
*   **Resolution without spec edit** (dispute rejected): PM/Architect determines the current spec is correct and marks the discovery as RESOLVED in the sidecar file without editing the feature file. In this case, no lifecycle reset occurs. Builder's BLOCKED status clears automatically because the OPEN SPEC_DISPUTE no longer exists (RESOLVED disputes do not trigger BLOCKED). Builder status reverts to whatever it was before the dispute (typically DONE if tests pass).
*   **Invariant:** The resolver (PM or Architect) MUST transition the discovery status from OPEN to either SPEC_UPDATED (if the spec is changed) or RESOLVED (if the spec is upheld). Leaving a dispute in OPEN status after resolution is a process error.

### 2.7 Canonical JSON Schema for Role Keys
The per-feature `critic.json` MUST include all four roles in `action_items`, `role_status`, and `role_status_reason`:

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
        "qa": "CLEAN | TODO | AUTO | FAIL | DISPUTED | N/A",
        "pm": "DONE | TODO | N/A"
    },
    "role_status_reason": {
        "architect": "<human-readable reason for current status>",
        "builder": "<human-readable reason for current status>",
        "qa": "<human-readable reason for current status>",
        "pm": "<human-readable reason for current status>"
    }
}
```

**Role Status Reason:** For each role, the Critic MUST produce a human-readable one-line reason explaining WHY the role has its current status. Terminal states use brief reasons: `"no action items"` (Architect DONE), `"all tests pass, no open items"` (Builder DONE), `"tests pass, no discoveries"` (QA CLEAN), `"no visual or design work"` (PM N/A). Non-terminal states include the specific trigger: `"spec modified after status commit (implementation exists, all tests pass)"`, `"missing tests.json"`, `"3 open BUGs in discovery sidecar"`, `"2 OPEN SPEC_DISPUTEs"`, etc. This eliminates the need for agents to investigate why a status value was assigned.

**QA CLEAN Gate — Regression Guidance:** QA status MUST NOT be CLEAN if the feature has a `## Regression Guidance` section AND no corresponding `tests/qa/scenarios/<feature_name>.json` exists AND no `> Regression Coverage: Yes` metadata line is present. In this case, QA status is TODO with reason `"regression harness authoring pending"`. This prevents completed features with unresolved regression guidance from disappearing from the QA work queue.

### 2.7.1 Lifecycle Reset Context

When a feature's lifecycle resets to TODO (spec file modified after status commit), the Critic MUST distinguish between genuinely unimplemented features and features that were reset by a spec touch. For `lifecycle_reset` category action items, the Critic MUST include a `reset_context` object:

```json
{
    "category": "lifecycle_reset",
    "reset_context": {
        "has_passing_tests": true,
        "structural_completeness": "PASS | WARN | FAIL | MISSING",
        "traceability": "PASS | WARN | FAIL",
        "scenario_diff": {
            "new": ["Scenario Title A"],
            "modified": ["Scenario Title B"],
            "removed": ["Scenario Title C"],
            "has_diff": true
        },
        "requirements_changed": true,
        "changed_sections": ["2.2", "2.5"]
    },
    "description": "<context-aware description>"
}
```

**Field definitions:**
*   `has_passing_tests`: `true` when `tests/<feature>/tests.json` exists AND contains `"status": "PASS"`. The timestamp of `tests.json` relative to the spec file is irrelevant — only the content matters. A cosmetic spec touch (heading rename, whitespace edit) MUST NOT invalidate passing tests.

**Description generation rules based reset context:**
*   If `has_passing_tests && !scenario_diff.has_diff && !requirements_changed`: `"Re-verify and re-tag <feature_name> (spec touched, no behavioral changes, implementation exists)"`
*   If `scenario_diff.has_diff`: `"Implement spec changes for <feature_name>: N new scenario(s) [titles], M modified [titles], K removed [titles]"` (existing behavior)
*   If `requirements_changed && !scenario_diff.has_diff`: `"Review requirements changes for <feature_name>: sections [changed_sections]"`

This eliminates the re-implementation loop where a Builder attempts to re-implement code that already exists because a spec file was touched without behavioral changes.

### 2.8 Aggregate Report Role Iteration
The aggregate report generator (`CRITIC_REPORT.md`) MUST iterate over `('Architect', 'Builder', 'QA', 'PM')` for the role-specific action items section. PM action items are listed under a `### PM` subsection.

**Note:** This iteration order (Architect first, PM last) differs from the CDD dashboard column order (PM first, then Architect, Builder, QA). The difference is intentional: the report is agent-facing and follows the traditional workflow sequence (spec -> build -> verify -> design review), while the dashboard is human-facing and places PM first as the project-level oversight role.

### 2.9 SPEC_DISPUTE Visual Detection
Visual SPEC_DISPUTEs are detected by checking the dispute title for: `Visual:` prefix, `visual specification` substring (case-insensitive), or exact screen name matches from the feature's parsed `visual_spec.screen_names`. This heuristic covers the standard naming conventions without requiring structured metadata in discovery entries. **Precedence:** The `Action Required` override (Section 2.5) takes precedence over visual detection heuristics. If `Action Required: Architect` is set on a dispute with a visual title, the dispute routes to Architect despite the visual heuristic. If `Action Required: PM` is set on a non-visual dispute, it routes to PM without needing a visual title match.

---

## 3. Scenarios

### Unit Tests

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

#### Scenario: QA action item from TESTING status with manual QA items

    Given a feature is in TESTING state per CDD feature_status.json
    And the feature has 3 manual QA scenarios
    When the Critic generates action items
    Then a QA action item is created identifying the feature and scenario count

#### Scenario: Anchor node Owner tag ignored

    Given an anchor node file (arch_*.md) with `> Owner: PM` metadata
    When the Critic parses the owner
    Then the owner resolves to Architect (anchor nodes are always Architect-owned)

#### Scenario: QA DISPUTED generates informational action item when dispute routes to PM

    Given a feature file with `> Owner: PM` metadata
    And the feature has an OPEN SPEC_DISPUTE in its discovery sidecar
    When the Critic computes role status and generates action items
    Then role_status.qa is DISPUTED
    And a LOW-priority QA action item is generated describing the suspended scenario
    And the QA action item references PM as the resolver
    And the HIGH-priority resolution action item appears in the pm action items

#### Scenario: SPEC_DISPUTE with Action Required PM on Architect-owned feature routes to PM

    Given a feature file with `> Owner: Architect` metadata (or no Owner tag)
    And the feature has an OPEN SPEC_DISPUTE with `Action Required: PM`
    When the Critic generates action items
    Then the SPEC_DISPUTE appears in the `pm` action items
    And does not appear in the `architect` action items
    And a LOW-priority QA action item is generated describing the suspended scenario
    And the QA action item references PM as the resolver

#### Scenario: SPEC_DISPUTE with Action Required Architect on PM-owned feature stays with Architect

    Given a feature file with `> Owner: PM` metadata
    And the feature has an OPEN SPEC_DISPUTE with `Action Required: Architect`
    When the Critic generates action items
    Then the SPEC_DISPUTE appears in the `architect` action items
    And does not appear in the `pm` action items
    And a LOW-priority QA action item is generated describing the suspended scenario
    And the QA action item references Architect as the resolver

#### Scenario: Builder BLOCKED clears when SPEC_DISPUTE moves to RESOLVED

    Given a feature had an OPEN SPEC_DISPUTE (Builder was BLOCKED)
    And PM resolves the dispute by marking it RESOLVED without editing the feature file
    When the Critic computes role status
    Then role_status.builder is not BLOCKED (no OPEN disputes remain)
    And the feature lifecycle has NOT reset to TODO (no spec edit occurred)

#### Scenario: Role status reason populated for all roles

    Given a feature with builder status TODO due to lifecycle reset
    When the Critic generates critic.json
    Then the role_status_reason object contains a key for each role (architect, builder, qa, pm)
    And each value is a non-empty human-readable string
    And builder reason contains the specific trigger (e.g., "spec modified after status commit")

#### Scenario: Reset context distinguishes spec-touch from real change

    Given a feature was previously at COMPLETE lifecycle state with all tests passing
    And the Architect touches the spec file (whitespace edit, no scenario or requirements change)
    And the feature resets to TODO lifecycle state
    When the Critic generates the lifecycle_reset action item
    Then reset_context.has_passing_tests is true
    And reset_context.scenario_diff.has_diff is false
    And reset_context.requirements_changed is false
    And the description reads "Re-verify and re-tag <feature_name> (spec touched, no behavioral changes, implementation exists)"

#### Scenario: Reset context with new scenarios

    Given a feature was previously at COMPLETE lifecycle state
    And the Architect adds 2 new automated scenarios and modifies 1 existing scenario
    And the feature resets to TODO lifecycle state
    When the Critic generates the lifecycle_reset action item
    Then reset_context.scenario_diff.has_diff is true
    And reset_context.scenario_diff.new contains 2 scenario titles
    And reset_context.scenario_diff.modified contains 1 scenario title
    And the description includes "2 new scenario(s)" and "1 modified"

#### Scenario: Reset context with requirements-only change

    Given a feature was previously at COMPLETE lifecycle state
    And the Architect modifies Requirements section 2.3 without changing any scenarios
    And the feature resets to TODO lifecycle state
    When the Critic generates the lifecycle_reset action item
    Then reset_context.scenario_diff.has_diff is false
    And reset_context.requirements_changed is true
    And reset_context.changed_sections contains "2.3"
    And the description includes "Review requirements changes"

#### Scenario: Reset context for genuinely unimplemented feature

    Given a feature has never had a status commit (no tests.json exists)
    And the feature is in TODO lifecycle state
    When the Critic generates action items
    Then the builder action item has category "lifecycle_reset"
    And reset_context.has_passing_tests is false
    And reset_context.structural_completeness is "MISSING"
    And the description follows the existing format "Implement spec changes for <feature_name>"

#### Scenario: QA AUTO when all QA scenarios are @auto

    Given a feature is in TESTING lifecycle state
    And the feature has 3 QA scenarios, all with @auto tag
    And the feature has no manual QA items
    When the Critic computes role status
    Then role_status.qa is AUTO
    And role_status_reason.qa describes "all QA scenarios are auto"

#### Scenario: QA TODO when mixed auto and manual QA scenarios

    Given a feature is in TESTING lifecycle state
    And the feature has 2 QA scenarios with @auto tag
    And the feature has 1 QA scenario without @auto tag
    When the Critic computes role status
    Then role_status.qa is TODO
    And role_status_reason.qa describes "has manual QA items"

#### Scenario: QA AUTO with visual spec on Web Test feature

    Given a feature is in TESTING lifecycle state
    And the feature has `> Web Test:` metadata
    And the feature has a Visual Specification with 3 checklist items
    And the feature has no QA scenarios without @auto tag
    When the Critic computes role status
    Then role_status.qa is AUTO
    And visual spec items are classified as auto (web test)

### QA Scenarios

None.
