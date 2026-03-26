# Feature: Anchor Node Authoring

> Label: "Agent Skills: PM: /pl-anchor Anchor Node Authoring"
> Category: "Agent Skills: PM"

[TODO]

## 1. Overview

The anchor node authoring skill with dual-mode behavior. For `design_*` and `policy_*` anchors, it activates PM mode. For `arch_*` anchors, it activates Engineer mode. Provides a guided workflow for creating or updating anchor nodes that define cross-cutting constraints, patterns, and invariants. Enforces template compliance, correct prefix selection, and cascade awareness (editing an anchor resets all dependent features to TODO).

---

## 2. Requirements

### 2.1 Mode Activation

- `design_*` and `policy_*` anchors activate PM mode.
- `arch_*` anchors activate Engineer mode.
- The skill determines the mode from the argument's prefix.

### 2.2 Prefix Disambiguation

When the topic argument does not start with a recognized prefix (`arch_`, `design_`, `policy_`), the skill MUST prompt the user to choose the anchor type before proceeding. It MUST NOT default to any type silently. The prompt presents all three options with brief domain descriptions.

### 2.3 Required Reading

- Before creating or updating any anchor node, the agent MUST read `instructions/references/spec_authoring_guide.md` Section 3 for anchor classification guidance.

### 2.4 Anchor Node Types

- `arch_*.md` -- Technical constraints: system architecture, API contracts, dependency rules.
- `design_*.md` -- Design constraints: visual language, typography, interaction patterns.
- `policy_*.md` -- Governance rules: security baselines, compliance, process protocols.

### 2.5 Template Compliance

- Anchor nodes MUST use the canonical template from `tools/feature_templates/_anchor.md`.
- Required section headings (scan checks): `purpose` and `invariants` (case-insensitive substring).
- Heading `## 1. Overview` does NOT satisfy the `purpose` check.

### 2.6 Cascade Awareness

- Editing an anchor node resets ALL dependent features to TODO.
- The agent MUST identify and present the impact list before committing changes.

### 2.7 Post-Authoring

- After editing, commit the change and run `scan.sh` to refresh scan results and reset dependent features.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Prefix disambiguation prompts when no recognized prefix

    Given the agent invokes /pl-anchor with argument "authentication"
    And "authentication" does not start with arch_, design_, or policy_
    When the skill processes the argument
    Then the agent presents all three anchor type options with descriptions
    And waits for the user's choice before proceeding
    And does not default to any type

#### Scenario: Recognized prefix skips disambiguation

    Given the agent invokes /pl-anchor with argument "arch_data_layer"
    When the skill processes the argument
    Then Engineer mode is activated
    And the skill proceeds directly without prompting for type

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
