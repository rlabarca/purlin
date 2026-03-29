# Feature: Anchor Node Authoring

> Label: "Agent Skills: PM: purlin:anchor Anchor Node Authoring"
> Category: "Agent Skills: PM"

[TODO]

## 1. Overview

The anchor node authoring skill with dual-mode behavior. For `design_*`, `policy_*`, `ops_*`, and `prodbrief_*` anchors, it activates PM mode. For `arch_*` anchors, it activates Engineer mode. Provides a guided workflow for creating or updating anchor nodes that define cross-cutting constraints, patterns, and invariants. Enforces template compliance, correct prefix selection, and cascade awareness (editing an anchor resets all dependent features to TODO). Arguments starting with `i_` are redirected to `purlin:invariant` since invariant files are externally-sourced and locally immutable.

---

## 2. Requirements

### 2.1 Mode Activation

- `design_*`, `policy_*`, `ops_*`, and `prodbrief_*` anchors activate PM mode.
- `arch_*` anchors activate Engineer mode.
- The skill determines the mode from the argument's prefix.

### 2.1.1 Invariant Prefix Redirect

If the topic argument starts with `i_`, the skill MUST NOT create or edit the file. Instead, redirect to `purlin:invariant`:
- "This is an invariant anchor (externally-sourced, locally immutable). Use `purlin:invariant add` to import it from a source repo, or `purlin:invariant add-figma` for Figma-sourced design invariants."

### 2.2 Prefix Disambiguation

When the topic argument does not start with a recognized prefix (`arch_`, `design_`, `policy_`, `ops_`, `prodbrief_`), the skill MUST prompt the user to choose the anchor type before proceeding. It MUST NOT default to any type silently. The prompt presents all five options with brief domain descriptions.

### 2.3 Required Reading

- Before creating or updating any anchor node, the agent MUST read `references/spec_authoring_guide.md` Section 3 for anchor classification guidance.

### 2.4 Anchor Node Types

- `arch_*.md` -- Technical constraints: system architecture, API contracts, dependency rules. (Engineer mode)
- `design_*.md` -- Design constraints: visual language, typography, interaction patterns. (PM mode)
- `policy_*.md` -- Governance rules: security baselines, compliance, process protocols. (PM mode)
- `ops_*.md` -- Operational constraints: CI/CD, deployment, monitoring, infrastructure mandates. (PM mode)
- `prodbrief_*.md` -- Product goals: user stories, outcomes, KPIs, success criteria. (PM mode)

All five types can also exist as invariants via the `i_` prefix (e.g., `i_arch_*.md`), managed by `purlin:invariant`.

### 2.4.1 Prodbrief Template Override

`prodbrief_*` anchors use a modified template structure: `## User Stories` and `## Success Criteria` sections replace the standard `## <Domain> Invariants` section.

### 2.5 Template Compliance

- Anchor nodes MUST use the canonical template from `scripts/feature_templates/_anchor.md`.
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

    Given the agent invokes purlin:anchor with argument "authentication"
    And "authentication" does not start with arch_, design_, policy_, ops_, or prodbrief_
    When the skill processes the argument
    Then the agent presents all five anchor type options with descriptions
    And waits for the user's choice before proceeding
    And does not default to any type

#### Scenario: Recognized prefix skips disambiguation

    Given the agent invokes purlin:anchor with argument "arch_data_layer"
    When the skill processes the argument
    Then Engineer mode is activated
    And the skill proceeds directly without prompting for type

#### Scenario: New anchor uses template structure

    Given no anchor node exists for the topic
    When purlin:anchor creates a new anchor node
    Then the file contains purpose and invariants sections
    And the heading prefix matches the anchor type

#### Scenario: Cascade warning shows dependent features

    Given arch_api.md has 3 dependent features
    When purlin:anchor modifies arch_api.md
    Then the agent presents the list of 3 features that will reset to TODO
    And asks for confirmation before committing

#### Scenario: Invariant prefix redirects to purlin:invariant

    Given the agent invokes purlin:anchor with argument "i_arch_api_standards"
    When the skill processes the argument
    Then the agent does not create or edit any file
    And redirects to purlin:invariant with an explanatory message

#### Scenario: ops_* anchor activates PM mode

    Given the agent invokes purlin:anchor with argument "ops_ci_pipeline"
    When the skill processes the argument
    Then PM mode is activated
    And the skill proceeds with anchor creation

#### Scenario: prodbrief_* anchor uses modified template

    Given the agent invokes purlin:anchor with argument "prodbrief_q2_goals"
    When the skill creates a new anchor node
    Then the file contains User Stories and Success Criteria sections
    And does not contain a Domain Invariants section

### QA Scenarios

None.
