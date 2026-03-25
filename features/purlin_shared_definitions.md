# Feature: Purlin Shared Agent Definitions

> Label: "Shared Agent Definitions: File Classification and Conventions"
> Category: "Shared Agent Definitions"
> Prerequisite: features/purlin_instruction_architecture.md

## 1. Overview

Shared agent definitions are reference files that define cross-cutting rules used by all modes, skills, and instructions. They are extracted from the base instruction file to ensure single-source-of-truth maintenance. Changing a definition in one place updates behavior across all modes without editing multiple instruction sections. These files live in `instructions/references/` and are loaded on demand by skills and the mode guard.

---

## 2. Requirements

### 2.1 File Classification (`references/file_classification.md`)

- MUST define three ownership categories: CODE (Engineer), SPEC (PM), QA-OWNED.
- MUST list specific file patterns for each category (glob patterns or path prefixes).
- MUST define cross-mode recording rights (e.g., any mode can add OPEN discoveries to sidecars).
- MUST include a quick-reference table mapping file patterns to required modes.
- The mode guard in PURLIN_BASE.md MUST reference this file for ownership checks, not maintain inline lists.
- When a new file type is introduced to a project, this file is the ONLY place to update.
- CODE category MUST include: source code, scripts, tests, config, skill files, instruction files, agent definitions, hooks, build/CI config, launcher scripts, technical anchors, companion files, process config.
- SPEC category MUST include: feature specs, design anchors, policy anchors, visual design artifacts, prose documentation.
- QA-OWNED category MUST include: discovery sidecars, QA scenario tags, regression JSON, QA verification scripts.

### 2.2 Commit Conventions (`references/commit_conventions.md`)

- MUST define mode attribution prefixes (Engineer: feat/fix/test, PM: spec/design, QA: qa/status).
- MUST define the `Purlin-Mode:` trailer requirement.
- MUST define status tag commit format and scope types.
- MUST define lifecycle reset exemption tags (`[QA-Tags]`, `[Spec-FMT]`, `[Migration]`).
- MUST define commit discipline rules (logical milestones, standalone status tags).

### 2.3 Active Deviations (`references/active_deviations.md`)

- MUST define the companion file table format (columns: Spec says, Implementation does, Tag, PM status).
- MUST define the decision hierarchy (spec baseline → deviation overrides → PENDING/ACCEPTED/REJECTED).
- MUST define the three Engineer-to-PM flows (INFEASIBLE, inline deviation, SPEC_PROPOSAL).
- MUST define builder decision tags with severity levels.
- MUST define PM review protocol.

### 2.4 Knowledge Colocation (`references/knowledge_colocation.md`)

- MUST define anchor node taxonomy (arch_*, design_*, policy_*) with ownership.
- MUST define the cross-cutting standards pattern (anchor → foundation → consumer).
- MUST define companion file conventions (standalone, not a feature file, status reset exemption).
- MUST define discovery sidecar conventions (QA lifecycle, queue hygiene).
- MUST define discovery types and lifecycle.

### 2.5 Design Constraint: Single Source of Truth

- Each definition MUST exist in exactly one reference file.
- PURLIN_BASE.md MUST NOT duplicate definition content — it references the file instead.
- Skills MUST reference the same files for consistency.
- Mode write-access lists in PURLIN_BASE.md say "All files classified as CODE/SPEC/QA-OWNED in `references/file_classification.md`" — not inline enumerations.

---

## 3. Scenarios

### Unit Tests

#### Scenario: File classification covers all standard file types

    Given references/file_classification.md exists
    When all file patterns from the three categories are extracted
    Then source code, scripts, tests, config, skill files, instruction files are CODE
    And feature specs, design anchors, policy anchors are SPEC
    And discovery sidecars, QA tags, regression JSON are QA-OWNED

#### Scenario: PURLIN_BASE.md references file classification not inline lists

    Given instructions/PURLIN_BASE.md exists
    When the mode definitions (Engineer, PM, QA) are parsed
    Then write-access rules reference "references/file_classification.md"
    And no mode definition contains an inline enumeration of file patterns

#### Scenario: Commit conventions define all required elements

    Given references/commit_conventions.md exists
    When the content is parsed
    Then it defines mode prefixes for Engineer, PM, QA
    And it defines the Purlin-Mode trailer
    And it defines status tag format
    And it defines exemption tags

#### Scenario: Active deviations define table format and flows

    Given references/active_deviations.md exists
    When the content is parsed
    Then it defines the Active Deviations table columns
    And it defines INFEASIBLE, inline deviation, and SPEC_PROPOSAL flows
    And it defines builder decision tags with severity

#### Scenario: Knowledge colocation defines all artifact types

    Given references/knowledge_colocation.md exists
    When the content is parsed
    Then it defines anchor node taxonomy with 3 prefixes
    And it defines companion file conventions
    And it defines discovery sidecar conventions
    And it defines discovery types and lifecycle

#### Scenario: No definition is duplicated between base and reference

    Given PURLIN_BASE.md and all reference files
    When checking for duplicated definitions
    Then the Active Deviations table format appears only in active_deviations.md
    And commit prefixes appear only in commit_conventions.md
    And file pattern lists appear only in file_classification.md
    And anchor taxonomy details appear only in knowledge_colocation.md

### QA Scenarios

#### Scenario: Mode guard uses file classification for ownership check

    Given the agent is in PM mode
    And references/file_classification.md classifies .claude/commands/*.md as CODE
    When the agent attempts to write a skill file
    Then the mode guard blocks the write
    And references the file classification in its response

## Regression Guidance
- Verify no inline file pattern lists remain in PURLIN_BASE.md mode definitions
- Verify all four reference files exist and are non-empty
- Verify file_classification.md covers every file type the agent encounters in normal operation
- Verify commit_conventions.md matches the conventions actually used in git log
- Verify adding a new file type to file_classification.md is reflected in mode guard behavior
