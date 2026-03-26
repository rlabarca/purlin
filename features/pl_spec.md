# Feature: Spec Authoring

> Label: "Agent Skills: PM: /pl-spec Spec Authoring"
> Category: "Agent Skills: PM"
> Prerequisite: features/impl_notes_companion.md
> Prerequisite: features/pl_find.md

[TODO]

## 1. Overview

The core spec authoring skill shared by PM and PM roles. Provides a guided workflow for creating new feature specs or refining existing ones, enforcing template compliance, category/label conventions, prerequisite checklist validation, and scan parser requirements. Integrates with `/pl-find` for topic discovery before authoring.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the PM or PM role.
- Non-PM agents MUST receive a redirect message.

### 2.2 Required Reading

- Before authoring or refining any spec, the agent MUST read `instructions/references/spec_authoring_guide.md` for shared authoring principles.

### 2.3 Topic Discovery

- The command MUST first run `/pl-find` logic to determine if a spec already exists or needs updating.
- If updating: open the existing feature file, review, identify gaps, propose targeted additions or revisions. Apply after user confirmation.
- If creating: follow the template and format rules.

### 2.4 Template Compliance

- New feature files MUST use the canonical template structure from `tools/feature_templates/_feature.md`.
- Required section headings (scan checks): a heading containing `overview`, `requirements`, and `scenarios`. Matching is case-insensitive substring (e.g., `## 2. Requirements` matches the `requirements` check).
- Scenario headings MUST use four-hash `####` format.

### 2.5 Category and Label Conventions

- Before assigning a category, the agent MUST scan `.purlin/cache/dependency_graph.json` for existing categories.
- Slash command features always go in "Agent Skills" category.
- Label prefix patterns MUST match the chosen category.

### 2.6 Prerequisite Checklist

- Features rendering UI MUST declare relevant `design_*.md` anchor prerequisites.
- Features accessing/transforming data MUST declare relevant `arch_*.md` anchor prerequisites.
- Features in governed processes MUST declare relevant `policy_*.md` anchor prerequisites.

### 2.7 Post-Authoring

- After editing, commit the change and run `scan.sh` to refresh scan results.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-PM invocation

    Given an Engineer agent session
    When the agent invokes /pl-spec
    Then the command responds with a redirect message
    And no spec file is created or modified

#### Scenario: Topic discovery finds existing spec

    Given a feature spec exists at features/my_feature.md
    When /pl-spec is invoked with argument "my_feature"
    Then the existing spec is opened for review
    And gaps are identified and proposed to the user

#### Scenario: New spec uses template structure

    Given no feature spec exists for the topic
    When /pl-spec creates a new feature file
    Then the file contains overview, requirements, and scenarios sections
    And scenario headings use four-hash format
    And the file is ready for Engineer implementation

#### Scenario: Category scan prevents duplicate categories

    Given dependency_graph.json contains category "Agent Skills"
    When /pl-spec creates a spec for a slash command feature
    Then the spec uses category "Agent Skills"
    And no new category is invented

#### Scenario: Prerequisite checklist enforced for UI features

    Given the new feature renders HTML/CSS output
    When /pl-spec creates the spec
    Then relevant design_*.md anchors are declared as prerequisites

### QA Scenarios

None.
