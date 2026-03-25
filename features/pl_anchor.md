# Feature: Anchor Node Authoring

> Label: "Agent Skills: PM: /pl-anchor Anchor Node Authoring"
> Category: "Agent Skills: PM"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The anchor node authoring skill shared by PM and PM roles. Provides a guided workflow for creating or updating anchor nodes (arch_*, design_*, policy_*) that define cross-cutting constraints, patterns, and invariants. Enforces template compliance, correct prefix selection, and cascade awareness (editing an anchor resets all dependent features to TODO).

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the PM or PM role.
- Non-PM agents MUST receive a redirect message.
- PM prefix restriction: PM may only create or modify `design_*` and `policy_*` anchors. `arch_*` anchors are PM-only.

### 2.2 Required Reading

- Before creating or updating any anchor node, the agent MUST read `instructions/references/spec_authoring_guide.md` Section 3 for anchor classification guidance.

### 2.3 Anchor Node Types

- `arch_*.md` -- Technical constraints: system architecture, API contracts, dependency rules.
- `design_*.md` -- Design constraints: visual language, typography, interaction patterns.
- `policy_*.md` -- Governance rules: security baselines, compliance, process protocols.

### 2.4 Template Compliance

- Anchor nodes MUST use the canonical template from `tools/feature_templates/_anchor.md`.
- Required section headings (Critic checks): `purpose` and `invariants` (case-insensitive substring).
- Heading `## 1. Overview` does NOT satisfy the `purpose` check.

### 2.5 Cascade Awareness

- Editing an anchor node resets ALL dependent features to TODO.
- The agent MUST identify and present the impact list before committing changes.

### 2.6 Post-Authoring

- After editing, commit the change and run `status.sh` to update the Critic report and reset dependent features.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-PM invocation

    Given an Engineer agent session
    When the agent invokes /pl-anchor
    Then the command responds with a redirect message

#### Scenario: PM restricted from arch_ prefix

    Given a PM agent session
    When the PM attempts to create an arch_data_layer.md anchor
    Then the command responds that arch_ anchors are PM-only

#### Scenario: New anchor uses template structure

    Given no anchor node exists for the topic
    When /pl-anchor creates a new anchor node
    Then the file contains purpose and invariants sections
    And the heading prefix matches the anchor type

#### Scenario: Cascade warning shows dependent features

    Given arch_api.md has 3 dependent features
    When /pl-anchor modifies arch_api.md
    Then the agent presents the list of 3 features that will reset to TODO
    And asks for confirmation before committing

### QA Scenarios

None.
